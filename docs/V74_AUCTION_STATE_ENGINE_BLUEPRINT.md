# TM Trading System V7.4 Auction State Engine Blueprint

Version: `7.4.0-PRIME`

Status: production blueprint; not yet the active implementation target.

Active foundation: V7.2 Nautilus-Prime remains the current build path until the
Chunk B proof, volume-bar confluence port, and replay validation gates are
complete.

Core rule:

> The system does not ask "what do the indicators say?" It asks "what auction
> state is the market in?"

## 1. Purpose

V7.4 formalizes auction transitions as the primary source of edge. The system
must stop treating CVD, footprint, VWAP, VPIN, absorption, and book signals as
independent entry triggers. Those engines become evidence streams feeding a
higher-level market-theory state machine.

The V7.4 decision layer classifies the current auction state first, then decides
which strategy classes are allowed to act. This shifts the architecture from
indicator stacking to state-aware permissioning.

The primary transition behaviors are:

- balanced auction to imbalance
- breakout to failed breakout
- trend to exhaustion
- absorption to reversal
- initiative activity to responsive activity
- liquidation cascade to value repair

This framing fits the existing repo direction: deterministic flow engines,
VWAP structure, absorption, failed auction logic, regime gating, and
AlphaPermission reason codes.

## 2. Core Law

- Auction state comes first.
- Indicators are evidence, not conclusions.
- Regime gates strategy eligibility.
- Structural memory persists across sessions.
- Confidence decays with time.
- Weak features must survive ablation or be deleted.
- Signal quality and execution quality are separate decisions.

CVD, footprint, VWAP, VPIN, and book signals do not drive entries directly in
V7.4. They feed the state machine that decides whether the market is
initiative, responsive, exhausted, balanced, discovering, or failing.

## 3. Five Pillars

### Pillar 1: Truth

Signed, immutable, auditable market data remains the base layer.

Required properties:

- deterministic trade signing
- strict quality firewall
- replayable raw inputs
- stable checksums
- no silent correction of corrupted feeds

If feed validity fails, every downstream layer is invalid.

### Pillar 2: Flow

Flow engines provide observations about auction behavior:

- CVD
- footprint
- absorption
- delta velocity and acceleration
- VWAP and VWAP migration
- volume profile
- VPIN
- large prints and whale pressure

These are not separate systems. They are evidence streams.

### Pillar 3: Auction State

The AuctionStateEngine is the new orchestration layer. It determines whether the
market is balanced, trending, exhausting, failing, squeezing, liquidating, or
rotating responsively.

### Pillar 4: Structural Memory

The system must retain path-dependent structures:

- failed auction levels
- trapped inventory zones
- HVNs and LVNs
- liquidation cascade zones
- iceberg detection zones
- session VWAP migration
- unfinished auctions

These levels are reaction zones, not static support/resistance labels. Their
importance decays with time and is reinforced by repeated interaction.

### Pillar 5: Permission and Execution

AlphaPermission remains the allow/deny and sizing gate, but V7.4 weights auction
state heavily. Execution intelligence becomes a separate layer so the system can
distinguish a valid signal from a bad fill environment.

## 4. AuctionStateEngine

Add a top-level state engine above individual flow indicators.

Initial auction states:

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

### State Definitions

#### BALANCED

- Range-bound auction.
- Two-sided flow.
- Value area holding.
- Mean reversion and range-fade strategies may be eligible.
- Breakout strategies require confirmation gates.

#### DISCOVERY

- Range expansion.
- Value area migration.
- Acceptance beyond prior value.
- Breakout continuation strategies may be eligible.
- Fade strategies are locked out unless rejection is proven.

#### TRENDING

- Initiative activity dominates.
- Price accepts beyond value.
- CVD and price are directionally aligned.
- Pullback entries may be permitted if structural memory supports them.
- Reversal strategies require exhaustion confirmation.

#### EXHAUSTION

- Effort without result.
- Delta efficiency decays.
- Absorption builds at extremes.
- Divergence and fade strategies may be eligible.
- Continuation strategies are reduced or locked out.

#### FAILED_AUCTION

- Price extends beyond structure and is rejected.
- Snapback into value confirms failure.
- Trapped inventory logic activates.
- Reversal strategies may be eligible.
- A new failed auction level is recorded in structural memory.

#### SHORT_COVERING

- Responsive buying against a downtrend.
- Initiative selling is absent or weakening.
- Mean-reversion long strategies may be eligible.
- Trend-continuation short strategies are locked out or reduced.

#### LONG_LIQUIDATION

- Responsive selling against an uptrend.
- Initiative buying is absent or weakening.
- Mean-reversion short strategies may be eligible.
- Trend-continuation long strategies are locked out or reduced.

#### RESPONSIVE_BUYING

