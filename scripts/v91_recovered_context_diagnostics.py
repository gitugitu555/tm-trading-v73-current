#!/usr/bin/env python3
"""Build recovered-context diagnostics from the verified six-year catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v89_volume_bar_builder import load_verified_catalog
from research.v91_recovered_context import build_context_events, context_report, event_metrics, replay_exits


def main() -> int:
    catalog = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    manifest_path = catalog.with_name("manifest.json")
    bars = load_verified_catalog(catalog)
    events = build_context_events(bars)
    report = {
        "purpose": "Recovered guide concepts evaluated as research features, never live rules.",
        "catalog": json.loads(manifest_path.read_text(encoding="utf-8")),
        "config": {
            "signal": "D4 past-only rolling HTF",
            "lookback_bars": 40,
            "signal_horizon_bars": 5,
            "exit_entry": "next_volume_bar_open",
            "roundtrip_cost_bps": 12,
        },
        "overall_signal": {
            period: event_metrics([event for event in events if period == "all" or event["period"] == period])
            for period in ("all", "2020-2023", "2024-2026")
        },
        "contexts": context_report(events),
        "derivatives_context": {
            field: {"status": "unavailable", "reason": "No timestamp-aligned historical derivatives source in verified spot aggTrades catalog."}
            for field in ("open_interest", "funding", "liquidation_cascade", "whale_aggressive_flow")
        },
        "exit_research": replay_exits(events, bars),
        "hard_rules": [
            "No AI decision-making or confluence score.",
            "All context features use current or completed prior observations only.",
            "Support/resistance uses prior rolling extrema, not future-confirmed swings.",
            "Exit replay enters at next volume-bar open, never signal-bar close.",
            "Unavailable derivatives fields are not synthesized from aggTrades.",
        ],
    }
    output = ROOT / "results/v91_alpha_discovery/recovered_context/recovered_context_diagnostics.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(report, ROOT / "docs/v91_alpha_discovery/08_recovered_context_diagnostics.md")
    print(f"events={len(events)} wrote {output}")
    return 0


def write_markdown(report: dict, path: Path) -> None:
    overall = report["overall_signal"]
    lines = [
        "# V9.1 Recovered-Context Diagnostics",
        "",
        "Guide concepts were evaluated only as isolated research features. No AI decision, arbitrary score, or live rule was used.",
        "",
        "## Method",
        "",
        "- D4 uses the verified 300 BTC catalog, 40-bar lookback, and past-only rolling HTF threshold.",
        "- Structure uses the slope of the prior 40 completed volume bars; support/resistance uses prior 100-bar extrema within 0.3%.",
        "- MTF biases use EMA20 on completed 15m, 1h, 4h, and daily buckets.",
        "- Volume profile uses 50 bins over the prior 100 completed bars.",
        "- Exit research enters at the next volume-bar open and applies 12 bps round-trip cost.",
        "- Exit variants are fixed 0.6%/0.3% TP/SL, first adverse CVD bar, 24-bar time exit, fixed-entry profile levels, trailing after 0.5% MFE, and 50% partial at 0.3%.",
        "",
        "## Overall D4 Decay",
        "",
        "| Period | Events | Hit Rate | Mean SFR | IC | T-stat | Cost-adjusted expectancy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for period in ("all", "2020-2023", "2024-2026"):
        row = overall[period]
        lines.append(f"| {period} | {row['events']:,} | {row['hit_rate']:.2%} | {row['mean_signed_return_bps']:.3f} bps | {row['ic']:.4f} | {row['t_stat']:.2f} | {row['cost_adjusted_expectancy_bps']:.3f} bps |")
    lines.extend(["", "## Context Buckets", ""])
    for dimension, buckets in report["contexts"].items():
        lines.extend([f"### {dimension.replace('_', ' ').title()}", "", "| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for bucket, periods in buckets.items():
            all_row, old, recent = periods["all"], periods["2020-2023"], periods["2024-2026"]
            lines.append(f"| {bucket} | {all_row['events']:,} | {all_row['hit_rate']:.2%} | {all_row['mean_signed_return_bps']:.3f} | {all_row['ic']:.4f} | {all_row['t_stat']:.2f} | {all_row['sharpe']:.3f} | {all_row['sortino']:.3f} | {all_row['max_drawdown']:.2%} | {old['mean_signed_return_bps']:.3f} | {recent['mean_signed_return_bps']:.3f} | {all_row['cost_adjusted_expectancy_bps']:.3f} |")
        lines.append("")
    lines.extend(["## Derivatives Context", "", "OI, funding, liquidation cascades, and whale flow are unavailable in the verified spot aggTrades catalog. They were not approximated.", "", "## Exit Research", "", "| Exit | Events | Net expectancy | IC | T-stat | Sharpe | Sortino | Max DD | 2024-26 expectancy |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for policy, periods in report["exit_research"].items():
        row, recent = periods["all"], periods["2024-2026"]
        lines.append(f"| {policy} | {row['events']:,} | {row['cost_adjusted_expectancy_bps']:.3f} bps | {row['ic']:.4f} | {row['t_stat']:.2f} | {row['sharpe']:.3f} | {row['sortino']:.3f} | {row['max_drawdown']:.2%} | {recent['cost_adjusted_expectancy_bps']:.3f} bps |")
    lines.extend([
        "",
        "## Decision",
        "",
        "- Completed-timeframe alignment is the strongest recovered feature, but its gross mean falls from 6.739 bps in 2020-2023 to 0.306 bps across only 92 recent events.",
        "- Near-support and near-resistance rules do not improve the full-sample D4 signal; no-key-level events performed better.",
        "- Below-POC and below-VAL contexts retain some gross structure, but neither clears explicit costs.",
        "- Every tested exit remains negative after 12 bps round-trip cost.",
        "- No bucket or exit is promoted from this full-sample diagnostic. Derivatives-context work requires a separately verified, timestamp-aligned historical dataset.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
