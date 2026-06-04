"""Price-level footprint engine."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


class FootprintEngine:
    def __init__(self, tick_size: float) -> None:
        if tick_size <= 0:
            raise ValueError("tick_size must be positive")
        self.tick_size = float(tick_size)
        self.levels: dict[float, dict[str, float]] = {}

    def round_price(self, price: float) -> float:
        units = Decimal(str(price)) / Decimal(str(self.tick_size))
        rounded_units = units.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return float(rounded_units * Decimal(str(self.tick_size)))

    def update(self, price: float, size: float, side: str) -> tuple[float, dict[str, float]]:
        level = self.round_price(price)
        row = self.levels.setdefault(
            level,
            {
                "buy_volume": 0.0,
                "sell_volume": 0.0,
                "delta": 0.0,
                "total_volume": 0.0,
            },
        )
        if side == "BUY":
            row["buy_volume"] += size
            row["delta"] += size
        elif side == "SELL":
            row["sell_volume"] += size
            row["delta"] -= size
        row["total_volume"] += size
        return level, dict(row)

    def snapshot(self) -> dict[float, dict[str, float]]:
        return {price: dict(row) for price, row in sorted(self.levels.items())}

    def reset(self) -> None:
        self.levels.clear()
