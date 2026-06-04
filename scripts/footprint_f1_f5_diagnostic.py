#!/usr/bin/env python3
"""Footprint F1-F5 diagnostic over Binance aggTrades volume bars."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.footprint import FootprintEngine
from prime.footprint_research import FootprintConfig, evaluate_footprint_bar
from prime.ic_harness import iter_binance_research_ticks
from prime.phase1 import SessionExtremeTracker
from prime.nautilus_compat import aggressor_name
from prime.volume_bars import VolumeBarSampler


DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")
DEFAULT_THRESHOLDS = [100.0, 200.0, 300.0]
DEFAULT_HORIZONS = [3, 5, 10]


@dataclass
class MetricAccumulator:
    events: int = 0
    hits: int = 0
    sum_sfr: float = 0.0
    sum_side: float = 0.0
    sum_raw_return: float = 0.0
    sum_side_sq: float = 0.0
    sum_raw_return_sq: float = 0.0
    sum_side_raw_return: float = 0.0

    def add(self, side: int, raw_return: float, signed_forward_return: float) -> None:
        self.events += 1
        if signed_forward_return > 0:
            self.hits += 1
        self.sum_sfr += signed_forward_return
        self.sum_side += side
        self.sum_raw_return += raw_return
        self.sum_side_sq += side * side
        self.sum_raw_return_sq += raw_return * raw_return
        self.sum_side_raw_return += side * raw_return

    def merge(self, other: "MetricAccumulator") -> None:
        self.events += other.events
        self.hits += other.hits
        self.sum_sfr += other.sum_sfr
        self.sum_side += other.sum_side
        self.sum_raw_return += other.sum_raw_return
        self.sum_side_sq += other.sum_side_sq
        self.sum_raw_return_sq += other.sum_raw_return_sq
        self.sum_side_raw_return += other.sum_side_raw_return

    def summary(self) -> dict:
        return {
            "events": self.events,
            "hit_rate": round(self.hits / self.events, 6) if self.events else 0.0,
            "mean_sfr": round(self.sum_sfr / self.events, 8) if self.events else 0.0,
            "ic": round(self._ic(), 6),
        }

    def _ic(self) -> float:
        if self.events < 2:
            return 0.0
        cov = self.sum_side_raw_return - (self.sum_side * self.sum_raw_return / self.events)
        side_var = self.sum_side_sq - (self.sum_side * self.sum_side / self.events)
        return_var = self.sum_raw_return_sq - (
            self.sum_raw_return * self.sum_raw_return / self.events
        )
        if side_var == 0.0 or return_var == 0.0:
            return 0.0
        return cov / (side_var * return_var) ** 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", action="append", dest="archives")
    parser.add_argument("--all-archives", action="store_true", default=False)
    parser.add_argument("--include-special-1m", action="store_true", default=False)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--threshold-btc", type=float, nargs="+", default=DEFAULT_THRESHOLDS)
    parser.add_argument("--horizons", type=int, nargs="+", default=DEFAULT_HORIZONS)
    parser.add_argument("--tick-size", type=float, default=0.5)
    parser.add_argument("--stack-levels", type=int, default=3)
    parser.add_argument("--imbalance-ratio", type=float, default=3.0)
    parser.add_argument("--min-level-total-volume", type=float, default=5.0)
    parser.add_argument("--max-extension-ticks", type=int, default=1)
    parser.add_argument("--absorption-delta-share", type=float, default=0.15)
    parser.add_argument("--volume-floor", type=float, default=50.0)
    parser.add_argument("--structure-tick-radius", type=int, default=2)
    parser.add_argument("--vwap-deviation-pct", type=float, default=0.003)
    parser.add_argument("--session-extreme-pct", type=float, default=0.003)
    parser.add_argument("--output", type=Path, default=Path("footprint_f1_f5_diagnostic.json"))
    parser.add_argument("--progress", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive_paths = select_archives(args)
    aggregate: dict[tuple, MetricAccumulator] = {}
    archives_processed = 0
    rows_seen = 0

    config = FootprintConfig(
        tick_size=args.tick_size,
        stack_levels=args.stack_levels,
        imbalance_ratio=args.imbalance_ratio,
        min_level_total_volume=args.min_level_total_volume,
        max_extension_ticks=args.max_extension_ticks,
        absorption_delta_share=args.absorption_delta_share,
        volume_floor=args.volume_floor,
        structure_tick_radius=args.structure_tick_radius,
        vwap_deviation_pct=args.vwap_deviation_pct,
        session_extreme_pct=args.session_extreme_pct,
    )

    for idx, archive in enumerate(archive_paths, start=1):
        archive_result = process_archive(
            archive=archive,
            thresholds=sorted(args.threshold_btc),
            horizons=sorted(args.horizons),
            max_rows=args.max_rows,
            config=config,
        )
        rows_seen += archive_result["rows_seen"]
        if archive_result["rows_seen"] > 0:
            archives_processed += 1
        for key in sorted(archive_result["accumulators"]):
            aggregate.setdefault(key, MetricAccumulator()).merge(archive_result["accumulators"][key])
        if args.progress:
            print(
                f"processed {idx}/{len(archive_paths)} {archive.name} rows={archive_result['rows_seen']}",
                file=sys.stderr,
            )

    aggregate_rows = rows_from_accumulators(
        aggregate,
        archive="ALL",
        regime_label="ALL",
        stack_levels=args.stack_levels,
    )
    payload = {
        "diagnostic": "footprint_f1_f5",
        "archives_requested": len(archive_paths),
        "archives_processed": archives_processed,
        "rows_seen": rows_seen,
        "threshold_btc": sorted(args.threshold_btc),
        "horizons": sorted(args.horizons),
        "stack_levels": args.stack_levels,
        "imbalance_ratio": args.imbalance_ratio,
        "min_level_total_volume": args.min_level_total_volume,
        "max_extension_ticks": args.max_extension_ticks,
        "absorption_delta_share": args.absorption_delta_share,
        "volume_floor": args.volume_floor,
        "structure_tick_radius": args.structure_tick_radius,
        "vwap_deviation_pct": args.vwap_deviation_pct,
        "session_extreme_pct": args.session_extreme_pct,
        "notes": [
            "Footprint uses level-local aggressive flow from aggTrades only.",
            "F5 requires F1 + F4 + (F2 or F3).",
            "This runner is a research diagnostic, not a trading signal.",
        ],
        "aggregate_state": [state_from_accumulator(key, acc) for key, acc in sorted(aggregate.items())],
        "aggregate_rows": aggregate_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print_summary(aggregate_rows, title="AGGREGATE ALL ARCHIVES")
    print(f"wrote {args.output}")
    return 0


def select_archives(args: argparse.Namespace) -> list[Path]:
    if args.archives:
        archives = sorted(args.dest / name for name in args.archives)
    if args.all_archives:
        archives = sorted(args.dest.glob("BTCUSDT-aggTrades-*.zip"))
        if not args.include_special_1m:
            archives = [archive for archive in archives if "_1m" not in archive.name]
    if not args.archives and not args.all_archives:
        raise SystemExit("provide --archive at least once or use --all-archives")
    if args.shard_count <= 1:
        return archives
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise SystemExit("--shard-index must be in [0, shard-count)")
    return [archive for idx, archive in enumerate(archives) if idx % args.shard_count == args.shard_index]


def process_archive(
    *,
    archive: Path,
    thresholds: list[float],
    horizons: list[int],
    max_rows: int | None,
    config: FootprintConfig,
) -> dict:
    if not archive.is_file():
        return {"rows_seen": 0, "rows": [], "accumulators": {}}

    threshold_state = {
        threshold: {
            "sampler": VolumeBarSampler(threshold),
            "footprint": FootprintEngine(config.tick_size),
            "ticks": [],
            "bars": [],
            "session": SessionExtremeTracker(),
            "vwap_pv": 0.0,
            "vwap_vol": 0.0,
            "last_day_key": None,
        }
        for threshold in thresholds
    }
    rows_seen = 0
    for tick in iter_binance_research_ticks([archive], max_rows=max_rows):
        rows_seen += 1
        day_key = tick.ts_event // 86_400_000_000_000
        for state in threshold_state.values():
            if state["last_day_key"] != day_key:
                state["vwap_pv"] = 0.0
                state["vwap_vol"] = 0.0
                state["last_day_key"] = day_key
            state["session"].update(tick.ts_event, tick.price)
            state["vwap_pv"] += float(tick.price) * float(tick.size)
            state["vwap_vol"] += float(tick.size)
            state["footprint"].update(float(tick.price), float(tick.size), _side_name(tick.aggressor_side))
            state["ticks"].append(tick)
            bar = state["sampler"].update(tick)
            if bar is None:
                continue
            state["bars"].append(bar)
            stage = evaluate_footprint_bar(
                snapshot=state["footprint"].snapshot(),
                bar_high=bar.high,
                bar_low=bar.low,
                bar_close=bar.close,
                session_high=state["session"].session_high,
                session_low=state["session"].session_low,
                vwap=(state["vwap_pv"] / state["vwap_vol"]) if state["vwap_vol"] > 0 else 0.0,
                config=config,
            )
            state["bars"][-1] = {
                "close": bar.close,
                "stage": stage,
            }
            state["footprint"] = FootprintEngine(config.tick_size)
            state["ticks"] = []

    archive_accumulators: dict[tuple, MetricAccumulator] = {}
    for threshold, state in threshold_state.items():
        bars = state["bars"]
        for horizon in horizons:
            _add_stage_samples(archive_accumulators, threshold, horizon, "F1_stacked_imbalance", bars, lambda stage: stage.f1)
            _add_stage_samples(archive_accumulators, threshold, horizon, "F2_rejection_confirm", bars, lambda stage: stage.f2)
            _add_stage_samples(archive_accumulators, threshold, horizon, "F3_absorption", bars, lambda stage: stage.f3)
            _add_stage_samples(archive_accumulators, threshold, horizon, "F4_structure_confluence", bars, lambda stage: stage.f4)
            _add_stage_samples(archive_accumulators, threshold, horizon, "F5_final_gate", bars, lambda stage: stage.f5)
        archive_accumulators.clear()

    # Rebuild archive-level accumulators using all thresholds combined.
    combined: dict[tuple, MetricAccumulator] = {}
    for threshold, state in threshold_state.items():
        bars = state["bars"]
        for horizon in horizons:
            _add_stage_samples(combined, threshold, horizon, "F1_stacked_imbalance", bars, lambda stage: stage.f1)
            _add_stage_samples(combined, threshold, horizon, "F2_rejection_confirm", bars, lambda stage: stage.f2)
            _add_stage_samples(combined, threshold, horizon, "F3_absorption", bars, lambda stage: stage.f3)
            _add_stage_samples(combined, threshold, horizon, "F4_structure_confluence", bars, lambda stage: stage.f4)
            _add_stage_samples(combined, threshold, horizon, "F5_final_gate", bars, lambda stage: stage.f5)

    return {
        "rows_seen": rows_seen,
        "rows": rows_from_accumulators(
            combined,
            archive=archive.name,
            regime_label=regime_label(archive.name),
            stack_levels=config.stack_levels,
        ),
        "accumulators": combined,
    }


def _add_stage_samples(
    accumulators: dict[tuple, MetricAccumulator],
    threshold: float,
    horizon: int,
    stage_name: str,
    bars: list[dict],
    predicate,
) -> None:
    for idx, record in enumerate(bars):
        stage = record["stage"]
        if not predicate(stage) or stage.side == 0:
            continue
        entry = record["close"]
        future_idx = idx + horizon
        if future_idx >= len(bars) or entry == 0.0:
            continue
        future_close = bars[future_idx]["close"]
        raw_return = (future_close - entry) / entry
        signed_forward_return = stage.side * raw_return
        key = (threshold, stage_name, horizon)
        accumulators.setdefault(key, MetricAccumulator()).add(stage.side, raw_return, signed_forward_return)


def rows_from_accumulators(
    accumulators: dict[tuple, MetricAccumulator],
    *,
    archive: str,
    regime_label: str,
    stack_levels: int,
) -> list[dict]:
    rows = []
    for threshold, stage, horizon in sorted(accumulators):
        summary = accumulators[(threshold, stage, horizon)].summary()
        rows.append(
            {
                "archive": archive,
                "regime_label": regime_label,
                "bar_threshold_btc": threshold,
                "stack_levels": stack_levels,
                "stage": stage,
                "horizon_bars": horizon,
                **summary,
            }
        )
    return rows


def state_from_accumulator(key: tuple, acc: MetricAccumulator) -> dict:
    threshold, stage, horizon = key
    return {
        "bar_threshold_btc": threshold,
        "stage": stage,
        "horizon_bars": horizon,
        "events": acc.events,
        "hits": acc.hits,
        "sum_sfr": acc.sum_sfr,
        "sum_side": acc.sum_side,
        "sum_raw_return": acc.sum_raw_return,
        "sum_side_sq": acc.sum_side_sq,
        "sum_raw_return_sq": acc.sum_raw_return_sq,
        "sum_side_raw_return": acc.sum_side_raw_return,
    }


def print_summary(rows: list[dict], *, title: str) -> None:
    print(title)
    print(f"{'thr':>6} {'stage':<24} {'h':>3} {'events':>8} {'hit':>7} {'mean_sfr':>11} {'ic':>8}")
    for row in sorted(rows, key=lambda item: (
        item["bar_threshold_btc"],
        item["stage"],
        item["horizon_bars"],
        item["archive"],
    )):
        print(
            f"{row['bar_threshold_btc']:>6.0f} "
            f"{row['stage']:<24} "
            f"{row['horizon_bars']:>3} "
            f"{row['events']:>8} "
            f"{row['hit_rate']:>7.4f} "
            f"{row['mean_sfr']:>11.8f} "
            f"{row['ic']:>8.4f}"
        )


def regime_label(archive_name: str) -> str:
    if "2022-05-09_1m" in archive_name:
        return "luna_crash_day"
    if "2022-05" in archive_name:
        return "luna_crash_month"
    if "2022-11" in archive_name:
        return "ftx_stress"
    if "2021-10" in archive_name or "2021-11" in archive_name:
        return "bull_trend"
    if "2022-09" in archive_name:
        return "bear_market"
    if "2023-01" in archive_name or "2023-03" in archive_name:
        return "recovery_range"
    return "historical"


def _side_name(side: object) -> str:
    name = aggressor_name(side)
    if name in {"BUYER", "BUY"}:
        return "BUY"
    if name in {"SELLER", "SELL"}:
        return "SELL"
    return "UNKNOWN"


if __name__ == "__main__":
    sys.exit(main())
