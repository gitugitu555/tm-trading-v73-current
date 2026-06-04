"""Chunk B performance metrics."""

from __future__ import annotations

import math


def sharpe_ratio(returns: list[float], periods_per_year: float = 365.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    stdev = math.sqrt(variance)
    return (mean / stdev) * math.sqrt(periods_per_year) if stdev else 0.0


def skewness(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    mean = sum(values) / len(values)
    m2 = sum((value - mean) ** 2 for value in values) / len(values)
    m3 = sum((value - mean) ** 3 for value in values) / len(values)
    return m3 / (m2 ** 1.5) if m2 else 0.0


def kurtosis(values: list[float]) -> float:
    if len(values) < 4:
        return 3.0
    mean = sum(values) / len(values)
    m2 = sum((value - mean) ** 2 for value in values) / len(values)
    m4 = sum((value - mean) ** 4 for value in values) / len(values)
    return m4 / (m2 * m2) if m2 else 3.0


def deflated_sharpe_probability(
    sharpe: float,
    n_trials: int,
    skew: float,
    kurt: float,
    n_obs: int,
) -> float:
    """Approximate Bailey-Lopez de Prado DSR probability.

    Returns the probability that the observed Sharpe exceeds the expected
    maximum Sharpe from multiple trials.
    """
    if n_obs <= 1:
        return 0.0
    benchmark = expected_max_sharpe(n_trials)
    variance_adj = max(1e-12, 1 - skew * sharpe + ((kurt - 1) / 4.0) * sharpe * sharpe)
    z = (sharpe - benchmark) * math.sqrt(n_obs - 1) / math.sqrt(variance_adj)
    return normal_cdf(z)


def expected_max_sharpe(n_trials: int) -> float:
    if n_trials <= 1:
        return 0.0
    gamma = 0.5772156649015329
    a = inverse_normal_cdf(1 - 1 / max(n_trials, 2))
    b = inverse_normal_cdf(1 - 1 / (max(n_trials, 2) * math.e))
    return (1 - gamma) * a + gamma * b


def normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def inverse_normal_cdf(probability: float) -> float:
    # Peter J. Acklam's rational approximation.
    if probability <= 0 or probability >= 1:
        raise ValueError("probability must be between 0 and 1")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if probability < plow:
        q = math.sqrt(-2 * math.log(probability))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if probability > phigh:
        q = math.sqrt(-2 * math.log(1 - probability))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = probability - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
    )

