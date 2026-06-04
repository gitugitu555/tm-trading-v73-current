#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${SYMBOL:-BTCUSDT}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${DEST:-${REPO_ROOT}/data/raw/binance/spot/aggTrades/${SYMBOL}/2020-05-22_to_2026-05-21}"
DEST="$(realpath -m "$DEST")"
LOG="${LOG:-${REPO_ROOT}/logs/binance_btcusdt_aggtrades_6y_download.log}"

expected_archives() {
  local year month day

  for day in $(seq -w 22 31); do
    echo "${SYMBOL}-aggTrades-2020-05-${day}.zip"
  done

  year=2020
  month=6
  while [[ "$year" -lt 2026 || "$month" -le 4 ]]; do
    printf "%s-aggTrades-%04d-%02d.zip\n" "$SYMBOL" "$year" "$month"
    month=$((month + 1))
    if [[ "$month" -eq 13 ]]; then
      year=$((year + 1))
      month=1
    fi
  done

  for day in $(seq -w 1 21); do
    echo "${SYMBOL}-aggTrades-2026-05-${day}.zip"
  done
}

present_archives() {
  find -L "$DEST" -maxdepth 1 -name "${SYMBOL}-aggTrades-*.zip" -printf "%f\n" | sort -u
}

echo "TM Trading download status"
date
echo

if [[ -d "$DEST" || -L "$DEST" ]]; then
  du -sh "$DEST"
else
  echo "DEST not found: $DEST"
fi
echo "expected=$(expected_archives | sort -u | wc -l)"
echo "present_expected=$(comm -12 <(expected_archives | sort -u) <(present_archives) | wc -l)"
echo "missing_expected=$(comm -23 <(expected_archives | sort -u) <(present_archives) | wc -l)"
echo "partials=$(find -L "$DEST" -maxdepth 1 -name "*.aria2" 2>/dev/null | wc -l)"
echo

echo "Active partials:"
find -L "$DEST" -maxdepth 1 -name "*.aria2" -printf "  %f\n" 2>/dev/null | sort || true
echo

echo "Latest aria2 progress:"
if [[ -f "$LOG" ]]; then
  tail -80 "$LOG" | sed -n '/Download Progress Summary/,$p'
else
  echo "  no log found: $LOG"
fi
