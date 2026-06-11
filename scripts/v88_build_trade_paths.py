#!/usr/bin/env python3
"""Build complete forward trade paths for every immutable V8.8 signal."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prime.bar_provider import get_bars
from research.v86_recovery import load_jsonl, write_jsonl
from research.v88_trade_path import reconstruct_path


def main() -> int:
    signals = load_jsonl(ROOT / "results/v88_tpsl_replay/signal_ledgers/immutable_signal_ledger.jsonl")
    bars = get_bars(300, cache_dir=ROOT / "results/volume_bars_catalog")
    paths = [reconstruct_path(signal, bars) for signal in signals if int(signal["bar_id"]) + 97 <= len(bars)]
    out = ROOT / "results/v88_tpsl_replay/trade_paths"
    write_jsonl(out / "trade_paths.jsonl", paths)
    summary = {
        "paths": len(paths),
        "positive_mfe_before_loss_rate": sum(path["positive_mfe_before_loss"] for path in paths) / len(paths) if paths else 0.0,
        "avg_mfe": sum(path["max_favorable_excursion_pct"] for path in paths) / len(paths) if paths else 0.0,
        "avg_mae": sum(path["max_adverse_excursion_pct"] for path in paths) / len(paths) if paths else 0.0,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
