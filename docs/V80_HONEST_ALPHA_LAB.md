# TM Trading V8.0 — Honest Alpha Lab Roadmap

A clean research release plan for correctness, no-lookahead replay, signal diagnostics, shadow-mode gates, and failure export.

**Version target:** V8.0.0 to V8.0.4  
**Repository:** `gitugitu555/tm-trading-v73-current`

---

## Executive Decision

Yes: creating V8.0 is advisable. But V8.0 should not be a hype release that adds many hardcoded filters at once. It should be the clean institutional research version that proves the edge honestly before optimisation.

- **V8.0** = honest baseline + diagnostics + ablation lab
- **V8.1** = adaptive volume bars
- **V8.2** = regime classifier V2
- **V8.3** = proven gates activated
- **V8.4** = exit optimisation
- **V8.5** = staged sizing / conviction sizing

### V8.0 Mission
- Fix correctness issues before chasing higher win rate.
- Measure the honest six-year next-bar baseline.
- Instrument every signal so future filters can be proven with evidence.
- Run candidate gates in shadow mode before allowing them to block trades.
- Export every losing trade with enough diagnostics for Hermes/Codex failure classification.
- Prepare the system for V8.1/V8.2 optimisation without overfitting.

### What V8.0 Is Not
- Not an immediate 80% win-rate claim.
- Not a package of 20 new hardcoded filters.
- Not a regime/VPin/whale optimisation release.
- Not a position-sizing overhaul.
- Not a version where trade count collapses and win rate looks artificially high.

---

## Recommended Build Phases

| Phase | Name | Purpose | Strategy impact |
|---|---|---|---|
| **V8.0.0** | Correctness Core | Fix report bug, add entry lag, tag lookahead metadata. | Yes, but controlled by flag |
| **V8.0.1** | Signal Diagnostics | Add passive derived metrics for CVD, VPIN, microprice, footprint, absorption, and whale signals. | No |
| **V8.0.2** | Shadow Gates | Evaluate candidate filters in what-if mode without blocking trades. | No |
| **V8.0.3** | Failure Export | Export trade diagnostics, MAE/MFE, exit reason, and failure_bucket=null. | No |
| **V8.0.4** | Exit Ablation Prep | Prepare signal-invalidation/time-stop/delta-exhaustion research. | Flagged only |

---

## Phase Details

### Stage 0: Correctness Core
This stage must happen before any alpha or win-rate optimisation. It determines whether the current results are genuinely executable or partly inflated by same-bar execution assumptions.
1. Fix the missing `Counter` import in `scripts/chunk_b_backtest_cached.py`.
2. Add `--entry-lag-bars` with allowed values `0` and `1`.
3. Preserve legacy behaviour when `--entry-lag-bars 0`.
4. When `--entry-lag-bars 1`, compute signal on completed bar N and execute entry on bar N+1.
5. Add result metadata: `entry_lag_bars`, `same_bar_entry`, `lookahead_safe`.
6. Add tests proving `lag=0` parity and `lag=1` no same-bar entry.

```python
from collections import Counter, deque

{
  "entry_lag_bars": 1,
  "same_bar_entry": false,
  "lookahead_safe": true
}
```

#### Lag Test Interpretation

| Result | Meaning |
|---|---|
| **Lag 0 = 63%, Lag 1 = 60-62%** | Healthy. Edge likely survives execution realism. |
| **Lag 0 = 63%, Lag 1 = 55-58%** | Usable but needs adaptive bars, failure export, and regime work before judging. |
| **Lag 0 = 63%, Lag 1 < 52%** | Current edge may be mostly replay artefact. Rebuild execution discipline first. |

---

### Stage 1: Signal Metric Extraction
Add metrics passively. Do not change entry or exit decisions in this phase.

#### CVD
- `relative_delta`
- `cvd_slope_3`
- `cvd_slope_5`
- `cvd_acceleration`
- `cvd_divergence_magnitude`
- `cvd_short_horizon`
- `cvd_medium_horizon`
- `cvd_long_horizon`

#### VPIN
- `vpin_fast`
- `vpin_slow`
- `vpin_slope`
- `vpin_fast_minus_slow`
- `vpin_session_percentile`

#### Microprice
- `microprice`
- `microprice_displacement_bps`
- `microprice_drift_3`
- `microprice_drift_5`

