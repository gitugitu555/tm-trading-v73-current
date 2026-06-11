# Repository Audit and Test Plan

## Executive Summary

I audited the public `gitugitu555/tm-trading-v73-current` repository as rendered on GitHub on `2026-06-11`.

The repository default branch is `master`, not `main`. The files relevant to this audit live under `prime/`, `scripts/`, `docs/`, `results/`, and `tests/`.

Core files inspected:

- `prime/configs.py`
- `prime/chunk_b_backtest.py`
- `prime/performance.py`
- `scripts/chunk_b_backtest_cached.py`
- `scripts/v73_backtest_6y_incremental.py`
- `results/v84_6y_sweep_results.json`
- `results/v85_grand_sweep_6y.json`
- the v7.3/v8.4/v8.5 session and programme documentation

## Main Findings

The diagnosis is directionally useful, but not exact at HEAD.

The repository does show a real signal-to-trade conversion mismatch, and it annualizes per-trade Sharpe as though returns were daily. That is a real statistical bug.

However, the "inverted TP/SL defaults" problem is not a single repo-wide truth:

- `prime/configs.py` still carries the Stage 2-style `0.45%` stop / `0.25%` target skew.
- `prime/chunk_b_backtest.py` itself defaults to the opposite and much healthier `0.30%` stop / `0.60%` target.
- The active six-year v7.3 runner in `scripts/v73_backtest_6y_incremental.py` overrides everything to a much wider `3.00%` stop / `0.40%` target.

The bigger problem at HEAD is not one bad default. It is configuration drift across docs, library code, and runner scripts.

## Fee and Execution Model

The backtest path applies `5 bps` per side in fees and `1 bp` per side in slippage.

In the cached backtester:

- entry prices are slipped
- exit prices are slipped
- PnL is reduced by `fee_bps_per_side * 2 / 10_000`

On that basis, the fee-only break-even win rate for the Stage 2-style `0.25%` target / `0.45%` stop is about `78.6%`.

The current six-year runner default of `0.40%` target / `3.00%` stop needs about `91.2%` win rate on a pure TP/SL basis before fees are covered.

## Sharpe and Daily Accounting

The most important correction is this:

`daily_equity` in `prime/chunk_b_backtest.py` is not primarily wrong because it overwrites same-day trades.

Because `running_equity` is cumulative, the last write for a day is effectively that day's close-equity, which is acceptable for end-of-day accounting.

The real defect is that the code builds a daily series only for days on which trades occurred. Zero-trade days are omitted. The resulting `daily_sharpe_ratio()` is therefore not a true calendar-daily Sharpe.

That mis-specification can materially bias daily Sharpe, and for sparse strategies it is more likely to inflate than depress it.

## Priority Fixes

1. Unify the repo's risk/reward defaults so reward exceeds risk everywhere.
2. Stop the six-year runner from overriding to `stop_pct=0.03` and `target_pct=0.004`.
3. Annualize Sharpe and DSR using actual trades per year when feeding per-trade return series.
4. Rebuild daily returns as a calendar-daily series with explicit zero-return carry days.

Those changes are enough to turn this from a confusing mix of incomparable experiments into a statistically coherent backtest surface.

## What The Repo Actually Does

The repo README frames the fork as an attempt to align Chunk B backtests with a measured volume-bar CVD edge of roughly `53%` signal hit rate, instead of the legacy momentum path that was showing about `17%` trade win rate on six-year runs.

The v7.3 programme document is more explicit. It describes a six-year momentum backtest around `17.5%` trade win rate, versus a measured volume-bar CVD signal-only hit rate of about `53.3%` using `300 BTC` bars, `40-bar` lookback, `D4` HTF filter, and a `5-bar` horizon.

A later session log updates that picture with a stage-3 example showing `54.5%` signal hit rate versus `34.1%` trade win rate in 2022-09.

That confirms the repo really does distinguish signal hit rate from trade-exit win rate, and the conversion layer remains central to the problem.

## Configuration Drift Snapshot

The active code path is not driven by `prime/configs.py`.

The cached backtest runner imports `ChunkBBacktestConfig` from `prime.chunk_b_backtest`, not from `prime.configs`, and the six-year v7.3 runner shells out directly to `scripts/chunk_b_backtest_cached.py`, passing explicit CLI overrides for stop, target, exit horizon, and signal mode.

That matters because the stale values in `prime/configs.py` do exist, but they are not the live defaults used by the current six-year runner.

Unit conventions are decimal returns:

