"""
tests/test_connectors.py
========================
Unit tests for deployment/connectors.py — MyEnergiConnector and price/device stubs.

All tests use mock HTTP responses so no live API calls are made.  The test suite
verifies the parsing logic that was confirmed against the live API on 2026-03-15,
guarding against regressions when connector.py is refactored.

Test classes
------------
TestDecodeBdd            — _decode_bdd() static method (bdd string → day names)
TestGetScheduleParsing   — get_schedule() response parsing (endpoint confirmed live)
TestGetHistoryDayParsing — get_history_day() 1441-entry structure parsing
TestGetStatusParsing     — get_status() list/dict response format handling
TestMockDeviceConnector  — MockDeviceConnector smoke tests
TestMockPriceConnector   — MockPriceConnector smoke tests
"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment"))

from connectors import MockDeviceConnector, MockPriceConnector, MyEnergiConnector


# ---------------------------------------------------------------------------
# Helper: build a connector without making any network calls
# ---------------------------------------------------------------------------

def make_connector() -> MyEnergiConnector:
    """Return a MyEnergiConnector with test credentials and a pre-set server.

    Setting _server bypasses _discover_server() so no HTTP requests are
    made during test setup.
    """
    c = MyEnergiConnector(serial="21509692", api_key="TEST_KEY")
    c._server = "https://s18.myenergi.net"
    return c


# ---------------------------------------------------------------------------
# 1. _decode_bdd
# ---------------------------------------------------------------------------

class TestDecodeBdd:
    """Unit tests for MyEnergiConnector._decode_bdd().

    Day mapping confirmed live (2026-03-15):
        bdd[0] = unused
        bdd[1] = Mon, bdd[2] = Tue, bdd[3] = Wed, bdd[4] = Thu,
        bdd[5] = Fri, bdd[6] = Sat, bdd[7] = Sun
    """

    def test_weekdays_and_sunday(self):
        """'01111101' = Mon+Tue+Wed+Thu+Fri+Sun (slots 11 & 12 — confirmed live)."""
        result = MyEnergiConnector._decode_bdd("01111101")
        assert result == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sun"]

    def test_saturday_only(self):
        """'00000010' = Saturday only (slots 13 & 14 — confirmed live)."""
        result = MyEnergiConnector._decode_bdd("00000010")
        assert result == ["Sat"]

    def test_sat_and_sun(self):
        """'00000011' = Saturday and Sunday."""
        result = MyEnergiConnector._decode_bdd("00000011")
        assert result == ["Sat", "Sun"]

    def test_weekdays_and_saturday(self):
        """'01111110' = Mon–Fri+Sat (no Sunday).

        bdd[6]=Sat, so '0' at position 6 means NOT Sat.
        '01111110' has position 6='1' → Sat included, position 7='0' → Sun excluded.
        Note: '01111100' = Mon–Fri only (positions 6 and 7 both '0').
        """
        result = MyEnergiConnector._decode_bdd("01111110")
        assert result == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def test_weekdays_only_no_sat(self):
        """'01111100' = Mon–Fri only (positions 6+7 = Sat+Sun both '0')."""
        result = MyEnergiConnector._decode_bdd("01111100")
        assert result == ["Mon", "Tue", "Wed", "Thu", "Fri"]

    def test_all_seven_days(self):
        """'01111111' = all days."""
        result = MyEnergiConnector._decode_bdd("01111111")
        assert result == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def test_monday_only(self):
        """'01000000' = Monday only."""
        result = MyEnergiConnector._decode_bdd("01000000")
        assert result == ["Mon"]

    def test_sunday_only(self):
        """'00000001' = Sunday only."""
        result = MyEnergiConnector._decode_bdd("00000001")
        assert result == ["Sun"]

    def test_all_zeros_returns_empty(self):
        """'00000000' = no active days → empty list."""
        result = MyEnergiConnector._decode_bdd("00000000")
        assert result == []

    def test_empty_string_returns_empty(self):
        """Empty string must return empty list without raising."""
        result = MyEnergiConnector._decode_bdd("")
        assert result == []

    def test_wrong_length_returns_empty(self):
        """Strings of wrong length return empty list."""
        assert MyEnergiConnector._decode_bdd("0111") == []
        assert MyEnergiConnector._decode_bdd("011111010") == []

    def test_position_zero_is_unused(self):
        """Position 0 is always ignored — '10000000' = no active days."""
        result = MyEnergiConnector._decode_bdd("10000000")
        assert result == []

    def test_position_zero_does_not_add_extra_day(self):
        """'11111111' = same as '01111111' — position 0 never adds a day."""
        with_bit0 = MyEnergiConnector._decode_bdd("11111111")
        without   = MyEnergiConnector._decode_bdd("01111111")
        assert with_bit0 == without


# ---------------------------------------------------------------------------
# 2. get_schedule parsing
# ---------------------------------------------------------------------------

class TestGetScheduleParsing:
    """Tests for get_schedule() response parsing.

    Uses the confirmed live response structure (2026-03-15):
        endpoint: /cgi-boost-time-E{serial}
        response key: boost_times  (NOT 'boost' or 'timers')
        bdd: 8-char string, positions 1–7 = Mon–Sun
    """

    # Live schedule confirmed 2026-03-15 (four active slots)
    _MOCK_BOOST_TIMES = {
        "boost_times": [
            # Slot 11: 07:00 +30min Mon–Fri+Sun
            {"slt": 11, "bsh": 7,  "bsm": 0,  "bdh": 0, "bdm": 30, "bdd": "01111101"},
            # Slot 12: 19:45 +30min Mon–Fri+Sun
            {"slt": 12, "bsh": 19, "bsm": 45, "bdh": 0, "bdm": 30, "bdd": "01111101"},
            # Slot 13: 09:15 +3h Saturday only
            {"slt": 13, "bsh": 9,  "bsm": 15, "bdh": 3, "bdm": 0,  "bdd": "00000010"},
            # Slot 14: 14:00 +3h Saturday only
            {"slt": 14, "bsh": 14, "bsm": 0,  "bdh": 3, "bdm": 0,  "bdd": "00000010"},
            # Inactive slot — must be filtered out
            {"slt": 21, "bsh": 0,  "bsm": 0,  "bdh": 0, "bdm": 0,  "bdd": "00000000"},
        ]
    }

    def test_returns_four_active_slots(self):
        """Inactive slot (bdd all-zeros) is excluded; 4 active slots returned."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        assert len(timers) == 4

    def test_sorted_by_start_time(self):
        """Results are sorted ascending by (start_hour, start_min)."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        starts = [(t["start_hour"], t["start_min"]) for t in timers]
        assert starts == sorted(starts), f"Expected sorted order, got {starts}"

    def test_slot11_correct_days(self):
        """Slot 11 (bdd='01111101') → Mon+Tue+Wed+Thu+Fri+Sun."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot11 = next(t for t in timers if t["slot"] == 11)
        assert slot11["days"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sun"]

    def test_slot13_saturday_only(self):
        """Slot 13 (bdd='00000010') → Saturday only."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot13 = next(t for t in timers if t["slot"] == 13)
        assert slot13["days"] == ["Sat"]

    def test_slot13_duration_180_minutes(self):
        """Slot 13: bdh=3, bdm=0 → duration_min=180."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot13 = next(t for t in timers if t["slot"] == 13)
        assert slot13["duration_min"] == 180
        assert slot13["start_hour"] == 9
        assert slot13["start_min"] == 15

    def test_slot11_duration_30_minutes(self):
        """Slot 11: bdh=0, bdm=30 → duration_min=30."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot11 = next(t for t in timers if t["slot"] == 11)
        assert slot11["duration_min"] == 30

    def test_slot12_label_contains_time(self):
        """Slot 12 label contains '19:45' and '30min'."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot12 = next(t for t in timers if t["slot"] == 12)
        assert "19:45" in slot12["label"]
        assert "30min" in slot12["label"]

    def test_slot14_label_contains_sat(self):
        """Slot 14 (Saturday only) label contains 'Sat'."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot14 = next(t for t in timers if t["slot"] == 14)
        assert "Sat" in slot14["label"]

    def test_bdd_raw_field_preserved(self):
        """Raw bdd string is returned in output (needed for auditability)."""
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        slot11 = next(t for t in timers if t["slot"] == 11)
        assert slot11["bdd"] == "01111101"

    def test_empty_boost_times_returns_empty_list(self):
        """Response with empty boost_times returns []."""
        c = make_connector()
        with patch.object(c, "_get", return_value={"boost_times": []}):
            timers = c.get_schedule()
        assert timers == []

    def test_api_error_returns_none(self):
        """Network / HTTP errors are caught and return None (graceful degradation after E-23 retry).

        None signals "the call failed" as distinct from [] which means
        "the call succeeded but no timers are scheduled".
        """
        c = make_connector()
        with patch.object(c, "_get", side_effect=Exception("connection timeout")):
            timers = c.get_schedule()
        assert timers is None

    def test_wrong_response_key_returns_empty(self):
        """Response using 'boost' key instead of 'boost_times' returns []."""
        c = make_connector()
        with patch.object(c, "_get", return_value={"boost": [{"slt": 11}]}):
            timers = c.get_schedule()
        assert timers == []

    def test_all_required_keys_present(self):
        """Each timer dict contains all expected keys."""
        required = {"slot", "start_hour", "start_min", "duration_h", "duration_m",
                    "duration_min", "days", "bdd", "label"}
        c = make_connector()
        with patch.object(c, "_get", return_value=self._MOCK_BOOST_TIMES):
            timers = c.get_schedule()
        for t in timers:
            missing = required - set(t.keys())
            assert not missing, f"Slot {t.get('slot')} missing keys: {missing}"


# ---------------------------------------------------------------------------
# 3. get_history_day parsing
# ---------------------------------------------------------------------------

class TestGetHistoryDayParsing:
    """Tests for get_history_day() 1441-entry response parsing.

    Confirmed live structure (2026-03-15):
        - 1 global header (index 0, no 'min' key)
        - 24 × 60 minute-level entries (indices 1–1440)
        - hour = (idx - 1) // 60  for idx ≥ 1
        - imp / hsk are INSTANTANEOUS centi-Watts (÷100 = W, ÷100000 = kW)
    """

    @staticmethod
    def _make_mock_response(
        imp_cw: int = 10000,
        hsk_cw: int = 5000,
        serial: str = "21509692",
    ) -> dict:
        """Build a minimal 1441-entry response with uniform imp/hsk.

        imp_cw=10000  → 100 W instantaneous → imported_kwh ≈ 0.1 per hour
        hsk_cw=5000   →  50 W instantaneous → diverted_kwh ≈ 0.05 per hour
        """
        entries = [{"yr": 2026, "mon": 3, "dom": 14}]  # index 0: global header
        for _hour in range(24):
            entries.append({"imp": imp_cw, "hsk": hsk_cw})          # hour-start (no 'min')
            for minute in range(1, 60):
                entries.append({"min": minute, "imp": imp_cw, "hsk": hsk_cw})
        assert len(entries) == 1441
        return {f"U{serial}": entries}

    def test_returns_24_hourly_records(self):
        """A complete 1441-entry response produces exactly 24 hourly records."""
        c = make_connector()
        mock_data = self._make_mock_response()
        with patch.object(c, "_get", return_value=mock_data):
            hours = c.get_history_day(date(2026, 3, 14))
        assert len(hours) == 24

    def test_all_hours_0_to_23(self):
        """Hours 0–23 are all present and in ascending order."""
        c = make_connector()
        mock_data = self._make_mock_response()
        with patch.object(c, "_get", return_value=mock_data):
            hours = c.get_history_day(date(2026, 3, 14))
        assert [h["hour"] for h in hours] == list(range(24))

    def test_centiwatt_to_kwh_conversion(self):
        """imp=10000 cW → avg≈0.1 kW → imported_kwh≈0.1; hsk=5000 → diverted≈0.05.

        Hour 0 is slightly lower (~0.0984) because the global header at array index 0
        contributes to hour-0's average but has no imp/hsk fields (real API behaviour).
        Hours 1–23 each have exactly 60 uniform entries → exact conversion.
        Tolerance is 2% (abs=2e-3) to cover the hour-0 global-header dilution.
        """
        c = make_connector()
        mock_data = self._make_mock_response(imp_cw=10000, hsk_cw=5000)
        with patch.object(c, "_get", return_value=mock_data):
            hours = c.get_history_day(date(2026, 3, 14))
        for h in hours:
            assert abs(h["imported_kwh"] - 0.1) < 2e-3, (
                f"Hour {h['hour']}: expected imported_kwh≈0.1, got {h['imported_kwh']}"
            )
            assert abs(h["diverted_kwh"] - 0.05) < 1e-3, (
                f"Hour {h['hour']}: expected diverted_kwh≈0.05, got {h['diverted_kwh']}"
            )

    def test_zero_fields_give_zero_kwh(self):
        """Entries with imp=0, hsk=0 → both kWh values are 0."""
        c = make_connector()
        mock_data = self._make_mock_response(imp_cw=0, hsk_cw=0)
        with patch.object(c, "_get", return_value=mock_data):
            hours = c.get_history_day(date(2026, 3, 14))
        for h in hours:
            assert h["imported_kwh"] == pytest.approx(0.0, abs=1e-6)
            assert h["diverted_kwh"] == pytest.approx(0.0, abs=1e-6)

    def test_status_minus14_returns_empty(self):
        """Status -14 from firmware → empty list (history API unsupported)."""
        c = make_connector()
        with patch.object(c, "_get", return_value={"status": -14}):
            hours = c.get_history_day(date(2026, 3, 14))
        assert hours == []

    def test_missing_u_key_returns_empty(self):
        """Response without a U-key returns empty list (graceful degradation)."""
        c = make_connector()
        with patch.object(c, "_get", return_value={"some_other_key": []}):
            hours = c.get_history_day(date(2026, 3, 14))
        assert hours == []

    def test_api_error_returns_empty(self):
        """Network errors are caught and return empty list."""
        c = make_connector()
        with patch.object(c, "_get", side_effect=Exception("timeout")):
            hours = c.get_history_day(date(2026, 3, 14))
        assert hours == []

    def test_default_date_uses_today_in_url(self):
        """Calling with no date defaults to today (correct URL format)."""
        c = make_connector()
        captured_path: list[str] = []

        def capture_get(path: str) -> dict:
            captured_path.append(path)
            return {}  # triggers empty-list path

        with patch.object(c, "_get", side_effect=capture_get):
            c.get_history_day()

        today = date.today()
        expected_fragment = f"-{today.year}-{today.month:02d}-{today.day:02d}"
        assert captured_path, "No API call was made"
        assert expected_fragment in captured_path[0], (
            f"Expected date fragment {expected_fragment!r} in URL, got {captured_path[0]!r}"
        )

    def test_output_keys_present(self):
        """Each hourly record contains 'hour', 'diverted_kwh', 'imported_kwh'."""
        c = make_connector()
        mock_data = self._make_mock_response()
        with patch.object(c, "_get", return_value=mock_data):
            hours = c.get_history_day(date(2026, 3, 14))
        for h in hours:
            assert "hour" in h
            assert "diverted_kwh" in h
            assert "imported_kwh" in h


# ---------------------------------------------------------------------------
# 4. get_status parsing
# ---------------------------------------------------------------------------

class TestGetStatusParsing:
    """Tests for get_status() response parsing.

    The API returns either:
      - List format:  [{"eddi": [...]}, {"harvi": [...]}, ...]   (observed live)
      - Dict format:  {"eddi": [...], "harvi": [...]}            (older firmware)
    Both formats must be handled.
    """

    _BASE_EDDI = {
        "sno": 21509692,
        "sta": 1,       # 1 = paused
        "div": 0,
        "grd": 191,
        "che": 1.234,   # today_kwh
        "frq": 4994,
        "v1":  2391,
    }

    def test_list_format_response(self):
        """List-format response [{'eddi': [...]}] is parsed correctly."""
        c = make_connector()
        with patch.object(c, "_get", return_value=[{"eddi": [self._BASE_EDDI]}]):
            status = c.get_status()
        assert status["eddi_serial"] == "21509692"
        assert status["mode"] == "paused"
        assert status["today_kwh"] == pytest.approx(1.234)
        assert status["grid_w"] == 191

    def test_dict_format_response(self):
        """Dict-format response {'eddi': [...]} is also accepted."""
        c = make_connector()
        with patch.object(c, "_get", return_value={"eddi": [self._BASE_EDDI]}):
            status = c.get_status()
        assert status["eddi_serial"] == "21509692"

    def test_empty_eddi_list_raises(self):
        """Empty eddi list raises RuntimeError with helpful message."""
        c = make_connector()
        with patch.object(c, "_get", return_value=[{"eddi": []}]):
            with pytest.raises(RuntimeError, match="No eddi devices"):
                c.get_status()

    def test_status_code_paused(self):
        """sta=1 → mode='paused'."""
        c = make_connector()
        entry = {**self._BASE_EDDI, "sta": 1}
        with patch.object(c, "_get", return_value=[{"eddi": [entry]}]):
            assert c.get_status()["mode"] == "paused"

    def test_status_code_diverting_solar(self):
        """sta=3 → mode='diverting_solar'."""
        c = make_connector()
        entry = {**self._BASE_EDDI, "sta": 3}
        with patch.object(c, "_get", return_value=[{"eddi": [entry]}]):
            assert c.get_status()["mode"] == "diverting_solar"

    def test_status_code_boost(self):
        """sta=5 → mode='boost'."""
        c = make_connector()
        entry = {**self._BASE_EDDI, "sta": 5}
        with patch.object(c, "_get", return_value=[{"eddi": [entry]}]):
            assert c.get_status()["mode"] == "boost"

    def test_unknown_status_code(self):
        """Unknown sta returns 'unknown(N)' string."""
        c = make_connector()
        entry = {**self._BASE_EDDI, "sta": 99}
        with patch.object(c, "_get", return_value=[{"eddi": [entry]}]):
            mode = c.get_status()["mode"]
        assert "unknown" in mode.lower()

    def test_today_kwh_rounded(self):
        """today_kwh from che field is returned rounded to 3 decimal places."""
        c = make_connector()
        entry = {**self._BASE_EDDI, "che": 2.56789}
        with patch.object(c, "_get", return_value=[{"eddi": [entry]}]):
            status = c.get_status()
        assert status["today_kwh"] == pytest.approx(2.568, abs=0.001)

    def test_all_expected_keys_present(self):
        """get_status() output contains all expected keys."""
        expected = {
            "eddi_serial", "mode", "diverted_w", "grid_w", "today_kwh",
            "tank_temp_c", "solar_w", "solar_lower_w",
        }
        c = make_connector()
        with patch.object(c, "_get", return_value=[{"eddi": [self._BASE_EDDI]}]):
            status = c.get_status()
        missing = expected - set(status.keys())
        assert not missing, f"Missing keys in get_status() output: {missing}"


# ---------------------------------------------------------------------------
# 5. MockDeviceConnector
# ---------------------------------------------------------------------------

class TestMockDeviceConnector:
    """Tests for MockDeviceConnector (used in CI and demos — no real device)."""

    def test_send_command_returns_true(self):
        """send_command always returns True."""
        dev = MockDeviceConnector()
        assert dev.send_command("HEAT_NOW", "B001") is True

    def test_command_logged(self):
        """Command is recorded in command_log."""
        dev = MockDeviceConnector()
        dev.send_command("DEFER_HEATING", "home")
        assert len(dev.command_log) == 1
        assert dev.command_log[0]["action"] == "DEFER_HEATING"
        assert dev.command_log[0]["building_id"] == "home"

    def test_timestamp_in_log(self):
        """Each log entry has a timestamp string."""
        dev = MockDeviceConnector()
        dev.send_command("HEAT_NOW", "B001")
        assert "timestamp" in dev.command_log[0]
        assert dev.command_log[0]["timestamp"]  # non-empty

    def test_multiple_commands_accumulated(self):
        """Multiple commands all appear in command_log."""
        dev = MockDeviceConnector()
        dev.send_command("HEAT_NOW",          "B001")
        dev.send_command("DEFER_HEATING",     "B001")
        dev.send_command("ALERT_HIGH_DEMAND", "B002")
        assert len(dev.command_log) == 3
        actions = [e["action"] for e in dev.command_log]
        assert "HEAT_NOW" in actions
        assert "DEFER_HEATING" in actions

    def test_default_building_id(self):
        """send_command with no building_id uses 'unknown' default."""
        dev = MockDeviceConnector()
        dev.send_command("HEAT_NOW")
        assert dev.command_log[0]["building_id"] == "unknown"


# ---------------------------------------------------------------------------
# 6. MockPriceConnector
# ---------------------------------------------------------------------------

class TestMockPriceConnector:
    """Smoke tests for MockPriceConnector (realistic Irish day-ahead curve)."""

    def test_returns_24_prices(self):
        """get_day_ahead_prices() returns exactly 24 values."""
        pc = MockPriceConnector()
        prices = pc.get_day_ahead_prices()
        assert len(prices) == 24

    def test_prices_are_floats(self):
        """All prices are floats."""
        for p in MockPriceConnector().get_day_ahead_prices():
            assert isinstance(p, float)

    def test_prices_in_plausible_range(self):
        """All prices are in a plausible range for Irish electricity (€0.10–€0.50/kWh)."""
        for p in MockPriceConnector().get_day_ahead_prices():
            assert 0.10 <= p <= 0.50, f"Price {p:.3f} EUR/kWh outside expected range"

    def test_night_rate_cheaper_than_peak(self):
        """Night-time prices (00:00–07:00) are lower than evening peak (17:00–19:00)."""
        prices = MockPriceConnector().get_day_ahead_prices()
        avg_night = sum(prices[0:8]) / 8
        avg_peak  = sum(prices[17:20]) / 3
        assert avg_night < avg_peak, (
            f"Night avg {avg_night:.3f} should be < peak avg {avg_peak:.3f}"
        )

    def test_same_result_repeated_calls(self):
        """Repeated calls return identical lists (deterministic mock)."""
        pc = MockPriceConnector()
        assert pc.get_day_ahead_prices() == pc.get_day_ahead_prices()
