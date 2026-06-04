"""CSV replay validator with deterministic output checksums."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from core.types import BookSnapshot, FeatureSnapshot
from features.snapshots import FeatureSnapshotBuilder
from features.trade_signing import TradeSigner, signed_delta


@dataclass(frozen=True)
class ReplayReport:
    snapshot_count: int
    checksum: str
    parity_passed: bool
    reason_codes: tuple[str, ...]


class ReplayValidator:
    def __init__(self, *, tick_size: float = 0.1) -> None:
        self.tick_size = tick_size

    def replay_csv(
        self,
        *,
        trades_csv: str | Path,
        books_csv: str | Path | None = None,
    ) -> tuple[list[FeatureSnapshot], ReplayReport]:
        signer = TradeSigner()
        builder = FeatureSnapshotBuilder(tick_size=self.tick_size)
        book_by_ts = self._load_books(books_csv) if books_csv else {}
        snapshots: list[FeatureSnapshot] = []
        signed_trades = []

        with Path(trades_csv).open(newline="") as handle:
            for row in csv.DictReader(handle):
                ts = _parse_ts(row["ts_event"])
                book = book_by_ts.get(row["ts_event"])
                if book is not None:
                    builder.update_book(book)
                buyer_is_maker = _parse_bool(row.get("buyer_is_maker"))
                trade = signer.sign(
                    ts_event=ts,
                    exchange=row.get("exchange") or "BINANCE",
                    symbol=row["symbol"],
                    price=float(row["price"]),
                    size_base=float(row.get("size_base") or row.get("size") or 0),
                    buyer_is_maker=buyer_is_maker,
                    native_aggressor_side=row.get("aggressor_side") or None,  # type: ignore[arg-type]
                    trade_id=row.get("trade_id") or None,
                )
                signed_trades.append(trade)
                snapshots.append(builder.update_trade(trade))

        checksum = checksum_snapshots(snapshots)
        return snapshots, ReplayReport(
            snapshot_count=len(snapshots),
            checksum=checksum,
            parity_passed=self._batch_cvd_parity_check(signed_trades, snapshots),
            reason_codes=("DETERMINISTIC_CHECKSUM", "BATCH_CVD_PARITY"),
        )

    def _batch_cvd_parity_check(self, signed_trades, snapshots: list[FeatureSnapshot]) -> bool:
        cvd = 0.0
        if len(signed_trades) != len(snapshots):
            return False
        for trade, snapshot in zip(signed_trades, snapshots):
            cvd += signed_delta(trade.size_base, trade.side)
            if abs(cvd - snapshot.cvd) > 1e-12:
                return False
        return True

    def _load_books(self, books_csv: str | Path) -> dict[str, BookSnapshot]:
        books: dict[str, BookSnapshot] = {}
        with Path(books_csv).open(newline="") as handle:
            for row in csv.DictReader(handle):
                bids = _parse_levels(row["bids"])
                asks = _parse_levels(row["asks"])
                books[row["ts_event"]] = BookSnapshot(
                    ts_event=_parse_ts(row["ts_event"]),
                    exchange=row.get("exchange") or "BINANCE",
                    symbol=row["symbol"],
                    bids=tuple(bids),
                    asks=tuple(asks),
                    sequence_id=row.get("sequence_id") or None,
                )
        return books


def checksum_snapshots(snapshots: list[FeatureSnapshot]) -> str:
    payload = json.dumps([snapshot.to_row() for snapshot in snapshots], sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def _parse_ts(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.lower() in {"true", "1", "yes"}


def _parse_levels(value: str) -> list[tuple[float, float]]:
    parsed = json.loads(value)
    return [(float(price), float(qty)) for price, qty in parsed]
