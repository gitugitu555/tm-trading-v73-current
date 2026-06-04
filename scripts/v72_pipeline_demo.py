#!/usr/bin/env python3
"""Run V7.2 staged pipeline on synthetic ticks (no backtest)."""

from __future__ import annotations

from prime.nautilus_compat import AggressorSide, InstrumentId, Price, Quantity, TradeId, TradeTick
from v72.pipeline import V72Pipeline


def main() -> None:
    pipeline = V72Pipeline()
    ticks = []
    for idx in range(120):
        side = AggressorSide.BUYER if idx % 5 else AggressorSide.SELLER
        ts = 1_700_000_000_000_000_000 + idx * 30_000_000_000
        ticks.append(
            TradeTick(
                instrument_id=InstrumentId.from_str("BTCUSDT.BINANCE"),
                price=Price(100.0 + idx * 0.01, precision=2),
                size=Quantity(1.0, precision=8),
                aggressor_side=side,
                trade_id=TradeId(str(idx)),
                ts_event=ts,
                ts_init=ts,
            )
        )

    last = None
    for tick in ticks:
        last = pipeline.on_trade_tick(tick)

    if last is None:
        print("no ticks processed")
        return

    print("stage_trace:", " -> ".join(last.stage_trace))
    print("halted:", last.halted, last.halt_reason)
    print("regime:", last.regime.hard_label if last.regime else None)
    print("signal:", last.signal.signal_id if last.signal else None)
    print("permission:", last.permission.verdict if last.permission else None)
    print("intent:", last.trade_intent.reason_codes if last.trade_intent else None)


if __name__ == "__main__":
    main()