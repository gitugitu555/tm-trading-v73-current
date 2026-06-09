"""Deterministic Chunk B research backtest over TradeTick streams."""

from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from collections import Counter, deque
import statistics
from typing import Iterable

from prime.contracts import DataQualitySnapshot
from prime.nautilus_compat import TradeTick
from prime.performance import deflated_sharpe_probability, kurtosis, sharpe_ratio, skewness
from prime.chunk_b_trade_state import OpenTradeState
from prime.auction_state import AuctionStateEngine
from prime.phase1 import (
    CVDEngine,
    DeltaVelocityEngine,
    FootprintEngine,
    SessionExtremeTracker,
    SwingDivergenceEngine,
    VWAPEngine,
)
from prime.phase4_minimal import HardRegimeClassifier, RegimeState
from prime.phase5_chunkb import AlphaPermissionEngineChunkB
from prime.volume_bars import VolumeBar, VolumeBarSampler
from prime.volume_bar_cvd import (
    entry_delta_aligns,
    htf_change_at,
    htf_flat_abs_threshold,
    volume_bar_cvd_signal,
    volume_bar_cvd_signal_d5,
)


@dataclass(frozen=True)
class ChunkBBacktestConfig:
    starting_equity: float = 100_000.0
    signal_mode: str = "momentum"
    divergence_threshold: float = 100.0
    price_change_threshold: float = 0.001
    divergence_threshold_1h: float = 200.0
    divergence_threshold_15m: float = 80.0
    divergence_threshold_5m: float = 30.0
    footprint_tick_size: float = 0.5
    footprint_warm_period: int = 100
    vwap_warm_period: int = 50
    use_vwap_gate: bool = True
    vwap_structure_pct: float = 0.003
    kq_approve: float = 0.55
    base_position_pct: float = 0.01
    hold_ns: int = 300_000_000_000
    use_time_exit: bool = True
    stop_pct: float = 0.003
    target_pct: float = 0.006
    use_tpsl: bool = True
    lookback_ns: int = 300_000_000_000
    regime_trend_threshold_pct: float = 0.0025
    regime_ranging_threshold_pct: float = 0.001
    use_stress_regime: bool = True
    regime_stress_price_change_pct: float = 0.0045
    regime_stress_cvd_threshold: float = 500.0
    fee_bps_per_side: float = 5.0
    slippage_bps_per_side: float = 1.0
    n_trials: int = 4
    use_cvd_quantile_filter: bool = False
    cvd_quantile_window: int = 200
    cvd_quantile: float = 0.75
    cvd_quantile_min_samples: int = 200
    use_session_cvd_reset: bool = True
    session_boundary_hour_utc: int = 0
    divergence_type: str = "opposite_delta"
    swing_lookback_ns: int = 1_800_000_000_000
    use_cvd_reversal_confirm: bool = True
    cvd_confirm_ticks: int = 2
    use_cvd_exit: bool = False
    invert_signal_side: bool = False
    use_session_extreme_gate: bool = True
    session_extreme_pct: float = 0.003
    use_auction_state_gate: bool = False
    use_vpin_gate: bool = False
    volume_bar_threshold: float = 300.0
    divergence_lookback_bars: int = 40
    htf_flat_quantile: float = 0.25
    exit_after_volume_bars: int | None = None
    use_regime_gate_volume_bar: bool = False
    use_footprint_confluence: bool = False
    footprint_require_stacked: bool = False
    footprint_invert_for_fade: bool = False
    footprint_allow_neutral: bool = True
    approve_only_permission: bool = False
    require_delta_exhaustion_fade: bool = False
    use_delta_rev_2_entry: bool = False
    require_entry_delta_alignment: bool = False


@dataclass(frozen=True)
class PaperTrade:
    entry_ts_ns: int
    exit_ts_ns: int
    side: int
    entry_price: float
    exit_price: float
    notional: float
    pnl: float
    return_pct: float
    signal_id: str
    permission_verdict: str
    reason_codes: tuple[str, ...]
    exit_reason: str
    max_adverse: float
    max_favorable: float


@dataclass(frozen=True)
class ChunkBBacktestReport:
    rows_seen: int
    signals_seen: int
    trades: int
    total_pnl: float
    ending_equity: float
    sharpe: float
    deflated_sharpe_probability: float
    dsr_passed: bool
    win_rate: float
    regime_counts: dict[str, int]
    trend_coverage: float
    exit_reasons: dict[str, int]
    permission_counts: dict[str, int]
    mae_stats: dict[str, float]
    mfe_stats: dict[str, float]
    config: dict


