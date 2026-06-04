# TM Trading v7.3 — Sub-Agent Research Synthesis: Grand Picture & Strategy Improvements

**Date**: 2026-06-04  
**Focus Mode**: ON  
**Context**: Spawned parallel sub-agent research on each core indicator in `features/` and `prime/` to extract best practices, edge preservation rules, and confluence opportunities. Goal: close the ~53% signal hit-rate to trade win-rate gap by smarter signal→trade conversion without diluting the primary CVD divergence edge.

## Sub-Agent Research Summaries (Parallel Passes)

### 1. Volume-Bar CVD Divergence (Core Edge — Protect at All Costs)
- **Key Insights from Research**: CVD divergence (price extension without delta confirmation) is one of the strongest order-flow exhaustion signals in futures/crypto perps. Works best on volume bars (not time bars). HTF flat CVD filter adds significant edge by avoiding counter-trend fades. D4 (simple divergence) slightly outperforms D5 (with delta reversal) in win-rate/ablation but D5 has fewer trades. ~53% signal hit-rate is real and measurable on 300 BTC bars, 40-lookback.
- **Best Practices**: Never dilute primary signal with too many filters. Use as *confirmation layer* or *conviction booster* for other confluence. Combine with footprint delta divergence for higher quality setups.
- **Risks**: Over-optimization on specific archives; regime shifts (high vol vs low). Keep deterministic and unit-tested.
- **Recommendation**: Keep D4 as default production signal. Make D5 opt-in. Add optional `confluence_boost` multiplier to signal strength when other agents confirm.

### 2. Footprint + Delta (Confluence King)
- **Key Insights**: Footprint charts reveal inside-bar dynamics (bid/ask volume, imbalances, absorption, stacked imbalances, delta clusters). Delta divergence inside footprint is early warning that complements bar-close CVD divergence. Stacked imbalances and absorption at divergence levels dramatically increase hit-rate in professional order-flow trading.
- **Best Practices**: Require footprint bias to match CVD side. Add stacked imbalance and absorption confirmation for high-conviction trades. Absorption (high volume no price move) at CVD divergence = strong smart-money defense/reversal signal.
- **Integration**: Already partially in `prime/footprint_confluence.py`. Expand it.
- **Recommendation**: Upgrade `footprint_confirms_fade` to `footprint_confluence_score(...)` returning 0-1 conviction. Include absorption flag, stacked bool, delta cluster strength. Use score > 0.6 to boost position size or tighten permission.

### 3. VPIN (Toxicity / Informed Flow Filter)
- **Key Insights**: VPIN measures probability of informed trading / order flow toxicity. High VPIN predicts short-term momentum and volatility spikes from adverse selection. Useful as regime or filter: extreme VPIN can mean toxic flow (avoid or tighten risk) or strong informed move (confirm with CVD alignment).
- **Best Practices**: Use as *contextual gate* not primary signal. Rising VPIN + CVD divergence in same direction = higher conviction continuation or reversal. High VPIN alone without CVD edge = noise.
- **Recommendation**: Add optional `--use-vpin-gate` in v73 runner. Compute VPIN on same volume bars. Filter or score down setups where VPIN is in top 10% without supporting CVD/footprint.

### 4. L2 Imbalance & Microprice (Precision Entry Timing)
- **Key Insights**: L2 order book imbalance (bid vs ask depth/volume) and Microprice (imbalance-weighted mid-price) are superior short-term predictors of next price move vs simple mid. Positive imbalance + CVD bullish divergence = high-probability long entry trigger. Microprice crossing the mid in signal direction provides precise, low-latency entry.
- **Best Practices**: Use for *entry execution* after signal generation, not for signal generation itself (preserve CVD edge). Combine with footprint for tape confirmation.
- **Recommendation**: In execution layer or Nautilus on_trade_tick / on_order_book, add microprice/imbalance trigger for limit order placement. Add to AlphaPermission as optional reason code.

### 5. Absorption, Iceberg, Spoofing (Smart Money & Trap Detection)
- **Key Insights**: Absorption (aggressive flow hitting hidden/resting size without price progress) signals institutional interest. Icebergs hide large size; detecting repeated fills at same level = hidden liquidity (often smart money accumulating/distributing). Spoofing (fake large limits that disappear) is manipulation to trap retail — detect and avoid or fade.
- **Best Practices**: At CVD divergence bar, presence of absorption or iceberg in opposing-to-price direction strengthens reversal case. Spoof detection near signal = potential fakeout, reduce size or skip.
- **Recommendation**: Integrate `features/absorption.py`, `iceberg.py`, `spoofing.py` outputs into confluence score. Add negative weight for spoof near signal. Positive for iceberg absorption confirming CVD fade.

### 6. Whale / Large Prints (Institutional Footprints)
- **Key Insights**: Large aggressive prints (whale trades) leave detectable signatures. Clusters of large prints in direction opposing price extension during divergence = exhaustion confirmation. Whale activity often precedes or confirms major reversals.
- **Best Practices**: Filter or boost signals when large prints align with CVD divergence side (or absorption). Avoid chasing if whales are fading the move.
- **Recommendation**: Enhance `features/whale.py` and `large_prints.py` usage in backtest manifests. Add to signal_scorecard as additional hit-rate dimension.

