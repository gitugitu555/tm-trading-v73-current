# TM Trading System V7.7 Improvement Roadmap

Version: `7.7.0-IMPROVE`

Status: consolidated improvement plan from repository review (2026-06-03).
Not the active implementation target until V7.6 edge pipeline gates pass.

Active build target remains: V7.2 Nautilus-Prime.

Upstream roadmaps:

- V7.4: auction-state orchestration (`docs/V74_AUCTION_STATE_ENGINE_BLUEPRINT.md`)
- V7.5: research operating system (`docs/V75_MASTER_ROADMAP.md`)
- V7.6: edge pipeline and SWOT (`docs/V76_SWOT_EDGE_ROADMAP.md`)

V7.7 target: turn review findings into an ordered, test-gated improvement program
that protects the measured volume-bar CVD edge, removes structural debt, and adds
only literature-backed tools with clear KEEP/DELETE promotion rules.

## 1. Executive Summary

V7.7 is not "version 7.7 of the strategy." It is the **engineering and research
hygiene release** that makes V7.6 promotable.

The project already has:

- strong deterministic feature and backtest foundations
- a measured six-year volume-bar CVD candidate (300 BTC bars, 40-bar lookback,
  D4 HTF filter)
- thoughtful V7.4–V7.6 architecture documentation

The project still lacks:

- a single source of truth for feature logic (duplicate `features/` vs `prime/`)
- parity between diagnostic scripts and Chunk B signal paths
- formal dataset and experiment manifests
- signal-only vs trade-converted score separation
- CI that installs declared dependencies and proves integration paths

V7.7 succeeds when the repo is **harder to fool** and **easier to reproduce**,
without adding indicator sprawl.

## 2. Review Baseline (2026-06-03)

### Repository facts

- GitHub: `gitugitu555/tm-trading-v555` (private), default branch `master`
- ~71 Python modules, 13+ test modules, 98 unit tests observed (1 cache test
  may fail without local volume-bar cache fixtures)
- Parallel local scaffold: `orderflow-nautilus` (replay, KQ score, storage SQL) not
  synced to GitHub — treat as staging lab until ported

### Strongest measured edge (unchanged from V7.6)

```text
Diagnostic: volume_bar_cvd
Data: BTCUSDT aggTrades, six-year span
Best aggregate row:
  threshold: 300 BTC volume bars
  divergence lookback: 40 bars
  stage: D4_htf
  horizon: 5 bars
  events: 22,506
  hit_rate: 0.532880
  IC: 0.051890
  mean_sfr: 0.00024894
```

Conclusion: **protect and formalize this signal** before building V7.5 layers at
full scale.

## 3. V7.7 Core Laws

1. No new raw indicator enters the hot path without ablation and a feature contract.
2. Diagnostic logic and Chunk B logic must share one engine module.
3. Every cited result file must have a `ResultManifest` with `git_commit` and command.
4. Signal IC and trade PnL are reported separately — never conflated.
5. Duplicate implementations are removed or adapted, not maintained in parallel.
6. Academic tools enter as deterministic engines first; ML stays behind triple-barrier
   and walk-forward gates.
7. Orchestration (Hermes, n8n, UI) stays off the hot path until V7.6 Phase 2 passes.
8. Live trading remains disabled until execution quality is measured separately from
   signal quality.

## 4. Architecture Target

```text
Truth Layer (manifests, signing, data quality)
    -> Flow Layer (volume bars, CVD, feature registry)
        -> State Layer (auction state, structural memory lite, eligibility)
            -> Gates (AlphaPermission V2, execution decision, kill switch)
                -> Research Layer (signal scorecard, trade scorecard, ablation)
```

V7.7 implements the **contracts and consolidation** that let V7.5/V7.6 layers plug
in without drift.

## 5. Improvement Program

### Phase 0 — Repo hygiene (P0, week 1)

