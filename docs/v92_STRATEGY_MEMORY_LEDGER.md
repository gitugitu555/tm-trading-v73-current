# V9.2 Strategy Memory Ledger

## Purpose

This ledger preserves useful concepts recovered from the Mistral strategy
export without reviving unsupported claims, arbitrary confluence scores, or AI
trade decisions.

Recovered source documents:

- `elite_90plus_strategy.md`
- `Ultimate_Crypto_Trading_Automation_Guide.md`
- `PROFESSIONAL_TRADING_SYSTEM_RUNDOWN.md`
- user-provided `V92_MISTRAL_STRATEGY_RECOVERY_INPUT.md` contents

The recovered architecture is:

```text
market regime
-> setup eligibility
-> order-flow confirmation
-> execution-quality gate
-> dynamic exit management
```

Every concept below must become a measurable, timestamp-safe diagnostic before
it can influence trade eligibility.

## Status Definitions

| Status | Meaning |
|---|---|
| already tested | Tested on verified history with a decision recorded |
| disproven | Current implementation or hypothesis failed its evidence threshold |
| under-tested | Some implementation/evidence exists, but validation is incomplete |
| data-blocked | Required verified historical source is unavailable |
| implementation-blocked | Data exists or may exist, but reliable implementation is missing |
| V9.2 priority | Approved next research work after prerequisites |
| archived | Retained only for historical context; do not revive directly |

## Core Strategy Memory

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| D4 / CVD divergence | Big 5; old core alpha | already tested | Verified purity, context, exit, and bar/horizon surface reports exist | Verified spot aggTrades and volume bars | Gross effect is too small and decays after 2023 | Exact 500 BTC / 10-bar catalog validation only | Exact surface or walk-forward fails recent post-cost expectancy | Exact recent post-cost expectancy positive with walk-forward support |
| 80-90% win-rate objective | Elite/automation guides | archived | Historical trade win rate explained by geometry and runner semantics | None | Invalid research objective | None | Always | Do not revive |
| Arbitrary confluence score | Automation guide | archived | Old score/gate ideas documented; prohibited in V9.2 | None | Hides negative components and encourages threshold mining | None | Always | Do not revive |
| AI trade decision | Automation guide | archived | No approved research role | None | Non-deterministic and untestable decision path | AI may summarize reports only | Always for backtests | Do not revive as trading rule |

## Regime And Location

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| Regime-first architecture | Recovered architecture | V9.2 priority | Basic trend/volatility/session features exist; no train-only selector | Verified feature ledger; later liquidity/derivatives states | Existing regimes are simple and not used in strict walk-forward family selection | Build past-only regime ledger before new signal sweeps | Regimes unstable or provide no out-of-sample differentiation | Stable states improve family selection in 2024-2026 |
| Trend/range state | Market structure | under-tested | Past-only slope state tested in recovered-context report | Verified bars | Current definition is coarse | Compare robust past-only definitions, then freeze before walk-forward | No recent bucket differentiation | Stable recent family-specific expectancy difference |
| Support/resistance proximity | Market structure | disproven | Prior rolling-extrema proximity tested; no-key-level D4 performed better | Verified bars | Recovered rule did not improve D4 | Retain as feature only in new family attribution | Repeated recent underperformance | New alpha shows stable recent benefit without future swings |
| Future-confirmed swings | Old market-structure implementation idea | archived | Explicitly prohibited | None | Lookahead leakage | None | Always | Do not revive |
| Volatility regime | High-impact support feature | V9.2 priority | Rolling volatility buckets exist but are underused | Verified bars; later spread/depth data | No regime-first walk-forward architecture | Build low/medium/high/extreme past-only state ledger | No stable recent conditional behavior | Improves recent post-cost family selection |
| Session quality | Big 5 | V9.2 priority | UTC session labels and session-hour reports exist | Verified timestamps | London/NY overlap and family-level recent analysis incomplete | Run session diagnostics for each new alpha and cost model | No stable recent differentiation | Positive recent post-cost bucket with sufficient events |
| Macro/risk state | Recovered risk layer | data-blocked | Risk-state placeholders/gates exist | Verified timestamped macro calendar and market data | No audited historical macro source | Inventory sources and publication timestamps | Leakage or no recent incremental value | Stable walk-forward value after timestamp audit |
| Cross-asset correlation | Recovered context | data-blocked | No verified synchronized multi-asset ledger | Spot/futures crypto and macro asset history | Data inventory absent | Build source inventory and synchronized manifest | Unstable or no recent value | Stable recent conditional value |
| Options gamma / GEX | Derivatives context | data-blocked | No verified options positioning history | Timestamped options OI/greeks by strike/expiry | Source and publication timing absent | Inventory Deribit/other historical options sources | Cannot prove point-in-time availability | Stable recent post-cost conditioning value |

