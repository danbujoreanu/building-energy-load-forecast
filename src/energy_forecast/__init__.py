"""
energy_forecast
===============
24-hour ahead electricity load forecasting for Norwegian public buildings.

Datasets
--------
- Drammen: 45 COFACTOR buildings (schools & kindergartens)
- Oslo: 48 SINTEF buildings (future work)

Pipeline
--------
data.loader → data.preprocessing → data.splits
    → features.temporal → features.selection
    → models.* → evaluation.metrics → visualization.plots
"""

__version__ = "0.1.0"
__author__ = "Dan Alexandru Bujoreanu"
