"""
energy_forecast.features.solar_baseline
========================================
Deterministic clear-sky solar PV production model with Open-Meteo cloud_cover
correction. Used to add ``clear_sky_kwh_predicted`` as a feature in temporal.py.

Model:
    clear-sky irradiance (latitude/DOY/solar-hour geometry)
    × cloud reduction factor (1 - cloud_cover% × cloud_opacity)
    × pv_peak_power_kw

If pv_peak_power_kw == 0 (no solar panels), returns zeros — safe to call always.

Usage:
    from energy_forecast.features.solar_baseline import SolarBaselineModel
    from deployment.connectors.weather import OpenMeteoConnector

    # Fetch cloud_cover alongside temperature
    connector = OpenMeteoConnector.for_city("dublin")
    model = SolarBaselineModel(pv_peak_power_kw=4.2)
    forecast = model.predict(hours_ahead=24, cloud_coverage=cloud_cover_list)
    # forecast is a list of 24 floats (kWh per hour)
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import List


class SolarBaselineModel:
    """Clear-sky PV model with cloud_cover correction from Open-Meteo.

    Parameters
    ----------
    pv_peak_power_kw:
        Installed PV peak power. Set 0 for households without solar.
    latitude, longitude:
        Property coordinates. Defaults to Dublin, Ireland.
    cloud_opacity:
        Fraction of clear-sky output lost per 100% cloud cover.
        0.75 = overcast sky reduces output by 75% (empirically reasonable for Ireland).
    """

    def __init__(
        self,
        pv_peak_power_kw: float = 0.0,
        latitude: float = 53.3,
        longitude: float = -6.3,
        cloud_opacity: float = 0.75,
    ) -> None:
        self.pv_peak_power_kw = pv_peak_power_kw
        self.latitude = latitude
        self.longitude = longitude
        self.cloud_opacity = cloud_opacity

    def predict(
        self,
        hours_ahead: int,
        cloud_coverage: List[float],
        start_time: datetime | None = None,
    ) -> List[float]:
        """Predict hourly solar PV output (kWh) for next ``hours_ahead`` hours.

        Parameters
        ----------
        hours_ahead:
            Number of hourly slots to predict.
        cloud_coverage:
            Cloud cover % (0–100) list from Open-Meteo ``cloud_cover`` variable.
            Padded with last value if shorter than ``hours_ahead``.
        start_time:
            First forecast hour. Defaults to current hour truncated to :00.

        Returns
        -------
        List of floats (kWh), length == hours_ahead. All zeros if no PV.
        """
        if self.pv_peak_power_kw <= 0:
            return [0.0] * hours_ahead

        if start_time is None:
            start_time = datetime.now().replace(minute=0, second=0, microsecond=0)

        if not cloud_coverage:
            cloud_coverage = [50.0] * hours_ahead
        while len(cloud_coverage) < hours_ahead:
            cloud_coverage.append(cloud_coverage[-1])

        result = []
        for h in range(hours_ahead):
            dt = start_time + timedelta(hours=h)
            doy = dt.timetuple().tm_yday
            solar_hour = self._clock_to_solar_hour(dt)
            cs = self._clear_sky_factor(self.latitude, doy, solar_hour)
            cloud_pct = max(0.0, min(100.0, cloud_coverage[h]))
            cloud_factor = 1.0 - (cloud_pct / 100.0) * self.cloud_opacity
            result.append(round(max(0.0, self.pv_peak_power_kw * cs * cloud_factor), 3))

        return result

    def _clock_to_solar_hour(self, dt: datetime) -> float:
        tz_offset = dt.utcoffset()
        tz_hours = tz_offset.total_seconds() / 3600.0 if tz_offset else 1.0
        standard_meridian = tz_hours * 15.0
        longitude_correction = (self.longitude - standard_meridian) / 15.0
        return dt.hour + dt.minute / 60.0 + longitude_correction

    @staticmethod
    def _clear_sky_factor(latitude: float, day_of_year: int, solar_hour: float) -> float:
        """Return fraction of peak output at given lat/DOY/solar-hour (0–1)."""
        lat_rad = math.radians(latitude)
        dec = math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + day_of_year))))
        ha = math.radians((solar_hour - 12.0) * 15.0)
        sin_alt = (
            math.sin(lat_rad) * math.sin(dec)
            + math.cos(lat_rad) * math.cos(dec) * math.cos(ha)
        )
        altitude = math.asin(max(-1.0, min(1.0, sin_alt)))
        return max(0.0, math.sin(altitude)) if altitude > 0 else 0.0
