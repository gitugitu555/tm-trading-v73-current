# V8.4 - Strategy, Implementations, Recovered Tools & Rules

## Purpose

V8.4 is the master design document for the TM-Trading stack.

It unifies:

- the current alpha engine
- the V8 diagnostic and validation layers
- the most useful legacy auction-market and risk rules
- the strongest additions from the microstructure and execution literature

The design goal is not to replace the current core with a generic indicator stack. The goal is to keep the present alpha engine as the primary trigger and add a disciplined set of context, toxicity, execution, exit, and promotion layers around it.

## Executive Summary

V8.4 should formalize a layered system where each module has one job.

- Volume-bar CVD divergence remains the primary alpha trigger.
- Market Profile and auction context provide location.
- ATR and realized volatility provide range expectation and exhaustion.
- MLOFI, GOFI, queue imbalance, and microprice provide short-horizon pressure context.
- VPIN and related toxicity measures provide adverse-selection context.
- DOM timing and execution realism provide fill-quality and slippage context.
- MAE/MFE analysis provides exit calibration.
- Risk-state orchestration controls exposure, pacing, and kill states.
- Validation prevents false edges from being promoted.

The governing rule is:

**Alpha first, context second, shadow-test third, promote only after evidence.**

That principle matches the legacy project philosophy and the empirical microstructure literature. Short-horizon signals degrade quickly if execution realism, transient quotes, regime shifts, and validation bias are ignored.

## Current System Inventory

The project is best described as a versioned stack rather than a monolith.

| Version | Role in stack | Main content | Status in V8.4 |
|---|---|---|---|
| V7.3 | Baseline alpha engine | Volume-bar CVD divergence, lookback / exit sweep logic, dynamic target scaling, baseline stop model, cached backtesting | Keep as alpha core |
| V8.0 | Honest Alpha Lab | No-lookahead replay, lagged-entry verification, passive diagnostics, failure export, shadow gates | Mandatory foundation |
| V8.1 | Institutional Microstructure Lab | Execution illusion tax, microprice drift, visible-depth normalization, MAE/MFE framing, richer L2 diagnostics | Absorb into V8.4 |
| V8.2 | Toxicity / Manipulation / Execution | Toxicity engine, manipulation-risk diagnostics, execution realism, MAE/MFE exit lab | Absorb into V8.4 |
| V8.2.1 | Qwen validation addendum | True MLOFI vectorization, sliding z-score normalization, weighted aggregation, VPIN binning variants, trade-path DB, percentile exits | Absorb into V8.4 |
| V8.3 | Promotion layer | Proven-gate activation, walk-forward / Monte Carlo validation, regime-specific permissions | Formalize inside V8.4 |

## Role Separation

V8.4 should make the jobs explicit.

| Layer | Single job |
|---|---|
| CVD / delta engine | Primary alpha trigger |
| Market Profile / auction context | Location and structural context |
| ATR / realized volatility | Range expectation and exhaustion |
| MLOFI / GOFI / queue imbalance | Pressure and short-horizon directional context |
| VPIN / toxicity | Adverse selection and do-not-touch state |
| DOM timing / execution realism | Timing, slippage, and fill quality |
| MAE/MFE exit lab | Exit calibration and stop / target learning |
| Risk-state orchestrator | Session, streak, exposure, and kill-state control |
| Validation layer | Prevent promotion of false edges |

## System Flow

```text
Trades + L2/L3 book + OHLCV + venue metadata
  -> barizer and event clock
  -> CVD and divergence core
  -> MLOFI / GOFI / queue imbalance
  -> VPIN / toxicity
  -> Market Profile / ATR / trend stack / session quality
  -> DOM timing / execution realism
  -> signal proposal
  -> shadow gates
  -> baseline trade path
  -> counterfactual gate outcomes
  -> trade-path database
  -> MAE/MFE exit lab
  -> walk-forward / Monte Carlo / CPCV / DSR
  -> promotion board
```

## Backtest Snapshot

The most recent backtest figures in the current owner notes should be treated as reported engineering results, not final research claims.

### Reported six-year dynamic sweep

The reported sweep covered:

