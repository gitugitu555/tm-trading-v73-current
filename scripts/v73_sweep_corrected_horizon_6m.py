#!/usr/bin/env python3
"""Sweep the volume-bar CVD fade using actual volume-bar holding horizons."""

from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.v73_sweep_6m import SweepConfig, run_config

ROOT = Path(__file__).resolve().parents[1]


def build_configs() -> list[SweepConfig]:
    configs: list[SweepConfig] = []
    for lookback in (25, 40, 60, 80, 100):
        for exit_bars in (5, 8, 12, 16):
            for mode, extra in (
                ("hybrid", ["--no-use-time-exit"]),
                ("bar_only", ["--no-use-time-exit", "--no-use-tpsl"]),
            ):
                configs.append(
                    SweepConfig(
                        name=f"corrected_{mode}_lb{lookback}_e{exit_bars}",
                        lookback=lookback,
                        exit_bars=exit_bars,
                        regime_gate=False,
                        footprint=False,
                        auction_gate=False,
                        vwap_gate=False,
                        session_extreme=False,
                        extra=extra,
                    )
                )
    return configs


def main() -> int:
    started = time.time()
    results = [run_config(config) for config in build_configs()]
    results.sort(key=lambda row: (-row.get("total_pnl", 0.0), -row.get("win_rate", 0.0)))
    summary = {
        "objective": "corrected_volume_bar_horizon",
        "note": "Wall-clock TIME exit disabled; compares hybrid TPSL+bar exits with pure bar exits.",
        "configs_tested": len(results),
        "best_by_pnl": results[0] if results else None,
        "top_10": results[:10],
        "elapsed_sec": round(time.time() - started, 1),
    }
    output = ROOT / "results/v73_sweep_corrected_horizon_6m_summary.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
