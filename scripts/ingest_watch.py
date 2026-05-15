"""
Energy RAG — Mac-Side Auto-Ingest Watcher
==========================================
Watches intel/docs/ on the Mac for .md and .pdf file changes, then triggers
ingest + flush + count-check inside the persistent local sparc-api container.

Follows the "no docker run --rm" rule: uses `docker exec sparc-api` against
the always-running Mac dev container, never a throwaway container. This ensures
ChromaDB has time to flush properly and the environment is stable.

Design:
  - File created/modified  → ingest_file() + flush_tier() in ONE exec call
    (same Python process = same singleton = _curr_batch stays alive)
  - File deleted           → delete_file() in ONE exec call (chunks removed + flushed)
  - Upsert semantics       → ingest_file() evicts stale chunks before re-embedding;
    dedup by doc_hash means unchanged files are skipped at zero cost
  - Count-check            → flush_tier() raises RuntimeError if post-flush count == 0;
    watcher logs the error and skips the export step for that tier
  - After successful ingest: export_to_nuc.py is NOT auto-triggered here —
    run it manually or via cron when ready to sync to NUC

Run (Mac, from project root):
    python3 scripts/ingest_watch.py

Dependencies (must be in active Python env):
    pip install watchdog  (or: pip install -r intel/requirements.txt)

NUC systemd note:
    The previous NUC-side energy-ingest-watch.service is now DEPRECATED.
    The NUC is read-only (no new docs added there). Disable it:
        ssh nuc "sudo systemctl disable --now energy-ingest-watch.service"

Port from: Gardening AI/ingest_watch.py (2026-05-13)
Updated: 2026-05-14 — Mac-side, delete-sync, flush + count-check
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("energy-ingest-watch")
logging.getLogger("chromadb").setLevel(logging.CRITICAL)

# ── Config ─────────────────────────────────────────────────────────────────────
# Mac-side: watch the project's intel/docs/ directory
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = _PROJECT_ROOT / "intel" / "docs"

# Map subdirectory name → tier (must match VALID_TIERS in intel/ingest.py)
TIER_MAP: dict[str, str] = {
    "operational": "operational",
    "strategic": "strategic",
    "research": "research",
    "market": "market",
    "career": "career",
    "mba": "mba",
    "garden": "garden",
    "engineering": "engineering",
    "regulatory": "regulatory",
}

# The persistent Mac dev container (never use docker run --rm for ingest)
CONTAINER_NAME = "sparc-api"

# Debounce: editors often emit multiple rapid events for a single save
_last_event: dict[str, float] = {}
DEBOUNCE_SECONDS = 3.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _container_path(path: Path, tier: str) -> str:
    """Convert a Mac host path to its container equivalent under /app/."""
    return f"/app/intel/docs/{tier}/{path.name}"


def _run_exec(cmd: list[str], label: str) -> bool:
    """Run a docker exec command and log the outcome. Returns True on success."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            logger.info("%s: %s", label, result.stdout.strip() or "ok")
            return True
        else:
            logger.error(
                "%s failed (exit %s): %s",
                label,
                result.returncode,
                result.stderr.strip() or result.stdout.strip(),
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error("%s timed out", label)
        return False
    except FileNotFoundError:
        logger.error("docker not found — is the Mac dev container running?")
        return False


def _debounce(path: Path) -> bool:
    """Return True if this event should be processed (not debounced)."""
    now = time.monotonic()
    key = str(path)
    if now - _last_event.get(key, 0) < DEBOUNCE_SECONDS:
        return False
    _last_event[key] = now
    return True


# ── Ingest + flush (combined in one exec call) ────────────────────────────────

def _ingest(path: Path, tier: str) -> None:
    """Ingest a changed file and flush the tier — single docker exec call.

    Combining ingest_file() + flush_tier() in one `-c` string is mandatory:
    both functions must share the same Python process to access _curr_batch.
    A second docker exec would create a new process with no _curr_batch → flush
    would silently produce an empty HNSW segment.
    """
    if not _debounce(path):
        return

    logger.info("Change: %s (tier=%s) — ingesting", path.name, tier)
    cpath = _container_path(path, tier)

    cmd = [
        "docker", "exec", CONTAINER_NAME,
        "python3", "-c",
        (
            "import sys, warnings; warnings.filterwarnings('ignore'); "
            "sys.path.insert(0, '/app'); "
            "from intel.ingest import ingest_file, flush_tier; "
            f"ingested = ingest_file('{cpath}', '{tier}'); "
            f"count = flush_tier('{tier}') if ingested else 0; "
            "print(f'ingested={ingested} chunks_verified={count}')"
        ),
    ]
    _run_exec(cmd, f"ingest {path.name}")


# ── Delete-sync ────────────────────────────────────────────────────────────────

def _delete(path: Path, tier: str) -> None:
    """Remove a deleted file's chunks from ChromaDB — single docker exec call."""
    if not _debounce(path):
        return

    logger.info("Delete: %s (tier=%s) — removing chunks", path.name, tier)

    cmd = [
        "docker", "exec", CONTAINER_NAME,
        "python3", "-c",
        (
            "import sys, warnings; warnings.filterwarnings('ignore'); "
            "sys.path.insert(0, '/app'); "
            "from intel.ingest import delete_file; "
            f"n = delete_file('{path.name}', '{tier}'); "
            "print(f'deleted {n} chunks')"
        ),
    ]
    _run_exec(cmd, f"delete {path.name}")


# ── Watchdog handler ───────────────────────────────────────────────────────────

class EnergyHandler(FileSystemEventHandler):
    """Handle file-system events for the intel/docs/ tree."""

    def _tier(self, path: Path) -> str | None:
        return TIER_MAP.get(path.parent.name)

    def _valid(self, path: Path) -> bool:
        return path.suffix in {".md", ".pdf"}

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._valid(path) and (tier := self._tier(path)):
            _ingest(path, tier)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._valid(path) and (tier := self._tier(path)):
            _ingest(path, tier)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._valid(path) and (tier := self._tier(path)):
            _delete(path, tier)

    def on_moved(self, event) -> None:
        # Treat rename/move-in as create of destination
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        src = Path(event.src_path)
        if self._valid(dest) and (tier := self._tier(dest)):
            _ingest(dest, tier)
        # If moved out of a watched tier, treat as delete
        if self._valid(src) and (tier := self._tier(src)):
            _delete(src, tier)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not DOCS_ROOT.exists():
        logger.error(
            "DOCS_ROOT does not exist: %s\n"
            "Expected intel/docs/ under the project root on Mac.",
            DOCS_ROOT,
        )
        sys.exit(1)

    logger.info("Energy ingest watcher starting (Mac-side)")
    logger.info("Watching: %s", DOCS_ROOT)
    logger.info("Container: %s (persistent dev container — never --rm)", CONTAINER_NAME)
    logger.info("Tiers: %s", ", ".join(sorted(TIER_MAP)))

    handler = EnergyHandler()
    observer = Observer()
    observer.schedule(handler, str(DOCS_ROOT), recursive=True)
    observer.start()

    logger.info("Watcher running — Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
