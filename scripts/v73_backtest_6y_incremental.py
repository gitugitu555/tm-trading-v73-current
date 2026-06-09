#!/usr/bin/env python3
"""V7.3 six-year backtest: volume-bar CVD edge profile (measured signal path)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prime.performance import deflated_sharpe_probability, kurtosis, sharpe_ratio, skewness
from research.mae_mfe_exit_lab import MAEMFEExitLab
from research.trade_path_db import TradePathDatabase
from storage.hot_path import assert_nvme_archive, hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
CACHE_DIR = ROOT / "results/indicator_cache"
DEFAULT_WORK_DIR = ROOT / "results/v73_backtest_6y_work"
THRESHOLD = 300.0
LOOKBACK = 40
EXIT_BARS = 16
STOP_PCT = 0.03
TARGET_PCT = 0.004


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    p.add_argument("--threshold-btc", type=float, default=THRESHOLD)
    p.add_argument("--divergence-lookback-bars", type=int, default=LOOKBACK)
    p.add_argument("--exit-after-volume-bars", type=int, default=EXIT_BARS)
    p.add_argument(
        "--use-time-exit",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable the wall-clock hold timeout; disable for pure volume-bar horizon tests",
    )
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--end-index", type=int, default=None)
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/v73_backtest_6y_volume_bar_cvd.json",
    )
    p.add_argument("--use-auction-state-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--use-regime-gate-volume-bar", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--stop-pct", type=float, default=STOP_PCT)
    p.add_argument("--target-pct", type=float, default=TARGET_PCT)
    p.add_argument("--use-footprint-confluence", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--invert-signal-side", action="store_true", default=False)
    p.add_argument("--require-entry-delta-alignment", action="store_true", default=False)
    p.add_argument("--approve-only-permission", action="store_true", default=False)
    p.add_argument("--scale-target-by-strength", action="store_true", default=False)
    p.add_argument("--entry-lag-bars", type=int, choices=(0, 1), default=1)
    p.add_argument("--use-market-profile-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--use-anti-pattern-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--use-risk-state-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--use-vpin-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--market-profile-lookback-bars", type=int, default=120)
    p.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Per-archive report/trades directory (default: results/v73_backtest_6y_work)",
    )
    p.add_argument("--resume", action="store_true")
    p.add_argument("--starting-equity", type=float, default=None)
    p.add_argument("--base-position-pct", type=float, default=0.01)
    p.add_argument(
        "--trade-path-out",
        type=Path,
        default=ROOT / "results/v73_trade_path_db.jsonl",
        help="Write an aggregated trade-path JSONL database",
    )
    p.add_argument(
        "--mae-mfe-out",
        type=Path,
        default=ROOT / "results/v73_mae_mfe_report.json",
        help="Write aggregated MAE/MFE research report",
    )
    return p.parse_args()


_DAILY_ARCHIVE = re.compile(r"BTCUSDT-aggTrades-\d{4}-\d{2}-\d{2}\.zip$")
_MONTHLY_ARCHIVE = re.compile(r"BTCUSDT-aggTrades-\d{4}-\d{2}\.zip$")


def archives(dest: Path) -> list[Path]:
    """Binance ships monthly rollups plus daily files; skip monthlies when dailies exist."""
    all_a = sorted(a for a in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)
    months_with_daily = {
        m.group(1)
        for a in all_a
        if (m := re.match(r"BTCUSDT-aggTrades-(\d{4}-\d{2})-\d{2}\.zip", a.name))
    }
    out: list[Path] = []
    for a in all_a:
        if _MONTHLY_ARCHIVE.match(a.name):
            month_key = a.name.replace("BTCUSDT-aggTrades-", "").replace(".zip", "")
            if month_key in months_with_daily:
                continue
        out.append(a)
    return out


def cache_path(archive: Path, threshold: float) -> Path:
    return CACHE_DIR / f"{archive.name}.threshold-{int(threshold)}.parquet"


def ensure_cache(archive: Path, threshold: float, dest: Path) -> None:
    assert_nvme_archive(archive)
    target = cache_path(archive, threshold)
    if target.is_file():
        return
    # Shared NVMe cache: another job (e.g. v555 Codex) may be building this archive.
    for attempt in range(720):
        if target.is_file():
            if attempt:
                print(f"[cache-ready] {archive.name}", flush=True)
            return
        if attempt == 0:
            print(f"[cache-wait] {archive.name} (shared NVMe)", flush=True)
        elif attempt % 10 == 0:
            print(f"[cache-wait] {archive.name} … {attempt}m", flush=True)
        time.sleep(60)
    print(f"[cache] {archive.name} (NVMe)", flush=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/cache_indicators.py"),
            "--dest",
            str(dest),
            "--archive",
            archive.name,
            "--threshold-btc",
            str(threshold),
            "--progress",
        ],
        cwd=ROOT,
        check=True,
    )


def run_archive_backtest(
    archive: Path,
    *,
    threshold: float,
    dest: Path,
    lookback: int,
    exit_bars: int,
    starting_equity: float,
    use_auction_state_gate: bool,
    use_regime_gate_volume_bar: bool,
    use_footprint_confluence: bool,
    stop_pct: float,
    target_pct: float,
    trades_out: Path,
    invert_signal_side: bool = False,
    use_time_exit: bool = True,
    require_entry_delta_alignment: bool = False,
    approve_only_permission: bool = False,
    scale_target_by_strength: bool = False,
    base_position_pct: float = 0.01,
    entry_lag_bars: int = 1,
    use_market_profile_gate: bool = False,
    use_anti_pattern_gate: bool = False,
    use_risk_state_gate: bool = False,
    use_vpin_gate: bool = False,
    market_profile_lookback_bars: int = 120,
) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/chunk_b_backtest_cached.py"),
        "--dest",
        str(dest),
        "--archive",
        archive.name,
        "--threshold-btc",
        str(threshold),
        "--signal-mode",
        "divergence",
        "--divergence-type",
        "volume_bar_cvd",
        "--divergence-lookback-bars",
        str(lookback),
        "--exit-after-volume-bars",
        str(exit_bars),
        "--use-time-exit" if use_time_exit else "--no-use-time-exit",
        "--no-use-cvd-reversal-confirm",
        "--stop-pct",
        str(stop_pct),
        "--target-pct",
        str(target_pct),
        "--use-regime-gate-volume-bar" if use_regime_gate_volume_bar else "--no-use-regime-gate-volume-bar",
        "--use-footprint-confluence" if use_footprint_confluence else "--no-use-footprint-confluence",
        "--starting-equity",
        str(starting_equity),
        "--base-position-pct",
        str(base_position_pct),
        "--entry-lag-bars",
        str(entry_lag_bars),
        "--use-vpin-gate" if use_vpin_gate else "--no-use-vpin-gate",
        "--use-market-profile-gate" if use_market_profile_gate else "--no-use-market-profile-gate",
        "--use-anti-pattern-gate" if use_anti_pattern_gate else "--no-use-anti-pattern-gate",
        "--use-risk-state-gate" if use_risk_state_gate else "--no-use-risk-state-gate",
        "--market-profile-lookback-bars",
        str(market_profile_lookback_bars),
        "--trades-out",
        str(trades_out),
    ]
    if use_auction_state_gate:
        cmd.append("--use-auction-state-gate")
    else:
        cmd.append("--no-use-auction-state-gate")
    if invert_signal_side:
        cmd.append("--invert-signal-side")
    if require_entry_delta_alignment:
        cmd.append("--require-entry-delta-alignment")
    if approve_only_permission:
        cmd.append("--approve-only-permission")
    if scale_target_by_strength:
        cmd.append("--scale-target-by-strength")
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": f"/home/tokio/tm-trading-research:{ROOT}"},
    )
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    text = proc.stdout.strip()
    if not text:
        proc.check_returncode()
    start = text.find("{")
    if start < 0:
        raise RuntimeError(f"No JSON in backtest stdout for {archive.name}")
    payload = json.loads(text[start:])
    if proc.returncode not in (0, 1):
        proc.check_returncode()
    return payload


def load_trades(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def merge_reports(archive_reports: list[dict], all_trades: list[dict]) -> dict:
    rows_seen = sum(r["report"]["rows_seen"] for r in archive_reports)
    signals_seen = sum(r["report"]["signals_seen"] for r in archive_reports)
    signal_hits = 0
    signal_scored = 0
    for item in archive_reports:
        card = item["report"].get("signal_scorecard", {})
        scored = int(card.get("scored_events", 0))
        if scored:
            signal_hits += int(round(float(card.get("hit_rate", 0.0)) * scored))
            signal_scored += scored
    regime_counts: Counter[str] = Counter()
    permission_counts: Counter[str] = Counter()
    exit_reasons: Counter[str] = Counter()
    shadow_gate_counts: Counter[str] = Counter()
    trade_path_db = TradePathDatabase()
    mae_lab = MAEMFEExitLab()
    for item in archive_reports:
        regime_counts.update(item["report"].get("regime_counts", {}))
        permission_counts.update(item["report"].get("permission_counts", {}))
        exit_reasons.update(item["report"].get("exit_reasons", {}))
        shadow_gate_counts.update(item["report"].get("shadow_gate_counts", {}))

    returns = [t["return_pct"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]
    sharpe = sharpe_ratio(returns)
    dsr = deflated_sharpe_probability(
        sharpe=sharpe,
        n_trials=4,
        skew=skewness(returns),
        kurt=kurtosis(returns),
        n_obs=len(returns),
    )
    wins = sum(1 for p in pnls if p > 0)
    trend_rows = regime_counts.get("TREND_BULL", 0) + regime_counts.get("TREND_BEAR", 0)
    classified = sum(regime_counts.values())
    starting = (
        archive_reports[0]["report"].get("config", {}).get("starting_equity", 100_000.0)
        if archive_reports
        else 100_000.0
    )
    ending = archive_reports[-1]["report"]["ending_equity"] if archive_reports else starting

    for trade in all_trades:
        trade_path_db.add_from_trade_dict(
            trade,
            symbol="BTCUSDT",
            signal_family="volume_bar_cvd",
            regime="UNKNOWN",
            volatility_bucket="UNKNOWN",
        )
        mae_lab.add_from_paper_trade(
            trade_id=str(trade.get("signal_id", trade.get("trade_id", ""))),
            signal_id=str(trade.get("signal_id", trade.get("trade_id", ""))),
            symbol="BTCUSDT",
            side=int(trade.get("side", 0)),
            entry_ts_ns=int(trade.get("entry_ts_ns", 0)),
            exit_ts_ns=int(trade.get("exit_ts_ns", trade.get("entry_ts_ns", 0))),
            entry_price=float(trade.get("entry_price", 0.0)),
            exit_price=float(trade.get("exit_price", trade.get("entry_price", 0.0))),
            max_adverse=float(trade.get("max_adverse", 0.0)),
            max_favorable=float(trade.get("max_favorable", 0.0)),
            pnl=float(trade.get("pnl", 0.0)),
            exit_reason=str(trade.get("exit_reason", "UNKNOWN")),
            signal_family="volume_bar_cvd",
            regime="UNKNOWN",
            bars_held=int(trade.get("bars_held", 0)),
            max_hold_bars=int(trade.get("max_hold_bars", 0)),
            target_pct=float(trade.get("target_pct", 0.0)),
            stop_pct=float(trade.get("stop_pct", 0.03)),
            toxicity_state=trade.get("toxicity_state"),
            mlofi_zscore=_maybe_float(trade.get("mlofi_zscore")),
            book_agreement=_maybe_float(trade.get("book_agreement")),
        )

    trade_path_summary = trade_path_db.summary()
    mae_mfe_report = mae_lab.full_report()

    return {
        "rows_seen": rows_seen,
        "signals_seen": signals_seen,
        "trades": len(all_trades),
        "total_pnl": round(sum(pnls), 2),
        "starting_equity": round(starting, 2),
        "ending_equity": round(ending, 2),
        "sharpe": round(sharpe, 4),
        "deflated_sharpe_probability": round(dsr, 4),
        "dsr_passed": dsr >= 0.95 and sharpe >= 1.5,
        "win_rate": round(wins / len(all_trades), 4) if all_trades else 0.0,
        "regime_counts": dict(sorted(regime_counts.items())),
        "trend_coverage": round(trend_rows / classified, 4) if classified else 0.0,
        "exit_reasons": dict(sorted(exit_reasons.items())),
        "permission_counts": dict(sorted(permission_counts.items())),
        "archives_processed": len(archive_reports),
        "signal_scorecard_aggregate": {
            "scored_events": signal_scored,
            "hit_rate": round(signal_hits / signal_scored, 6) if signal_scored else 0.0,
        },
        "trade_scorecard": {
            "trades": len(all_trades),
            "win_rate": round(wins / len(all_trades), 4) if all_trades else 0.0,
            "total_pnl": round(sum(pnls), 2),
        },
        "entry_lag_bars": (
            archive_reports[0]["report"].get("entry_lag_bars", 0) if archive_reports else 0
        ),
        "same_bar_entry": (
            archive_reports[0]["report"].get("same_bar_entry", True) if archive_reports else True
        ),
        "lookahead_safe": (
            archive_reports[0]["report"].get("lookahead_safe", False) if archive_reports else False
        ),
        "shadow_gate_counts": dict(sorted(shadow_gate_counts.items())),
        "market_profile": archive_reports[-1]["report"].get("market_profile") if archive_reports else {},
        "mlofi_snapshot": archive_reports[-1]["report"].get("mlofi_snapshot") if archive_reports else {},
        "trade_path_db": {
            "summary": {
                "n_trades": trade_path_summary.n_trades,
                "n_wins": trade_path_summary.n_wins,
                "win_rate": trade_path_summary.win_rate,
                "total_pnl": trade_path_summary.total_pnl,
                "avg_return_pct": trade_path_summary.avg_return_pct,
                "avg_mae_r": trade_path_summary.avg_mae_r,
                "avg_mfe_r": trade_path_summary.avg_mfe_r,
                "avg_bars_held": trade_path_summary.avg_bars_held,
                "by_signal_family": trade_path_summary.by_signal_family,
                "by_regime": trade_path_summary.by_regime,
                "by_session_hour": trade_path_summary.by_session_hour,
                "by_exit_reason": trade_path_summary.by_exit_reason,
            }
        },
        "mae_mfe_exit_lab": {
            "all": mae_mfe_report.get("all", {}),
            "shadow_gates": mae_mfe_report.get("shadow_gates", {}),
        },
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def equity_through_last_report(all_archives: list[Path], work_dir: Path) -> float:
    """Chain ending_equity through consecutive reports from archive 0."""
    equity = 100_000.0
    for archive in all_archives:
        report_file = work_dir / f"{archive.name}.report.json"
        if not report_file.is_file():
            break
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        equity = float(payload["report"]["ending_equity"])
    return equity


def main() -> int:
    args = parse_args()
    work_dir = args.work_dir if args.work_dir is not None else DEFAULT_WORK_DIR
    work_dir.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    dest = hot_btcusdt_aggtrades_dir()
    all_archives = archives(dest)
    end = args.end_index if args.end_index is not None else len(all_archives)
    start_index = args.start_index
    equity = args.starting_equity if args.starting_equity is not None else 100_000.0
    all_trades: list[dict] = []
    archive_reports: list[dict] = []

    if args.resume:
        # Always scan from archive 0; skip months that already have *.report.json.
        equity = equity_through_last_report(all_archives, work_dir)
        for trades_file in sorted(work_dir.glob("*.trades.jsonl")):
            all_trades.extend(load_trades(trades_file))

    slice_archives = all_archives[start_index:end]
    print(
        f"V7.3 volume_bar_cvd 6y: {len(slice_archives)} archives "
        f"(index {start_index}..{end - 1})",
        flush=True,
    )

    for idx, archive in enumerate(slice_archives):
        global_index = start_index + idx
        report_file = work_dir / f"{archive.name}.report.json"
        if args.resume and report_file.is_file():
            print(f"[skip] {archive.name} (report exists)", flush=True)
            payload = json.loads(report_file.read_text(encoding="utf-8"))
            equity = float(payload["report"]["ending_equity"])
            continue
        print(f"[{idx + 1}/{len(slice_archives)}] {archive.name}", flush=True)
        ensure_cache(archive, args.threshold_btc, dest)
        trades_path = work_dir / f"{archive.name}.trades.jsonl"
        payload = run_archive_backtest(
            archive,
            threshold=args.threshold_btc,
            dest=dest,
            lookback=args.divergence_lookback_bars,
            exit_bars=args.exit_after_volume_bars,
            starting_equity=equity,
            use_auction_state_gate=args.use_auction_state_gate,
            use_regime_gate_volume_bar=args.use_regime_gate_volume_bar,
            use_footprint_confluence=args.use_footprint_confluence,
            stop_pct=args.stop_pct,
            target_pct=args.target_pct,
            trades_out=trades_path,
            invert_signal_side=args.invert_signal_side,
            use_time_exit=args.use_time_exit,
            require_entry_delta_alignment=args.require_entry_delta_alignment,
            approve_only_permission=args.approve_only_permission,
            scale_target_by_strength=args.scale_target_by_strength,
            base_position_pct=args.base_position_pct,
            entry_lag_bars=args.entry_lag_bars,
            use_market_profile_gate=args.use_market_profile_gate,
            use_anti_pattern_gate=args.use_anti_pattern_gate,
            use_risk_state_gate=args.use_risk_state_gate,
            use_vpin_gate=args.use_vpin_gate,
            market_profile_lookback_bars=args.market_profile_lookback_bars,
        )
        archive_reports.append(payload)
        (work_dir / f"{archive.name}.report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        chunk_trades = load_trades(trades_path)
        all_trades.extend(chunk_trades)
        equity = payload["report"]["ending_equity"]
        (work_dir / "progress.json").write_text(
            json.dumps(
                {
                    "last_archive": archive.name,
                    "index": idx,
                    "global_index": global_index,
                    "equity": equity,
                    "trades_total": len(all_trades),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    all_report_payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(work_dir.glob("*.report.json"))
    ]
    merged = merge_reports(all_report_payloads, all_trades)
    trade_path_db = TradePathDatabase()
    mae_lab = MAEMFEExitLab()
    for trade in all_trades:
        trade_path_db.add_from_trade_dict(
            trade,
            symbol="BTCUSDT",
            signal_family="volume_bar_cvd",
            regime="UNKNOWN",
            volatility_bucket="UNKNOWN",
        )
        mae_lab.add_from_paper_trade(
            trade_id=str(trade.get("signal_id", trade.get("trade_id", ""))),
            signal_id=str(trade.get("signal_id", trade.get("trade_id", ""))),
            symbol="BTCUSDT",
            side=int(trade.get("side", 0)),
            entry_ts_ns=int(trade.get("entry_ts_ns", 0)),
            exit_ts_ns=int(trade.get("exit_ts_ns", trade.get("entry_ts_ns", 0))),
            entry_price=float(trade.get("entry_price", 0.0)),
            exit_price=float(trade.get("exit_price", trade.get("entry_price", 0.0))),
            max_adverse=float(trade.get("max_adverse", 0.0)),
            max_favorable=float(trade.get("max_favorable", 0.0)),
            pnl=float(trade.get("pnl", 0.0)),
            exit_reason=str(trade.get("exit_reason", "UNKNOWN")),
            signal_family="volume_bar_cvd",
            regime="UNKNOWN",
            bars_held=int(trade.get("bars_held", 0)),
            max_hold_bars=int(trade.get("max_hold_bars", 0)),
            target_pct=float(trade.get("target_pct", 0.0)),
            stop_pct=float(trade.get("stop_pct", 0.03)),
            toxicity_state=trade.get("toxicity_state"),
            mlofi_zscore=_maybe_float(trade.get("mlofi_zscore")),
            book_agreement=_maybe_float(trade.get("book_agreement")),
        )
    if args.trade_path_out is not None:
        trade_path_db.export_jsonl(args.trade_path_out)
    if args.mae_mfe_out is not None:
        mae_lab.export_report_json(args.mae_mfe_out)
    envelope = {
        "version": "7.3.0",
        "strategy": "volume_bar_cvd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "threshold_btc": args.threshold_btc,
        "divergence_lookback_bars": args.divergence_lookback_bars,
        "exit_after_volume_bars": args.exit_after_volume_bars,
        "use_time_exit": args.use_time_exit,
        "use_auction_state_gate": args.use_auction_state_gate,
        "use_vpin_gate": args.use_vpin_gate,
        "use_regime_gate_volume_bar": args.use_regime_gate_volume_bar,
        "use_footprint_confluence": args.use_footprint_confluence,
        "stop_pct": args.stop_pct,
        "target_pct": args.target_pct,
        "invert_signal_side": args.invert_signal_side,
        "require_entry_delta_alignment": args.require_entry_delta_alignment,
        "approve_only_permission": args.approve_only_permission,
        "trade_path_out": str(args.trade_path_out) if args.trade_path_out is not None else None,
        "mae_mfe_out": str(args.mae_mfe_out) if args.mae_mfe_out is not None else None,
        "command": "scripts/v73_backtest_6y_incremental.py",
        "report": merged,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
