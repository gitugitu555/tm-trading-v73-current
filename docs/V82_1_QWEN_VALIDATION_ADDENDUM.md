# V8.2.1 Qwen Validation Addendum

Project: `tm-trading-v73-current`

Status: expansion-phase research and validation blueprint; not an active
implementation target.

Prerequisite: complete the active V7.7 replay, no-lookahead, parity, and
signal-to-trade validation gates before implementing this addendum.

Purpose: incorporate useful review findings around multi-level order-flow
imbalance (MLOFI), VPIN toxicity, and MAE/MFE validation without activating
unproven strategy gates.

## 1. Executive Summary

V8.2.1 narrows the broader future architecture into three concrete research
modules:

1. **MLOFI**: true multi-level order-book pressure diagnostics.
2. **VPIN**: toxicity measurement with comparable construction variants.
3. **MAE/MFE**: a historical trade-path and exit-optimisation laboratory.

The objective is not to add more indicators. It is to make each diagnostic
scientifically valid, comparable across regimes, and measurable in shadow mode
before it can affect strategy logic.

Proposed future progression:

```text
V8.0   = Honest Alpha Lab
V8.1   = Institutional Microstructure Lab
V8.2   = Toxicity, Manipulation, and Execution Research Pipeline
V8.2.1 = Qwen Validation Addendum
V8.3   = Proven Gate Activation and Validation Framework
```

## 2. Core Principle

No V8.2.1 feature may be promoted based on win rate alone.

Every candidate improvement must be evaluated against:

- win rate
- expectancy
- e-ratio
- profit factor
- max drawdown
- trade count
- average R
- MAE/MFE distribution
- walk-forward stability
- Monte Carlo robustness

The primary objective is robust positive expectancy under honest next-bar
replay.

All gates introduced by this addendum must default to passive shadow mode and
must not alter entries, exits, position size, or trade count.

## 3. MLOFI Upgrade Requirements

### 3.1 Problem

A best-bid/best-ask scalar is not true multi-level order-flow imbalance. MLOFI
must preserve the structure of liquidity pressure across multiple book levels.

### 3.2 Required Diagnostic Fields

```text
mlofi_l1
mlofi_l3
mlofi_l5
mlofi_l10
near_book_imbalance
far_book_imbalance
book_agreement_score
book_trap_score
mlofi_raw_vector
mlofi_weighted_aggregate
mlofi_zscore
mlofi_window_mean
mlofi_window_std
```

Fields that cannot be calculated because L2 depth is unavailable must remain
explicitly `None` with a reason code. They must not be approximated silently.

### 3.3 True Multi-Level Vector

Instead of only calculating:

```python
imbalance = (best_bid_size - best_ask_size) / (best_bid_size + best_ask_size)
```

represent the book as:

```python
mlofi_vector = [
    imbalance_level_1,
    imbalance_level_2,
    imbalance_level_3,
    # ...
    imbalance_level_n,
]
```

For each level:

```python
imbalance_i = (bid_size_i - ask_size_i) / max(
    bid_size_i + ask_size_i,
    epsilon,
)
```

### 3.4 Weighted Aggregation

Test these aggregation variants in shadow mode:

- equal weight
- distance-decay weight
- liquidity-adjusted weight
- volatility-adjusted weight
- learned-weight placeholder

An initial distance-decay prototype may use:

```python
weights = [1.00, 0.80, 0.65, 0.50, 0.40]
weighted_mlofi = sum(w * x for w, x in zip(weights, mlofi_vector)) / sum(weights)
```

This must not become a permanent hardcoded policy. Every backtest manifest must
record the aggregation method, levels used, and parameters.

### 3.5 Sliding-Window Normalisation

Raw MLOFI values are not comparable across regimes. Add rolling normalisation:

```python
mlofi_zscore = (mlofi_raw - rolling_mean) / max(rolling_std, epsilon)
```

Initial windows to compare:

- 50 bars
- 100 bars
- 200 bars
- 500 bars

Each run must log:

```text
mlofi_normalization_window
mlofi_aggregation_method
mlofi_levels_used
```

### 3.6 Shadow-Mode MLOFI Gates

Evaluate, but do not activate:

- `mlofi_zscore_extreme_gate`
- `book_agreement_gate`
- `book_trap_avoidance_gate`
- `near_far_book_alignment_gate`
- `mlofi_slope_gate`

Each gate report must include:

```text
evaluable trades
passed trades
failed trades
winners blocked
losers blocked
hypothetical win rate
hypothetical expectancy
trade count retained
```

