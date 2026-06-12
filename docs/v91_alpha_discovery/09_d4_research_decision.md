# V9.1 D4 Research Decision

## Decision

D4 is retained only as a research feature and benchmark.

D4 is not a live strategy candidate under taker execution. No further D4
TP/SL sweeps should be run unless an exact bar-size/horizon surface produces
positive recent post-cost expectancy and then survives chronological
walk-forward validation.

## Verified Signal Purity

The exact verified 300 BTC catalog reproduced a small past-only D4 directional
effect at a five-bar horizon:

- Events: 22,016
- Hit rate: 53.1114%
- Mean signed return: 2.3895 bps
- IC: 0.052391
- Mean-return t-stat: 7.56

This confirms that D4 contains historical predictive structure. It does not
validate the historical 80-93% trade win-rate claims, which were produced by
trade conversion and runner semantics rather than signal purity.

## Cost-Adjusted Failure And Decay

At a realistic 12 bps round-trip taker cost, the five-bar D4 signal has
approximately -9.61 bps expectancy.

The signal also decays materially:

| Period | Events | Hit Rate | Mean Signed Return | IC | Cost-Adjusted Expectancy |
|---|---:|---:|---:|---:|---:|
| 2020-2023 | 19,381 | 53.61% | 2.605 bps | 0.0585 | -9.395 bps |
| 2024-2026 | 2,634 | 49.43% | 0.808 bps | 0.0178 | -11.192 bps |

Recent D4 is statistically weak and not cost-covering.

## Recovered Context Diagnostics

Recovered market-structure, MTF, key-level, and volume-profile concepts were
tested as isolated past-only features. No AI decision or arbitrary confluence
score was used.

The strongest recovered feature was completed-timeframe alignment:

- Full sample: 2,023 events, 56.90% hit rate, 6.447 bps gross expectancy
- 2020-2023: 6.739 bps gross expectancy
- 2024-2026: 0.306 bps gross expectancy across only 92 events
- Full-sample expectancy after 12 bps costs: -5.553 bps

MTF alignment is not deployable because it does not cover taker costs, its
recent effect collapses, and the recent aligned sample is too small.

Other recovered-context conclusions:

- Near-support and near-resistance buckets underperformed no-key-level events.
- Below-POC and below-VAL buckets retained some gross structure but did not
  clear explicit costs.
- OI, funding, liquidation, and whale-flow hypotheses remain untested because
  the verified catalog has no timestamp-aligned derivatives dataset.

## Exit Closure

All tested exits remained negative after 12 bps round-trip costs:

| Exit | Cost-Adjusted Expectancy |
|---|---:|
| Fixed TP/SL | -10.700 bps |
| CVD reversal | -11.382 bps |
| Time exit | -11.111 bps |
| POC/VAH/VAL exit | -10.992 bps |
| Trailing after favorable excursion | -11.631 bps |
| Partial first target plus dynamic remainder | -11.171 bps |

Exit tuning cannot rescue the current D4 signal under realistic taker costs.

## Final Scale Test

The final scale test evaluated:

- Bar sizes: 300, 500, 750, 1000, and 1500 BTC
- Horizons: 5, 10, 15, 24, 36, and 48 bars
- Contexts: none, MTF aligned, MTF against, range, and trend
- Cost ladder: 1, 2, 3, 5, 8, and 12 bps
- Separate 2020-2023 and 2024-2026 results

The 300 BTC catalog is exact. Larger bars are deterministic approximations
rebuilt from canonical 100 BTC caches, so promising larger-bar results require
an exact raw-trade rebuild before they can be trusted.

The only sufficiently populated recent lead with a positive gross bootstrap
interval was:

| Configuration | Recent Events | Recent Gross Mean | Recent Gross 95% CI | Recent Net At 5 bps | Full Gross Mean |
|---|---:|---:|---:|---:|---:|
| Approximate 500 BTC / 10 bars / no context | 1,452 | 6.678 bps | [1.166, 11.849] bps | 1.678 bps | 3.463 bps |
| Approximate 500 BTC / 10 bars / range | 1,185 | 6.999 bps | [1.249, 12.557] bps | 1.999 bps | 3.751 bps |

These configurations do not justify a live candidate:

- They use approximate rebar boundaries.
- Full-history expectancy does not clear 5 bps costs.
- They have not passed monthly walk-forward selection.
- Their post-cost bootstrap confidence interval is not proven positive.

They do satisfy the condition for one limited follow-up: build an exact 500
BTC raw-trade catalog and test the 10-bar horizon under walk-forward. Do not
run another D4 TP/SL sweep before that data-quality check.

## Closure

D4 work is closed as a strategy-development path. Future use is limited to:

- research benchmark;
- weak feature in new alpha families;
- exact 500 BTC / 10-bar validation experiment;
- comparison target for V9.2 features.

Raw outputs:

- `results/v91_parameter_test/verified_signal_purity_lb40_h5.json`
- `results/v91_alpha_discovery/recovered_context/recovered_context_diagnostics.json`
- `results/v91_alpha_discovery/d4_bar_horizon_surface.json`