- `base_target_pct` in `{0.3%, 0.4%, 0.5%, 0.6%}`
- `exit_after_volume_bars` in `{10, 16, 20, 24}`
- `lookback_bars` in `{30, 40, 50, 60}`
- dynamic target scaling enabled
- `stop` at `3%`
- no advanced gates
- no time-exit overlay

| Config label | Base target | Exit bars | Lookback | Reported WR | Reported PnL | Reported Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Fixed baseline | 0.4% | 16 | 40 | 60.99% | $5,359 | 2.596 |
| V2 optimized | 0.4% | 16 | 40 | 72.04% | $3,777 | 2.215 |
| High WR | 0.3% | 24 | 30 | 81.89% | $4,041 | 1.930 |
| Balanced | 0.5% | 24 | 30 | 72.62% | $7,222 | 2.938 |
| High PnL | 0.6% | 24 | 30 | 68.87% | $7,654 | 2.970 |

### Engineering conclusions

1. `lookback ~= 30` and `exit_after_volume_bars ~= 24` appears to be a real structural sweet spot under the current replay assumptions.
2. The highest win-rate setting is not automatically the best production candidate if Sharpe, expectancy, fees, or trade efficiency deteriorate.
3. The balanced and high-PnL variants deserve honest reruns under lagged execution, fill realism, and multiple-testing correction.

### Compounding test

A second reported run used:

- starting equity: `$500`
- `base_position_pct = 50%`
- `base_target_pct = 0.5%`
- `lookback = 30`
- `exit_after_volume_bars = 24`
- `stop = 3%`
- dynamic scaling enabled

Reported results:

| Metric | Reported value |
|---|---:|
| Starting equity | $500 |
| Ending equity | $15,808.70 |
| Total return | +3,061% |
| Win rate | 72.62% |
| Trades | 8,659 |
| Targets hit | 5,469 |
| Stops hit | 78 |
| Volume-bar exits | 3,112 |
| Sharpe | 2.9383 |
| DSR | 1.0000 |

The correct interpretation is not that the system is already production-ready at that compounding level. The correct interpretation is that the current alpha engine may have found a promising parameter manifold, but that manifold must still pass honest replay, fill-quality modeling, and trial-mining correction.

## Recovered Legacy Tools And Rules

The most valuable legacy concepts should be brought back in automated form, not as discretionary clutter.

### Strong recoveries

| Recovered idea | Why it matters | V8.4 role |
|---|---|---|
| Market Profile and auction context | Location matters; a divergence at value extreme is not the same as a divergence in the middle of value | Context layer |
| ATR-used exhaustion | Prevents fresh continuation trades after most of the expected range has been spent | Shadow gate |
| DOM timing | Execution should be timed, not guessed | Execution layer |
| Risk-state orchestration | Stops clusters of correlated losses from compounding | Live risk layer |
| Anti-pattern detection | Explicitly detect known failure modes instead of assuming every trade is independent | Shadow gate |
| Session quality tiers | Trading quality changes by session and liquidity regime | Context / gate layer |
| Trend-stack context | Useful as regime context, not as the main signal | Context layer |
| Track A / B / C framework | Enables counterfactual evaluation without live interference | Validation layer |

### Weak or outdated ideas to exclude from the live stack

- manual human-in-the-loop execution
- n8n-centric orchestration
- direct obsession with 90%+ win rate
- undocumented discretionary overrides

## Literature-Driven Additions

The final literature pass supports a few additions that were missing or underweighted.

### Additions to MLOFI

MLOFI should not stop at simple multi-level imbalance.

It should also test:

- depth-aware scaling
- generalized or stationarized OFI variants
- filtered order-book imbalance that removes very short-lived quotes
- queue imbalance features
- microprice drift

### Additions to validation

The validation stack should explicitly account for:

- selection bias
- serial correlation in Sharpe
- multiple-testing inflation
- purged / embargoed validation when label overlap exists
- trade-retention accounting
- blocked-loser versus blocked-winner accounting

### Additions to execution diagnostics

The execution stack should log:

- spread recovery after shocks
- depth recovery after shocks
- wall lifetime and wall churn
- cancel-to-add ratios
- queue state and queue penalties
- expected slippage and effective entry price

## V8.4 Architecture

V8.4 should formalize six live-capable layers and two research-only layers.

