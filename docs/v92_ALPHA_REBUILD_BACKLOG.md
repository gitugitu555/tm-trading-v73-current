# V9.2 Alpha Rebuild Backlog

## Objective

Replace the rejected D4 strategy with new alpha families built on timestamp-safe
features, immutable opportunities, explicit costs, and recent-period
validation. D4 remains a benchmark feature only.

## Global Research Rules

- No AI decisions.
- No arbitrary confluence score.
- No same-bar lookahead.
- No future swing confirmation.
- All features must be observable at the decision timestamp.
- Every alpha must report post-cost recent expectancy.
- 2024-2026 performance is mandatory.
- Every candidate must use immutable signal generation and chronological
  walk-forward validation.
- No L2, derivatives, or liquidation feature may be synthesized from spot
  aggTrades.
- Capital sizing cannot hide negative expectancy.

## Data Foundation Requirements

Before testing an alpha family, write a deterministic source manifest covering:

- source venue and instrument;
- spot or futures market;
- timestamp range and resolution;
- missing intervals and overlap checks;
- feature availability timestamp;
- build hash and code commit;
- explicit cost and latency assumptions.

## Priority 1 — OFI / Microprice Imbalance

Hypothesis: short-horizon price moves are better predicted by changes in
displayed queue pressure than by completed-bar CVD divergence.

Required data:

- timestamped L2 book updates or snapshots;
- best bid/ask sizes and prices;
- sequence numbers and gap detection;
- synchronized trade tape.

Features:

- OFI and multi-level OFI;
- microprice displacement;
- queue imbalance and imbalance change;
- spread and depth regime;
- cancellation and refill pressure.

Acceptance:

- positive 2024-2026 post-cost expectancy;
- survives latency ladder;
- stable across spread/depth regimes;
- no simulated maker fills without queue data.

## Priority 2 — Absorption / Iceberg

Hypothesis: aggressive flow that repeatedly fails to move price identifies
absorption and subsequent reversal or breakout pressure.

Required data:

- trade tape;
- L2 refill observations for true iceberg claims;
- spot-only failed-impulse proxy retained separately from true iceberg labels.

Features:

- aggressive volume per price movement;
- repeated prints at level;
- refill count and refill persistence;
- failed buy/sell impulse;
- post-absorption breakout versus reversal labels.

Acceptance:

- separate proxy absorption from verified iceberg evidence;
- positive recent post-cost expectancy;
- stable across volatility and volume regimes.

## Priority 3 — VPIN / Toxicity

Hypothesis: order-flow toxicity predicts when continuation, reversal, or trade
avoidance has positive value.

Features:

- volume-bucket buy/sell imbalance;
- VPIN and rolling VPIN percentile;
- toxicity acceleration;
- interaction with spread and volatility.

Research questions:

- Is toxicity predictive, or only a risk/skip feature?
- Does high toxicity favor continuation while low toxicity favors reversion?

Acceptance:

- blocked-winner versus blocked-loser accounting;
- positive value in 2024-2026;
- no promotion based only on drawdown reduction.

## Priority 4 — Liquidation Cascade Reversal / Continuation

Hypothesis: liquidation cascades create either exhaustion reversals or
short-lived continuation depending on flow persistence and market structure.

Required data:

- timestamped futures liquidation events;
- verified long/short liquidation direction;
- synchronized futures price, OI, and funding.

Labels:

- continuation over 1, 5, 15, and 60 minutes;
- reversal after cascade peak;
- MFE-before-MAE after cascade.

Acceptance:

- timestamp-aligned source with no publication-delay leakage;
- separate long and short cascades;
- recent post-cost and latency-stressed expectancy.

## Priority 5 — Funding + OI Squeeze

Hypothesis: extreme positioning plus changing OI identifies squeeze risk and
forced-position unwinds.

Features:

- funding level, percentile, and change;
- OI level, change, and acceleration;
- price/OI state combinations;
- basis if available;
- crowding persistence.

Candidate states:

- price up + OI up;
- price down + OI up;
- price up + OI down;
- price down + OI down;
- extreme funding with OI reversal.

Acceptance:

- use the value available before the signal timestamp;
- account for funding publication/update schedule;
- positive 2024-2026 post-cost expectancy.

## Priority 6 — Auction Profile State

Hypothesis: auction state and transitions are more useful than static profile
levels.

Features:

- value-area migration;
- POC migration velocity;
- balanced versus discovery state;
- failed auction and acceptance outside value;
- low-volume-node traversal;
- profile state transition probabilities.

Acceptance:

- profile built only from completed prior data;
- test state transitions, not isolated POC proximity;
- positive recent post-cost expectancy and walk-forward stability.

## Priority 7 — Regime-Classifier-First Architecture

Hypothesis: alpha families should be selected by observable market regime
rather than combined into one universal rule.

Architecture:

1. Classify regime using past-only volatility, trend, liquidity, toxicity, and
   volume state.
2. Evaluate each alpha family independently inside each regime.
3. Select or disable families using train-only evidence.
4. Evaluate the selected policy on the next chronological test window.

Hard constraints:

- classifier trained only on prior data;
- regime definitions and family selection frozen before each test window;
- report transition stability and unclassified states;
- no score aggregation that hides individual negative alphas.

## V9.2 Execution Order

1. Build exact 500 BTC catalog and close the D4 10-bar lead.
2. Acquire and verify L2 source for OFI/microprice and true iceberg research.
3. Acquire and verify futures OI, funding, and liquidation histories.
4. Build timestamp-aligned multi-source feature ledger.
5. Test OFI/microprice and absorption first.
6. Test VPIN/toxicity as alpha and shadow filter.
7. Test derivatives families.
8. Introduce regime-classifier-first selection only after multiple independent
   alpha families exist.

## Promotion Gate

A V9.2 family may move beyond shadow research only if:

- recent post-cost expectancy is positive;
- 2024-2026 sample size is sufficient;
- bootstrap confidence interval is acceptable;
- monthly walk-forward median test expectancy is positive;
- positive test split rate exceeds 55%;
- no single year dominates profit;
- cost and latency stress do not collapse the result;
- source manifest and feature timestamps prove no leakage.
