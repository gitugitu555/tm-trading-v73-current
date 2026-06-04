#!/usr/bin/env bash
# Grok-owned v7.3 pipeline: NVMe cache + volume_bar_cvd 6y backtest (no Codex).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TM_DATA_HOT_ROOT="${TM_DATA_HOT_ROOT:-/home/tokio/tm-trading-v555/data/raw}"
mkdir -p logs
PY="${ROOT}/.venv/bin/python"
DEST="${TM_DATA_HOT_ROOT}/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
CACHE="${ROOT}/results/indicator_cache"
LOG="${ROOT}/logs/grok_v73_supervisor.log"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

running_backtest() {
  pgrep -f "scripts/v73_backtest_6y_incremental.py --resume" >/dev/null 2>&1
}

running_cache() {
  pgrep -f "cache_indicators.py.*--archive" >/dev/null 2>&1
}

ensure_backtest() {
  if running_backtest; then
    log "v73 backtest already running"
    return
  fi
  log "starting v73_backtest_6y_incremental.py --resume"
  nohup nice -n 19 "$PY" scripts/v73_backtest_6y_incremental.py --resume \
    >>"${ROOT}/logs/v73_backtest_6y_full.log" 2>&1 &
  log "backtest pid=$!"
}

# Optional: build a specific monthly archive when backtest is blocked (pass archive name).
build_cache_if_missing() {
  local archive="${1:-}"
  [[ -n "$archive" ]] || return 0
  local parquet="${CACHE}/${archive}.threshold-300.parquet"
  if [[ -f "$parquet" ]]; then
    log "cache exists: $archive"
    return 0
  fi
  if running_cache; then
    log "cache builder already running; skip $archive"
    return 0
  fi
  log "building cache: $archive"
  nohup nice -n 15 "$PY" scripts/cache_indicators.py \
    --dest "$DEST" \
    --archive "$archive" \
    --threshold-btc 300 \
    --progress \
    >>"${ROOT}/logs/grok_cache_${archive%.zip}.log" 2>&1 &
  log "cache pid=$!"
}

log "supervisor tick"
build_cache_if_missing "${GROK_CACHE_ARCHIVE:-}"
ensure_backtest