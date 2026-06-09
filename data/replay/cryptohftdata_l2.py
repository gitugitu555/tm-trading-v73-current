"""Second-pass CryptoHFTData L2 replay over hourly orderbook files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import BytesIO
import math
import subprocess
from pathlib import Path

from core.types import BookSnapshot
from features.iceberg import IcebergDetector
from features.l2_imbalance import OrderBookImbalanceEngine
from features.microprice import microprice
from features.spoofing import SpoofingDetector
from features.whale import WhalePressureEngine
from storage.hot_path import hot_cryptohftdata_orderbook_dir


@dataclass(frozen=True)
class L2SecondPassReport:
    exchange: str
    symbol: str
    files_processed: int
    rows_seen: int
    snapshot_rows: int
    update_rows: int
    emitted_snapshots: int
    crossed_books: int
    spoof_events: int
    iceberg_events: int
    average_book_imbalance: float
    average_microprice_spread_bps: float
    average_whale_pressure: float
    first_ts: str | None
    last_ts: str | None
    top_depth: int
    reason_codes: tuple[str, ...]


class _BookState:
    def __init__(self) -> None:
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.sequence_id: str | None = None

    def reset_from_rows(self, rows: list[tuple[str, float, float]]) -> None:
        self.bids.clear()
        self.asks.clear()
        self.apply_rows(rows)

    def apply_rows(self, rows: list[tuple[str, float, float]]) -> None:
        for side, price, quantity in rows:
            book = self.bids if side == "bid" else self.asks
            if quantity <= 0.0:
                book.pop(price, None)
            else:
                book[price] = quantity

    def snapshot(self, *, ts_event: datetime, exchange: str, symbol: str, top_depth: int) -> BookSnapshot | None:
        bids = tuple(sorted(self.bids.items(), key=lambda item: item[0], reverse=True)[:top_depth])
        asks = tuple(sorted(self.asks.items(), key=lambda item: item[0])[:top_depth])
        if not bids or not asks:
            return None
        try:
            return BookSnapshot(
                ts_event=ts_event,
                exchange=exchange,
                symbol=symbol,
                bids=bids,
                asks=asks,
                sequence_id=self.sequence_id,
            )
        except ValueError:
            return None


class CryptoHFTDataL2SecondPass:
    def __init__(
        self,
        *,
        exchange: str = "bybit",
        symbol: str = "BTCUSDT",
        data_root: Path | None = None,
        top_depth: int = 200,
        batch_size: int = 65_536,
    ) -> None:
        self.exchange = exchange
        self.symbol = symbol
        self.data_root = Path(data_root) if data_root is not None else hot_cryptohftdata_orderbook_dir(exchange=exchange, symbol=symbol)
        self.top_depth = top_depth
        self.batch_size = batch_size
        self.imbalance = OrderBookImbalanceEngine()
        self.spoofing = SpoofingDetector()
        self.iceberg = IcebergDetector()
        self.whale = WhalePressureEngine()

    def run(self, *, start_date: str | None = None, end_date: str | None = None) -> L2SecondPassReport:
        files = list(self._iter_files(start_date=start_date, end_date=end_date))
        state = _BookState()
        rows_seen = 0
        snapshot_rows = 0
        update_rows = 0
        emitted_snapshots = 0
        crossed_books = 0
        spoof_events = 0
        iceberg_events = 0
        imbalance_sum = 0.0
        spread_bps_sum = 0.0
        whale_sum = 0.0
        metrics_count = 0
        reason_codes: set[str] = set()
        first_ts: datetime | None = None
        last_ts: datetime | None = None
        pending_event_time: int | None = None
        pending_rows: list[tuple] = []

        for path in files:
            for row_batch in self._iter_rows(path):
                for row in row_batch:
                    rows_seen += 1
                    event_time = int(row[1])
                    if pending_event_time is None:
                        pending_event_time = event_time
                    if event_time != pending_event_time:
                        (
                            emitted,
                            crossed,
                            spoof_count,
                            iceberg_count,
                            imbalance_total,
                            spread_total,
                            whale_total,
                            metric_rows,
                            group_ts,
                            group_reason_codes,
                            group_snapshot_rows,
                            group_update_rows,
                        ) = self._flush_group(state, pending_rows)
                        emitted_snapshots += emitted
                        crossed_books += crossed
                        spoof_events += spoof_count
                        iceberg_events += iceberg_count
                        imbalance_sum += imbalance_total
                        spread_bps_sum += spread_total
                        whale_sum += whale_total
                        metrics_count += metric_rows
                        snapshot_rows += group_snapshot_rows
                        update_rows += group_update_rows
                        if group_ts is not None:
                            if first_ts is None:
                                first_ts = group_ts
                            last_ts = group_ts
                        reason_codes.update(group_reason_codes)
                        pending_rows = []
                        pending_event_time = event_time
                    pending_rows.append(row)

        if pending_rows:
            (
                emitted,
                crossed,
                spoof_count,
                iceberg_count,
                imbalance_total,
                spread_total,
                whale_total,
                metric_rows,
                group_ts,
                group_reason_codes,
                group_snapshot_rows,
                group_update_rows,
            ) = self._flush_group(state, pending_rows)
            emitted_snapshots += emitted
            crossed_books += crossed
            spoof_events += spoof_count
            iceberg_events += iceberg_count
            imbalance_sum += imbalance_total
            spread_bps_sum += spread_total
            whale_sum += whale_total
            metrics_count += metric_rows
            snapshot_rows += group_snapshot_rows
            update_rows += group_update_rows
            if group_ts is not None:
                if first_ts is None:
                    first_ts = group_ts
                last_ts = group_ts
            reason_codes.update(group_reason_codes)

        return L2SecondPassReport(
            exchange=self.exchange,
            symbol=self.symbol,
            files_processed=len(files),
            rows_seen=rows_seen,
            snapshot_rows=snapshot_rows,
            update_rows=update_rows,
            emitted_snapshots=emitted_snapshots,
            crossed_books=crossed_books,
            spoof_events=spoof_events,
            iceberg_events=iceberg_events,
            average_book_imbalance=imbalance_sum / metrics_count if metrics_count else 0.0,
            average_microprice_spread_bps=spread_bps_sum / metrics_count if metrics_count else 0.0,
            average_whale_pressure=whale_sum / metrics_count if metrics_count else 0.0,
            first_ts=first_ts.isoformat() if first_ts else None,
            last_ts=last_ts.isoformat() if last_ts else None,
            top_depth=self.top_depth,
            reason_codes=tuple(sorted(reason_codes)),
        )

    def _iter_files(self, *, start_date: str | None, end_date: str | None):
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        for path in sorted(self.data_root.rglob("*.parquet.zst")):
            day = self._day_from_path(path)
            if day is None:
                continue
            if start is not None and day < start:
                continue
            if end is not None and day > end:
                continue
            yield path

    def _iter_rows(self, path: Path):
        import pyarrow.parquet as pq

        raw = subprocess.check_output(["zstd", "-dc", str(path.resolve())])
        table = pq.read_table(BytesIO(raw))
        batch_size = self.batch_size
        for batch in table.to_batches(max_chunksize=batch_size):
            columns = batch.to_pydict()
            yield zip(
                columns["received_time"],
                columns["event_time"],
                columns["transaction_time"],
                columns["symbol"],
                columns["event_type"],
                columns["first_update_id"],
                columns["final_update_id"],
                columns["prev_final_update_id"],
                columns["last_update_id"],
                columns["side"],
                columns["price"],
                columns["quantity"],
            )

    def _flush_group(
        self,
        state: _BookState,
        rows: list[tuple],
    ) -> tuple[int, int, int, int, float, float, float, int, datetime | None, set[str], int, int]:
        if not rows:
            return (0, 0, 0, 0, 0.0, 0.0, 0.0, 0, None, set(), 0, 0)

        snapshot_levels: list[tuple[str, float, float]] = []
        update_levels: list[tuple[str, float, float]] = []
        event_ts: datetime | None = None
        sequence_id: str | None = None
        snapshot_rows = 0
        update_rows = 0

        for row in rows:
            received_time, event_time, transaction_time, symbol, event_type, first_update_id, final_update_id, prev_final_update_id, last_update_id, side, price, quantity = row
            event_ts = datetime.fromtimestamp(int(event_time) / 1000.0, tz=timezone.utc)
            sequence_id = self._sequence_from_row(final_update_id, last_update_id, prev_final_update_id)
            side_str = str(side).lower()
            price_f = float(price)
            qty_f = float(quantity)
            if str(event_type) == "snapshot":
                snapshot_rows += 1
                snapshot_levels.append((side_str, price_f, qty_f))
            else:
                update_rows += 1
                update_levels.append((side_str, price_f, qty_f))

        state.sequence_id = sequence_id
        if snapshot_levels:
            state.reset_from_rows(snapshot_levels)
        if update_levels:
            state.apply_rows(update_levels)

        book = state.snapshot(
            ts_event=event_ts or datetime.now(timezone.utc),
            exchange=self.exchange,
            symbol=self.symbol,
            top_depth=self.top_depth,
        )
        if book is None:
            return (0, 1, 0, 0, 0.0, 0.0, 0.0, 0, event_ts, set(), snapshot_rows, update_rows)

        try:
            book_imbalance = self.imbalance.update(book.bids, book.asks)
            micro = microprice(book.bids, book.asks)
        except ValueError:
            return (1, 0, 0, 0, 0.0, 0.0, 0.0, 0, event_ts, set(), snapshot_rows, update_rows)

        spoof_batch = self.spoofing.update(
            ts_event=book.ts_event,
            bids=book.bids,
            asks=book.asks,
        )
        iceberg_batch = self.iceberg.update(bids=book.bids, asks=book.asks)
        whale = self.whale.compute(
            large_print=None,
            book_imbalance=book_imbalance,
            spoofing_events=spoof_batch,
            iceberg_events=iceberg_batch,
        )

        reason_codes = set(whale.reason_codes)
        reason_codes.update(code for event in spoof_batch for code in event.reason_codes)
        reason_codes.update(code for event in iceberg_batch for code in event.reason_codes)
        spread_bps = self._spread_bps(book.bids[0][0], book.asks[0][0])
        return (
            1,
            0,
            len(spoof_batch),
            len(iceberg_batch),
            book_imbalance,
            spread_bps,
            whale.pressure,
            1,
            event_ts,
            reason_codes,
            snapshot_rows,
            update_rows,
        )

    def _day_from_path(self, path: Path) -> date | None:
        try:
            return date.fromisoformat(path.parent.parent.name)
        except ValueError:
            return None

    def _sequence_from_row(self, final_update_id: object, last_update_id: object, prev_final_update_id: object) -> str | None:
        for value in (final_update_id, last_update_id, prev_final_update_id):
            if value is None:
                continue
            if isinstance(value, float) and math.isnan(value):
                continue
            try:
                return str(int(value))
            except (TypeError, ValueError, OverflowError):
                continue
        return None

    def _spread_bps(self, best_bid: float, best_ask: float) -> float:
        mid = (best_bid + best_ask) / 2.0
        if mid <= 0:
            return 0.0
        return ((best_ask - best_bid) / mid) * 10_000.0