## Auction, VWAP, And Profile

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| VWAP context | Big 5 | under-tested | VWAP engine, cached columns, and v8.5 filters exist; prior VWAP-filter run was negative | Verified bars/trades | Anchoring definitions and recent diagnostics incomplete | Test session VWAP distance, reclaim, rejection, and migration as isolated features | No positive recent post-cost bucket | Stable recent feature value across walk-forward |
| Anchored VWAP | Big 5 | implementation-blocked | No approved non-leaky anchor protocol | Verified bars plus deterministic anchor events | Anchor selection risks hindsight leakage | Define anchors from observable events only | Anchor requires future confirmation or mines event choices | Stable recent post-cost value with frozen anchors |
| Static POC proximity | Volume profile | already tested | Recovered-context report shows below-POC structure but no cost coverage | Verified bars | Does not clear costs | Retain as feature, not rule | Continued recent post-cost failure | Positive incremental value in new alpha family |
| VAH/VAL/static value state | Auction profile | already tested | Inside/above/below value tested; no bucket clears costs | Verified bars | Static state insufficient | Move to state transitions | Transition features also fail recent post-cost tests | Stable recent transition edge |
| Auction profile state transitions | Recovered auction logic | V9.2 priority | Market profile engine exists; migration/acceptance transition ledger absent | Verified bars | Need deterministic transition definitions | Build POC/value migration, acceptance, rejection, failed-auction features | No recent post-cost predictive value | Walk-forward-stable recent expectancy |
| Failed auction | Auction logic | implementation-blocked | Concept documented, no validated past-only detector | Verified bars; L2 optional | Definition not frozen | Implement completed-bar failed-auction labels and diagnostics | Requires future confirmation or lacks recent value | Stable recent post-cost value |
| Profile/auction invalidation exit | Exit management | already tested | Profile exit variants tested and negative after costs | Verified paths/profile snapshots | Does not rescue D4 | Re-test only for a new positive raw alpha | Negative raw alpha or recent post-cost failure | Improves positive alpha out-of-sample |

