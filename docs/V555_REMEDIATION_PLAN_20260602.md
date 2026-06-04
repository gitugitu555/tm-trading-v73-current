# V555 Remediation Plan - 2026-06-02

This note tracks fixes for the current review findings while keeping existing
files untouched until the next integration pass.

## Immediate Additions

- `scripts/audit_repo_artifacts.py` reports tracked sweeps, tracked result
  artifacts, tracked cache files, and untracked generated/context files.
- `prime/chunk_b_trade_state.py` provides an immutable `OpenTradeState` to
  replace the raw mutable `open_trade` dictionaries in `prime/chunk_b_backtest.py`.
- `tests/test_chunk_b_trade_state.py` verifies long/short excursion accounting
  and the compatibility shape needed by the current backtester.

## Recommended Next Integration

1. Replace `open_trade: dict | None` in `prime/chunk_b_backtest.py` with
   `OpenTradeState | None`.
2. Replace `_update_trade_excursion(open_trade, price)` mutation with
   `open_trade = open_trade.with_excursion(price)`.
3. Update `_exit_reason` and `_close_trade` to accept `OpenTradeState`.
4. Move generated outputs out of Git with `git rm --cached`, using
   `scripts/audit_repo_artifacts.py --print-commands` as the source of truth.
5. Add a narrow `.gitignore` update for `results/*.html`, `results/*cache/`,
   `data/nautilus/`, and root-level ad hoc `sweep_*.json` outputs after
   approving edits to existing files.

## Evidence Threshold

Treat current positive backtests as research diagnostics only. The repo should
not promote an edge until it has an out-of-sample report with meaningful trade
count, fees, slippage, and artifact paths captured in one reproducible manifest.
