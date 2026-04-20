# Redis — Prediction Cache

**What it is:** Redis is a fast in-memory key-value store. Think of it as a "memory" that stores recent answers so the API doesn't recalculate them.  
**Port:** 6379  
**Container:** `sparc-redis`  
**You almost never interact with it directly.**

---

## What It Does for Sparc Energy

When the FastAPI `/predict` endpoint is called:

```
Request comes in for "ireland household, 2026-04-21"
    ↓
Check Redis: "Do I already have this forecast?"
    ↓
YES → Return cached result instantly (~1ms)   ← Redis hit
    ↓
NO  → Run LightGBM model (~50ms) → Store in Redis with 23h TTL → Return result   ← Redis miss
```

The TTL (Time To Live) is 23 hours — matching the forecast horizon. After 23 hours, the cache expires and the next request rebuilds the forecast with fresh weather data.

---

## You Don't Need to Configure It

Redis starts automatically with `docker compose up -d`.  
The FastAPI app connects via `REDIS_URL=redis://redis:6379/0` (set in docker-compose.yml).

---

## Verify Redis is Working

```bash
# Check it's running:
docker compose ps redis

# Ping it:
docker exec sparc-redis redis-cli ping
# Expected: PONG

# See what's cached:
docker exec sparc-redis redis-cli KEYS "*"
# After a prediction: shows keys like "predict:ireland_main:2026-04-21"

# See cache stats:
docker exec sparc-redis redis-cli INFO stats | grep -E "hits|misses"
```

---

## Configuration (already set in docker-compose.yml)

| Setting | Value | Why |
|---------|-------|-----|
| Max memory | 256 MB | Prevents Redis consuming unbounded RAM |
| Eviction policy | `allkeys-lru` | When full, evict the least-recently-used key |
| Persistence | `appendonly yes` + snapshots | Data survives container restart |

For a single-household setup, Redis uses less than 1 MB. This is not a concern.

---

## Troubleshooting

### API logs show "Redis connection refused"
```bash
docker compose ps redis  # Should be "running (healthy)"
docker compose restart redis
docker compose restart api  # Reconnects after Redis comes back
```

### Clear all cached predictions (forces re-run)
```bash
docker exec sparc-redis redis-cli FLUSHDB
```
