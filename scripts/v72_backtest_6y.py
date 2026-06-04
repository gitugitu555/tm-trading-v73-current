#!/usr/bin/env python3
"""V7.2 six-year BTCUSDT backtest: cache volume bars then run momentum Chunk B."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
CACHE_DIR = ROOT / "results/indicator_cache"
THRESHOLD_BTC = 300.0
RESULTS_DIR = ROOT / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--threshold-btc", type=float, default=THRESHOLD_BTC)
    parser.add_argument("--signal-mode", choices=["momentum", "divergence"], default="momentum")
    parser.add_argument("--skip-cache", action="store_true", help="Do not build missing parquet caches")
    parser.add_argument("--cache-only", action="store_true", help="Only build caches, do not backtest")
    parser.add_argument("--use-auction-state-gate", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def list_archives(dest: Path) -> list[Path]:
    return sorted(a for a in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)


def list_caches(threshold: float) -> list[Path]:
    pattern = f"*.threshold-{int(threshold)}.parquet"
    return sorted(
        f for f in CACHE_DIR.glob(pattern) if f.is_file() and "maxrows" not in f.name
    )


def git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def run_cache_missing(dest: Path, threshold: float) -> int:
    script = ROOT / "scripts/cache_all.py"
    print("Running cache_all.py for missing archives...", flush=True)
    return subprocess.call([sys.executable, str(script)], cwd=ROOT)


def run_backtest(args: argparse.Namespace) -> tuple[int, str]:
    script = ROOT / "scripts/backtest_all_cached.py"
    cmd = [
        sys.executable,
        str(script),
        "--dest",
        str(args.dest),
        "--threshold-btc",
        str(args.threshold_btc),
        "--signal-mode",
        args.signal_mode,
        "--divergence-threshold",
        "100.0",
        *(["--use-auction-state-gate"] if args.use_auction_state_gate else ["--no-use-auction-state-gate"]),
    ]
    print("Running:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if stderr:
        print(stderr, file=sys.stderr)
    print(stdout)
    return proc.returncode, stdout


def main() -> int:
    args = parse_args()
    archives = list_archives(args.dest)
    caches = list_caches(args.threshold_btc)
    missing = len(archives) - len(caches)

    print(f"Archives: {len(archives)}  Caches (threshold {int(args.threshold_btc)}): {len(caches)}")
    if missing > 0 and not args.skip_cache:
        code = run_cache_missing(args.dest, args.threshold_btc)
        if code != 0:
            return code
        caches = list_caches(args.threshold_btc)
        missing = len(archives) - len(caches)

    if missing > 0:
        print(
            f"ERROR: still missing {missing} cache files. Run scripts/cache_all.py first.",
            file=sys.stderr,
        )
        return 2

    if args.cache_only:
        print("Cache complete; --cache-only set, skipping backtest.")
        return 0

    code, stdout = run_backtest(args)
    payload: dict | None = None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        print("WARNING: backtest stdout was not valid JSON; saving raw output.", file=sys.stderr)

    out_path = args.output or RESULTS_DIR / (
        f"v72_backtest_6y_{args.signal_mode}_t{int(args.threshold_btc)}.json"
    )
    envelope = {
        "version": "7.2.0",
        "strategy": "CVDMomentumConfirmation" if args.signal_mode == "momentum" else "divergence",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "archives_expected": len(archives),
        "cache_files": len(caches),
        "threshold_btc": args.threshold_btc,
        "signal_mode": args.signal_mode,
        "use_auction_state_gate": args.use_auction_state_gate,
        "command": "scripts/v72_backtest_6y.py",
        "report": payload,
        "raw_stdout": None if payload else stdout,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())