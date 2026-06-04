#!/usr/bin/env python3
"""V7.3 six-year backtest: volume-bar CVD edge profile (measured signal path)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prime.performance import deflated_sharpe_probability, kurtosis, sharpe_ratio, skewness
from storage.hot_path import assert_nvme_archive, hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
CACHE_DIR = ROOT / "results/indicator_cache"
WORK_DIR = ROOT / "results/v73_backtest_6y_work"
THRESHOLD = 300.0
LOOKBACK = 40
EXIT_BARS = 5


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    p.add_argument("--threshold-btc", type=float, default=THRESHOLD)
    p.add_argument("--divergence-lookback-bars", type=int, default=LOOKBACK)
    p.add_argument("--exit-after-volume-bars", type=int, default=EXIT_BARS)
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--end-index", type=int, default=None)
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/v73_backtest_6y_volume_bar_cvd.json",
    )
    p.add_argument("--use-auction-state-gate", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--starting-equity", type=float, default=None)
    return p.parse_args()


def archives(dest: Path) -> list[Path]:
    return sorted(a for a in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)


def cache_path(archive: Path, threshold: float) -> Path:
    return CACHE_DIR / f"{archive.name}.threshold-{int(threshold)}.parquet"


def ensure_cache(archive: Path, threshold: float, dest: Path) -> None:
    assert_nvme_archive(archive)
    target = cache_path(archive, threshold)
    if target.is_file():
        return
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
    trades_out: Path,
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
        "--no-use-cvd-reversal-confirm",
        "--starting-equity",
        str(starting_equity),
        "--trades-out",
        str(trades_out),
    ]
    if use_auction_state_gate:
        cmd.append("--use-auction-state-gate")
    else:
        cmd.append("--no-use-auction-state-gate")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
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
    regime_counts: Counter[str] = Counter()
    permission_counts: Counter[str] = Counter()
    exit_reasons: Counter[str] = Counter()
    for item in archive_reports:
        regime_counts.update(item["report"].get("regime_counts", {}))
        permission_counts.update(item["report"].get("permission_counts", {}))
        exit_reasons.update(item["report"].get("exit_reasons", {}))

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
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main() -> int:
    args = parse_args()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    dest = hot_btcusdt_aggtrades_dir()
    all_archives = archives(dest)
    end = args.end_index if args.end_index is not None else len(all_archives)
    start_index = args.start_index
    equity = args.starting_equity if args.starting_equity is not None else 100_000.0
    all_trades: list[dict] = []
    archive_reports: list[dict] = []

    if args.resume:
        progress_file = WORK_DIR / "progress.json"
        if progress_file.is_file():
            prog = json.loads(progress_file.read_text(encoding="utf-8"))
            equity = float(prog.get("equity", equity))
            if start_index == 0:
                start_index = int(prog.get("index", -1)) + 1
            for trades_file in sorted(WORK_DIR.glob("*.trades.jsonl")):
                all_trades.extend(load_trades(trades_file))

    slice_archives = all_archives[start_index:end]
    print(
        f"V7.3 volume_bar_cvd 6y: {len(slice_archives)} archives "
        f"(index {start_index}..{end - 1})",
        flush=True,
    )

    for idx, archive in enumerate(slice_archives):
        print(f"[{idx + 1}/{len(slice_archives)}] {archive.name}", flush=True)
        ensure_cache(archive, args.threshold_btc, dest)
        trades_path = WORK_DIR / f"{archive.name}.trades.jsonl"
        payload = run_archive_backtest(
            archive,
            threshold=args.threshold_btc,
            dest=dest,
            lookback=args.divergence_lookback_bars,
            exit_bars=args.exit_after_volume_bars,
            starting_equity=equity,
            use_auction_state_gate=args.use_auction_state_gate,
            trades_out=trades_path,
        )
        archive_reports.append(payload)
        (WORK_DIR / f"{archive.name}.report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        chunk_trades = load_trades(trades_path)
        all_trades.extend(chunk_trades)
        equity = payload["report"]["ending_equity"]
        (WORK_DIR / "progress.json").write_text(
            json.dumps(
                {
                    "last_archive": archive.name,
                    "index": idx,
                    "equity": equity,
                    "trades_total": len(all_trades),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    merged = merge_reports(archive_reports, all_trades)
    envelope = {
        "version": "7.3.0",
        "strategy": "volume_bar_cvd",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "threshold_btc": args.threshold_btc,
        "divergence_lookback_bars": args.divergence_lookback_bars,
        "exit_after_volume_bars": args.exit_after_volume_bars,
        "use_auction_state_gate": args.use_auction_state_gate,
        "command": "scripts/v73_backtest_6y_incremental.py",
        "report": merged,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())