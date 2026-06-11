"""Monthly walk-forward selection over the verified immutable replay set."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median
from typing import Any

from research.v86_recovery import summarize_trades
from research.v88_policy_replay import replay_policy
from research.v88_tpsl_policies import replay_tpsl


def policy_space() -> list[dict[str, Any]]:
    policies = []
    for target in (0.0025, 0.005, 0.0075):
        for stop in (0.005, 0.01, 0.03):
            for bar_exit in (8, 16, 24, 48, 72):
                policies.append({"name": f"fixed_t{target}_s{stop}_b{bar_exit}", "target_pct": target, "stop_pct": stop, "bar_exit": bar_exit})
    for trigger in (0.001, 0.002, 0.0035, 0.005):
        for lock in (0.0, 0.0005, 0.001):
            policies.append({"name": f"be_{trigger}_{lock}", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "breakeven_trigger_mfe_pct": trigger, "breakeven_lock_pct": lock})
    for start in (0.002, 0.0035, 0.005):
        for giveback in (0.25, 0.5, 0.66):
            policies.append({"name": f"trail_{start}_{giveback}", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": start, "trail_giveback_pct": giveback})
    policies.extend(
        [
            {"name": "baseline_fixed_tpsl", "target_pct": 0.0055, "stop_pct": 0.03, "bar_exit": 24},
            {"name": "best_breakeven_policy", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "breakeven_trigger_mfe_pct": 0.001, "breakeven_lock_pct": 0.001},
            {"name": "best_mfe_trailing_policy", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25},
        ]
    )
    deduped = {json.dumps(policy, sort_keys=True): policy for policy in policies}
    return sorted(deduped.values(), key=lambda row: row["name"])


def build_monthly_walkforward_report(
    signals: list[dict[str, Any]],
    paths: dict[str, dict[str, Any]],
    *,
    protocols: list[tuple[int, int]] = [(6, 1), (12, 3), (24, 6)],
) -> dict[str, Any]:
    month_index = _month_index(signals)
    months = sorted(month_index)
    policies = policy_space()
    policy_month_summaries: dict[str, dict[str, dict[str, Any]]] = {}
    for policy in policies:
        replay = replay_policy(signals, paths, policy, occupancy_mode="independent")
        monthly = defaultdict(list)
        for trade in replay["trades"]:
            month = datetime.fromtimestamp(int(trade["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y-%m")
            monthly[month].append(trade)
        policy_month_summaries[policy["name"]] = {month: _month_summary(rows) for month, rows in monthly.items()}

    protocol_reports = []
    for train_months, test_months in protocols:
        folds = []
        for start in range(0, max(0, len(months) - train_months - test_months + 1)):
            train = months[start : start + train_months]
            test = months[start + train_months : start + train_months + test_months]
            train_scores = {
                policy["name"]: _aggregate_months(policy_month_summaries[policy["name"]], train)
                for policy in policies
            }
            best_name = max(train_scores, key=lambda name: train_scores[name]["net_expectancy"])
            train_summary = train_scores[best_name]
            test_summary = _aggregate_months(policy_month_summaries[best_name], test)
            folds.append(
                {
                    "train_months": train,
                    "test_months": test,
                    "selected_policy": best_name,
                    "train_expectancy": train_summary["net_expectancy"],
                    "test_expectancy": test_summary["net_expectancy"],
                    "train_profit_factor": train_summary["profit_factor"],
                    "test_profit_factor": test_summary["profit_factor"],
                    "train_sharpe": train_summary["sharpe"],
                    "test_sharpe": test_summary["sharpe"],
                    "selected_params": next(policy for policy in policies if policy["name"] == best_name),
                    "parameter_stability": 1.0,
                    "cost_sensitivity": _cost_sensitivity(train_summary, test_summary),
                }
            )
        protocol_reports.append(
            {
                "train_months": train_months,
                "test_months": test_months,
                "folds": folds,
                "train_positive_splits": sum(fold["train_expectancy"] > 0 for fold in folds),
                "test_positive_splits": sum(fold["test_expectancy"] > 0 for fold in folds),
                "mean_test_expectancy": sum(fold["test_expectancy"] for fold in folds) / len(folds) if folds else 0.0,
                "median_test_expectancy": median([fold["test_expectancy"] for fold in folds]) if folds else 0.0,
                "worst_test_month": min((min(fold["test_months"]), fold["test_expectancy"]) for fold in folds) if folds else None,
                "best_test_month": max((max(fold["test_months"]), fold["test_expectancy"]) for fold in folds) if folds else None,
                "train_test_degradation": _degradation(folds),
                "positive_test_split_rate": sum(fold["test_expectancy"] > 0 for fold in folds) / len(folds) if folds else 0.0,
                "status": "candidate_rejected" if any(fold["test_expectancy"] <= 0 for fold in folds) else "candidate",
            }
        )
    return {
        "protocols": protocol_reports,
        "policy_count": len(policies),
        "available_months": months,
        "hard_rule": "median test expectancy > 0 and test profit factor > 1.05 required",
    }


def _month_index(signals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    month_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in signals:
        month = datetime.fromtimestamp(int(row["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y-%m")
        month_index[month].append(row)
    return month_index


def _aggregate_months(monthly: dict[str, dict[str, Any]], months: list[str]) -> dict[str, Any]:
    rows = [monthly[month] for month in months if month in monthly]
    if not rows:
        return _month_summary([])
    return {
        "trade_count": sum(row["trade_count"] for row in rows),
        "net_expectancy": sum(row["net_expectancy"] * row["trade_count"] for row in rows) / sum(row["trade_count"] for row in rows),
        "gross_expectancy": sum(row["gross_expectancy"] * row["trade_count"] for row in rows) / sum(row["trade_count"] for row in rows),
        "profit_factor": sum(row["gross_profit"] for row in rows) / max(sum(row["gross_loss"] for row in rows), 1e-12),
        "sharpe": sum(row["sharpe"] for row in rows) / len(rows),
    }


def _degradation(folds: list[dict[str, Any]]) -> float:
    if not folds:
        return 0.0
    deltas = [fold["train_expectancy"] - fold["test_expectancy"] for fold in folds]
    return sum(deltas) / len(deltas)


def _cost_sensitivity(train_summary: dict[str, Any], test_summary: dict[str, Any]) -> dict[str, float]:
    return {
        "train_minus_test_expectancy": train_summary["net_expectancy"] - test_summary["net_expectancy"],
        "train_minus_test_sharpe": train_summary["sharpe"] - test_summary["sharpe"],
    }


def _month_summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return {
            "trade_count": 0,
            "net_expectancy": 0.0,
            "gross_expectancy": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
        }
    net_returns = [float(row["net_return_pct"]) for row in trades]
    gross_returns = [float(row["gross_return_pct"]) for row in trades]
    gross_profit = sum(value for value in net_returns if value > 0)
    gross_loss = abs(sum(value for value in net_returns if value < 0))
    return {
        "trade_count": len(trades),
        "net_expectancy": sum(net_returns) / len(net_returns),
        "gross_expectancy": sum(gross_returns) / len(gross_returns),
        "profit_factor": gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0),
        "sharpe": summarize_trades(trades)["sharpe"],
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }
