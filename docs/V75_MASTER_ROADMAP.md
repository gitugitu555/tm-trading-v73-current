# TM Trading System V7.5 Master Roadmap

Version: `7.5.0-MASTER`

Status: strategic roadmap; not yet the active implementation target.

Active build target remains: V7.2 Nautilus-Prime.

V7.4 blueprint target: AuctionStateEngine and market-theory orchestration.

V7.5 target: turn the project into a deterministic research and execution
operating system where every signal, state, permission, execution decision, and
learning loop is auditable, replayable, ablated, and promoted only after proof.

## 1. Executive Summary

V7.5 should not be "more indicators." It should be the system that prevents bad
indicators, bad state labels, bad fills, and bad research habits from reaching
production logic.

The big jump:

```text
V7.2 = deterministic feature and Chunk B research scaffold
V7.4 = auction-state orchestration blueprint
V7.5 = full research operating system with state, memory, permission,
       execution, validation, ablation, and learning governance
```

The system should become a closed loop:

```text
truth -> flow -> auction state -> structural memory -> strategy eligibility
      -> permission -> execution decision -> paper/live result -> ablation
      -> scorecard -> promotion/delete decision -> updated roadmap
```

V7.5 is successful only if it makes the project harder to fool.

## 2. Source Material Consolidated

This roadmap consolidates:

- V7.2 active spec and Chunk B direction.
- Session 5 volume-bar CVD confluence plan.
- V7.4 AuctionStateEngine blueprint.
- V555 three-phase build plan.
- V555 build order and Rule Zero.
- V7.2 Nautilus-Prime patch notes.
- Data layout, project roadmap, project log, and lessons learned.
- Existing unit test coverage across feature engines, replay, memory,
  AlphaPermission, Chunk B, volume bars, and data management.
- DeepSeek and Claude discussion themes: auction market theory, initiative vs
  responsive activity, structural memory, delta efficiency, liquidity events,
  confidence decay, and execution alpha.

## 3. Current Repo State

### Implemented Foundations

The repo already has strong deterministic foundations:

- signed trade logic
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
- replay validator with stable checksums
- AlphaPermission with reason-coded decisions
- Nautilus compatibility layer and no-trade boundary
- Chunk B deterministic backtester
- volume-bar sampler
- volume-bar cache
- data layout helpers and Binance dataset manager
- 6-year BTCUSDT aggTrades cold-storage workflow

### Existing Test Coverage

Current tests cover:

- config hash and logging stability
- Binance buyer-is-maker signing, Lee-Ready fallback, BVC mid split
- CVD, footprint, delta, VPIN, microprice, L2 imbalance, absorption
- spoofing, iceberg, whale pressure
- replay determinism
- AlphaPermission reason codes
- memory export serialization
- Nautilus boundary no-trade behavior
- V7.2 Phase 0 data foundation and quality firewall
- V7.2 Phase 1 CVD windows, swing divergence, session extremes, VWAP,
  IC gate, collinearity
- Chunk B regime proxy, permission chain, synthetic trend backtest, divergence
  mode, swing divergence, session extreme gates, CVD confirmation, CVD exit,
  CVD quantile filter, momentum-path stability
- Footprint F1-F5 research primitives
- VolumeBarSampler and volume_bar_cache
- dataset path helpers

This is enough to build V7.5 incrementally. It is not enough to claim live
readiness.

### Known Gaps

The important gaps are not cosmetic:

- Session 5 volume-bar confluence is documented but not ported into Chunk B.
- Footprint F1-F5 six-year shard outputs are placeholders, not completed
  research outputs.
- `scripts/download_status.sh` does not correctly reflect the symlinked
  cold-storage layout.
- README quick-start still points at `/home/sam` and `python3`, while the
  working tested environment is the repo `.venv`.
- Empty sweep result files exist and should be replaced with real results or
  documented as intentionally empty.
- The regime layer is still coarse compared with the V7.4 market-theory target.
- AlphaPermission does not yet ingest auction state, structural memory, or
  execution quality.
- Execution intelligence is not a first-class layer.
- Dataset manifests and experiment manifests are not yet formalized.
- There is no complete promotion/deletion governance for features.

## 4. V7.5 Core Laws

V7.5 should enforce these laws:

