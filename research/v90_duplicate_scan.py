"""Resumable raw-trade duplicate scan for BTCUSDT aggTrades archives."""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile


@dataclass(frozen=True)
class DuplicateScanConfig:
    raw_dir: Path
    checkpoint_path: Path
    output_path: Path
    resume: bool = True
    max_archives: int | None = None


def scan_archives(archives: Iterable[Path], *, checkpoint_path: Path | None = None) -> dict[str, Any]:
    processed: list[str] = []
    duplicate_within = 0
    duplicate_across = 0
    timestamp_overlaps: list[dict[str, Any]] = []
    non_monotonic_files: list[str] = []
    parse_errors: list[dict[str, Any]] = []
    total_rows = 0
    previous_last_id: str | None = None
    previous_last_ts: int | None = None
    resume_state = _load_checkpoint(checkpoint_path) if checkpoint_path else None
    seen_ids = _open_seen_db(checkpoint_path)

    for archive in archives:
        if resume_state and archive.name in resume_state["processed_archives"]:
            processed.append(archive.name)
            previous_last_id = resume_state.get("previous_last_id")
            previous_last_ts = resume_state.get("previous_last_ts")
            continue
        rows_seen, first_id, last_id, first_ts, last_ts, within_dupes, across_dupes, monotonic_ok = _scan_archive(
            archive, seen_ids
        )
        total_rows += rows_seen
        duplicate_within += within_dupes
        duplicate_across += across_dupes
        if not monotonic_ok:
            non_monotonic_files.append(archive.name)
        if previous_last_ts is not None and first_ts is not None and first_ts < previous_last_ts:
            timestamp_overlaps.append(
                {
                    "previous_archive": processed[-1] if processed else None,
                    "archive": archive.name,
                    "previous_last_ts": previous_last_ts,
                    "first_ts": first_ts,
                }
            )
        processed.append(archive.name)
        previous_last_id = last_id
        previous_last_ts = last_ts
        _save_checkpoint(
            checkpoint_path,
            processed_archives=processed,
            previous_last_id=previous_last_id,
            previous_last_ts=previous_last_ts,
            raw_trades_scanned=total_rows,
        )
        if seen_ids is not None:
            seen_ids.commit()
    if checkpoint_path is not None:
        seen_ids.close()
    return {
        "raw_trades_scanned": total_rows,
        "files_scanned": len(processed),
        "duplicate_trade_ids_within_file": duplicate_within,
        "duplicate_trade_ids_across_files": duplicate_across,
        "timestamp_overlaps": timestamp_overlaps,
        "non_monotonic_files": non_monotonic_files,
        "parse_errors": parse_errors,
        "scan_complete": True,
    }


def _scan_archive(path: Path, seen_ids: sqlite3.Connection | None) -> tuple[int, str | None, str | None, int | None, int | None, int, int, bool]:
    csv_name = path.name.removesuffix(".zip") + ".csv"
    rows_seen = 0
    first_id = last_id = None
    first_ts = last_ts = None
    within_dupes = 0
    across_dupes = 0
    monotonic_ok = True
    prev_ts: int | None = None
    local_seen: set[str] = set()
    with ZipFile(path) as zipped, zipped.open(csv_name) as raw:
        reader = csv.reader((line.decode("utf-8") for line in raw))
        for row in reader:
            if len(row) < 8:
                raise ValueError(f"{path.name}: expected 8 columns, got {len(row)}")
            trade_id = row[0]
            ts_ns = _timestamp_ns(row[5])
            if first_id is None:
                first_id = trade_id
            last_id = trade_id
            first_ts = ts_ns if first_ts is None else first_ts
            last_ts = ts_ns
            if prev_ts is not None and ts_ns < prev_ts:
                monotonic_ok = False
            prev_ts = ts_ns
            rows_seen += 1
            if trade_id in local_seen:
                within_dupes += 1
            else:
                local_seen.add(trade_id)
            if seen_ids is not None:
                if _seen_before(seen_ids, trade_id):
                    across_dupes += 1
                else:
                    _mark_seen(seen_ids, trade_id)
    return rows_seen, first_id, last_id, first_ts, last_ts, within_dupes, across_dupes, monotonic_ok


def _timestamp_ns(value: str) -> int:
    raw = int(value)
    if raw >= 10_000_000_000_000:
        seconds, micros = divmod(raw, 1_000_000)
    else:
        seconds, millis = divmod(raw, 1_000)
        micros = millis * 1_000
    return int(datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=micros).timestamp() * 1e9)


def _open_seen_db(checkpoint_path: Path | None) -> sqlite3.Connection | None:
    if checkpoint_path is None:
        return None
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(checkpoint_path.with_suffix(".seen.sqlite")))
    conn.execute("create table if not exists seen_ids (trade_id text primary key)")
    conn.commit()
    return conn


def _seen_before(conn: sqlite3.Connection, trade_id: str) -> bool:
    row = conn.execute("select 1 from seen_ids where trade_id = ?", (trade_id,)).fetchone()
    return row is not None


def _mark_seen(conn: sqlite3.Connection, trade_id: str) -> None:
    conn.execute("insert or ignore into seen_ids(trade_id) values (?)", (trade_id,))


def _load_checkpoint(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_checkpoint(path: Path | None, **payload: Any) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
