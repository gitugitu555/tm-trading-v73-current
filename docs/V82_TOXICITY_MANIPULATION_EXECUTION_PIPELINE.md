# TM Trading V8.2 — Toxicity, Manipulation & Execution Research Pipeline
*Evolution from V8.0 Honest Alpha Lab and V8.1 Institutional Microstructure Lab*

**Repository:** `gitugitu555/tm-trading-v73-current`

---

## 1. Executive Decision

Yes: V8.2 is advisable. The new research has value, especially around toxicity, MLOFI, manipulation-risk diagnostics, execution realism, and MAE/MFE exit research. However, V8.2 must remain diagnostics-first. Advanced and wild ideas are preserved in a separate future-trials section so they are not lost, but they are not allowed to contaminate the core build before the baseline is honest.

- **V8.2 Status:** Research roadmap / Codex implementation brief
- **Core rule:** No new advanced gate becomes live until shadow-mode evidence proves value.
- **Direct target:** Honest expectancy, drawdown reduction, and explainable loser removal.
- **Not a target:** Blindly optimizing for 85%+ win rate.

---

## 2. Version Lineage

- **V8.0 (Honest Alpha Lab):** No-lookahead replay, passive diagnostics, shadow gates, failure export.
- **V8.1 (Institutional Microstructure Lab):** MLOFI language, microprice drift, visible-depth normalization, MAE/MFE framing, multi-AI merge policy.
- **V8.2 (Toxicity, Manipulation & Execution Research Pipeline):** Toxicity engine, MLOFI engine, manipulation-risk diagnostics, execution realism model, MAE/MFE exit lab. *(This release)*
- **V8.3 (Proven Gate Activation):** Only activate filters that V8.0-V8.2 shadow evidence proves useful.
- **V8.4 (Regime V2):** Regime-specific permission tables and toxicity-aware signal weights.
- **V8.5 (Sizing & Staged Entries):** Conviction sizing, staged entry, risk-adjusted allocation.
- **V10+ (Advanced Agentic / RL Research):** GRPO, Hawkes/MMHP, simulator-based execution agents, adversarial market games.

---

## 3. V8.2 Core Principle

V8.2 should not chase an 85% win rate directly. High win rate may emerge from avoiding toxic flow, removing bad regimes, improving fill realism, and exiting invalidated trades earlier. The real target is an honest next-bar baseline with positive expectancy, stable trade count, lower drawdown, and explainable blocked losers.

- Every new signal begins as passive diagnostics.
- Every proposed gate runs in shadow mode before it can block trades.
- Every exit rule runs as an ablation before it can replace existing exit logic.
- Every advanced model must prove incremental value over simple baselines.

---

## 4. V8.2 Core Modules

### 4.1 Toxicity Engine
The toxicity engine turns VPIN and related flow-toxicity measures into a stateful diagnostic layer. It should not be a single static threshold such as VPIN > 0.55. It should track level, slope, fast-vs-slow spread, and session-relative percentile.

- `vpin_level`: Current VPIN or toxicity proxy.
- `vpin_fast`: Short-window VPIN.
- `vpin_slow`: Long-window VPIN baseline.
- `vpin_slope`: Rate of toxicity increase/decrease.
- `vpin_fast_minus_slow`: Fast toxicity relative to baseline.
- `vpin_session_percentile`: Toxicity relative to the same UTC/session bucket.
- `toxicity_state`: `BENIGN`, `RISING_TOXICITY`, `HIGH_TOXICITY`, `FALLING_TOXICITY`, `UNKNOWN`.

```python
# features/toxicity.py
class ToxicityState(Enum):
    BENIGN = "BENIGN"
    RISING_TOXICITY = "RISING_TOXICITY"
    HIGH_TOXICITY = "HIGH_TOXICITY"
    FALLING_TOXICITY = "FALLING_TOXICITY"
    UNKNOWN = "UNKNOWN"
```

### 4.2 MLOFI Engine
MLOFI means Multi-Level Order Flow Imbalance. It replaces a naive single L2 imbalance snapshot with a vector across near, mid, and far book levels, plus dynamics and agreement/disagreement between depth zones.

