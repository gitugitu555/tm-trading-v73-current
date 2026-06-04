"""V7.2 Chunk B Nautilus strategy shell for CVDDivergenceMomentum."""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.trading.strategy import Strategy

from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktester


class CVDDivergenceConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId = InstrumentId.from_str("BTCUSDT-PERP.BINANCE")
    divergence_threshold: float = 100.0
    footprint_tick_size: float = 0.5
    warm_period: int = 200
    kq_approve: float = 0.55
    base_position_pct: float = 0.01
    min_rr: float = 1.5
    stop_atr_mult: float = 1.5
    target_1_r: float = 1.5
    trade_notional_usdt: Decimal = Decimal("1000")


class CVDDivergenceMomentum(Strategy):
    """Nautilus Strategy wrapper for the Chunk B CVD/Footprint signal."""

    def __init__(self, config: CVDDivergenceConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument | None = None
        self._core = ChunkBBacktester(
            ChunkBBacktestConfig(
                divergence_threshold=config.divergence_threshold,
                footprint_tick_size=config.footprint_tick_size,
                footprint_warm_period=config.warm_period,
                kq_approve=config.kq_approve,
                base_position_pct=config.base_position_pct,
            )
        )

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_trade_ticks(self.config.instrument_id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        # The deterministic research backtester owns the signal proof path.
        # This shell keeps Chunk B importable and order-capable under Nautilus.
        # Full order routing is wired after the first Nautilus catalog run proves
        # instrument/data configuration end-to-end.
        return None

    def _submit_limit(self, side: int, price: float) -> None:
        if self.instrument is None:
            return
        order_side = OrderSide.BUY if side == +1 else OrderSide.SELL
        quantity = self.instrument.make_qty(
            float(self.config.trade_notional_usdt) / max(price, 1e-9)
        )
        order = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=order_side,
            quantity=quantity,
            price=self.instrument.make_price(price),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        self.submit_order(order)

