# TM Trading System V7.6 SWOT and Edge Roadmap

Version: `7.6.0-EDGE`

Status: strategic edge roadmap; not yet the active implementation target.

Active build target remains: V7.2 Nautilus-Prime.

V7.4 target: auction-state orchestration.

V7.5 target: full research operating system.

V7.6 target: identify the highest-probability edge path and turn it into a
disciplined, tested, state-gated, execution-aware strategy pipeline.

## 1. Executive Decision

The highest edge in the current project is not a new indicator. It is the
conversion of the measured six-year volume-bar CVD divergence result into a
state-gated strategy.

Best current evidence:

```text
Diagnostic: volume_bar_cvd
Data: BTCUSDT aggTrades, 133 archives, 3,735,879,540 rows
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

This is the strongest measured signal in the repo. It is materially stronger
than the small trade sweeps, many of which fail badly after conversion into
trades. That means the next edge is not "find more signal." The next edge is:

```text
signal evidence -> auction state filter -> structural location filter
                -> permission sizing -> execution-quality filter
                -> scorecard and ablation
```

V7.6 should be named `EDGE` because its job is to separate real edge from
research noise.

## 2. Evidence Base

### Repo Scale

Current project facts:

- 71 Python files.
- 13 test modules.
- 82 unit tests pass in the repo `.venv`.
- BTCUSDT six-year aggTrades cold dataset exists through hot symlink.
- Cold dataset size is about 51 GB.
- Volume-bar CVD six-year diagnostic completed.
- Footprint F1-F5 six-year shard outputs are placeholders.
- Some sweep files are empty placeholders.
- `scripts/download_status.sh` gives a false missing-data report because it does
  not handle the symlinked cold-storage layout correctly.

### Strong Evidence

Strongest measured signal:

```text
300 BTC volume bars + 40-bar CVD divergence + D4 HTF filter
```

Why it matters:

- It was measured over the full six-year dataset.
- It has 22,506 events, not a tiny sample.
- It has positive hit rate above 53%.
- It has IC above 0.05, materially above the V7.2 0.02 keep threshold.
- It aligns with the market-theory direction: participation bars, divergence,
  and higher-timeframe state filter.

### Weak Evidence

Small trade sweeps show fragility:

- Only two sweep result rows show `dsr_passed=True`.
- Those passing rows are from a limited 2021-11 sample.
- Several 2022-09 and Luna/crash style sweeps are strongly negative.
- Some strategy variants create many trades with very poor win rates.
- CVD exit and swing variants can make results worse, not better.

Conclusion:

```text
The signal exists, but the current conversion layer is weak.
```

V7.6 should focus on conversion quality.

## 3. Highest Edge Thesis

### V7.6 Prime Edge

The highest edge path is:

```text
Event-qualified volume-bar CVD divergence
filtered by HTF state
gated by auction state
confirmed by structural memory
sized by AlphaPermission
executed only when book quality is acceptable
validated by scorecard and ablation
```

### Why This Is Better Than Adding Indicators

Adding another raw indicator would increase feature sprawl. The current
problem is not absence of signals. The current problem is that signals are not
yet routed through enough market context and execution constraints.

The repo already has:

- CVD
- footprint
- delta velocity
- absorption
- VWAP
- VPIN
- volume bars
- L2 features
- whale pressure

The missing layer is selection:

- Which state allows this signal?
- Which structural location makes it worth acting on?
- Which execution environment makes it expressible?
- Which evidence proves it survives costs?

## 4. SWOT Summary

### Strengths

- Deterministic foundation is already strong.
- Tests cover core feature logic and Chunk B behavior.
- Six-year BTCUSDT dataset exists locally.
- Volume-bar CVD diagnostic produced a real candidate edge.
- Data layout and cold/hot storage conventions are documented.
- AlphaPermission already has reason-coded verdicts.
- Backtester supports fees, slippage, Sharpe, and approximate DSR.
- V7.4 and V7.5 blueprints provide a coherent architecture direction.

### Weaknesses

- The best measured signal is not yet integrated into Chunk B.
- Trade conversion from signal to PnL is weak and inconsistent.
- Footprint F1-F5 full-run evidence is missing.
- Research outputs lack formal manifests.
- Some result files are empty or placeholders.
- Execution quality is not a first-class decision layer.
- Current regime labels are too coarse.
- Structural memory is not implemented.
- `download_status.sh` contradicts the dataset manager.
- README quick-start still references the wrong path and plain `python3`.

### Opportunities

- Convert the 300/40/D4 volume-bar CVD result into the first real V7.6 strategy
  candidate.
- Use auction-state gating to avoid trading the signal in bad regimes.
- Use structural memory to improve entry location.
- Use execution filters to avoid valid signals in toxic books.
- Add experiment manifests to stop result drift.
- Add ablation and scorecards to delete weak features.
- Use BTCUSDT as the proof instrument before expanding to ETHUSDT or futures.

### Threats

- Overfitting to the two passing 2021-11 sweep rows.
- Treating IC as directly tradable PnL.
- Letting placeholder results become project lore.
- Building V7.4/V7.5 architecture before finishing Session 5.
- Adding ML before deterministic state labels exist.
- Running expensive full sweeps before fixing manifests and resumability.
- Ignoring execution costs and adverse selection.
- Confusing structural memory with static support/resistance.

## 5. SWOT By Specific Area

## 5.1 Data and Truth Layer

### Strengths

- Canonical cold/hot data layout exists.
- BTCUSDT six-year aggTrades data is present.
- Dataset manager sees the symlinked cold-storage layout.
- Real-data checks can validate selected archives.
- Replay and signing tests exist.

### Weaknesses

- No formal dataset manifest.
- Download status script is stale.
- Full checksum validation is expensive and not summarized into manifests.
- Storage state lives partly in docs and shell history.

### Opportunities

- Add `DatasetManifest` and make it the source of truth.
- Replace `download_status.sh` with a data-manager subcommand.
- Add benchmark metadata for zipped vs unzipped replay.
- Add archive-level row-count and checksum summaries.

### Threats

- False missing-data reports waste time.
- Large file movement can break symlinks.
- Missing manifest makes research hard to reproduce.

### Improvement Priority

High. This is not alpha, but it protects every alpha test.

### V7.6 Actions

1. Add BTCUSDT six-year dataset manifest.
2. Add manifest validation tests.
3. Fix download status to follow symlinks or retire it.
4. Add result manifest for the completed volume-bar CVD run.

## 5.2 Flow Feature Layer

### Strengths

- Broad deterministic feature set exists.
- Feature tests cover major primitives.
- Volume bars are already implemented and tested.
- CVD windows and swing divergence are tested.

### Weaknesses

- No feature registry.
- No universal feature contract.
- Warm-up and reset behavior are not uniformly exposed.
- Not every feature has streaming-vs-batch parity.

### Opportunities

- Build a feature registry with input/output/warm-up/reset/test metadata.
- Add DELETE/KEEP status for each feature after ablation.
- Convert features into evidence streams for AuctionStateEngine.

### Threats

- Feature sprawl.
- Raw indicators used as entries without state context.
- Duplicated APIs if Session 5 is not implemented against existing sampler.

### Improvement Priority

Medium-high. The features are enough; governance is missing.

### V7.6 Actions

1. Add `FeatureContract`.
2. Register CVD, footprint, absorption, VWAP, VPIN, delta velocity, volume bars.
3. Require every strategy dependency to be in the registry.

## 5.3 Volume-Bar CVD Edge

### Strengths

- Best measured signal in the project.
- Full six-year diagnostic completed.
- Strong IC and hit rate for 300/40/D4 at 5-bar horizon.
- Existing sampler/cache reduce implementation risk.

### Weaknesses

- Not yet ported into Chunk B.
- Diagnostic edge is not the same as tradeable edge.
- HTF flat-abs uses archive-level precompute, which is research-valid but needs
  careful live interpretation.
- Current smoke result is too small to matter.

### Opportunities

- Make this the V7.6 flagship edge candidate.
- Turn it into a signal-only scorecard before trading it.
- Gate it with auction state and structural memory.
- Compare D1 only vs D4 HTF vs D5 reversal confirmation.

### Threats

- Overfitting the exact 300/40/0.25 values.
- Misimplementing diagnostic logic and losing edge.
- Permission gating could delete too many good signals.
- Trading all signals without state filters could destroy PnL.

### Improvement Priority

Highest.

### V7.6 Actions

1. Implement Session 5 exactly.
2. Add tests for D1, D4, HTF quantile, and momentum isolation.
3. Add signal-only scorecard for the volume-bar signal before PnL conversion.
4. Run 2022-09 smoke, then 2021-11, 2023-03, 2022-05 stress.
5. Only after signal scorecard passes, connect to trade simulation.

## 5.4 Footprint F1-F5

### Strengths

- Detailed F1-F5 spec exists.
- Unit tests cover stacked imbalance, rejection, absorption, structure, and
  final gate.
- Footprint is conceptually aligned with auction-state confluence.

### Weaknesses

- Six-year shard outputs are placeholders.
- Long-running shard jobs died or were interrupted.
- No completed aggregate footprint scorecard.

### Opportunities

- Use footprint as confirmation for volume-bar edge, not as the first primary
  strategy.
- Complete a smaller shard first to estimate throughput and edge.
- Add shard manifests and checkpointing.

### Threats

- Footprint research can consume compute without producing tradeable edge.
- Placeholder outputs can mislead future work.

### Improvement Priority

Medium. Important, but second to volume-bar CVD.

### V7.6 Actions

1. Mark current shard outputs as placeholders in a result manifest.
2. Add restartable shard runner.
3. Run one known volatile archive before full six-year shards.
4. Use F1-F5 as an auction-state evidence input.

## 5.5 Chunk B Backtester

### Strengths

- Handles synthetic ticks and research ticks.
- Tracks signals, trades, PnL, Sharpe, DSR, win rate, regimes, exits,
  permission counts, MAE, and MFE.
- Has meaningful tests for current behavior.
- Momentum mode stability is tested.

### Weaknesses

- Volume-bar signal path is not wired.
- Signal quality and execution quality are not separated.
- Backtester trades signal output directly through simplified execution.
- No experiment manifest.
- No explicit signal-only scorecard path.

### Opportunities

- Add a two-layer backtest:
  signal evaluation first, trade conversion second.
- Add state-gated signal eligibility.
- Add result manifests automatically.
- Add cost/slippage sensitivity sweeps.

### Threats

- Backtester can make a good signal look bad through poor conversion.
- Backtester can make a bad signal look good on one archive.
- Small sample DSR passes can be overvalued.

### Improvement Priority

Highest after Session 5.

### V7.6 Actions

1. Add signal-only report.
2. Add volume-bar mode.
3. Add experiment manifest output.
4. Add cost sensitivity.
5. Add state and execution gates behind flags.

## 5.6 Regime and Auction State

### Strengths

- Current regime proxy exists.
- V7.4 defines a strong state-machine blueprint.
- Tests exist for current regime behavior.

### Weaknesses

- Current labels are coarse.
- No AuctionStateEngine implementation.
- No state transition hysteresis.
- No anti-flicker tests.

### Opportunities

- Use AuctionStateEngine as the main V7.6 edge filter.
- Start minimal: BALANCED, DISCOVERY, TRENDING, EXHAUSTION, FAILED_AUCTION.
- Only gate the volume-bar signal after synthetic tests pass.

### Threats

- Subjective state definitions can become untestable.
- Too many states too early will slow implementation.
- State filters can overfit by deleting losing examples after the fact.

### Improvement Priority

Very high, but after Session 5 implementation.

### V7.6 Actions

1. Implement minimal synthetic AuctionStateEngine.
2. Add transition tests.
3. Add anti-flicker tests.
4. Use it as an experimental filter on volume-bar CVD.

## 5.7 Structural Memory

### Strengths

- Strong conceptual basis in V7.4/V7.5 docs.
- Existing session high/low and VWAP engines can provide basic memory anchors.
- Failed auction logic aligns with footprint and volume-bar divergence.

### Weaknesses

- No structural memory implementation.
- No object decay.
- No invalidation rules.
- No query API.

### Opportunities

- Start with only three memory objects:
  failed auction level, session VWAP migration, trapped inventory zone.
- Use memory to improve entry location for the volume-bar edge.
- Use memory to block bad trades into nearby structural resistance/support.

### Threats

- Memory can become vague support/resistance if not evidence-coded.
- Persistent state bugs can corrupt backtests.

### Improvement Priority

High, but keep minimal.

### V7.6 Actions

1. Add `StructuralMemoryObject`.
2. Implement failed auction level creation and decay.
3. Add nearest-object query.
4. Gate only after tests.

## 5.8 AlphaPermission and Risk

### Strengths

- Reason-coded permission chain exists.
- Hard deny, approve, reduced verdicts exist.
- Ablation helper exists.
- Current tests cover feed halt, CVD confirmation, VWAP multiplier, and regime.

### Weaknesses

- No auction-state input.
- No structural-memory input.
- No execution-quality input.
- No delay or passive-only verdict.
- Current permission can approve signals in regimes that later prove bad.

### Opportunities

- Add AlphaPermission V2 behind an experimental flag.
- Use auction state and structural memory as major multipliers.
- Add passive-only and delay verdicts.
- Record bottleneck layer and decision trace.

### Threats

- Overcomplicated permission can hide why trades disappear.
- Multipliers can be overfit.

### Improvement Priority

High.

### V7.6 Actions

1. Add typed optional inputs for auction state and memory.
2. Add stable reason-code order tests.
3. Add passive-only/delay only after execution layer exists.
4. Run ablation on each permission multiplier.

## 5.9 Execution Intelligence

### Strengths

- Backtester already models fees and slippage.
- PaperTrade records MAE/MFE and exits.

### Weaknesses

- No book-quality execution decision.
- No queue position model.
- No adverse selection model.
- No spread-state logic.
- No signal-fill dissonance accounting.

### Opportunities

- Add a separate `ExecutionDecision`.
- Track when signal is good but execution is bad.
- Use L2 features when available; use explicit `BOOK_UNKNOWN` when unavailable.
- Add spread/thin-book/toxic-book synthetic tests.

### Threats

- A good strategy can fail live through bad fills.
- A backtest can hide fill assumptions.

### Improvement Priority

High, but after signal/state gating.

### V7.6 Actions

1. Add execution decision contract.
2. Add delay/skip/passive-only simulation.
3. Add fill-quality scorecard.
4. Separate signal IC from trade PnL.

## 5.10 Research Outputs and Manifests

### Strengths

- Many result files exist.
- Volume-bar 6-year result is valuable.
- Sweep files preserve research history.

### Weaknesses

- No formal result manifest.
- Empty files exist.
- Placeholder shard outputs exist.
- Commands and git commits are not tied to results.

### Opportunities

- Add `ExperimentManifest` and `ResultManifest`.
- Add placeholder detection.
- Require manifests for cited results.
- Make sweeps reproducible and comparable.

### Threats

- Result drift.
- Citing stale or interrupted outputs.
- Overweighting small positive sweeps.

### Improvement Priority

High. It prevents false edge.

### V7.6 Actions

1. Create manifest for `volume_bar_cvd_6y.json`.
2. Mark footprint shards as placeholders.
3. Mark empty sweep files as placeholders or rerun/delete.
4. Add manifest generation to sweep scripts.

## 5.11 Tests

### Strengths

- 82 tests pass.
- Tests cover many core primitives.
- Momentum-path unchanged test is valuable.

### Weaknesses

- No tests for V7.4/V7.5 concepts yet.
- No result manifest tests.
- No experiment reproducibility tests.
- No execution-state tests.

### Opportunities

- Add tests before each new layer.
- Make anti-flicker tests mandatory.
- Add cost sensitivity and leakage tests.

### Threats

- Architecture docs can outrun test coverage.
- Complex state systems without tests become subjective.

### Improvement Priority

Highest as an enabling layer.

### V7.6 Actions

1. Add Session 5 tests.
2. Add minimal AuctionStateEngine tests.
3. Add manifest tests.
4. Add placeholder result detection test.
5. Add state flicker tests.

## 5.12 UI, Orchestration, and ML

### Strengths

- UI/orchestration are correctly kept out of hot path.
- V7.5 defines UI as visibility, not alpha computation.

### Weaknesses

- UI is placeholder only.
- Orchestration is placeholder only.
- ML has no deterministic label framework yet.

### Opportunities

- Later UI can display state, permission, memory, and execution decisions.
- ML can later calibrate state confidence or execution slippage.

### Threats

- UI or ML too early will distract from edge validation.
- ML before leakage tests creates false confidence.

### Improvement Priority

Low for V7.6.

### V7.6 Actions

- Do not build UI or ML in V7.6 except schema preparation.

## 6. Highest Edge Ranking

### Rank 1: Volume-Bar CVD D4 HTF Strategy Candidate

Evidence: strongest six-year result.

Impact: very high.

Effort: medium.

Confidence: high relative to other current options.

Action:

- Port Session 5 exactly.
- Preserve diagnostic logic.
- Build signal-only scorecard.
- Then convert to trade strategy.

### Rank 2: Auction-State Filter For The Volume-Bar Signal

Evidence: trade sweeps show conversion weakness; state gating can avoid bad
contexts.

Impact: high.

Effort: medium-high.

Confidence: medium-high.

Action:

- Implement minimal state engine.
- Gate volume-bar signal only after tests.
- Compare signal performance before/after state filter.

### Rank 3: Structural Memory Lite

Evidence: DeepSeek/Claude discussion and market-theory alignment; current
system lacks path dependence.

Impact: high if kept minimal.

Effort: medium.

Confidence: medium.

Action:

- Start with failed auction levels and session VWAP migration.
- Use only as location filter.
- Add decay and invalidation.

### Rank 4: Execution Quality Filter

Evidence: current backtests model costs but not fill quality; execution can
erase edge.

Impact: high for live readiness.

Effort: medium-high.

Confidence: medium.

Action:

- Add execution decision layer.
- Track signal-valid/book-bad cases.
- Do not overfit without L2 data.

### Rank 5: Research Manifests and Scorecards

Evidence: current result files include placeholders and empty outputs.

Impact: high on research quality.

Effort: low-medium.

Confidence: high.

Action:

- Add manifests now.
- Require scorecards for every claim.

### Rank 6: Footprint F1-F5 As Confluence

Evidence: spec and tests exist, full-run evidence missing.

Impact: medium-high if used as confluence.

Effort: high.

Confidence: medium.

Action:

- Complete small shard first.
- Do not prioritize above volume-bar CVD.

### Rank 7: Multi-Symbol Expansion

Evidence: not yet needed.

Impact: high later.

Effort: high.

Confidence: low until BTCUSDT edge conversion works.

Action:

- Defer until V7.6 candidate passes on BTCUSDT.

## 7. V7.6 Strategy Blueprint

### Strategy Name

```text
VolumeBarCVDStateEdge
```

### Signal Thesis

Large-participation volume bars reveal when price extension and cumulative delta
disagree. The D4 HTF filter removes low-quality divergence contexts. Auction
state and structural memory decide whether the divergence is a valid exhaustion
or failed-auction opportunity.

### Required Inputs

- VolumeBarSampler output
- cumulative delta per volume bar
- D1 divergence
- D4 HTF filter
- auction state snapshot
- structural memory query
- AlphaPermission verdict
- execution decision

### Initial Rules

```text
1. Build 300 BTC volume bars.
2. Detect 40-bar D1 divergence.
3. Apply D4 HTF filter matching diagnostic logic.
4. Require auction state in EXHAUSTION, FAILED_AUCTION,
   RESPONSIVE_BUYING, or RESPONSIVE_SELLING.
