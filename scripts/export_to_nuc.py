"""
scripts/export_to_nuc.py
========================
Exports intel_garden and intel_mba collections from the Mac's monolithic
ChromaDB (data/chromadb/) into a clean, portable nuc_export_db/ directory
that Gardening's unified-rag-api can mount directly on the NUC.

Why raw copy instead of Python API:
  chromadb is not installed on the Mac's system Python. The raw copy approach
  works by: (1) copying the HNSW VECTOR segment directories for garden + mba,
  (2) creating a new sqlite3 with only the garden + mba rows. No re-embedding.

Usage:
    python3 scripts/export_to_nuc.py [--dry-run]

Output:
    outputs/nuc_export_db/   (a valid ChromaDB directory, ~15MB)

Sync to NUC afterward:
    rsync -avz --delete outputs/nuc_export_db/ dan@192.168.68.119:~/gardening/nuc_export_db/

Note: Run from project root. Last known working with chromadb==0.6.3 layout.
"""

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
SRC_CHROMADB = _ROOT / "data" / "chromadb"
DST_CHROMADB = _ROOT / "outputs" / "nuc_export_db"

EXPORT_COLLECTIONS = {
    # ── Mac-ingested collections (from data/chromadb) ──────────────────────────
    "intel_garden",      # Gardening Digital Twin corpus
    "intel_mba",         # UCD MBA textbooks + HBR cases (97 PDFs, ~4300 chunks)
    "intel_career",      # Career frameworks, BSS prep, PM interview notes
    # ── Mac-ingested collections (from data/chromadb, added 2026-05-14) ────────
    "intel_regulatory",  # CRU decisions, Smart Meter Access, Reduce Your Use campaign
    "intel_market",      # COMMERCIAL_ANALYSIS, MARKET_POSITIONING, BMS JD gap analysis
    "intel_strategic",   # STRATEGY, APP_PRODUCT_SPEC, funding docs, Google Accelerator
    # ── EXCLUDED ────────────────────────────────────────────────────────────────
    # "intel_operational"  — NUC's version (328 chunks) is authoritative;
    #                        Mac's data/chromadb copy (27 chunks) is stale.
    #                        Operational docs are served by sparc-api directly.
}
# ── Single-source workflow ─────────────────────────────────────────────────────
# ALL ingestion happens on Mac. NUC only serves the pre-built database.
#
#   1. Add/edit docs in intel/docs/<tier>/ or ~/UCD/ (PDFs)
#   2. python3 scripts/export_to_nuc.py              → builds nuc_export_db/ from data/chromadb
#   3. rsync outputs/nuc_export_db/ → NUC            → delivers finished database
#
# To ingest new tiers on Mac (use the PERSISTENT dev container — never --rm):
#   docker exec sparc-api python3 /app/scripts/ingest_changed.py --tier <tier>
#
# DO NOT use `docker run --rm` for ingest. ChromaDB's HNSW flush requires
# the container to stay alive long enough to call _persist(). A --rm container
# is destroyed before the flush completes, leaving data_level0.bin empty.


def _handshake(src: sqlite3.Connection, col_ids: list, col_rows: list) -> None:
    """Verify all export collections have > 0 embeddings before syncing.

    Queries the METADATA segment embedding count from SQLite — no chromadb
    import needed (consistent with this script's raw-copy design). If any
    collection has 0 chunks, the function prints a diagnostic and calls
    sys.exit(1) so the rsync never starts with a broken database.

    This is the Pre-Sync Handshake: run it before every export.
    """
    ph = ",".join("?" for _ in col_ids)
    seg_counts = src.execute(
        f"SELECT c.name, COUNT(e.id) "
        f"FROM collections c "
        f"JOIN segments s ON s.collection = c.id "
        f"JOIN embeddings e ON e.segment_id = s.id "
        f"WHERE c.id IN ({ph}) AND s.scope = 'METADATA' "
        f"GROUP BY c.name",
        col_ids,
    ).fetchall()

    count_map = {name: cnt for name, cnt in seg_counts}
    failed = []
    for row in col_rows:
        name = row[1]
        cnt = count_map.get(name, 0)
        status = "✓" if cnt > 0 else "✗ FAIL"
        print(f"  {status}  {name}: {cnt} chunks")
        if cnt == 0:
            failed.append(name)

    if failed:
        print(
            f"\n❌ Handshake FAILED — 0 chunks in: {failed}\n"
            "Do NOT sync. Re-run ingest_changed.py for the affected tiers,\n"
            "then verify with: docker exec sparc-api python3 -c "
            "\"from intel.ingest import get_status; import json; "
            "print(json.dumps(get_status(), indent=2))\"",
            file=sys.stderr,
        )
        sys.exit(1)

    print("✓ Handshake passed — all collections have data\n")