1. No signal enters a strategy without a contract test.
2. No strategy enters a backtest without a replay manifest.
3. No backtest result is trusted without fees, slippage, and reproducibility.
4. No feature survives without ablation evidence.
5. No state transition is accepted without hysteresis or event proof.
6. No trade is valid unless signal quality and execution quality both pass.
7. No live path depends on UI, LLMs, vector DBs, n8n, or non-deterministic
   services.
8. No structural memory object persists without decay and invalidation rules.
9. No ML is introduced before deterministic labels, leakage tests, and
   walk-forward validation exist.
10. No roadmap item is complete until it has tests, docs, and a promotion gate.

## 5. Strategic Thesis

The main improvement is not a new alpha. The main improvement is building a
system that can decide which alpha is allowed to exist in which market state.

The system should stop doing this:

```text
CVD high + footprint stacked + VWAP deviation -> entry
```

It should do this:

```text
1. Is the feed valid?
2. What auction state is active?
3. Is activity initiative or responsive?
4. Has price accepted or rejected value?
5. What structural memory objects are nearby?
6. Which strategy classes are eligible in this state?
7. Does flow confirm the strategy thesis?
8. Is the book clean enough to execute?
9. What size is allowed?
10. What evidence will later prove this feature should stay or be deleted?
```

That shift makes the project institutional: it models market behavior, not
indicator coincidence.

## 6. V7.5 Architecture

Recommended high-level architecture:

```text
PHASE 0  Truth Layer
PHASE 1  Flow Layer
PHASE 2  Book Intelligence Layer
PHASE 3  Derived State Features
PHASE 4  Auction State Engine
PHASE 5  Structural Memory Vault
PHASE 6  Regime and Strategy Eligibility Engine
PHASE 7  AlphaPermission V2
PHASE 8  Execution Intelligence
PHASE 9  Research Store and Experiment Manifests
PHASE 10 Validation, Ablation, and Scorecards
PHASE 11 Operator UI and Review
PHASE 12 Learning Layer
```

The implementation rule is sequential: do not build Phase 8 before Phases 0-7
are deterministic and tested.

## 7. Phase 0: Truth Layer

### Goal

Make raw market data signed, auditable, immutable, and easy to replay across
symbols and feed types.

### Current Assets

- `features/trade_signing.py`
- `data/quality/firewall.py`
- `data/replay/validator.py`
- `prime/phase0.py`
- `scripts/phase1_realdata_check.py`
- `storage/dataset_layout.py`
- `scripts/binance_data_manager.py`
- `docs/DATA_LAYOUT.md`

### Improvements

- Add dataset manifests for every raw dataset.
- Include source URL pattern, symbol, market, kind, date range, checksums,
  file count, byte count, and verification timestamp.
- Add manifest validation to the data manager.
- Add an explicit hot-cache/cold-storage health command.
- Fix `download_status.sh` or replace it with the data manager status path.
- Add benchmark metadata: zipped parse time, unzipped parse time, HDD, NVMe,
  CPU parse cost.

### Suggested Contracts

```python
class DatasetManifest:
    exchange: str
    market: str
    kind: str
    symbol: str
    range_label: str
    files_expected: int
    files_present: int
    checksums_verified: bool
    total_bytes: int
    source: str
    created_at: str
```

### Tests To Add

- manifest round-trip JSON
- missing archive detection
- checksum mismatch detection with small fixture
- symlinked hot path status
- cold path status
- no raw data writes inside repo when cold root is configured

### Promotion Gate

Truth Layer is V7.5-ready when a fresh clone can validate dataset manifests
without relying on tribal knowledge or shell history.

## 8. Phase 1: Flow Layer

### Goal

Keep raw flow engines deterministic, small, and replaceable.

### Current Assets

- CVD
- footprint
- absorption
- delta velocity
- VWAP
- VPIN
- whale and large-print logic
- volume bars
- footprint F1-F5 research utilities

### Improvements

- Create a feature registry listing every feature, input type, output type,
  warm-up period, reset behavior, and test file.
- Add streaming-vs-batch parity tests for every feature that can be computed in
  batch.
- Add explicit feature invalidation rules.
- Add "DELETE candidate" tracking for weak features.
- Make warm-up behavior visible in every feature output.

### Suggested Contracts

```python
class FeatureContract:
    name: str
    version: str
    inputs: tuple[str, ...]
    output_schema: str
    warmup_ticks: int
    reset_policy: str
    deterministic: bool
    test_module: str
```