## Order Flow, Liquidity, And Execution

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| Liquidity heatmap | Big 5 | data-blocked | No verified historical depth ledger | Historical L2 snapshots/deltas with sequence integrity | L2 inventory absent | Bybit/other L2 inventory, parser, gaps, checksums | Source cannot prove complete ordered updates | Verified point-in-time L2 history exists |
| Order-book imbalance | High-impact support | data-blocked | Engines/tests exist, but no verified historical L2 research data | Historical L2 | Cannot backtest honestly | Same L2 foundation as liquidity heatmap | Must not synthesize from aggTrades | Positive recent post-cost/latency-stressed value |
| OFI / MLOFI | Alpha rebuild | data-blocked | MLOFI modules/docs exist; aggTrades proxy is not true MLOFI | Multi-level L2 updates | Historical L2 absent | Build true OFI/MLOFI after source verification | Proxy-only or sequence gaps | Stable recent post-cost value |
| Microprice imbalance | Execution alpha | data-blocked | Some architecture references; no verified history | BBO/L2 updates | Historical book absent | Build after L2 manifest passes | No latency-stressed edge | Positive recent post-cost edge |
| Absorption proxy | Order-flow recovery | under-tested | Failed-impulse/absorption proxy features exist | Verified aggTrades/bars | Proxy is not true iceberg/absorption evidence | Evaluate proxy separately as V9.2 alpha family | No recent post-cost value | Stable recent walk-forward edge |
| True absorption / iceberg / replenishment | Order-flow recovery | data-blocked | Iceberg/whale feature code exists but lacks verified research history | L2 refill and trade tape | Historical L2 absent | Build only after L2 sequence audit | Cannot distinguish refill from missing updates | Positive recent post-cost edge |
| Liquidity sweep/reclaim | Execution/auction recovery | data-blocked | No verified depth-removal/replenishment history | L2 plus trades | Historical L2 absent | Add after L2 foundation | Incomplete sequence or no recent value | Stable recent edge |
| VPIN / toxicity | High-impact support | under-tested | Simplified VPIN/proxy diagnostics exist; true interpretation unresolved | Trade tape; L2 helpful | Existing variants may measure volatility rather than toxicity | Rebuild volume-bucket VPIN and test as alpha versus risk filter | No blocked-loser value or recent expectancy | Stable recent value with honest labeling |
| Spread gate | Execution quality | data-blocked | Cost model exists; historical spread ledger absent | BBO history | Cannot reconstruct spread from aggTrades | Add to L2 feature ledger | Synthesized spread or no recent benefit | Positive blocked-loser/execution value |
| Depth/liquidity gate | Execution quality | data-blocked | Concept only | L2 history | No historical depth | Add after L2 foundation | No recent value or excessive retention loss | Stable recent execution improvement |
| Slippage model | Execution quality | under-tested | Explicit static cost/slippage ladders exist | L2/trade response for empirical calibration | Static assumptions only | Calibrate by spread, volatility, size, latency | Model unsupported by fills | Out-of-sample calibration and stress survival |
| Maker-first/passive placement | Execution quality | data-blocked | Hypothetical maker mode explicitly labeled | Queue-aware L2 and order/fill data | Fill probability and adverse selection unknown | Build simulator only after queue data | Any claim based only on aggTrades | Positive latency/fill-stressed recent expectancy |
| Cancel/replace on signal flip | Execution quality | data-blocked | Concept not validated | Queue/order state and latency model | No fill/queue history | Test after maker simulator | Unrealistic fills or no recent value | Robust execution improvement |
| Toxic-flow avoidance | Execution quality | data-blocked | VPIN/risk ideas exist | Verified toxicity plus L2/spread | True toxicity history incomplete | Test as shadow skip filter | Blocked-winner cost exceeds losses saved | Stable recent positive net gate value |

## Derivatives And Forced Flow

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| Funding state | High-impact support | data-blocked | No verified historical funding ledger | Point-in-time funding history | Source inventory absent | Prioritize Bybit funding inventory | Publication timing/leakage unresolved | Stable recent conditioning value |
| Open-interest state | High-impact support | data-blocked | No verified historical OI ledger | Point-in-time OI history | Source inventory absent | Prioritize Bybit OI inventory | Gaps or publication timing unresolved | Stable recent conditioning value |
| Funding + OI squeeze | Forced-flow family | data-blocked | V9.2 backlog defined | Funding, OI, futures price/basis | Data foundation absent | Build after derivatives manifest | No recent post-cost edge | Walk-forward-stable recent edge |
| Liquidation cascade reversal/continuation | Forced-flow family | data-blocked | V9.2 backlog defined | Timestamped directional liquidations | Data foundation absent | Inventory Bybit liquidation source | Publication delay or incomplete coverage | Stable recent post-cost/latency edge |
| Long/short ratio | Crowding context | data-blocked | No verified history | Point-in-time ratio history | Source inventory absent | Inventory and audit | Unclear calculation/publication timing | Stable recent conditioning value |
| Perp basis/premium | Crowding context | data-blocked | No verified synchronized ledger | Spot/perp prices and index history | Data inventory absent | Add to derivatives foundation | No stable recent value | Stable squeeze/regime value |
| Whale aggressive flow | Recovered forced flow | data-blocked | Whale engine exists; static 5 BTC rule prohibited | Trade-level size distribution; L2 optional | No statistically normalized historical whale ledger | Build rolling-percentile large-flow feature | Static threshold or no recent value | Stable recent post-cost value |
| Static 5 BTC whale threshold | Automation guide | archived | Explicitly prohibited | None | Non-stationary and arbitrary | None | Always | Do not revive |

