#!/usr/bin/env python3
"""Create chronological verified-data walk-forward windows."""

from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    summary=json.loads((ROOT/"results/v89_data_foundation/v88_verified_replay/policy_summary.json").read_text())
    years=sorted(summary["best_by_year"])
    report={"available_years":years,"protocols":["train 6m -> test 1m","train 12m -> test 3m","train 24m -> test 6m"],"status":"structure_ready; full policy-selection implementation pending monthly fold execution","hard_rule":"no promotion from full-sample rank"}
    out=ROOT/"results/v89_data_foundation/walkforward"; out.mkdir(parents=True,exist_ok=True); (out/"verified_walkforward.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