5. Require no structural memory conflict.
6. Feed signal to AlphaPermission.
7. If execution state is toxic, delay or skip.
8. Record signal-only score and trade-converted score separately.
```

### Initial Hard Denies

- Feed quality halt.
- Unknown data quality.
- State is INITIATIVE_TREND against fade direction.
- State flicker detected.
- Structural memory conflict directly ahead.
- Execution state toxic.
- Signal appears during low participation unless explicitly classified as
  liquidation event.

### Initial Scorecard

```text
signals_seen
signals_after_state_filter
signals_after_memory_filter
signals_after_permission
signals_after_execution
trades
hit_rate_signal_only
hit_rate_trade_converted
IC_signal_only
mean_sfr_signal_only
net_pnl
win_rate
sharpe
deflated_sharpe_probability
max_drawdown
MAE
MFE
permission_counts
execution_counts
state_counts
filter_drop_reason_counts
```

## 8. V7.6 Phased Implementation

### Phase 0: Repo Hygiene and Manifests

Goal: remove friction and false state.

Tasks:

- Fix README quick-start.
- Fix or replace download status.
- Add dataset manifest.
- Add result manifest for volume-bar CVD six-year diagnostic.
- Mark empty and placeholder results.

Exit gate:

- `.venv/bin/python -m unittest` passes.
- Dataset manager and status agree.
- Result manifest identifies completed vs placeholder results.

### Phase 1: Session 5 Volume-Bar Port

Goal: make the best measured signal executable in Chunk B.

Tasks:

- Add `VolumeBarCVDConfluenceEngine`.
- Add `use_volume_bar_signal`.
- Add `volume_bar_threshold`, `cvd_lookback_bars`, `htf_flat_quantile`.
- Add sweep flags.
- Add tests.
- Run smoke.

Exit gate:

- Momentum mode unchanged.
- D1/D4 tests pass.
- Smoke run reports whether blocker is signal, permission, or execution.

### Phase 2: Signal-Only Scorecard

Goal: avoid confusing signal quality with trade conversion.

Tasks:

- Add signal-only scoring to volume-bar mode.
- Report IC/hit rate before permission and after filters.
- Compare D1 vs D4 vs D5.

Exit gate:

- Signal-only scorecard reproduces diagnostic direction.
- Trade conversion does not obscure raw signal behavior.

### Phase 3: Minimal Auction State

Goal: add state gating without building the full V7.4 machine.

States:

```text
BALANCED
DISCOVERY
TRENDING
EXHAUSTION
FAILED_AUCTION
RESPONSIVE
```

Tasks:

- Add synthetic transition tests.
- Add anti-flicker hysteresis.
- Add state confidence.
- Add reason codes.

Exit gate:

- State transitions are deterministic.
- State filter improves or safely reduces the volume-bar signal candidate.

### Phase 4: Structural Memory Lite

Goal: add path dependence without overbuilding.

Objects:

- failed auction level
- session VWAP migration
- trapped inventory zone

Tasks:

- Add decay.
- Add invalidation.
- Add nearest-object query.
- Add location filter for volume-bar signal.

Exit gate:

- Memory tests pass.
- Memory filter improves risk-adjusted score or remains disabled.

### Phase 5: AlphaPermission V2 Experimental

Goal: route state and memory through permission.

Tasks:

- Add optional state input.
- Add optional memory input.
- Add stable reason chain.
- Add filter-drop accounting.

Exit gate:

- Permission chain remains explainable.
- Ablation shows state/memory multipliers add value.

### Phase 6: Execution Filter

Goal: separate valid signals from bad fills.

Tasks:

- Add `ExecutionDecision`.
- Add `BOOK_UNKNOWN`.
- Add passive-only/delay/skip decisions.
- Add execution counts to scorecard.

Exit gate:

- Execution filter is measured separately.
- It reduces bad fill exposure without deleting all edge.

### Phase 7: Cross-Regime Validation

Goal: prevent 2021-11 overfit.

Archives:

```text
BTCUSDT-aggTrades-2021-11.zip
BTCUSDT-aggTrades-2022-05.zip
BTCUSDT-aggTrades-2022-09.zip
BTCUSDT-aggTrades-2023-01.zip
BTCUSDT-aggTrades-2023-03.zip
```

Exit gate:

- Candidate does not collapse outside the discovery archive.
- Losing regimes are identified with reason codes.

### Phase 8: Full Six-Year Revalidation

Goal: prove V7.6 edge survives after filters and costs.

Tasks:

- Shard full run.
- Manifest every shard.
- Aggregate scorecard.
- Ablate state, memory, permission, execution filters.

Exit gate:

- Out-of-sample or chronological validation passes after fees and slippage.
- Ablation supports keeping each added layer.

## 9. What Not To Do In V7.6

Do not:

- add ML
- build UI
- expand to many symbols
- optimize on the two positive sweep rows
- trade footprint F1-F5 before completing evidence
- implement full structural memory before memory-lite
- claim live readiness
- add another raw indicator
- run more full sweeps without manifests
- skip signal-only scorecards

## 10. V7.6 Test Plan

Immediate high-value tests:

```text
test_volume_bar_cvd_detects_bearish_d1
test_volume_bar_cvd_detects_bullish_d1
test_htf_flat_abs_matches_diagnostic_quantile
test_htf_blocks_disagreeing_direction
test_chunkb_momentum_unchanged_with_volume_bar_flag_off
test_chunkb_volume_bar_signal_smoke_synthetic
test_dataset_status_follows_symlink
test_result_manifest_marks_placeholder_outputs
test_auction_state_no_flicker
test_delta_efficiency_absorption_vs_initiative
test_failed_auction_memory_decay
test_alpha_permission_state_gate_reason_codes
test_execution_decision_toxic_book_delays_entry
```

Minimum test command:

```bash
.venv/bin/python -m unittest
```

Smoke command target after Session 5:

```bash
.venv/bin/python scripts/chunk_b_sweep.py \
  --archive BTCUSDT-aggTrades-2022-09.zip \
  --max-rows 500000 \
  --signal-mode divergence \
  --use-volume-bar-signal \
  --volume-bar-threshold 300 \
  --cvd-lookback-bars 40 \
  --htf-flat-quantile 0.25