```python
class FlowEvidence:
    timestamp_ns: int
    feature_name: str
    value: float | str | dict
    confidence: float
    reason_codes: tuple[str, ...]
```

### Tests To Add

- feature registry includes every feature module
- every feature has at least one test reference
- warm-up not initialized before required samples
- reset behavior is deterministic
- streaming output equals batch output on fixture data

### Promotion Gate

No feature may be used by AuctionStateEngine unless it appears in the registry
with deterministic tests.

## 9. Phase 2: Book Intelligence Layer

### Goal

Separate trade-flow evidence from book-quality evidence.

### Current Assets

- microprice
- L2 imbalance
- spoofing
- iceberg detection
- whale pressure

### Improvements

- Add a `BookStateSnapshot` object.
- Track spread state, depth state, imbalance, microprice deviation, spoof risk,
  iceberg evidence, and book toxicity.
- Make book quality a gate for execution, not just a feature for signal
  generation.
- Add test fixtures for clean book, thin book, spoofed book, crossed book, and
  stale book.

### Suggested Contracts

```python
class BookStateSnapshot:
    timestamp_ns: int
    spread_bps: float
    top_depth_base: float
    imbalance: float
    microprice_deviation: float
    spoof_risk: float
    iceberg_score: float
    toxicity_score: float
    executable: bool
    reason_codes: tuple[str, ...]
```

### Tests To Add

- clean book is executable
- crossed book hard-denies
- stale book hard-denies
- high spoof risk forces passive-only or deny
- thin book reduces size

### Promotion Gate

Execution code cannot consume a trade signal without a `BookStateSnapshot` or an
explicit `BOOK_UNKNOWN` reason code.

## 10. Phase 3: Derived State Features

### Goal

Build features that explain auction behavior, not just raw indicator values.

### Required Derived Features

- delta efficiency
- acceptance/rejection score
- effort-vs-result score
- liquidity event score
- trend exhaustion score
- responsive absorption score
- initiative displacement score
- confidence decay

### Delta Efficiency

```text
delta_efficiency = abs(price_change) / max(abs(cvd_change), epsilon)
```

Interpretation:

- high efficiency + aligned CVD: initiative control
- low efficiency + high CVD: absorption
- high efficiency + divergent CVD: thin-book displacement or hidden liquidity
- low efficiency + divergent CVD: no conviction

### Acceptance/Rejection Score

Inputs:

- range extension beyond prior value
- time spent outside value
- close location
- snapback speed
- VWAP reclaim/rejection
- volume at extension
- follow-through

Output:

```text
-1.0 = strong rejection
 0.0 = unresolved
 1.0 = strong acceptance
```

### Liquidity Event Detector

Detect:

- stop run
- liquidation cascade
- liquidity vacuum
- forced unwind
- thin-book acceleration

### Tests To Add

- high CVD/no movement -> absorption classification
- high CVD/large movement -> initiative classification
- breakout with fast return -> rejection
- breakout with hold and follow-through -> acceptance
- cascade fixture -> liquidity event
- stale event confidence decays

### Promotion Gate

Derived features must prove better explanatory power than raw CVD/footprint
alone in ablation.

## 11. Phase 4: AuctionStateEngine

### Goal

Make auction state the orchestration layer above indicators.

### Required States

```text
BALANCED
DISCOVERY
TRENDING
EXHAUSTION
FAILED_AUCTION
SHORT_COVERING
LONG_LIQUIDATION
RESPONSIVE_BUYING
RESPONSIVE_SELLING
```

### V7.5 Improvement Over V7.4

V7.4 defines the market-theory blueprint. V7.5 adds governance:

- state transition contracts
- hysteresis
- minimum dwell time
- event-based override rules
- state confidence decay
- transition reason codes
- replay stability checks
- ablation against simpler regime labels

### Suggested Contracts

```python
class AuctionStateSnapshot:
    timestamp_ns: int
    label: str
    confidence: float
    previous_label: str | None
    transition: str | None
    initiative_score: float
    responsive_score: float
    acceptance_score: float
    rejection_score: float
    exhaustion_score: float
    liquidity_event_score: float
    reason_codes: tuple[str, ...]
```

```python
class StateTransitionRule:
    from_state: str
    to_state: str
    min_confidence: float
    min_dwell_ns: int
    required_evidence: tuple[str, ...]
    override_event: str | None
```

