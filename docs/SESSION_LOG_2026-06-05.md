# Session Log — 2026-06-05 (v7.3 cache, backtest tuning, win-rate & expectancy sweeps)

## Repo

- **Remote:** https://github.com/gitugitu555/tm-trading-v73-current
- **Local:** `/home/tokio/tm-trading-v73-current`
- **Research PYTHONPATH:** `/home/tokio/tm-trading-research` (symlink `research/` → manifests + scorecard)
- **Shared cache:** `results/indicator_cache/*.threshold-300.parquet` on NVMe (~134 archives)

---

## Goals this session

1. Confirm cache builders run **offline** (no internet) after disconnect.
2. Ramp to **28 concurrent** `cache_indicators.py` workers (300 + 100 thresholds).
3. Run **full 6y backtest** when 300-threshold caches completed.
4. Pursue **70% trade win rate** on 6 months (cached data), then pivot to **expectancy / Sharpe** (option 3).

---

## What we built / ran

### Cache pipeline (worked)

| Item | Status |
|------|--------|
| `scripts/ensure_cache_builders.sh` | Auto-replenish/heal; default `--max 32`; `setsid` + `nohup` |
| `logs/cache_manager.pid` / `cache_manager.log` | Manager survives SSH/logout |
| 300-threshold caches | **133/133** main archives + `_1m` special — **complete** |
| 28 builders (14×300 + 14×100 stragglers) | Ran detached; verified **zero TCP** on worker PIDs |
| Internet off | Safe: local zips → parquet only |

**Cheat sheet:** end of `cache_self_management.sh` (manager start/stop, tail logs).

### Backtest — baseline 6y (completed earlier in session)

**Script:** `scripts/v73_backtest_6y_incremental.py --resume`  
**Output:** `results/v73_backtest_6y_volume_bar_cvd.json`

| Metric | Value |
|--------|-------|
| Archives | 132 |
| Trades | 6,110 |
| **Win rate** | **44.4%** |
| Signal hit rate | 54.6% |
| PnL | -$5,095 |
| Sharpe | -9.95 |
| Stop / target | 0.45% / 0.15% (defaults) |

Caches are suitable for strategy backtests (volume-bar CVD + footprint/regime columns in parquet).

---

## Win-rate optimization (70% target) — did not work

### Sweeps run

| Sweep | Configs | Period | Best trade WR | ≥70% configs |
|-------|---------|--------|---------------|--------------|
| `scripts/v73_sweep_6m.py` | 296 | Dec 2024–May 2025 | 42.0% (`tight_minimal`, no invert) | **0** |
| `scripts/v73_sweep_invert_6m.py` | 82 | same 6m | **57.4%** (`inv_t0.0015_lb100`) | **0** |
| Ultra grid (invert, 0.15% target) | 48 | same 6m | 57.4% | **0** |

### What worked (win rate, not PnL)

**Best 6m config — high WR, still loses money:**

```bash
--invert-signal-side
--no-use-regime-gate-volume-bar --no-use-footprint-confluence --no-use-auction-state-gate
--stop-pct 0.03 --target-pct 0.0015
--divergence-lookback-bars 100 --exit-after-volume-bars 5
```

| Metric | Value |
|--------|-------|
| Win rate | **57.4%** (202 trades) |
| PnL | **-$273** (fees > tiny targets) |
| Best month | 2025-02 **67.4%** WR |

**Insight:** Invert fixes wrong-side fades on **recent** 6m; **not** stable on full history.

### What did not work

- 70% aggregate WR over 6m — **no configuration reached it** (378+ trials).
- Tight scalp targets (0.15%) — high WR but **negative expectancy** after ~0.12% round-trip costs.
- ` --require-delta-exhaustion-fade` — **0 trades** (too strict).
- Footprint invert stacks — ~54% WR, worse than plain invert on 6m.
- Main grid without invert — capped ~42% WR with gates off.

### Sub-agent research (spawned at &lt;70%)

Topics: CVD (`volume_bar_cvd.py`), footprint, regime gate, exits/TP-SL, permission layer.  
Findings captured in code flags below; full prose was in agent outputs (not all committed).

---

## Expectancy / Sharpe pivot (option 3) — did not work

**Objective:** Stop chasing 70% WR; optimize **PnL / Sharpe** with invert + **wider targets**, 3% stop.

| Run | Result |
|-----|--------|
| `scripts/v73_sweep_expectancy_6m.py` (90 configs, invert, targets 0.6%–5%) | **0 profitable**; best loss **-$266** (`exp_t0.006_e8_lb100`) |
| 6y invert wide (`results/v73_backtest_6y_invert_exp.json`) | **WR 21.9%**, PnL **-$6,537**, Sharpe -9.49 |
| 6m sanity **without** invert, 3% target | PnL **-$140** (better than invert -$266); Jan/Mar slightly green |

**6y invert exits:** 4,233 `TIME`, 3 `TARGET`, 5 `STOP` — wide target rarely hits; time exits dominate.