| ID | Action | Rationale |
| --- | --- | --- |
| P0-1 | Fix README quick-start paths (use repo `.venv`, document `master`) | Removes onboarding friction |
| P0-2 | Add `DatasetManifest` for BTCUSDT six-year aggTrades | Reproducible truth layer |
| P0-3 | Add `ResultManifest` for `results/volume_bar_cvd_6y.json` | Stops result lore |
| P0-4 | Mark empty sweep files and footprint shard placeholders in manifests | Prevents false edge claims |
| P0-5 | Fix or replace `scripts/download_status.sh` with data-manager status | Symlinked cold storage false negatives |
| P0-6 | CI: `pip install -e .` or install `pyproject.toml` dependencies | CI must match declared stack |
| P0-7 | Add volume-bar cache fixture so `test_volume_bar_cache` passes in CI | Green CI without local data |

Exit gate: unittest green on clean clone; dataset manager and status agree.

### Phase 1 — Session 5 completion (P0, week 1–2)

| ID | Action | Rationale |
| --- | --- | --- |
| P1-1 | Extract `VolumeBarCVDConfluenceEngine` from `prime/chunk_b_backtest.py` | Single source for diagnostic ≡ backtest |
| P1-2 | Wire Chunk B via engine import, not inlined `_volume_bar_cvd_signal` | Prevents silent drift |
| P1-3 | Add alias `use_volume_bar_signal` -> `divergence_type=volume_bar_cvd` | Doc/code alignment |
| P1-4 | Tests: D1 bearish, D1 bullish, HTF flat-abs quantile parity | Session 5 acceptance |
| P1-5 | Test: momentum mode unchanged when volume-bar flag off | Regression guard |
| P1-6 | Smoke: `BTCUSDT-aggTrades-2022-09.zip` with manifest output | First integrated evidence |

Exit gate: diagnostic row direction reproduced on signal-only scorecard.

### Phase 2 — Signal-only research layer (P0, week 2)

| ID | Action | Rationale |
| --- | --- | --- |
| P2-1 | Add `SignalScorecard` (events, hit_rate, IC, mean_sfr, filter drops) | Separates signal from PnL |
| P2-2 | Chunk B reports `signal_scorecard` and `trade_scorecard` separately | V7.6 conversion weakness |
| P2-3 | Add `ExperimentManifest` to sweep and backtest scripts | Every run reproducible |
| P2-4 | Register `n_trials` per sweep for deflated Sharpe | Bailey & López de Prado DSR honesty |

Exit gate: six-year diagnostic direction visible in signal-only report without
opening a trade.

### Phase 3 — Codebase consolidation (P1, week 2–3)

| ID | Action | Rationale |
| --- | --- | --- |
| P3-1 | Declare `prime/` as canonical for Nautilus and Chunk B paths | Ends dual-stack ambiguity |
| P3-2 | Make `features/` thin adapters or re-exports over `prime` | One implementation |
| P3-3 | Deprecate `strategy/alpha_permission.py` if unused; document Chunk B path | Two permission systems |
| P3-4 | Integrate `OpenTradeState` in `chunk_b_backtest.py` per remediation plan | Immutable trade state |
| P3-5 | Port from `orderflow-nautilus`: replay engine, no-lookahead tests, KQ breakdown | Staging lab → repo |
| P3-6 | `git rm --cached` generated sweeps; extend `.gitignore` per `audit_repo_artifacts.py` | Repo hygiene |

Exit gate: no duplicate CVD/footprint logic without adapter justification.

### Phase 4 — Feature registry and governance (P1, week 3)

| ID | Action | Rationale |
| --- | --- | --- |
| P4-1 | Add `research/feature_registry.py` with `FeatureContract` | V7.5 law #1 |
| P4-2 | Register all engines: inputs, warmup, reset, test module, version | Auditable surface |
| P4-3 | Mark VPIN as `SIMPLIFIED_TRADE_WINDOW` or upgrade to volume-bucket VPIN | Academic honesty |
| P4-4 | Streaming-vs-batch parity tests for registry features | Replay safety |
| P4-5 | IC validation hooks: KEEP / CONTEXT_ONLY / DELETE from `prime/ic_validation.py` | Feature deletion machine |

Exit gate: every strategy dependency appears in registry with a test reference.

### Phase 5 — State and location filters (P1, week 3–4)