- Absorption at discount.
- Delta efficiency is low.
- Value-area support holds.
- Counter-trend long entries require structural memory confirmation.
- This state is not a trend reversal signal by itself.

#### RESPONSIVE_SELLING

- Absorption at premium.
- Delta efficiency is low.
- Value-area resistance holds.
- Counter-trend short entries require structural memory confirmation.
- This state is not a trend reversal signal by itself.

### Transition Graph

States are not static labels. They are nodes in a transition graph:

```text
BALANCED -> DISCOVERY
  evidence: range expansion + acceptance beyond value

BALANCED -> FAILED_AUCTION
  evidence: breakout attempt + rejection + return into value

DISCOVERY -> TRENDING
  evidence: continued acceptance + initiative flow + efficient displacement

TRENDING -> EXHAUSTION
  evidence: delta efficiency decay + absorption + failed extension

EXHAUSTION -> RESPONSIVE_BUYING
  evidence: sell effort absorbed at discount + snapback

EXHAUSTION -> RESPONSIVE_SELLING
  evidence: buy effort absorbed at premium + snapback

EXHAUSTION -> FAILED_AUCTION
  evidence: extension rejected beyond prior structure

RESPONSIVE_BUYING -> BALANCED
RESPONSIVE_SELLING -> BALANCED
  evidence: return to value + two-sided flow restored

FAILED_AUCTION -> BALANCED
  evidence: value re-established after rejection

TRENDING -> LONG_LIQUIDATION
TRENDING -> SHORT_COVERING
  evidence: cascade event + trapped inventory unwind
```

Every transition must have an evidence threshold. The state engine must not flip
on a single tick, print, or bar unless that event is explicitly classified as a
liquidity event.

## 5. Initiative vs Responsive Activity

This distinction is mandatory in V7.4.

### Initiative Activity

Initiative activity means displacement with acceptance. Aggressive participants
are consuming liquidity, extending range, and creating value migration.

Evidence:

- expanding range bars
- rising delta velocity
- price accepting beyond prior value area
- low absorption ratio
- CVD trending with price
- high delta efficiency
- VWAP migration in the direction of price

Implication:

- Continuation is more likely than reversal.
- Counter-trend strategies need strong structural-memory support.
- Mean reversion is locked out unless rejection appears.

### Responsive Activity

Responsive activity means absorption without durable displacement. Passive
participants are controlling the auction and rejecting extension.

Evidence:

- heavy volume with minimal price displacement
- rejection tails at extremes
- fast snapback into value
- CVD divergence from price
- low delta efficiency
- VWAP acting as a magnet instead of a trend anchor

Implication:

- The move may be a trap.
- Continuation entries are dangerous.
- Mean-reversion and divergence strategies can become eligible.

### Why This Matters

Retail order-flow systems often treat every delta spike the same. V7.4 must not.

Examples:

- Initiative delta at value edge: breakout entry can be valid.
- Responsive delta at value edge: absorption/fade can be valid.
- Initiative delta mid-trend: add or hold can be valid.
- Responsive delta mid-trend: reduce, wait, or prepare for exhaustion.

## 6. Structural Memory

Markets are path dependent. V7.4 needs a persistent memory layer for structural
objects and their decay.

| Object | Persistence | Decay | Reinforcement |
| --- | --- | --- | --- |
| Failed auction level | Session+ | Half-life 30 minutes | Retest confirms |
| Trapped inventory zone | Session+ | Half-life 15 minutes | Liquidation event resets |
| HVN | Multi-session | Half-life 2 hours | Price interaction |
| LVN | Multi-session | Half-life 1 hour | Fast movement through |
| Liquidation cascade zone | Session | Half-life 10 minutes | New cascade |
| Iceberg detection zone | 30 minutes | Linear decay | Redetection refreshes |
| Session VWAP deviation | Session | Rolling only | Updated each bar |
| Unfinished auction | Session+ | Until filled or invalidated | Price approach |

### Structural Memory Query Example

V7.3-style question:

```text
Price is 2% from VWAP. Should mean reversion enter?
```

V7.4 question chain:

```text
1. Is price 2% from VWAP?
2. Is there a failed auction between current price and VWAP?
3. Is trapped inventory aligned with snapback direction?
4. Is current activity initiative or responsive?
5. Is there an LVN that could accelerate movement back to value?
6. Is there an HVN that could block the trade?
7. Is execution quality good enough to express the signal?
```

If activity is initiative and no structural barrier exists, mean reversion is
locked out. If activity is responsive and structural memory supports reversion,
mean reversion can become eligible.

## 7. Derived State Features

V7.4 should add derived features that explain auction behavior rather than only
describing raw flow.

### Delta Efficiency

Definition:

```text
delta_efficiency = abs(price_change) / max(abs(cvd_change), epsilon)
```

