#!/usr/bin/env python3
"""Summarize V8.4 promotion evidence from full six-year artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.promotion_summary import build_promotion_summary, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-report",
        type=Path,
        default=ROOT / "results/v84_full_replay.json",
        help="Baseline six-year report to summarize",
    )
    parser.add_argument(
        "--candidate-report",
        type=Path,
        default=ROOT / "results/v84_full_shadow.json",
        help="Optional candidate / shadow report to compare against baseline",
    )
    parser.add_argument(
        "--trade-path-db",
        type=Path,
        default=ROOT / "results/v73_trade_path_db.jsonl",
        help="Trade-path JSONL database",
    )
    parser.add_argument(
        "--mae-mfe-report",
        type=Path,
        default=ROOT / "results/v73_mae_mfe_report.json",
        help="Aggregated MAE/MFE report",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/v84_promotion_summary.json",
        help="Write JSON summary here",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline = load_json(args.baseline_report)
    mae_mfe = load_json(args.mae_mfe_report)
    candidate = load_json(args.candidate_report) if args.candidate_report.is_file() else None

    summary = build_promotion_summary(
        baseline_report=baseline,
        trade_path_db_path=args.trade_path_db,
        mae_mfe_report=mae_mfe,
        candidate_report=candidate,
    )
    payload = {
        "baseline_report": str(args.baseline_report),
        "candidate_report": str(args.candidate_report) if candidate is not None else None,
        "trade_path_db": str(args.trade_path_db),
        "mae_mfe_report": str(args.mae_mfe_report),
        "summary": summary,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