class ChunkBBacktester:
    def __init__(self, config: ChunkBBacktestConfig | None = None) -> None:
        self.config = config or ChunkBBacktestConfig()
        self._cvd = CVDEngine(divergence_threshold=self.config.divergence_threshold)
        self._footprint = FootprintEngine(
            tick_size=self.config.footprint_tick_size,
            warm_period=self.config.footprint_warm_period,
        )
        self._delta = DeltaVelocityEngine()
        self._vwap = VWAPEngine(warm_period=self.config.vwap_warm_period)
        self._swing = SwingDivergenceEngine(window_ns=self.config.swing_lookback_ns)
        self._session_extreme = SessionExtremeTracker()
        self._regime = HardRegimeClassifier(
            trend_threshold_pct=self.config.regime_trend_threshold_pct,
            ranging_threshold_pct=self.config.regime_ranging_threshold_pct,
            stress_price_change_pct=self.config.regime_stress_price_change_pct,
            stress_cvd_threshold=self.config.regime_stress_cvd_threshold,
            use_stress_regime=self.config.use_stress_regime,
        )
        self._permission = AlphaPermissionEngineChunkB(
            kq_approve=self.config.kq_approve,
            base_position_size=self.config.base_position_pct,
            vwap_structure_pct=self.config.vwap_structure_pct,
            use_auction_state_gate=self.config.use_auction_state_gate,
        )
        self._auction = AuctionStateEngine()
        self._last_session_key: int | None = None
        self._cvd_prev_5m = 0.0
        self._cvd_confirm_count = 0
        self._pending_signal: dict | None = None
        self._pending_signal_ts = 0
        self._volume_sampler = VolumeBarSampler(self.config.volume_bar_threshold)
        self._bars: deque[VolumeBar] = deque(maxlen=2000)
        self._htf_changes_history: deque[float] = deque(maxlen=2000)

    def run(self, ticks: Iterable[TradeTick]) -> tuple[ChunkBBacktestReport, list[PaperTrade]]:
        rows_seen = 0
        signals_seen = 0
        equity = self.config.starting_equity
        prices: deque[tuple[int, float]] = deque()
        cvd5m_history: deque[float] = deque(maxlen=self.config.cvd_quantile_window)
        trades: list[PaperTrade] = []
        regime_counts: Counter[str] = Counter()
        permission_counts: Counter[str] = Counter()
        open_trade: OpenTradeState | None = None
        quality = DataQualitySnapshot(
            state="CLEAN",
            latency_ms=0.0,
            duplicate_rate=0.0,
            sequence_gap_count=0,
            crossed_book=False,
            stale_feed_ms=0.0,
            confidence_scalar=1.0,
            reason_codes=[],
        )

        for tick in ticks:
            rows_seen += 1
            ts = int(tick.ts_event)
            price = float(tick.price)
            self._reset_session_if_needed(ts)
            self._session_extreme.update(ts, price)
            prices.append((ts, price))
            cutoff = ts - self.config.lookback_ns
            while prices and prices[0][0] < cutoff:
                prices.popleft()

            self._cvd.handle_trade_tick(tick)
            self._footprint.handle_trade_tick(tick)
            self._delta.handle_trade_tick(tick)
            self._vwap.handle_trade_tick(tick)
            self._swing.update(ts, price, self._cvd.cvd_15m)
            cvd5m_history.append(self._cvd.cvd_5m)

            # Update volume bar sampler
            bar = self._volume_sampler.update(tick)
            is_bar_boundary = False
            if bar is not None:
                self._bars.append(bar)
                is_bar_boundary = True
                htf_change = htf_change_at(self._bars, bar.end_ts_ns, bar.cumulative_delta)
                self._htf_changes_history.append(abs(htf_change))

            if open_trade is not None:
                open_trade = open_trade.with_excursion(price)
                if is_bar_boundary and open_trade.exit_after_volume_bars is not None:
                    open_trade = replace(
                        open_trade,
                        bars_since_entry=open_trade.bars_since_entry + 1,
                    )
                exit_reason = self._exit_reason(open_trade, ts, price)
                self._cvd_prev_5m = self._cvd.cvd_5m
                if exit_reason is None:
                    continue
                paper_trade = self._close_trade(open_trade, ts, price, exit_reason)
                trades.append(paper_trade)
                equity += paper_trade.pnl
                open_trade = None

            if not self._ready():
                continue

            price_change = self._price_change(prices)
            regime = self._regime.classify(
                timestamp_ns=ts,
                price_change_5m_pct=price_change,
                cvd_session=self._cvd.cvd_5m,
            )
            auction_state = self._auction.update(
                timestamp_ns=ts,
                price_change_5m_pct=price_change,
                cvd_session=self._cvd.cvd_5m,
                value_acceptance=regime.hard_label in {"TREND_BULL", "TREND_BEAR"},
            )
            regime_counts[regime.hard_label] += 1
            cvd_quantile_ok = self._cvd_quantile_extreme(
                self._cvd.cvd_5m,
                cvd5m_history,
                min_samples=self.config.cvd_quantile_min_samples,
                quantile=self.config.cvd_quantile,
            )
            signal = self._signal(
                timestamp_ns=ts,
                price=price,
                price_change=price_change,
                regime=regime,
                cvd_quantile_ok=cvd_quantile_ok,
                is_bar_boundary=is_bar_boundary,
            )
            signal = self._confirm_divergence_signal(signal, ts, price)
            self._cvd_prev_5m = self._cvd.cvd_5m
            if signal is None:
                continue

            signals_seen += 1
            permission = self._permission.evaluate(
                signal_id=signal["id"],
                timestamp_ns=ts,
                trade_side=signal["side"],
                raw_strength=signal["strength"],
                quality_snapshot=quality,
                regime=regime,
                cvd_divergence=not self._uses_volume_bar_edge(),
                cvd_5m=self._cvd.cvd_5m,
                signal_mode=self.config.signal_mode,
                vwap_deviation=(
                    self._vwap.deviation
                    if self.config.use_vwap_gate and not self._uses_volume_bar_edge()
                    else None
                ),
                auction_state=auction_state,
                divergence_type=self.config.divergence_type,
            )
            permission_counts[permission.verdict] += 1
            if permission.verdict not in {"APPROVE", "REDUCED"}:
                continue

            notional = equity * permission.permitted_size
            open_trade = OpenTradeState(
                entry_ts_ns=ts,
                side=signal["side"],
                entry_price=self._apply_slippage(price, signal["side"], is_entry=True),
                notional=notional,
                signal_id=signal["id"],
                permission_verdict=permission.verdict,
                reason_codes=tuple(record.code for record in permission.chain),
                exit_after_ts_ns=ts + self.config.hold_ns,
                exit_after_volume_bars=self.config.exit_after_volume_bars,
            )

        returns = [trade.return_pct for trade in trades]
        adverse_list = [trade.max_adverse for trade in trades]
        favorable_list = [trade.max_favorable for trade in trades]
        total_pnl = sum(trade.pnl for trade in trades)
        sharpe = sharpe_ratio(returns)
        dsr = deflated_sharpe_probability(
            sharpe=sharpe,
            n_trials=self.config.n_trials,
            skew=skewness(returns),
            kurt=kurtosis(returns),
            n_obs=len(returns),
        )
        wins = sum(1 for trade in trades if trade.pnl > 0)
        exit_reasons = Counter(trade.exit_reason for trade in trades)
        trend_rows = regime_counts.get("TREND_BULL", 0) + regime_counts.get("TREND_BEAR", 0)
        classified_rows = sum(regime_counts.values())
        report = ChunkBBacktestReport(
            rows_seen=rows_seen,
            signals_seen=signals_seen,
            trades=len(trades),
            total_pnl=round(total_pnl, 2),
            ending_equity=round(equity, 2),
            sharpe=round(sharpe, 4),
            deflated_sharpe_probability=round(dsr, 4),
            dsr_passed=dsr >= 0.95 and sharpe >= 1.5,
            win_rate=round(wins / len(trades), 4) if trades else 0.0,
            regime_counts=dict(sorted(regime_counts.items())),
            trend_coverage=round(trend_rows / classified_rows, 4) if classified_rows else 0.0,
            exit_reasons=dict(sorted(exit_reasons.items())),
            permission_counts=dict(sorted(permission_counts.items())),
            mae_stats=self._pct_stats(adverse_list),
            mfe_stats=self._pct_stats(favorable_list),
            config=asdict(self.config),
        )
        return report, trades

    def _ready(self) -> bool:
        return (
            self._cvd.initialized
            and self._footprint.initialized
            and self._delta.initialized
            and self._vwap.initialized
            and self._swing.initialized
        )

    def _reset_session_if_needed(self, ts: int) -> None:
        if not self.config.use_session_cvd_reset:
            return
        hour_ns = 3_600_000_000_000
        day_ns = 24 * hour_ns
        tick_hour = (ts // hour_ns) % 24
        if tick_hour != self.config.session_boundary_hour_utc:
            return
        session_key = ts // day_ns
        if self._last_session_key == session_key:
            return
        self._cvd.reset_session()
        self._pending_signal = None
        self._cvd_confirm_count = 0
        self._cvd_prev_5m = 0.0
        self._last_session_key = session_key

    @staticmethod
    def _price_change(prices: deque[tuple[int, float]]) -> float:
        if len(prices) < 2 or prices[0][1] == 0:
            return 0.0
        return (prices[-1][1] - prices[0][1]) / prices[0][1]

    def _signal(
        self,
        timestamp_ns: int,
        price: float,
        price_change: float,
        regime: RegimeState,
        cvd_quantile_ok: bool = True,
        is_bar_boundary: bool = False,
    ) -> dict | None:
        if self.config.signal_mode == "divergence":
            if self.config.divergence_type == "volume_bar_cvd":
                return self._volume_bar_cvd_signal(timestamp_ns, price, regime, is_bar_boundary)
            return self._divergence_signal(timestamp_ns, price, price_change, regime, cvd_quantile_ok)
        return self._momentum_signal(timestamp_ns, price, regime.hard_label, cvd_quantile_ok)

    def _uses_volume_bar_edge(self) -> bool:
        return (
            self.config.signal_mode == "divergence"
            and self.config.divergence_type == "volume_bar_cvd"
        )

    def _volume_bar_cvd_signal(
        self,
        timestamp_ns: int,
        price: float,
        regime: RegimeState,
        is_bar_boundary: bool,
    ) -> dict | None:
        if not is_bar_boundary:
            return None
        if self.config.use_regime_gate_volume_bar and not self._regime.gate_for_signal_mode(
            regime, "divergence"
        ):
            return None
        current_bar = self._bars[-1]
        htf_change = htf_change_at(self._bars, current_bar.end_ts_ns, current_bar.cumulative_delta)
        flat_abs = htf_flat_abs_threshold(
            self._htf_changes_history,
            quantile=self.config.htf_flat_quantile,
        )
        if self.config.use_delta_rev_2_entry:
            signal = volume_bar_cvd_signal_d5(
                self._bars,
                lookback_bars=self.config.divergence_lookback_bars,
                htf_change=htf_change,
                flat_abs=flat_abs,
                timestamp_ns=timestamp_ns,
                price=price,
                invert_signal_side=self.config.invert_signal_side,
            )
        else:
            signal = volume_bar_cvd_signal(
                self._bars,
                lookback_bars=self.config.divergence_lookback_bars,
                htf_change=htf_change,
                flat_abs=flat_abs,
                timestamp_ns=timestamp_ns,
                price=price,
                invert_signal_side=self.config.invert_signal_side,
            )
        if (
            signal is not None
            and self.config.require_entry_delta_alignment
            and not entry_delta_aligns(int(signal["side"]), current_bar.delta)
        ):
            return None
        return signal

    def _momentum_signal(
        self,
        timestamp_ns: int,
        price: float,
        regime_label: str,
        cvd_quantile_ok: bool,
    ) -> dict | None:
        if not regime_label.startswith("TREND"):
            return None
        if self._cvd.cvd_5m >= self.config.divergence_threshold:
            side = +1
        elif self._cvd.cvd_5m <= -self.config.divergence_threshold:
            side = -1
        else:
            return None
        if regime_label == "TREND_BULL" and side < 0:
            return None
        if regime_label == "TREND_BEAR" and side > 0:
            return None
        if self._footprint.footprint_bias != side:
            return None
        if self.config.use_cvd_quantile_filter and not cvd_quantile_ok:
            return None
        strength = min(1.0, abs(self._cvd.cvd_5m) / (self.config.divergence_threshold * 2))
        if self._footprint.stacked:
            strength = min(1.0, strength + 0.15)
        if self._delta.exhaustion == "NONE":
            strength = min(1.0, strength + 0.10)
        return {
            "id": f"CVDDIV_{timestamp_ns}_{side}",
            "side": side,
            "strength": round(strength, 6),
            "price": price,
        }

    def _divergence_signal(
        self,
        timestamp_ns: int,
        price: float,
        price_change: float,
        regime: RegimeState,
        cvd_quantile_ok: bool,
    ) -> dict | None:
        if self.config.divergence_type == "swing":
            return self._swing_divergence_signal(timestamp_ns, price, regime, cvd_quantile_ok)
        if not self._regime.gate_for_signal_mode(regime, "divergence"):
            return None
        cvd_1h = self._cvd.cvd_1h
        if cvd_1h <= -self.config.divergence_threshold_1h:
            side = -1
        elif cvd_1h >= self.config.divergence_threshold_1h:
            side = +1
        else:
            return None

        cvd_15m = self._cvd.cvd_15m
        if side == -1:
            if not (
                price_change > self.config.price_change_threshold
                and cvd_15m <= -self.config.divergence_threshold_15m
            ):
                return None
        else:
            if not (
                price_change < -self.config.price_change_threshold
                and cvd_15m >= self.config.divergence_threshold_15m
            ):
                return None

        cvd_5m = self._cvd.cvd_5m
        if side == -1:
            if cvd_5m >= 0 or abs(cvd_5m) < self.config.divergence_threshold_5m:
                return None
        else:
            if cvd_5m <= 0 or abs(cvd_5m) < self.config.divergence_threshold_5m:
                return None

        if self.config.use_cvd_quantile_filter and not cvd_quantile_ok:
            return None

        if not self._at_session_extreme(price, side):
            return None

        strength = min(1.0, abs(cvd_15m) / (self.config.divergence_threshold_15m * 2))
        if self._footprint.footprint_bias == side:
            strength = min(1.0, strength + 0.10)
        if abs(self._vwap.deviation) < 0.002:
            strength = min(1.0, strength + 0.10)
        if self.config.invert_signal_side:
            side = -side
        return {
            "id": f"CVDMTF_{timestamp_ns}_{side}",
            "side": side,
            "strength": round(strength, 6),
            "price": price,
        }

    def _swing_divergence_signal(
        self,
        timestamp_ns: int,
        price: float,
        regime: RegimeState,
        cvd_quantile_ok: bool,
    ) -> dict | None:
        if not self._regime.gate_for_signal_mode(regime, "divergence"):
            return None
        if self.config.use_cvd_quantile_filter and not cvd_quantile_ok:
            return None

        cvd_now = self._cvd.cvd_15m
        side = 0
        near_high = price >= self._swing.price_high * 0.999
        bearish_div = cvd_now < self._swing.cvd_high - self.config.divergence_threshold_15m
        near_low = price <= self._swing.price_low * 1.001
        bullish_div = cvd_now > self._swing.cvd_low + self.config.divergence_threshold_15m
        if near_high and bearish_div:
            side = -1
        elif near_low and bullish_div:
            side = +1
        else:
            return None

        if not self._at_session_extreme(price, side):
            return None

        reference_cvd = self._swing.cvd_high if side == -1 else self._swing.cvd_low
        magnitude = abs(cvd_now - reference_cvd)
        strength = min(1.0, magnitude / (self.config.divergence_threshold_15m * 2))
        if self._footprint.footprint_bias == side:
            strength = min(1.0, strength + 0.10)
        if abs(self._vwap.deviation) < 0.002:
            strength = min(1.0, strength + 0.10)
        if self.config.invert_signal_side:
            side = -side
        return {
            "id": f"SWING_{timestamp_ns}_{side}",
            "side": side,
            "strength": round(strength, 6),
            "price": price,
        }

    def _at_session_extreme(self, price: float, side: int) -> bool:
        if not self.config.use_session_extreme_gate:
            return True
        pct = self.config.session_extreme_pct
        return (
            (side == -1 and self._session_extreme.near_high(price, pct))
            or (side == +1 and self._session_extreme.near_low(price, pct))
        )

    def _confirm_divergence_signal(self, signal: dict | None, ts: int, price: float) -> dict | None:
        if self.config.signal_mode != "divergence" or not self.config.use_cvd_reversal_confirm:
            return signal
        if self._uses_volume_bar_edge():
            return signal
        if signal is not None and self._pending_signal is None:
            self._pending_signal = signal
            self._pending_signal_ts = ts
            self._cvd_confirm_count = 0
            return None
        if self._pending_signal is None:
            return None

        side = self._pending_signal["side"]
        cvd_moving_right = (
            (side == -1 and self._cvd.cvd_5m < self._cvd_prev_5m)
            or (side == +1 and self._cvd.cvd_5m > self._cvd_prev_5m)
        )
        if cvd_moving_right:
            self._cvd_confirm_count += 1
        else:
            self._cvd_confirm_count = 0

        price_moved_against = (
            (side == -1 and price > self._pending_signal["price"] * 1.002)
            or (side == +1 and price < self._pending_signal["price"] * 0.998)
        )
        if price_moved_against:
            self._pending_signal = None
            self._cvd_confirm_count = 0
            return None

        if self._cvd_confirm_count >= self.config.cvd_confirm_ticks:
            confirmed = self._pending_signal
            self._pending_signal = None
            self._cvd_confirm_count = 0
            return confirmed
        return None

    @staticmethod
    def _cvd_quantile_extreme(
        cvd_5m: float,
        history: deque[float],
        *,
        min_samples: int,
        quantile: float,
    ) -> bool:
        if len(history) < min_samples:
            return False
        clamped_quantile = min(max(quantile, 0.0), 1.0)
        sorted_abs = sorted(abs(value) for value in history)
        idx = min(len(sorted_abs) - 1, int(len(sorted_abs) * clamped_quantile))
        return abs(cvd_5m) >= sorted_abs[idx]

    def _exit_reason(self, open_trade: OpenTradeState, ts: int, raw_price: float) -> str | None:
        side = open_trade.side
        entry_price = open_trade.entry_price
        if self.config.use_cvd_exit:
            if (side < 0 and self._cvd.cvd_5m > 0) or (side > 0 and self._cvd.cvd_5m < 0):
                return "CVD_EXIT"
        if self.config.use_tpsl:
            if side > 0:
                if raw_price <= entry_price * (1 - self.config.stop_pct):
                    return "STOP"
                if raw_price >= entry_price * (1 + self.config.target_pct):
                    return "TARGET"
            else:
                if raw_price >= entry_price * (1 + self.config.stop_pct):
                    return "STOP"
                if raw_price <= entry_price * (1 - self.config.target_pct):
                    return "TARGET"
        if (
            open_trade.exit_after_volume_bars is not None
            and open_trade.bars_since_entry >= open_trade.exit_after_volume_bars
        ):
            return "BAR_EXIT"
        if self.config.use_time_exit and ts >= open_trade.exit_after_ts_ns:
            return "TIME"
        return None

    @staticmethod
    def _pct_stats(values: list[float]) -> dict[str, float]:
        if not values:
            return {}
        sorted_values = sorted(values)
        n_values = len(sorted_values)
        return {
            "mean": round(statistics.mean(sorted_values), 6),
            "median": round(statistics.median(sorted_values), 6),
            "p75": round(sorted_values[min(n_values - 1, int(n_values * 0.75))], 6),
            "p90": round(sorted_values[min(n_values - 1, int(n_values * 0.90))], 6),
            "max": round(sorted_values[-1], 6),
        }

    def _close_trade(
        self,
        open_trade: OpenTradeState,
        exit_ts_ns: int,
        raw_exit_price: float,
        exit_reason: str,
    ) -> PaperTrade:
        side = open_trade.side
        entry_price = open_trade.entry_price
        exit_price = self._apply_slippage(raw_exit_price, side, is_entry=False)
        gross = side * (exit_price - entry_price) / entry_price * open_trade.notional
        fees = open_trade.notional * (self.config.fee_bps_per_side * 2 / 10_000)
        pnl = gross - fees
        return_pct = pnl / open_trade.notional if open_trade.notional else 0.0
        return PaperTrade(
            entry_ts_ns=open_trade.entry_ts_ns,
            exit_ts_ns=exit_ts_ns,
            side=side,
            entry_price=round(entry_price, 2),
            exit_price=round(exit_price, 2),
            notional=round(open_trade.notional, 2),
            pnl=round(pnl, 2),
            return_pct=return_pct,
            signal_id=open_trade.signal_id,
            permission_verdict=open_trade.permission_verdict,
            reason_codes=open_trade.reason_codes,
            exit_reason=exit_reason,
            max_adverse=round(open_trade.max_adverse, 6),
            max_favorable=round(open_trade.max_favorable, 6),
        )

    def _apply_slippage(self, price: float, side: int, *, is_entry: bool) -> float:
        bps = self.config.slippage_bps_per_side / 10_000
        direction = side if is_entry else -side
        return price * (1 + direction * bps)
