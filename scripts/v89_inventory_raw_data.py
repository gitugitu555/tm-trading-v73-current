#!/usr/bin/env python3
"""Inventory BTCUSDT raw archives using verified cache metadata where available."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v89_data_catalog import canonical_hash, inventory_archive, write_csv
from storage.hot_path import hot_btcusdt_aggtrades_dir


def main() -> int:
    raw_dir = hot_btcusdt_aggtrades_dir()
    cache_dir = ROOT / "results/volume_bar_cvd_cache"
    records = []
    for archive in sorted(raw_dir.glob("BTCUSDT-aggTrades-*.zip")):
        cache = cache_dir / f"{archive.name}.thresholds-100-200-300.v1.parquet"
        metadata = None
        if cache.is_file():
            table = pq.read_table(cache, columns=["archive_size", "archive_mtime_ns", "rows_seen", "threshold_btc", "start_ts_ns", "end_ts_ns"])
            rows = table.to_pylist()
            threshold_rows = [row for row in rows if float(row["threshold_btc"]) == 300.0]
            stat = archive.stat()
            metadata = {
                "first_ts_ns": min(int(row["start_ts_ns"]) for row in threshold_rows),
                "last_ts_ns": max(int(row["end_ts_ns"]) for row in threshold_rows),
                "row_count": int(rows[0]["rows_seen"]),
                "timestamp_monotonic": all(int(a["end_ts_ns"]) <= int(b["end_ts_ns"]) for a, b in zip(threshold_rows, threshold_rows[1:])),
            }
            if int(rows[0]["archive_size"]) != stat.st_size or int(rows[0]["archive_mtime_ns"]) != stat.st_mtime_ns:
                metadata = None
        record = inventory_archive(archive, metadata)
        record["cache_metadata_available"] = metadata is not None
        records.append(record)
    summary = {
        "records": records,
        "total_files": len(records),
        "canonical_archive_count": sum("_1m" not in row["filename"] for row in records),
        "total_rows_from_verified_caches": sum(int(row["row_count"] or 0) for row in records if "_1m" not in row["filename"]),
        "raw_manifest_hash": canonical_hash(records),
    }
    out = ROOT / "results/v89_data_foundation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "raw_inventory.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(out / "raw_inventory.csv", records)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
