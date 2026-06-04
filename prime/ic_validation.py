"""V7.2 IC validation with tightened strategy-horizon gate."""

from __future__ import annotations

from bisect import bisect_left
import math


STRATEGY_HORIZONS_NS = {
    "5m": 300_000_000_000,
    "15m": 900_000_000_000,
    "30m": 1_800_000_000_000,
}
ALL_HORIZONS_NS = {
    **STRATEGY_HORIZONS_NS,
    "1h": 3_600_000_000_000,
    "2h": 7_200_000_000_000,
    "4h": 14_400_000_000_000,
}
IC_MIN = 0.02
COLLINEARITY_MAX = 0.85


def compute_ic(
    signal_series: list[float],
    price_series: list[float],
    timestamps_ns: list[int],
    horizon_ns: int,
) -> float:
    if len(signal_series) < 30:
        return 0.0

    fwd_returns: list[float] = []
    sigs: list[float] = []
    for idx, (ts, sig) in enumerate(zip(timestamps_ns, signal_series)):
        fut = bisect_left(timestamps_ns, ts + horizon_ns, lo=idx + 1)
        if fut < len(timestamps_ns) and price_series[idx] != 0:
            fwd_returns.append((price_series[fut] - price_series[idx]) / price_series[idx])
            sigs.append(sig)

    if len(sigs) < 30:
        return 0.0
    return _spearman(sigs, fwd_returns)


def validate_engine(
    name: str,
    signal_values: list[float],
    price_series: list[float],
    timestamps_ns: list[int],
) -> dict:
    results: dict = {}
    strategy_pass = False
    any_pass = False

    for label, horizon_ns in ALL_HORIZONS_NS.items():
        ic = compute_ic(signal_values, price_series, timestamps_ns, horizon_ns)
        passed = abs(ic) >= IC_MIN
        results[label] = {"ic": round(ic, 4), "pass": passed}
        if passed:
            any_pass = True
            if label in STRATEGY_HORIZONS_NS:
                strategy_pass = True

    if strategy_pass:
        verdict = "KEEP"
    elif any_pass:
        verdict = "CONTEXT_ONLY"
    else:
        verdict = "DELETE"

    results["verdict"] = verdict
    results["engine"] = name
    results["sample_size"] = len(signal_values)
    return results


def check_collinearity(a: list[float], b: list[float]) -> float:
    if len(a) < 30 or len(b) < 30:
        return 0.0
    size = min(len(a), len(b))
    return abs(_spearman(a[:size], b[:size]))


def _spearman(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    return _pearson(_ranks(a), _ranks(b))


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    denom = math.sqrt(var_a * var_b)
    return cov / denom if denom else 0.0


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(indexed):
        end = idx + 1
        while end < len(indexed) and indexed[end][1] == indexed[idx][1]:
            end += 1
        avg_rank = (idx + 1 + end) / 2.0
        for pos in range(idx, end):
            ranks[indexed[pos][0]] = avg_rank
        idx = end
    return ranks

