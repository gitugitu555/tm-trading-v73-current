#!/usr/bin/env python3
"""Build exact-range verified consolidated volume bars from per-archive caches."""

from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from research.v89_volume_bar_builder import build_manifest,consolidate_cached_bars,write_verified_catalog

def main()->int:
    inventory=json.loads((ROOT/"results/v89_data_foundation/raw_inventory.json").read_text()); audit=json.loads((ROOT/"results/v89_data_foundation/coverage_audit.json").read_text())
    if not audit["coverage_passed"]: raise SystemExit("coverage audit failed; verified catalog build refused")
    names=audit["expected_archives"]
    caches=[ROOT/"results/volume_bar_cvd_cache"/f"{name}.thresholds-100-200-300.v1.parquet" for name in names]
    missing=[str(path) for path in caches if not path.is_file()]
    if missing: raise SystemExit(f"missing verified per-archive caches: {missing}")
    bars,trades=consolidate_cached_bars(caches)
    out=ROOT/"results/v89_data_foundation/catalog"; path=out/"BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    manifest=build_manifest(bars=bars,trade_count=trades,raw_manifest_hash=inventory["raw_manifest_hash"],coverage_audit_hash=audit["coverage_audit_hash"],output_file=path,repo_commit=commit)
    write_verified_catalog(path,bars,manifest); (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