## Exit, Meta-Labeling, And Risk

| Concept | Origin | Status | Current Repo Status | Data Required | Current Blocker | Next Experiment | Kill Criteria | Revive Criteria |
|---|---|---|---|---|---|---|---|---|
| Fixed TP/SL | Legacy conversion | disproven | Multiple verified replays negative after costs | Verified paths | Cannot rescue D4 | Use only as benchmark | Negative raw alpha | Positive new alpha needs benchmark |
| CVD reversal exit | Dynamic exits | already tested | Negative after costs on D4 | Verified paths | Does not rescue D4 | Re-test only with positive new alpha | No incremental OOS value | Improves positive alpha recent expectancy |
| Time stop | Dynamic exits | already tested | Negative after costs on D4 | Verified paths | Does not rescue D4 | Re-test only with positive new alpha | No incremental OOS value | Improves positive alpha recent expectancy |
| Trailing after MFE | Dynamic exits | already tested | Negative after costs on D4 | Verified paths | Does not rescue D4 | Keep in exit lab for new alphas | No incremental OOS value | Improves positive alpha recent expectancy |
| Breakeven after MFE | Dynamic exits | already tested | Reduced losses but did not repair alpha | Verified paths | Negative raw expectancy | Keep as benchmark overlay | No incremental OOS value | Improves positive alpha recent expectancy |
| Partial/staged exits | Dynamic exits | already tested | Negative after costs on D4 | Verified paths | Does not rescue D4 | Re-test only with new positive alpha | No incremental OOS value | Improves positive alpha recent expectancy |
| Hard disaster stop | Risk control | under-tested | Supported in policy engines | Verified paths and live risk assumptions | Must remain separate from alpha/normal exit | Calibrate tail protection on positive candidates | Degrades expectancy without material tail benefit | Reduces ruin/tail risk acceptably |
| MFE/MAE and triple-barrier labels | Adaptive research | already tested | Deterministic labels/path ledgers exist | Verified paths | Labels not yet tied to a successful new feature family | Reuse for V9.2 eligibility models | Leakage or no recent mapping to expectancy | Stable recent cost-aware predictive value |
| Cost-aware meta-labeling | Adaptive research | V9.2 priority | First-pass predictive baselines weak | Multi-source feature ledger and labels | Current features insufficient; accuracy near random | Predict trade eligibility after costs, time-split only | No monotonic probability-to-expectancy mapping | Positive recent post-cost walk-forward replay |
| Walk-forward optimization | Adaptive research | already tested | Monthly walk-forward exists and rejected D4 | Immutable ledgers | Must be integrated into every new family | Full-sample-only evidence | Positive median test expectancy and split rate |
| Fractional Kelly sizing | Risk control | implementation-blocked | Capital replay exists; cannot create edge | Positive validated candidate | No positive alpha | Do nothing until alpha passes | Raw/filtered expectancy non-positive | Positive robust alpha exists |
| Drawdown/daily/weekly loss limits | Risk control | under-tested | Throttle concepts/engines exist | Positive candidate trade ledger | No alpha to protect | Evaluate only after candidate exists | Hides negative alpha or excessive opportunity loss | Improves ruin/tail risk without destroying edge |
| Max concurrent positions | Risk control | already tested | Occupancy replay exists | Immutable signals/paths | Alpha remains negative | Reuse for future candidates | Used to manufacture signal selection | Positive candidate requires portfolio replay |
| Macro event calendar gate | Risk control/context | data-blocked | No verified point-in-time calendar ledger | Timestamped release calendar and surprise values | Data source absent | Inventory source/publication times | Leakage or no recent net gate value | Stable recent blocked-loser value |

## Immediate Decisions

1. Do not revive D4 as a strategy.
2. Do not run new alpha sweeps before a regime ledger exists.
3. Prioritize verified historical Bybit L2 and derivatives inventory.
4. Treat existing L2/OFI/MLOFI/iceberg code as implementation scaffolding, not
   validated research.
5. Use dynamic exits and risk controls only after a new alpha has positive raw
   or filtered post-cost expectancy.
6. Use D4 as a benchmark feature in cost-aware meta-labeling, never as an
   automatic trade rule.
