#!/usr/bin/env python3
"""Run staged V8.8 policies over the verified full-range catalog."""

from __future__ import annotations
import itertools,json,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from research.v86_recovery import load_jsonl,write_jsonl
from research.v88_policy_replay import replay_policy

def main()->int:
    signals=load_jsonl(ROOT/"results/v89_data_foundation/verified_signal_ledger/immutable_signal_ledger.jsonl")
    paths={p["signal_id"]:p for p in load_jsonl(ROOT/"results/v89_data_foundation/verified_trade_paths/trade_paths.jsonl")}
    policies=[]
    for t,s,b in itertools.product((.0025,.005,.0075),(.005,.01,.03),(8,16,24,48,72)): policies.append({"name":f"fixed_t{t}_s{s}_b{b}","target_pct":t,"stop_pct":s,"bar_exit":b})
    for trigger,lock in itertools.product((.001,.002,.0035,.005),(0,.0005,.001)): policies.append({"name":f"be_{trigger}_{lock}","target_pct":.005,"stop_pct":.03,"bar_exit":24,"breakeven_trigger_mfe_pct":trigger,"breakeven_lock_pct":lock})
    for start,give in itertools.product((.002,.0035,.005),(.25,.5,.66)): policies.append({"name":f"trail_{start}_{give}","target_pct":.01,"stop_pct":.03,"bar_exit":48,"trail_start_mfe_pct":start,"trail_giveback_pct":give})
    results={}
    for p in policies:
        r=replay_policy(signals,paths,p,occupancy_mode="independent"); results[p["name"]]={"policy":p,**{k:v for k,v in r.items() if k!="trades"}}
    ranked=sorted(results,key=lambda n:results[n]["summary"]["net_expectancy"],reverse=True); best=replay_policy(signals,paths,results[ranked[0]]["policy"],occupancy_mode="independent")
    by_year=defaultdict(list)
    for trade in best["trades"]: by_year[str(datetime.fromtimestamp(int(trade["signal_ts_ns"])/1e9,tz=timezone.utc).year)].append(float(trade["net_return_pct"]))
    payload={"tested_policy_count":len(results),"ranked":ranked,"results":results,"best_by_year":{year:{"trades":len(vals),"net_expectancy":sum(vals)/len(vals)} for year,vals in sorted(by_year.items())}}
    out=ROOT/"results/v89_data_foundation/v88_verified_replay"; out.mkdir(parents=True,exist_ok=True); (out/"policy_summary.json").write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8"); write_jsonl(out/"best_policy_trades.jsonl",best["trades"])
    return 0
if __name__=="__main__": raise SystemExit(main())
