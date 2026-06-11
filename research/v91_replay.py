"""Replay utilities for V9.1 candidate signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from research.v88_policy_replay import replay_policy
from research.v88_trade_path import reconstruct_path
from research.v88_tpsl_policies import replay_tpsl


def replay_candidates(catalog_bars, signals: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    paths = {signal["signal_id"]: reconstruct_path(signal, catalog_bars) for signal in signals if int(signal["bar_id"]) + 97 <= len(catalog_bars)}
    trades = [replay_tpsl(path, policy) for path in paths.values()]
    summary = replay_policy(signals, paths, policy, occupancy_mode=policy.get("occupancy_mode", "independent"), max_concurrent=int(policy.get("max_concurrent", 1)))
    by_year = {}
    for year in sorted({datetime.fromtimestamp(int(row["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y") for row in trades}):
        year_trades = [row for row in trades if datetime.fromtimestamp(int(row["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y") == year]
        by_year[year] = {"trades": len(year_trades), "expectancy": sum(float(row["net_return_pct"]) for row in year_trades) / len(year_trades) if year_trades else 0.0}
    return {"paths": paths, "trades": trades, "summary": summary["summary"], "by_year": by_year}