```

## 11. V7.6 Scorecard Standard

Every V7.6 claim must include:

```text
git_commit
dataset_manifest
experiment_manifest
command
rows_seen
archives_processed
signal_count
trade_count
state_counts
filter_drop_counts
gross_pnl
net_pnl
fees
slippage
hit_rate
IC
mean_sfr
win_rate
sharpe
deflated_sharpe_probability
max_drawdown
MAE
MFE
ablation_keep_delete
```

No scorecard, no edge claim.

## 12. V7.6 Promotion Gates

V7.6 becomes active only when:

- Current 82-test suite remains green.
- Session 5 volume-bar CVD is implemented and tested.
- Signal-only scorecard reproduces the six-year diagnostic direction.
- Trade-converted scorecard improves after state/memory/execution filters.
- Result and dataset manifests exist.
- Placeholder outputs are resolved or marked.
- Minimal AuctionStateEngine passes anti-flicker tests.
- Structural memory lite passes decay/invalidation tests.
- AlphaPermission reason chain includes state and memory.
- ExecutionDecision separates signal quality from fill quality.
- Cross-regime validation does not collapse.
- Full six-year revalidation passes after fees and slippage.
- Ablation proves V7.6 layers add value over raw D4 volume-bar CVD.

## 13. Final Recommendation

The best edge path is not broad. It is narrow and disciplined:

```text
Finish Session 5.
Protect the 300/40/D4 volume-bar CVD edge.
Add signal-only scorecards.
Gate with minimal auction state.
Add structural memory lite.
Add execution filter.
Run cross-regime validation.
Only then run full six-year revalidation.
```

If this works, V7.6 becomes the first version with a real edge pipeline:

```text
measured signal -> state selection -> location filter -> permission -> execution
                -> scorecard -> ablation -> promotion
```

That is the highest-edge direction available from the current project.