| Layer | Function | Default mode |
|---|---|---|
| Alpha core | Volume-bar CVD divergence and dynamic target baseline | Live baseline |
| Context | Market Profile, ATR exhaustion, trend stack, session quality | Shadow by default |
| Pressure | MLOFI, GOFI, queue imbalance, microprice drift | Shadow by default |
| Toxicity | VPIN, transient-book filters, manipulation risk, resiliency | Shadow by default |
| Execution | DOM timing, spread/depth quality, fill realism | Live realism overlay, shadow filters |
| Risk state | Streaks, drawdown, exposure, pacing, kill state | Live control layer |
| Exit research | MAE/MFE percentile exits, profile targets, ATR exits | Shadow by default |
| Validation | Walk-forward, Monte Carlo, DSR, promotion report | Mandatory gate |

## Mathematical Core

### CVD and divergence

Let `s_i` be signed aggressive side and `v_i` be trade size inside volume bar `t`.

`Delta_t = sum(s_i * v_i)`

`CVD_t = sum_{j <= t} Delta_j`

Minimal long-divergence candidate:

`LongDiv_t = 1(P_t <= min(P_u for u in [t-L, t])) * 1(CVD_t > min(CVD_u for u in [t-L, t]) + delta_cvd)`

The symmetric short version should be used for bearish candidates.

### Dynamic target scaling

`target_bps_t = base_target_bps * (1 + beta * signal_strength_t)`

Clamp the result to a configured floor and ceiling.

### Queue imbalance and MLOFI

At level `i`:

`QI_i = (B_i - A_i) / (B_i + A_i + epsilon)`

The weighted MLOFI aggregate is:

`MLOFI_w_t = sum(w_i * z_W(QI_i,t)) / sum(w_i)`

with exponential decay weights:

`w_i = exp(-lambda * (i - 1))`

Depth-scaled variant:

`MLOFI_d_t = MLOFI_w_t / (D_topK_t + epsilon)`

where:

`D_topK_t = sum(B_i,t + A_i,t for i in 1..K)`

### Microprice

`microprice_t = (ask_t * q_bid_t + bid_t * q_ask_t) / (q_ask_t + q_bid_t)`

`microprice_drift_bps_t = 1e4 * (microprice_t - mid_t) / mid_t`

### VPIN

The platform should support time bins, fixed-volume bins, and fixed-tick bins.

For bucket `j`:

`VPIN_t = (1 / n) * sum(abs(V_j^B - V_j^S) / V_star for j in t-n+1..t)`

Toxicity states should be logged, not used as a direct trigger unless explicitly promoted.

### ATR and exhaustion

`TR_t = max(H_t - L_t, abs(H_t - C_{t-1}), abs(L_t - C_{t-1}))`

`ATR_t = ((n - 1) * ATR_{t-1} + TR_t) / n`

`atr_used_pct_t = 100 * session_range_t / (ATR_t + epsilon)`

`range_remaining_t = ATR_t - session_range_t`

### Market Profile

Let `V(p)` be the volume histogram on price buckets.

`POC = argmax_p V(p)`

Value area expands from POC until cumulative volume reaches the configured share, typically 70%.

### DOM timing

`spread_bps_t = 1e4 * (ask_t - bid_t) / ((ask_t + bid_t) / 2)`

`depth_imbalance_topK_t = (sum(B_i,t) - sum(A_i,t)) / (sum(B_i,t) + sum(A_i,t) + epsilon)`

### MAE and MFE

For a long trade with entry `P_0`, stop distance `R_0`, and path prices `P_s`:

`MAE_R = max(0, (P_0 - min(P_s)) / R_0)`

`MFE_R = max(0, (max(P_s) - P_0) / R_0)`

Percentile-based stops and targets should be learned on the same conditional cohort used for the trade-path database.

### Position sizing

`Q_t = min(Q_max, (rho * E_t) / (k_stop * ATR_t * PV))`

This keeps the risk layer orthogonal to the signal layer.

## Parameter Grids

V8.4 should freeze a documented research grid.

