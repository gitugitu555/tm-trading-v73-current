# Session Log - 2026-06-03

This document records the work completed in this Cursor/Grok session with user
**tokio** (workspace) and GitHub account **gitugitu555**.

## Session Goals

1. Deep-dive review of `tm-trading-v555` for improvements (no code changes initially).
2. Cross-check ideas against academic microstructure literature.
3. Produce a V7.7 improvement roadmap and push to GitHub.
4. Build full V7.2 **stage by stage**, modular and rearrangeable, **without backtesting**
   (backtests delegated to another AI).

## Starting Point

- GitHub repo: `gitugitu555/tm-trading-v555` (private), branch `master`.
- Local clone: `/home/tokio/tm-trading-v555` with `.venv` and passing tests.
- Parallel local scaffold: `orderflow-nautilus` at `/home/tokio/orderflow-nautilus`
  (not a git repo, not synced to GitHub).
- `gh` authenticated as `gitugitu555`, not Linux user `tokio`.
- Prior session log: `docs/SESSION_LOG_2026-06-02.md`.

## What We Achieved Today

### 1. Repository review (read-only phase)

- Cloned and analyzed `tm-trading-v555` structure (~71 Python modules, 98+ tests).
- Confirmed strongest measured edge: **300 BTC volume bars / 40-bar CVD / D4 HTF**
  (six-year diagnostic, IC ~0.052, 22k+ events) per `docs/V76_SWOT_EDGE_ROADMAP.md`.
- Mapped architectural debt: duplicate `features/` vs `prime/phase1`, two
  AlphaPermission paths, Session 5 doc vs code gap (`use_volume_bar_signal` vs
  `divergence_type=volume_bar_cvd`), CI installing only `pyarrow` not full deps.
- Identified literature-backed additions (volume-bucket VPIN, PIN, Kyle λ,
  deflated Sharpe discipline, triple-barrier labels, BOCPD, order-flow entropy).
- **Deliverable:** analysis only; user asked not to change code yet.

### 2. V7.7 improvement roadmap

- **Added:** `docs/V77_IMPROVEMENT_ROADMAP.md` (`7.7.0-IMPROVE`).
- Eight phased improvement program (hygiene → Session 5 engine → signal scorecards
  → consolidation → registry → state filters → execution → cross-regime validation).
- Academic tool tiers and explicit remove/quarantine list.
- **Commit:** `aaf1392` — `docs: add V7.7 improvement roadmap from repository review`
- **README** updated with link under Project Memory.

### 3. V7.2 modular staged build (implementation phase)

- **Added:** `v72/` package — composable pipeline, no `ChunkBBacktester` import.
- **Added:** `docs/V72_STAGED_BUILD.md` with stage map and exit criteria.
- **Stages implemented:**

| Stage | Module | Role |
| --- | --- | --- |
| S0 | `v72/stages/s0_truth.py` | Trade signing + data quality firewall |
| S1 | `v72/stages/s1_flow.py` | CVD, footprint, delta, VWAP (`prime/phase1`) |
| S2 | `v72/stages/s2_book.py` | Book intel via `features/` (optional) |
| S3 | `v72/stages/s3_regime.py` | `HardRegimeClassifier` |
| S4 | `v72/stages/s4_signal.py` | `CVDMomentumConfirmation` (V720 momentum, not divergence entry) |
| S5 | `v72/stages/s5_permission.py` | `AlphaPermissionEngineChunkB` |
| S6 | `v72/stages/s6_memory_risk.py` | Kill switch + `TradeIntentV72` + memory export |

- **Added:** `v72/pipeline.py` — `V72Pipeline` with `stage_order` and per-stage enable flags.
- **Added:** `v72/nautilus/cvd_momentum_confirmation.py` — facade + Nautilus Strategy
  factory when `nautilus_trader` installed; uses `register_indicator_for_trade_ticks`.