### Tests To Add

- balanced -> discovery requires range expansion and acceptance
- balanced -> failed auction requires rejection
- discovery -> trending requires continued acceptance
- trending -> exhaustion requires efficiency decay and absorption
- exhaustion -> responsive buying/selling requires snapback evidence
- liquidity event can override dwell time
- state does not flicker on alternating ticks
- replaying the same fixture gives identical transition timestamps

### Promotion Gate

AuctionStateEngine is enabled only after synthetic transition tests and one real
data replay show stable state coverage without pathological flicker.

## 12. Phase 5: Structural Memory Vault

### Goal

Persist path-dependent market structures with decay, reinforcement, and
invalidation.

### Required Objects

- failed auction level
- trapped inventory zone
- HVN
- LVN
- liquidation cascade zone
- iceberg detection zone
- session VWAP deviation object
- unfinished auction
- prior day/session value area

### Suggested Contracts

```python
class StructuralMemoryObject:
    object_id: str
    kind: str
    price_low: float
    price_high: float
    first_seen_ts_ns: int
    last_touched_ts_ns: int
    strength: float
    confidence: float
    decay_half_life_ns: int
    invalidation_rule: str
    reason_codes: tuple[str, ...]
```

```python
class StructuralMemoryQuery:
    timestamp_ns: int
    price: float
    side: int
    max_distance_bps: float
    object_kinds: tuple[str, ...]
```

### Improvements

- Store memory as deterministic JSON/parquet snapshots.
- Keep memory separate from semantic memory.
- Do not let memory become vague "support/resistance."
- Every object needs creation evidence, decay, reinforcement, and invalidation.
- Strategy logic queries memory; it does not mutate it directly.

### Tests To Add

- failed auction object is created on rejected breakout
- repeated retest reinforces strength
- stale object decays
- invalidated object is removed or marked inactive
- nearest object query is deterministic
- memory replay round-trip preserves object state

### Promotion Gate

Structural memory can affect permission only after invalidation tests exist.

## 13. Phase 6: Regime and Strategy Eligibility Engine

### Goal

Separate "what state is the market in" from "which strategies may act."

### Required Regimes

```text
BALANCED_ROTATION
INITIATIVE_TREND
EXHAUSTED_TREND
VOLATILE_DISCOVERY
LIQUIDATION_EVENT
FAILED_BREAKOUT
MEAN_REVERSION
LOW_PARTICIPATION
```

### Strategy Classes

```text
MOMENTUM_CONTINUATION
PULLBACK_CONTINUATION
BREAKOUT_CONTINUATION
DIVERGENCE_FADE
FAILED_AUCTION_FADE
MEAN_REVERSION_TO_VALUE
LIQUIDATION_PLAYBOOK
NO_TRADE
```

### Eligibility Matrix

| Regime | Eligible Classes | Locked Out |
| --- | --- | --- |
| BALANCED_ROTATION | Mean reversion, range fade | Breakout without acceptance |
| INITIATIVE_TREND | Momentum, pullback | Counter-trend fade |
| EXHAUSTED_TREND | Divergence fade, reduce trend | Add-on continuation |
| VOLATILE_DISCOVERY | Breakout continuation | Mean reversion |
| LIQUIDATION_EVENT | Liquidation playbook only | Ordinary trend/range logic |
| FAILED_BREAKOUT | Failed auction fade | Breakout continuation |
| MEAN_REVERSION | Return-to-value | Momentum chase |
| LOW_PARTICIPATION | No trade | All entries |

### Tests To Add

- every regime maps to at least one explicit strategy class
- locked-out class returns a reason code
- unknown state maps to no trade or reduced confidence
- strategy class cannot bypass regime eligibility

### Promotion Gate

Chunk B and future strategies cannot call AlphaPermission directly without a
strategy eligibility verdict.

## 14. Phase 7: AlphaPermission V2

### Goal

Make AlphaPermission a complete evidence chain:

```text
feed quality -> regime -> auction state -> structural memory -> flow
             -> L2 quality -> context -> execution constraints -> verdict/size
```

### Current Assets

- `prime/phase5_chunkb.py`
- reason-coded multiplier chain
- approve/reduced/hard-deny verdicts
- ablation helper

### Improvements

