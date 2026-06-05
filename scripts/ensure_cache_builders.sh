#!/bin/bash
# ensure_cache_builders.sh
# Auto-replenish cache builders for missing archives.
# Launches up to --max concurrent builders (using same nohup+setsid as manual waves).
# Survives disconnects. If a builder dies without producing cache, it will auto-relaunch it.
# Run once in bg: nohup bash scripts/ensure_cache_builders.sh --max 32 >> logs/cache_manager.log 2>&1 &
#
# "make more cache builders if some has finished" -- this keeps concurrency up as quick ones complete,
# and heals any that crashed. Builders themselves need zero internet (local zips only).
# Current default max=32 to allow ramping to 28+ total workers (e.g. 300 + 100 thresholds on stragglers).

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

MAX_CONC=32
THRESH=300
DEST="data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
CACHE_DIR="results/indicator_cache"
LOG_DIR="logs"
POLL=25

usage() {
  echo "Usage: $0 [--max N] [--once] [--poll SECS]"
  echo "  --max N     max concurrent builders (default 16)"
  echo "  --once      launch up to max then exit (no loop)"
  echo "  --poll S    seconds between checks (default 25)"
  exit 1
}

ONCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max) MAX_CONC="$2"; shift 2;;
    --once) ONCE=1; shift;;
    --poll) POLL="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown arg: $1"; usage;;
  esac
done

mkdir -p "$LOG_DIR" "$CACHE_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

have_proc_for() {
  local arch="$1"
  pgrep -f "cache_indicators.py.*${arch}" >/dev/null 2>&1
}

get_missing() {
  comm -23 \
    <(ls "$DEST"/BTCUSDT-aggTrades-*.zip 2>/dev/null | xargs -I{} basename {} | grep -v _1m | sort) \
    <(ls "$CACHE_DIR"/*.threshold-${THRESH}.parquet 2>/dev/null | sed 's|.*/||; s|\.threshold-'"${THRESH}"'\.parquet$||' | sort) \
    2>/dev/null || true
}

get_running_count() {
  # count only the real python worker processes (bash -c wrappers contain the text too, so exclude them)
  ps -eo pid,cmd 2>/dev/null | grep -E '\.venv/bin/python .*cache_indicators.py' | grep -v 'bash -c' | grep -v grep | wc -l || echo 0
}

launch_one() {
  local arch="$1"
  local short
  short=$(echo "$arch" | sed 's/BTCUSDT-aggTrades-//; s/\.zip$//')
  local logf="$LOG_DIR/cache_${short}.log"

  if [ -f "$CACHE_DIR/${arch}.threshold-${THRESH}.parquet" ]; then
    return 0
  fi
  if have_proc_for "$arch"; then
    return 0
  fi

  log "LAUNCH: $arch (log: $logf)"
  setsid -f bash -c "
    nohup .venv/bin/python scripts/cache_indicators.py \
      --dest '$DEST' \
      --archive '$arch' \
      --threshold-btc $THRESH --progress \
      >> '$logf' 2>&1
  " </dev/null >/dev/null 2>&1 || true
  sleep 0.6
}

log "=== ensure_cache_builders starting (max_conc=$MAX_CONC, once=$ONCE, poll=${POLL}s) ==="
log "Project: $(pwd)"
log "Note: builders are offline-capable (only read local zips + write local parquet)."

while true; do
  mapfile -t missing < <(get_missing)
  run_cnt=$(get_running_count)

  log "status: missing=${#missing[@]} running=${run_cnt} target_max=${MAX_CONC}"

  if [ ${#missing[@]} -eq 0 ]; then
    log "SUCCESS: no missing caches left for threshold ${THRESH}. Manager done."
    exit 0
  fi

  slots=$(( MAX_CONC - run_cnt ))
  if [ $slots -le 0 ]; then
    if [ "$ONCE" -eq 1 ]; then
      log "once mode: max concurrency reached or exceeded, exiting."
      exit 0
    fi
    sleep "$POLL"
    continue
  fi

  launched_this=0
  for arch in "${missing[@]}"; do
    if [ $launched_this -ge $slots ]; then
      break
    fi
    if have_proc_for "$arch"; then
      continue
    fi
    if [ -f "$CACHE_DIR/${arch}.threshold-${THRESH}.parquet" ]; then
      continue
    fi
    launch_one "$arch"
    launched_this=$((launched_this + 1))
  done

  if [ $launched_this -gt 0 ]; then
    log "launched $launched_this this cycle; now running ~$((run_cnt + launched_this))"
  fi

  if [ "$ONCE" -eq 1 ]; then
    log "once mode: initial/ top-up launches done."
    exit 0
  fi

  sleep "$POLL"
done
