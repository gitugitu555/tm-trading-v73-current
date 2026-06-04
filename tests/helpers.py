from datetime import datetime, timezone

from core.types import SignedTrade


def ts(second: int = 0) -> datetime:
    return datetime(2026, 5, 21, 9, 30, second, tzinfo=timezone.utc)


def trade(
    *,
    second: int = 0,
    price: float = 100.0,
    size: float = 1.0,
    side: str = "BUY",
) -> SignedTrade:
    return SignedTrade(
        ts_event=ts(second),
        exchange="BINANCE",
        symbol="BTCUSDT",
        price=price,
        size_base=size,
        notional_quote=price * size,
        side=side,  # type: ignore[arg-type]
        confidence=1.0,
        method="test",
    )
