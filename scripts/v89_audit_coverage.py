#!/usr/bin/env python3
"""Audit configured date coverage and hard-fail on incomplete canonical archives."""

from __future__ import annotations
import argparse, json, sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.v89_data_catalog import canonical_hash, coverage_audit, write_csv

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--start-date",default="2020-05-22"); p.add_argument("--end-date",default="2026-05-21"); ns=p.parse_args()
    inventory=json.loads((ROOT/"results/v89_data_foundation/raw_inventory.json").read_text())
    audit=coverage_audit(inventory["records"],start=date.fromisoformat(ns.start_date),end=date.fromisoformat(ns.end_date))
    audit["coverage_audit_hash"]=canonical_hash(audit)
    out=ROOT/"results/v89_data_foundation"; (out/"coverage_audit.json").write_text(json.dumps(audit,indent=2,sort_keys=True),encoding="utf-8")
    write_csv(out/"coverage_audit.csv",[{"filename":name,"status":"missing"} for name in audit["missing_archives"]] or [{"filename":"","status":"complete"}])
    return 0 if audit["coverage_passed"] else 2
if __name__=="__main__": raise SystemExit(main())
