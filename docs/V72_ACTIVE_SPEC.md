# TM Trading System V7.2 Active Spec

The active implementation target is now V7.2 Nautilus-Prime.

Modular staged implementation (no backtest coupling): `v72/` package and
`docs/V72_STAGED_BUILD.md`.

## Current Chunk

Chunk B - Prove Edge is now being built after Chunk A passed on real BTCUSDT
sample data.

Build order:

1. Implement Phase 0 data contracts, deterministic signing, and firewall.
2. Implement Phase 1 CVD and Footprint engines using event-driven trade ticks.
3. Run sample-first IC checks.
4. Keep engines only if `abs(IC) >= 0.02` at at least one strategy horizon:
   `5m`, `15m`, or `30m`.
5. Check CVD vs Footprint collinearity is below `0.85`.

## Local Dependency State

This repo currently includes a compatibility layer in `prime/nautilus_compat.py`.
It imports real Nautilus Trader classes when available and otherwise provides
deterministic stand-ins for tests and raw-data IC smoke checks.

Install the full Chunk A stack before production Nautilus validation:

```bash
pip install nautilus_trader pandas pyarrow scipy
```

## Commands

```bash
python3 -m unittest
python3 scripts/chunk_a_ic_sample.py --max-rows 50000
```

If the IC script returns `DELETE`, stop. Fix signal quality before Chunk B.

Chunk B commands:

```bash
python3 scripts/chunk_b_backtest.py --max-rows 50000
python3 scripts/chunk_b_sweep.py --max-rows 500000 --divergence-threshold 80
```

The deterministic Chunk B probe is not a substitute for the final Nautilus
catalog walk-forward. It verifies the reduced three-multiplier signal path,
fees, slippage, Sharpe, and approximate deflated Sharpe before expensive
catalog runs.