- Add typed inputs for auction state, structural memory, book state, and
  execution state.
- Add delay verdict, not only approve/reduced/hard-deny.
- Add passive-only verdict for execution.
- Record bottleneck layer.
- Record feature contributions and deleted features.
- Keep raw strength separate from permission-adjusted KQ.

### Suggested Verdicts

```text
APPROVE
REDUCED
DELAY
PASSIVE_ONLY
HARD_DENY
```

### Suggested Reason Code Layers

```text
FEED_VALIDITY
MARKET_REGIME
AUCTION_STATE
STRUCTURAL_MEMORY
FLOW_CONFIRMATION
BOOK_QUALITY
CONTEXT_MULTIPLIER
EXECUTION_CONSTRAINT
RISK_LIMIT
```

### Tests To Add

- feed halt hard-denies before all other logic
- unknown auction state reduces or denies
- structural conflict denies location
- book toxicity returns passive-only or delay
- execution constraint can reduce size after signal approval
- reason chain order is stable
- ablation deletes weak multiplier

### Promotion Gate

No strategy can place an order unless AlphaPermission returns a stable
reason-coded verdict with input and output hashes.

## 15. Phase 8: Execution Intelligence

### Goal

Separate signal quality from fill quality.

### Required Concepts

- spread state
- queue position estimate
- adverse selection risk
- passive vs aggressive routing decision
- slippage expectation
- book toxicity
- time-in-force logic
- cancel/replace policy

### Suggested Contracts

```python
class ExecutionDecision:
    timestamp_ns: int
    signal_id: str
    action: str
    order_type: str | None
    size_scalar: float
    limit_price: float | None
    max_slippage_bps: float
    reason_codes: tuple[str, ...]
```

Actions:

```text
TAKE
POST
PASSIVE_ONLY
DELAY
SKIP
CANCEL
REDUCE
```

### Improvements

- Add execution simulation separate from signal backtest.
- Track realized slippage and adverse excursion after fill.
- Add TCA logs.
- Add "good signal, bad book" accounting.
- Add queue-position assumptions explicitly.

### Tests To Add

- wide spread forces passive-only or skip
- toxic book delays entry
- thin book reduces size
- strong signal + clean book permits normal execution
- execution decision does not alter signal evidence

### Promotion Gate

Paper trading cannot be promoted until execution decision logs show that fill
quality is measured separately from signal quality.

## 16. Phase 9: Research Store and Experiment Manifests

### Goal

Make every experiment reproducible and comparable.

### Required Manifests

- dataset manifest
- feature config manifest
- strategy config manifest
- backtest manifest
- result manifest
- environment manifest

### Suggested ExperimentManifest

```python
class ExperimentManifest:
    experiment_id: str
    git_commit: str
    dataset_manifest_id: str
    strategy_name: str
    config_hash: str
    start_ts_ns: int
    end_ts_ns: int
    fees_bps: float
    slippage_bps: float
    random_seed: int | None
    command: str
    output_path: str
```

### Improvements

- Stop relying on ad hoc sweep JSON file names.
- Add `results/manifest.jsonl` or a SQLite/Postgres research store.
- Make every sweep resumable and shardable.
- Mark placeholder or interrupted outputs explicitly.
- Add "do not commit huge derived cache unless justified" policy.

### Tests To Add

- manifest hash stable
- result manifest points to existing output
- interrupted run writes partial status
- completed run marks complete
- config changes alter hash

### Promotion Gate

No result is cited in docs unless it has a manifest and a reproducible command.

## 17. Phase 10: Validation, Ablation, and Scorecards

### Goal

Build the feature deletion machine.

### Required Validation Modes

- synthetic unit tests
- sample real-data smoke tests
- single-archive integration tests
- cross-regime validation
- walk-forward validation
- out-of-sample holdout
- ablation
- permutation/shuffle sanity checks
- leakage tests
- cost sensitivity
- slippage sensitivity

### Scorecard

Every strategy and feature should have:

```text
events
trades
hit_rate
mean_signed_forward_return
IC
gross_pnl
net_pnl
win_rate
sharpe
deflated_sharpe_probability
max_drawdown
turnover
fee_sensitivity
slippage_sensitivity
state_coverage
ablation_keep_delete
```

### Delete Rules

Delete or quarantine a feature if:

