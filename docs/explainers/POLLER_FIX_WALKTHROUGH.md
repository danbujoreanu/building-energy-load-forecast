# Sparc Energy & Greenhouse Poller Fix

I have applied the necessary fixes to resolve the missing Energy data, documented the changes, and investigated the historical data gap on the Greenhouse dashboard.

## 1. Energy Poller Fix (MyEnergi)
The root cause of the missing Energy data was that the `sparc-api` container on the NUC was running a 10-day-old version of `scheduler.py` that still used the `23:30` schedule. This caused the Open-Meteo archive API to reject the requests with a `400 Bad Request`.

**Actions taken:**
1. I synced the updated `deployment/scheduler.py` (which correctly sets the cron job to `00:15`) from your Mac to the NUC.
2. I initiated a rebuild of the `sparc-api` container on the NUC (`docker compose up -d --build api`) so it picks up the new code.
3. Once the build finishes (it is currently installing dependencies in the background), you can run the backfill script to recover the missing data for May 10th and May 11th. I have prepared the command for you below.
4. I updated `docs/explainers/MYENERGI_POLLER_EXPLAINED.md` with detailed notes on the `00:15` vs `23:30` scheduling constraint caused by the Open-Meteo archive API.

### Next Step (Data Recovery)
Once the `sparc-api` container finishes restarting in a few minutes, run this command on the NUC to backfill the missing MyEnergi and Open-Meteo data:
```bash
docker exec sparc-api python /app/scripts/myenergi_backfill.py --start-date 2026-05-10
```

---

## 2. Greenhouse Dashboard (30-Day View)
You asked if Open-Meteo being faulty could also be the cause of issues for the `greenhouse-v1` dashboard over the last 30 days (`from=now-30d&to=now`).

**The answer is no; Open-Meteo is not responsible for this.**

The reason the `greenhouse-v1` dashboard on the NUC looks empty over the last 30 days is because **the historical data was never successfully imported into the NUC's database.** 

If you recall the `NUC_MIGRATION_GUIDE.md`, the import commands you attempted relied on the `influxdb3 write` CLI tool. However, the NUC runs **InfluxDB 2.7** (because the NUC's Intel N3700 CPU doesn't support the AVX2 instructions required for InfluxDB 3). As a result, the NUC's database only contains a small handful of stray points prior to May 7th. 

The NUC dashboard is perfectly healthy and is actively recording *new* live data from the Ecowitt sensors right now, but it simply lacks the historical data because the import process failed due to the database version mismatch.
