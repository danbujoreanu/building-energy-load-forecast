# Feature: Demand-Response Control Engine

**Status:** ✅ Production (dry-run mode)
**Linear:** DAN-32, DAN-33, DAN-56, DAN-57
**Owner:** Dan Bujoreanu

---

## What it does

Takes a P10/P50/P90 load forecast + solar + grid prices → outputs per-hour DEFER/IDEAL/NORMAL decisions → dispatches to Eddi diverter.

## Endpoint

```bash
POST /control
{
  "building_id": "home_maynooth",
  "city": "drammen",
  "target_hours": [6,7,8,...,22],
  "dry_run": true
}
```

## Decision logic

| Condition | Action | Rationale |
|-----------|--------|-----------|
| Peak hour (17-19) + load > 5 kWh | DEFER_HEATING | Save ~€0.10/hour at BGE peak rate |
| Night rate + load < 3 kWh | IDEAL | Run high-consumption tasks now |
| Solar surplus > load | SOLAR_USE | Maximise self-consumption |
| Default | NORMAL | No action needed |

## Key files

- `src/energy_forecast/control/actions.py` — EnvironmentState, ForecastBundle, ActionDecision
- `src/energy_forecast/control/controller.py` — ControlEngine.decide(), ControlEngine.explain()
- `deployment/connectors.py` — EddiConnector, MockPriceConnector, OpenMeteoConnector
- `deployment/mock_data.py` — MOCK_SOLAR_24H (shared curve)
- `deployment/live_inference.py` — Phase 6 morning brief CLI

## Current limitations

- `dry_run=false` raises 501 until SEMOConnector is implemented (DAN-57)
- Eddi send_command() is a stub — not yet dispatching (DAN-56)
- Live DataConnector not wired to /control endpoint (uses mock P50 profile)

## BGE tariff rates (src/energy_forecast/tariff.py)

- Day: 40.34c/kWh
- Night (23:00–08:00): 29.65c/kWh
- Peak (Mon-Fri 17:00–19:00): 49.28c/kWh
- Free Sat (09:00–17:00): ~0c/kWh (Bord Gáis Free Time Saturday plan)
