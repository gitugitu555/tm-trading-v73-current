#!/usr/bin/env python3
"""Volume-bar CVD divergence diagnostic with compact aggregate output."""

from __future__ import annotations

import argparse
from bisect import bisect_left
from dataclasses import dataclass
import json
from math import sqrt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prime.ic_harness import iter_binance_research_ticks
from prime.volume_bar_cache import load_cached_bars, write_cached_bars
from prime.volume_bars import VolumeBar, VolumeBarSampler


DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")
DEFAULT_THRESHOLDS = [100.0, 200.0, 300.0]
DEFAULT_LOOKBACKS = [20, 30, 40]
DEFAULT_HORIZONS = [3, 5, 10]
STAGES = [
    "D1_divergence",
    "D2_delta_rev_2",
    "D3_delta_rev_3",
    "D4_htf",
    "D5_delta_rev_2_htf",
]


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
        return cov / sqrt(side_var * return_var)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", action="append", dest="archives")
    parser.add_argument("--all-archives", action="store_true", default=False)
    parser.add_argument("--include-special-1m", action="store_true", default=False)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--threshold-btc", type=float, nargs="+", default=DEFAULT_THRESHOLDS)
    parser.add_argument("--lookback-bars", type=int, nargs="+", default=DEFAULT_LOOKBACKS)
    parser.add_argument("--horizons", type=int, nargs="+", default=DEFAULT_HORIZONS)
    parser.add_argument("--htf-flat-quantile", type=float, default=0.25)
    parser.add_argument("--output", type=Path, default=Path("volume_bar_cvd_diagnostic.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path("results/volume_bar_cvd_cache"))
    parser.add_argument("--no-cache", action="store_true", default=False)
    parser.add_argument("--print-archive-rows", action="store_true", default=False)
    parser.add_argument("--progress", action="store_true", default=False)
    parser.add_argument("--checkpoint", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive_paths = select_archives(args)
    aggregate: dict[tuple, MetricAccumulator] = {}
    archive_rows: list[dict] = []
    archives_processed = 0
    rows_seen = 0

    for idx, archive in enumerate(archive_paths, start=1):
        archive_result = process_archive(
            archive=archive,
            thresholds=sorted(args.threshold_btc),
            lookbacks=sorted(args.lookback_bars),
            horizons=sorted(args.horizons),
            max_rows=args.max_rows,
            htf_flat_quantile=args.htf_flat_quantile,
            cache_dir=args.cache_dir,
            use_cache=not args.no_cache,
        )
        rows_seen += archive_result["rows_seen"]
        if archive_result["rows_seen"] > 0:
            archives_processed += 1
        for row in archive_result["rows"]:
            archive_rows.append(row)
        for key in sorted(archive_result["accumulators"]):
            acc = aggregate.setdefault(key, MetricAccumulator())
            acc.merge(archive_result["accumulators"][key])
        if args.progress:
            cache_state = "cache" if archive_result.get("cache_hit") else "raw"
            print(
                f"processed {idx}/{len(archive_paths)} {archive.name} rows={archive_result['rows_seen']} {cache_state}",
                file=sys.stderr,
            )
        if args.checkpoint:
            write_checkpoint(
                args.output.with_suffix(".progress.json"),
                archive_paths=archive_paths,
                archive_index=idx,
                archives_processed=archives_processed,
                rows_seen=rows_seen,
                aggregate=aggregate,
            )

    aggregate_rows = rows_from_accumulators(aggregate, archive="ALL", regime_label="ALL")
    payload = {
        "diagnostic": "volume_bar_cvd",
        "archives_requested": len(archive_paths),
        "archives_processed": archives_processed,
        "rows_seen": rows_seen,
        "threshold_btc": sorted(args.threshold_btc),
        "lookback_bars": sorted(args.lookback_bars),
        "horizons": sorted(args.horizons),
        "htf_flat_quantile": args.htf_flat_quantile,
        "notes": [
            "Full-history archive selection excludes *_1m.zip by default to avoid double counting special extracts.",
            "2022-05-09_1m is a single-day Luna crash stress archive and should not be treated as representative alone.",
            "signed_forward_return = side * raw_forward_return; positive means price moved in predicted direction.",
        ],
        "aggregate_rows": aggregate_rows,
        "archive_rows": archive_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))

    print_summary(aggregate_rows, title="AGGREGATE ALL ARCHIVES")
    if args.print_archive_rows:
        print_summary(archive_rows, title="PER ARCHIVE")
    print(f"wrote {args.output}")
    return 0


def select_archives(args: argparse.Namespace) -> list[Path]:
    if args.archives:
        return sorted(args.dest / name for name in args.archives)
    if args.all_archives:
        archives = sorted(args.dest.glob("BTCUSDT-aggTrades-*.zip"))
        if not args.include_special_1m:
            archives = [archive for archive in archives if "_1m" not in archive.name]
        return archives
    raise SystemExit("provide --archive at least once or use --all-archives")


def process_archive(
    *,
    archive: Path,
    thresholds: list[float],
    lookbacks: list[int],
    horizons: list[int],
    max_rows: int | None,
    htf_flat_quantile: float,
    cache_dir: Path,
    use_cache: bool,
) -> dict:
    if not archive.is_file():
        return {"rows_seen": 0, "rows": [], "samples": {}}

    if use_cache and max_rows is None:
        cached = load_cached_bars(cache_dir, archive, thresholds)
        if cached is not None:
            archive_accumulators: dict[tuple, MetricAccumulator] = {}
            for threshold in sorted(cached["bars_by_threshold"]):
                analyze_bars(
                    bars=cached["bars_by_threshold"][threshold],
                    threshold=threshold,
                    lookbacks=lookbacks,
                    horizons=horizons,
                    htf_flat_quantile=htf_flat_quantile,
                    accumulators=archive_accumulators,
                )
            return {
                "rows_seen": cached["rows_seen"],
                "rows": rows_from_accumulators(
                    archive_accumulators,
                    archive=archive.name,
                    regime_label=regime_label(archive.name),
                ),
                "accumulators": archive_accumulators,
                "cache_hit": True,
            }

    samplers = {threshold: VolumeBarSampler(threshold) for threshold in thresholds}
    bars_by_threshold: dict[float, list[VolumeBar]] = {threshold: [] for threshold in thresholds}
    rows_seen = 0

    for tick in iter_binance_research_ticks([archive], max_rows=max_rows):
        rows_seen += 1
        for threshold in sorted(samplers):
            bar = samplers[threshold].update(tick)
            if bar is not None:
                bars_by_threshold[threshold].append(bar)

    archive_accumulators: dict[tuple, MetricAccumulator] = {}
    for threshold in sorted(bars_by_threshold):
        analyze_bars(
            bars=bars_by_threshold[threshold],
            threshold=threshold,
            lookbacks=lookbacks,
            horizons=horizons,
            htf_flat_quantile=htf_flat_quantile,
            accumulators=archive_accumulators,
        )
    if use_cache and max_rows is None:
        write_cached_bars(cache_dir, archive, thresholds, rows_seen, bars_by_threshold)
    return {
        "rows_seen": rows_seen,
        "rows": rows_from_accumulators(
            archive_accumulators,
            archive=archive.name,
            regime_label=regime_label(archive.name),
        ),
        "accumulators": archive_accumulators,
        "cache_hit": False,
    }


def write_checkpoint(
    output: Path,
    *,
    archive_paths: list[Path],
    archive_index: int,
    archives_processed: int,
    rows_seen: int,
    aggregate: dict[tuple, MetricAccumulator],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "archive_index": archive_index,
        "archives_requested": len(archive_paths),
        "archives_processed": archives_processed,
        "last_archive": archive_paths[archive_index - 1].name,
        "rows_seen": rows_seen,
        "aggregate_rows": rows_from_accumulators(aggregate, archive="PARTIAL", regime_label="PARTIAL"),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True))


def analyze_bars(
    *,
    bars: list[VolumeBar],
    threshold: float,
    lookbacks: list[int],
    horizons: list[int],
    htf_flat_quantile: float,
    accumulators: dict[tuple, MetricAccumulator],
) -> None:
    if not bars:
        return
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    closes = [bar.close for bar in bars]
    deltas = [bar.delta for bar in bars]
    cvds = [bar.cumulative_delta for bar in bars]
    timestamps = [bar.end_ts_ns for bar in bars]
    htf_changes = one_hour_cvd_changes(timestamps, cvds)
    htf_flat_abs = quantile([abs(change) for change in htf_changes], htf_flat_quantile)

    max_horizon = max(horizons)
    for lookback in sorted(lookbacks):
        if len(bars) <= lookback + max_horizon:
            continue
        for idx in range(lookback, len(bars) - max_horizon):
            prior_high = max(highs[idx - lookback : idx])
            prior_low = min(lows[idx - lookback : idx])
            prior_cvd_high = max(cvds[idx - lookback : idx])
            prior_cvd_low = min(cvds[idx - lookback : idx])
            bearish = highs[idx] >= prior_high and cvds[idx] < prior_cvd_high
            bullish = lows[idx] <= prior_low and cvds[idx] > prior_cvd_low
            if bearish == bullish:
                continue
            side = -1 if bearish else +1
            add_event_samples(accumulators, threshold, lookback, "D1_divergence", idx, side, closes, horizons)

            if htf_allows(side, htf_changes[idx], htf_flat_abs):
                add_event_samples(accumulators, threshold, lookback, "D4_htf", idx, side, closes, horizons)

            rev2_idx = delta_reversal_index(idx, side, 2, deltas)
            if rev2_idx is not None:
                add_event_samples(
                    accumulators,
                    threshold,
                    lookback,
                    "D2_delta_rev_2",
                    rev2_idx,
                    side,
                    closes,
                    horizons,
                )
                if htf_allows(side, htf_changes[rev2_idx], htf_flat_abs):
                    add_event_samples(
                        accumulators,
                        threshold,
                        lookback,
                        "D5_delta_rev_2_htf",
                        rev2_idx,
                        side,
                        closes,
                        horizons,
                    )

            rev3_idx = delta_reversal_index(idx, side, 3, deltas)
            if rev3_idx is not None:
                add_event_samples(
                    accumulators,
                    threshold,
                    lookback,
                    "D3_delta_rev_3",
                    rev3_idx,
                    side,
                    closes,
                    horizons,
                )


def add_event_samples(
    accumulators: dict[tuple, MetricAccumulator],
    threshold: float,
    lookback: int,
    stage: str,
    idx: int,
    side: int,
    closes: list[float],
    horizons: list[int],
) -> None:
    entry = closes[idx]
    if entry == 0.0:
        return
    for horizon in sorted(horizons):
        future_idx = idx + horizon
        if future_idx >= len(closes):
            continue
        raw_return = (closes[future_idx] - entry) / entry
        signed_forward_return = side * raw_return
        key = (threshold, lookback, stage, horizon)
        accumulators.setdefault(key, MetricAccumulator()).add(side, raw_return, signed_forward_return)


def delta_reversal_index(idx: int, side: int, bars_required: int, deltas: list[float]) -> int | None:
    end = idx + bars_required
    if end >= len(deltas):
        return None
    for rev_idx in range(idx + 1, end + 1):
        if side == -1 and deltas[rev_idx] >= 0:
            return None
        if side == +1 and deltas[rev_idx] <= 0:
            return None
    return end


def one_hour_cvd_changes(timestamps: list[int], cvds: list[float]) -> list[float]:
    hour_ns = 3_600_000_000_000
    changes = []
    for idx, ts in enumerate(timestamps):
        prior_idx = bisect_left(timestamps, ts - hour_ns)
        changes.append(cvds[idx] - cvds[prior_idx])
    return changes


def htf_allows(side: int, htf_change: float, flat_abs: float) -> bool:
    if side == -1:
        return htf_change <= flat_abs
    return htf_change >= -flat_abs


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    clamped = min(max(q, 0.0), 1.0)
    sorted_values = sorted(values)
    idx = int((len(sorted_values) - 1) * clamped)
    return sorted_values[idx]


def rows_from_accumulators(
    accumulators: dict[tuple, MetricAccumulator],
    *,
    archive: str,
    regime_label: str,
) -> list[dict]:
    rows = []
    for threshold, lookback, stage, horizon in sorted(accumulators):
        summary = accumulators[(threshold, lookback, stage, horizon)].summary()
        rows.append(
            {
                "archive": archive,
                "regime_label": regime_label,
                "bar_threshold_btc": threshold,
                "divergence_lookback_bars": lookback,
                "stage": stage,
                "horizon_bars": horizon,
                **summary,
            }
        )
    return rows


def print_summary(rows: list[dict], *, title: str) -> None:
    print(title)
    print(
        f"{'thr':>6} {'lb':>4} {'stage':<20} {'h':>3} "
        f"{'events':>8} {'hit':>7} {'mean_sfr':>11} {'ic':>8}"
    )
    for row in sorted(rows, key=lambda item: (
        item["bar_threshold_btc"],
        item["divergence_lookback_bars"],
        item["stage"],
        item["horizon_bars"],
        item["archive"],
    )):
        print(
            f"{row['bar_threshold_btc']:>6.0f} "
            f"{row['divergence_lookback_bars']:>4} "
            f"{row['stage']:<20} "
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


if __name__ == "__main__":
    sys.exit(main())
