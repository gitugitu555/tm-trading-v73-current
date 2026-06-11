#!/usr/bin/env python3
"""Rebuild occupancy-free immutable signals on the verified V8.9 catalog."""

from __future__ import annotations
import json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys; sys.path.insert(0,str(ROOT))
from research.v86_recovery import write_jsonl
from research.v88_signal_ledger import build_signal_ledger
from research.v89_data_catalog import canonical_hash
from research.v89_volume_bar_builder import load_verified_catalog

def main()->int:
    catalog_path=ROOT/"results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    catalog_manifest=json.loads((catalog_path.parent/"manifest.json").read_text())
    bars=load_verified_catalog(catalog_path)
    params={"lookback_bars":30,"htf_flat_quantile":0.25,"catalog_manifest_hash":catalog_manifest["catalog_manifest_hash"]}
    params_hash=canonical_hash(params)
    ledger=build_signal_ledger(bars,lookback_bars=30,source_archive=catalog_manifest["catalog_id"],build_manifest_hash=params_hash)
    out=ROOT/"results/v89_data_foundation/verified_signal_ledger"; write_jsonl(out/"immutable_signal_ledger.jsonl",ledger)
    monthly=Counter(datetime.fromtimestamp(int(row["signal_ts_ns"])/1e9,tz=timezone.utc).strftime("%Y-%m") for row in ledger)
    summary={"catalog_manifest_hash":catalog_manifest["catalog_manifest_hash"],"coverage_audit_hash":catalog_manifest["coverage_audit_hash"],"signal_params_hash":params_hash,"start_ts_ns":bars[0].start_ts_ns,"end_ts_ns":bars[-1].end_ts_ns,"signal_count":len(ledger),"long_count":sum(r["side_int"]>0 for r in ledger),"short_count":sum(r["side_int"]<0 for r in ledger),"monthly_signal_counts":dict(sorted(monthly.items()))}
    (ROOT/"results/v89_data_foundation/verified_signal_ledger_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
