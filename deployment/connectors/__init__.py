"""
deployment.connectors
======================
Abstract connector interfaces and concrete implementations for the
real-world data-ingestion and device-control layers of the
Building Energy Load Forecast system.

Three connector families
------------------------
DataConnector   — fetch recent historical load + weather time-series
PriceConnector  — fetch day-ahead electricity prices (EUR/kWh per hour)
DeviceConnector — send control commands to managed devices (eddi, HVAC)

Implementations
---------------
DataConnector
  CSVConnector         — reads from committed parquet/CSV files (test/demo)
  OpenMeteoConnector   — live weather + solar forecast (Open-Meteo free API)
  EcowittConnector     — Ecowitt cloud API [STUB — pending hardware]
  MQTTConnector        — MQTT topic subscriber [STUB — pending broker]

PriceConnector
  MockPriceConnector   — realistic Irish day-ahead price curve (demo mode)
  SEMOConnector        — SEMO day-ahead prices [STUB — pending scraper]

DeviceConnector
  MockDeviceConnector  — logs command to stdout (demo / CI mode)
  MyEnergiConnector    — myenergi eddi API [STUB — pending API key]
"""

from .base import DataConnector, DeviceConnector, PriceConnector, _retry_http
from .csv_ingest import CSVConnector
from .hardware import MockDeviceConnector, MyEnergiConnector
from .markets import MockPriceConnector, SEMOConnector
from .weather import EcowittConnector, OpenMeteoConnector, _weather_cache

__all__ = [
    # helpers
    "_retry_http",
    "_weather_cache",
    # ABCs
    "DataConnector",
    "PriceConnector",
    "DeviceConnector",
    # data connectors
    "CSVConnector",
    "OpenMeteoConnector",
    "EcowittConnector",
    # price connectors
    "MockPriceConnector",
    "SEMOConnector",
    # device connectors
    "MockDeviceConnector",
    "MyEnergiConnector",
]