## 4. VPIN Toxicity Engine Upgrade

### 4.1 Problem

VPIN is a toxicity sensor, not an execution engine. It must not directly emit
buy, sell, reverse, or block actions. Its results are sensitive to construction
method, and static thresholds are brittle.

The repo's current simplified trade-window VPIN must remain clearly labelled
until a volume-bucket implementation is validated.

### 4.2 Construction Variants

Prepare comparable diagnostics for:

- `vpin_time_bin`
- `vpin_volume_bin`
- `vpin_tick_bin`

Compare each variant's ability to predict:

- future volatility
- adverse selection
- bad entries
- stop-outs
- MAE expansion
- drawdown clusters

### 4.3 Required Diagnostic Fields

```text
vpin_method
vpin_level
vpin_fast
vpin_slow
vpin_slope
vpin_fast_minus_slow
vpin_rolling_mean
vpin_rolling_std
vpin_zscore
vpin_session_percentile
toxicity_score
toxicity_state
```

### 4.4 Dynamic Threshold Research

Do not promote hardcoded policy such as:

```python
if vpin > 0.55:
    block_trade()
```

Test rolling alarms:

```python
vpin_alarm = rolling_mean + k * rolling_std
```

Initial `k` values: `1.0`, `1.5`, and `2.0`.

Also compare the 75th, 85th, 90th, and 95th percentiles. Thresholds should be
calibrated and validated by regime, session hour, volatility bucket, and symbol.

### 4.5 Decouple Toxicity From Action

VPIN should output only diagnostic state:

```text
toxicity_score
toxicity_state
confidence
method_used
```

A later strategy or execution layer may independently test responses such as
size reduction, stronger confirmation, entry delay, or shadow blocking.

### 4.6 Toxicity States

Initial states:

```text
BENIGN
RISING_TOXICITY
HIGH_TOXICITY
FALLING_TOXICITY
UNKNOWN
```

An initial hypothesis for shadow testing:

```python
if vpin_zscore >= 2.0 and vpin_slope > 0:
    toxicity_state = "HIGH_TOXICITY"
elif vpin_slope > 0 and vpin_fast > vpin_slow:
    toxicity_state = "RISING_TOXICITY"
elif vpin_slope < 0 and vpin_fast < vpin_slow:
    toxicity_state = "FALLING_TOXICITY"
else:
    toxicity_state = "BENIGN"
```

This is a test hypothesis, not a final threshold policy.

## 5. MAE/MFE Exit Laboratory

### 5.1 Objective

Transform MAE/MFE from a summary report into a historical trade-path database.
Use the strategy's own trade behaviour to research exits without changing
active exit logic.

### 5.2 Required Trade-Path Fields

Every completed trade should export:

```text
trade_id
signal_id
symbol
side
entry_timestamp
exit_timestamp
entry_price
exit_price
intra_trade_high
intra_trade_low
mae
mfe
mae_r
mfe_r
pnl
pnl_r
win
exit_reason
signal_family
regime
session_hour_utc
volatility_bucket
toxicity_state
mlofi_state
microprice_displacement_bps
max_hold_bars
bars_held
failure_bucket
```

### 5.3 Historical Performance Store

Use a queryable format and preserve experiment manifests:

1. JSONL for a simple first version.
2. Parquet for larger research runs.
3. DuckDB or SQLite for local analysis.
4. Postgres/TimescaleDB only when production research requires it.

### 5.4 Percentile-Based Exit Research

Test passive counterfactual rules such as:

- exit if current MAE exceeds the 80th percentile for the signal family
- exit if current MAE exceeds the 85th percentile for the regime
- take partial profit if current MFE exceeds the 70th percentile
- trail after MFE exceeds the 80th percentile and CVD slope weakens

Candidate grids:

```text
MAE percentiles: 70, 75, 80, 85, 90, 95
MFE percentiles: 50, 60, 70, 80, 90
```

Avoid leakage: percentile thresholds must be fitted only on the applicable
training window and evaluated on later data.

### 5.5 Optimisation Objective

Do not optimise percentile exits for win rate alone. Evaluate:

- e-ratio
- expectancy
- profit factor
- drawdown
- average R
- tail-loss reduction
- trade-duration reduction

A higher win rate with worse expectancy must be rejected.

### 5.6 Research Reports

The exit lab should report MAE and MFE by:

- signal family
- regime
- session hour
- volatility bucket
- toxicity state
- MLOFI state

It should also report:

- optimal time stop by signal family
- signal-invalidation exit effectiveness
- partial-exit effectiveness
- trailing-exit effectiveness

