"""Raw archive inventory and coverage-audit helpers for V8.9."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile


DAILY = re.compile(r"BTCUSDT-aggTrades-(\d{4}-\d{2}-\d{2})\.zip$")
MONTHLY = re.compile(r"BTCUSDT-aggTrades-(\d{4}-\d{2})\.zip$")


def iso_ns(value: int | None) -> str | None:
    return datetime.fromtimestamp(value / 1e9, tz=timezone.utc).isoformat() if value else None


def checksum_for_archive(path: Path) -> str:
    sidecar = Path(str(path) + ".CHECKSUM")
    if sidecar.is_file():
        return sidecar.read_text(encoding="utf-8").split()[0]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_archive(path: Path, cache_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "symbol": "BTCUSDT", "source": "binance", "data_type": "aggTrades",
        "path": str(path), "filename": path.name, "file_size_bytes": path.stat().st_size,
        "sha256": checksum_for_archive(path), "first_ts_ns": None, "last_ts_ns": None,
        "first_ts_iso": None, "last_ts_iso": None, "row_count": None,
        "duplicate_trade_ids": None, "timestamp_monotonic": None, "parse_ok": True, "error": None,
    }
    try:
        with ZipFile(path) as zipped:
            csv_name = path.name.removesuffix(".zip") + ".csv"
            info = zipped.getinfo(csv_name)
            if info.file_size <= 0:
                raise ValueError("zero-size CSV member")
        if cache_metadata:
            record.update(
                first_ts_ns=int(cache_metadata["first_ts_ns"]),
                last_ts_ns=int(cache_metadata["last_ts_ns"]),
                row_count=int(cache_metadata["row_count"]),
                timestamp_monotonic=bool(cache_metadata["timestamp_monotonic"]),
            )
        record["first_ts_iso"] = iso_ns(record["first_ts_ns"])
        record["last_ts_iso"] = iso_ns(record["last_ts_ns"])
    except Exception as exc:
        record["parse_ok"] = False
        record["error"] = str(exc)
    return record


def expected_archive_names(start: date, end: date) -> list[str]:
    names = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        month_start = max(start, cursor)
        next_month = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
        month_end = min(end, date.fromordinal(next_month.toordinal() - 1))
        if month_start.day == 1 and month_end == date.fromordinal(next_month.toordinal() - 1):
            names.append(f"BTCUSDT-aggTrades-{cursor:%Y-%m}.zip")
        else:
            day = month_start
            while day <= month_end:
                names.append(f"BTCUSDT-aggTrades-{day:%Y-%m-%d}.zip")
                day = date.fromordinal(day.toordinal() + 1)
        cursor = next_month
    return names


def coverage_audit(records: Iterable[dict[str, Any]], *, start: date, end: date) -> dict[str, Any]:
    rows = [row for row in records if "_1m" not in row["filename"]]
    daily_months = {
        match.group(1)[:7]
        for row in rows
        if (match := DAILY.match(row["filename"]))
    }
    canonical_rows = [
        row for row in rows
        if not ((match := MONTHLY.match(row["filename"])) and match.group(1) in daily_months)
    ]
    actual_names = {row["filename"] for row in canonical_rows}
    expected = expected_archive_names(start, end)
    for month in daily_months:
        monthly_name = f"BTCUSDT-aggTrades-{month}.zip"
        if monthly_name in expected:
            expected.remove(monthly_name)
            expected.extend(sorted(row["filename"] for row in canonical_rows if row["filename"].startswith(f"BTCUSDT-aggTrades-{month}-")))
    expected = sorted(expected)
    missing = sorted(set(expected) - actual_names)
    unexpected = sorted(actual_names - set(expected))
    parse_bad = sorted(row["filename"] for row in canonical_rows if not row["parse_ok"])
    monotonic_bad = sorted(row["filename"] for row in canonical_rows if row["timestamp_monotonic"] is False)
    first_values = [int(row["first_ts_ns"]) for row in canonical_rows if row.get("first_ts_ns")]
    last_values = [int(row["last_ts_ns"]) for row in canonical_rows if row.get("last_ts_ns")]
    span_start = min(first_values) if first_values else None
    span_end = max(last_values) if last_values else None
    requested_start_ns = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1e9)
    requested_end_ns = int(datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1e9)
    passed = not missing and not parse_bad and not monotonic_bad and span_start is not None and span_end is not None and span_start <= requested_start_ns + 86_400_000_000_000 and span_end >= requested_end_ns - 86_400_000_000_000
    return {
        "requested_start": start.isoformat(), "requested_end": end.isoformat(),
        "expected_archives": expected, "actual_archive_count": len(canonical_rows),
        "excluded_overlapping_archives": sorted(set(row["filename"] for row in rows) - actual_names),
        "missing_archives": missing, "unexpected_archives": unexpected,
        "bad_parse_archives": parse_bad, "non_monotonic_archives": monotonic_bad,
        "actual_start_ts_ns": span_start, "actual_end_ts_ns": span_end,
        "actual_start_iso": iso_ns(span_start), "actual_end_iso": iso_ns(span_end),
        "coverage_passed": passed,
    }


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
