# Signal Ledger Schema

`research/v88_signal_ledger.py` generates deterministic append-only signals from immutable volume bars. Position occupancy is not an input.

The ledger includes deterministic IDs, bar timestamps/OHLCV, delta/CVD slope/acceleration, signal strength, feature snapshots, provenance, and build-manifest hash.

Current source warning: the available consolidated catalog contains 14,282 bars from May-August 2020 despite its six-year name.
