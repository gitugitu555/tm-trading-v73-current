# V555 Footprint F1-F5 Spec

This spec defines the footprint research path for raw Binance aggTrades and
volume-bar replay. It is deliberately different from CVD:

- CVD asks whether cumulative flow diverges from price.
- Footprint asks whether aggressive flow is concentrated at specific levels and
  then fails or absorbs there.

The footprint signal must be treated as a structural confluence feature, not a
standalone alpha source.

## Data Model

Use the price-level footprint representation already present in
`features/footprint.py` and `prime/phase1.py`:

- `level = round(price / tick_size) * tick_size`
- per level, track:
  - `buy_volume`
  - `sell_volume`
  - `delta = buy_volume - sell_volume`
  - `total_volume = buy_volume + sell_volume`

This spec assumes raw aggressive trade flow only. It does not assume access to
resting L2 book state, hidden liquidity, or cancellations.

## Core Hypothesis

The useful footprint question is:

- "Did aggressive flow cluster at a level, and did price fail to continue
  through that level?"

That breaks into three measurable objects:

1. Stacked imbalance.
2. Rejection confirmation.
3. Absorption at the level.

## F1: Stacked Imbalance

Goal: identify a directional cluster of consecutive price levels where one side
dominates.

Default rule:

- `stack_levels = 3`
- `imbalance_ratio = 3.0`
- `min_level_total_volume = 5.0`

Short setup:

- At least 3 consecutive price levels.
- Each level has `sell_volume >= imbalance_ratio * max(buy_volume, 1e-9)`.
- Each level has `total_volume >= min_level_total_volume`.

Long setup:

- At least 3 consecutive price levels.
- Each level has `buy_volume >= imbalance_ratio * max(sell_volume, 1e-9)`.
- Each level has `total_volume >= min_level_total_volume`.

Interpretation:

- This is the "level structure" event.
- It should be directional and local, not a slow aggregate over many minutes.

Reason code:

- `FOOTPRINT_STACKED_IMBALANCE`

## F2: Rejection Confirmation

Goal: verify that price actually rejected the imbalance zone.

Default rule:

- Evaluate over the next `1-3` volume bars after F1.
- `max_extension_ticks = 1`
- `close_back_inside = true`

Short setup:

- Price probes the upper boundary of the imbalance cluster.
- Price extends no more than `max_extension_ticks * tick_size` beyond the zone.
- The bar closes back below the cluster boundary.

Long setup:

- Price probes the lower boundary of the imbalance cluster.
- Price extends no more than `max_extension_ticks * tick_size` beyond the zone.
- The bar closes back above the cluster boundary.

Interpretation:

- This prevents treating a continuation as an exhaustion event.
- If price accepts beyond the cluster, the setup is invalid.

Reason code:

- `FOOTPRINT_REJECTION`

## F3: Absorption

Goal: detect aggressive volume that does not produce corresponding price
extension.

Default rule:

- `absorption_delta_share <= 0.15`
- `volume_floor = 50.0`
- `max_price_extension_ticks = 1`

For a candidate level or cluster:

- `total_volume >= volume_floor`
- `abs(delta) / total_volume <= absorption_delta_share`
- price movement from the first touch of the level to bar close is no more
  than `max_price_extension_ticks * tick_size`

Interpretation:

- A lot of volume traded, but net directional commitment stayed compressed.
- On aggTrades, this is the closest honest proxy for absorption.
- It does not prove hidden liquidity. It only proves aggressive flow did not
  get price much farther.

Reason code:

- `FOOTPRINT_ABSORPTION`

## F4: Structure Confluence

Goal: restrict footprint signals to meaningful levels.

Default confluence set:

- prior day high
- prior day low
- session high
- session low
- VWAP band
- volume profile POC / VAH / VAL

Default proximity rules:

- `structure_tick_radius = 2`
- `vwap_deviation_pct = 0.003`
- `session_extreme_pct = 0.003`

Interpretation:

- A raw footprint cluster is not enough.
- The level should matter structurally, otherwise the signal is too noisy.

Reason code:

- `FOOTPRINT_STRUCTURE`

## F5: Final Gate

Goal: define the actual trade trigger.

Default gate:

- `F1` must pass.
- `F4` must pass.
- At least one of `F2` or `F3` must pass.

Optional stricter gate:

- Require all of `F1`, `F2`, `F3`, and `F4` for the highest-confidence tier.

Recommended interpretation:

- `F5` is the trade trigger.
- `F1-F4` are diagnostic stages.
- A signal that passes only `F1` should not trade.

Reason code:

- `FOOTPRINT_FINAL_GATE`

## Suggested Stage Names

Use the same compact stage style as the CVD diagnostics:

- `F1_stacked_imbalance`
- `F2_rejection_confirm`
- `F3_absorption`
- `F4_structure_confluence`
- `F5_final_gate`

## Suggested Test Matrix

Unit tests should cover:

1. Tick rounding:
   - `100.24` at `tick_size=0.5` maps to `100.0`
   - `100.26` maps to `100.5`
2. Stacked imbalance:
   - three consecutive levels satisfy the 3:1 dominance rule
   - two consecutive levels do not
3. Rejection:
   - price touches the cluster and closes back inside
   - acceptance through the cluster invalidates the setup
4. Absorption:
   - high total volume with compressed delta passes
   - high delta with meaningful extension fails
5. Structure confluence:
   - signal near prior day high/low or VWAP band passes
   - signal in the middle of nowhere fails
6. Final gate:
   - `F1 + F4 + (F2 or F3)` passes
   - any incomplete combination fails

## Acceptance Criteria

Do not promote footprint beyond research unless:

- it is deterministic on replay,
- it survives walk-forward validation,
- and it adds measurable edge after fees and slippage.

If it only improves trade selectivity but not out-of-sample performance, keep it
as a filter, not a primary alpha source.
