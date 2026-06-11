# V8.9 Final Data Foundation Decision

## Decision

The prior `6y` catalog was a mislabeled partial consolidation that stopped in
August 2020. The raw data itself was present locally; the failure was catalog
construction and validation, not missing downloads.

V8.9 now provides a deterministic verified catalog spanning May 22, 2020
through May 21, 2026. It contains 3,662,935,692 canonical raw trades and
509,147 completed 300-BTC volume bars.

## Verified Foundation

- Coverage passes with no missing canonical archive.
- One overlapping May 2021 monthly archive is excluded.
- Catalog hash: `234617593ff6f697e1a584b88b6f8b1b9ee1bd2a8cc2e0b314bb3e8aca4a7233`
- Catalog manifest hash: `6361d90d275d9658ca6bda1e102a82d039073ae6c11dd96178f72be2396b0ef9`
- Repeated builds produce identical hashes.
- The immutable ledger contains 27,979 occupancy-free signals.
- 27,978 signals have complete 96-bar paths.

## Alpha Result

The May-August 2020 negative result generalizes to the full verified sample.
The best of 66 fixed policies remains negative:

- Policy: `trail_0.002_0.25`
- Net expectancy: -0.00023704
- Profit factor: 0.8660
- Sharpe: -0.7279

There are positive years, but no policy has survived chronological
walk-forward selection. MFE protection reduces losses but does not repair
expectancy. No strategy or capital policy should be promoted.

## Remaining Limits

- Full raw trade-ID duplicate scanning remains pending.
- The replay's explicit fee/slippage accounting remains incomplete.
- Monthly walk-forward train/select/test execution remains pending.
- Profile, CVD slope/acceleration, and capital overlays remain shadow-only.

## Next Phase

Implement cost-aware chronological walk-forward policy selection over the
verified catalog. If no policy reaches positive out-of-sample expectancy and
profit factor above one, retire this CVD-divergence alpha rather than continue
full-sample tuning.

