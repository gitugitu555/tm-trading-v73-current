"""CVDMomentumConfirmation — V720 Nautilus shell without ChunkBBacktester."""

from __future__ import annotations

from dataclasses import dataclass

from prime.nautilus_compat import NAUTILUS_AVAILABLE, TradeTick
from prime.phase1 import CVDEngine, DeltaVelocityEngine, FootprintEngine
from v72.contracts import V72PipelineConfig
from v72.pipeline import V72Pipeline


@dataclass(frozen=True)
class CVDMomentumConfirmationConfig:
    instrument_id: str = "BTCUSDT.BINANCE"
    cvd_threshold: float = 100.0
    footprint_tick_size: float = 0.5
    kq_approve: float = 0.55
    enable_trading: bool = False


class CVDMomentumConfirmationFacade:
    """Deterministic facade used when Nautilus Strategy runtime is unavailable."""

    def __init__(self, config: CVDMomentumConfirmationConfig | None = None) -> None:
        cfg = config or CVDMomentumConfirmationConfig()
        self.config = cfg
        self._pipeline = V72Pipeline(
            V72PipelineConfig(
                cvd_threshold=cfg.cvd_threshold,
                footprint_tick_size=cfg.footprint_tick_size,
                kq_approve=cfg.kq_approve,
                enable_s2_book=False,
            )
        )
        self.intents: list = []

    def on_trade_tick(self, tick: TradeTick) -> None:
        state = self._pipeline.on_trade_tick(tick)
        if state.trade_intent is not None:
            self.intents.append(state.trade_intent)
            if self.config.enable_trading:
                raise RuntimeError("live order routing is disabled in V7.2 staged build")


def build_cvd_momentum_strategy_class():
    """Return Nautilus Strategy subclass when nautilus_trader is installed."""

    if not NAUTILUS_AVAILABLE:
        return None

    from decimal import Decimal

    from nautilus_trader.config import StrategyConfig
    from nautilus_trader.model.data import TradeTick as NtTradeTick
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.trading.strategy import Strategy

    class CVDMomentumConfirmationConfig(StrategyConfig, frozen=True):
        instrument_id: InstrumentId = InstrumentId.from_str("BTCUSDT-PERP.BINANCE")
        cvd_threshold: float = 100.0
        footprint_tick_size: float = 0.5
        warm_period: int = 200
        kq_approve: float = 0.55
        enable_trading: bool = False

    class CVDMomentumConfirmation(Strategy):
        """V720: momentum confirmation with tick-registered indicators."""

        def __init__(self, config: CVDMomentumConfirmationConfig) -> None:
            super().__init__(config)
            self._cvd = CVDEngine(divergence_threshold=config.cvd_threshold)
            self._delta = DeltaVelocityEngine()
            self._footprint = FootprintEngine(
                tick_size=config.footprint_tick_size,
                warm_period=config.warm_period,
            )
            self._facade = CVDMomentumConfirmationFacade(
                CVDMomentumConfirmationConfig(
                    instrument_id=str(config.instrument_id),
                    cvd_threshold=config.cvd_threshold,
                    footprint_tick_size=config.footprint_tick_size,
                    kq_approve=config.kq_approve,
                    enable_trading=config.enable_trading,
                )
            )

        def on_start(self) -> None:
            self.register_indicator_for_trade_ticks(self.config.instrument_id, self._cvd)
            self.register_indicator_for_trade_ticks(self.config.instrument_id, self._delta)
            self.register_indicator_for_trade_ticks(
                self.config.instrument_id,
                self._footprint,
            )
            self.subscribe_trade_ticks(self.config.instrument_id)

        def on_trade_tick(self, tick: NtTradeTick) -> None:
            self._facade.on_trade_tick(tick)

    return CVDMomentumConfirmation