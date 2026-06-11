#!/usr/bin/env python3
"""Rebuild 96-bar paths for verified immutable signals."""

from __future__ import annotations
import json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from research.v86_recovery import load_jsonl,write_jsonl
from research.v88_trade_path import reconstruct_path
from research.v89_volume_bar_builder import load_verified_catalog

def main()->int:
    signals=load_jsonl(ROOT/"results/v89_data_foundation/verified_signal_ledger/immutable_signal_ledger.jsonl")
    bars=load_verified_catalog(ROOT/"results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet")
    paths=[reconstruct_path(s,bars) for s in signals if int(s["bar_id"])+97<=len(bars)]
    out=ROOT/"results/v89_data_foundation/verified_trade_paths"; write_jsonl(out/"trade_paths.jsonl",paths)
    summary={"signals_total":len(signals),"paths_complete":len(paths),"paths_incomplete":len(signals)-len(paths),"completion_rate":len(paths)/len(signals) if signals else 0,"avg_mfe":statistics.mean(p["max_favorable_excursion_pct"] for p in paths),"avg_mae":statistics.mean(p["max_adverse_excursion_pct"] for p in paths),"positive_mfe_before_loss_rate":sum(p["positive_mfe_before_loss"] for p in paths)/len(paths)}
    (ROOT/"results/v89_data_foundation/verified_trade_path_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
