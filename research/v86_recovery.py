"""Shared measurement and validation helpers for the V8.6 recovery program."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from prime.performance import (
    deflated_sharpe_probability,
    kurtosis,
    max_drawdown,
    sharpe_ratio,
    skewness,
    sortino_ratio,
)


def canonical_cli_args(args: Iterable[str]) -> list[str]:
    """Resolve repeated CLI options using argparse's last-value-wins behavior."""
    tokens = list(args)
    flags: dict[str, list[str]] = {}
    positional: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            positional.append(token)
            index += 1
            continue
        values: list[str] = []
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
            values.append(tokens[index + 1])
            index += 1
        flags[token] = values
        index += 1
    resolved: list[str] = positional
    for flag in sorted(flags):
        resolved.append(flag)
        resolved.extend(flags[flag])
    return resolved


def args_hash(args: Iterable[str]) -> str:
    payload = json.dumps(canonical_cli_args(args), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def git_commit(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
    except Exception:
        return "unknown"


def write_manifest(
    *,
    output_path: Path,
    strategy_label: str,
    strategy_description: str,
    repo_root: Path,
    runner_script: str,
    cli_args: Iterable[str],
    archives: Iterable[Path],
    execution_model: dict[str, Any],
    position_model: dict[str, Any],
    feature_flags: dict[str, Any],
) -> dict[str, Any]:
    resolved = canonical_cli_args(cli_args)
    archive_list = sorted(Path(path) for path in archives)
    names = [path.name for path in archive_list]
    dates = [name.removeprefix("BTCUSDT-aggTrades-").removesuffix(".zip") for name in names]
    manifest = {
        "strategy_label": strategy_label,
        "strategy_description": strategy_description,
        "repo_commit": git_commit(repo_root),
        "runner_script": runner_script,
        "resolved_cli_args": resolved,
        "args_hash": args_hash(resolved),
        "dataset_manifest": {
            "symbol": "BTCUSDT",
            "archive_count": len(names),
            "archive_paths_or_names": names,
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        },
        "execution_model": execution_model,
        "position_model": position_model,
        "feature_flags": feature_flags,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def normalize_trade(
    trade: dict[str, Any],
    *,
    strategy_label: str = "",
    archive: str = "",
    fee_bps_per_side: float = 5.0,
    slippage_bps_per_side: float = 1.0,
) -> dict[str, Any]:
    row = dict(trade)
    side_raw = row.get("side", 0)
    side = 1 if side_raw in {1, "long", "LONG"} else -1
    notional = float(row.get("notional", 0.0))
    pnl_net = float(row.get("pnl_net", row.get("pnl", 0.0)))
    fees = float(row.get("fees", notional * fee_bps_per_side * 2 / 10_000))
    slippage = float(row.get("slippage", notional * slippage_bps_per_side * 2 / 10_000))
    # Historical ledgers embed slippage in fill prices and subtract fees later.
    pnl_gross = float(row.get("pnl_gross", pnl_net + fees + slippage))
    return_net = float(row.get("return_net_pct", row.get("return_pct", pnl_net / notional if notional else 0.0)))
    return_gross = float(row.get("return_gross_pct", pnl_gross / notional if notional else 0.0))
    mae = float(row.get("mae_pct", row.get("max_adverse", 0.0)))
    mfe = float(row.get("mfe_pct", row.get("max_favorable", 0.0)))
    normalized = {
        **row,
        "strategy_label": row.get("strategy_label", strategy_label),
        "archive": row.get("archive", archive),
        "side": "long" if side > 0 else "short",
        "return_gross_pct": return_gross,
        "return_net_pct": return_net,
        "pnl_gross": pnl_gross,
        "pnl_net": pnl_net,
        "fees": fees,
        "slippage": slippage,
        "bars_held": int(row.get("bars_held", 0)),
        "target_pct_used": row.get("target_pct_used", row.get("target_pct")),
        "stop_pct_used": row.get("stop_pct_used", row.get("stop_pct")),
        "entry_signal_strength": row.get("entry_signal_strength"),
        "entry_cvd": row.get("entry_cvd"),
        "exit_cvd": row.get("exit_cvd"),
        "entry_poc": row.get("entry_poc"),
        "exit_poc": row.get("exit_poc"),
        "entry_vah": row.get("entry_vah"),
        "entry_val": row.get("entry_val"),
        "mfe_pct": mfe,
        "mae_pct": mae,
        "mfe_before_exit_pct": row.get("mfe_before_exit_pct", mfe),
        "mae_before_exit_pct": row.get("mae_before_exit_pct", mae),
        "would_hit_target_before_exit": row.get("would_hit_target_before_exit"),
        "would_hit_stop_before_exit": row.get("would_hit_stop_before_exit"),
    }
    return normalized


def summarize_trades(
    trades: Iterable[dict[str, Any]],
    *,
    starting_equity: float = 500.0,
    synthetic_position_pct: float = 0.01,
) -> dict[str, Any]:
    rows = sorted((normalize_trade(row) for row in trades), key=lambda row: row.get("exit_ts_ns", 0))
    pnls = [float(row["pnl_net"]) for row in rows]
    returns = [float(row["return_net_pct"]) for row in rows]
    gross_pnls = [float(row["pnl_gross"]) for row in rows]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    actual_curve = [starting_equity]
    synthetic_curve = [starting_equity]
    for row in rows:
        actual_curve.append(actual_curve[-1] + float(row["pnl_net"]))
        synthetic_curve.append(
            synthetic_curve[-1]
            + synthetic_curve[-1] * synthetic_position_pct * float(row["return_net_pct"])
        )
    fees = sum(float(row.get("fees", 0.0)) for row in rows)
    slippage = sum(float(row.get("slippage", 0.0)) for row in rows)
    net_pnl = sum(pnls)
    return {
        "starting_equity": starting_equity,
        "ending_equity_actual": actual_curve[-1],
        "ending_equity_synthetic_1pct": synthetic_curve[-1],
        "gross_pnl": sum(gross_pnls),
        "net_pnl": net_pnl,
        "fees_paid": fees,
        "slippage_paid": slippage,
        "avg_win_net": statistics.mean(wins) if wins else 0.0,
        "avg_loss_net": statistics.mean(losses) if losses else 0.0,
        "median_win": statistics.median(wins) if wins else 0.0,
        "median_loss": statistics.median(losses) if losses else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else math.inf if gross_profit else 0.0,
        "expectancy_per_trade": statistics.mean(pnls) if pnls else 0.0,
        "expectancy_bps": statistics.mean(returns) * 10_000 if returns else 0.0,
        "turnover": sum(float(row.get("notional", 0.0)) for row in rows),
        "trade_count": len(rows),
        "win_rate": len(wins) / len(rows) if rows else 0.0,
        "loss_rate": len(losses) / len(rows) if rows else 0.0,
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "max_drawdown": max_drawdown(actual_curve),
        "exit_reasons": dict(Counter(str(row.get("exit_reason", "?")) for row in rows)),
    }


def gate_shadow_value(baseline: Iterable[dict[str, Any]], allowed_signal_ids: set[str]) -> dict[str, Any]:
    rows = [normalize_trade(row) for row in baseline]
    blocked = [row for row in rows if str(row.get("signal_id", "")) not in allowed_signal_ids]
    blocked_winners = [row for row in blocked if float(row["pnl_net"]) > 0]
    blocked_losers = [row for row in blocked if float(row["pnl_net"]) < 0]
    winner_pnl = sum(float(row["pnl_net"]) for row in blocked_winners)
    loser_pnl = sum(float(row["pnl_net"]) for row in blocked_losers)
    allowed = len(rows) - len(blocked)
    return {
        "trades_allowed": allowed,
        "trades_blocked": len(blocked),
        "blocked_winners": len(blocked_winners),
        "blocked_losers": len(blocked_losers),
        "blocked_winner_pnl": winner_pnl,
        "blocked_loser_pnl": loser_pnl,
        "net_gate_value": abs(loser_pnl) - winner_pnl,
        "trade_retention_pct": allowed / len(rows) if rows else 0.0,
    }


def grouped_expectancy(trades: Iterable[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        row = normalize_trade(trade)
        groups[str(row.get(key, "unknown"))].append(row)
    return {name: summarize_trades(rows) for name, rows in sorted(groups.items())}


def robustness_metrics(
    trades: Iterable[dict[str, Any]],
    *,
    n_trials: int = 1,
    monte_carlo_samples: int = 1000,
    seed: int = 86,
) -> dict[str, Any]:
    rows = [normalize_trade(row) for row in trades]
    returns = [float(row["return_net_pct"]) for row in rows]
    summary = summarize_trades(rows)
    sharpe = float(summary["sharpe"])
    dsr = deflated_sharpe_probability(
        sharpe=sharpe,
        n_trials=max(1, n_trials),
        skew=skewness(returns),
        kurt=kurtosis(returns),
        n_obs=len(returns),
    )
    rng = random.Random(seed)
    order_paths: list[float] = []
    skip_paths: list[float] = []
    for _ in range(monte_carlo_samples):
        shuffled = returns[:]
        rng.shuffle(shuffled)
        order_paths.append(sum(shuffled))
        skip_paths.append(sum(value for value in shuffled if rng.random() >= 0.10))
    order_paths.sort()
    skip_paths.sort()
    return {
        **summary,
        "deflated_sharpe_probability": dsr,
        "dsr_passed": dsr >= 0.95,
        "trade_order_monte_carlo": _distribution(order_paths),
        "trade_skipping_10pct_monte_carlo": _distribution(skip_paths),
        "cost_sensitivity": {
            str(multiplier): statistics.mean(
                float(row["return_gross_pct"])
                - multiplier * (float(row.get("fees", 0.0)) + float(row.get("slippage", 0.0)))
                / max(float(row.get("notional", 0.0)), 1e-12)
                for row in rows
            )
            if rows
            else 0.0
            for multiplier in (0, 1, 2, 3)
        },
    }


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p05": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "p05": values[int((len(values) - 1) * 0.05)],
        "p50": values[int((len(values) - 1) * 0.50)],
        "p95": values[int((len(values) - 1) * 0.95)],
    }
