# TM Trading V8.1 — Institutional Microstructure Lab
*Evolutionary addendum to V8.0 Honest Alpha Lab*

**Repository:** `gitugitu555/tm-trading-v73-current`

---

## 1. Executive Verdict

Yes, Gemini adds value. The value is not the headline target of 85%+ win rate. The value is the institutional vocabulary and research decomposition: execution illusion tax, VPIN toxicity dynamics, microprice drift, multi-level order-flow imbalance (MLOFI), visible-depth normalization, and MAE/MFE exit ablation.

V8.1 should therefore evolve V8.0 from an Honest Alpha Lab into an Institutional Microstructure Lab. It should still avoid premature hardcoded filters. All new logic must first run in passive diagnostics or shadow-mode ablation.

---

## 2. V8.0 vs V8.1 Comparison

| Area | V8.0 Honest Alpha Lab | V8.1 Institutional Microstructure Lab |
|---|---|---|
| **Execution** | No-lookahead entry lag, lag=0 vs lag=1 baseline. | Adds execution illusion tax metric and optional slippage/latency diagnostics. |
| **Signals** | Passive diagnostics across CVD, VPIN, microprice, footprint, absorption, whale. | Adds MLOFI, toxicity dynamics, liquidity normalization, and signal half-life fields. |
| **Gates** | Shadow gates only; no live blocking. | Shadow gates become grouped by microstructure family and report edge contribution by family. |
| **Exits** | Failure export and basic exit ablation preparation. | Dedicated MAE/MFE profile engine and exit ablation matrix. |
| **Optimization** | Prepare evidence for V8.1/V8.2. | Prepare evidence for selective gate activation in V8.2; still no blind hardcoding. |

---

## 3. Non-Negotiable Principles

- No optimization before Stage 0 correctness is complete.
- `lag=0` must remain available only as legacy parity; `lag=1` is the honest research baseline.
- Every new signal first runs as passive diagnostics or shadow gate, never direct live blocking.
- Win rate is not the primary target; expectancy, drawdown, trade count, regime stability, and explainable loser reduction matter more.
- No hardcoded institutional-sounding thresholds unless shadow-mode data proves they add expectancy without destroying sample size.

---

## 4. Valuable Gemini Additions to Keep

| Gemini Concept | Keep? | Why | Implementation Mode |
|---|---|---|---|
| **Execution illusion tax** | Yes | Quantifies the cost of same-bar execution assumptions. | Core report metric. |
| **MLOFI** | Yes | More rigorous than a single L2 imbalance snapshot. | Passive diagnostics first. |
| **VPIN toxicity dynamics** | Yes | VPIN level alone is weaker than level + slope + fast/slow spread. | Shadow-mode toxicity gates. |
| **Microprice drift estimation** | Yes | Clean intrabar timing tool for avoiding chased entries. | Diagnostics and shadow gate. |
| **Visible-depth liquidity normalization** | Yes | Makes whale/large-print events context-aware. | Diagnostics; no hard threshold yet. |
| **MAE/MFE exit ablation** | Strong yes | Likely one of the biggest win-rate and expectancy levers. | Dedicated V8.1 module. |
| **85%+ win-rate target** | No | Can cause overfit and bad tail risk. | Aspirational only; not optimization target. |

---

## 5. V8.1 Microstructure Architecture

### 5.1 Execution Illusion Tax
Definition: the performance delta between legacy same-bar execution and honest next-bar execution.

```json
{
  "lag0_win_rate": 0.63,
  "lag1_win_rate": 0.58,
  "execution_illusion_tax_win_rate_points": 5.0,
  "lag0_expectancy_r": 0.18,
  "lag1_expectancy_r": 0.07,
  "execution_illusion_tax_expectancy_r": 0.11
}
```
*Interpretation:* If the tax is small, the edge is likely structurally real. If the tax is large, alpha work must stop until replay and execution realism are repaired.

### 5.2 MLOFI: Multi-Level Order-Flow Imbalance
V8.0 says L2 imbalance. V8.1 should upgrade the research vocabulary to MLOFI. A single top-of-book imbalance can be stale or spoof-prone. Multi-level imbalance separates near-book urgency from far-book liquidity walls.

$$\text{near\_imbalance} = \frac{\text{bid\_depth\_1\_3} - \text{ask\_depth\_1\_3}}{\max(\text{bid\_depth\_1\_3} + \text{ask\_depth\_1\_3}, \epsilon)}$$

$$\text{far\_imbalance} = \frac{\text{bid\_depth\_4\_10} - \text{ask\_depth\_4\_10}}{\max(\text{bid\_depth\_4\_10} + \text{ask\_depth\_4\_10}, \epsilon)}$$

- `book_agreement = sign(near_imbalance) == sign(far_imbalance)`
- `imbalance_change_rate = near_imbalance_t - near_imbalance_t_minus_3`

### 5.3 VPIN Toxicity Dynamics
VPIN should not be a single hard threshold in V8.1. Use fast/slow spread, slope, and session percentile to detect rising adverse-selection risk.
- `vpin_fast_minus_slow = vpin_fast - vpin_slow`
- `vpin_slope = vpin_t - vpin_t_minus_n`
- `vpin_session_percentile = percentile_rank(vpin_t, history_for_same_utc_hour)`

