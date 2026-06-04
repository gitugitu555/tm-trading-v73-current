# V555 Three-Phase Build Plan

This compresses the Gold Master build into three result-oriented phases. The rule is simple:
hot-path correctness first, storage and risk second, agents/UI last.

## Phase 1 - Deterministic Market Physics MVP

Goal: prove that raw trade and L2 inputs produce deterministic, testable feature snapshots.

Includes:

- repository structure, config hash, logging, tests
- CSV trade/book replay validator with stable checksum
- data quality firewall
- pure feature engines: signing, CVD, footprint, delta velocity/acceleration, VPIN,
  microprice, L2 imbalance, absorption, spoofing, iceberg, large prints, whale MVP
- AlphaPermission deterministic fallback with reason codes
- no-trade Nautilus boundary skeleton
- setup memory export object

Visible result:

- `python3 -m unittest`
- `python3 scripts/replay_demo.py`

Exit criteria:

- all tests pass
- replay checksum is stable across repeated runs
- every candidate/no-trade has reason codes
- no database, n8n, vector DB, LLM, or UI dependency in the hot path

## Phase 2 - Research Store, Risk, and Paper Execution

Goal: make experiments queryable, reproducible, and impossible to route around risk.

Includes:

- Binance historical trade loader and L2 collector
- immutable raw storage and replay file format
- TimescaleDB/Postgres schemas and buffered writers
- feature snapshot table writes outside the hot path
- Nautilus adapter backed by real Nautilus when installed
- RiskGate, kill switch, sizing, slippage, TCA logs
- paper orders only
- GEX/OI/funding/basis/VWAP/realized moments stubs promoted into tested engines

Visible result:

- one day of BTCUSDT replay loads, validates, and writes snapshots
- feature snapshots query by instrument/session/regime
- paper TradeIntent cannot bypass RiskGate

Tools likely needed:

- `nautilus-trader`
- `psycopg` or `asyncpg`
- local Docker/Podman for TimescaleDB, unless you already have Postgres/Timescale running

## Phase 3 - Memory, Orchestration, UI, and ML Candidate

Goal: add review, retrieval, operator visibility, and only then ML candidates.

Includes:

- n8n workflow exports for alerts/reviews
- OpenClaw/vector memory inserts and similarity search
- operator UI for existing features only
- replay controls, CVD panel, whale panel, footprint canvas
- triple-barrier labels
- leakage detector
- walk-forward training
- ML-KQ candidate gated behind out-of-sample improvement after costs

Visible result:

- current setup retrieves similar historical setups
- UI displays replayed features without computing alpha itself
- ML candidate is accepted only after leakage and walk-forward checks pass

Tools likely needed:

- Qdrant or LanceDB
- n8n
- React/Vite if the UI is built in this repo
- ML stack only after Phase 2 is stable

## Current Decision

Do not delete the existing scaffold. It already matches Phase 1 shape and has passing tests.
Replacing it from zero would slow the build without improving alignment to V555.
