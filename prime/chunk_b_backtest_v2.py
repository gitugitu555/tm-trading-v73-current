"""Chunk B backtester v2 entrypoint.

The v2 entrypoint points at the typed trade-state implementation in
`prime.chunk_b_backtest`. It exists so future experiments can import a stable
v2 module while the original module remains available for compatibility.
"""

from __future__ import annotations

from prime.chunk_b_backtest import (
    ChunkBBacktestConfig,
    ChunkBBacktestReport,
    ChunkBBacktester,
    PaperTrade,
)
from prime.chunk_b_trade_state import OpenTradeState

__all__ = [
    "ChunkBBacktestConfig",
    "ChunkBBacktestReport",
    "ChunkBBacktester",
    "OpenTradeState",
    "PaperTrade",
]