#### L2 / Book
- `near_book_imbalance`
- `far_book_imbalance`
- `imbalance_change_rate`
- `book_agreement`
- `refill_score`

#### Footprint
- `stacked_imbalance_depth`
- `poc_migration`
- `unfinished_high`
- `unfinished_low`
- `delta_at_poc`
- `delta_at_extremes`

#### Absorption
- `absorption_rate`
- `consecutive_absorption_bars`
- `absorption_at_structural_level`

#### Whale
- `whale_significance_vs_book_depth`
- `whale_position_in_bar`
- `whale_cvd_alignment`

---

### Stage 2: Shadow-Mode Gates
Candidate filters should first run in diagnostics-only mode. They must report what they would have blocked, without changing trade count.

```json
{
  "gate_name": "microprice_displacement",
  "passed": true,
  "value": -0.8,
  "threshold": 0.0,
  "would_block_trade": false
}
```

- `cvd_relative_delta_gate`
- `cvd_slope_alignment_gate`
- `microprice_displacement_gate`
- `vpin_fast_below_slow_gate`
- `absorption_consecutive_gate`
- `footprint_stacked_depth_gate`
- `session_hour_gate_placeholder`

#### Shadow-Gate Summary Requirements
- evaluable trades
- passed trades
- failed trades
- winners blocked
- losers blocked
- hypothetical trade count
- hypothetical win rate
- expectancy impact if available

**Example Output:**
```text
Gate: microprice_displacement
Trades evaluable: 4,812
Would block: 1,204
Blocked winners: 311
Blocked losers: 893
Hypothetical win rate: +6.2%
Trade count reduction: -25.0%
Expectancy change: +0.18R
```

---

### Stage 3: Failure Export
Every completed trade should export a diagnostics payload that can be analysed later by Hermes/Codex. `failure_bucket` starts as `null` and is classified later.

```json
{
  "signal_ts": "...",
  "entry_ts": "...",
  "exit_ts": "...",
  "side": "long",
  "regime": "RANGING_LOW_VOL",
  "session_hour_utc": 14,
  "relative_delta": 0.42,
  "cvd_slope_5": 123.4,
  "vpin_fast": 0.48,
  "vpin_slow": 0.52,
  "microprice_displacement_bps": -0.8,
  "mae": -0.35,
  "mfe": 0.92,
  "exit_reason": "TIME_STOP",
  "pnl": 0.41,
  "win": true,
  "failure_bucket": null
}
```

---

### Stage 4: Exit Ablation Lab
Exit logic may be the largest practical win-rate lever. Test each exit independently before combining them.

| Exit Ablation | Rule Idea | Purpose |
|---|---|---|
| **E1** | Signal invalidation exit | Exit when the original reason for entry no longer holds. |
| **E2** | Delta exhaustion exit | Exit when relative delta flips hard against the trade. |
| **E3** | Time stop after N bars | Exit stale trades where short-duration edge has decayed. |
| **E4** | MAE-derived stop by regime | Use historical winning-trade MAE to set data-derived stops. |
| **E5** | Partial exit + trailing remainder | Book partial wins while preserving upside tail. |

---

## Deep Signal Improvement Notes for Later V8.x
These ideas are valuable, but should not become hard gates until the V8.0 diagnostics prove they block more losers than winners without destroying trade count.

### CVD Engine
- Use CVD divergence magnitude, not just positive/negative CVD.
- Normalise delta by bar volume with `relative_delta`.
- Measure CVD slope and acceleration over 3-5 bars.
- Use multi-horizon CVD instead of one arbitrary reset window.

### Footprint Engine
- Quantify stacked imbalance depth instead of binary stacked/not-stacked.
- Track POC migration direction.
- Add unfinished auction levels.
- Split delta at POC versus delta at extremes.

### VPIN
- Use VPIN slope and fast-vs-slow VPIN, not only absolute level.
- Normalise VPIN by session-hour baseline.

### Microprice
- Use microprice displacement at entry time to avoid chasing.
- Track microprice drift over 3 and 5 bars.

### L2 Imbalance
- Use imbalance change rate rather than static snapshot only.
- Split near-book and far-book imbalance.
- Measure book refill/resilience after large prints.

