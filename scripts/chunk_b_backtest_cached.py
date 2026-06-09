#!/usr/bin/env python3
"""Run Chunk B backtest using pre-computed indicators from Parquet cache."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
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
from prime.footprint_confluence import footprint_confirms_fade
from prime.volume_bar_cvd import (
    entry_delta_aligns,
    htf_change_at,
    htf_flat_abs_threshold,
    volume_bar_cvd_signal,
    volume_bar_cvd_signal_d5,
)
from research.manifests import append_manifest_jsonl, wrap_result_payload
from research.signal_scorecard import SignalEvent, SignalScorecard
from prime.auction_state import AuctionStateEngine
from storage.hot_path import assert_nvme_archive, assert_nvme_path, hot_btcusdt_aggtrades_dir
from features.vpin import VPINEngine, ToxicityState

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
CACHE_DIR = Path("results/indicator_cache")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", default="BTCUSDT-aggTrades-2026-05-21.zip")
    parser.add_argument("--max-rows", type=int, default=None)
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
    parser.add_argument(
        "--use-time-exit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable the wall-clock hold timeout; disable for pure volume-bar horizon tests",
    )
    parser.add_argument("--stop-pct", type=float, default=0.003)
    parser.add_argument("--target-pct", type=float, default=0.006)
    parser.add_argument("--use-tpsl", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-vwap-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--vwap-structure-pct", type=float, default=0.003)
    parser.add_argument("--use-auction-state-gate", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-vpin-gate", action=argparse.BooleanOptionalAction, default=False, help="Use VPIN toxicity gate to block entries")
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
    parser.add_argument("--starting-equity", type=float, default=None)
    parser.add_argument("--trades-out", type=Path, default=None, help="Write all trades as JSON lines")
    parser.add_argument(
        "--scale-target-by-strength",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Scale target_pct dynamically by (1.0 + signal_strength)",
    )
    parser.add_argument(
        "--exit-after-volume-bars",
        type=int,
        default=None,
        help="Exit open trade after N volume bars (aligns with diagnostic horizon)",
    )
    parser.add_argument(
        "--use-regime-gate-volume-bar",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Gate volume_bar_cvd to RANGING/UNKNOWN regimes (mean-reversion eligibility)",
    )
    parser.add_argument(
        "--use-footprint-confluence",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Require cached footprint_bias to align with fade side",
    )
    parser.add_argument(
        "--footprint-require-stacked",
        action="store_true",
        default=False,
        help="Require footprint_stacked when footprint gate is on",
    )
    parser.add_argument(
        "--footprint-invert-for-fade",
        action="store_true",
        default=False,
        help="Require opposing footprint_bias (absorption hypothesis)",
    )
    parser.add_argument(
        "--no-footprint-allow-neutral",
        action="store_true",
        default=False,
        help="Block neutral footprint_bias when footprint gate is on",
    )
    parser.add_argument(
        "--approve-only-permission",
        action="store_true",
        default=False,
        help="Skip REDUCED permission trades (APPROVE only)",
    )
    parser.add_argument(
        "--require-delta-exhaustion-fade",
        action="store_true",
        default=False,
        help="Require delta_exhaustion aligned with fade side",
    )
    parser.add_argument("--signal-horizon-bars", type=int, default=5)
    parser.add_argument(
        "--use-delta-rev-2-entry",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="D5 entry: wait 2 bar deltas confirm fade after divergence",
    )
    parser.add_argument(
        "--require-entry-delta-alignment",
        action="store_true",
        default=False,
        help="Require current volume-bar delta direction to align with the trade side",
    )
    parser.add_argument(
        "--base-position-pct",
        type=float,
        default=0.01,
        help="Base position size as fraction of equity (default: 0.01)",
    )
    parser.add_argument(
        "--entry-lag-bars",
        type=int,
        choices=(0, 1),
        default=0,
        help="Enter on the signal-bar close (0, legacy) or next-bar open (1, lookahead-safe)",
    )
    parser.add_argument(
        "--manifest-jsonl",
        type=Path,
        default=Path("results/manifest.jsonl"),
        help="Append experiment/result manifest records",
    )
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
    dest = assert_nvme_path(args.dest.resolve(), label="backtest dest")
    archive = dest / args.archive
    assert_nvme_archive(archive)
    cache_root = assert_nvme_path((Path(__file__).resolve().parents[1] / CACHE_DIR).resolve(), label="indicator cache")
    suffix = f".maxrows-{args.max_rows}" if args.max_rows is not None else ""
    cache_file = cache_root / f"{args.archive}.threshold-{int(args.threshold_btc)}{suffix}.parquet"

    # Auto-generate cache if missing
    if not cache_file.is_file():
        print(f"Parquet cache not found. Precomputing indicators first...")
        python_bin = sys.executable
        script_path = Path(__file__).resolve().parent / "cache_indicators.py"
        cmd = [
            python_bin, str(script_path),
            "--dest", str(dest),
            "--archive", args.archive,
            "--threshold-btc", str(args.threshold_btc),
            "--progress"
        ]
        if args.max_rows is not None:
            cmd.extend(["--max-rows", str(args.max_rows)])
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("Failed to generate Parquet cache.", file=sys.stderr)
            return 2

    # Load Parquet file
    df = pd.read_parquet(cache_file)
    
    start_ns = parse_datetime_ns(args.start_date)
    end_ns = parse_datetime_ns(args.end_date)
    
    if start_ns is not None:
        df = df[df["end_ts_ns"] >= start_ns]
    if end_ns is not None:
        df = df[df["end_ts_ns"] <= end_ns]

    # Setup configurations and classifiers
    config = ChunkBBacktestConfig(
        starting_equity=args.starting_equity if args.starting_equity is not None else 100_000.0,
        signal_mode=args.signal_mode,
        divergence_threshold=args.divergence_threshold,
        price_change_threshold=args.price_change_threshold,
        divergence_threshold_1h=args.divergence_threshold_1h,
        divergence_threshold_15m=args.divergence_threshold_15m,
        divergence_threshold_5m=args.divergence_threshold_5m,
        hold_ns=args.hold_ns,
        use_time_exit=args.use_time_exit,
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
        use_vpin_gate=args.use_vpin_gate,
        exit_after_volume_bars=args.exit_after_volume_bars,
        use_regime_gate_volume_bar=args.use_regime_gate_volume_bar,
        use_footprint_confluence=args.use_footprint_confluence,
        footprint_require_stacked=args.footprint_require_stacked,
        footprint_invert_for_fade=args.footprint_invert_for_fade,
        footprint_allow_neutral=not args.no_footprint_allow_neutral,
        approve_only_permission=args.approve_only_permission,
        require_delta_exhaustion_fade=args.require_delta_exhaustion_fade,
        use_delta_rev_2_entry=args.use_delta_rev_2_entry,
        require_entry_delta_alignment=args.require_entry_delta_alignment,
        base_position_pct=args.base_position_pct,
    )
    uses_volume_bar_edge = (
        config.signal_mode == "divergence" and config.divergence_type == "volume_bar_cvd"
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
    vpin_engine = VPINEngine() if config.use_vpin_gate else None
    
    needs_volume_bar_history = config.signal_mode == "divergence" and config.divergence_type == "volume_bar_cvd"
    needs_cvd_confirm = (
        config.signal_mode == "divergence"
        and config.use_cvd_reversal_confirm
        and not uses_volume_bar_edge
    )

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
    pending_entry: dict | None = None
    
    # 5-minute rolling window history for price change (lookback_ns = 300,000,000,000)
    price_history: deque[tuple[int, float]] = deque()
    # cvd_5m history for quantile filters
    cvd_history: deque[float] = deque(maxlen=args.cvd_quantile_window)
    # volume bars history
    bars: deque[VolumeBar] | None = deque(maxlen=2000) if needs_volume_bar_history else None
    htf_changes_history: deque[float] | None = deque(maxlen=2000) if needs_volume_bar_history else None
    
    # CVD confirm tracker
    pending_signal: dict | None = None
    cvd_confirm_count = 0
    cvd_prev_5m = 0.0

    horizon_bars = args.exit_after_volume_bars or args.signal_horizon_bars
    signal_scorecard = SignalScorecard(horizon_bars=horizon_bars)
    bar_closes = df["close"].astype(float).tolist()

    print(f"Running backtest over cached bars...")
    rows_seen = 0
    signals_seen = 0

    for row in df.itertuples():
        rows_seen += 1
        bar_index = rows_seen - 1
        ts = int(row.end_ts_ns)
        close = float(row.close)
        high = float(row.high)
        low = float(row.low)

        if pending_entry is not None and open_trade is None:
            direction = int(pending_entry["side"])
            bps = config.slippage_bps_per_side / 10_000
            actual_entry_price = float(row.open) * (1 + direction * bps)
            open_trade = OpenTradeState(
                entry_ts_ns=int(row.start_ts_ns),
                side=direction,
                entry_price=actual_entry_price,
                notional=equity * float(pending_entry["permitted_size"]),
                signal_id=str(pending_entry["signal_id"]),
                permission_verdict=str(pending_entry["permission_verdict"]),
                reason_codes=tuple(pending_entry["reason_codes"]),
                exit_after_ts_ns=int(row.start_ts_ns) + config.hold_ns,
                exit_after_volume_bars=config.exit_after_volume_bars,
                target_pct=float(pending_entry["target_pct"]),
                stop_pct=config.stop_pct,
            )
            pending_entry = None

        htf_change = 0.0
        if needs_volume_bar_history:
            assert bars is not None
            assert htf_changes_history is not None
            # Construct VolumeBar object only for the volume-bar CVD path.
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

            htf_change = htf_change_at(bars, bar_obj.end_ts_ns, bar_obj.cumulative_delta)
            htf_changes_history.append(abs(htf_change))

        # Update VPIN engine
        vpin_snap = None
        if vpin_engine is not None:
            vpin_snap = vpin_engine.update_volume_bar(float(row.buy_volume), float(row.sell_volume))

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
            if open_trade.exit_after_volume_bars is not None:
                open_trade = replace(
                    open_trade,
                    bars_since_entry=open_trade.bars_since_entry + 1,
                )

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
                t_pct = open_trade.target_pct if open_trade.target_pct is not None else config.target_pct
                s_pct = open_trade.stop_pct if open_trade.stop_pct is not None else config.stop_pct
                if side > 0:
                    if low <= entry_price * (1 - s_pct):
                        exit_reason = "STOP"
                        exit_price = entry_price * (1 - s_pct)
                    elif high >= entry_price * (1 + t_pct):
                        exit_reason = "TARGET"
                        exit_price = entry_price * (1 + t_pct)
                else:
                    if high >= entry_price * (1 + s_pct):
                        exit_reason = "STOP"
                        exit_price = entry_price * (1 + s_pct)
                    elif low <= entry_price * (1 - t_pct):
                        exit_reason = "TARGET"
                        exit_price = entry_price * (1 - t_pct)

            if (
                exit_reason is None
                and open_trade.exit_after_volume_bars is not None
                and open_trade.bars_since_entry >= open_trade.exit_after_volume_bars
            ):
                exit_reason = "BAR_EXIT"
            if exit_reason is None and config.use_time_exit and ts >= open_trade.exit_after_ts_ns:
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
                if needs_cvd_confirm:
                    cvd_prev_5m = float(row.cvd_5m)
                if args.entry_lag_bars == 0:
                    continue
            if args.entry_lag_bars == 1:
                # In lagged-entry mode, only skip while a trade is still open.
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
                assert bars is not None
                assert htf_changes_history is not None
                if config.use_regime_gate_volume_bar and not classifier.gate_for_signal_mode(
                    regime, "divergence"
                ):
                    signal_scorecard.record_drop("regime_gate")
                elif not config.use_regime_gate_volume_bar or classifier.gate_for_signal_mode(
                    regime, "divergence"
                ):
                    flat_abs = htf_flat_abs_threshold(
                        htf_changes_history,
                        quantile=config.htf_flat_quantile,
                    )
                    if config.use_delta_rev_2_entry:
                        signal = volume_bar_cvd_signal_d5(
                            bars,
                            lookback_bars=config.divergence_lookback_bars,
                            htf_change=htf_change,
                            flat_abs=flat_abs,
                            timestamp_ns=ts,
                            price=close,
                            invert_signal_side=config.invert_signal_side,
                        )
                    else:
                        signal = volume_bar_cvd_signal(
                            bars,
                            lookback_bars=config.divergence_lookback_bars,
                            htf_change=htf_change,
                            flat_abs=flat_abs,
                            timestamp_ns=ts,
                            price=close,
                            invert_signal_side=config.invert_signal_side,
                        )
                    if signal is not None and config.use_footprint_confluence:
                        if not footprint_confirms_fade(
                            trade_side=int(signal["side"]),
                            footprint_bias=int(row.footprint_bias),
                            footprint_stacked=bool(row.footprint_stacked),
                            require_stacked=config.footprint_require_stacked,
                            allow_neutral=config.footprint_allow_neutral,
                            invert_for_fade=config.footprint_invert_for_fade,
                        ):
                            signal_scorecard.record_drop("footprint_confluence")
                            signal = None
                    if signal is not None and config.require_delta_exhaustion_fade:
                        want = "BUY_EXHAUSTION" if int(signal["side"]) == -1 else "SELL_EXHAUSTION"
                        if row.delta_exhaustion != want:
                            signal_scorecard.record_drop("delta_exhaustion_mismatch")
                            signal = None
                    if (
                        signal is not None
                        and config.require_entry_delta_alignment
                        and not entry_delta_aligns(int(signal["side"]), float(row.delta))
                    ):
                        signal_scorecard.record_drop("entry_delta_misaligned")
                        signal = None
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

        if needs_cvd_confirm:
            cvd_prev_5m = float(row.cvd_5m)
        if signal is None:
            continue

        signals_seen += 1
        if signal is not None:
            signal_scorecard.add(
                SignalEvent(
                    bar_index=bar_index,
                    timestamp_ns=ts,
                    side=int(signal["side"]),
                    entry_price=close,
                    signal_id=signal["id"],
                    permission_verdict="PENDING",
                )
            )

        # Evaluate permission
        permission = permission_engine.evaluate(
            signal_id=signal["id"],
            timestamp_ns=ts,
            trade_side=signal["side"],
            raw_strength=signal["strength"],
            quality_snapshot=quality,
            regime=regime,
            cvd_divergence=not uses_volume_bar_edge,
            cvd_5m=row.cvd_5m,
            signal_mode=config.signal_mode,
            vwap_deviation=(
                row.vwap_deviation
                if config.use_vwap_gate and not uses_volume_bar_edge
                else None
            ),
            auction_state=auction_state,
            divergence_type=config.divergence_type,
        )
        permission_counts[permission.verdict] = permission_counts.get(permission.verdict, 0) + 1
        allowed_verdicts = {"APPROVE"} if config.approve_only_permission else {"APPROVE", "REDUCED"}
        if permission.verdict not in allowed_verdicts:
            signal_scorecard.record_drop(f"permission_{permission.verdict}")
            continue

        # Check VPIN toxicity
        if vpin_engine is not None and vpin_snap is not None:
            if vpin_snap.toxicity_state in {ToxicityState.HIGH_TOXICITY}:
                signal_scorecard.record_drop("vpin_toxicity")
                continue

        t_pct = config.target_pct
        if args.scale_target_by_strength:
            # Scale target fractionally based on signal strength to allow high conviction signals to run
            # but preserve a high win rate by not over-extending targets for standard/weaker signals.
            t_pct = config.target_pct * (0.8 + 0.25 * float(signal.get("strength", 0.0)))

        entry = {
            "side": signal["side"],
            "permitted_size": permission.permitted_size,
            "signal_id": signal["id"],
            "permission_verdict": permission.verdict,
            "reason_codes": tuple(record.code for record in permission.chain),
            "target_pct": t_pct,
        }
        if args.entry_lag_bars == 1:
            pending_entry = entry
        else:
            bps = config.slippage_bps_per_side / 10_000
            direction = signal["side"]
            actual_entry_price = close * (1 + direction * bps)
            open_trade = OpenTradeState(
                entry_ts_ns=ts,
                side=direction,
                entry_price=actual_entry_price,
                notional=equity * permission.permitted_size,
                signal_id=signal["id"],
                permission_verdict=permission.verdict,
                reason_codes=entry["reason_codes"],
                exit_after_ts_ns=ts + config.hold_ns,
                exit_after_volume_bars=config.exit_after_volume_bars,
                target_pct=t_pct,
                stop_pct=config.stop_pct,
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

    if args.trades_out is not None:
        args.trades_out.parent.mkdir(parents=True, exist_ok=True)
        with args.trades_out.open("w", encoding="utf-8") as handle:
            for trade in trades:
                handle.write(json.dumps(asdict(trade), sort_keys=True))
                handle.write("\n")

    report_dict = asdict(report)
    report_dict["entry_lag_bars"] = args.entry_lag_bars
    report_dict["same_bar_entry"] = args.entry_lag_bars == 0
    report_dict["lookahead_safe"] = args.entry_lag_bars == 1
    signal_only = signal_scorecard.finalize(bar_closes)
    report_dict["signal_scorecard"] = signal_only
    report_dict["trade_scorecard"] = {
        "trades": report.trades,
        "win_rate": report.win_rate,
        "total_pnl": report.total_pnl,
        "sharpe": report.sharpe,
    }

    payload = {
        "chunk": "B_CACHED",
        "archive": args.archive,
        "strategy": config.divergence_type if config.signal_mode == "divergence" else config.signal_mode,
        "signal_mode": args.signal_mode,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "report": report_dict,
        "trade_count": len(trades),
        "sample_trades": [asdict(trade) for trade in trades[:5]],
    }
    command = " ".join(sys.argv)
    experiment_id = f"{args.archive}:{config.signal_mode}:{config.divergence_type}"
    payload = wrap_result_payload(
        payload,
        experiment_id=experiment_id,
        command=command,
        output_path=args.manifest_jsonl,
        repo_root=Path(__file__).resolve().parents[1],
    )
    append_manifest_jsonl(
        args.manifest_jsonl,
        {
            "experiment_manifest": payload["experiment_manifest"],
            "result_manifest": payload["result_manifest"],
        },
    )
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