| ID | Action | Rationale |
| --- | --- | --- |
| P5-1 | Expand `AuctionStateEngine` per V7.4 minimal set + anti-flicker tests | Edge filter for fade signal |
| P5-2 | Add `delta_efficiency` and `acceptance_rejection` in `prime/derived_state.py` | Initiative vs absorption |
| P5-3 | Structural memory lite: failed auction, session VWAP migration, decay | Location without fake S/R |
| P5-4 | Strategy eligibility matrix before AlphaPermission | Regime → allowed class |
| P5-5 | Enable `use_auction_state_gate` in volume-bar mode with ablation | Measure filter value |

Exit gate: state filter improves or safely reduces signal-only score; ablation
documents KEEP/DELETE.

### Phase 6 — AlphaPermission and execution (P2, week 4–5)

| ID | Action | Rationale |
| --- | --- | --- |
| P6-1 | AlphaPermission V2 optional inputs: auction state, memory, book snapshot | Evidence chain |
| P6-2 | Verdicts: APPROVE, REDUCED, DELAY, PASSIVE_ONLY, HARD_DENY | Execution-aware |
| P6-3 | `ExecutionDecision` module: TAKE, POST, DELAY, SKIP, `BOOK_UNKNOWN` | Signal ≠ fill |
| P6-4 | Kyle λ / Amihud proxies for delay and size reduction | Literature-backed execution gate |
| P6-5 | Fill-quality scorecard separate from signal scorecard | Live-readiness metric |

Exit gate: toxic-book synthetic tests delay entry without corrupting signal evidence.

### Phase 7 — Cross-regime validation (P2, week 5–6)

Run signal-only and trade-converted scorecards on:

```text
BTCUSDT-aggTrades-2021-11.zip
BTCUSDT-aggTrades-2022-05.zip
BTCUSDT-aggTrades-2022-09.zip
BTCUSDT-aggTrades-2023-01.zip
BTCUSDT-aggTrades-2023-03.zip
```

Exit gate: candidate does not collapse outside discovery archive; losing regimes
have reason-coded drop counts.

## 6. Academic and Literature-Backed Tool Additions

Add only as **deterministic engines** or **offline calibrators** until V7.7 Phase 7
passes.

### Tier 1 — Implement or upgrade (high value, fits repo)

| Tool | Reference | V7.7 use |
| --- | --- | --- |
| Volume-bucket VPIN | Easley, López de Prado, O'Hara (2012), *Review of Financial Studies* | Toxicity gate; upgrade or relabel current trade-window proxy |
| PIN (batch) | Easley et al.; Bayesian PIN (e.g. Paiardini et al.) | Offline informed-flow regime label |
| Kyle λ / Amihud | Kyle (1985); Amihud (2002) | Execution delay and size scalar |
| Deflated Sharpe + trial count | Bailey & López de Prado (2014) | Sweep promotion honesty |
| Purged K-fold / walk-forward | López de Prado, *Advances in Financial Machine Learning* | Parameter promotion across six-year data |
| Triple-barrier labels | López de Prado (AFML) | Prerequisite for any ML layer |

### Tier 2 — State and event detection

| Tool | Reference | V7.7 use |
| --- | --- | --- |
| Acceptance / rejection scoring | Auction market theory / value migration | AuctionStateEngine evidence |
| Order-flow entropy | ECB and recent microstructure entropy literature | Low-participation and chop filter |
| Bayesian change-point (BOCPD) | Online change-point for order flow (e.g. arXiv:2307.02375) | Liquidity event override with reason codes |
| Value area / POC migration | Market Profile (Steidlmayer); structural memory | Location filter for volume-bar fades |

### Tier 3 — Defer until Tier 1–2 ablated

| Tool | Notes |
| --- | --- |
| Hawkes trade clustering | Cascade detection; high complexity |
| Deep LOB ML | Requires sustained L2 capture and labeling infrastructure |
| Transformer / NN order-flow | Forbidden until triple-barrier + leakage + walk-forward exist |

## 7. Logic and Modules to Remove or Quarantine

Do not delete capability without ablation — **remove duplication and distraction**.

| Item | V7.7 action |
| --- | --- |
| Duplicate `features/*` vs `prime/phase1` engines | Consolidate; keep one implementation |
| `strategy/alpha_permission.py` | Deprecate if Chunk B path is canonical |
| Simplified VPIN as "full VPIN" | Relabel or upgrade to volume buckets |
| Hermes CLI bridge on hot path | Quarantine to `orchestration/`; fix hardcoded paths |
| Empty sweep JSON and placeholder footprint shards | Manifest as `PLACEHOLDER` or delete from git tracking |
| New raw indicators before Session 5 scorecard | Block by V7.7 law #1 |
| UI / ML / multi-symbol expansion | Defer per V7.6 |

