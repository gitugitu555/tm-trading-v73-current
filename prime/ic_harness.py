"""V7.2 sample-first IC harnesses."""

from __future__ import annotations

import csv
from collections import namedtuple
from pathlib import Path
from typing import Callable, Iterable
from zipfile import ZipFile

from core.types import SignedTrade as LegacySignedTrade
from prime.contracts import SignedTrade
from prime.ic_validation import validate_engine
from prime.nautilus_compat import (
    AggressorSide,
    InstrumentId,
    Price,
    Quantity,
    TradeId,
    TradeTick,
)


INSTRUMENT = InstrumentId.from_str("BTCUSDT.BINANCE")
ResearchTick = namedtuple(
    "ResearchTick",
    ["price", "size", "aggressor_side", "ts_event"],
)


def build_tick(row) -> TradeTick:
    return TradeTick(
        instrument_id=INSTRUMENT,
        price=Price(row.price, precision=2),
        size=Quantity(row.size, precision=8),
        aggressor_side=AggressorSide.BUYER if row.side == "buy" else AggressorSide.SELLER,
        trade_id=TradeId(str(row.trade_id)),
        ts_event=int(row.timestamp_ns),
        ts_init=int(row.timestamp_ns),
    )


def signed_to_tick(
    trade: SignedTrade | LegacySignedTrade,
    precision_price: int = 2,
    precision_size: int = 8,
) -> TradeTick:
    if isinstance(trade, SignedTrade):
        side_value = trade.side
        symbol = trade.symbol
        source = trade.source
        price = trade.price
        size = trade.size
        timestamp_ns = trade.timestamp_ns
        trade_id = trade.trade_id
    else:
        side_value = {"BUY": +1, "SELL": -1}.get(trade.side, 0)
        symbol = trade.symbol
        source = trade.exchange
        price = trade.price
        size = trade.size_base
        timestamp_ns = int(trade.ts_event.timestamp() * 1_000_000_000)
        trade_id = trade.trade_id or f"{symbol}_{timestamp_ns}"

    if side_value == +1:
        side = AggressorSide.BUYER
    elif side_value == -1:
        side = AggressorSide.SELLER
    else:
        side = AggressorSide.NO_AGGRESSOR

    return TradeTick(
        instrument_id=InstrumentId.from_str(f"{symbol}.{source}"),
        price=Price(price, precision=precision_price),
        size=Quantity(size, precision=precision_size),
        aggressor_side=side,
        trade_id=TradeId(str(trade_id)),
        ts_event=timestamp_ns,
        ts_init=timestamp_ns,
    )


def run_ic_sample_first(
    engine_cls,
    engine_kwargs: dict,
    signal_fn: Callable,
    parquet_path: str,
    sample_weeks: int = 1,
) -> dict:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - dependency-dependent path.
        raise RuntimeError("pandas is required for parquet IC harness") from exc

    df = pd.read_parquet(parquet_path)
    df = df.sort_values("timestamp_ns").reset_index(drop=True)
    cutoff = df["timestamp_ns"].iloc[0] + (sample_weeks * 7 * 86400 * 1_000_000_000)
    sample = df[df["timestamp_ns"] <= cutoff]
    return run_ic_on_ticks(
        engine_cls=engine_cls,
        engine_kwargs=engine_kwargs,
        signal_fn=signal_fn,
        ticks=(build_tick(row) for row in sample.itertuples(index=False)),
    )


def run_ic_on_binance_archives(
    engine_cls,
    engine_kwargs: dict,
    signal_fn: Callable,
    archive_paths: Iterable[Path],
    max_rows: int | None = 50_000,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> dict:
    return run_ic_on_ticks(
        engine_cls=engine_cls,
        engine_kwargs=engine_kwargs,
        signal_fn=signal_fn,
        ticks=iter_binance_ticks(
            archive_paths,
            max_rows=max_rows,
            start_ns=start_ns,
            end_ns=end_ns,
        ),
    )


def run_ic_on_ticks(engine_cls, engine_kwargs: dict, signal_fn: Callable, ticks: Iterable[TradeTick]) -> dict:
    engine = engine_cls(**engine_kwargs)
    signal_values: list[float] = []
    prices: list[float] = []
    timestamps: list[int] = []

    for tick in ticks:
        engine.handle_trade_tick(tick)
        if not engine.initialized:
            continue
        signal_values.append(float(signal_fn(engine)))
        prices.append(float(tick.price))
        timestamps.append(int(tick.ts_event))

    return validate_engine(
        name=engine_cls.__name__,
        signal_values=signal_values,
        price_series=prices,
        timestamps_ns=timestamps,
    )


def iter_binance_ticks(
    archive_paths: Iterable[Path],
    max_rows: int | None,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> Iterable[TradeTick]:
    emitted = 0
    for archive in sorted(Path(path) for path in archive_paths):
        with ZipFile(archive) as zipped:
            csv_name = archive.name.removesuffix(".zip") + ".csv"
            with zipped.open(csv_name) as raw:
                lines = (line.decode("utf-8") for line in raw)
                for row in csv.reader(lines):
                    if len(row) != 8:
                        continue
                    timestamp_ns = binance_timestamp_to_ns(row[5])
                    if start_ns is not None and timestamp_ns < start_ns:
                        continue
                    if end_ns is not None and timestamp_ns >= end_ns:
                        return
                    side = AggressorSide.SELLER if row[6] == "True" else AggressorSide.BUYER
                    yield TradeTick(
                        instrument_id=INSTRUMENT,
                        price=Price(row[1], precision=2),
                        size=Quantity(row[2], precision=8),
                        aggressor_side=side,
                        trade_id=TradeId(row[0]),
                        ts_event=timestamp_ns,
                        ts_init=timestamp_ns,
                    )
                    emitted += 1
                    if max_rows is not None and emitted >= max_rows:
                        return


def iter_binance_research_ticks(
    archive_paths: Iterable[Path],
    max_rows: int | None,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> Iterable[ResearchTick]:
    emitted = 0
    for archive in sorted(Path(path) for path in archive_paths):
        with ZipFile(archive) as zipped:
            csv_name = archive.name.removesuffix(".zip") + ".csv"
            with zipped.open(csv_name) as raw:
                lines = (line.decode("utf-8") for line in raw)
                for row in csv.reader(lines):
                    if len(row) != 8:
                        continue
                    timestamp_ns = binance_timestamp_to_ns(row[5])
                    if start_ns is not None and timestamp_ns < start_ns:
                        continue
                    if end_ns is not None and timestamp_ns >= end_ns:
                        return
                    yield ResearchTick(
                        price=float(row[1]),
                        size=float(row[2]),
                        aggressor_side=AggressorSide.SELLER if row[6] == "True" else AggressorSide.BUYER,
                        ts_event=timestamp_ns,
                    )
                    emitted += 1
                    if max_rows is not None and emitted >= max_rows:
                        return


def binance_timestamp_to_ns(value: str) -> int:
    raw = int(value)
    if raw >= 10_000_000_000_000:
        return raw * 1_000
    return raw * 1_000_000
