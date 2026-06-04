"""On-disk cache for derived volume bars.

The cache keeps raw Binance ZIP archives untouched. It stores only derived
volume bars keyed by archive identity and threshold set so repeated diagnostics
can skip ZIP decompression and CSV parsing.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from prime.volume_bars import VolumeBar


CACHE_VERSION = 1


def cache_path(cache_dir: Path, archive: Path, thresholds: list[float]) -> Path:
    threshold_key = "-".join(_format_threshold(threshold) for threshold in sorted(thresholds))
    return cache_dir / f"{archive.name}.thresholds-{threshold_key}.v{CACHE_VERSION}.parquet"


def load_cached_bars(
    cache_dir: Path,
    archive: Path,
    thresholds: list[float],
) -> dict | None:
    try:
        import pyarrow.parquet as pq
    except Exception:
        return None

    path = cache_path(cache_dir, archive, thresholds)
    if not path.is_file():
        return None

    try:
        table = pq.read_table(path)
        records = table.to_pylist()
    except Exception:
        return None

    if not records:
        return None

    stat = archive.stat()
    expected_thresholds = {float(threshold) for threshold in thresholds}
    observed_thresholds = set()
    rows_seen = int(records[0]["rows_seen"])
    bars_by_threshold: dict[float, list[VolumeBar]] = {threshold: [] for threshold in thresholds}

    for record in records:
        if int(record.get("cache_version", 0)) != CACHE_VERSION:
            return None
        if record.get("archive_name") != archive.name:
            return None
        if int(record.get("archive_size", -1)) != stat.st_size:
            return None
        if int(record.get("archive_mtime_ns", -1)) != stat.st_mtime_ns:
            return None
        if int(record.get("rows_seen", -1)) != rows_seen:
            return None

        threshold = float(record["threshold_btc"])
        observed_thresholds.add(threshold)
        if threshold not in bars_by_threshold:
            return None

        bars_by_threshold[threshold].append(
            VolumeBar(
                start_ts_ns=int(record["start_ts_ns"]),
                end_ts_ns=int(record["end_ts_ns"]),
                open=float(record["open"]),
                high=float(record["high"]),
                low=float(record["low"]),
                close=float(record["close"]),
                volume=float(record["volume"]),
                buy_volume=float(record["buy_volume"]),
                sell_volume=float(record["sell_volume"]),
                delta=float(record["delta"]),
                cumulative_delta=float(record["cumulative_delta"]),
                ticks=int(record["ticks"]),
            )
        )

    if observed_thresholds != expected_thresholds:
        return None

    return {
        "rows_seen": rows_seen,
        "bars_by_threshold": bars_by_threshold,
    }


def write_cached_bars(
    cache_dir: Path,
    archive: Path,
    thresholds: list[float],
    rows_seen: int,
    bars_by_threshold: dict[float, list[VolumeBar]],
) -> Path | None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception:
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, archive, thresholds)
    stat = archive.stat()
    records: list[dict] = []

    for threshold in sorted(bars_by_threshold):
        for bar in bars_by_threshold[threshold]:
            record = {
                "cache_version": CACHE_VERSION,
                "archive_name": archive.name,
                "archive_size": stat.st_size,
                "archive_mtime_ns": stat.st_mtime_ns,
                "rows_seen": rows_seen,
                "threshold_btc": float(threshold),
            }
            record.update(asdict(bar))
            records.append(record)

    if not records:
        return None

    table = pa.Table.from_pylist(records)
    pq.write_table(table, path, compression="zstd")
    return path


def _format_threshold(threshold: float) -> str:
    value = float(threshold)
    if value.is_integer():
        return str(int(value))
    return str(value).replace(".", "p")