- **Added:** `tests/test_v72_pipeline_stages.py` (5 tests).
- **Added:** `scripts/v72_pipeline_demo.py` (synthetic tick demo, no backtest).
- **Updated:** `pyproject.toml` (packages `v72`, `v72.stages`, `v72.nautilus`),
  `docs/V72_ACTIVE_SPEC.md`, `README.md`.
- **Commit:** `528b425` — `feat(v72): modular V7.2 staged pipeline without backtest coupling`

### 4. Validation at end of session

```text
.venv/bin/python -m unittest tests.test_v72_pipeline_stages -v  → 5/5 OK
.venv/bin/python -m unittest discover -q                         → 103/103 OK
```

## What Worked

- **GitHub access** via `gh` and local repo at `/home/tokio/tm-trading-v555`.
- **Shallow clone + API** for review when needed.
- **Existing V7.5/V7.6 docs** were accurate; review aligned with SWOT and edge ranking.
- **Staged pipeline design** — each stage reads/writes `V72PipelineState`; stages can be
  disabled or reordered via `V72PipelineConfig` without touching backtest code.
- **Reusing proven modules** (`prime/phase0`, `phase1`, `phase4`, `phase5`) instead of
  rewriting feature math.
- **Tests green** after fixing `tick` name clash with `unittest.TestCase.tick` → `make_tick`.
- **Determinism test** — separate pipeline instances per run with unique trade ids.
- **Push to `master`** succeeded for both doc and code commits.

## What Did Not Work / Limitations

- **GitHub user `tokio`** — no public repos under that handle; actual remote is
  `gitugitu555/tm-trading-v555`. Linux user `tokio` ≠ GitHub org/user name.
- **Some web searches failed** (transient errors); literature section used partial
  results plus known references (Easley et al. VPIN, Bailey/López de Prado DSR, etc.).
- **CI gap not fixed today** — `.github/workflows/ci.yml` still only installs `pyarrow`;
  full `pyproject.toml` deps not wired (noted in V7.7 P0).
- **`orderflow-nautilus` not merged** — valuable replay/KQ/storage still local-only.
- **Volume-bar CVD Session 5** — not extracted into `v72` as separate stage (still in
  `prime/chunk_b_backtest.py` for other AI backtests).
- **No real-archive run today** — pipeline demo uses synthetic ticks only (by design;
  user excluded backtest).
- **Nautilus Strategy class** — only built when `nautilus_trader` installed; tests use
  `CVDMomentumConfirmationFacade` fallback.
- **S2 book stage** — uses adapter from `prime` SignedTrade → `core` SignedTrade; two
  type systems remain (consolidation deferred to V7.7).

## Intentionally Out Of Scope (User Direction)

- No runs of `chunk_b_backtest.py`, `chunk_b_sweep.py`, or PnL proof.
- No changes to sweep results or six-year shard outputs.
- No live trading or order routing (`enable_trading` raises if set).

## Git Commits This Session

| Commit | Summary |
| --- | --- |
| `aaf1392` | V7.7 improvement roadmap + README link |
| `528b425` | V7.2 `v72/` staged pipeline, tests, demo, docs |

Previous head before session (context): `ab0830c` (cache pool size).

## Files Added Or Materially Changed Today

```text
docs/V77_IMPROVEMENT_ROADMAP.md
docs/V72_STAGED_BUILD.md
docs/V72_ACTIVE_SPEC.md
docs/SESSION_LOG_2026-06-03.md          (this file)
v72/__init__.py
v72/contracts.py
v72/pipeline.py
v72/stages/*.py
v72/nautilus/*.py
tests/test_v72_pipeline_stages.py
scripts/v72_pipeline_demo.py
README.md
pyproject.toml
```

## Recommended Next Session (Not Done Today)

1. **V7.7 P0** — dataset/result manifests, CI `pip install -e .`, README/download status.
2. **Extract `VolumeBarCVDConfluenceEngine`** as optional `v72` stage S4b (parity with diagnostic).
3. **Port `orderflow-nautilus`** replay + no-lookahead tests into `v72`.
4. **Signal-only scorecard** module (no trade conversion) for other AI to consume outputs.
5. **Consolidate `features/` vs `prime/`** per V7.7 Phase 3.

