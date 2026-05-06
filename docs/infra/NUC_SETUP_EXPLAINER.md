# NUC Setup Explainer — Intel NUC5PGYHR as Sparc Energy Home Server
*Written 2026-05-06 — documents exactly what was done and why*

---

## Why a home server?

Until AWS Activate credits land, the NUC runs the full Sparc Docker stack locally:
- Live predictions on your own household (Eddi + ESB smart meter)
- Grafana dashboards accessible from Mac over local WiFi
- ML inference 24/7 without burning Mac battery or needing it open

Training stays on Mac (the N3700 CPU is too slow — 8 min to build a Docker image).
NUC role: **inference-only server**.

---

## What happened during setup (step-by-step)

### 1. OS install
- Flashed Ubuntu 26.04 LTS ISO to SD card using Balena Etcher on Mac
- NUC booted from front SD card slot (BIOS → boot order → SD card first, Secure Boot off)
- Ubuntu installed to 120GB SSD ("Use entire disk" — Windows wiped)
- OpenSSH server installed during setup (critical for headless access)

### 2. LVM extension
Ubuntu's LVM installer defaults to allocating ~50% of the physical disk. The NUC had
107GB of physical volume but only 54GB of logical volume usable.

Fixed with:
```bash
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```
Result: 107GB available (88GB free after OS + Docker images).

### 3. SSH key setup
Generated ed25519 key on Mac (`~/.ssh/id_ed25519`), pushed to NUC with `ssh-copy-id`.
From this point on: `ssh dan@192.168.68.119` with no password.

### 4. Static WiFi IP
The installer had already configured a static IP via netplan:
- Interface: `wlp2s0` (WiFi — ethernet `enp3s0` has no cable)
- IP: `192.168.68.119/24` (fixed, not DHCP)
- Gateway: `192.168.68.1` (Eero router)
- DNS: `1.1.1.1` (Cloudflare), `8.8.8.8` (Google)

Config lives at: `/etc/netplan/00-installer-config.yaml`

### 5. Docker install
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker dan
```
Official Docker install script — adds the Docker apt repo and installs Docker CE.

### 6. Source sync from Mac
The correct project structure on NUC (`~/sparc/`) requires:
```
~/sparc/
  docker-compose.yml   ← stack definition
  .env                 ← secrets (never in git)
  deployment/          ← FastAPI package
  src/                 ← energy_forecast Python package
  config/              ← config.yaml
  infra/               ← DB migrations, Grafana provisioning, Prometheus config
  outputs/models/      ← LightGBM/XGBoost/Ridge joblib files (~11MB total)
```

Synced with `rsync` from Mac project root, excluding:
- `*.keras`, `*RandomForest*`, `*.ckpt` (DL models — not used in inference)
- `data/`, `intel/`, `memory/`, `tests/`, `notebooks/` (not needed at runtime)
- `CAREER_CONTEXT.md` (private)

`.env` and model files copied separately via `scp`.

**Common mistake avoided:** rsync with `deployment/` (trailing slash) copies the
*contents* into the destination — not the directory itself. Always sync from project root.

### 7. Dockerfile fix
The Dockerfile was stale — it listed individual files that had since been refactored:
- `connectors.py` no longer exists → now `connectors/` package
- `schemas.py`, `routers/`, `db_repository.py`, `scheduler.py` were all missing

Fixed by replacing 7 individual `COPY` lines with one:
```dockerfile
COPY deployment/ ./deployment/
```

### 8. Monitoring stack added
Three new containers added to `docker-compose.yml` before first build:

**cAdvisor** (`gcr.io/cadvisor/cadvisor:v0.49.1`)
- Reads `/sys`, `/var/lib/docker`, `/var/run` (needs `privileged: true`)
- Exposes per-container CPU, RAM, network, disk metrics on port 8082
- Prometheus scrapes it every 15s

**node-exporter** (`prom/node-exporter:v1.8.1`)
- Reads `/proc` and `/sys` from host
- Exposes host-level NUC metrics: total CPU, RAM, disk, network on port 9100
- Prometheus scrapes it every 15s

**Prometheus** (`prom/prometheus:v2.52.0`)
- Scrapes cAdvisor + node-exporter + itself
- 30-day metric retention
- Exposes metrics API on port 9090 (Grafana queries this)

Config: `infra/prometheus/prometheus.yml`

**Grafana dashboard** auto-provisioned at startup:
`infra/grafana/provisioning/dashboards/nuc_overview.json`
→ accessible at `http://192.168.68.119:3001/d/nuc-overview`

### 9. Grafana 11 alert fix
The existing `sparc_alerts.yml` used `execErrState: NoData` which is invalid in
Grafana 11 (`NoData` is only valid for `noDataState`, not `execErrState`).

