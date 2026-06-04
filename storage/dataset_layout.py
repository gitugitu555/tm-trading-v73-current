"""Canonical dataset path helpers for raw market data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSpec:
    """Describe one logical market-data dataset."""

    exchange: str
    market: str
    kind: str
    symbol: str
    range_label: str

    def relative_path(self) -> Path:
        return Path(self.exchange) / self.market / self.kind / self.symbol / self.range_label


def dataset_path(root: Path, spec: DatasetSpec) -> Path:
    return root / spec.relative_path()


def binance_dataset_spec(
    *,
    market: str,
    kind: str,
    symbol: str,
    range_label: str,
) -> DatasetSpec:
    return DatasetSpec(
        exchange="binance",
        market=market,
        kind=kind,
        symbol=symbol,
        range_label=range_label,
    )

