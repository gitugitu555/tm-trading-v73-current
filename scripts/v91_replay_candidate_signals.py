#!/usr/bin/env python3
"""Replay V9.1 candidate signals through the existing TPSL engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v89_volume_bar_builder import load_verified_catalog
from research.v91_features import build_extended_feature_ledger
from research.v91_scan import build_candidate_signals
from research.v91_replay import replay_candidates


def main() -> int:
    catalog_path = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    bars = load_verified_catalog(catalog_path)
    features, _ = build_extended_feature_ledger(catalog_path)
    candidates = {
        "absorption_long": (lambda df: df["failed_sell_impulse_score"] > 0, 1),
        "absorption_short": (lambda df: df["failed_buy_impulse_score"] > 0, -1),
        "continuation_long": (lambda df: (df["cvd_slope_5"] > 0) & (df["price_cvd_alignment"] > 0), 1),
        "mfe_classifier": (lambda df: (df["absorption_score"] > df["absorption_score"].median()) & (df["continuation_setup_score"] > df["continuation_setup_score"].median()), 1),
    }
    policy = {"name": "v91_candidate_policy", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25}
    results = {}
    for candidate_id, (rule, side) in candidates.items():
        signals = build_candidate_signals(features, rule, side=side)
        replay = replay_candidates(bars, signals, policy)
        summary = replay["summary"]
        results[candidate_id] = {
            "candidate_id": candidate_id,
            "family": candidate_id.split("_")[0],
            "signal_count": len(signals),
            "test_expectancy": summary["net_expectancy"],
            "test_profit_factor": summary["profit_factor"],
            "positive_test_split_rate": float(sum(v["expectancy"] > 0 for v in replay["by_year"].values()) / len(replay["by_year"])) if replay["by_year"] else 0.0,
            "sharpe": summary["sharpe"],
            "max_drawdown": summary["max_drawdown"],
            "cost_breakeven_bps": 0.0,
            "recommendation": "candidate" if len(signals) >= 500 and summary["net_expectancy"] > 0 and summary["profit_factor"] > 1.05 else "reject",
        }
    out = ROOT / "results/v91_alpha_discovery/candidate_replay"
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate_replay.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v91_alpha_discovery/06_candidate_replay.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Candidate Replay\n\n"
        "Candidate signals are replayed through the existing TPSL engine under explicit-cost accounting.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
