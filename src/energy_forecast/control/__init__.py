"""
energy_forecast.control
=======================
Probabilistic demand-response control layer.

Translates P10/P50/P90 load forecasts + external signals (solar irradiance,
electricity price) into actionable setpoints for devices such as the
myenergi eddi hot-water diverter or smart HVAC controllers.

Public API
----------
    from energy_forecast.control.actions import (
        ActionType, ForecastBundle, EnvironmentState, ControlAction
    )
    from energy_forecast.control.controller import ControlEngine
"""
