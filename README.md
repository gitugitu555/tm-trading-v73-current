# TM Trading v7.3 Current

Win-rate improvement fork of [tm-trading-v555](https://github.com/gitugitu555/tm-trading-v555).
Focus: align Chunk B backtests with the measured **volume-bar CVD** edge (~53% signal hit rate)
instead of the legacy momentum path (~17% trade win rate on 6y runs).

See `docs/V73_WIN_RATE_PROGRAM.md` for the staged checkpoint plan.

The upstream repo still targets V7.2 Nautilus-Prime (`v72/`); this fork owns
signal→trade conversion experiments until promoted back.

The project starts with the parts that must be correct before any strategy, UI, agent, or live execution work:

- pure feature engines
- replay validator
- AlphaPermission object
- Nautilus strategy boundary skeleton
- memory export object
- whale MVP components from free trade and L2 data

No live trading is enabled in this scaffold. The hot path has no database, network, vector DB, n8n, or LLM dependency.

## Quick Start

```bash
cd /home/tokio/tm-trading-v555
.venv/bin/python -m unittest
.venv/bin/python scripts/replay_demo.py
.venv/bin/python -m unittest tests.test_v72_pipeline_stages -v
.venv/bin/python scripts/v72_pipeline_demo.py
```

## Project Rules

- Feature engines are deterministic and unit tested.
- Feature engines accept explicit inputs and return structured outputs.
- Nautilus integration stays a boundary layer; feature logic lives in `features/`.
- Semantic memory stores setup summaries, not raw ticks.
- AlphaPermission can permit candidates, but risk owns the final execution gate.
- No ML is introduced before replay, parity, and leakage tests exist.

## Current Scope

Implemented now:

- trade signing
- CVD
- footprint
- delta velocity and acceleration
- VPIN
- microprice
- L2 imbalance
- absorption
- spoofing
- iceberg detection
- large-print whale signal
- whale composite MVP
- replay validator with deterministic checksum
- AlphaPermission deterministic KQ fallback
- memory setup summary export
- Nautilus no-trade skeleton

Planned next:

- Binance collectors
- TimescaleDB buffered writer
- Nautilus package-backed replay adapter
- GEX/OI/funding/basis engines
- n8n workflow exports
- operator UI after feature validation

## Data Layout

Raw market-data storage and cache workflow is documented in `docs/DATA_LAYOUT.md`.

## Project Memory

- Roadmap: `docs/PROJECT_ROADMAP.md`
- Project log: `docs/PROJECT_LOG.md`
- Session log (2026-06-03): `docs/SESSION_LOG_2026-06-03.md` (V7.7, `v72/` build, 6y backtest, NVMe)
- Session log (2026-06-02): `docs/SESSION_LOG_2026-06-02.md` (trade state, caching, artifacts)
- Lessons learned: `docs/LESSONS_LEARNED.md`
- Data layout: `docs/DATA_LAYOUT.md`
- V7.4 auction-state blueprint: `docs/V74_AUCTION_STATE_ENGINE_BLUEPRINT.md`
- V7.5 master roadmap: `docs/V75_MASTER_ROADMAP.md`
- V7.6 SWOT and edge roadmap: `docs/V76_SWOT_EDGE_ROADMAP.md`
- V7.2 staged modular build: `docs/V72_STAGED_BUILD.md`
- V7.7 improvement roadmap: `docs/V77_IMPROVEMENT_ROADMAP.md`
- Multi-agent automation roadmap: `docs/MULTI_AGENT_AUTOMATION_ROADMAP.md`

## Build Phases

The Gold Master build is compressed into three phases in
`docs/V555_3_PHASE_PLAN.md`:

- Phase 1: deterministic market physics MVP
- Phase 2: research store, risk, and paper execution
- Phase 3: memory, orchestration, UI, and ML candidate