Interpretation:

| Delta Efficiency | CVD Relationship | Interpretation |
| --- | --- | --- |
| High | Aligned with price | Initiative control, genuine movement |
| Low | Aligned with price | Absorption, move may fail |
| High | Divergent from price | Hidden liquidity or thin-book displacement |
| Low | Divergent from price | No conviction, balanced or noisy auction |

Delta efficiency separates initiative control from absorption:

- High delta with little price movement means absorption.
- High delta with strong movement means initiative dominance.

### Acceptance/Rejection Score

Inputs:

- close location relative to range
- time spent beyond value
- return speed into value
- VWAP reclaim or rejection
- volume at extension
- follow-through after breakout

Output:

```text
acceptance_score in [-1.0, 1.0]
negative: rejection
positive: acceptance
near zero: unresolved
```

### Liquidity Event Detector

Detects:

- stop runs
- liquidation cascades
- liquidity vacuums
- thin-book accelerations
- forced unwind behavior

The detector must label when ordinary trend or reversion logic should be
overridden.

### Confidence Decay

Every structural object and setup confidence score decays over time.

Rules:

- Recent failed auctions matter more than stale failed auctions.
- Retests reinforce memory.
- Violations invalidate memory.
- Cascades can reset trapped-inventory memory.

### Hierarchical Feature Weighting

Feature weight depends on auction state.

Examples:

- Absorption has high weight in EXHAUSTION and RESPONSIVE states.
- Delta velocity has high weight in DISCOVERY and TRENDING.
- VPIN has high weight around toxicity and liquidation events.
- Spoofing has high weight when L2 quality is required for execution.

## 8. Regime Model Upgrade

V7.4 regimes are market-theory states, not vague trend/range labels.

| Regime | Description | Allowed Strategy Classes |
| --- | --- | --- |
| BALANCED_ROTATION | Value area holding, two-sided flow | Mean reversion, range fade |
| INITIATIVE_TREND | Acceptance beyond value, delta efficient | Trend continuation, pullback entry |
| EXHAUSTED_TREND | Trend exists but efficiency decays | Divergence fade, reduce trend exposure |
| VOLATILE_DISCOVERY | Range expanding, value migrating | Breakout continuation, no fade |
| LIQUIDATION_EVENT | Cascade, trapped inventory unwinding | Liquidation playbook only, caution |
| FAILED_BREAKOUT | Extension rejected, snapback | Reversal, trapped trader fade |
| MEAN_REVERSION | Return to value from responsive activity | Mean reversion, no trend continuation |
| LOW_PARTICIPATION | Volume absent, no conviction | No entries |

This removes strategy conflicts. A divergence fade and a breakout continuation
should not compete inside one vague "trend" bucket.

## 9. Permission Chain

AlphaPermission remains the decision gate for allow/deny and size. V7.4 feeds it
auction state and structural memory before raw indicator confirmation.

Priority order:

```text
1. FEED_VALIDITY
   - quality firewall pass/fail
   - hard deny if invalid

2. MARKET_REGIME
   - auction-theory regime classification
   - gates strategy class eligibility

3. AUCTION_STATE
   - initiative vs responsive classification
   - acceptance/rejection score
   - gates entry direction permission

4. STRUCTURAL_MEMORY
   - key level proximity
   - trapped inventory alignment
   - location validation

5. FLOW_CONFIRMATION
   - CVD alignment
   - footprint confirmation
   - delta efficiency
   - absorption

6. L2_QUALITY
   - spoof detection
   - iceberg and absorption signals
   - book honesty check

7. CONTEXT_MULTIPLIERS
   - whale flow
   - VPIN
   - time of session
   - volatility and participation

8. EXECUTION_CONSTRAINTS
   - spread state
   - queue position
   - adverse selection risk
   - size reduction, delay, or skip
```

Reason codes must identify which layer approved, reduced, delayed, or denied
the signal.

## 10. Execution Intelligence

Execution is a separate intelligence layer. A valid alpha can disappear live if
fills are toxic.

Execution intelligence must evaluate:

- queue positioning
- adverse selection risk
- adaptive passive pricing
- spread-state logic
- book depth at entry and exit
- slippage expectation
- latency sensitivity
- whether taking or posting is appropriate

### Signal-Fill Dissonance

| Signal Quality | Book Quality | Action |
| --- | --- | --- |
| Strong | Clean | Full size, immediate or normal entry |
| Strong | Toxic | Reduce size, passive only, or delay |
| Strong | Thin | Delay or wait for liquidity |
| Moderate | Clean | Reduced size, monitor |
| Weak | Any | No entry |

The system must be able to say:

```text
The signal is valid, but the book is wrong for execution.
```

In that case the entry is delayed, reduced, or skipped.