def export(dry_run: bool) -> None:
    src_sqlite = SRC_CHROMADB / "chroma.sqlite3"
    if not src_sqlite.exists():
        print(f"Source ChromaDB not found: {src_sqlite}", file=sys.stderr)
        sys.exit(1)

    # ── Read source metadata ──────────────────────────────────────────────────
    src = sqlite3.connect(src_sqlite)

    # Collections to export
    ph = ",".join("?" for _ in EXPORT_COLLECTIONS)
    col_rows = src.execute(
        f"SELECT id, name, dimension, database_id, config_json_str FROM collections WHERE name IN ({ph})",
        list(EXPORT_COLLECTIONS),
    ).fetchall()
    if len(col_rows) != len(EXPORT_COLLECTIONS):
        found = {r[1] for r in col_rows}
        missing = EXPORT_COLLECTIONS - found
        print(f"WARNING: Collections not found in source (skip or ingest first): {missing}", file=sys.stderr)
        if not col_rows:
            sys.exit(1)

    col_ids = [r[0] for r in col_rows]
    print(f"Collections to export: {[r[1] for r in col_rows]}")

    # ── Pre-sync handshake: verify all collections have data ──────────────────
    print("\n── Handshake: verifying all collections have embeddings ──")
    _handshake(src, col_ids, col_rows)

    # Segments (VECTOR + METADATA) for these collections
    ph = ",".join("?" for _ in col_ids)
    seg_rows = src.execute(
        f"SELECT id, type, scope, collection FROM segments WHERE collection IN ({ph})",
        col_ids,
    ).fetchall()
    seg_ids = [r[0] for r in seg_rows]
    vector_seg_ids = [r[0] for r in seg_rows if r[2] == "VECTOR"]
    print(f"Segments: {len(seg_rows)} ({len(vector_seg_ids)} VECTOR)")

    # Embeddings (rows in embeddings table)
    ph_s = ",".join("?" for _ in seg_ids)
    emb_rows = src.execute(
        f"SELECT id, segment_id, embedding_id, seq_id, created_at FROM embeddings WHERE segment_id IN ({ph_s})",
        seg_ids,
    ).fetchall()
    emb_ids = [r[0] for r in emb_rows]
    print(f"Embeddings: {len(emb_ids)}")

    # Embedding metadata
    ph_e = ",".join("?" for _ in emb_ids)
    meta_rows = src.execute(
        f"SELECT id, key, string_value, int_value, float_value, bool_value "
        f"FROM embedding_metadata WHERE id IN ({ph_e})",
        emb_ids,
    ).fetchall()
    print(f"Metadata rows: {len(meta_rows)}")

    # Max seq_id
    max_seq = src.execute(
        "SELECT segment_id, seq_id FROM max_seq_id WHERE segment_id IN (" + ph_s + ")",
        seg_ids,
    ).fetchall()

    if dry_run:
        print("\n[Dry run] Nothing written.")
        src.close()
        return

    # ── Create destination ────────────────────────────────────────────────────
    if DST_CHROMADB.exists():
        shutil.rmtree(DST_CHROMADB)
    DST_CHROMADB.mkdir(parents=True)

    # ── Copy VECTOR segment directories ──────────────────────────────────────
    for seg_id in vector_seg_ids:
        src_dir = SRC_CHROMADB / seg_id
        if src_dir.exists():
            shutil.copytree(src_dir, DST_CHROMADB / seg_id)
            print(f"Copied VECTOR segment dir: {seg_id[:8]}...")
        else:
            print(f"WARNING: VECTOR segment dir not on disk: {seg_id}", file=sys.stderr)

    # ── Build new sqlite3 ─────────────────────────────────────────────────────
    dst_sqlite = DST_CHROMADB / "chroma.sqlite3"
    dst = sqlite3.connect(dst_sqlite)

    # Copy schema from source (all CREATE statements)
    schema = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
    ).fetchall()
    for (sql,) in schema:
        try:
            dst.execute(sql)
        except sqlite3.OperationalError:
            pass  # table already exists in a fresh db — skip

    # Copy index definitions
    indexes = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ).fetchall()
    for (sql,) in indexes:
        try:
            dst.execute(sql)
        except sqlite3.OperationalError:
            pass

    # Populate required infrastructure tables (tenants, databases)
    tenant_rows = src.execute("SELECT * FROM tenants").fetchall()
    db_rows = src.execute("SELECT * FROM databases").fetchall()
    # Migrations
    mig_rows = src.execute("SELECT * FROM migrations").fetchall()

    dst.executemany("INSERT OR IGNORE INTO tenants VALUES (" + ",".join("?" for _ in tenant_rows[0]) + ")", tenant_rows)
    dst.executemany("INSERT OR IGNORE INTO databases VALUES (" + ",".join("?" for _ in db_rows[0]) + ")", db_rows)
    if mig_rows:
        dst.executemany("INSERT OR IGNORE INTO migrations VALUES (" + ",".join("?" for _ in mig_rows[0]) + ")", mig_rows)

    # Collections
    dst.executemany("INSERT INTO collections VALUES (?,?,?,?,?)", col_rows)

    # Segments
    dst.executemany("INSERT INTO segments VALUES (?,?,?,?)", seg_rows)

    # Max seq_id
    if max_seq:
        dst.executemany("INSERT OR IGNORE INTO max_seq_id VALUES (?,?)", max_seq)

    # Embeddings (batch insert for performance)
    batch_size = 1000
    for i in range(0, len(emb_rows), batch_size):
        batch = emb_rows[i : i + batch_size]
        dst.executemany("INSERT INTO embeddings VALUES (?,?,?,?,?)", batch)

    # Embedding metadata
    for i in range(0, len(meta_rows), batch_size):
        batch = meta_rows[i : i + batch_size]
        dst.executemany("INSERT INTO embedding_metadata VALUES (?,?,?,?,?,?)", batch)

    dst.commit()
    dst.close()
    src.close()

    size = sum(f.stat().st_size for f in DST_CHROMADB.rglob("*") if f.is_file())
    print(f"\nExported to: {DST_CHROMADB}")
    print(f"Total size: {size / 1024 / 1024:.1f} MB")
    print("\nSync to NUC:")
    print(f"  rsync -avz --delete {DST_CHROMADB}/ dan@192.168.68.119:~/gardening/nuc_export_db/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export intel_garden + intel_mba to nuc_export_db/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    export(args.dry_run)


if __name__ == "__main__":
    main()
