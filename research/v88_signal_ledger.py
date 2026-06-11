"""Deterministic immutable signal-ledger construction."""

from __future__ import annotations

import hashlib
import json
import bisect
from collections import deque
from pathlib import Path
from typing import Any, Sequence

from prime.volume_bars import VolumeBar
from prime.volume_bar_cvd import volume_bar_cvd_signal


def deterministic_signal_id(bar: VolumeBar, side: int, lookback_bars: int, manifest_hash: str) -> str:
    raw = f"BTCUSDT|{bar.end_ts_ns}|{side}|{lookback_bars}|{manifest_hash}"
    return f"V88_{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def build_signal_ledger(
    bars: Sequence[VolumeBar],
    *,
    lookback_bars: int = 30,
    htf_flat_quantile: float = 0.25,
    source_archive: str = "consolidated_catalog",
    build_manifest_hash: str = "",
) -> list[dict[str, Any]]:
    ledger = []
    timestamps = [bar.end_ts_ns for bar in bars]
    abs_changes: deque[float] = deque(maxlen=2000)
    sorted_abs: list[float] = []
    previous_cvd = 0.0
    previous_slope = 0.0
    for idx, bar in enumerate(bars):
        prior_idx = bisect.bisect_left(timestamps, bar.end_ts_ns - 3_600_000_000_000, 0, idx + 1)
        htf_change = bar.cumulative_delta - bars[prior_idx].cumulative_delta
        flat_abs = sorted_abs[int((len(sorted_abs) - 1) * htf_flat_quantile)] if len(sorted_abs) >= 10 else 0.0
        abs_value = abs(htf_change)
        if len(abs_changes) == abs_changes.maxlen:
            old = abs_changes[0]
            sorted_abs.pop(bisect.bisect_left(sorted_abs, old))
        abs_changes.append(abs_value)
        bisect.insort(sorted_abs, abs_value)
        slope = bar.cumulative_delta - previous_cvd
        accel = slope - previous_slope
        previous_cvd = bar.cumulative_delta
        previous_slope = slope
        signal = volume_bar_cvd_signal(
            bars[max(0, idx - lookback_bars): idx + 1], lookback_bars=lookback_bars, htf_change=htf_change,
            flat_abs=flat_abs, timestamp_ns=bar.end_ts_ns, price=bar.close,
        )
        if signal is None:
            continue
        side = int(signal["side"])
        ledger.append(
            {
                "signal_id": deterministic_signal_id(bar, side, lookback_bars, build_manifest_hash),
                "symbol": "BTCUSDT",
                "bar_id": idx,
                "bar_start_ts_ns": bar.start_ts_ns,
                "bar_end_ts_ns": bar.end_ts_ns,
                "signal_ts_ns": bar.end_ts_ns,
                "side": "long" if side > 0 else "short",
                "side_int": side,
                "entry_reference_price": bar.close,
                "bar_open": bar.open, "bar_high": bar.high, "bar_low": bar.low, "bar_close": bar.close,
                "volume": bar.volume, "delta": bar.delta, "cvd": bar.cumulative_delta,
                "cvd_slope": slope, "cvd_accel": accel,
                "divergence_score": float(signal["strength"]),
                "signal_strength": float(signal["strength"]),
                "lookback_bars": lookback_bars,
                "feature_snapshot": {"htf_change": htf_change, "htf_flat_abs": flat_abs},
                "profile_snapshot": {},
                "risk_snapshot": {},
                "source_archive": source_archive,
                "build_manifest_hash": build_manifest_hash,
            }
        )
    return ledger


def write_append_only(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if existing != records:
            raise RuntimeError(f"append-only ledger mismatch: {path}")
        return
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8")