## 11. Recommended Architecture

### Phase 0: Truth

- signed trades
- quality firewall
- audit trail
- deterministic replay checksums

### Phase 1: Flow Signals

- CVD
- footprint
- absorption
- delta velocity
- VWAP
- volume profile
- VPIN

### Phase 2: Book Intelligence

- imbalance
- iceberg detection
- spoofing detection
- impact pressure
- queue and depth state

### Phase 3: Auction State

- initiative vs responsive classification
- acceptance vs rejection score
- failed auction detection
- liquidity event detection
- exhaustion classification

### Phase 4: Structural Memory

- key levels
- trapped inventory
- value migration
- liquidity zones
- unfinished auctions
- decay and reinforcement

### Phase 5: Regime Engine

- balanced rotation
- initiative trend
- exhausted trend
- volatile discovery
- liquidation event
- failed breakout
- mean reversion
- low participation

### Phase 6: AlphaPermission

- weighted confidence chain
- hard-deny logic
- size modifiers
- confidence decay
- reason-coded output

### Phase 7: Strategy Layer

Each strategy class is restricted by regime and auction state:

- divergence
- momentum
- breakout
- reversion
- liquidation playbook
- trapped trader fade

### Phase 8: Execution Intelligence

- queue logic
- slippage control
- adaptive placement
- adverse selection filters
- spread-state filters

### Phase 9: Vault and Learning

- ablation studies
- feature decay tracking
- walk-forward validation
- scorecards
- structural-memory persistence
- delete weak features

## 12. Research Agenda

High-value research themes:

- auction market theory: balanced vs imbalanced auctions
- acceptance vs rejection and value migration
- initiative vs responsive order-flow taxonomy
- trapped inventory and failed auctions
- HVN/LVN reaction behavior
- absorption and effort vs result
- delta efficiency
- liquidity cascades and stop runs
- confidence decay for structural events
- execution alpha and adverse selection

Useful query clusters for later web-backed research:

```text
auction market theory acceptance rejection
initiative responsive activity order flow
absorption effort versus result trading
trapped inventory liquidation cascades
value area migration market profile
failed auction order flow
delta efficiency order flow
adverse selection execution queue position
liquidity vacuum crypto microstructure
market memory high volume nodes
```

## 13. Immediate Implementation Order

Do not jump straight from V7.2 to full V7.4. Promote only after evidence.

1. Finish V7.2 Chunk B volume-bar confluence port.
2. Add deterministic tests for D1 + D4 confluence and momentum-path isolation.
3. Build a minimal `AuctionStateEngine` with synthetic tests only.
4. Add `DeltaEfficiencyEngine` and acceptance/rejection scoring.
5. Add structural memory objects with decay and invalidation rules.
6. Feed auction state into AlphaPermission as a non-default experimental gate.
7. Add strategy eligibility matrices.
8. Add execution-state filters after signal quality is stable.
9. Run ablation before enabling any new feature by default.

## 14. Promotion Gates

V7.4 should become active only when these gates pass:

- V7.2 tests remain green.
- Momentum mode behavior remains unchanged unless explicitly migrated.
- Auction state has deterministic synthetic coverage.
- State transitions are stable under replay.
- Structural memory has decay and invalidation tests.
- At least one strategy improves out-of-sample after fees and slippage.
- Ablation shows the auction-state layer adds value beyond raw indicators.
- Execution filters reduce bad fills without deleting all valid trades.

## 15. Non-Goals

V7.4 does not mean:

- adding another raw indicator because it is easy
- letting ML choose states before deterministic labels exist
- replacing AlphaPermission with strategy logic
- bypassing risk because auction state looks strong
- treating structural levels as static support/resistance
- trading failed auctions without acceptance/rejection proof
- claiming live readiness before execution intelligence is tested

## 16. Skeleton Interfaces

These are design targets, not implementation commitments.

```python
class AuctionState:
    label: str
    confidence: float
    initiative_score: float
    responsive_score: float
    acceptance_score: float
    rejection_score: float
    reason_codes: tuple[str, ...]
```

```python
class StructuralMemoryObject:
    kind: str
    price: float
    first_seen_ts_ns: int
    last_touched_ts_ns: int
    strength: float
    decay_model: str
    invalidation_price: float | None
    reason_codes: tuple[str, ...]
```

```python
class StrategyEligibility:
    strategy_class: str
    permitted: bool
    size_multiplier: float
    reason_codes: tuple[str, ...]
```

## 17. Version Position

This is V7.4 if the foundation remains V7.2/V555 and the upgrade is mainly the
decision layer: indicator synthesis becomes auction-state orchestration.

If the project later replaces the data model, execution model, or replay
contract, that would justify a larger version boundary. For now, V7.4 is the
next market-theory blueprint above the current deterministic research stack.