- `l1_imbalance`: Top-of-book imbalance.
- `l3_imbalance`: First 3 levels.
- `l5_imbalance`: First 5 levels.
- `l10_imbalance`: First 10 levels.
- `near_book_imbalance`: Pressure closest to executable price.
- `far_book_imbalance`: Deeper book pressure.
- `imbalance_slope`: Change rate across recent bars/snapshots.
- `book_agreement_score`: Whether near and far book pressure agree.
- `book_trap_score`: Divergence between near retail pressure and far institutional pressure.

### 4.3 Manipulation-Risk Diagnostics
This module is defensive. It detects spoofing/layering/quote-burst risk so the strategy can reduce confidence or avoid entries in suspicious conditions. It must not implement manipulative behaviour.

- `large_wall_added`: Large visible order/wall appears.
- `large_wall_removed`: Large visible order/wall disappears before execution.
- `wall_lifetime_ms`: How long the wall stayed visible.
- `cancel_to_add_ratio`: Excessive cancellation pressure versus placement.
- `spoof_removal_direction`: Direction implied by removal of fake liquidity.
- `quote_burst_score`: Rapid quote add/cancel burst diagnostic.
- `manipulation_risk_score`: Composite risk score for shadow blocking/confidence reduction.

### 4.4 Execution Realism Model
After same-bar lookahead is removed, the next inflation risk is assuming perfect fills. V8.2 should add an execution-realism model that estimates spread, slippage, queue penalty, and effective entry price. This should first run as a report overlay.

- `next_bar_entry_price`: Price used when `entry_lag_bars=1`.
- `spread_bps`: Bid/ask spread cost at execution time.
- `slippage_bps`: Estimated slippage against chosen executable price.
- `queue_penalty_bps`: Penalty for not having first queue priority.
- `effective_entry_price`: Entry after spread/slippage/queue penalty.
- `execution_quality_score`: Diagnostic score for fill realism.

### 4.5 MAE/MFE Exit Research Lab
MAE/MFE profiling learns how winning and losing trades behave after entry, split by regime, signal family, session hour, volatility bucket, and toxicity state.

- **MAE by regime:** How far winners/losers usually move against the trade.
- **MFE by regime:** How much favourable movement appears before decay.
- **MAE by signal family:** Different stop logic for CVD fade vs footprint vs absorption.
- **Optimal time stop:** Number of bars after which edge decays.
- **Invalidation exit test:** Exit when entry premise dies rather than waiting for stop.

---

## 5. V8.2 Shadow Gate Expansion

All gates below run in shadow mode first. They produce would-have-blocked reports but do not alter entries.

| Gate | Description | Mode |
|---|---|---|
| `toxicity_rising_gate` | Block if toxicity is rising faster than threshold. | Shadow only |
| `vpin_fast_above_slow_gate` | Block if current toxicity exceeds baseline. | Shadow only |
| `mlofi_book_agreement_gate` | Require near/far book agreement. | Shadow only |
| `book_trap_gate` | Block near/far disagreement trap conditions. | Shadow only |
| `manipulation_risk_gate` | Block high manipulation-risk score. | Shadow only |
| `execution_quality_gate` | Block poor fill-quality conditions. | Shadow only |
| `mae_profile_gate` | Compare expected MAE to learned winner profile. | Shadow only |

---

## 6. End-of-Run Reporting Requirements

V8.2 must produce institutional-style attribution:
- Trades kept, trades blocked, blocked winners, blocked losers.
- Hypothetical win rate if each gate were active.
- Hypothetical expectancy, average R, max drawdown, and trade count.
- Long/short split, regime split, session-hour split, toxicity-state split.
- Execution-adjusted results using `effective_entry_price`.
- MAE/MFE distribution tables and percentile stops.

```json
// Example JSON Summary Output
{
  "gate": "toxicity_rising_gate",
  "evaluable_trades": 4812,
  "would_block": 904,
  "blocked_winners": 188,
  "blocked_losers": 716,
  "hypothetical_trade_count": 3908,
  "hypothetical_win_rate": 0.684,
  "expectancy_delta_r": 0.11
}
```

