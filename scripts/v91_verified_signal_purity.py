#!/usr/bin/env python3
"""Run a signal-only purity test on the verified six-year volume-bar catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.v89_volume_bar_builder import load_verified_catalog
from research.v91_signal_purity import score_signal_purity


DEFAULT_CATALOG = Path(
    "results/v89_data_foundation/catalog/"
    "BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
)
DEFAULT_MANIFEST = DEFAULT_CATALOG.with_name("manifest.json")
DEFAULT_OUTPUT = Path("results/v91_parameter_test/verified_signal_purity_lb40_h5.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lookback-bars", type=int, default=40)
    parser.add_argument("--horizon-bars", type=int, default=5)
    parser.add_argument("--htf-flat-quantile", type=float, default=0.25)
    parser.add_argument("--rolling-window", type=int, default=2000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    bars = load_verified_catalog(args.catalog)
    report = score_signal_purity(
        bars,
        lookback_bars=args.lookback_bars,
        horizon_bars=args.horizon_bars,
        htf_flat_quantile=args.htf_flat_quantile,
        rolling_window=args.rolling_window,
    )
    report["catalog"] = {
        "path": str(args.catalog),
        "catalog_hash": manifest["catalog_hash"],
        "catalog_manifest_hash": manifest["catalog_manifest_hash"],
        "bar_count": manifest["bar_count"],
        "start_iso": manifest["start_iso"],
        "end_iso": manifest["end_iso"],
    }
    report["notes"] = [
        "No TP/SL, fees, slippage, position occupancy, entry lag, or trade-exit logic is used.",
        "Legacy D4 uses a full-history HTF quantile and is reported only to reproduce the old diagnostic.",
        "Past-only D4 uses the prior 2,000 HTF changes and excludes the current observation.",
        "Year attribution uses the UTC year of the signal bar; forward returns may cross year boundaries.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    for mode, values in report["modes"].items():
        overall = values["overall"]
        print(
            f"{mode}: events={overall['events']} hit={overall['hit_rate']:.4%} "
            f"mean_sfr={overall['mean_signed_forward_return']:.8f} ic={overall['ic']:.6f}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
