#!/usr/bin/env python3
"""Run Chunk B probes across volatile BTCUSDT archives."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktester
from prime.ic_harness import iter_binance_research_ticks


DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")
DEFAULT_ARCHIVES = [
    "BTCUSDT-aggTrades-2021-04.zip",
    "BTCUSDT-aggTrades-2021-11.zip",
    "BTCUSDT-aggTrades-2022-05.zip",
    "BTCUSDT-aggTrades-2022-11.zip",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", action="append", dest="archives")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--signal-mode", choices=["momentum", "divergence"], default="momentum")
    parser.add_argument("--divergence-threshold", type=float, default=80.0)
    parser.add_argument("--price-change-threshold", type=float, default=0.001)
    parser.add_argument("--divergence-threshold-1h", type=float, default=200.0)
    parser.add_argument("--divergence-threshold-15m", type=float, default=80.0)
    parser.add_argument("--divergence-threshold-5m", type=float, default=30.0)
    parser.add_argument("--regime-trend-threshold", type=float, default=0.0025)
    parser.add_argument("--regime-ranging-threshold", type=float, default=0.001)
    parser.add_argument("--use-stress-regime", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--regime-stress-price-change-pct", type=float, default=0.0045)
    parser.add_argument("--regime-stress-cvd-threshold", type=float, default=500.0)
    parser.add_argument("--kq-approve", type=float, default=0.55)
    parser.add_argument("--hold-ns", type=int, default=300_000_000_000)
    parser.add_argument("--stop-pct", type=float, default=0.003)
    parser.add_argument("--target-pct", type=float, default=0.006)
    parser.add_argument("--use-tpsl", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-vwap-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--vwap-structure-pct", type=float, default=0.003)
    parser.add_argument("--use-cvd-quantile-filter", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--cvd-quantile-window", type=int, default=200)
    parser.add_argument("--cvd-quantile", type=float, default=0.75)
    parser.add_argument("--cvd-quantile-min-samples", type=int, default=200)
    parser.add_argument("--divergence-type", choices=["opposite_delta", "swing"], default="opposite_delta")
    parser.add_argument("--swing-lookback-ns", type=int, default=1_800_000_000_000)
    parser.add_argument("--use-cvd-reversal-confirm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cvd-confirm-ticks", type=int, default=2)
    parser.add_argument("--use-cvd-exit", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-session-cvd-reset", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--session-boundary-hour-utc", type=int, default=0)
    parser.add_argument("--invert-signal-side", action="store_true", default=False)
    parser.add_argument("--use-session-extreme-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--session-extreme-pct", type=float, default=0.003)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archives = args.archives or DEFAULT_ARCHIVES
    start_ns = parse_datetime_ns(args.start_date)
    end_ns = parse_datetime_ns(args.end_date)
    results = []
    any_gate_passed = False
    for archive_name in archives:
        archive = args.dest / archive_name
        if not archive.is_file():
            results.append({"archive": archive_name, "error": "missing"})
            continue
        config = ChunkBBacktestConfig(
            signal_mode=args.signal_mode,
            divergence_threshold=args.divergence_threshold,
            price_change_threshold=args.price_change_threshold,
            divergence_threshold_1h=args.divergence_threshold_1h,
            divergence_threshold_15m=args.divergence_threshold_15m,
            divergence_threshold_5m=args.divergence_threshold_5m,
            hold_ns=args.hold_ns,
            regime_trend_threshold_pct=args.regime_trend_threshold,
            regime_ranging_threshold_pct=args.regime_ranging_threshold,
            use_stress_regime=args.use_stress_regime,
            regime_stress_price_change_pct=args.regime_stress_price_change_pct,
            regime_stress_cvd_threshold=args.regime_stress_cvd_threshold,
            kq_approve=args.kq_approve,
            stop_pct=args.stop_pct,
            target_pct=args.target_pct,
            use_tpsl=args.use_tpsl,
            use_vwap_gate=args.use_vwap_gate,
            vwap_structure_pct=args.vwap_structure_pct,
            use_cvd_quantile_filter=args.use_cvd_quantile_filter,
            cvd_quantile_window=args.cvd_quantile_window,
            cvd_quantile=args.cvd_quantile,
            cvd_quantile_min_samples=args.cvd_quantile_min_samples,
            divergence_type=args.divergence_type,
            swing_lookback_ns=args.swing_lookback_ns,
            use_cvd_reversal_confirm=args.use_cvd_reversal_confirm,
            cvd_confirm_ticks=args.cvd_confirm_ticks,
            use_cvd_exit=args.use_cvd_exit,
            use_session_cvd_reset=args.use_session_cvd_reset,
            session_boundary_hour_utc=args.session_boundary_hour_utc,
            invert_signal_side=args.invert_signal_side,
            use_session_extreme_gate=args.use_session_extreme_gate,
            session_extreme_pct=args.session_extreme_pct,
        )
        report, trades = ChunkBBacktester(config).run(
            iter_binance_research_ticks(
                [archive],
                max_rows=args.max_rows,
                start_ns=start_ns,
                end_ns=end_ns,
            )
        )
        any_gate_passed = any_gate_passed or report.dsr_passed
        results.append(
            {
                "archive": archive_name,
                "report": asdict(report),
                "sample_trades": [asdict(trade) for trade in trades[:3]],
            }
        )

    payload = {
        "chunk": "B",
        "max_rows": args.max_rows,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "divergence_threshold": args.divergence_threshold,
        "signal_mode": args.signal_mode,
        "regime_trend_threshold": args.regime_trend_threshold,
        "regime_ranging_threshold": args.regime_ranging_threshold,
        "results": results,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if any_gate_passed else 1


def parse_datetime_ns(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


if __name__ == "__main__":
    sys.exit(main())
