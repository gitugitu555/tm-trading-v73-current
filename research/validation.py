"""Walk-forward and Monte Carlo validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from statistics import median
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class WalkForwardFold:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class MonteCarloSummary:
    mean: float
    p05: float
    p50: float
    p95: float
    min_value: float
    max_value: float


@dataclass(frozen=True)
class PromotionVerdict:
    eligible: bool
    reasons: tuple[str, ...]
    metrics: dict[str, float]


def walk_forward_splits(
    items: Sequence[T],
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> list[WalkForwardFold]:
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    step = step_size or test_size
    folds: list[WalkForwardFold] = []
    start = 0
    while start + train_size + test_size <= len(items):
        folds.append(
            WalkForwardFold(
                train_start=start,
                train_end=start + train_size,
                test_start=start + train_size,
                test_end=start + train_size + test_size,
            )
        )
        start += step
    return folds


def monte_carlo_trade_bootstrap(
    returns: Sequence[float],
    *,
    n_samples: int = 1000,
    block_size: int = 1,
    seed: int = 7,
) -> MonteCarloSummary:
    if not returns:
        return MonteCarloSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_samples):
        path: list[float] = []
        while len(path) < len(returns):
            start = rng.randrange(0, len(returns))
            path.extend(returns[start : start + block_size])
        path = path[: len(returns)]
        samples.append(sum(path))
    samples.sort()
    return MonteCarloSummary(
        mean=sum(samples) / len(samples),
        p05=_pct(samples, 0.05),
        p50=_pct(samples, 0.50),
        p95=_pct(samples, 0.95),
        min_value=samples[0],
        max_value=samples[-1],
    )


def promote_shadow_gate(
    *,
    baseline_expectancy: float,
    candidate_expectancy: float,
    baseline_sharpe: float,
    candidate_sharpe: float,
    baseline_drawdown: float,
    candidate_drawdown: float,
    baseline_trade_count: int,
    candidate_trade_count: int,
    blocked_winners: int,
    blocked_losers: int,
) -> PromotionVerdict:
    reasons: list[str] = []
    eligible = True
    if candidate_expectancy < baseline_expectancy * 1.05:
        eligible = False
        reasons.append("EXPECTANCY_DELTA_TOO_SMALL")
    if candidate_sharpe < baseline_sharpe + 0.10 and candidate_sharpe < baseline_sharpe * 1.05:
        eligible = False
        reasons.append("SHARPE_DELTA_TOO_SMALL")
    if candidate_drawdown < baseline_drawdown * 0.95:
        reasons.append("DRAWDOWN_IMPROVED")
    elif candidate_drawdown > baseline_drawdown * 1.05:
        eligible = False
        reasons.append("DRAWDOWN_WORSENED")
    retention = candidate_trade_count / max(baseline_trade_count, 1)
    if retention < 0.50:
        eligible = False
        reasons.append("TRADE_RETENTION_TOO_LOW")
    ratio = blocked_losers / max(blocked_winners, 1)
    if ratio <= 1.5:
        eligible = False
        reasons.append("BLOCK_RATIO_TOO_LOW")
    return PromotionVerdict(
        eligible=eligible,
        reasons=tuple(reasons),
        metrics={
            "retention": round(retention, 6),
            "block_ratio": round(ratio, 6),
        },
    )


def _pct(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    idx = min(len(values) - 1, max(0, int(math.floor(len(values) * pct))))
    return float(values[idx])
