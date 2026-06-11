#!/usr/bin/env python3
"""Bucketized signal-attribution report over the verified replay set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v86_recovery import load_jsonl
from research.v90_signal_attribution import signal_attribution


def main() -> int:
    signals = load_jsonl(ROOT / "results/v89_data_foundation/verified_signal_ledger/immutable_signal_ledger.jsonl")
    paths = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v89_data_foundation/verified_trade_paths/trade_paths.jsonl")}
    report = signal_attribution(signals, paths)
    out = ROOT / "results/v90_alpha_rebuild/signal_attribution"
    out.mkdir(parents=True, exist_ok=True)
    (out / "signal_attribution.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v90_alpha_rebuild/01_signal_attribution.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Signal Attribution\n\n"
        "The bucketed signal attribution artifact is written under `results/v90_alpha_rebuild/signal_attribution/`.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
