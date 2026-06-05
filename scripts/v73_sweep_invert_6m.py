#!/usr/bin/env python3
"""Focused 6m sweep: invert-signal + gates-off (best path to higher WR)."""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.v73_sweep_6m import STOP_PCT, SweepConfig, run_config

def main() -> int:
    configs: list[SweepConfig] = []
    for t in [0.001, 0.0015, 0.002, 0.0025, 0.003]:
        for lb in [80, 100, 120, 150]:
            for e in [5, 8, 12, 15]:
                configs.append(
                    SweepConfig(
                        name=f"inv_t{t}_lb{lb}_e{e}",
                        invert=True,
                        regime_gate=False,
                        footprint=False,
                        auction_gate=False,
                        target_pct=t,
                        exit_bars=e,
                        lookback=lb,
                    )
                )
    # Footprint invert stacks on best region
    for t, lb, e in [(0.0015, 100, 12), (0.002, 100, 12)]:
        configs.append(
            SweepConfig(
                name=f"inv_fp_{t}",
                invert=True,
                regime_gate=False,
                auction_gate=False,
                footprint=True,
                target_pct=t,
                exit_bars=e,
                lookback=lb,
                extra=["--footprint-invert-for-fade", "--no-footprint-allow-neutral"],
            )
        )

    out = ROOT / "results/v73_sweep_invert_6m.jsonl"
    results = []
    for i, c in enumerate(configs, 1):
        r = run_config(c)
        results.append(r)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
        mark = " ***" if r.get("win_rate", 0) >= 0.70 else ""
        print(f"[{i}/{len(configs)}] {c.name} wr={r.get('win_rate')} trades={r.get('total_trades')}{mark}", flush=True)

    results.sort(key=lambda x: (-x.get("win_rate", 0), -x.get("total_trades", 0)))
    summary = {
        "stop_pct": STOP_PCT,
        "best": results[0] if results else None,
        "top_10": results[:10],
        "count_70_plus": sum(1 for r in results if r.get("win_rate", 0) >= 0.70),
    }
    (ROOT / "results/v73_sweep_invert_6m_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["count_70_plus"] else 1


if __name__ == "__main__":
    sys.exit(main())