#!/usr/bin/env python3
"""Run the Chunk B backtester over a Nautilus Parquet catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from nautilus_trader.analysis import TearsheetConfig
from nautilus_trader.analysis import create_tearsheet_from_stats
from nautilus_trader.model.data import TradeTick
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktester
from nautilus_trader.test_kit.providers import TestInstrumentProvider


DEFAULT_CATALOG = Path("data/nautilus/catalogs/btcusdt_trade_ticks")
DEFAULT_ARCHIVE = Path(
    "data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21/BTCUSDT-aggTrades-2020-05-22.zip"
)
DEFAULT_OUTPUT = Path("results/nautilus_chunkb_backtest.json")
DEFAULT_TEARSHEET = Path("results/nautilus_chunkb_backtest_tearsheet.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--instrument", default=TestInstrumentProvider.btcusdt_binance().id.value)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--window-days", type=int, default=1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--signal-mode", choices=["momentum", "divergence"], default="momentum")
    parser.add_argument("--divergence-threshold", type=float, default=100.0)
    parser.add_argument("--price-change-threshold", type=float, default=0.001)
    parser.add_argument("--divergence-threshold-1h", type=float, default=200.0)
    parser.add_argument("--divergence-threshold-15m", type=float, default=80.0)
    parser.add_argument("--divergence-threshold-5m", type=float, default=30.0)
    parser.add_argument("--footprint-tick-size", type=float, default=0.5)
    parser.add_argument("--footprint-warm-period", type=int, default=100)
    parser.add_argument("--vwap-structure-pct", type=float, default=0.003)
    parser.add_argument("--kq-approve", type=float, default=0.55)
    parser.add_argument("--hold-ns", type=int, default=300_000_000_000)
    parser.add_argument("--stop-pct", type=float, default=0.003)
    parser.add_argument("--target-pct", type=float, default=0.006)
    parser.add_argument("--use-tpsl", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-vwap-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-cvd-quantile-filter", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-cvd-reversal-confirm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-cvd-exit", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-session-cvd-reset", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-session-extreme-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--invert-signal-side", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--tearsheet", type=Path, default=DEFAULT_TEARSHEET)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = ParquetDataCatalog(args.catalog_path)
    instrument_id = args.instrument
    start_ns = parse_datetime_ns(args.start)
    end_ns = parse_datetime_ns(args.end)

    config = ChunkBBacktestConfig(
        signal_mode=args.signal_mode,
        divergence_threshold=args.divergence_threshold,
        price_change_threshold=args.price_change_threshold,
        divergence_threshold_1h=args.divergence_threshold_1h,
        divergence_threshold_15m=args.divergence_threshold_15m,
        divergence_threshold_5m=args.divergence_threshold_5m,
        footprint_tick_size=args.footprint_tick_size,
        footprint_warm_period=args.footprint_warm_period,
        use_vwap_gate=args.use_vwap_gate,
        vwap_structure_pct=args.vwap_structure_pct,
        kq_approve=args.kq_approve,
        hold_ns=args.hold_ns,
        stop_pct=args.stop_pct,
        target_pct=args.target_pct,
        use_tpsl=args.use_tpsl,
        use_cvd_quantile_filter=args.use_cvd_quantile_filter,
        use_cvd_reversal_confirm=args.use_cvd_reversal_confirm,
        use_cvd_exit=args.use_cvd_exit,
        use_session_cvd_reset=args.use_session_cvd_reset,
        invert_signal_side=args.invert_signal_side,
        use_session_extreme_gate=args.use_session_extreme_gate,
    )
    report, trades = ChunkBBacktester(config).run(
        iter_catalog_ticks(
            catalog=catalog,
            instrument_id=instrument_id,
            start_ns=start_ns,
            end_ns=end_ns,
            window_days=args.window_days,
            max_rows=args.max_rows,
        )
    )
    payload = {
        "catalog_path": str(args.catalog_path),
        "instrument": instrument_id,
        "start": args.start,
        "end": args.end,
        "max_rows": args.max_rows,
        "report": report.__dict__,
        "sample_trades": [trade.__dict__ for trade in trades[:10]],
        "tearsheet": str(args.tearsheet),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))

    render_official_tearsheet(report=report, trades=trades, output_path=args.tearsheet)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def render_official_tearsheet(*, report, trades, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    returns = build_returns_series(trades)
    stats_pnls = {
        "Total PnL": report.total_pnl,
        "Ending Equity": report.ending_equity,
        "Win Rate": report.win_rate,
        "Trades": report.trades,
    }
    stats_returns = {
        "Sharpe": report.sharpe,
        "Deflated Sharpe Probability": report.deflated_sharpe_probability,
        "DSR Passed": report.dsr_passed,
    }
    stats_general = {
        "Rows Seen": report.rows_seen,
        "Signals Seen": report.signals_seen,
        "Trend Coverage": report.trend_coverage,
    }
    run_info = {
        "Rows seen": report.rows_seen,
        "Signals seen": report.signals_seen,
        "Trades": report.trades,
        "Total PnL": report.total_pnl,
    }
    account_info = {
        "Starting equity": f"{report.config.get('starting_equity', 0):,.2f}",
        "Ending equity": f"{report.ending_equity:,.2f}",
    }
    config = TearsheetConfig(theme="nautilus_dark", title="NautilusTrader Footprint Backtest")
    create_tearsheet_from_stats(
        stats_pnls=stats_pnls,
        stats_returns=stats_returns,
        stats_general=stats_general,
        returns=returns,
        output_path=str(output_path),
        title="NautilusTrader Footprint Backtest",
        config=config,
        run_info=run_info,
        account_info=account_info,
    )
    return output_path


def build_returns_series(trades) -> pd.Series:
    if not trades:
        return pd.Series(dtype=float)
    index = pd.to_datetime([trade.exit_ts_ns for trade in trades], unit="ns", utc=True)
    values = [trade.return_pct for trade in trades]
    return pd.Series(values, index=index).sort_index()


def parse_datetime_ns(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


def iter_catalog_ticks(
    *,
    catalog: ParquetDataCatalog,
    instrument_id: str,
    start_ns: int | None,
    end_ns: int | None,
    window_days: int,
    max_rows: int | None,
):
    emitted = 0
    if window_days <= 0:
        window_days = 30

    if start_ns is None:
        first = catalog.query_first_timestamp(TradeTick, instrument_id)
        start_ns = int(first.value) if first is not None else 0
    if end_ns is None:
        last = catalog.query_last_timestamp(TradeTick, instrument_id)
        end_ns = int(last.value) if last is not None else 0

    window_ns = window_days * 24 * 60 * 60 * 1_000_000_000
    cursor = start_ns
    while cursor <= end_ns:
        upper = min(cursor + window_ns - 1, end_ns)
        batch = catalog.query(TradeTick, identifiers=[instrument_id], start=cursor, end=upper)
        for tick in batch:
            yield tick
            emitted += 1
            if max_rows is not None and emitted >= max_rows:
                return
        cursor = upper + 1


if __name__ == "__main__":
    raise SystemExit(main())
