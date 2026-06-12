# TM Trading Future Roadmap — Source-of-Truth Recovery, V9.2 Alpha Rebuild, and Data-First Research Plan

## 1. Purpose

This document defines the next roadmap for tm-trading after the V9.1 D4/CVD research closeout.

The project has reached an important research inflection point:

- The D4/CVD signal showed real historical predictive information.
- The signal is too weak after realistic taker costs.
- Recent 2024–2026 performance decayed materially.
- Fixed TP/SL optimisation did not rescue the edge.
- Recovered context ideas from older strategy documents are useful, but must be converted into measurable diagnostics.
- Future alpha research is blocked by missing verified historical L2/order-book and derivatives data.

The goal of this roadmap is to prevent further drift by creating a clean source-of-truth process.

## 2. Critical Clarification: Tool Context and Repo Visibility

Different assistants and systems may have different visibility:

- Claude may only see code pasted into its chat.
- Codex may only see files in the repo or files explicitly provided to it.
- ChatGPT may have connector access in some sessions, but Codex does not automatically inherit uploaded documents or chat history.
- Mistral exports, older strategy notes, and uploaded markdown/PDF files must be committed into the repo if Codex needs to use them.

Therefore, the repository must become the only source of truth.

**Required action**

Create a source recovery directory:

`docs/source_recovery/`

Add any external strategy-memory inputs there, including:

- `docs/source_recovery/V92_MISTRAL_STRATEGY_RECOVERY_INPUT.md`
- `docs/source_recovery/V92_CLAUDE_AUDIT_NOTES.md`
- `docs/source_recovery/V92_OLD_STRATEGY_CONCEPTS_INDEX.md`

Every future roadmap or implementation task must reference repo files, not chat memory.

## 3. Immediate Audit Reconciliation

Claude raised three important points that must be reconciled against the actual current repo state.

### 3.1 TP/SL geometry

Claude observed a configuration where:

`stop_pct = 0.003`
`target_pct = 0.006`

This is a 0.30% stop and 0.60% target, giving nominal 2:1 reward.

However, prior audits found possible runner/config drift, including script-level overrides and mismatched defaults in older backtest harnesses.

**Required action**

Create:

`docs/v92_PARAMETER_SOURCE_OF_TRUTH.md`

It must document:

- Every script/backtester that can run D4/CVD strategy logic.
- The exact stop/target defaults for each runner.
- Whether fees/slippage are applied.
- Whether position sizing is applied consistently.
- Whether any scripts hard-code stop/target values.
- Which runner is official for future research.

**Acceptance criterion:**

There must be exactly one official parameter source for each research run.

### 3.2 Sharpe annualisation

Claude correctly identified that per-trade returns should not be annualised with a fixed daily value such as:

`periods_per_year = 365`

unless the observations are actually daily returns.

**Required action**

All performance reporting must separate:

- per-trade expectancy
- per-trade Sharpe-style diagnostic
- calendar-daily Sharpe
- active-day Sharpe
- trade-frequency-adjusted annualisation
- Sortino
- max drawdown
- profit factor
- cost-adjusted expectancy

The official scoreboard must prioritise:

- net expectancy after costs
- calendar-daily Sharpe
- max drawdown
- 2024–2026 out-of-sample behaviour

Do not use per-trade annualised Sharpe as a primary decision metric.

### 3.3 Daily aggregation

If a runner does not construct daily equity, then daily Sharpe claims are invalid for that runner.

**Required action**

All official backtests must emit:

- `equity_curve_by_trade.csv`
- `calendar_daily_equity.csv`
- `daily_returns.csv`
- `trade_log.csv`
- `run_manifest.json`

The `run_manifest.json` must include:

- commit_hash
- branch
- script_name
- config_path
- symbol
- date_range
- bar_type
- bar_size
- fees
- slippage
- entry_lag
- stop_pct
- target_pct
- exit_model
- position_sizing_model
- random_seed_if_any

