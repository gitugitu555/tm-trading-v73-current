#!/usr/bin/env python3
"""Run V7.2 Chunk A sample-first IC checks on downloaded Binance aggTrades."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prime.ic_harness import run_ic_on_binance_archives
from prime.ic_validation import check_collinearity
from prime.phase1 import CVDEngine, FootprintEngine


DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", default="BTCUSDT-aggTrades-2026-05-21.zip")
    parser.add_argument("--max-rows", type=int, default=50_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive = args.dest / args.archive
    if not archive.is_file():
        print(f"missing archive: {archive}", file=sys.stderr)
        return 2

    cvd = run_ic_on_binance_archives(
        CVDEngine,
        {"divergence_threshold": 100.0},
        lambda engine: engine.cvd_5m,
        [archive],
        max_rows=args.max_rows,
    )
    footprint = run_ic_on_binance_archives(
        FootprintEngine,
        {"tick_size": 0.5, "warm_period": 100},
        lambda engine: float(engine.footprint_bias),
        [archive],
        max_rows=args.max_rows,
    )

    # Collinearity is computed on aligned engine outputs.
    cvd_values, fp_values = collect_aligned_signals(archive, args.max_rows)
    collinearity = check_collinearity(cvd_values, fp_values)
    result = {
        "chunk": "A",
        "archive": archive.name,
        "max_rows": args.max_rows,
        "cvd": cvd,
        "footprint": footprint,
        "cvd_footprint_collinearity": round(collinearity, 4),
        "collinearity_pass": collinearity < 0.85,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(
        [
            cvd["verdict"] == "KEEP",
            footprint["verdict"] == "KEEP",
            collinearity < 0.85,
        ]
    ) else 1


def collect_aligned_signals(archive: Path, max_rows: int) -> tuple[list[float], list[float]]:
    from prime.ic_harness import iter_binance_ticks

    cvd = CVDEngine(divergence_threshold=100.0)
    footprint = FootprintEngine(tick_size=0.5, warm_period=100)
    cvd_values: list[float] = []
    fp_values: list[float] = []
    for tick in iter_binance_ticks([archive], max_rows=max_rows):
        cvd.handle_trade_tick(tick)
        footprint.handle_trade_tick(tick)
        if cvd.initialized and footprint.initialized:
            cvd_values.append(cvd.cvd_5m)
            fp_values.append(float(footprint.footprint_bias))
    return cvd_values, fp_values


if __name__ == "__main__":
    sys.exit(main())