- `0.0045` means `0.45%`
- `0.006` means `0.60%`
- `0.03` means `3.00%`

## Current Runner Surface

Location or run path | Stop | Target | Reward-to-risk | Fee-only break-even win rate | What it affects
---|---:|---:|---:|---:|---
`prime/configs.py` | `0.45%` | `0.25%` | `0.56` | `78.6%` | Stale config module; Stage 2 conversion skew
`prime/chunk_b_backtest.py` default config | `0.30%` | `0.60%` | `2.00` | `44.4%` | Typed library backtester default
`scripts/chunk_b_backtest_cached.py` CLI default | `0.30%` | `0.60%` | `2.00` | `44.4%` | Direct cached backtester default
`scripts/v73_backtest_6y_incremental.py` default | `3.00%` | `0.40%` | `0.13` | `91.2%` | Current six-year v7.3 runner default
`v85_risk_only` committed run | `3.00%` | `0.50%` | `0.17` | `88.6%` | Committed v8.5 result in `results/v85_grand_sweep_6y.json`

## Rechecked Diagnosis

The first part of the diagnosis - that an inverted risk/reward conversion harmed the strategy - is partly true, but overstated as a single root cause.

It is true that the v7.3 programme document still memorializes Stage 2 as "stop 0.45%, target 0.25%", and `prime/configs.py` still carries the same skew.

But the typed backtester default in `prime/chunk_b_backtest.py` is the opposite, with `0.30%` stop and `0.60%` target, and the active six-year v7.3 runner at HEAD overrides to a much wider `3.00%` stop and `0.40%` target.

So the real issue is not simply "the repo default is inverted". It is that different components encode incompatible trade conversion assumptions.

It is also too strong to say the negative v8.5 results are explained primarily by the TP/SL ratio alone.

The `v85_risk_only` run reports:

- `4,526` trades
- `80.31%` win rate
- Sharpe `-1.6051`
- ending equity `479.93`
- exit mix dominated by `TARGET`, `PROFILE_POC_RECLAIMED`, `PROFILE_VAL_BREAK`, `BAR_EXIT`, `PROFILE_VAH_BREAK`, `PROFILE_HARD_STOP`, and `STOP`

That means only a minority of trades are literal stop exits, and the majority are being resolved by profile/bar logic.

## Sharpe Annualization Bug

This is fully confirmed.

In `prime/chunk_b_backtest.py`, the report is built from `returns = [trade.return_pct for trade in trades]`, then passed to `sharpe_ratio(returns)`.

In the six-year incremental runner, the merged report similarly builds `returns = [t["return_pct"] for t in all_trades]` and then calls `sharpe_ratio(returns)`.

In `prime/performance.py`, `sharpe_ratio()` defaults `periods_per_year` to `365.0`.

Since those series are per-trade returns, using `365` is incoherent unless the strategy makes exactly one trade per day on average.

The same misannualized Sharpe is then passed into the DSR calculation in the six-year runner.

## Daily Sharpe Correction

The current daily-equity flow is:

1. trade closes
2. trade PnL is added to running equity
3. the exit day maps to the latest running equity
4. only days that appear in the map are kept
5. daily returns are computed from consecutive mapped days
6. `daily_sharpe_ratio()` is computed

Calendar days with no trade are omitted.

That is why the daily series is not calendar-complete.

For sparse strategies, omitting zero-trade days tends to inflate the active-day Sharpe.

## Recommended Defaults

I would separate a minimum acceptable floor from a preferred setting:

- minimum acceptable floor: `target=0.45%`, `stop=0.30%`
- preferred setting: `target=0.60%`, `stop=0.30%`

The minimum floor restores reward greater than risk and brings fee-only break-even down to about `53.3%`.

The preferred setting lowers fee-only break-even further to about `44.4%` and is already aligned with the typed backtester's current geometry.

## Next Test Branch

For the next sweep, keep the analysis branch frozen and test on a new branch that only contains the parameter experiment.

Suggested starting point:

- branch: `codex/v91-parameter-test`
- scope: parameter changes only
- rule: do not mutate the audit branch while comparing variants

## Bottom Line

The repo contains a real signal-vs-trade conversion issue and a real Sharpe annualization bug.

But the main problem at HEAD is configuration drift, not a single inverted default.

The fastest way to make the backtest surface statistically coherent is:

1. unify the live defaults
2. fix Sharpe annualization
3. rebuild calendar-daily returns
4. move parameter experiments onto a separate branch
