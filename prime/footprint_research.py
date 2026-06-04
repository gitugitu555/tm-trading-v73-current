"""Footprint F1-F5 research helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from math import isclose
from typing import Iterable

from features.footprint import FootprintEngine as LevelFootprintEngine


@dataclass(frozen=True)
class FootprintConfig:
    tick_size: float = 0.5
    stack_levels: int = 3
    imbalance_ratio: float = 3.0
    min_level_total_volume: float = 5.0
    max_extension_ticks: int = 1
    absorption_delta_share: float = 0.15
    volume_floor: float = 50.0
    structure_tick_radius: int = 2
    vwap_deviation_pct: float = 0.003
    session_extreme_pct: float = 0.003


@dataclass(frozen=True)
class FootprintStageResult:
    side: int
    f1: bool
    f2: bool
    f3: bool
    f4: bool
    f5: bool
    dominant_level: float | None
    boundary_level: float | None
    cluster_levels: tuple[float, ...]


def round_level(price: float, tick_size: float) -> float:
    units = Decimal(str(price)) / Decimal(str(tick_size))
    rounded_units = units.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(rounded_units * Decimal(str(tick_size)))


def build_snapshot_from_ticks(
    ticks: Iterable[tuple[float, float, str]],
    *,
    tick_size: float,
) -> dict[float, dict[str, float]]:
    engine = LevelFootprintEngine(tick_size)
    for price, size, side in ticks:
        engine.update(price, size, side)
    return engine.snapshot()


def detect_stacked_imbalance(
    snapshot: dict[float, dict[str, float]],
    *,
    tick_size: float,
    stack_levels: int = 3,
    imbalance_ratio: float = 3.0,
    min_level_total_volume: float = 5.0,
) -> dict:
    ordered_levels = sorted(snapshot)
    best_run: list[float] = []
    best_side = 0
    best_score = -1.0

    current_run: list[float] = []
    current_side = 0

    def finalize_run() -> None:
        nonlocal best_run, best_side, best_score, current_run, current_side
        if len(current_run) < stack_levels or current_side == 0:
            current_run = []
            current_side = 0
            return
        if not all(snapshot[level]["total_volume"] >= min_level_total_volume for level in current_run):
            current_run = []
            current_side = 0
            return
        score = sum(snapshot[level]["total_volume"] for level in current_run)
        if score > best_score:
            best_score = score
            best_run = list(current_run)
            best_side = current_side
        current_run = []
        current_side = 0

    for level in ordered_levels:
        side = _level_side(snapshot[level], imbalance_ratio)
        if side == 0:
            finalize_run()
            continue
        if current_run and side == current_side and _is_consecutive(current_run[-1], level, tick_size):
            current_run.append(level)
        else:
            finalize_run()
            current_run = [level]
            current_side = side
    finalize_run()

    if not best_run:
        return {
            "pass": False,
            "side": 0,
            "dominant_level": None,
            "boundary_level": None,
            "cluster_levels": (),
        }

    dominant_level = max(best_run, key=lambda level: abs(snapshot[level]["delta"]))
    boundary_level = max(best_run) if best_side == -1 else min(best_run)
    return {
        "pass": True,
        "side": best_side,
        "dominant_level": dominant_level,
        "boundary_level": boundary_level,
        "cluster_levels": tuple(best_run),
    }


def rejection_confirmation(
    *,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    boundary_level: float,
    side: int,
    tick_size: float,
    max_extension_ticks: int = 1,
) -> bool:
    extension = max_extension_ticks * tick_size
    if side == -1:
        return bar_high >= boundary_level and bar_close < boundary_level and (bar_high - boundary_level) <= extension
    if side == +1:
        return bar_low <= boundary_level and bar_close > boundary_level and (boundary_level - bar_low) <= extension
    return False


def absorption_confirmation(
    *,
    row: dict[str, float],
    bar_high: float,
    bar_low: float,
    boundary_level: float,
    side: int,
    tick_size: float,
    absorption_delta_share: float = 0.15,
    volume_floor: float = 50.0,
    max_price_extension_ticks: int = 1,
) -> bool:
    total_volume = row.get("total_volume", 0.0)
    delta = row.get("delta", 0.0)
    if total_volume < volume_floor or total_volume <= 0:
        return False
    if abs(delta) / total_volume > absorption_delta_share:
        return False
    extension = max_price_extension_ticks * tick_size
    if side == -1:
        return (bar_high - boundary_level) <= extension
    if side == +1:
        return (boundary_level - bar_low) <= extension
    return False


def structure_confluence(
    *,
    level: float,
    session_high: float,
    session_low: float,
    vwap: float,
    tick_size: float,
    structure_tick_radius: int = 2,
    vwap_deviation_pct: float = 0.003,
    session_extreme_pct: float = 0.003,
) -> bool:
    tick_band = structure_tick_radius * tick_size

    if session_high > 0.0:
        high_band = max(tick_band, session_high * session_extreme_pct)
        if abs(level - session_high) <= high_band:
            return True

    if session_low != float("inf"):
        low_band = max(tick_band, session_low * session_extreme_pct)
        if abs(level - session_low) <= low_band:
            return True

    if vwap > 0.0:
        vwap_band = max(tick_band, vwap * vwap_deviation_pct)
        if abs(level - vwap) <= vwap_band:
            return True

    return False


def evaluate_footprint_bar(
    *,
    snapshot: dict[float, dict[str, float]],
    bar_high: float,
    bar_low: float,
    bar_close: float,
    session_high: float,
    session_low: float,
    vwap: float,
    config: FootprintConfig,
) -> FootprintStageResult:
    stacked = detect_stacked_imbalance(
        snapshot,
        tick_size=config.tick_size,
        stack_levels=config.stack_levels,
        imbalance_ratio=config.imbalance_ratio,
        min_level_total_volume=config.min_level_total_volume,
    )
    if not stacked["pass"]:
        return FootprintStageResult(
            side=0,
            f1=False,
            f2=False,
            f3=False,
            f4=False,
            f5=False,
            dominant_level=None,
            boundary_level=None,
            cluster_levels=(),
        )

    side = int(stacked["side"])
    boundary_level = float(stacked["boundary_level"])
    dominant_level = float(stacked["dominant_level"])
    row = snapshot[boundary_level]
    f1 = True
    f2 = rejection_confirmation(
        bar_high=bar_high,
        bar_low=bar_low,
        bar_close=bar_close,
        boundary_level=boundary_level,
        side=side,
        tick_size=config.tick_size,
        max_extension_ticks=config.max_extension_ticks,
    )
    f3 = absorption_confirmation(
        row=row,
        bar_high=bar_high,
        bar_low=bar_low,
        boundary_level=boundary_level,
        side=side,
        tick_size=config.tick_size,
        absorption_delta_share=config.absorption_delta_share,
        volume_floor=config.volume_floor,
        max_price_extension_ticks=config.max_extension_ticks,
    )
    f4 = structure_confluence(
        level=boundary_level,
        session_high=session_high,
        session_low=session_low,
        vwap=vwap,
        tick_size=config.tick_size,
        structure_tick_radius=config.structure_tick_radius,
        vwap_deviation_pct=config.vwap_deviation_pct,
        session_extreme_pct=config.session_extreme_pct,
    )
    f5 = f1 and f4 and (f2 or f3)
    return FootprintStageResult(
        side=side,
        f1=f1,
        f2=f2,
        f3=f3,
        f4=f4,
        f5=f5,
        dominant_level=dominant_level,
        boundary_level=boundary_level,
        cluster_levels=tuple(stacked["cluster_levels"]),
    )


def _level_side(row: dict[str, float], imbalance_ratio: float) -> int:
    buy_volume = row.get("buy_volume", 0.0)
    sell_volume = row.get("sell_volume", 0.0)
    if sell_volume >= imbalance_ratio * max(buy_volume, 1e-9):
        return -1
    if buy_volume >= imbalance_ratio * max(sell_volume, 1e-9):
        return +1
    return 0


def _is_consecutive(prev_level: float, current_level: float, tick_size: float) -> bool:
    return isclose(current_level - prev_level, tick_size, rel_tol=0.0, abs_tol=tick_size * 1e-6)