| Module | Parameters to test | Initial grid |
|---|---|---|
| CVD core | lookback bars | 20, 30, 40, 50, 60 |
| CVD core | exit-after-volume-bars | 16, 20, 24, 32 |
| CVD core | base target pct | 0.30, 0.40, 0.50, 0.60, 0.75 |
| Stop models | fixed stop pct | 2.0, 2.5, 3.0, 4.0 |
| Stop models | ATR stop multiple | 1.0, 1.5, 2.0, 2.5 |
| MLOFI | levels | 1, 3, 5, 10 |
| MLOFI | z-score window | 50, 100, 200, 500 |
| MLOFI | weighting lambda | 0.00, 0.15, 0.30, 0.50 |
| MLOFI | filtered order lifetime ms | 50, 100, 250, 500 |
| VPIN | bin type | time, volume, tick |
| VPIN | rolling window | 20, 50, 100 bins |
| VPIN | z-threshold | 1.0, 1.5, 2.0, 2.5 |
| ATR context | ATR period | 14, 20, 30 |
| ATR context | exhaustion threshold | 70%, 75%, 80%, 85% |
| Profile | value-area share | 68%, 70%, 75% |
| Profile | price bucket size | 1x, 2x, 5x minimum tick |
| DOM | top-K depth | 5, 10, 20 |
| DOM | wall-z threshold | 2, 3, 4 standard deviations |
| MAE/MFE | MAE stop percentile | 75, 80, 85, 90, 95 |
| MAE/MFE | MFE profit percentile | 50, 60, 70, 80, 90 |

## Data Contracts

Minimum required lanes:

| Data lane | Minimum requirement | Preferred requirement |
|---|---|---|
| Trades | tick prints with side and size | tick prints with aggressor side, venue, and trade ID |
| Book | L1 best bid/ask | L2-L10 snapshots or event stream with queue updates |
| Bars | volume bars and OHLCV | volume bars plus event-aligned snapshots |
| Context | ATR inputs and session metadata | full profile histogram inputs and cross-venue alignment |
| Execution | fill timestamps and prices | order lifecycle, queue position proxy, slippage audit |
| Validation | trade returns series | full trial return matrix across all sweeps |

## Suggested Python File Layout

| Path | Action | Purpose |
|---|---|---|
| `docs/V8_4_STRATEGY_IMPLEMENTATION.md` | create | master document |
| `schema/market_state.py` | create | canonical dataclasses or pydantic models |
| `features/cvd_core.py` | modify | baseline alpha definitions |
| `features/mlofi.py` | create or modify | vectorized MLOFI, GOFI, filtered imbalance |
| `features/queue_imbalance.py` | create | top-of-book and top-K queue imbalance |
| `features/toxicity.py` | create or modify | VPIN variants and toxicity states |
| `features/market_profile.py` | create | POC / VAH / VAL / LVN / profile type |
| `features/atr_context.py` | create | ATR, ATR-used, percentile, trend-stack context |
| `features/anti_patterns.py` | create | forbidden-pattern diagnostics |
| `execution/dom_timing.py` | create | spread, depth, wall, resiliency |
| `execution/realism.py` | create or modify | lagged fills, slippage, execution illusion tax |
| `risk/risk_state.py` | create | drawdown, streak, exposure, pacing layer |
| `research/trade_path_db.py` | create | path-level trade export |
| `research/mae_mfe_exit_lab.py` | create or modify | percentile exits, trade-path research |
| `research/profile_exit_lab.py` | create | profile-based targets and exits |
| `research/validation.py` | create or modify | walk-forward, Monte Carlo, promotion report |
| `research/cpcv.py` | create | purge / embargo validation helper |
| `tests/` | expand | deterministic module and parity tests |

## API Contracts

```python
@dataclass
class BookSnapshot:
    ts_ns: int
    symbol: str
    venue: str
    bid_px: list[float]
    bid_sz: list[float]
    ask_px: list[float]
    ask_sz: list[float]


@dataclass
class MarketStateFrame:
    ts_ns: int
    symbol: str
    side_candidate: str | None
    cvd: float
    cvd_divergence_score: float
    microprice_drift_bps: float | None
    mlofi_w: float | None
    mlofi_depth_scaled: float | None
    queue_imbalance_top5: float | None
    vpin_score: float | None
    toxicity_state: str | None
    atr_used_pct: float | None
    profile_context: str | None
    distance_to_poc_bps: float | None
    dom_entry_quality: float | None
    risk_state: str


@dataclass
class ShadowGateResult:
    gate_id: str
    passed: bool
    score: float | None
    reason: str | None
    would_block: bool
```

