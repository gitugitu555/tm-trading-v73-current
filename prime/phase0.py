"""V7.2 Phase 0 data foundation: signing and data quality."""

from __future__ import annotations

from collections import deque
import hashlib

from prime.contracts import DataQualitySnapshot, SignMethod, SignedTrade
from prime.nautilus_compat import AggressorSide, TradeTick, aggressor_name


class TradeSigner:
    """Sign every TradeTick with deterministic aggressor direction."""

    _CONFIDENCE: dict[SignMethod, float] = {
        SignMethod.NATIVE: 1.00,
        SignMethod.LEE_READY: 0.85,
        SignMethod.TICK_RULE: 0.65,
        SignMethod.BVC: 0.40,
        SignMethod.UNKNOWN: 0.00,
    }

    def __init__(self, source: str, session_id: str) -> None:
        self._source = source
        self._session_id = session_id
        self._last_price: dict[str, float] = {}

    def sign(self, tick: TradeTick) -> SignedTrade:
        symbol = str(tick.instrument_id)
        price = float(tick.price)
        size = float(tick.size)
        side, method = self._classify(tick, symbol, price)
        raw_hash = self._compute_hash(tick)
        self._last_price[symbol] = price
        return SignedTrade(
            trade_id=f"{symbol}_{tick.ts_event}_{raw_hash[:8]}",
            symbol=symbol,
            timestamp_ns=int(tick.ts_event),
            price=price,
            size=size,
            side=side,
            sign_method=method,
            sign_confidence=self._CONFIDENCE[method],
            source=self._source,
            raw_hash=raw_hash,
            session_id=self._session_id,
        )

    def _classify(self, tick: TradeTick, symbol: str, price: float) -> tuple[int, SignMethod]:
        side_name = aggressor_name(tick.aggressor_side)
        if tick.aggressor_side == AggressorSide.BUYER or side_name in {"BUYER", "BUY"}:
            return +1, SignMethod.NATIVE
        if tick.aggressor_side == AggressorSide.SELLER or side_name in {"SELLER", "SELL"}:
            return -1, SignMethod.NATIVE

        last = self._last_price.get(symbol)
        if last is not None:
            if price > last:
                return +1, SignMethod.TICK_RULE
            if price < last:
                return -1, SignMethod.TICK_RULE
        return 0, SignMethod.UNKNOWN

    @staticmethod
    def _compute_hash(tick: TradeTick) -> str:
        payload = f"{tick.instrument_id}|{tick.ts_event}|{tick.price}|{tick.size}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DataQualityFirewall:
    """Monitor stream quality and return snapshots without raising."""

    def __init__(
        self,
        latency_warn_ms: float = 150.0,
        latency_halt_ms: float = 500.0,
        dup_warn_rate: float = 0.005,
        dup_halt_rate: float = 0.020,
        gap_warn: int = 1,
        gap_halt: int = 5,
        window: int = 1000,
    ) -> None:
        self._thresholds = {
            "latency_warn": latency_warn_ms,
            "latency_halt": latency_halt_ms,
            "dup_warn": dup_warn_rate,
            "dup_halt": dup_halt_rate,
            "gap_warn": gap_warn,
            "gap_halt": gap_halt,
        }
        self._seen_ids: deque[str] = deque(maxlen=window)
        self._gap_count = 0
        self._last_ts_ns = 0
        self._dup_count = 0
        self._total_count = 0

    def check(
        self,
        trade: SignedTrade,
        receive_ts_ns: int,
        crossed_book: bool = False,
    ) -> DataQualitySnapshot:
        self._total_count += 1
        reason_codes: list[str] = []
        halt_count = 0
        warn_count = 0

        try:
            latency_ms = (int(receive_ts_ns) - int(trade.timestamp_ns)) / 1_000_000
        except Exception as exc:
            reason_codes.append(f"LATENCY_COMPUTE_ERROR:{exc}")
            latency_ms = 0.0
            halt_count += 1

        if latency_ms > self._thresholds["latency_halt"]:
            reason_codes.append("LATENCY_HALT")
            halt_count += 1
        elif latency_ms > self._thresholds["latency_warn"]:
            reason_codes.append("LATENCY_WARN")
            warn_count += 1

        try:
            if trade.trade_id in self._seen_ids:
                self._dup_count += 1
                reason_codes.append("DUPLICATE")
            self._seen_ids.append(trade.trade_id)
            dup_rate = self._dup_count / max(self._total_count, 1)
        except Exception as exc:
            reason_codes.append(f"DUP_CHECK_ERROR:{exc}")
            dup_rate = 0.0

        if dup_rate > self._thresholds["dup_halt"]:
            reason_codes.append("DUP_RATE_HALT")
            halt_count += 1
        elif dup_rate > self._thresholds["dup_warn"]:
            reason_codes.append("DUP_RATE_WARN")
            warn_count += 1

        try:
            if self._last_ts_ns > 0 and trade.timestamp_ns < self._last_ts_ns:
                self._gap_count += 1
                reason_codes.append("SEQ_GAP")
            self._last_ts_ns = max(self._last_ts_ns, int(trade.timestamp_ns))
        except Exception as exc:
            reason_codes.append(f"SEQ_CHECK_ERROR:{exc}")

        if self._gap_count >= self._thresholds["gap_halt"]:
            reason_codes.append("SEQ_GAPS_HALT")
            halt_count += 1
        elif self._gap_count >= self._thresholds["gap_warn"]:
            reason_codes.append("SEQ_GAPS_WARN")
            warn_count += 1

        if crossed_book:
            reason_codes.append("CROSSED_BOOK")
            halt_count += 1

        if halt_count:
            state, scalar = "HALT", 0.0
        elif warn_count >= 2:
            state, scalar = "DEGRADED", 0.5
        elif warn_count == 1:
            state, scalar = "DEGRADED", 0.75
        else:
            state, scalar = "CLEAN", 1.0

        return DataQualitySnapshot(
            state=state,
            latency_ms=latency_ms,
            duplicate_rate=dup_rate,
            sequence_gap_count=self._gap_count,
            crossed_book=crossed_book,
            stale_feed_ms=0.0,
            confidence_scalar=scalar,
            reason_codes=sorted(set(reason_codes)),
        )

