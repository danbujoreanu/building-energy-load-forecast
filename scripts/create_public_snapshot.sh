#!/usr/bin/env bash
# create_public_snapshot.sh
# =========================
# Creates a clean public-facing academic snapshot of the pipeline.
# Run this ONCE at journal paper submission time.
#
# What it does:
#   1. Copies academic code only (src/, scripts/, config/, tests/, docs/ — minus commercial files)
#   2. Initialises a new git repo in the snapshot directory
#   3. Prints the commands to push it to a new public GitHub repo
#
# What it EXCLUDES (commercial IP):
#   - deployment/           (ControlEngine, connectors, live_inference API)
#   - docs/COMMERCIAL_ANALYSIS.md
#   - Any *.env, secrets, credentials
#
# Usage:
#   bash scripts/create_public_snapshot.sh
#
# Prerequisites:
#   - Run from the project root
#   - gh CLI authenticated

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT_DIR="${HOME}/building-energy-load-forecast-paper"
PUBLIC_REPO="danbujoreanu/building-energy-load-forecast-paper"

echo "=== Academic Snapshot Builder ==="
echo "Source:      ${PROJECT_ROOT}"
echo "Destination: ${SNAPSHOT_DIR}"
echo ""

# ── Safety check ────────────────────────────────────────────────────────────
if [ -d "${SNAPSHOT_DIR}" ]; then
    echo "ERROR: ${SNAPSHOT_DIR} already exists. Remove it first:"
    echo "  rm -rf ${SNAPSHOT_DIR}"
    exit 1
fi

mkdir -p "${SNAPSHOT_DIR}"

# ── Copy academic files only ─────────────────────────────────────────────────
echo "Copying academic pipeline files..."

rsync -av --progress \
    --exclude='.git/' \
    --exclude='deployment/' \
    --exclude='docs/COMMERCIAL_ANALYSIS.md' \
    --exclude='outputs/predictions/' \
    --exclude='outputs/models/' \
    --exclude='outputs/logs/' \
    --exclude='data/raw/' \
    --exclude='data/processed/' \
    --exclude='**/__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='*.env' \
    --exclude='secrets.yaml' \
    --exclude='*.h5' \
    --exclude='*.pkl' \
    --exclude='*.pt' \
    --exclude='*.pth' \
    --exclude='*.ckpt' \
    --exclude='lightning_logs/' \
    "${PROJECT_ROOT}/" "${SNAPSHOT_DIR}/"

echo ""
echo "Copied. Contents:"
ls "${SNAPSHOT_DIR}/"

# ── Confirm no commercial files leaked ──────────────────────────────────────
echo ""
echo "=== Verifying no commercial files in snapshot ==="
if [ -d "${SNAPSHOT_DIR}/deployment" ]; then
    echo "ERROR: deployment/ found in snapshot. Check rsync excludes."
    exit 1
fi
if [ -f "${SNAPSHOT_DIR}/docs/COMMERCIAL_ANALYSIS.md" ]; then
    echo "ERROR: COMMERCIAL_ANALYSIS.md found in snapshot. Check rsync excludes."
    exit 1
fi
echo "Clean. No commercial files detected."

# ── Initialise git ───────────────────────────────────────────────────────────
echo ""
echo "=== Initialising public git repo ==="
cd "${SNAPSHOT_DIR}"
git init
git add .
git commit -m "$(cat <<'EOF'
Initial public release — Building Energy Load Forecast (academic pipeline)

Three-paradigm benchmark: LightGBM (Setup A) vs DL on features (Setup B, negative
control) vs DL on raw sequences (Setup C) for H+24 day-ahead building load forecasting.

Key results:
  LightGBM MAE = 4.029 kWh, R² = 0.975 (Drammen, 44 buildings)
  Oslo generalisation: LightGBM R² = 0.963 (48 buildings, zero-shot)
  PatchTST (best DL): MAE = 6.955 kWh, R² = 0.910

Companion to: Bujoreanu, D.A. & Onwuegbuche, F.C. (2025). Forecasting Energy Demand
in Buildings: The Case for Trees over Deep Nets. AICS 2025, Springer LNCS.

Journal paper: under review at Applied Energy / Energy and Buildings.
EOF
)"

echo ""
echo "=== Next steps to publish ==="
echo ""
echo "1. Create the public repo on GitHub (do NOT auto-init):"
echo "   gh repo create ${PUBLIC_REPO} --public --description 'Building energy load forecasting — academic pipeline'"
echo ""
echo "2. Push:"
echo "   git remote add origin https://github.com/${PUBLIC_REPO}.git"
echo "   git push -u origin main"
echo ""
echo "3. Add Zenodo DOI (for journal paper citation):"
echo "   → Go to zenodo.org, connect GitHub, release the repo, get DOI"
echo "   → Add DOI badge to README"
echo ""
echo "Snapshot ready at: ${SNAPSHOT_DIR}"
