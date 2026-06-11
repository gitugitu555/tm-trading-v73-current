# V9.2 Data-First Alpha Plan

## Decision

V9.2 alpha research is blocked from its highest-priority families until a
verified historical L2 and derivatives data inventory exists.

The repo has a trustworthy six-year spot aggTrades and volume-bar foundation.
It does not yet have the point-in-time L2, spread, depth, queue, funding, open
interest, liquidation, basis, whale-flow, macro, correlation, or options-gamma
history required to test the recovered strategy architecture honestly.

No L2 or derivatives feature may be promoted, or even reported as historically
tested, until its source manifest and timestamp audit pass.

## Completed Prerequisites

- Verified six-year spot aggTrades coverage and deterministic 300 BTC catalog.
- Immutable signal and path replay methodology.
- Explicit cost stress and monthly walk-forward framework.
- D4 purity, recovered-context, exit, and bar-size/horizon closure.
- Final D4 surface run completed once.
- D4 retained only as research benchmark.

The final D4 surface found one limited lead: approximate 500 BTC / 10-bar D4.
That lead requires an exact raw-trade 500 BTC catalog and walk-forward
validation. It does not reopen general D4 TP/SL research.

## Phase 1 — Bybit Historical Inventory

Bybit historical inventory/download is the first V9.2 data priority because
the next alpha families require futures positioning, liquidation, and L2
context.

Inventory candidate sources for:

- L2 snapshots and incremental depth updates;
- trades with aggressor side;
- best bid/ask and spread;
- open interest;
- funding;
- liquidations;
- mark, index, and perpetual prices;
- basis/premium;
- long/short ratios if available.

For every source record:

```text
venue
instrument
market type
data type
archive URL/path
file checksum
file size
first/last event timestamp
first/last availability timestamp if different
row/update count
sequence range
missing sequence count
duplicate count
timestamp monotonicity
parse status
schema version
```

Do not download blindly. First create an exact inventory and download plan.

## Phase 2 — Verification Foundation

Before feature construction, implement:

1. Deterministic source manifests and hashes.
2. Gap, overlap, duplicate, corruption, and sequence checks.
3. Resumable download and parsing.
4. Small sample parsers with fixture tests.
5. Point-in-time availability timestamps.
6. Spot/futures/L2 clock-alignment diagnostics.
7. Explicit source caveats and coverage waivers.

Hard failure conditions:

- missing or reordered L2 update sequences;
- unclear snapshot/delta reconstruction semantics;
- derivatives values without point-in-time publication timestamps;
- silent missing intervals;
- unverifiable archive identity;
- inability to reproduce feature hashes.

## Phase 3 — Regime Classifier Before Signal Sweeps

Build the past-only regime classifier before testing new alpha thresholds.

Initial regimes from verified spot data:

- trend/range;
- volatility: low/medium/high/extreme;
- session: Asia/London/NY/London-NY overlap/other;
- VWAP state: above/below/near/extended;
- auction state: inside value/outside value/near POC/above VAH/below VAL;
- volume and bar-duration state.

Add only after verified data exists:

- spread/depth/liquidity regime;
- toxicity regime;
- funding/OI/crowding regime;
- liquidation state;
- macro/risk state.

Architecture:

```text
past-only regime state
-> immutable alpha-family opportunity
-> isolated feature attribution
-> cost-aware eligibility label
-> chronological replay
```

The classifier does not emit trades. It labels context and selects eligible
alpha families using train-only evidence.

Acceptance:

- deterministic states;
- no future-confirmed swings;
- state definitions frozen before each test period;
- transition and unclassified-state reporting;
- 2020-2023 and 2024-2026 results;
- no arbitrary confluence score.

## Phase 4 — Under-Tested Spot Diagnostics

While L2/derivatives data is being acquired, complete low-cost diagnostics that
the verified spot foundation supports:

1. Session quality by alpha family and cost model.
2. Volatility-regime attribution.
3. Session VWAP distance, reclaim, rejection, and migration.
4. Deterministic anchored-VWAP experiments using observable anchors only.
5. Auction-state transitions: POC/value migration, acceptance, rejection, and
   failed auction.
