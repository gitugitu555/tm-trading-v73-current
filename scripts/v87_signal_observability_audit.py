#!/usr/bin/env python3
"""Replay raw ticks and audit when final volume-bar CVD signals become observable."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prime.ic_harness import iter_binance_research_ticks
from prime.volume_bars import VolumeBar, VolumeBarSampler
from prime.volume_bar_cvd import htf_change_at, htf_flat_abs_threshold, volume_bar_cvd_signal
from research.v87_execution import PARTIAL_THRESHOLDS, classify_partial_predictions, partial_signal
from research.v86_recovery import write_manifest
from storage.hot_path import hot_btcusdt_aggtrades_dir

OUT = ROOT / "results/v87_execution_rescue/signal_observability"


def replay_archive(archive: Path, *, threshold_btc: float, lookback: int, horizon: int, max_rows: int | None) -> tuple[list[dict], int]:
    sampler = VolumeBarSampler(threshold_btc)
    bars: list[VolumeBar] = []
    partials: list[dict[float, dict]] = []
    current: dict[float, dict] = {}
    next_threshold_index = 0
    for tick in iter_binance_research_ticks([archive], max_rows=max_rows):
        bar = sampler.update(tick)
        if bar is None:
            while next_threshold_index < len(PARTIAL_THRESHOLDS) and sampler.progress >= PARTIAL_THRESHOLDS[next_threshold_index]:
                fraction = PARTIAL_THRESHOLDS[next_threshold_index]
                snap = sampler.partial_snapshot()
                if snap is not None:
                    current[fraction] = {"bar": snap, "price": snap.close, "ts_ns": snap.end_ts_ns, "ticks": snap.ticks}
                next_threshold_index += 1
            continue
        # A large final tick can cross thresholds and emit immediately.
        for fraction in PARTIAL_THRESHOLDS:
            current.setdefault(fraction, {"bar": bar, "price": bar.close, "ts_ns": bar.end_ts_ns, "ticks": bar.ticks})
        bars.append(bar)
        partials.append(current)
        current = {}
        next_threshold_index = 0

    events = []
    abs_changes: list[float] = []
    for idx, bar in enumerate(bars):
        htf_change = htf_change_at(bars[: idx + 1], bar.end_ts_ns, bar.cumulative_delta)
        flat_abs = htf_flat_abs_threshold(abs_changes, quantile=0.25)
        abs_changes.append(abs(htf_change))
        if idx < lookback or idx + horizon >= len(bars):
            continue
        final = volume_bar_cvd_signal(
            bars[: idx + 1], lookback_bars=lookback, htf_change=htf_change,
            flat_abs=flat_abs, timestamp_ns=bar.end_ts_ns, price=bar.close,
        )
        for fraction, snapshot in sorted(partials[idx].items()):
            partial_htf_change = htf_change_at(bars[:idx], snapshot["bar"].end_ts_ns, snapshot["bar"].cumulative_delta)
            partial = partial_signal(
                bars[max(0, idx - lookback):idx],
                snapshot["bar"],
                lookback_bars=lookback,
                htf_change=partial_htf_change,
                flat_abs=flat_abs,
            )
            side = int(partial["side"]) if partial else None
            final_side = int(final["side"]) if final else None
            horizon_bar = bars[idx + horizon]
            signed_return = side * (horizon_bar.close - snapshot["price"]) / snapshot["price"] if side else 0.0
            events.append(
                {
                    "archive": archive.name,
                    "bar_index": idx,
                    "partial_fraction": fraction,
                    "partial_price": snapshot["price"],
                    "partial_ts_ns": snapshot["ts_ns"],
                    "partial_ticks": snapshot["ticks"],
                    "partial_volume": snapshot["bar"].volume,
                    "partial_delta": snapshot["bar"].delta,
                    "partial_cvd": snapshot["bar"].cumulative_delta,
                    "partial_high": snapshot["bar"].high,
                    "partial_low": snapshot["bar"].low,
                    "partial_signal": partial is not None,
                    "partial_side": side,
                    "partial_strength": partial["strength"] if partial else None,
                    "final_signal": final is not None,
                    "final_side": final_side,
                    "final_strength": final["strength"] if final else None,
                    "signal_id": final["id"] if final else None,
                    "lag0_close": bar.close,
                    "lag0_close_ts_ns": bar.end_ts_ns,
                    "lag1_open": bars[idx + 1].open,
                    "lag1_open_ts_ns": bars[idx + 1].start_ts_ns,
                    "lag1_close": bars[idx + 1].close,
                    "lag1_close_ts_ns": bars[idx + 1].end_ts_ns,
                    "lag2_open": bars[idx + 2].open if idx + 2 < len(bars) else None,
                    "lag2_open_ts_ns": bars[idx + 2].start_ts_ns if idx + 2 < len(bars) else None,
                    "horizon_exit_price": horizon_bar.close,
                    "horizon_exit_ts_ns": horizon_bar.end_ts_ns,
                    "signed_forward_return": signed_return,
                    "ticks_after_partial": bar.ticks - snapshot["ticks"],
                    "time_after_partial_ns": bar.end_ts_ns - snapshot["ts_ns"],
                }
            )
    return events, len(bars)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="append")
    parser.add_argument("--threshold-btc", type=float, default=300)
    parser.add_argument("--lookback", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--max-rows", type=int)
    ns = parser.parse_args()
    dest = hot_btcusdt_aggtrades_dir()
    names = ns.archive or ["BTCUSDT-aggTrades-2026-05-21.zip"]
    all_events = []
    bar_counts = {}
    for name in names:
        events, bar_count = replay_archive(dest / name, threshold_btc=ns.threshold_btc, lookback=ns.lookback, horizon=ns.horizon, max_rows=ns.max_rows)
        all_events.extend(events)
        bar_counts[name] = bar_count
    OUT.mkdir(parents=True, exist_ok=True)
    events_path = OUT / "partial_signal_events.jsonl"
    with events_path.open("w", encoding="utf-8") as handle:
        for event in all_events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    report = {
        "scope": "raw-tick partial-bar signal observability diagnostic",
        "archives": names,
        "events": len(all_events),
        "completed_bar_counts": bar_counts,
        "minimum_bars_for_eligible_observation": ns.lookback + ns.horizon + 1,
        "by_partial_threshold": classify_partial_predictions(all_events),
        "limitations": ["Trade-only aggTrades cannot measure spread, queue imbalance, maker fill probability, or true microprice."],
    }
    (OUT / "observability_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(
        output_path=OUT / "manifest.json",
        strategy_label="v87_signal_observability_audit",
        strategy_description="raw-tick partial volume-bar signal observability",
        repo_root=ROOT,
        runner_script="scripts/v87_signal_observability_audit.py",
        cli_args=[
            "--threshold-btc", str(ns.threshold_btc), "--lookback", str(ns.lookback),
            "--horizon", str(ns.horizon), *sum((["--archive", name] for name in names), []),
        ],
        archives=[dest / name for name in names],
        execution_model={
            "entry_lag_bars": None, "fee_bps_per_side": None, "slippage_bps_per_side": None,
            "entry_price_rule": "diagnostic only", "exit_price_rule": f"{ns.horizon}-bar close",
            "stop_fill_rule": "not applicable",
        },
        position_model={"starting_equity": None, "base_position_pct": None, "compounding": False},
        feature_flags={"partial_bar_observability": True, "uses_l2": False},
    )
    doc = ROOT / "docs/v87_execution_rescue/02_signal_observability_audit.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Signal Observability Audit\n\nRaw-tick partial-bar results are in `results/v87_execution_rescue/signal_observability/observability_summary.json`.\n\nThis audit evaluates only information observable at each replayed tick. L2-dependent features are unavailable in aggTrades.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
