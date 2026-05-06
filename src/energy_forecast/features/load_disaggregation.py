"""
energy_forecast.features.load_disaggregation
=============================================
Disaggregate highly-variable device loads (Eddi hot-water diverter) from total
grid import to produce a cleaner base_load_kwh for model training.

Why: The LightGBM model predicts total household consumption. When the Eddi is
running, it adds 1.4–3.0 kW of load that is solar/tariff-triggered rather than
behavioural. Training on base_load (import minus eddi) improves forecast
accuracy for the controllable part of demand.

Usage:
    from energy_forecast.features.load_disaggregation import LoadDisaggregator

    df = LoadDisaggregator.separate_eddi_load(df,
        total_load_col='import_kwh',  # from meter_readings
        eddi_load_col='eddi_kwh',     # from myenergi_readings join
    )
    # df now has 'base_load_kwh' column, clipped to >= 0
"""
from __future__ import annotations

import pandas as pd


class LoadDisaggregator:
    """Subtract Eddi diversion load from total ESB import to get base load."""

    @staticmethod
    def separate_eddi_load(
        df: pd.DataFrame,
        total_load_col: str = "import_kwh",
        eddi_load_col: str = "eddi_kwh",
    ) -> pd.DataFrame:
        """Return df with a new ``base_load_kwh`` column.

        Parameters
        ----------
        df:
            DataFrame with at least ``total_load_col`` and ``eddi_load_col``.
        total_load_col:
            Column name for total grid import kWh (from meter_readings).
        eddi_load_col:
            Column name for Eddi diversion kWh (from myenergi_readings).

        Returns
        -------
        DataFrame copy with added ``base_load_kwh`` column (>= 0).
        """
        if total_load_col not in df.columns or eddi_load_col not in df.columns:
            raise ValueError(
                f"Columns '{total_load_col}' and/or '{eddi_load_col}' not found in DataFrame. "
                f"Available: {list(df.columns)}"
            )
        df_out = df.copy()
        df_out["base_load_kwh"] = (
            df_out[total_load_col] - df_out[eddi_load_col].fillna(0.0)
        ).clip(lower=0.0)
        return df_out
