#!/usr/bin/env python3
"""Run consolidated Chunk B backtest using pre-computed indicators from Parquet caches."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from collections import deque
import statistics

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktestReport, PaperTrade
from prime.chunk_b_trade_state import OpenTradeState
from prime.phase4_minimal import HardRegimeClassifier, RegimeState
from prime.phase5_chunkb import AlphaPermissionEngineChunkB
from prime.performance import deflated_sharpe_probability, kurtosis, sharpe_ratio, skewness
from prime.contracts import DataQualitySnapshot
from prime.volume_bars import VolumeBar
from prime.auction_state import AuctionStateEngine

DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")
CACHE_DIR = Path("results/indicator_cache")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--threshold-btc", type=float, default=300.0)
    parser.add_argument("--signal-mode", choices=["momentum", "divergence"], default="momentum")
    parser.add_argument("--divergence-threshold", type=float, default=100.0)
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
    parser.add_argument("--use-auction-state-gate", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-cvd-quantile-filter", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--cvd-quantile-window", type=int, default=200)
    parser.add_argument("--cvd-quantile", type=float, default=0.75)
    parser.add_argument("--cvd-quantile-min-samples", type=int, default=200)
    parser.add_argument("--divergence-type", choices=["opposite_delta", "swing", "volume_bar_cvd"], default="opposite_delta")
    parser.add_argument("--divergence-lookback-bars", type=int, default=40)
    parser.add_argument("--htf-flat-quantile", type=float, default=0.25)
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

def parse_datetime_ns(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)

def main() -> int:
    args = parse_args()
    
    # Locate all Parquet cache files for this threshold
    cache_files = sorted(CACHE_DIR.glob(f"*.threshold-{int(args.threshold_btc)}.parquet"))
    # Exclude files that have maxrows in them to ensure we only load full files
    cache_files = [f for f in cache_files if "maxrows" not in f.name]
    
    if not cache_files:
        print(f"No precomputed Parquet caches found in {CACHE_DIR} for threshold {args.threshold_btc}.", file=sys.stderr)
        return 2
        
    print(f"Loading {len(cache_files)} cache files...")
    dfs = []
    for f in cache_files:
        dfs.append(pd.read_parquet(f))
    df = pd.concat(dfs, ignore_index=True)
    
    # Sort by end_ts_ns to be absolutely sure of chronology
    df = df.sort_values("end_ts_ns").reset_index(drop=True)
    print(f"Loaded {len(df):,} volume bars total.")
    
    start_ns = parse_datetime_ns(args.start_date)
    end_ns = parse_datetime_ns(args.end_date)
    
    if start_ns is not None:
        df = df[df["end_ts_ns"] >= start_ns]
    if end_ns is not None:
        df = df[df["end_ts_ns"] <= end_ns]

    # Setup configurations and classifiers
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
        volume_bar_threshold=args.threshold_btc,
        divergence_lookback_bars=args.divergence_lookback_bars,
        htf_flat_quantile=args.htf_flat_quantile,
        use_auction_state_gate=args.use_auction_state_gate,
    )

    classifier = HardRegimeClassifier(
        trend_threshold_pct=args.regime_trend_threshold,
        ranging_threshold_pct=args.regime_ranging_threshold,
        stress_price_change_pct=args.regime_stress_price_change_pct,
        stress_cvd_threshold=args.regime_stress_cvd_threshold,
        use_stress_regime=args.use_stress_regime,
    )

    permission_engine = AlphaPermissionEngineChunkB(
        kq_approve=args.kq_approve,
        base_position_size=config.base_position_pct,
        vwap_structure_pct=args.vwap_structure_pct,
        use_auction_state_gate=args.use_auction_state_gate,
    )

    auction_engine = AuctionStateEngine(hysteresis_bars=2)

    quality = DataQualitySnapshot(
        state="CLEAN", latency_ms=0.0, duplicate_rate=0.0, sequence_gap_count=0,
        crossed_book=False, stale_feed_ms=0.0, confidence_scalar=1.0, reason_codes=[]
    )

    # Backtester loop variables
    equity = config.starting_equity
    trades: list[PaperTrade] = []
    regime_counts: dict[str, int] = {}
    permission_counts: dict[str, int] = {}
    open_trade: OpenTradeState | None = None
    
    # 5-minute rolling window history for price change (lookback_ns = 300,000,000,000)
    price_history: deque[tuple[int, float]] = deque()
    # cvd_5m history for quantile filters
    cvd_history: deque[float] = deque(maxlen=args.cvd_quantile_window)
    # volume bars history
    bars: deque[VolumeBar] = deque(maxlen=2000)
    htf_changes_history: deque[float] = deque(maxlen=2000)
    
    # CVD confirm tracker
    pending_signal: dict | None = None
    cvd_confirm_count = 0
    cvd_prev_5m = 0.0
    last_session_key: int | None = None

    print(f"Running consolidated backtest...")
    rows_seen = 0
    signals_seen = 0

    for row in df.itertuples():
        rows_seen += 1
        ts = int(row.end_ts_ns)
        close = float(row.close)
        high = float(row.high)
        low = float(row.low)

        # Reset session if needed
        if config.use_session_cvd_reset:
            hour_ns = 3_600_000_000_000
            day_ns = 24 * hour_ns
            tick_hour = (ts // hour_ns) % 24
            if tick_hour == config.session_boundary_hour_utc:
                session_key = ts // day_ns
                if last_session_key != session_key:
                    pending_signal = None
                    cvd_confirm_count = 0
                    cvd_prev_5m = 0.0
                    last_session_key = session_key

        # Construct VolumeBar object
        bar_obj = VolumeBar(
            start_ts_ns=int(row.start_ts_ns),
            end_ts_ns=int(row.end_ts_ns),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            buy_volume=float(row.buy_volume),
            sell_volume=float(row.sell_volume),
            delta=float(row.delta),
            cumulative_delta=float(row.cumulative_delta),
            ticks=int(row.ticks),
        )
        bars.append(bar_obj)

        # Compute HTF change
        hour_ns = 3_600_000_000_000
        target_ts = ts - hour_ns
        htf_change = 0.0
        for b in bars:
            if b.end_ts_ns >= target_ts:
                htf_change = bar_obj.cumulative_delta - b.cumulative_delta
                break
        htf_changes_history.append(abs(htf_change))

        # Update rolling price history
        price_history.append((ts, close))
        cutoff_ns = ts - 300_000_000_000
        while price_history and price_history[0][0] < cutoff_ns:
            price_history.popleft()

        # Compute price change
        price_change = 0.0
        if len(price_history) >= 2 and price_history[0][1] != 0:
            price_change = (price_history[-1][1] - price_history[0][1]) / price_history[0][1]

        cvd_history.append(float(row.cvd_5m))

        # Check exits
        if open_trade is not None:
            side = open_trade.side
            entry_price = open_trade.entry_price
            
            # Excursion logic
            if side > 0:
                open_trade = open_trade.with_excursion(low)
                open_trade = open_trade.with_excursion(high)
            else:
                open_trade = open_trade.with_excursion(high)
                open_trade = open_trade.with_excursion(low)

            exit_reason = None
            exit_price = close

            if config.use_cvd_exit:
                if (side < 0 and row.cvd_5m > 0) or (side > 0 and row.cvd_5m < 0):
                    exit_reason = "CVD_EXIT"

            if exit_reason is None and config.use_tpsl:
                if side > 0:
                    if low <= entry_price * (1 - config.stop_pct):
                        exit_reason = "STOP"
                        exit_price = entry_price * (1 - config.stop_pct)
                    elif high >= entry_price * (1 + config.target_pct):
                        exit_reason = "TARGET"
                        exit_price = entry_price * (1 + config.target_pct)
                else:
                    if high >= entry_price * (1 + config.stop_pct):
                        exit_reason = "STOP"
                        exit_price = entry_price * (1 + config.stop_pct)
                    elif low <= entry_price * (1 - config.target_pct):
                        exit_reason = "TARGET"
                        exit_price = entry_price * (1 - config.target_pct)

            if exit_reason is None and ts >= open_trade.exit_after_ts_ns:
                exit_reason = "TIME"

            if exit_reason is not None:
                # Apply slippage and fees
                bps = config.slippage_bps_per_side / 10_000
                direction = -side
                actual_exit_price = exit_price * (1 + direction * bps)
                gross = side * (actual_exit_price - entry_price) / entry_price * open_trade.notional
                fees = open_trade.notional * (config.fee_bps_per_side * 2 / 10_000)
                pnl = gross - fees
                
                paper_trade = PaperTrade(
                    entry_ts_ns=open_trade.entry_ts_ns,
                    exit_ts_ns=ts,
                    side=side,
                    entry_price=round(entry_price, 2),
                    exit_price=round(actual_exit_price, 2),
                    notional=round(open_trade.notional, 2),
                    pnl=round(pnl, 2),
                    return_pct=pnl / open_trade.notional if open_trade.notional else 0.0,
                    signal_id=open_trade.signal_id,
                    permission_verdict=open_trade.permission_verdict,
                    reason_codes=open_trade.reason_codes,
                    exit_reason=exit_reason,
                    max_adverse=round(open_trade.max_adverse, 6),
                    max_favorable=round(open_trade.max_favorable, 6),
                )
                trades.append(paper_trade)
                equity += pnl
                open_trade = None
                cvd_prev_5m = float(row.cvd_5m)
                continue

        # Classify regime
        regime = classifier.classify(
            timestamp_ns=ts,
            price_change_5m_pct=price_change,
            cvd_session=float(row.cvd_5m),
        )
        regime_counts[regime.hard_label] = regime_counts.get(regime.hard_label, 0) + 1

        auction_state = auction_engine.update(
            timestamp_ns=ts,
            price_change_5m_pct=price_change,
            cvd_session=float(row.cvd_5m),
            value_acceptance=regime.hard_label in {"TREND_BULL", "TREND_BEAR"},
        )

        # Check CV Quantile extreme
        cvd_quantile_ok = True
        if config.use_cvd_quantile_filter:
            if len(cvd_history) < config.cvd_quantile_min_samples:
                cvd_quantile_ok = False
            else:
                sorted_abs = sorted(abs(val) for val in cvd_history)
                idx = min(len(sorted_abs) - 1, int(len(sorted_abs) * config.cvd_quantile))
                cvd_quantile_ok = abs(row.cvd_5m) >= sorted_abs[idx]

        # Signal Generator
        signal = None
        if config.signal_mode == "momentum":
            # Momentum logic
            if regime.hard_label.startswith("TREND"):
                side = 0
                if row.cvd_5m >= config.divergence_threshold:
                    side = +1
                elif row.cvd_5m <= -config.divergence_threshold:
                    side = -1
                
                if side != 0 and not (regime.hard_label == "TREND_BULL" and side < 0) and not (regime.hard_label == "TREND_BEAR" and side > 0):
                    if row.footprint_bias == side:
                        if not config.use_cvd_quantile_filter or cvd_quantile_ok:
                            strength = min(1.0, abs(row.cvd_5m) / (config.divergence_threshold * 2))
                            if row.footprint_stacked:
                                strength = min(1.0, strength + 0.15)
                            if row.delta_exhaustion == "NONE":
                                strength = min(1.0, strength + 0.10)
                            signal = {
                                "id": f"CVDDIV_{ts}_{side}",
                                "side": side,
                                "strength": round(strength, 6),
                                "price": close,
                            }
        else:
            # Divergence logic
            if config.divergence_type == "swing":
                if classifier.gate_for_signal_mode(regime, "divergence") and (not config.use_cvd_quantile_filter or cvd_quantile_ok):
                    near_high = close >= row.swing_price_high * 0.999
                    bearish_div = row.cvd_15m < row.swing_cvd_high - config.divergence_threshold_15m
                    near_low = close <= row.swing_price_low * 1.001
                    bullish_div = row.cvd_15m > row.swing_cvd_low + config.divergence_threshold_15m
                    
                    side = 0
                    if near_high and bearish_div:
                        side = -1
                    elif near_low and bullish_div:
                        side = +1
                    
                    if side != 0:
                        # Session extreme gate
                        at_extreme = True
                        if config.use_session_extreme_gate:
                            if side == -1:
                                at_extreme = close >= row.session_high * (1 - config.session_extreme_pct)
                            else:
                                at_extreme = close <= row.session_low * (1 + config.session_extreme_pct)
                        
                        if at_extreme:
                            ref_cvd = row.swing_cvd_high if side == -1 else row.swing_cvd_low
                            magnitude = abs(row.cvd_15m - ref_cvd)
                            strength = min(1.0, magnitude / (config.divergence_threshold_15m * 2))
                            if row.footprint_bias == side:
                                strength = min(1.0, strength + 0.10)
                            if abs(row.vwap_deviation) < 0.002:
                                strength = min(1.0, strength + 0.10)
                            if config.invert_signal_side:
                                side = -side
                            signal = {
                                "id": f"SWING_{ts}_{side}",
                                "side": side,
                                "strength": round(strength, 6),
                                "price": close,
                            }
            elif config.divergence_type == "volume_bar_cvd":
                lookback = config.divergence_lookback_bars
                if len(bars) > lookback:
                    bars_list = list(bars)
                    prior_bars = bars_list[-lookback - 1 : -1]
                    current_bar = bars_list[-1]

                    highs = [b.high for b in prior_bars]
                    lows = [b.low for b in prior_bars]
                    cvds = [b.cumulative_delta for b in prior_bars]

                    prior_high = max(highs)
                    prior_low = min(lows)
                    prior_cvd_high = max(cvds)
                    prior_cvd_low = min(cvds)

                    bearish = current_bar.high >= prior_high and current_bar.cumulative_delta < prior_cvd_high
                    bullish = current_bar.low <= prior_low and current_bar.cumulative_delta > prior_cvd_low

                    if bearish != bullish:
                        side = -1 if bearish else +1

                        # Check HTF filter
                        flat_abs = 0.0
                        if len(htf_changes_history) >= 10:
                            sorted_values = sorted(htf_changes_history)
                            idx = int((len(sorted_values) - 1) * config.htf_flat_quantile)
                            flat_abs = sorted_values[idx]

                        if side == -1:
                            allowed = htf_change <= flat_abs
                        else:
                            allowed = htf_change >= -flat_abs

                        if allowed:
                            strength = min(1.0, abs(current_bar.cumulative_delta) / 100.0)
                            if config.invert_signal_side:
                                side = -side
                            signal = {
                                "id": f"VOLBARCVD_{ts}_{side}",
                                "side": side,
                                "strength": round(strength, 6),
                                "price": close,
                            }
            else:
                # Opposite delta divergence logic
                if classifier.gate_for_signal_mode(regime, "divergence"):
                    cvd_1h = row.cvd_1h
                    side = 0
                    if cvd_1h <= -config.divergence_threshold_1h:
                        side = -1
                    elif cvd_1h >= config.divergence_threshold_1h:
                        side = +1
                    
                    if side != 0:
                        cond = False
                        if side == -1:
                            cond = price_change > config.price_change_threshold and row.cvd_15m <= -config.divergence_threshold_15m
                        else:
                            cond = price_change < -config.price_change_threshold and row.cvd_15m >= config.divergence_threshold_15m
                        
                        if cond:
                            cvd_5m = row.cvd_5m
                            cvd_cond = (side == -1 and cvd_5m < 0 and abs(cvd_5m) >= config.divergence_threshold_5m) or \
                                       (side == +1 and cvd_5m > 0 and abs(cvd_5m) >= config.divergence_threshold_5m)
                            if cvd_cond:
                                if not config.use_cvd_quantile_filter or cvd_quantile_ok:
                                     at_extreme = True
                                     if config.use_session_extreme_gate:
                                         if side == -1:
                                             at_extreme = close >= row.session_high * (1 - config.session_extreme_pct)
                                         else:
                                             at_extreme = close <= row.session_low * (1 + config.session_extreme_pct)
                                     
                                     if at_extreme:
                                         strength = min(1.0, abs(row.cvd_15m) / (config.divergence_threshold_15m * 2))
                                         if row.footprint_bias == side:
                                             strength = min(1.0, strength + 0.10)
                                         if abs(row.vwap_deviation) < 0.002:
                                             strength = min(1.0, strength + 0.10)
                                         if config.invert_signal_side:
                                             side = -side
                                         signal = {
                                             "id": f"CVDMTF_{ts}_{side}",
                                             "side": side,
                                             "strength": round(strength, 6),
                                             "price": close,
                                         }

        # CVD reversal confirmation (delay entry)
        if config.signal_mode == "divergence" and config.use_cvd_reversal_confirm:
            if signal is not None and pending_signal is None:
                pending_signal = signal
                cvd_confirm_count = 0
            elif pending_signal is not None:
                ps_side = pending_signal["side"]
                cvd_moving_right = (ps_side == -1 and row.cvd_5m < cvd_prev_5m) or \
                                   (ps_side == +1 and row.cvd_5m > cvd_prev_5m)
                if cvd_moving_right:
                    cvd_confirm_count += 1
                else:
                    cvd_confirm_count = 0
                
                price_moved_against = (ps_side == -1 and close > pending_signal["price"] * 1.002) or \
                                      (ps_side == +1 and close < pending_signal["price"] * 0.998)
                if price_moved_against:
                    pending_signal = None
                    cvd_confirm_count = 0
                elif cvd_confirm_count >= config.cvd_confirm_ticks:
                    signal = pending_signal
                    pending_signal = None
                    cvd_confirm_count = 0
                else:
                    signal = None

        cvd_prev_5m = float(row.cvd_5m)
        if signal is None:
            continue

        signals_seen += 1
        
        # Evaluate permission
        permission = permission_engine.evaluate(
            signal_id=signal["id"],
            timestamp_ns=ts,
            trade_side=signal["side"],
            raw_strength=signal["strength"],
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=True,
            cvd_5m=row.cvd_5m,
            signal_mode=config.signal_mode,
            vwap_deviation=row.vwap_deviation if config.use_vwap_gate else None,
            auction_state=auction_state,
        )
        permission_counts[permission.verdict] = permission_counts.get(permission.verdict, 0) + 1
        if permission.verdict not in {"APPROVE", "REDUCED"}:
            continue

        bps = config.slippage_bps_per_side / 10_000
        direction = signal["side"]
        actual_entry_price = close * (1 + direction * bps)
        notional = equity * permission.permitted_size
        open_trade = OpenTradeState(
            entry_ts_ns=ts,
            side=signal["side"],
            entry_price=actual_entry_price,
            notional=notional,
            signal_id=signal["id"],
            permission_verdict=permission.verdict,
            reason_codes=tuple(record.code for record in permission.chain),
            exit_after_ts_ns=ts + config.hold_ns,
        )

    # Post backtest calculations
    returns = [trade.return_pct for trade in trades]
    adverse_list = [trade.max_adverse for trade in trades]
    favorable_list = [trade.max_favorable for trade in trades]
    total_pnl = sum(trade.pnl for trade in trades)
    sharpe = sharpe_ratio(returns)
    dsr = deflated_sharpe_probability(
        sharpe=sharpe,
        n_trials=config.n_trials,
        skew=skewness(returns),
        kurt=kurtosis(returns),
        n_obs=len(returns),
    )
    wins = sum(1 for trade in trades if trade.pnl > 0)
    exit_reasons_counter = Counter(trade.exit_reason for trade in trades)
    
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
        exit_reasons=dict(sorted(exit_reasons_counter.items())),
        permission_counts=dict(sorted(permission_counts.items())),
        mae_stats=_pct_stats(adverse_list),
        mfe_stats=_pct_stats(favorable_list),
        config=asdict(config),
    )

    payload = {
        "chunk": "B_CACHED_CONSOLIDATED",
        "archive": "ALL_133_ARCHIVES",
        "signal_mode": args.signal_mode,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "report": asdict(report),
        "sample_trades": [asdict(trade) for trade in trades[:10]],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.dsr_passed else 1

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

class Counter(dict):
    def __init__(self, iterable=None):
        super().__init__()
        if iterable is not None:
            for item in iterable:
                self[item] = self.get(item, 0) + 1

if __name__ == "__main__":
    sys.exit(main())