**Conclusion:** Invert + wide targets **not deployable** on full 6y. Treat invert as **walk-forward / regime-specific**.

---

## Code & scripts added/changed (local)

| Path | Change |
|------|--------|
| `scripts/ensure_cache_builders.sh` | max 32, offline heal |
| `scripts/v73_sweep_6m.py` | 6m WR grid + research extras |
| `scripts/v73_sweep_invert_6m.py` | invert-focused 6m sweep |
| `scripts/v73_sweep_expectancy_6m.py` | PnL/Sharpe 6m sweep |
| `scripts/v73_quick_6m.py` | priority config probes |
| `scripts/v73_backtest_6y_incremental.py` | `--invert-signal-side`, `--work-dir` |
| `scripts/chunk_b_backtest_cached.py` | footprint invert/stacked/neutral; approve-only; delta exhaustion gate |
| `prime/footprint_confluence.py` | `invert_for_fade`, `allow_neutral` |
| `prime/chunk_b_backtest.py` | config fields for above |
| `cache_self_management.sh` | manager + 28-builder notes |

**Note:** `results/` is gitignored — sweep summaries stay local unless copied into `docs/`.

---

## Local artifacts (not on GitHub)

| File | Purpose |
|------|---------|
| `results/v73_sweep_6m_summary.json` | 296-config WR sweep |
| `results/v73_sweep_invert_6m_summary.json` | 82-config invert sweep |
| `results/v73_sweep_expectancy_6m_summary.json` | 90-config expectancy sweep |
| `results/v73_best57_6m_config.json` | Best WR config CLI |
| `results/v73_expectancy_strategy_note.json` | Expectancy findings JSON |
| `results/v73_backtest_6y_invert_exp.json` | 6y invert wide run |
| `results/v73_backtest_6y_volume_bar_cvd.json` | 6y baseline |
| `logs/v73_sweep_*.log`, `logs/v73_backtest_6y_invert_exp.log` | Run logs |

---

## Commands reference

```bash
cd /home/tokio/tm-trading-v73-current
export PYTHONPATH=/home/tokio/tm-trading-research:.

# Cache status
python3 -c "import subprocess,re; ..."  # builder count one-liner in cache_self_management.sh
tail -f logs/cache_manager.log

# Best WR 6m (single archive example)
.venv/bin/python scripts/chunk_b_backtest_cached.py \
  --archive BTCUSDT-aggTrades-2025-02.zip --threshold-btc 300 \
  --signal-mode divergence --divergence-type volume_bar_cvd \
  --invert-signal-side \
  --no-use-regime-gate-volume-bar --no-use-footprint-confluence --no-use-auction-state-gate \
  --stop-pct 0.03 --target-pct 0.0015 \
  --divergence-lookback-bars 100 --exit-after-volume-bars 5 \
  --no-use-cvd-reversal-confirm --manifest-jsonl /dev/null

# 6y invert expectancy (completed — poor)
.venv/bin/python scripts/v73_backtest_6y_incremental.py \
  --invert-signal-side --no-use-regime-gate-volume-bar \
  --no-use-footprint-confluence --no-use-auction-state-gate \
  --stop-pct 0.03 --target-pct 0.03 \
  --divergence-lookback-bars 100 --exit-after-volume-bars 20 \
  --work-dir results/v73_backtest_6y_invert_exp_work \
  --output results/v73_backtest_6y_invert_exp.json

# Re-run sweeps
.venv/bin/python scripts/v73_sweep_6m.py
.venv/bin/python scripts/v73_sweep_invert_6m.py
.venv/bin/python scripts/v73_sweep_expectancy_6m.py
```

---

## Recommended next steps

1. **Do not** enable `--invert-signal-side` globally — use walk-forward or rolling 6m validation.
2. **Non-invert 6y expectancy sweep** — wide targets, rank by chained PnL (invert hurt 6y).
3. **Signal/cache:** session-reset `cumulative_delta` in `cache_indicators.py`; min CVD divergence gap; RANGING-only gate.
4. **Align exits:** `exit-after-volume-bars` = `signal-horizon-bars`; reduce `TIME` exits vs micro targets.
5. **Publish research** in `tm-trading-research` repo (manifests live there; v73 symlinks for runs).

---

## Summary table

| Experiment | Worked? | Best metric |
|------------|---------|-------------|
| Offline cache builders | ✅ Yes | 133/133 @ 300 BTC |
| 28 detached workers | ✅ Yes | Survives net/logout |
| 6y baseline backtest | ✅ Ran | 44.4% WR, -$5.1k |
| 70% WR on 6m | ❌ No | Max **57.4%** (invert scalp) |
| Expectancy invert + wide 6m | ❌ No | 0/90 profitable |
| Expectancy invert + wide 6y | ❌ No | 21.9% WR, -$6.5k |
| High WR + profit | ❌ No | Fees eat 0.15% targets |

*Logged for GitHub — push with `docs/SESSION_LOG_2026-06-05.md` on `master`.*