## 8. Suggested New Files (V7.7)

```text
docs/V77_IMPROVEMENT_ROADMAP.md          (this document)
prime/volume_bar_cvd_confluence.py       (extracted Session 5 engine)
prime/derived_state.py                   (delta efficiency, acceptance/rejection)
research/feature_registry.py
research/experiment_manifest.py
research/signal_scorecard.py
storage/dataset_manifest.py
prime/execution_decision.py
tests/test_volume_bar_cvd_confluence.py
tests/test_signal_scorecard.py
tests/test_experiment_manifest.py
tests/test_feature_registry.py
```

Avoid god files. Each module: contract + deterministic tests before integration.

## 9. CI and Quality Bar (V7.7)

Update `.github/workflows/ci.yml`:

```yaml
# Target shape (implement in V7.7 Phase 0)
- pip install -e .
- python -m unittest discover -v
- python scripts/replay_demo.py
# Optional smoke (no large data in CI):
- python -m unittest tests.test_volume_bar_cvd_confluence -v
```

Requirements:

- Python 3.11 and 3.12 matrix (keep)
- Install `pyproject.toml` dependencies including `nautilus_trader` where tests need it
- Fail CI on placeholder results referenced without manifest status

## 10. V7.7 Test Ladder

Every improvement must pass:

1. Contract test
2. Synthetic deterministic unit test
3. Edge-case synthetic test
4. Streaming-vs-batch parity (if applicable)
5. Single-archive smoke with manifest
6. Cross-regime archive set (Phase 7)
7. Signal-only scorecard reproduction
8. Trade-converted scorecard with fees and slippage
9. Ablation KEEP/DELETE per added layer
10. Walk-forward or chronological holdout before promotion

## 11. V7.7 Promotion Gates

V7.7 documentation is **complete** when this file is merged.

V7.7 **implementation** is promotable to active target only when:

- [ ] P0 hygiene exit gate passes
- [ ] `VolumeBarCVDConfluenceEngine` matches diagnostic on fixtures
- [ ] Signal-only scorecard reproduces six-year diagnostic direction
- [ ] Feature registry covers all Chunk B dependencies
- [ ] Duplicate feature stacks resolved
- [ ] Experiment manifests emitted by sweep and backtest scripts
- [ ] Cross-regime Phase 7 does not collapse to a single archive
- [ ] Ablation supports auction state and memory lite layers (or they stay disabled)
- [ ] CI installs project dependencies and stays green
- [ ] No edge claim in docs without manifest + scorecard

## 12. Relationship to V7.6

V7.6 defines **what edge to pursue** (`VolumeBarCVDStateEdge`).

V7.7 defines **how to implement and protect it** without scope creep:

```text
V7.6 = edge thesis and phased strategy pipeline
V7.7 = engineering program, consolidation, literature gates, and promotion discipline
```

Execute V7.7 phases **in order**. Do not skip to execution intelligence (Phase 6)
before Session 5 engine extraction and signal-only scorecards (Phases 1–2).

## 13. Immediate Next Actions (copy-paste checklist)

```text
[ ] Merge V77_IMPROVEMENT_ROADMAP.md and README link
[ ] P0-2 DatasetManifest for six-year BTCUSDT
[ ] P1-1 Extract VolumeBarCVDConfluenceEngine
[ ] P1-4 D1 + HTF unit tests
[ ] P2-1 SignalScorecard in Chunk B report
[ ] P3-1 Document prime/ as canonical
[ ] P4-1 Feature registry skeleton
[ ] P0-6 CI installs pyproject dependencies
```

## 14. Final Definition

V7.7 is the version where the project stops accumulating **indicators and lore**
and starts accumulating **proof**:

- one engine per signal definition
- one manifest per cited result
- one scorecard for signals and one for trades
- one promotion gate per layer

If V7.6 asks "where is the edge?", V7.7 asks:

```text
Can we reproduce it, explain every filter drop, ablate every added layer,
and delete anything that fails without breaking the build?
```

That is the improvement roadmap.