- it fails deterministic tests
- it only works before costs
- it fails out-of-sample
- it flips sign across regimes without explanation
- it adds no value in ablation
- it creates state flicker
- it improves entries but damages execution quality

### Tests To Add

- ablation report emits KEEP/DELETE
- cost sensitivity can flip a strategy from keep to delete
- leakage detector catches future-looking fields
- walk-forward split is chronological
- state coverage report includes no-trade periods

### Promotion Gate

Nothing reaches default-enabled status without a scorecard and ablation result.

## 18. Phase 11: Operator UI and Review

### Goal

Give visibility without letting the UI compute alpha.

### UI Should Display

- current auction state
- state transition history
- structural memory objects
- AlphaPermission chain
- execution decision
- risk state
- replay controls
- CVD/footprint/VWAP panels
- signal vs fill quality
- scorecards

### UI Must Not Do

- compute signals
- mutate strategy state
- bypass permission
- place orders directly
- silently edit research results

### Tests To Add Later

- API returns stable snapshot schema
- UI renders no-trade state
- UI shows reason-code chain
- replay controls do not mutate raw data

### Promotion Gate

UI is allowed only after the backend has stable snapshot APIs.

## 19. Phase 12: Learning Layer

### Goal

Use learning only after deterministic labels and validation exist.

### Allowed Learning Targets

- strategy score calibration
- state confidence calibration
- execution slippage estimation
- feature weighting suggestions
- anomaly detection
- setup retrieval from structural memory

### Forbidden Early ML Targets

- raw entry decisions
- hidden state labels without deterministic ground truth
- live sizing without risk gate
- self-modifying strategy logic

### Required Before ML

- triple-barrier labels
- leakage detector
- walk-forward framework
- feature registry
- experiment manifests
- scorecards
- ablation reports

### Promotion Gate

ML cannot enter AlphaPermission until it improves out-of-sample after fees and
slippage and passes leakage tests.

## 20. Concrete Next Work

Do these in order.

### Step 1: Clean Current Repo Friction

- Fix README quick-start to use the actual repo path and `.venv`.
- Fix or replace `scripts/download_status.sh`.
- Mark empty sweep files as placeholders or replace with real outputs.
- Add a dataset manifest for BTCUSDT six-year aggTrades.
- Add a result manifest for `results/volume_bar_cvd_6y.json`.

### Step 2: Finish Session 5

- Implement `VolumeBarCVDConfluenceEngine`.
- Add `use_volume_bar_signal` config to Chunk B.
- Add sweep flags.
- Add tests from Session 5.
- Run the 2022-09 smoke test.
- Keep momentum mode unchanged.

### Step 3: Complete Footprint F1-F5 Evidence

- Replace placeholder shard outputs with completed shard results or delete them.
- Add run manifest for each shard.
- Add interruption/resume tracking.
- Add aggregate result builder.

### Step 4: Minimal V7.4 Engine

- Add synthetic-only AuctionStateEngine.
- Add delta efficiency.
- Add acceptance/rejection scoring.
- Add state transition tests.
- Do not connect to strategies yet.

### Step 5: Minimal V7.5 Governance

- Add feature registry.
- Add experiment manifest.
- Add result manifest.
- Add scorecard schema.
- Add ablation report schema.

### Step 6: Strategy Eligibility

- Add strategy-class enum.
- Add regime/state eligibility matrix.
- Make Chunk B request eligibility before AlphaPermission.

### Step 7: AlphaPermission V2 Experimental Path

- Add optional auction-state input.
- Add optional structural-memory input.
- Add optional book-state input.
- Keep default V7.2 behavior unchanged.

### Step 8: Execution Intelligence Sandbox

- Add execution-decision object.
- Add passive/take/delay/skip logic.
- Backtest signal quality separately from fill quality.

## 21. Suggested File Layout

New files should be small and contract-driven:

```text
prime/auction_state.py
prime/derived_state.py
prime/structural_memory.py
prime/strategy_eligibility.py
prime/execution_state.py
research/experiment_manifest.py
research/scorecard.py
research/ablation.py
storage/dataset_manifest.py
tests/test_auction_state.py
tests/test_derived_state.py
tests/test_structural_memory.py
tests/test_strategy_eligibility.py
tests/test_execution_state.py
tests/test_experiment_manifest.py
```

Avoid large god files. Each new layer should have contracts and deterministic
unit tests before integration.

