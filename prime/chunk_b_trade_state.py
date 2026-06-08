"""Typed open-trade state for Chunk B backtests."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class OpenTradeState:
    entry_ts_ns: int
    side: int
    entry_price: float
    notional: float
    signal_id: str
    permission_verdict: str
    reason_codes: tuple[str, ...]
    exit_after_ts_ns: int
    exit_after_volume_bars: int | None = None
    bars_since_entry: int = 0
    max_adverse: float = 0.0
    max_favorable: float = 0.0
    target_pct: float | None = None
    stop_pct: float | None = None

    @classmethod
    def from_legacy_dict(cls, values: dict) -> "OpenTradeState":
        return cls(
            entry_ts_ns=int(values.get("entry_ts_ns", 0)),
            side=int(values["side"]),
            entry_price=float(values["entry_price"]),
            notional=float(values.get("notional", 0.0)),
            signal_id=str(values.get("signal_id", "")),
            permission_verdict=str(values.get("permission_verdict", "")),
            reason_codes=tuple(values.get("reason_codes", ())),
            exit_after_ts_ns=int(values["exit_after_ts_ns"]),
            max_adverse=float(values.get("max_adverse", 0.0)),
            max_favorable=float(values.get("max_favorable", 0.0)),
            target_pct=values.get("target_pct"),
            stop_pct=values.get("stop_pct"),
        )

    def with_excursion(self, price: float) -> "OpenTradeState":
        if self.entry_price == 0:
            return self
        if self.side > 0:
            adverse = max(0.0, (self.entry_price - price) / self.entry_price)
            favorable = max(0.0, (price - self.entry_price) / self.entry_price)
        else:
            adverse = max(0.0, (price - self.entry_price) / self.entry_price)
            favorable = max(0.0, (self.entry_price - price) / self.entry_price)
        return replace(
            self,
            max_adverse=max(self.max_adverse, adverse),
            max_favorable=max(self.max_favorable, favorable),
        )

    def as_legacy_dict(self) -> dict:
        return {
            "entry_ts_ns": self.entry_ts_ns,
            "side": self.side,
            "entry_price": self.entry_price,
            "notional": self.notional,
            "signal_id": self.signal_id,
            "permission_verdict": self.permission_verdict,
            "reason_codes": self.reason_codes,
            "exit_after_ts_ns": self.exit_after_ts_ns,
            "max_adverse": self.max_adverse,
            "max_favorable": self.max_favorable,
            "target_pct": self.target_pct,
            "stop_pct": self.stop_pct,
        }
