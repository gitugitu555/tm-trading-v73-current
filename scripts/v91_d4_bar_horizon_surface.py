#!/usr/bin/env python3
"""Run the final D4 bar-size, horizon, and context surface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v89_volume_bar_builder import consolidate_cached_bars, load_verified_catalog
from research.v91_d4_surface import build_surface, rebar_volume_bars


def main() -> int:
    audit = json.loads((ROOT / "results/v89_data_foundation/coverage_audit.json").read_text(encoding="utf-8"))
    cache_files = [
        ROOT / "results/volume_bar_cvd_cache" / f"{name}.thresholds-100-200-300.v1.parquet"
        for name in audit["expected_archives"]
    ]
    missing = [str(path) for path in cache_files if not path.is_file()]
    if missing:
        raise SystemExit(f"missing canonical caches: {missing}")
    base_100, _ = consolidate_cached_bars(cache_files, threshold=100.0)
    verified_300 = load_verified_catalog(
        ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    )
    bars_by_threshold = {300: verified_300}
    for threshold in (500, 750, 1000, 1500):
        bars_by_threshold[threshold] = rebar_volume_bars(base_100, threshold)
    report = build_surface(bars_by_threshold)
    report["data_sources"] = {
        "300": "exact verified catalog",
        "500_750_1000_1500": "deterministic rebars from canonical 100 BTC per-archive caches; approximate boundaries",
        "coverage_audit_hash": audit["coverage_audit_hash"],
        "bar_counts": {str(key): len(value) for key, value in bars_by_threshold.items()},
    }
    output = ROOT / "results/v91_alpha_discovery/d4_bar_horizon_surface.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print_summary(report)
    print(f"wrote {output}")
    return 0


def print_summary(report: dict) -> None:
    recent = sorted(
        report["rows"],
        key=lambda row: row["2024-2026"]["net_expectancy_bps"]["1"],
        reverse=True,
    )
    for row in recent[:10]:
        metrics = row["2024-2026"]
        print(
            f"{row['bar_size_btc']:>4} h={row['horizon_bars']:>2} {row['context']:<11} "
            f"n={metrics['events']:>5} mean={metrics['mean_signed_return_bps']:>7.3f}bps "
            f"net1={metrics['net_expectancy_bps']['1']:>7.3f}bps"
        )


if __name__ == "__main__":
    raise SystemExit(main())
