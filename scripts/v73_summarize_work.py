#!/usr/bin/env python3
"""Summarize partial or complete v73_backtest_6y_work results."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "results/v73_backtest_6y_work"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", type=Path, default=WORK)
    p.add_argument("--output", type=Path, default=ROOT / "results/v73_partial_summary.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    reports = sorted(args.work_dir.glob("*.report.json"))
    if not reports:
        print("No report files found.")
        return 1

    trades = 0
    wins = 0
    pnl = 0.0
    signal_hits = 0
    signal_scored = 0
    exit_reasons: Counter[str] = Counter()
    per_archive: list[dict] = []

    for path in reports:
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload.get("report", payload)
        t = int(report.get("trades", 0))
        wr = float(report.get("win_rate", 0.0))
        trades += t
        wins += int(round(wr * t)) if t else 0
        pnl += float(report.get("total_pnl", 0.0))
        exit_reasons.update(report.get("exit_reasons", {}))
        sc = report.get("signal_scorecard") or {}
        se = int(sc.get("scored_events", 0))
        if se:
            signal_hits += int(round(float(sc.get("hit_rate", 0.0)) * se))
            signal_scored += se
        per_archive.append(
            {
                "archive": payload.get("archive", path.name.replace(".report.json", "")),
                "trades": t,
                "win_rate": wr,
                "total_pnl": report.get("total_pnl"),
                "signal_hit_rate": sc.get("hit_rate"),
            }
        )

    summary = {
        "archives": len(reports),
        "trades": trades,
        "trade_win_rate": round(wins / trades, 4) if trades else 0.0,
        "total_pnl": round(pnl, 2),
        "signal_hit_rate": round(signal_hits / signal_scored, 4) if signal_scored else None,
        "signal_scored_events": signal_scored,
        "exit_reasons": dict(sorted(exit_reasons.items())),
        "per_archive": per_archive[-10:],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())