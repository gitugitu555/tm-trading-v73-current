#!/usr/bin/env python3
"""Pre-cache volume-bar indicators on NVMe (parallel, skips existing parquets)."""

from __future__ import annotations

import argparse
import multiprocessing
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.cache_indicators import process_archive
from storage.hot_path import assert_nvme_path, hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
CACHE_DIR = ROOT / "results/indicator_cache"
THRESHOLD = 300.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    p.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    p.add_argument("--threshold-btc", type=float, default=THRESHOLD)
    p.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel cache jobs (keep low while backtest runs)",
    )
    p.add_argument(
        "--skip-archive",
        action="append",
        default=[],
        help="Archive basename to skip (e.g. month backtest is caching now)",
    )
    return p.parse_args()


def run_archive(job: tuple[Path, float, Path]) -> None:
    archive_path, threshold, cache_dir = job
    cache_file = cache_dir / f"{archive_path.name}.threshold-{int(threshold)}.parquet"
    if cache_file.is_file():
        return
    try:
        process_archive(
            archive=archive_path,
            thresholds=[threshold],
            cache_dir=cache_dir,
            max_rows=None,
            progress=False,
        )
    except Exception as exc:
        print(f"Error processing {archive_path.name}: {exc}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    dest = assert_nvme_path(args.dest.resolve(), label="cache dest")
    cache_dir = assert_nvme_path(args.cache_dir.resolve(), label="indicator cache")

    skip = set(args.skip_archive)
    archives = sorted(a for a in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)
    to_process: list[Path] = []
    for archive in archives:
        if archive.name in skip:
            continue
        cache_file = cache_dir / f"{archive.name}.threshold-{int(args.threshold_btc)}.parquet"
        if not cache_file.is_file():
            to_process.append(archive)

    print(
        f"NVMe cache: {len(archives)} archives, {len(to_process)} to build, "
        f"skip={sorted(skip) or 'none'}, workers={args.workers}",
        flush=True,
    )
    if not to_process:
        print("All archives are already cached.")
        return 0

    jobs = [(a, args.threshold_btc, cache_dir) for a in to_process]
    workers = max(1, min(args.workers, len(jobs)))
    print(f"Starting parallel caching with {workers} processes...", flush=True)

    if workers == 1:
        for job in jobs:
            run_archive(job)
    else:
        with multiprocessing.Pool(workers) as pool:
            pool.map(run_archive, jobs)

    print("Caching complete!", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())