Fixed: `execErrState: NoData` → `execErrState: OK` across all 4 alert rules.

Also created missing `infra/grafana/provisioning/plugins/` directory (Grafana 11
logs a warning if it doesn't exist).

### 10. First `docker compose up -d`
All 9 containers started. Build time on N3700: 130 seconds (pip install).
Subsequent starts use cached layers — much faster.

### 11. DB migrations
`init.sql` runs automatically on first DB container start (mounted to
`/docker-entrypoint-initdb.d/`). Creates base schema: households, meter_readings,
predictions, recommendations, recommendation_outcomes, tariff_changes.

Migrations 002-004 run manually:
```bash
for f in 002 003 004; do
  docker compose exec -T db psql -U sparc -d sparc_energy < infra/db/migrations/${f}_*.sql
done
```

### 12. systemd auto-start
Service file at `/etc/systemd/system/sparc.service`.
`ExecStartPre` pulls latest images on each boot.
`Restart=on-failure` recovers if Docker crashes.

Enable once, runs forever:
```bash
sudo systemctl enable sparc
sudo systemctl start sparc
```

---

## RAM breakdown (actual measurements)

| Container | RAM | Why |
|-----------|-----|-----|
| sparc-n8n | ~280MB | Node.js runtime — heaviest. Can stop if not using automation. |
| sparc-api | ~128MB | FastAPI + LightGBM model kept in memory for fast inference |
| sparc-db | ~87MB | TimescaleDB buffer pool — grows slightly with query load |
| sparc-grafana | ~56MB | Dashboard server |
| sparc-prometheus | ~31MB | In-memory TSDB index + active series |
| sparc-cadvisor | ~33MB | Continuously reads /sys and Docker socket |
| sparc-caddy | ~14MB | Go binary — extremely efficient |
| sparc-node-exporter | ~8MB | Go binary |
| sparc-redis | ~6MB | Mostly empty until predictions cached |
| **Total** | **~643MB** | Of 6.4GB — 90% free |

If RAM pressure ever appears: `docker compose stop n8n` frees ~280MB immediately.
Core ML pipeline (api + db + redis) uses only ~220MB.

---

## Disk breakdown

| Item | Size |
|------|------|
| Ubuntu 26.04 base | ~3GB |
| Docker images (9 containers) | ~6GB |
| LightGBM + XGBoost + Ridge models | ~11MB |
| PostgreSQL data (fresh) | ~50MB |
| Prometheus data (30d) | grows ~10MB/day |
| **Total used** | ~15GB |
| **Free** | **~88GB** |

---

## Day-to-day commands from Mac

```bash
# SSH in
ssh dan@192.168.68.119

# Check all containers
ssh dan@192.168.68.119 "cd ~/sparc && docker compose ps"

# Live logs
ssh dan@192.168.68.119 "cd ~/sparc && docker compose logs -f api"

# RAM per container (live)
ssh dan@192.168.68.119 "docker stats --no-stream"

# Restart single container
ssh dan@192.168.68.119 "cd ~/sparc && docker compose restart grafana"

# Restart full stack
ssh dan@192.168.68.119 "cd ~/sparc && docker compose restart"

# Push code update from Mac to NUC
rsync -av --exclude='__pycache__' --exclude='*.pyc' \
  -e "ssh -i ~/.ssh/id_ed25519" \
  deployment/ src/ config/ \
  dan@192.168.68.119:~/sparc/
ssh dan@192.168.68.119 "cd ~/sparc && docker compose build api && docker compose up -d api"
```

---

## Security posture (current — private LAN only)

| What | Status | Risk |
|------|--------|------|
| Internet exposure | None — no port forwarding on Eero | None |
| SSH access | Key-only from Mac | Low |
| NOPASSWD sudo | Enabled for `dan` user | Low (private LAN) |
| All Docker ports | Exposed on LAN (8000, 3001, 5432 etc) | Low (trusted network) |
| .env secrets | On NUC filesystem | Low (private machine) |

**If Cloudflare Tunnel is ever added (public HTTPS):**
Before doing this, harden the NUC:
1. Disable SSH password auth: `PasswordAuthentication no` in `/etc/ssh/sshd_config`
2. Scope sudo: replace `NOPASSWD:ALL` with specific commands only
3. Move secrets to Docker secrets or a secrets manager
4. Add UFW firewall rules

---

## Versions installed

| Software | Version |
|----------|---------|
| Ubuntu | 26.04 LTS |
| Docker CE | latest (from get.docker.com) |
| TimescaleDB | latest-pg16 |
| Grafana OSS | 11.0.0 |
| Redis | 7-alpine |
| n8n | latest |
| Caddy | 2-alpine |
| Prometheus | 2.52.0 |
| cAdvisor | 0.49.1 |
| node-exporter | 1.8.1 |
