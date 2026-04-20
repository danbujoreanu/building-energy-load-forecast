# Docker Beginner Guide — Sparc Energy Local Stack

**For:** Someone who has Docker Desktop installed but hasn't used it much.  
**Goal:** Understand what's running, start it, stop it, fix it.

---

## What Docker Actually Does (2-minute version)

Think of Docker as a way to run **mini-computers inside your Mac** — each one is a "container".  
Instead of installing PostgreSQL, Redis, Grafana etc. directly on your Mac (messy, version conflicts), Docker runs each one in its own isolated box.

```
Your Mac
│
├── Docker Desktop (the manager)
│
├── Container: sparc-api        ← Your FastAPI Python app, port 8000
├── Container: sparc-db         ← PostgreSQL database, port 5432
├── Container: sparc-redis      ← Redis cache, port 6379
├── Container: sparc-grafana    ← Grafana dashboard, port 3001
└── Container: sparc-caddy      ← HTTPS reverse proxy, ports 80/443
```

`docker compose` is the command that reads `docker-compose.yml` and starts all of them together, wired up so they can talk to each other.

**Volumes** = the containers' persistent hard drives. Your data survives even if containers stop.  
**Networks** = private Wi-Fi between containers. `sparc-api` can reach `sparc-db` as `db:5432`.

---

## Before First Run — Set Passwords in `.env`

The stack needs two passwords you must set first. Open `.env` in any text editor:

```bash
# Open .env in TextEdit (or VS Code):
open -a TextEdit ~/building-energy-load-forecast/.env
```

Add these two lines (pick any passwords you like):

```
DB_PASSWORD=sparc_local_2026
GRAFANA_PASSWORD=grafana_local_2026
```

Your `.env` should now have at minimum:
```
MYENERGI_SERIAL=21509692
MYENERGI_API_KEY=...
DB_PASSWORD=sparc_local_2026
GRAFANA_PASSWORD=grafana_local_2026
```

> These passwords are only used locally — they never leave your Mac.

---

## First Run — Start Everything

### Step 1: Open Terminal, go to the project

```bash
cd ~/building-energy-load-forecast
```

### Step 2: Start the stack

```bash
docker compose up -d
```

What happens:
1. Docker downloads the images (PostgreSQL, Redis, Grafana) — **first time only, ~2–5 minutes depending on internet**
2. Builds the FastAPI image from your `Dockerfile` — **~2 minutes first time**
3. Starts all 5 containers
4. TimescaleDB runs `infra/db/init.sql` to create all tables automatically

The `-d` flag means "detached" — runs in the background so your terminal stays free.

### Step 3: Verify everything is running

```bash
docker compose ps
```

Expected output — all should say `running`:
```
NAME            STATUS
sparc-api       running (healthy)
sparc-db        running (healthy)
sparc-redis     running (healthy)
sparc-grafana   running
sparc-caddy     running
```

If anything shows `starting` — wait 30 more seconds and run `docker compose ps` again.

### Step 4: Test the API

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","model":"active","city":"ireland",...}`

### Step 5: Open Grafana

```bash
open http://localhost:3001
```

Login: `admin` / whatever you set as `GRAFANA_PASSWORD` in `.env`

---

## Daily Use

### Start the stack (if it's not running)
```bash
cd ~/building-energy-load-forecast
docker compose up -d
```

### Stop the stack (preserves all data)
```bash
docker compose down
```

### Restart a single service (e.g. after code change)
```bash
docker compose restart api
```

### Check if things are running
```bash
docker compose ps
```

### See what the API is logging (live)
```bash
docker compose logs -f api
# Press Ctrl+C to stop watching
```

### See all logs from all services
```bash
docker compose logs --tail=50
```

---

## Docker Desktop UI

You can also use the Docker Desktop app instead of the terminal:

1. Click the Docker icon in your Mac menu bar
2. Open Dashboard
3. Click "Containers" — you'll see all Sparc containers
4. Click a container to see its logs
5. The ▶ / ■ buttons start/stop individual containers

Useful for: checking logs visually, seeing which containers are healthy.

---

## Common Problems + Fixes

### "Port already in use"
Something else on your Mac is using port 8000, 5432, or 3001.

```bash
# Find what's using port 8000:
lsof -i :8000

# Kill it (replace PID with the number shown):
kill -9 <PID>
```

### API shows "unhealthy" or keeps restarting
Usually means DB_PASSWORD is wrong or the database isn't ready yet.

```bash
docker compose logs api --tail=20  # See the error
docker compose logs db --tail=20   # Check if DB started OK
```

### "No such service" or "unknown flag"
You're running the command from the wrong directory.

```bash
cd ~/building-energy-load-forecast  # Always run from here
```

### Start fresh (wipes ALL data — use carefully)
```bash
docker compose down -v  # -v removes volumes (data)
docker compose up -d    # Start again from scratch
```

### Rebuild after code change
```bash
docker compose build api   # Rebuild only the FastAPI image
docker compose up -d api   # Restart with new image
```

---

## Dev Mode (faster iteration — no rebuild needed)

In dev mode, FastAPI reloads automatically when you change Python files:

```bash
# Dev mode — code changes take effect instantly
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Or use the shorthand alias (add to ~/.zshrc):
alias dcd="docker compose -f ~/building-energy-load-forecast/docker-compose.yml -f ~/building-energy-load-forecast/docker-compose.dev.yml"
dcd up -d
dcd logs -f api
```

In dev mode, Caddy is disabled — access services directly:
- FastAPI: http://localhost:8000
- Grafana: http://localhost:3001

---

## Services Summary

| Service | Port | What it does | You interact with it? |
|---------|------|-------------|----------------------|
| `sparc-api` | 8000 | Your FastAPI Python app — forecasting, control, RAG queries | Yes — `curl localhost:8000` |
| `sparc-db` | 5432 | PostgreSQL/TimescaleDB — stores predictions, meter readings | Indirectly (via API) |
| `sparc-redis` | 6379 | Cache — stores forecast results for 23h to avoid re-running | Never directly |
| `sparc-grafana` | 3001 | Dashboard — visualise everything | Yes — browser at localhost:3001 |
| `sparc-caddy` | 80/443 | HTTPS proxy — makes services available at `*.sparc.localhost` | Rarely |

**ChromaDB (RAG)** does NOT run in Docker — it's a local folder at `data/chromadb/`. The Python scripts read/write it directly.

---

## Individual Service Guides

| Service | Guide |
|---------|-------|
| Grafana dashboard | `docs/infra/services/GRAFANA.md` |
| n8n workflow automation | `docs/infra/services/N8N.md` |
| PostgreSQL / TimescaleDB | `docs/infra/services/POSTGRES_TIMESCALE.md` |
| Redis cache | `docs/infra/services/REDIS.md` |
| ChromaDB / RAG | `docs/features/intel-rag/README.md` |
| FastAPI deployment | `docs/HOW_TO_RUN.md` |
