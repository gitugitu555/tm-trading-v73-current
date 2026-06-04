# Contributing

This document captures the build rules for tm-trading-v555.

## Before You Write Code

1. Run the test suite.
   ```bash
   .venv/bin/python -m unittest
   ```
2. Read the relevant spec in `docs/`.
3. Identify the module that already owns the abstraction you need.

## Hard Rules

- No pandas inside engine or backtester classes.
- Use `sorted()` on dict/set iteration where deterministic output matters.
- Use `apply_patch` for targeted edits.
- Timestamps are nanoseconds (`int`).
- Do not use `is_buyer_maker` in engine code.
- New signal paths must default to off.
- Every feature change ships with tests.

## Phase Gates

| Phase | Gate |
|-------|------|
| Signal exists | `abs(IC) >= 0.02` at a strategy horizon in at least two archives |
| Signal promoted to Chunk B | Win rate > 0.52, trades > 30, Sharpe > 0 |
| Paper trading enabled | All of the above and kill switch tested |
| Live trading enabled | Paper trading profitable over a meaningful sample |

## Result Standards

A result is evidence only when it includes:

- git commit hash
- archive name and row count
- exact command used to reproduce it
- fees and slippage
- trade count >= 30

## Do Not

- Add a new raw indicator before existing ones survive ablation.
- Run a full six-year sweep before a single-archive smoke test passes.
- Call AlphaPermission from inside signal detection logic.
- Promote a feature to default-enabled before cross-regime validation.
