"""Enforce NVMe hot-path reads for research scripts."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOT_ROOT = Path(os.environ.get("TM_DATA_HOT_ROOT", REPO_ROOT / "data/raw"))
DEFAULT_COLD_ROOT = Path(os.environ.get("TM_DATA_COLD_ROOT", "/mnt/seagate/tm-trading-v555/data/raw"))

BTCUSDT_AGGTRADES_6Y = (
    DEFAULT_HOT_ROOT / "binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
)


def _seagate_st_dev() -> int | None:
    cold = DEFAULT_COLD_ROOT
    if not cold.exists():
        return None
    return cold.stat().st_dev


def assert_nvme_path(path: Path, *, label: str = "path") -> Path:
    """Raise if path resolves to the Seagate cold-storage device."""
    resolved = path.resolve()
    if str(resolved).startswith("/mnt/seagate"):
        raise RuntimeError(
            f"{label} resolves to Seagate HDD ({resolved}). "
            f"Set TM_DATA_HOT_ROOT to NVMe data under {REPO_ROOT / 'data/raw'}."
        )
    seagate_dev = _seagate_st_dev()
    if seagate_dev is not None and resolved.exists():
        try:
            if resolved.stat().st_dev == seagate_dev:
                raise RuntimeError(
                    f"{label} is on Seagate device ({resolved}). Use NVMe hot cache."
                )
        except FileNotFoundError:
            pass
    return resolved


def assert_nvme_archive(archive: Path) -> Path:
    """Ensure one aggTrades zip is read from NVMe, not cold HDD."""
    assert_nvme_path(archive, label="archive")
    seagate_dev = _seagate_st_dev()
    if seagate_dev is not None and archive.stat().st_dev == seagate_dev:
        raise RuntimeError(
            f"Archive {archive.name} is on Seagate HDD. "
            "Run: python scripts/binance_data_manager.py ... sync --direction cold-to-hot"
        )
    return archive


def hot_btcusdt_aggtrades_dir() -> Path:
    """Canonical six-year BTCUSDT aggTrades directory on NVMe."""
    path = assert_nvme_path(BTCUSDT_AGGTRADES_6Y, label="BTCUSDT aggTrades hot path")
    if not path.is_dir():
        raise FileNotFoundError(f"Hot dataset directory missing: {path}")
    return path