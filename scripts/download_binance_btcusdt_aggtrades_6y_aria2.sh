#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${SYMBOL:-BTCUSDT}"
DATA_ROOT="${TM_DATA_COLD_ROOT:-/mnt/seagate/tm-trading-v555/data/raw}"
DEST="${DEST:-${DATA_ROOT}/binance/spot/aggTrades/${SYMBOL}/2020-05-22_to_2026-05-21}"
BASE="https://data.binance.vision/data/spot"
JOBS="${JOBS:-6}"
SPLIT="${SPLIT:-8}"

mkdir -p "$DEST" logs

manifest="$(mktemp)"
trap 'rm -f "$manifest"' EXIT

add_item() {
  local kind="$1"
  local label="$2"
  local name="${SYMBOL}-aggTrades-${label}.zip"
  local url="${BASE}/${kind}/aggTrades/${SYMBOL}/${name}"

  {
    echo "$url"
    echo "  dir=${DEST}"
    echo "  out=${name}"
    echo "${url}.CHECKSUM"
    echo "  dir=${DEST}"
    echo "  out=${name}.CHECKSUM"
  } >> "$manifest"
}

for day in 22 23 24 25 26 27 28 29 30 31; do
  add_item "daily" "2020-05-${day}"
done

year=2020
month=6
while [[ "$year" -lt 2026 || "$month" -le 4 ]]; do
  add_item "monthly" "$(printf "%04d-%02d" "$year" "$month")"
  month=$((month + 1))
  if [[ "$month" -eq 13 ]]; then
    year=$((year + 1))
    month=1
  fi
done

for day in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21; do
  add_item "daily" "2026-05-${day}"
done

aria2c \
  --continue=true \
  --max-concurrent-downloads="$JOBS" \
  --split="$SPLIT" \
  --max-connection-per-server="$SPLIT" \
  --min-split-size=8M \
  --max-tries=0 \
  --retry-wait=5 \
  --auto-file-renaming=false \
  --allow-overwrite=true \
  --file-allocation=none \
  --summary-interval=30 \
  --input-file="$manifest"

(
  cd "$DEST"
  sha256sum -c ./*.CHECKSUM
)

echo "Download complete: ${DEST}"
du -sh "$DEST"
