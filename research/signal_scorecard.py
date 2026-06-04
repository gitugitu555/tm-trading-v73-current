"""Signal-only metrics separate from trade conversion (V7.7 law #4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SignalEvent:
    bar_index: int
    timestamp_ns: int
    side: int
    entry_price: float
    signal_id: str
    permission_verdict: str


@dataclass
class SignalScorecard:
    horizon_bars: int = 5
    events: list[SignalEvent] = field(default_factory=list)
    filter_drops: dict[str, int] = field(default_factory=dict)

    def record_drop(self, reason: str) -> None:
        self.filter_drops[reason] = self.filter_drops.get(reason, 0) + 1

    def add(self, event: SignalEvent) -> None:
        self.events.append(event)

    def finalize(self, closes: list[float]) -> dict[str, Any]:
        if not self.events:
            return {
                "horizon_bars": self.horizon_bars,
                "events": 0,
                "hit_rate": 0.0,
                "mean_sfr": 0.0,
                "ic_proxy": 0.0,
                "filter_drops": dict(sorted(self.filter_drops.items())),
            }

        signed_returns: list[float] = []
        hits = 0
        for event in self.events:
            idx = event.bar_index
            horizon = self.horizon_bars
            if idx + horizon >= len(closes) or event.entry_price == 0:
                continue
            forward = (closes[idx + horizon] - closes[idx]) / event.entry_price
            signed = event.side * forward
            signed_returns.append(signed)
            if signed > 0:
                hits += 1

        n = len(signed_returns)
        if n == 0:
            return {
                "horizon_bars": self.horizon_bars,
                "events": len(self.events),
                "scored_events": 0,
                "hit_rate": 0.0,
                "mean_sfr": 0.0,
                "ic_proxy": 0.0,
                "filter_drops": dict(sorted(self.filter_drops.items())),
            }

        mean_sfr = sum(signed_returns) / n
        hit_rate = hits / n
        if n > 1:
            mean = mean_sfr
            var = sum((r - mean) ** 2 for r in signed_returns) / (n - 1)
            std = var**0.5
            ic_proxy = mean / std if std > 1e-12 else 0.0
        else:
            ic_proxy = 0.0

        return {
            "horizon_bars": self.horizon_bars,
            "events": len(self.events),
            "scored_events": n,
            "hit_rate": round(hit_rate, 6),
            "mean_sfr": round(mean_sfr, 8),
            "ic_proxy": round(ic_proxy, 6),
            "filter_drops": dict(sorted(self.filter_drops.items())),
        }