### 5.4 Microprice Displacement and Drift
Microprice is the cleanest proposed entry-timing diagnostic. It should be measured at intended execution time, not only signal time.

$$\text{microprice} = \frac{(\text{best\_ask} \times \text{bid\_size}) + (\text{best\_bid} \times \text{ask\_size})}{\max(\text{bid\_size} + \text{ask\_size}, \epsilon)}$$

$$\text{displacement\_bps} = 10000 \times \frac{\text{trade\_price} - \text{microprice}}{\max(\text{microprice}, \epsilon)}$$

- `drift_3 = microprice_t - microprice_t_minus_3`

### 5.5 Visible-Depth Normalization
Large prints and whale events should be scaled by visible book depth. A 100 BTC print is not the same event in a thin book and a thick book.
- `whale_significance_vs_book_depth = large_print_size / max(visible_book_depth, epsilon)`

### 5.6 MAE/MFE Exit Ablation Engine
This is the highest-value Gemini addition. V8.1 should explicitly profile winning and losing trades by maximum adverse excursion (MAE), maximum favourable excursion (MFE), hold time, regime, and exit reason.

```json
{
  "trade_id": "...",
  "regime": "RANGING_LOW_VOL",
  "side": "long",
  "mae_r": -0.42,
  "mfe_r": 1.15,
  "hold_bars": 6,
  "exit_reason": "TIME_STOP",
  "win": true
}
```

---

## 6. V8.1 Implementation Plan

1. **V8.1.0 - Microstructure Research Schema:** Define a unified diagnostics schema for execution tax, MLOFI, VPIN dynamics, microprice drift, visible-depth normalization, and MAE/MFE.
2. **V8.1.1 - MLOFI Diagnostics:** Add near/far book imbalance, book agreement, imbalance change rate, and refill/resilience placeholders.
3. **V8.1.2 - Toxicity Diagnostics:** Add VPIN fast/slow/slope/session percentile fields; no hard VPIN gate yet.
4. **V8.1.3 - Microprice Timing Diagnostics:** Add displacement and drift at signal time and intended entry time.
5. **V8.1.4 - Liquidity-Normalized Whale Diagnostics:** Normalize whale and large-print events by visible book depth when available.
6. **V8.1.5 - MAE/MFE Exit Ablation Matrix:** Export MAE/MFE/hold-time distributions by regime and test exit rules in shadow mode.
7. **V8.1.6 - Microstructure Family Attribution Report:** Summarize which signal families block losers, block winners, improve expectancy, or destroy trade count.

---

## 7. Codex Prompt: V8.1 Evolution
*Use this only after V8.0 Stage 0 correctness is merged and lag=1 baseline is measured.*

You are working in repository `gitugitu555/tm-trading-v73-current`.

Create `V8.1: Institutional Microstructure Lab`.

**Precondition:**
- V8.0 Stage 0 no-lookahead correctness must already exist.
- Do not change live trading decisions.
- Do not activate hard gates.
- All additions are passive diagnostics, shadow-mode ablations, or reporting.

**Goal:**  
Evolve V8.0 Honest Alpha Lab by adding institutional microstructure diagnostics from the Gemini research review:
- execution illusion tax
- MLOFI / multi-level order-flow imbalance
- VPIN toxicity dynamics
- microprice displacement and drift
- visible-depth liquidity normalization
- MAE/MFE exit ablation
- microstructure family attribution

---

## 8. Evolution Path After DeepSeek and MiniMax Reviews

Keep V8.1 modular so DeepSeek and MiniMax can add research without forcing another rewrite. Use this merge policy:
- If a new idea changes live trades, demote it to shadow-mode first.
- If a new idea adds a signal, add it as a passive diagnostic field first.
- If a new idea adds a threshold, require blocked-winner/blocked-loser attribution before activation.
- If a new idea claims a win-rate improvement, require lag=1 six-year evidence and trade-count impact.
- If a new idea improves exits, test it in the MAE/MFE ablation matrix before modifying production exits.

---

## 9. What V8.1 Still Does Not Do

- It does not claim or optimize directly for 85% win rate.
- It does not activate VPIN, MLOFI, microprice, whale, or footprint gates live.
- It does not introduce adaptive position sizing.
- It does not replace the regime classifier yet.
- It does not allow same-bar execution to be treated as honest performance.

---

## 10. V8.1 Acceptance Checklist

| Requirement | Pass Condition | Status |
|---|---|---|
| **No-lookahead baseline respected** | Lag=1 results are labelled lookahead_safe=true. | Required |
| **Diagnostics passive** | Trade count unchanged with diagnostics enabled. | Required |
| **Execution illusion tax** | Lag=0 vs lag=1 performance delta report exists. | Required |
| **MLOFI fields** | Near/far imbalance and book agreement exported or None with TODO. | Required |
| **VPIN dynamics** | Expose fast/slow/slope fields or None with TODO. | Required |
| **Microprice timing** | Signal and entry displacement fields exported or None with TODO. | Required |
| **MAE/MFE export** | Completed trades include MAE/MFE/hold-time fields. | Required |
| **Family attribution** | Report groups diagnostics by signal family. | Required |
