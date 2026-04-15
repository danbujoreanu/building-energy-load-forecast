# Live Connector Upgrade Path

**Current state:** `dry_run=True` default (ADR-005). All three production connectors are either mock or partially stubbed.
**Purpose:** This document is the implementation roadmap to move from demo-safe to production-live.

---

## Current State by Connector

| Connector | Status | Gap |
|-----------|--------|-----|
| `CSVConnector` | Live (historical data) | Needs real-time streaming path for live inference |
| `OpenMeteoConnector` | Stubbed (class exists, not wired in live_inference.py) | API key + wiring |
| `SEMOConnector` | Not implemented | Full build required |
| `MockDeviceConnector` | Live (mock only) | Replace with myenergi API (home trial) or Modbus (commercial) |

---

## Upgrade Sequence (ordered by value / complexity)

### Phase 1: OpenMeteo (quick win — 1–2 hours)

**Status:** OpenMeteo is free, no API key required for standard resolution.

**What's needed:**
1. Remove `# TODO: wire CSVConnector for historical data` in `deployment/app.py /control` endpoint
2. Wire `OpenMeteoConnector` in `deployment/live_inference.py` — replace `MOCK_SOLAR_24H` with live call
3. Add location config to `config/config.yaml`: `lat: 59.9139` (Oslo) / `lon: 10.7522`
4. Test: `python deployment/live_inference.py --live` — should print real solar forecast

**Code change (live_inference.py):**
```python
# Replace:
solar_forecast = MOCK_SOLAR_24H

# With:
from energy_forecast.data.connectors import OpenMeteoConnector
connector = OpenMeteoConnector(lat=cfg["location"]["lat"], lon=cfg["location"]["lon"])
solar_forecast = connector.get_solar_forecast_24h()
```

**Risk:** None — OpenMeteo is free, no auth, deterministic format. Zero production risk.

---

### Phase 2: myenergi Eddi (home trial → production path)

**Status:** Home trial live — Dan's Eddi is the first production device.

**What's needed:**
1. Replace `MockDeviceConnector` with `MyenergiConnector` in `deployment/live_inference.py`
2. Credentials: myenergi API key — store in environment variable `MYENERGI_API_KEY` (never in config.yaml)
3. Hub serial: already rotated and redacted from public docs (Apr 8 security remediation)

**Implementation:**
```python
# In deployment/connectors.py — add:
class MyenergiConnector:
    """Live connector for myenergi Eddi hot water diverter."""
    BASE_URL = "https://s18.myenergi.net"
    
    def __init__(self, hub_serial: str, api_key: str):
        self.hub_serial = hub_serial
        self.api_key = api_key
        self.command_log = []  # maintain same interface as MockDeviceConnector
    
    def send_command(self, device: str, action: str, **kwargs) -> dict:
        # myenergi zappi/eddi API: POST to /cgi-eddi-mode-{mode}
        # See: https://github.com/twonk/MyEnergi-App-Api
        ...
```

**Credential injection (never hardcode):**
```bash
export MYENERGI_HUB_SERIAL=$(cat ~/.secrets/myenergi_hub)
export MYENERGI_API_KEY=$(cat ~/.secrets/myenergi_key)
```

**Risk:** LOW — home trial only, Dan's own hardware. No safety-critical consequence of failure.

---

### Phase 3: SEMOConnector (electricity price feed)

**Status:** Not implemented. Required for real demand-response value (cheapest hours scheduling).

**Data source options:**
| Source | Coverage | API | Cost |
|--------|----------|-----|------|
| SEMO (Single Electricity Market Operator) | Ireland + NI | REST — [smartgriddashboard.com](https://www.smartgriddashboard.com/) | Free |
| ENTSO-E Transparency Platform | All of Europe | REST + API key | Free (registration) |
| Nord Pool | Nordics (original thesis data) | REST | Free tier available |

**Recommended:** Start with SEMO (Irish market relevance for Sparc Energy commercial pitch) + ENTSO-E as fallback.

**Implementation sketch:**
```python
class SEMOConnector:
    """Day-ahead electricity price connector — SEMO/smartgriddashboard."""
    BASE_URL = "https://www.smartgriddashboard.com/DashboardService.svc"
    
    def get_day_ahead_prices(self, date: str) -> list[float]:
        """Returns 24h price vector in €/MWh."""
        ...
```

**Risk:** MED — SEMO API is undocumented/unofficial (smartgriddashboard scraping). Use ENTSO-E as backup if SEMO breaks.

---

### Phase 4: Remove HTTPException(501) Guard

**Current code in `deployment/app.py`:**
```python
if not request.dry_run:
    raise HTTPException(status_code=501, detail="Live mode not yet implemented")
```

**When to remove:** Only after Phase 1 + Phase 2 are both live and tested. Do not remove early — the 501 is a safety net, not technical debt.

**Replacement:** Wire live connectors through the request context. See ADR-005 for full rationale.

---

## Environment Variables (production checklist)

```bash
# Required for live mode
MYENERGI_HUB_SERIAL=<from ~/.secrets/>
MYENERGI_API_KEY=<from ~/.secrets/>
ENTSO_E_API_KEY=<register at transparency.entsoe.eu>

# Optional — defaults to mock if absent
OPENMETEO_LAT=59.9139
OPENMETEO_LON=10.7522
```

Store in `~/.secrets/` on Dev machine. For production deployment: use environment variable injection (Render, Railway, or equivalent PaaS). Never commit to git.

---

## Testing Live Mode

```bash
# Phase 1 test (OpenMeteo only):
python deployment/live_inference.py --live

# Full live test (all connectors):
DRY_RUN=false python -m pytest tests/test_live_inference.py -v

# FastAPI live endpoint:
curl -X POST http://localhost:8000/control \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "target_date": "2026-04-15"}'
```

---

## Related Files
- `deployment/app.py` — FastAPI app with dry_run guard
- `deployment/live_inference.py` — Morning brief script
- `deployment/connectors.py` — Connector implementations
- `docs/adr/ADR-005-mock-first-design.md` — Rationale for dry_run=True default
- `config/config.yaml` — Location config (add lat/lon for OpenMeteo)
