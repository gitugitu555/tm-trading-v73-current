"""Nautilus boundary skeleton.

The module intentionally avoids importing NautilusTrader at import time so the
feature package can be tested before the execution dependency is installed.
"""

from __future__ import annotations

from core.types import BookSnapshot, FeatureSnapshot, SignedTrade
from features.snapshots import FeatureSnapshotBuilder
from strategy.alpha_permission import AlphaPermissionEngine


class NoTradeNautilusStrategy:
    """No-order strategy boundary for deterministic feature snapshots."""

    def __init__(self, *, tick_size: float = 0.1, enable_trading: bool = False) -> None:
        self.enable_trading = enable_trading
        self.snapshots: list[FeatureSnapshot] = []
        self.snapshot_builder = FeatureSnapshotBuilder(tick_size=tick_size)
        self.alpha = AlphaPermissionEngine()

    def on_order_book_delta(self, book: BookSnapshot) -> None:
        self.snapshot_builder.update_book(book)

    def on_trade_tick(self, trade: SignedTrade) -> FeatureSnapshot:
        snapshot = self.snapshot_builder.update_trade(trade)
        permission = self.alpha.compute(snapshot)
        self.snapshots.append(snapshot)
        if permission.allow_trade and self.enable_trading:
            raise RuntimeError("live order routing is intentionally disabled in this skeleton")
        return snapshot
