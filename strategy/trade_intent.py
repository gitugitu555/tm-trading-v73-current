"""Structured trade intent object."""

from __future__ import annotations

from dataclasses import dataclass

from strategy.alpha_permission import AlphaPermission


@dataclass(frozen=True)
class TradeIntent:
    instrument_id: str
    direction: int
    urgency: str
    max_notional: float
    entry_type: str
    invalidation_price: float
    reason_codes: tuple[str, ...]
    alpha_permission: AlphaPermission