## 4. Current Strategic Verdict

### D4/CVD status

D4/CVD is not a live strategy candidate under current assumptions.

It remains useful as:

- research feature
- historical benchmark
- input into future meta-labeling
- microstructure signal prototype

It should not be used as:

- standalone entry engine
- live strategy
- fixed TP/SL strategy
- arbitrary confluence-score component

### Revival criteria

D4 can only be revived if future tests show:

- positive 2024–2026 post-cost expectancy
- minimum viable event count
- bootstrap confidence interval excluding zero
- no single-year dependency
- no leakage
- no runner/config drift
- cost stress remains acceptable

## 5. Roadmap Overview

The future roadmap is divided into seven phases.

- Phase 0 — Source-of-truth cleanup
- Phase 1 — Final D4 scale closeout
- Phase 2 — Data foundation / Bybit historical inventory
- Phase 3 — Regime-first contextual diagnostics
- Phase 4 — Dynamic exit research
- Phase 5 — New microstructure alpha families
- Phase 6 — Meta-labeling and alpha permission
- Phase 7 — Paper trading and execution validation

## 6. Phase 0 — Source-of-Truth Cleanup

**Goal**
Remove ambiguity between repo files, pasted code, external assistant outputs, and old strategy documents.

**Deliverables**
- `docs/v92_PARAMETER_SOURCE_OF_TRUTH.md`
- `docs/v92_RESEARCH_RUN_MANIFEST_SPEC.md`
- `docs/source_recovery/V92_MISTRAL_STRATEGY_RECOVERY_INPUT.md`
- `docs/source_recovery/V92_CLAUDE_AUDIT_NOTES.md`
- `docs/v92_STRATEGY_MEMORY_LEDGER.md`

**Required checks**
- Identify all scripts that can run D4/CVD logic.
- Identify official research runner.
- Deprecate or clearly label old/experimental runners.
- Document exact fee/slippage model.
- Document exact bar construction method.
- Document exact entry/exit timing.

**Kill criterion**
No further alpha research should proceed until the official runner and parameter source are documented.

## 7. Phase 1 — Final D4 Scale Closeout

**Goal**
Determine whether D4 failed because the signal is dead or because the tested bar/horizon scale was wrong.

**Experiment**
Run D4 signal-purity surface across:

- bar sizes: 300, 500, 750, 1000, 1500 BTC
- horizons: 5, 10, 15, 24, 36, 48 bars
- filters: none, MTF aligned, MTF against, range regime, trend regime

**Metrics**
For each bucket:
- events
- hit_rate
- mean_signed_return_bps
- median_signed_return_bps
- IC
- t_stat
- bootstrap_95pct_CI
- net_expectancy at 1,2,3,5,8,12 bps costs
- 2020–2023 split
- 2024–2026 split

**Decision**
If no bucket produces positive recent post-cost expectancy, D4 is archived as a research feature only.

## 8. Phase 2 — Data Foundation / Bybit Historical Inventory

**Goal**
Unlock V9.2/V9.3 research by acquiring verified historical microstructure and derivatives data.

**Required datasets**
Priority order:
1. trades
2. L2 order book snapshots/deltas
3. funding rate
4. open interest
5. liquidation events
6. long/short ratio
7. optional whale/large-trade classification

First symbol: BTCUSDT perpetual
Optional second symbol: ETHUSDT perpetual

**Deliverables**
- `docs/v92_DATA_FOUNDATION_PLAN.md`
- `docs/v92_DATA_STATUS.md`
- `scripts/v92_bybit_inventory.py`
- `scripts/v92_download_bybit_sample.py`
- `data/bybit/manifest_schema.md`

**Downloader requirements**
- resumable downloads
- manifest JSONL
- checksums
- file-size validation
- gap detection
- duplicate detection
- timestamp normalization to UTC ns
- symbol normalization
- dry-run mode
- rate-limit/backoff handling
- sample parser validation

