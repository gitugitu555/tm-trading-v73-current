#!/usr/bin/env python3
"""Build deterministic V8.8 immutable signals from consolidated volume bars."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prime.bar_provider import get_bars
from research.v88_signal_ledger import build_signal_ledger, write_append_only


def main() -> int:
    bars = get_bars(300, cache_dir=ROOT / "results/volume_bars_catalog")
    manifest = {"threshold_btc": 300, "lookback_bars": 30, "bar_count": len(bars), "date_min_ns": bars[0].start_ts_ns, "date_max_ns": bars[-1].end_ts_ns}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    ledger = build_signal_ledger(bars, lookback_bars=30, build_manifest_hash=digest)
    out = ROOT / "results/v88_tpsl_replay/signal_ledgers"
    write_append_only(out / "immutable_signal_ledger.jsonl", ledger)
    (out / "manifest.json").write_text(json.dumps({**manifest, "build_manifest_hash": digest, "signal_count": len(ledger)}, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
