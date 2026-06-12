# V9.2 Claude Audit Notes (Source Recovery)

## Source: Previous Chat Context / Roadmap Injection

These notes were recovered from external chat context to prevent context drift and serve as an audit trail for the V9.2 rebuild.

### 1. TP/SL Geometry Drift
Claude observed a specific configuration being run:
- `stop_pct = 0.003` (0.30% stop)
- `target_pct = 0.006` (0.60% target)

This 2:1 reward ratio geometry was found to be floating in some scripts (identified as `legacy_tpsl` in `v73_conversion_sweep.py`), but did not match the V8.x institutional sweeps which defaulted to `stop_pct = 0.03` (3.0%). This revealed a severe parameter drift between "chunk_b" legacy scripts and newer V8 validation scripts.

### 2. Sharpe Annualization Fallacy
Claude correctly identified that per-trade returns should not be annualized with a fixed daily value (e.g., `periods_per_year = 365`) unless the observations are actually calendar-daily returns.

Applying annualization to per-trade returns artificially inflates the Sharpe ratio, making high-frequency strategies with small edges look artificially robust.

### 3. Daily Aggregation
If a runner does not construct daily equity curves, then any daily Sharpe claims are invalid for that runner. Future backtesters must construct explicit calendar daily equity before computing Sharpe.

## Resulting Action
These observations directly led to the creation of:
- `docs/v92_PARAMETER_SOURCE_OF_TRUTH.md`
- `docs/v92_RESEARCH_RUN_MANIFEST_SPEC.md`
