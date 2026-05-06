#!/usr/bin/env bash
# docker_stats_prom.sh — write Docker container metrics in Prometheus textfile format.
# Run every 30s via cron (see crontab entry in NUC_ACCESS.md).
# node_exporter reads /var/node_exporter/textfiles/*.prom automatically.
#
# Exposes:
#   docker_container_memory_bytes{name}   — RSS memory in bytes
#   docker_container_cpu_percent{name}    — CPU % (0–100 per core)
#   docker_container_running{name}        — 1 if running
#
# Install:
#   sudo mkdir -p /var/node_exporter/textfiles
#   sudo chmod 777 /var/node_exporter/textfiles
#   chmod +x ~/sparc/scripts/docker_stats_prom.sh
#   crontab -e  →  add the two lines below:
#   * * * * * /home/dan/sparc/scripts/docker_stats_prom.sh
#   * * * * * sleep 30 && /home/dan/sparc/scripts/docker_stats_prom.sh

set -euo pipefail

OUTDIR="/var/node_exporter/textfiles"
OUTFILE="$OUTDIR/docker_stats.prom"
TMP="$(mktemp "$OUTDIR/docker_stats.XXXXXX")"

cat > "$TMP" << 'HEADER'
# HELP docker_container_memory_bytes Container memory usage in bytes (RSS)
# TYPE docker_container_memory_bytes gauge
# HELP docker_container_cpu_percent Container CPU usage percent
# TYPE docker_container_cpu_percent gauge
# HELP docker_container_running Container is running (1=yes)
# TYPE docker_container_running gauge
HEADER

# docker stats --no-stream returns one sample (no CPU % warmup needed for trend)
docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' \
| while IFS=$'\t' read -r cname memstr cpustr; do
    # Parse memory: "160.5MiB / 6.429GiB" — take only the used part (before " /")
    used_mem="${memstr%% /*}"
    mem_bytes=$(awk -v v="$used_mem" 'BEGIN {
        val = v; gsub(/[^0-9.]/,"",val)
        if (v ~ /GiB/) val = val * 1073741824
        else if (v ~ /MiB/) val = val * 1048576
        else if (v ~ /kB/)  val = val * 1000
        else if (v ~ /KiB/) val = val * 1024
        printf "%.0f", val
    }')
    cpu=$(echo "$cpustr" | tr -d '%')
    printf 'docker_container_memory_bytes{name="%s"} %s\n' "$cname" "$mem_bytes"
    printf 'docker_container_cpu_percent{name="%s"} %s\n'  "$cname" "$cpu"
    printf 'docker_container_running{name="%s"} 1\n'       "$cname"
done >> "$TMP"

chmod 644 "$TMP"
mv "$TMP" "$OUTFILE"
