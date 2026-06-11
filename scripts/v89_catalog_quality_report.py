#!/usr/bin/env python3
"""Generate verified catalog quality diagnostics."""

from __future__ import annotations
import json,statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    rows=pq.read_table(ROOT/"results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet").to_pylist()
    durations=[int(r["end_ts_ns"])-int(r["start_ts_ns"]) for r in rows]; months=Counter(datetime.fromtimestamp(int(r["end_ts_ns"])/1e9,tz=timezone.utc).strftime("%Y-%m") for r in rows)
    gaps=[int(b["start_ts_ns"])-int(a["end_ts_ns"]) for a,b in zip(rows,rows[1:])]
    report={"bar_count":len(rows),"bar_count_by_month":dict(sorted(months.items())),"avg_trades_per_bar":statistics.mean(int(r["ticks"]) for r in rows),"avg_duration_ns":statistics.mean(durations),"median_duration_ns":statistics.median(durations),"max_duration_ns":max(durations),"min_duration_ns":min(durations),"max_gap_ns":max(gaps),"negative_timestamp_gaps":sum(g<0 for g in gaps),"equal_timestamp_boundaries":sum(g==0 for g in gaps),"bad_prices":sum(min(float(r[k]) for k in ("open","high","low","close"))<=0 for r in rows),"bad_volume":sum(float(r["volume"])<300 for r in rows)}
    out=ROOT/"results/v89_data_foundation"; (out/"catalog_quality.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