## Shadow Gate Rules

Every non-baseline module in V8.4 should behave as a shadow gate unless explicitly promoted.

| Rule | Requirement |
|---|---|
| No silent interference | A shadow gate must never change trade count in default mode |
| Full counterfactual logging | It must report whether it would have blocked a winner or loser |
| Group-aware attribution | Results must be grouped by symbol, regime, side, session hour, and signal family |
| Promotion isolation | A gate can only be turned live after standalone and combined validation |

## Validation And Promotion

Validation should be a formal promotion pipeline, not an informal backtest check.

Minimum stack:

- lagged-entry honest replay
- walk-forward optimization
- Monte Carlo trade-order simulation
- multiple-testing adjustment using DSR
- purged / embargoed validation where label overlap exists
- trade-retention and blocked-loser / blocked-winner accounting

### Suggested promotion thresholds

| Metric | Provisional promotion | Production promotion |
|---|---|---|
| Expectancy uplift | +3% | +5% |
| Max drawdown | not worse | improved or unchanged |
| Trade retention | >= 60% | >= 50% with clear benefit |
| Blocked losers / blocked winners | > 1.25 | > 1.50 |
| Walk-forward stability | positive in majority of windows | positive in large majority of windows |
| Monte Carlo robustness | median positive, no ruin | strong 5th percentile behavior |
| DSR | > 0.80 | > 0.95 |
| Lagged execution parity | acceptable degradation | fully documented and accepted |

### Walk-forward template

| Train window | Test window | Use case |
|---|---|---|
| 6 months | 1 month | responsive tuning |
| 12 months | 3 months | stability check |
| 24 months | 3 to 6 months | long-regime robustness |

Monte Carlo should randomize:

- trade order
- execution slippage shock
- a configurable fraction of missed fills

## Track A / B / C

The old Track A / Track B idea should be reintroduced in an automated form.

| Track | Meaning in V8.4 |
|---|---|
| Track A | baseline mechanical strategy |
| Track B | promoted-gate strategy |
| Track C | shadow-gate counterfactuals |
| Track H | optional human audit log, not part of live execution |

## Roadmap

```text
V8.4 unified strategy and research document
V8.4 implementation sprint
V8.5 proven-gate activation and vol sizing
V8.6 cross-venue and cross-impact context
V9 realistic simulator and queue-reactive TCA
V10+ RL execution and deep LOB research
```

## Future Improvements And Wild Trials

These ideas should be preserved but kept outside the default live scope.

| Idea | Why preserve it | Why not activate yet |
|---|---|---|
| GRPO / RL execution agent | Could optimize slicing and timing in realistic simulators | Needs trustworthy simulator, queue model, and reward design |
| MMHP / queue-reactive Hawkes | Strong candidate for manipulation burst and state-dependent flow modeling | Heavy calibration burden; better after diagnostics stabilize |
| DeepLOB / deep LOB encoders | Strong research path for universal microstructure features | Forecast accuracy does not guarantee actionable alpha |
| Cross-venue liquidity divergence | Likely valuable in crypto lead-lag and spoof detection | Requires synchronized venue clocks and multi-venue L2 |
| Queue-reactive simulator | Excellent for future execution and RL work | Separate build effort, not a first-pass strategy rule |
| Hidden liquidity / iceberg inference | Useful for DOM timing and trap avoidance | Needs richer event data and careful false-positive control |
| Purged CPCV and PBO dashboards | Strong defense against optimization bias | More compute and bookkeeping, but worth adding |

## Commit-Ready Sequence

1. Rerun the balanced and high-PnL baselines under honest lagged replay.
2. Add the trade-path database and export every completed trade path before changing exits.
3. Implement Market Profile, ATR context, MLOFI / queue imbalance, and VPIN as passive modules.
4. Add risk-state orchestration and anti-pattern logging.
5. Bring in walk-forward, Monte Carlo, and DSR accounting before promoting any new gate.
6. Only then test live activation of the strongest one or two gates.

## Final Rule

No new signal, gate, exit, or sizing rule becomes live unless it is honest under lagged execution, survives effective-entry costs, improves expectancy out of sample, and is explained well enough to be debugged.