### 7. Auction State (Contextual Regime)
- **Key Insights**: Auction theory (balance/imbalance, acceptance/rejection) provides market context. In crypto, adapt to funding regimes, volatility clusters, or session-like boundaries (e.g., daily/weekly opens). Failed auctions or acceptance zones align well with order flow edges.
- **Best Practices**: Use as *permission overlay* — e.g., only take CVD fades in direction of higher-TF auction acceptance or avoid counter to current auction mode.
- **Recommendation**: Mature `prime/auction_state.py` and wire it as default-on regime gate in v73 (already partially done). Expand to multi-timeframe auction context for CVD.

## Grand Picture — Unified Strategy Vision

**Primary Signal (Non-Negotiable Edge)**: Volume-Bar CVD Divergence (D4 default) + HTF flat filter. This is the 53% hit-rate foundation. Do not add filters that reduce frequency below viable levels without proven lift in trade WR.

**Layered Confluence (Conviction & Filtering)**:
- Footprint: bias match + stacked + absorption (core booster)
- L2/Microprice: entry trigger + short-term direction confirmation
- VPIN: toxicity context (filter extremes or confirm strong flow)
- Whale/Iceberg/Absorption/Spoof: smart-money validation / trap avoidance
- Auction/Regime: higher-TF context gate

**Signal → Trade Pipeline Improvements**:
1. **Signal Generation**: CVD divergence → compute multi-factor conviction_score (0-1) from sub-agents above.
2. **Permission**: AlphaPermission V2 uses conviction + reason chain (CVD + footprint + L2 + no_spoof + whale_align). Only high-conviction or medium with regime pass.
3. **Entry**: After signal, wait for microprice/L2 trigger in signal direction or immediate if high conviction. Use footprint absorption confirmation for aggressive entry.
4. **Position Sizing**: Scale with conviction_score (e.g., base * (1 + 0.5*score)).
5. **Exit**: Dynamic — opposing CVD turn, footprint reversal, or absorption against position. Or time-based 5-vol-bar max with early exit on opposing flow. Target based on recent HVN or absorption levels.
6. **Risk**: VPIN-aware stops (wider in high toxicity). Fee-aware TP/SL already good; make dynamic.

**Expected Impact**: By requiring moderate confluence (e.g., footprint confirm + no spoof) we filter ~30-40% low-quality signals while keeping most of the edge, lifting trade win-rate toward 30%+ range while preserving expectancy. Backtests will validate.

**Multi-Agent Automation Alignment**: This synthesis follows the MULTI_AGENT_AUTOMATION_ROADMAP. Sub-agents (vibe/research) output structured hypotheses + metrics. Implementation (kilo) integrates validated pieces. Verifier (codex) runs ablations. Coordinator (jarvis) gates push.

## Recommended Next Stage (Stage 6 — Confluence & Dynamic Conversion)

- [ ] Upgrade `prime/footprint_confluence.py` to return conviction score incorporating absorption, stacked, and optional L2/VPIN inputs.
- [ ] Wire conviction into `prime/phase5_chunkb.py` or ChunkBBacktester for scoring and position sizing.
- [ ] Add optional vpin_gate, l2_trigger, whale_confirm CLI flags to v73 runners.
- [ ] Extend `research/signal_scorecard.py` to report per-confluence-dimension hit rates.
- [ ] Run targeted ablations on 2022-09 and full 6y with new confluence (protect baseline).
- [ ] Update `AlphaPermission` with new reason codes.
- [ ] Document in manifests and push checkpoint `stage-6-confluence`.

## Actionable Code Improvements (Implemented in this session)

1. Created this synthesis doc as source of truth for sub-agent findings.
2. (Next) Small enhancement to `prime/footprint_confluence.py` for absorption support (example below — will be committed after validation).

```python
# Example enhanced function (to be implemented)
def footprint_confluence_score(
    *,
    trade_side: int,
    footprint_bias: int,
    footprint_stacked: bool,
    absorption_confirmed: bool = False,
    require_stacked: bool = False,
    min_score: float = 0.5,
) -> float:
    """Return conviction score 0-1 for footprint alignment with CVD fade."""
    score = 0.5  # base
    if footprint_bias == trade_side:
        score += 0.3
    if footprint_stacked:
        score += 0.15
    if absorption_confirmed:
        score += 0.2  # strong smart money confirmation per research
    if require_stacked and not footprint_stacked:
        score = 0.0
    return max(0.0, min(1.0, score))
```

**Focus Mode Summary**: All research converged on protecting CVD divergence while intelligently layering footprint, L2, VPIN, and smart-money (whale/iceberg/absorption) context. This is the path to materially higher trade win rates without overfitting or breaking determinism.

**Next Steps for Human/Coordinator**: Review synthesis, approve Stage 6 cards on Hermes board, task kilo for implementation of enhanced confluence, run verifier on ablations.

---
*Generated via focused sub-agent parallel research on indicators. Committed to repo for team/agent continuity.*