## 6. Validation Framework

### 6.1 Required Methods

Before any diagnostic is promoted:

- shadow-mode comparison
- walk-forward validation
- Monte Carlo trade-sequence simulation
- out-of-sample test
- regime split analysis
- session-hour split analysis
- long/short split analysis

### 6.2 Walk-Forward Validation

Compare at least:

```text
train: 6 months
test:  1 month
roll:  1 month

train: 12 months
test:   3 months
roll:   1 month
```

### 6.3 Monte Carlo Robustness

Use at least 1,000 simulations for research and prefer 10,000 for final
promotion. Report:

- median equity curve
- 5th and 95th percentile drawdown
- probability of ruin
- worst 5% expectancy
- trade-count sensitivity

### 6.4 Promotion Criteria

A candidate gate may be promoted only if it improves expectancy, profit factor,
drawdown profile, and loser blocking without unacceptable damage to trade count,
long/short balance, regime coverage, or out-of-sample stability.

Initial promotion criteria for evaluation:

```text
expectancy improvement >= 5%
max drawdown does not worsen
trade count retained > 50%
blocked losers / blocked winners > 1.5
improvement survives walk-forward validation
```

These are candidate governance thresholds, not strategy constants.

## 7. Expansion Implementation Roadmap

### Phase 1: Repository Audit

- Map current implementations in `features/`, `prime/`, `strategy/`,
  `execution/`, `research/`, `scripts/`, and `tests/`.
- Identify existing MLOFI, VPIN/toxicity, and MAE/MFE functionality.
- Identify missing L2 and trade-path data dependencies.
- Do not assume module names or create duplicate feature engines.

### Phase 2: MLOFI Diagnostics

- Implement a true multi-level vector when L2 depth is available.
- Compare weighted aggregation variants.
- Add sliding-window z-score normalisation.
- Add near/far book agreement and book-trap diagnostics.
- Produce shadow-gate reports.

### Phase 3: VPIN Diagnostics

- Compare time-bin, volume-bin, and tick-bin variants.
- Add rolling z-score, slope, fast/slow, and session percentile.
- Emit toxicity score and state without action coupling.

### Phase 4: MAE/MFE Database

- Export complete trade paths.
- Calculate MAE/MFE and R-normalised variants.
- Group by regime, session, signal family, toxicity, and MLOFI.
- Evaluate percentile exits as passive counterfactuals.

### Phase 5: Validation Layer

- Add walk-forward runner scaffolding.
- Add Monte Carlo trade-sequence simulation.
- Add a standard shadow-gate promotion report and checklist.

## 8. Implementation Contract

When this expansion phase becomes active, implementation must:

1. Audit before adding modules.
2. Preserve legacy parity unless diagnostics are explicitly enabled.
3. Keep all new gates and exit rules passive by default.
4. Avoid hardcoding final thresholds.
5. Report missing-data fields explicitly as `None`.
6. Prove diagnostics do not change trade count.
7. Add deterministic unit tests before integration.

Minimum tests:

- MLOFI vector calculation
- MLOFI z-score with short and normal windows
- VPIN variant interfaces
- toxicity-state classification
- MAE/MFE calculation from a synthetic trade path
- percentile-exit diagnostics remain passive
- shadow gates do not alter trade count

Completion reporting must include:

```text
files changed
tests added
tests run
diagnostic fields implemented
fields left as None due to missing data
whether passive diagnostics preserved trade count
```

## 9. Deferred Advanced Trials

These are not V8.2.1 implementation tasks:

- Markov-modulated Hawkes processes for manipulation bursts and self-exciting
  order events
- deep order-book models such as TCN, LSTM, Transformer encoder, or DeepLOB
- reinforcement learning or GRPO for execution
- cross-exchange liquidity-divergence gates
- a learned meta-gate combining MLOFI, VPIN, microprice, and CVD

Do not implement advanced models until deterministic diagnostics, realistic
simulation, leakage controls, labels, and shadow exports are trustworthy.

## 10. Final Decision Rule

The useful additions from the review are:

1. True MLOFI vectorisation and adaptive normalisation.
2. Weighted MLOFI aggregation comparisons.
3. VPIN construction-method comparisons.
4. VPIN toxicity/action decoupling.
5. MAE/MFE historical trade-path storage.
6. Percentile exit research with leakage controls.
7. E-ratio, walk-forward, and Monte Carlo validation.

The governing sequence is:

```text
measure first
shadow-test second
promote only proven gates third
```
