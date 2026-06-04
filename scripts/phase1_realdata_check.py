#!/usr/bin/env python3
"""Phase 1 real-data validation for downloaded Binance aggTrades archives."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sys
from zipfile import BadZipFile, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.quality.firewall import DataQualityFirewall
from data.replay.validator import checksum_snapshots
from features.snapshots import FeatureSnapshotBuilder
from features.trade_signing import TradeSigner


SYMBOL = "BTCUSDT"
DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")


@dataclass(frozen=True)
class ArchiveCheck:
    name: str
    rows: int
    checksum: str
    first_ts: datetime | None
    last_ts: datetime | None
    parity_passed: bool
    quality_statuses: tuple[str, ...]


def expected_archives() -> list[str]:
    names: list[str] = []
    for day in range(22, 32):
        names.append(f"{SYMBOL}-aggTrades-2020-05-{day:02d}.zip")

    year = 2020
    month = 6
    while year < 2026 or month <= 4:
        names.append(f"{SYMBOL}-aggTrades-{year:04d}-{month:02d}.zip")
        month += 1
        if month == 13:
            year += 1
            month = 1

    for day in range(1, 22):
        names.append(f"{SYMBOL}-aggTrades-2026-05-{day:02d}.zip")
    return names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=50_000,
        help="Rows to replay from each selected archive.",
    )
    parser.add_argument(
        "--archives",
        nargs="*",
        default=[
            f"{SYMBOL}-aggTrades-2020-05-22.zip",
            f"{SYMBOL}-aggTrades-2021-05.zip",
            f"{SYMBOL}-aggTrades-2024-01.zip",
            f"{SYMBOL}-aggTrades-2026-05-21.zip",
        ],
        help="Archive names to replay for deterministic feature checks.",
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="Skip full SHA-256 verification of every expected zip.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dest = args.dest

    errors: list[str] = []
    expected = expected_archives()
    missing = [name for name in expected if not (dest / name).is_file()]
    missing_checksums = [name for name in expected if not (dest / f"{name}.CHECKSUM").is_file()]
    partials = sorted(path.name for path in dest.glob("*.aria2"))

    if missing:
        errors.append(f"missing archives: {len(missing)}")
    if missing_checksums:
        errors.append(f"missing checksums: {len(missing_checksums)}")
    if partials:
        errors.append(f"partials present: {len(partials)}")

    checksum_failures: list[str] = []
    if not args.skip_checksums:
        for name in expected:
            archive = dest / name
            checksum_file = dest / f"{name}.CHECKSUM"
            if archive.is_file() and checksum_file.is_file() and not verify_checksum(archive, checksum_file):
                checksum_failures.append(name)
        if checksum_failures:
            errors.append(f"checksum failures: {len(checksum_failures)}")

    structure_failures = []
    structure_warnings = []
    for name in expected:
        archive = dest / name
        if archive.is_file():
            structure = inspect_zip_structure(archive)
            if not structure["has_expected_csv"]:
                structure_failures.append(name)
            if structure["extra_members"]:
                structure_warnings.append(f"{name}: extra_members={structure['extra_members']}")
    if structure_failures:
        errors.append(f"bad zip/csv structure: {len(structure_failures)}")

    checks: list[ArchiveCheck] = []
    selected = args.archives or []
    for name in selected:
        archive = dest / name
        if not archive.is_file():
            errors.append(f"selected archive missing: {name}")
            continue
        first = replay_archive(archive, args.sample_rows)
        second = replay_archive(archive, args.sample_rows)
        if first.checksum != second.checksum:
            errors.append(f"non-deterministic replay checksum: {name}")
        checks.append(first)

    print("Phase 1 real-data check")
    print(f"dest={dest}")
    print(f"expected_archives={len(expected)}")
    print(f"missing_archives={len(missing)}")
    print(f"missing_checksums={len(missing_checksums)}")
    print(f"partials={len(partials)}")
    print(f"checksums_verified={'no' if args.skip_checksums else 'yes'}")
    print(f"checksum_failures={len(checksum_failures)}")
    print(f"zip_structure_failures={len(structure_failures)}")
    print(f"zip_structure_warnings={len(structure_warnings)}")
    print()

    for check in checks:
        print(f"archive={check.name}")
        print(f"  rows_replayed={check.rows}")
        print(f"  deterministic_checksum={check.checksum}")
        print(f"  first_ts={check.first_ts.isoformat() if check.first_ts else 'NONE'}")
        print(f"  last_ts={check.last_ts.isoformat() if check.last_ts else 'NONE'}")
        print(f"  cvd_parity={check.parity_passed}")
        print(f"  quality_statuses={','.join(check.quality_statuses)}")

    if errors:
        print()
        print("FAIL")
        for error in errors:
            print(f"  {error}")
        for name in checksum_failures[:20]:
            print(f"  checksum_failed={name}")
        for name in structure_failures[:20]:
            print(f"  zip_structure_failed={name}")
        return 1

    if structure_warnings:
        print()
        print("WARN")
        for warning in structure_warnings[:20]:
            print(f"  {warning}")

    print()
    print("PASS")
    return 0


def verify_checksum(archive: Path, checksum_file: Path) -> bool:
    expected_hash = checksum_file.read_text(encoding="utf-8").split()[0]
    digest = sha256()
    with archive.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == expected_hash


def inspect_zip_structure(archive: Path) -> dict[str, object]:
    try:
        with ZipFile(archive) as zipped:
            infos = zipped.infolist()
            expected_csv = archive.name.removesuffix(".zip") + ".csv"
            file_names = [info.filename for info in infos if not info.is_dir()]
            return {
                "has_expected_csv": expected_csv in file_names,
                "extra_members": max(0, len(file_names) - 1),
            }
    except BadZipFile:
        return {"has_expected_csv": False, "extra_members": 0}


def replay_archive(archive: Path, sample_rows: int) -> ArchiveCheck:
    signer = TradeSigner()
    builder = FeatureSnapshotBuilder(tick_size=0.01)
    firewall = DataQualityFirewall()
    snapshots = []
    signed_delta_total = 0.0
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    quality_statuses: set[str] = set()

    with ZipFile(archive) as zipped:
        csv_name = archive.name.removesuffix(".zip") + ".csv"
        with zipped.open(csv_name) as raw:
            lines = (line.decode("utf-8") for line in raw)
            reader = csv.reader(lines)
            for rows_seen, row in enumerate(reader, start=1):
                if rows_seen > sample_rows:
                    break
                if len(row) != 8:
                    raise ValueError(f"{archive.name}: expected 8 columns, got {len(row)}")

                ts_event = timestamp_from_binance_us(row[5])
                trade = signer.sign(
                    ts_event=ts_event,
                    exchange="BINANCE",
                    symbol=SYMBOL,
                    price=float(row[1]),
                    size_base=float(row[2]),
                    buyer_is_maker=parse_bool(row[6]),
                    trade_id=row[0],
                )
                quality = firewall.check_trade(trade)
                quality_statuses.add(quality.status)
                snapshots.append(builder.update_trade(trade))
                signed_delta_total += trade.size_base if trade.side == "BUY" else -trade.size_base
                first_ts = first_ts or ts_event
                last_ts = ts_event

    if snapshots:
        parity_passed = abs(signed_delta_total - snapshots[-1].cvd) <= 1e-9
    else:
        parity_passed = False

    return ArchiveCheck(
        name=archive.name,
        rows=len(snapshots),
        checksum=checksum_snapshots(snapshots),
        first_ts=first_ts,
        last_ts=last_ts,
        parity_passed=parity_passed,
        quality_statuses=tuple(sorted(quality_statuses)),
    )


def timestamp_from_binance_us(value: str) -> datetime:
    raw = int(value)
    if raw >= 10_000_000_000_000:
        seconds, micros = divmod(raw, 1_000_000)
    else:
        seconds, millis = divmod(raw, 1_000)
        micros = millis * 1_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=micros)


def parse_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"unexpected boolean value: {value}")


if __name__ == "__main__":
    sys.exit(main())