## Quick Commands For Next Time

```bash
cd /home/tokio/tm-trading-v555
.venv/bin/python -m unittest tests.test_v72_pipeline_stages -v
.venv/bin/python scripts/v72_pipeline_demo.py
```

## Session Outcome In One Line

We documented how to improve the repo (V7.7), then shipped a **modular, backtest-free
V7.2 pipeline (`v72/`)** so each layer can be swapped or tested independently while
another process owns backtests and PnL proof.

---

## Part 2 — Six-Year Backtest, NVMe Hot Path, Pre-Cache (Same Day)

Continuation after user requested full V7.2 six-year backtest on BTCUSDT aggTrades and
faster I/O. Backtests run here (not delegated) using existing Chunk B cached path.

### Goals (Part 2)

1. Run full 6y momentum backtest (`signal_mode=momentum`, 300 BTC volume bars).
2. Force hot-path reads on **NVMe**, not Seagate cold HDD.
3. Speed up wall clock via background parquet pre-cache.
4. Diagnose poor interim win rate vs measured diagnostic edge.

### What We Achieved (Part 2)

#### Six-year incremental backtest runner

- **Added:** `scripts/v72_backtest_6y_incremental.py` — per-archive cache →
  `chunk_b_backtest_cached.py` → merge trades, carry equity, `progress.json` resume.
- **Added:** `scripts/v72_backtest_6y.py` (companion entry).
- **Output target:** `results/v72_backtest_6y_momentum.json`
- **Work dir:** `results/v72_backtest_6y_work/` (per-archive `*.trades.jsonl`, `progress.json`)
- **Commit:** `04826e9` — `feat: V7.2 six-year incremental backtest runner`

#### NVMe hot-path enforcement

- **Added:** `storage/hot_path.py` — `assert_nvme_path`, `assert_nvme_archive`,
  `hot_btcusdt_aggtrades_dir()`; fails on `/mnt/seagate` or same `st_dev` as cold root.
- **Added:** `scripts/ensure_nvme_hot_data.sh` — verify 134 zips on NVMe, remove nested
  Seagate symlink inside hot dir if present.
- Wired guards into `cache_indicators.py`, `v72_backtest_6y_incremental.py`.
- **Verified:** 134 archives under `data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21`
  on `/dev/nvme0n1p2`; indicator cache on NVMe (`results/indicator_cache/`).
- **Commit:** `f827bd2` — `fix: enforce NVMe hot path for 6y cache and backtest`

#### Background pre-cache

- **Updated:** `scripts/cache_all.py` — NVMe guards, `--workers` (default 4), `--skip-archive`,
  skip-if-parquet-exists via `cache_indicators.py`.
- **Updated:** `scripts/cache_indicators.py` — early return when parquet already present.
- **Updated:** `scripts/chunk_b_backtest_cached.py` — NVMe guards on dest/cache/archive.
- Started: `nice -n 10 .venv/bin/python scripts/cache_all.py --workers 4 --threshold-btc 300`
  (skips month backtest is actively caching to avoid double-write).

#### Interim backtest results (archives 0–16, ~May–Dec 2020)

From `results/v72_backtest_6y_work/*.trades.jsonl` (**1915** trades):

| Metric | Value |
| --- | --- |
| Win rate | **17.5%** (335 W / 1578 L) |
| Equity | **$96,080** (from $100k) |
| PnL | **−$3,920** |
| Exits | STOP 1133, TIME 610, TARGET 172 |

**Interpretation (not a backtest bug):**

- Run uses **`signal_mode=momentum`** (trend-follow CVD in `TREND_*`).
- Strongest repo evidence is **`volume_bar_cvd` divergence** (~53% event hit rate, IC ~0.05)
  per `results/volume_bar_cvd_6y.json` and `docs/V76_SWOT_EDGE_ROADMAP.md`.