## 22. Recommended Test Ladder

Every new concept should pass this ladder:

1. Contract test.
2. Synthetic deterministic unit test.
3. Edge-case synthetic test.
4. Streaming-vs-batch parity test when applicable.
5. Single archive smoke test.
6. Cross-regime archive test.
7. Full span shardable run.
8. Cost sensitivity.
9. Ablation.
10. Walk-forward or holdout.

Skipping the ladder is how indicator stacks become superstition.

## 23. V7.5 Risk Register

### Risk: Overbuilding Before Evidence

Mitigation:

- Keep V7.5 behind docs and experimental flags.
- Finish V7.2 Session 5 first.
- Require promotion gates.

### Risk: State Machine Becomes Subjective

Mitigation:

- Every transition must have numeric evidence and reason codes.
- Synthetic transition fixtures are mandatory.
- State flicker tests are mandatory.

### Risk: Structural Memory Becomes Fake Support/Resistance

Mitigation:

- Every object needs creation evidence, decay, reinforcement, and invalidation.
- Strategies query memory; they do not blindly trade memory.

### Risk: Good Backtest, Bad Fills

Mitigation:

- Separate signal quality from execution quality.
- Add execution decision logs and TCA.
- Model adverse selection and spread state.

### Risk: Result File Drift

Mitigation:

- Add experiment and result manifests.
- Mark interrupted and placeholder outputs explicitly.
- Do not cite results without manifests.

### Risk: ML Too Early

Mitigation:

- Keep ML out until deterministic state labels, leakage tests, walk-forward
  validation, and ablation exist.

## 24. V7.5 Promotion Gates

V7.5 becomes active only when:

- V7.2 test suite is green.
- Session 5 volume-bar confluence is implemented and tested.
- Footprint F1-F5 placeholder outputs are resolved.
- Dataset manifests exist for active datasets.
- AuctionStateEngine has deterministic transition tests.
- StructuralMemory has decay and invalidation tests.
- StrategyEligibility gates strategies before AlphaPermission.
- AlphaPermission V2 has reason-coded outputs and hashes.
- ExecutionDecision exists and separates signal from fill quality.
- Experiment manifests exist for cited results.
- At least one strategy improves out-of-sample after costs.
- Ablation shows the V7.5 layers improve over simpler V7.2/V7.4 baselines.

## 25. Hard Recommendations

1. Do not implement V7.5 directly. Use it as the master direction.
2. Finish the Session 5 volume-bar CVD port first.
3. Treat the V7.4 AuctionStateEngine as a synthetic-test project before any
   strategy integration.
4. Add manifests before running more large sweeps.
5. Delete or quarantine weak result files instead of letting them become lore.
6. Make state flicker a first-class failure.
7. Make execution quality a separate score from signal quality.
8. Require a scorecard before every "this works" claim.
9. Prefer fewer, stronger features with ablation proof.
10. Keep live trading disabled until the execution and risk layers are real.

## 26. Immediate Next Tests

The next tests that create the most leverage:

1. `VolumeBarCVDConfluenceEngine` D1 bearish/bullish synthetic tests.
2. HTF flat-abs quantile test matching `volume_bar_cvd_diagnostic.py`.
3. Chunk B momentum mode unchanged with `use_volume_bar_signal=False`.
4. Chunk B volume-bar signal smoke test on `BTCUSDT-aggTrades-2022-09.zip`.
5. Dataset manifest validation on the six-year BTCUSDT archive set.
6. Download status symlink test.
7. Placeholder result detection test.
8. Minimal AuctionStateEngine transition tests:
   `BALANCED -> DISCOVERY`, `BALANCED -> FAILED_AUCTION`,
   `TRENDING -> EXHAUSTION`.
9. Delta efficiency absorption vs initiative tests.
10. Structural memory decay/invalidation tests.

## 27. Final V7.5 Definition

V7.5 is not a version number for "more ideas." It is the point where the project
becomes a disciplined market research operating system:

- deterministic enough to replay
- structured enough to reason about
- strict enough to delete weak features
- stateful enough to model markets
- cautious enough to separate signal from execution
- auditable enough to trust results

If V7.4 asks "what auction state is the market in?", V7.5 asks:

```text
What evidence proves this state, which strategies are allowed, can we execute
without being picked off, and will ablation prove this feature deserves to live?
```

That is the roadmap.