6. Volume-bucket VPIN variants, honestly labeled as tape-based toxicity
   diagnostics.
7. Exact raw-trade 500 BTC / 10-bar D4 validation.

These diagnostics remain feature research. They cannot become score-based
gates.

## Phase 5 — L2 Alpha Families

After L2 verification passes, build:

- OFI and MLOFI;
- microprice imbalance;
- spread/depth state;
- absorption and true refill/iceberg features;
- liquidity sweep/reclaim;
- toxic-flow avoidance;
- queue-aware passive-entry simulation.

Required reporting:

- point-in-time feature availability;
- latency ladder;
- taker and empirically calibrated maker scenarios;
- fill rate and adverse selection;
- blocked-winner/blocked-loser accounting for gates;
- 2024-2026 post-cost expectancy;
- chronological walk-forward.

Maker-first execution remains blocked until queue-aware fill assumptions can be
supported by historical data.

## Phase 6 — Derivatives And Forced-Flow Families

After derivatives verification passes, build:

- funding and OI state;
- funding + OI squeeze;
- liquidation cascade reversal and continuation;
- perp basis/premium;
- long/short crowding;
- normalized whale aggressive flow.

Each feature must use the value known at the decision timestamp, not a
retrospectively revised or later-published value.

Required reporting:

- source and availability timestamp;
- missingness by year/month;
- standalone attribution;
- interaction with regimes;
- recent post-cost expectancy;
- latency and publication-delay stress.

## Phase 7 — Dynamic Exit Lab

Dynamic exits are evaluation overlays, not alpha.

Evaluate only after an alpha family has positive post-cost opportunity
expectancy:

- MFE/MAE distributions;
- trailing after MFE;
- breakeven after MFE;
- CVD/OFI reversal;
- auction invalidation;
- time stop;
- staged/partial exits;
- hard disaster stop.

Reject any exit that improves win rate while reducing net expectancy.

## Phase 8 — Cost-Aware Meta-Labeling

The final V9.2 architecture predicts whether an immutable setup is tradeable
after costs.

Inputs may include:

- D4 and other weak alpha primitives;
- regime state;
- VWAP/auction state;
- L2 pressure and toxicity;
- derivatives/crowding state;
- execution-quality state.

Labels:

- net profitable after explicit cost ladder;
- MFE-before-MAE;
- triple barrier;
- clean trade path;
- maker/taker eligibility where supported.

Rules:

- time-series splits only;
- no random shuffle;
- features timestamped before labels;
- calibrated probability buckets must map monotonically to recent realized
  expectancy;
- model accuracy alone is irrelevant.

## Build Order

1. Inventory Bybit and alternative historical L2/derivatives sources.
2. Generate download plan; verify samples, schemas, gaps, sequences, and
   checksums.
3. Build regime classifier from currently verified spot data.
4. Complete session, volatility, VWAP, auction-transition, and exact 500 BTC
   diagnostics.
5. Build timestamp-aligned multi-source feature ledger.
6. Test OFI/microprice and absorption first.
7. Test VPIN/toxicity as alpha and risk filter separately.
8. Test liquidation and funding/OI forced-flow families.
9. Run dynamic exits only on positive candidates.
10. Build cost-aware meta-labeling and family selection.

## Universal Promotion Gate

No V9.2 alpha, context gate, execution rule, or meta-label may advance unless:

- data source and feature manifest pass;
- no same-bar or publication-time lookahead exists;
- no future-confirmed swing is used;
- 2024-2026 post-cost expectancy is positive;
- recent sample size is sufficient;
- bootstrap confidence interval is acceptable;
- monthly walk-forward median test expectancy is positive;
- positive test split rate exceeds 55%;
- cost and latency stress do not collapse the result;
- no single year or regime explains most profit;
- every component has isolated attribution;
- no arbitrary score or AI trade decision is used.

## Stop Conditions

Stop a research family when:

- required source data cannot be verified;
- recent post-cost expectancy is non-positive across reasonable definitions;
- apparent value disappears under publication-delay or latency stress;
- feature value depends on future confirmation;
- improvement comes only from capital sizing or opportunity suppression;
- walk-forward repeatedly rejects it.
