#!/usr/bin/env python3
"""Quick TP/SL + gate ablation on one cached archive (v7.3 volume_bar_cvd)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", default="BTCUSDT-aggTrades-2022-09.zip")
    p.add_argument("--output", type=Path, default=ROOT / "results/v73_conversion_sweep.json")
    return p.parse_args()


def run_case(archive: str, extra: list[str]) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/chunk_b_backtest_cached.py"),
        "--archive",
        archive,
        "--signal-mode",
        "divergence",
        "--divergence-type",
        "volume_bar_cvd",
        "--threshold-btc",
        "300",
        "--divergence-lookback-bars",
        "40",
        "--exit-after-volume-bars",
        "5",
        "--no-use-cvd-reversal-confirm",
        *extra,
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    text = proc.stdout.strip()
    start = text.find("{")
    if start < 0:
        raise RuntimeError(proc.stderr or "no json output")
    payload = json.loads(text[start:])
    report = payload["report"]
    return {
        "trades": report["trades"],
        "win_rate": report["win_rate"],
        "total_pnl": report["total_pnl"],
        "signals_seen": report["signals_seen"],
        "exit_reasons": report.get("exit_reasons", {}),
    }


def main() -> int:
    args = parse_args()
    grid = [
        ("baseline_v73", ["--stop-pct", "0.0045", "--target-pct", "0.0025", "--use-regime-gate-volume-bar", "--use-auction-state-gate"]),
        ("legacy_tpsl", ["--stop-pct", "0.003", "--target-pct", "0.006", "--no-use-regime-gate-volume-bar", "--no-use-auction-state-gate"]),
        ("wide_stop", ["--stop-pct", "0.006", "--target-pct", "0.0025", "--use-regime-gate-volume-bar", "--use-auction-state-gate"]),
        ("tight_target", ["--stop-pct", "0.0045", "--target-pct", "0.0015", "--use-regime-gate-volume-bar", "--use-auction-state-gate"]),
        ("no_auction", ["--stop-pct", "0.0045", "--target-pct", "0.0025", "--use-regime-gate-volume-bar", "--no-use-auction-state-gate"]),
        ("no_regime_gate", ["--stop-pct", "0.0045", "--target-pct", "0.0025", "--no-use-regime-gate-volume-bar", "--use-auction-state-gate"]),
    ]
    results: dict = {
        "archive": args.archive,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": {},
    }
    for name, flags in grid:
        print(f"[sweep] {name}", flush=True)
        results["cases"][name] = run_case(args.archive, flags)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())