**Decision gate**
No L2-dependent alpha research should proceed until inventory is complete, sample downloads validate, schema is stable, gap detection works, and manifest tracking works.

## 9. Phase 3 — Regime-First Contextual Diagnostics

**Goal**
Recover older strategy concepts as measurable context filters, not arbitrary scorecards.

**Features to test**
- ADX regime
- ATR regime
- ADR / daily range exhaustion
- RSI macro exhaustion
- session quality
- VWAP / anchored VWAP
- VWAP standard deviation bands
- volume profile / POC / VAH / VAL
- market structure
- distance to lagged swing high/low
- MTF alignment

**Important rule**
Traditional indicators must not be primary entries. They are only context filters, regime classifiers, trade eligibility features, exit modifiers, and position sizing modifiers.

**Leakage rules**
- No centered rolling windows without confirmation delay.
- No future-confirmed swing used at the pivot bar.
- Higher-timeframe indicators must use completed candles only.
- ADR must use previous completed daily ranges only.
- All features must be prefix-stable.

**Deliverables**
- `features/contextual_filters.py`
- `features/market_structure.py`
- `scripts/v92_contextual_filter_diagnostics.py`
- `docs/v92_CONTEXTUAL_FILTER_DIAGNOSTICS.md`
- `results/v92_contextual_filters/contextual_filter_diagnostics.json`

**Metrics**
For every context bucket:
- events, hit_rate, mean_return_bps, median_return_bps, IC, t_stat, bootstrap_CI, net_expectancy at multiple costs, median_duration_bars, median_MFE_bps, median_MAE_bps, 2020–2023 split, 2024–2026 split.

## 10. Phase 4 — Dynamic Exit Research

**Goal**
Test whether the old strategy’s dynamic-exit concept improves D4 or future microstructure signals compared with fixed TP/SL.

**Priority order**
1. CVD reversal exit
2. POC / VAH / VAL exit
3. time stop
4. ATR trailing stop
5. partial exit + dynamic remainder

**Exit definitions**
*(See detailed specs in document for CVD reversal, POC/VAH/VAL, Time stop, ATR trailing stop, Partial + dynamic remainder)*

**Deliverables**
- `exits/dynamic_exits.py`
- `scripts/v92_dynamic_exit_research.py`
- `docs/v92_DYNAMIC_EXIT_RESEARCH.md`
- `results/v92_dynamic_exits/dynamic_exit_research.json`

**Required comparison**
Each dynamic exit must be compared against fixed TP/SL baseline, no-exit horizon return, bar-exit baseline, and profile-exit baseline if available.

**Metrics**
- events, win_rate, mean_net_return_bps, median_net_return_bps, profit_factor, max_drawdown, median_duration_bars, median_MFE_bps, median_MAE_bps, MFE_capture_ratio, MAE_avoidance_ratio, slippage_estimate_bps, exit_reason_counts, 2020–2023 split, 2024–2026 split.

## 11. Phase 5 — New Microstructure Alpha Families

**Goal**
Move beyond D4 into larger, more executable alpha primitives.

**Candidate families**
- OFI / order-flow imbalance
- microprice imbalance
- absorption
- iceberg/replenishment detection
- VPIN / toxicity regime
- liquidation cascade continuation/reversal
- funding + OI squeeze
- volume profile auction state
- VWAP mean reversion / acceptance
- maker-first execution alpha

**Data dependency**
Most of this phase is blocked until Phase 2 data foundation is complete.

**Rule**
Do not implement these as live strategies first. Implement as diagnostics (event detector, label builder, purity test, cost-adjusted expectancy report, recent-period split).

## 12. Phase 6 — Meta-Labeling and Alpha Permission

**Goal**
Convert D4 and future signals from direct entry systems into features inside a trade eligibility model.