- Tight stop (0.3%) vs target (0.6%) + fees → low win rate expected for weak momentum conversion;
  aligns with historical sweeps (often 11–25% win rate).
- V7.6 thesis: signal exists; **conversion layer is weak**.

#### Network interruption and recovery

- Backtest killed mid-cache on **2021-01** (no parquet written after ~35M tick progress lines).
- **Restarted** with `--resume` from index 17; `cache_all` left running.
- Corrected other-agent ETA note: bottleneck is **parquet build (CPU/NVMe)**, not 51 GB HDD
  cold zip reads for this run.

### Performance Expectations (Documented for User)

| Phase | When | Typical time |
| --- | --- | --- |
| Cache build | Parquet missing | ~15–45 min / month |
| Backtest only | Parquet exists | ~1–3 min / month |
| Full 6y rerun | All 133 `threshold-300` parquets | ~2–6 h (backtest-only) |

Pre-cache raises cache hit rate so **subsequent archives in the same run get faster**;
a future rerun at the same threshold is much faster if parquets are kept.

### What Worked (Part 2)

- NVMe path verification via `findmnt`, `st_dev`, and open-file checks on running PIDs.
- Resume checkpoint (`progress.json`) preserved 17 archives of trade history.
- Parallel `cache_all` writing parquets while incremental job runs (with skip for active month).
- Session log commit from Part 1: `2c6232d`.

### What Did Not Work / Still Open (Part 2)

- **Full `results/v72_backtest_6y_momentum.json` not complete** at log write — job interrupted
  and restarted; monitor `progress.json` and logs.
- **2021-01 parquet** was missing twice (longest single-month cache).
- **Uncommitted local edits** at end of Part 2: `cache_all.py`, `cache_indicators.py`,
  `chunk_b_backtest_cached.py` (pre-cache + guards) — committed with this log update.
- **Momentum 6y PnL** negative on interim sample — strategy/param review needed, not I/O.
- **Volume-bar CVD** not yet wired as `v72` stage or default 6y backtest mode.

### Git Commits (Part 2)

| Commit | Summary |
| --- | --- |
| `2c6232d` | Session log 2026-06-03 (Part 1) |
| `04826e9` | `v72_backtest_6y_incremental.py` runner |
| `f827bd2` | NVMe hot path module + script guards |
| *(this push)* | Part 2 log + pre-cache script hardening |

### Monitor Commands (Part 2)

```bash
cat results/v72_backtest_6y_work/progress.json
tail -f logs/v72_backtest_6y_nvme.log
tail -f logs/cache_all_nvme.log
ls results/indicator_cache/*.threshold-300.parquet | wc -l
pgrep -af 'v72_backtest_6y_incremental|cache_all'
```

### Resume Backtest

```bash
cd /home/tokio/tm-trading-v555
export TM_DATA_HOT_ROOT="$PWD/data/raw"
export TM_DATA_COLD_ROOT="/mnt/seagate/tm-trading-v555/data/raw"
.venv/bin/python scripts/v72_backtest_6y_incremental.py \
  --signal-mode momentum --threshold-btc 300 --resume \
  --output results/v72_backtest_6y_momentum.json
```

### Recommended Next Steps (Part 2)

1. Let pre-cache + incremental run finish; summarize final JSON metrics.
2. Re-run or branch with `--signal-mode divergence --divergence-type volume_bar_cvd` aligned
   with Session 5 / six-year diagnostic.
3. V7.7 P0 manifests + CI full deps.
4. Extract `VolumeBarCVDConfluenceEngine` as optional `v72` stage S4b.

## Combined Session Outcome (Parts 1 + 2)

Shipped **V7.7 roadmap**, **modular `v72/` pipeline**, **NVMe-guarded 6y backtest runner**,
and **parallel pre-cache**; interim momentum results are poor (~17.5% win rate) while measured
edge remains in volume-bar CVD diagnostics — conversion/strategy mode is the next lever.