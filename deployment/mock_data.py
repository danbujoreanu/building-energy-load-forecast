"""Shared mock data for dry-run and demo mode.

Import from here rather than duplicating inline in app.py and live_inference.py.
"""

MOCK_SOLAR_24H: list[float] = [
    0, 0, 0, 0, 0, 0,      # 00–05: night
    20, 80, 180, 300, 400,  # 06–10: sunrise ramp
    480, 520, 500, 450,     # 11–14: midday
    380, 280, 150, 60,      # 15–18: afternoon decline
    10, 0, 0, 0, 0, 0,      # 19–23: dusk/night
]
