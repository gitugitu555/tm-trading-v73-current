# Session Log — 2026-06-04 (v7.3 fork)

## Repo

- **New:** `gitugitu555/tm-trading-v73-current` (fork from `tm-trading-v555`)
- **Local:** `/home/tokio/tm-trading-v73-current`
- **Shared cache:** `results/indicator_cache` → v555 NVMe parquets

## Commits shipped

| Commit | Stage |
| --- | --- |
| `4dc03ff` | Stage 1 — volume_bar_cvd alignment |
| `7c56c82` | Stage 2 — conversion tuning |
| `33e4927` | Target 0.15% from sweep |
| `badabb4` | Stage 3–4 — scorecards, manifests, CI |

## Key metrics

### Signal vs trade (2022-09, stage-3 profile)

| Metric | Value |
| --- | --- |
| Signal hit rate (5 bars) | **54.5%** |
| Trade win rate | **34.1%** |

### Partial 6y work (47 archives, indices 25+)

| Metric | Value |
| --- | --- |
| Trades | 1,930 |
| Trade win rate | **~45%** |
| Total PnL | −$1,487 |
| Signal hit (where scored) | **~54%** |

Pilot (0–24) still building **2021-04** parquet (shared with Codex v555 momentum run).

## Background jobs

- `logs/v73_backtest_6y_full.log` — **resumed** `e3026bb`: scan from index 0, skip existing reports, fill gaps (2021-04, 2021-05-01..04), wait on shared NVMe cache
- `v73_backtest_6y_pilot.log` — archives 0–24 (superseded)
- `v73_backtest_6y_full.log` — archives 25+ (`--resume`)

## Commands

```bash
cd /home/tokio/tm-trading-v73-current
.venv/bin/python scripts/v73_summarize_work.py
.venv/bin/python scripts/v73_backtest_6y_incremental.py --resume
```