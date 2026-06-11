# V9.0 Alpha Rebuild Decision

## Verified Foundation

The six-year BTCUSDT catalog is now deterministic and reproducible.

- Canonical archives: 132
- Date range: 2020-05-22 to 2026-05-21
- Raw trades: 3,662,935,692
- Volume bars: 509,147
- Immutable signals: 27,979
- Complete 96-bar paths: 27,978
- Catalog hash: `234617593ff6f697e1a584b88b6f8b1b9ee1bd2a8cc2e0b314bb3e8aca4a7233`

The feature ledger and labels are also deterministic:

- Feature rows: 509,147
- Feature hash: `59b64942388d9e0333a0a6857737c10393b6b91452baf0160ea3d8f2631486de`
- Label rows: 509,147

## Explicit Cost Replay

Zero-cost replay over the verified immutable ledger remains positive for the best
V8.9 policy, but explicit taker-cost stress breaks it.

Best V8.9 policy at zero cost:

- Policy: `trail_0.002_0.25`
- Net expectancy: `0.0009629620866668607`
- Profit factor: `1.6186094971980287`
- Sharpe: `2.9571951032569936`
- Sortino: `3.4293029426518546`

At `fee_bps_per_side=10` and `slippage_bps_per_side=10`:

- Net expectancy: `-0.00303703791333314`
- Profit factor: `0.1085896002144181`
- Sharpe: `-9.326549580784938`
- Sortino: `-8.526379795631367`

The break-even drag implied by the zero-cost gross edge is about
`4.8 bps per side` combined fee+slippage, or roughly `9.6 bps round-trip`.

Conclusion: the strategy is not robust to realistic explicit costs.

## Monthly Walk-Forward

Chronological monthly walk-forward rejects the old alpha.

- `6m -> 1m`: median test expectancy `-0.0000945524541909925`, positive split rate `0.4179`
- `12m -> 3m`: median test expectancy `-0.00009203275873930676`, positive split rate `0.4576`
- `24m -> 6m`: median test expectancy `-0.0002271606629930015`, positive split rate `0.3182`

No protocol meets the candidate rule:

- median test expectancy > 0
- test profit factor > 1.05
- positive test split rate > 55%

## Regime Attribution

The bucketed attribution report found no robust buckets.

- Robust buckets meeting the count/profit/stability rule: `0`
- Best bucket by net expectancy is not a promotable regime

The old CVD-divergence signal does not show a clean, stable conditioning edge.

## Predictive Baselines

The first-pass predictive baselines are weak.

- Best feature: `rolling_volatility`
- Accuracy: `0.5114068702455006`
- Precision: `0.5119661290674582`
- Recall: `0.9032342522716772`

This is not sufficient for a promotable alpha and was not walk-forward validated.

## Duplicate Scan Status

The raw-trade duplicate scanner is implemented, checkpointed, and resumable, but the
full 3.66B-row archive scan has not been executed in this turn.

Status:

- Code: complete
- Full scan: pending

This is the only remaining validation blocker that is not fully closed by execution.

## Final Decision

- Old CVD-divergence alpha: reject for production
- Profile and context overlays: shadow-only
- Feature- and label-led rebuild: continue
- Duplicate scan: execute as the next validation job before any new promotion work

## Next Candidate For V9.1

The most plausible next line of inquiry is not more divergence tuning. It is a
regime-conditioned or MFE-predictive family built on the verified feature ledger,
with explicit walk-forward validation and cost stress from the start.

