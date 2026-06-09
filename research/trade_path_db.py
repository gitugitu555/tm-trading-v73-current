"""Trade-path database utilities for backtest research."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TradePathRecord:
    trade_id: str
    signal_id: str
    symbol: str
    side: int
    entry_ts_ns: int
    exit_ts_ns: int
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    win: bool
    exit_reason: str
    signal_family: str
    regime: str
    session_hour_utc: int
    volatility_bucket: str
    mae: float
    mfe: float
    mae_r: float
    mfe_r: float
    bars_held: int
    max_hold_bars: int
    target_pct: float
    stop_pct: float
    notional: float | None = None
    permission_verdict: str | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    toxicity_state: str | None = None
    mlofi_zscore: float | None = None
    book_agreement: float | None = None
    market_profile_context: str | None = None
    atr_used_pct: float | None = None


@dataclass(frozen=True)
class TradePathSummary:
    n_trades: int
    n_wins: int
    win_rate: float
    total_pnl: float
    avg_return_pct: float
    avg_mae_r: float
    avg_mfe_r: float
    avg_bars_held: float
    by_signal_family: dict[str, int]
    by_regime: dict[str, int]
    by_session_hour: dict[str, int]
    by_exit_reason: dict[str, int]


class TradePathDatabase:
    """Append-only trade-path database built from completed trades."""

    def __init__(self) -> None:
        self._records: list[TradePathRecord] = []

    def add(self, record: TradePathRecord) -> None:
        self._records.append(record)

    def add_from_trade_dict(
        self,
        trade: dict,
        *,
        symbol: str = "BTCUSDT",
        signal_family: str = "volume_bar_cvd",
        regime: str = "UNKNOWN",
        volatility_bucket: str = "UNKNOWN",
        market_profile_context: str | None = None,
        atr_used_pct: float | None = None,
    ) -> TradePathRecord:
        entry_ts_ns = int(trade.get("entry_ts_ns", 0))
        exit_ts_ns = int(trade.get("exit_ts_ns", entry_ts_ns))
        side = int(trade.get("side", 0))
        entry_price = float(trade.get("entry_price", 0.0))
        exit_price = float(trade.get("exit_price", entry_price))
        pnl = float(trade.get("pnl", 0.0))
        return_pct = float(trade.get("return_pct", 0.0))
        win = pnl > 0
        mae = abs(float(trade.get("max_adverse", 0.0)))
        mfe = abs(float(trade.get("max_favorable", 0.0)))
        stop_pct = float(trade.get("stop_pct", 0.03))
        risk = max(stop_pct, 1e-12)
        mae_r = mae / risk
        mfe_r = mfe / risk
        session_hour = _utc_hour(exit_ts_ns)
        record = TradePathRecord(
            trade_id=str(trade.get("trade_id", trade.get("signal_id", ""))),
            signal_id=str(trade.get("signal_id", trade.get("trade_id", ""))),
            symbol=symbol,
            side=side,
            entry_ts_ns=entry_ts_ns,
            exit_ts_ns=exit_ts_ns,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            return_pct=return_pct,
            win=win,
            exit_reason=str(trade.get("exit_reason", "UNKNOWN")),
            signal_family=signal_family,
            regime=regime,
            session_hour_utc=session_hour,
            volatility_bucket=volatility_bucket,
            mae=mae,
            mfe=mfe,
            mae_r=mae_r,
            mfe_r=mfe_r,
            bars_held=int(trade.get("bars_held", 0)),
            max_hold_bars=int(trade.get("max_hold_bars", 0)),
            target_pct=float(trade.get("target_pct", 0.0)),
            stop_pct=stop_pct,
            notional=float(trade["notional"]) if "notional" in trade else None,
            permission_verdict=trade.get("permission_verdict"),
            reason_codes=tuple(trade.get("reason_codes", ())),
            toxicity_state=trade.get("toxicity_state"),
            mlofi_zscore=_maybe_float(trade.get("mlofi_zscore")),
            book_agreement=_maybe_float(trade.get("book_agreement")),
            market_profile_context=market_profile_context,
            atr_used_pct=atr_used_pct,
        )
        self.add(record)
        return record

    def extend_from_trade_dicts(
        self,
        trades: Iterable[dict],
        *,
        symbol: str = "BTCUSDT",
        signal_family: str = "volume_bar_cvd",
        regime: str = "UNKNOWN",
        volatility_bucket: str = "UNKNOWN",
        market_profile_context: str | None = None,
        atr_used_pct: float | None = None,
    ) -> None:
        for trade in trades:
            self.add_from_trade_dict(
                trade,
                symbol=symbol,
                signal_family=signal_family,
                regime=regime,
                volatility_bucket=volatility_bucket,
                market_profile_context=market_profile_context,
                atr_used_pct=atr_used_pct,
            )

    def summary(self) -> TradePathSummary:
        if not self._records:
            return TradePathSummary(
                n_trades=0,
                n_wins=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_return_pct=0.0,
                avg_mae_r=0.0,
                avg_mfe_r=0.0,
                avg_bars_held=0.0,
                by_signal_family={},
                by_regime={},
                by_session_hour={},
                by_exit_reason={},
            )
        n = len(self._records)
        wins = sum(1 for rec in self._records if rec.win)
        total_pnl = sum(rec.pnl for rec in self._records)
        return TradePathSummary(
            n_trades=n,
            n_wins=wins,
            win_rate=round(wins / n, 4),
            total_pnl=round(total_pnl, 2),
            avg_return_pct=round(sum(rec.return_pct for rec in self._records) / n, 6),
            avg_mae_r=round(sum(rec.mae_r for rec in self._records) / n, 6),
            avg_mfe_r=round(sum(rec.mfe_r for rec in self._records) / n, 6),
            avg_bars_held=round(sum(rec.bars_held for rec in self._records) / n, 2),
            by_signal_family=_count_by(self._records, "signal_family"),
            by_regime=_count_by(self._records, "regime"),
            by_session_hour=_count_by(self._records, "session_hour_utc", prefix="H"),
            by_exit_reason=_count_by(self._records, "exit_reason"),
        )

    def export_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in self._records:
                handle.write(json.dumps(asdict(record), sort_keys=True))
                handle.write("\n")

    def export_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": asdict(self.summary()),
            "records": [asdict(record) for record in self._records],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load_jsonl(cls, path: Path) -> "TradePathDatabase":
        db = cls()
        if not path.is_file():
            return db
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            db.add(TradePathRecord(**json.loads(line)))
        return db

    def __len__(self) -> int:
        return len(self._records)


def _utc_hour(ts_ns: int) -> int:
    dt = datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)
    return dt.hour


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _count_by(records: list[TradePathRecord], field: str, *, prefix: str = "") -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = getattr(record, field)
        label = f"{prefix}{int(key):02d}" if prefix and isinstance(key, int) else str(key)
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))
