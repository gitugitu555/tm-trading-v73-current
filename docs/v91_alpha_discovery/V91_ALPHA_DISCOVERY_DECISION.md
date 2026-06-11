# V9.1 Alpha Discovery Decision

## Verdict

Reject the old CVD-divergence family for live trading. Retain it as a research feature and benchmark only.

The verified feature/label stack did not uncover a new promotable alpha family from aggTrades-only inputs. The strongest signal in the new discovery pass is regime structure, not directional edge.

## What Was Verified

- Verified six-year catalog and immutable feature/label ledgers are in place.
- Feature and label rebuilds completed on the verified catalog.
- Univariate scan completed on the current feature set.
- Family-level alpha probes and candidate replay completed.
- Explicit cost replay confirms the old edge is fragile under realistic friction.

## Duplicate Scan Status

The final 3.66B-row raw trade-ID duplicate scan remains a validation blocker in this workspace.

That audit is still required to formally close the data-foundation loop, but it is not expected to rescue the rejected alpha.

## Key Evidence

### Explicit Cost Stress

The best verified V8.9/V9.0 policy remains positive only at zero or very low friction. Under realistic taker-style friction it fails hard.

From `results/v90_validation_closure/cost_replay/explicit_cost_replay.json`:

- Best zero-cost policy net expectancy: `0.0009629620866668607`
- Best policy at `10 bps fee + 10 bps slippage` per side:
  - Sharpe: `-9.326549580784938`
  - Profit factor: `0.1085896002144181`
  - Net expectancy: `-0.00303703791333314`

Interpretation:

- The edge is not robust to realistic execution friction.
- Zero-cost positive results do not translate into a tradable strategy.

### Monthly Walk-Forward

The monthly walk-forward protocols reject the old alpha.

Interpretation:

- No stable out-of-sample edge survives walk-forward selection.
- The old signal is not recoverable by simple exit tuning or capital overlays.

### Univariate Scan

The strongest surviving univariate features are regime variables, not the old divergence signal.

Top positive mean-IC features include:

- `realized_vol_50`
- `realized_vol_20`
- `range_pct`
- `hour_utc`

These are useful as context features, not as a promotable standalone alpha.

The old divergence features remain weak:

- `old_divergence_signal` and `old_divergence_score` are near-zero to negative on mean IC.
- Their bucket expectancies are not strong enough to justify live promotion.

### Alpha Family Research

All tested V9.1 candidate families were rejected:

- absorption reversal
- continuation
- regime-conditioned divergence
- MFE classifier

Current replay summary:

- `absorption_long`: reject
- `absorption_short`: reject
- `continuation_long`: reject
- `mfe_classifier`: reject

### Model Baseline

The first-pass model baseline is weak.

- Chronological split was used.
- Logistic regression test accuracy was below 50%.
- Precision and recall were effectively zero for the positive class in the current baseline output.

Interpretation:

- The feature set does not yet support a reliable predictive model for tradable edge.

## Decision

### Retain

- Old CVD-divergence as a research benchmark
- Regime features such as volatility, range, and session context
- Immutable feature and label ledgers
- Explicit cost replay and walk-forward validation machinery

### Shadow Only

- Old divergence signal variants
- Absorption / continuation / MFE candidates from the current aggTrades-only feature set
- Any model baseline that does not survive walk-forward after costs

### Reject

- Old CVD-divergence family as a live strategy
- The current V9.1 alpha families as live candidates

## What This Means

The project has moved from "can the old signal be salvaged?" to "what actually carries predictive information in the verified data?"

Current answer:

- The old signal is not tradable after realistic cost stress.
- The new discovered features mostly identify regime/context rather than a robust standalone alpha.
- More data validation is still needed before any new strategy research can be treated as fully closed.

## Next Step

Close the duplicate-scan audit blocker, then use the verified feature/label foundation to test a new V9.2 hypothesis family instead of continuing to tune the rejected divergence stack.
