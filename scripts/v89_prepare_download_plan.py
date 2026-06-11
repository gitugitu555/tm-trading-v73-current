#!/usr/bin/env python3
"""Generate an explicit Binance public-data repair plan without downloading by default."""

from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE="https://data.binance.vision/data/spot"

def main()->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--execute",action="store_true"); ns=p.parse_args()
    audit=json.loads((ROOT/"results/v89_data_foundation/coverage_audit.json").read_text())
    items=[]
    for name in audit["missing_archives"]:
        kind="daily" if len(name.removeprefix("BTCUSDT-aggTrades-").removesuffix(".zip"))==10 else "monthly"
        items.append({"symbol":"BTCUSDT","expected_filename":name,"expected_url":f"{BASE}/{kind}/aggTrades/BTCUSDT/{name}","destination_path":name})
    plan={"missing_archives":audit["missing_archives"],"download_items":items,"executed":False,"note":"Use existing approved downloader workflow; this script refuses implicit network mutation."}
    out=ROOT/"results/v89_data_foundation"; (out/"download_plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    return 3 if ns.execute and items else 0
if __name__=="__main__": raise SystemExit(main())