### Absorption
- Measure absorption rate.
- Track consecutive absorption bars.
- Require structural-level context before treating absorption as a primary signal.

### Iceberg / Spoofing
- Use iceberg side and location as directional intelligence.
- Treat spoof removal as a potential reversal contributor.

### Whale Composite
- Normalise large prints by visible book depth.
- Classify whale intent by position in bar.
- Boost only when whale direction aligns with CVD.

### What Not To Hardcode Yet
- VPIN > 0.55 block
- `stacked_imbalance_depth` >= 5 block
- `whale_significance_vs_book_depth` > 0.02 block
- max_hold_bars = 8
- full three-tier gate architecture
- conviction-based sizing
- staged entries

---

## Codex Prompt: Create V8.0
Paste this directly into Codex after Stage 0 context is clear. It is intentionally scoped to correctness and instrumentation.

You are working in repository `gitugitu555/tm-trading-v73-current`.

Create `TM Trading V8.0 — Honest Alpha Lab`.

**Goal:**  
Create a new V8.0 research version focused on correctness, no-lookahead replay, signal diagnostics, shadow-mode gates, and failure export. Do not implement aggressive alpha filters yet.

**Version philosophy:**  
V8.0 is not an 80% win-rate claim. V8.0 is the version that proves the honest six-year baseline and gives us the instrumentation needed to safely reach higher win rate later.

### Phase 1 — Correctness Core:
- Fix missing `Counter` import in `scripts/chunk_b_backtest_cached.py`.
- Add `--entry-lag-bars`.
- Default: `0` for legacy parity.
- Support: `0` and `1`.
- `0` = current same-bar behaviour.
- `1` = signal on completed bar N, entry on bar N+1.
- Add result metadata: `entry_lag_bars`, `same_bar_entry`, `lookahead_safe`.
- Add tests proving lag=0 preserves parity and lag=1 prevents same-bar entry.

### Phase 2 — Signal Diagnostics:
Add passive diagnostic fields to trade/signal exports. Do not change trade decisions.
Include:
- `relative_delta`
- `cvd_slope_3`
- `cvd_slope_5`
- `cvd_acceleration`
- `cvd_divergence_magnitude`
- `cvd_short_horizon`
- `cvd_medium_horizon`
- `cvd_long_horizon`
- `vpin_fast`
- `vpin_slow`
- `vpin_slope`
- `vpin_fast_minus_slow`
- `microprice_displacement_bps`
- `microprice_drift_3`
- `microprice_drift_5`
- `stacked_imbalance_depth`
- `poc_migration`
- `absorption_rate`
- `consecutive_absorption_bars`
- `whale_significance_vs_book_depth`
- `whale_cvd_alignment`

If data is unavailable in the current cache path, use `None` and document the missing dependency.

### Phase 3 — Shadow Gates:
Add diagnostics-only gates. They must not block trades yet.
Initial shadow gates:
- `cvd_relative_delta_gate`
- `cvd_slope_alignment_gate`
- `microprice_displacement_gate`
- `vpin_fast_below_slow_gate`
- `absorption_consecutive_gate`
- `footprint_stacked_depth_gate`
- `session_hour_gate_placeholder`

Each gate should report:
- gate name
- passed
- value
- threshold
- would_block_trade

End-of-run summary per gate:
- evaluable trades
- passed trades
- failed trades
- winners blocked
- losers blocked
- hypothetical trade count
- hypothetical win rate
- expectancy impact if available

### Phase 4 — Failure Export:
Every completed trade should export:
- signal timestamp
- entry timestamp
- exit timestamp
- side
- regime
- session hour UTC
- diagnostics payload
- MAE
- MFE
- exit reason
- PnL
- win/loss boolean
- `failure_bucket = null`

### Phase 5 — Version Documentation:
Create or update docs:
- `docs/V80_HONEST_ALPHA_LAB.md` (this file)

### Constraints:
- Do not implement adaptive volume bars yet.
- Do not implement regime classifier V2 yet.
- Do not implement VPIN hard gates yet.
- Do not implement staged entries yet.
- Do not implement position sizing changes yet.
- Preserve legacy parity when `--entry-lag-bars 0`.
- Keep every strategy-impacting change behind explicit flags.
- Add tests for correctness and diagnostics.