---

## 7. Implementation Order

1. **Correctness Core Verification:** Keep Stage 0 correctness completed first (lag=1 execution baseline).
2. **Add `toxicity.py` Diagnostics:** Expose VPIN state, slope, fast/slow, session percentile.
3. **Add `mlofi.py` Diagnostics:** Multi-level L2 imbalance vector and book agreement.
4. **Add `manipulation_risk.py` Diagnostics:** Wall, cancel/add ratio, spoof-removal and burst scores.
5. **Add `execution/realism.py` Overlay:** Effective entry price and fill-quality scoring.
6. **Add `research/mae_mfe_exit_lab.py`:** Exit ablation data and percentile profiles.
7. **Extend Shadow-Gate Reporting:** Implement attribution aggregates per gate family.
8. **Create Documentation:** Ensure `docs/V82_TOXICITY_MANIPULATION_EXECUTION_PIPELINE.md` contains explicit implementation instructions.

---

## 8. V8.2 Codex Prompt
*Use this prompt only after V8.0/V8.1 correctness and diagnostics are stable.*

You are working in repository `gitugitu555/tm-trading-v73-current`.

Create `TM Trading V8.2 - Toxicity, Manipulation & Execution Research Pipeline`.

**Goal:**  
Add passive diagnostics and shadow-mode reporting for toxicity, MLOFI, manipulation risk, execution realism, and MAE/MFE exit research. Do not activate new live gates yet.

**Implement:**
1. `features/toxicity.py`
2. `features/mlofi.py`
3. `features/manipulation_risk.py`
4. `execution/realism.py`
5. `research/mae_mfe_exit_lab.py`
6. Expose the 7 shadow gates listed in the roadmap.

---

## 9. Future Improvements and Wild Trials

Do not discard advanced ideas. Store them here for future trials after the simulator, data foundation, and cost model are robust enough.

### 9.1 MMHP Manipulation Detection
Model bursts of order submissions, cancellations, and aggressive prints as self-exciting event processes (Markov-Modulated Hawkes Processes) to detect spoof/layering regimes.

### 9.2 GRPO / Reinforcement Learning Execution Agent
Reinforcement learning execution agent trained on simulator states to minimize trading costs and avoid adverse selection.

### 9.3 Agent-Based Market Simulator
Simulate LPs, retail flow, spoofers, and whales to stress-test gates against liquidity shocks and adversarial regimes.

### 9.4 Causal Inference Gate Testing
Estimate whether a gate truly causes improved expectancy using matched trades, regime controls, and adversarial validation.

### 9.5 Conformal Risk Filters
Conformal prediction layers to yield uncertainty bands and refuse trades when primary signal confidence is statistically weak.

### 9.6 Online Learning & Drift Detection
Detect when signal behavior drifts across months or exchange regimes and trigger drift alarms.

### 9.7 Cross-Market and On-Chain Fusion
Fuse BTC perp-spot basis, liquidations, OI, stablecoin flows, and exchange inflows/outflows.

### 9.8 Whale Intent Classifier
Classify whale prints as initiating, absorbing, stop-running, or chasing.

### 9.9 Swarm Research Agents
Assign independent agents to CVD, VPIN, MLOFI, footprint, execution, and exits to validate metrics before merging.

---

## 10. V8.2 Acceptance Checklist

| Criterion | Definition | Status |
|---|---|---|
| **Passive preservation** | Diagnostics do not change trade count or entries. | Required |
| **Coverage** | Every completed trade receives toxicity/MLOFI/execution/MAE-MFE payload. | Required |
| **Shadow summaries** | Each proposed gate reports blocked winners/losers, WR, and expectancy impact. | Required |
| **Execution overlay** | Backtest can report raw result and execution-adjusted result. | Required |
| **Exit lab** | MAE/MFE reports can be produced by regime, signal family, and toxicity state. | Required |
| **Future trials preserved** | Advanced ideas are documented but not implemented prematurely. | Required |
