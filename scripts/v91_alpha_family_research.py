#!/usr/bin/env python3
"""Probe the main V9.1 alpha families on the verified catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

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
    families = {
        "family_a_cvd_continuation": (
            lambda df: (df["cvd_slope_5"] > df["cvd_slope_5"].rolling(50, min_periods=10).median().fillna(0)) & (df["cvd_accel_3_10"] > 0) & (df["price_cvd_alignment_strength"] > df["price_cvd_alignment_strength"].median()) & (df["session_label"] != "overnight"),
            1,
        ),
        "family_b_failed_impulse_reversal": (
            lambda df: (df["failed_buy_impulse_score"] > 0) | (df["failed_sell_impulse_score"] > 0),
            -1,
        ),
        "family_c_regime_divergence": (
            lambda df: (df["old_divergence_signal"] != 0) & (df["volatility_regime"] == "mid") & (df["trend_strength"] < df["trend_strength"].median()),
            1,
        ),
        "family_d_mfe_classifier": (
            lambda df: (df["absorption_score"] > df["absorption_score"].median()) & (df["continuation_setup_score"] > df["continuation_setup_score"].median()),
            1,
        ),
    }
    outputs = {}
    for family_name, (rule, side) in families.items():
        signals = build_candidate_signals(features, rule, side=side)
        policy = {"name": f"{family_name}_policy", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25}
        replay = replay_candidates(bars, signals, policy)
        outputs[family_name] = {
            "signal_count": len(signals),
            "summary": replay["summary"],
            "by_year": replay["by_year"],
            "recommendation": "candidate" if len(signals) >= 500 and replay["summary"]["net_expectancy"] > 0 and replay["summary"]["profit_factor"] > 1.05 else "reject",
        }
    out = ROOT / "results/v91_alpha_discovery/alpha_families"
    out.mkdir(parents=True, exist_ok=True)
    (out / "alpha_families.json").write_text(json.dumps(outputs, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v91_alpha_discovery/04_alpha_family_research.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Alpha Family Research\n\n"
        "This report evaluates continuation, failed-impulse, regime-divergence, and MFE-classifier families on the verified catalog.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