**Inputs**
- D4/CVD feature, MTF alignment, ADX/ATR/ADR regime, VWAP state, volume profile state, session state, spread/depth/slippage state, funding/OI/liquidation state, recent toxicity, recent volatility.

**Labels**
Use cost-aware labels such as reached positive MFE before MAE, net profitable after costs, maker fill feasible, hit dynamic exit profitably, survived slippage stress.

**Validation**
- purged walk-forward, embargoed splits, 2024–2026 out-of-sample priority, feature attribution, calibration curve, precision/recall by trade eligibility bucket.

**Rule**
No AI trade decisions. AI/LLM tools may only be used for documentation, research summaries, code review, experiment planning.

## 13. Phase 7 — Paper Trading and Execution Validation

**Goal**
Only after historical research proves recent post-cost expectancy, validate live execution assumptions.

**Components**
- Nautilus adapter, paper-trading harness, maker/taker execution model, queue-aware passive order simulation, spread/slippage/TCA logging, kill switch, position limits, drawdown limits, latency logging, order reject logging.

**Live readiness criteria**
- positive paper-trading expectancy, execution slippage within model, no unexplained order-state bugs, daily loss limits validated, kill switch tested, no data-feed gaps during trading window.

## 14. Global Research Rules

These rules apply to every future phase.

**No leakage**
- no future bars, no same-bar entry after signal calculation, no centered rolling windows without delayed confirmation, no future swing confirmation at pivot timestamp, higher timeframe features must use completed candles only.

**No arbitrary scorecards**
- Do not implement: 90/100 confluence score, AI confidence score as trading rule, manual point weighting, unvalidated indicator stacking.

**Always report costs**
- Every result must include gross expectancy, net expectancy at 1,2,3,5,8,12 bps, fee assumptions, slippage assumptions, maker/taker assumption.

**Always split time periods**
- Every result must report full sample, 2020–2023, 2024–2026, year-by-year.

**Always log run provenance**
- Every official run must include commit hash, branch, script, config, date range, symbol, bar size, cost model, exit model, position sizing, data manifest hash.

## 15. Immediate Next Codex Tasks

**Task 1 — Source-of-truth cleanup**
Create:
- `docs/v92_PARAMETER_SOURCE_OF_TRUTH.md`
- `docs/v92_RESEARCH_RUN_MANIFEST_SPEC.md`
- `docs/source_recovery/V92_CLAUDE_AUDIT_NOTES.md`

**Task 2 — Final D4 bar/horizon surface**
Create:
- `scripts/v91_d4_bar_horizon_surface.py`
- `docs/v91_alpha_discovery/09_d4_scale_closeout.md`

**Task 3 — Bybit inventory**
Create:
- `scripts/v92_bybit_inventory.py`
- `scripts/v92_download_bybit_sample.py`
- `docs/v92_DATA_FOUNDATION_PLAN.md`
- `docs/v92_DATA_STATUS.md`

**Task 4 — Contextual filters**
Create:
- `features/market_structure.py`
- `features/contextual_filters.py`
- `scripts/v92_contextual_filter_diagnostics.py`

**Task 5 — Dynamic exits**
Create:
- `exits/dynamic_exits.py`
- `scripts/v92_dynamic_exit_research.py`
- `docs/v92_DYNAMIC_EXIT_RESEARCH.md`

## 16. Final Roadmap Verdict

The project should not continue as a TP/SL optimisation project.

The future path is:
source-of-truth cleanup → final D4 scale test → data foundation → regime-first diagnostics → dynamic exit research → new microstructure alpha → meta-labeling → paper execution

The main lesson is:
- The signal is not the strategy.
- The strategy is signal + regime + execution + exit + cost feasibility.

D4 taught us that a statistically real signal can still be economically useless if it is too small, too stale, or executed at the wrong cost structure.

The next phase must focus on recoverable architecture, verified data, leakage-safe diagnostics, and recent post-cost expectancy.
