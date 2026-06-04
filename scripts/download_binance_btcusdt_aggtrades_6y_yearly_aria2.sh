#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${SYMBOL:-BTCUSDT}"
DATA_ROOT="${TM_DATA_COLD_ROOT:-/mnt/seagate/tm-trading-v555/data/raw}"
DEST="${DEST:-${DATA_ROOT}/binance/spot/aggTrades/${SYMBOL}/2020-05-22_to_2026-05-21}"
BASE="https://data.binance.vision/data/spot"
JOBS="${JOBS:-2}"
SPLIT="${SPLIT:-4}"

mkdir -p "$DEST" logs

is_verified() {
  local name="$1"

  [[ -f "${DEST}/${name}" && -f "${DEST}/${name}.CHECKSUM" ]] || return 1
  (cd "$DEST" && sha256sum -c "${name}.CHECKSUM" >/dev/null 2>&1)
}

add_item() {
  local manifest="$1"
  local kind="$2"
  local label="$3"
  local name="${SYMBOL}-aggTrades-${label}.zip"
  local url="${BASE}/${kind}/aggTrades/${SYMBOL}/${name}"

  if is_verified "$name"; then
    echo "OK existing ${name}"
    return
  fi

  {
    echo "$url"
    echo "  dir=${DEST}"
    echo "  out=${name}"
    echo "${url}.CHECKSUM"
    echo "  dir=${DEST}"
    echo "  out=${name}.CHECKSUM"
  } >> "$manifest"
}

add_daily_range() {
  local manifest="$1"
  local year="$2"
  local month="$3"
  local first_day="$4"
  local last_day="$5"
  local day

  for day in $(seq -w "$first_day" "$last_day"); do
    add_item "$manifest" "daily" "${year}-${month}-${day}"
  done
}

add_monthly_range() {
  local manifest="$1"
  local start_year="$2"
  local start_month="$3"
  local end_year="$4"
  local end_month="$5"
  local year="$start_year"
  local month="$start_month"

  while [[ "$year" -lt "$end_year" || "$month" -le "$end_month" ]]; do
    add_item "$manifest" "monthly" "$(printf "%04d-%02d" "$year" "$month")"
    month=$((month + 1))
    if [[ "$month" -eq 13 ]]; then
      year=$((year + 1))
      month=1
    fi
  done
}

verify_item() {
  local label="$1"
  local name="${SYMBOL}-aggTrades-${label}.zip"

  (cd "$DEST" && sha256sum -c "${name}.CHECKSUM")
}

verify_daily_range() {
  local year="$1"
  local month="$2"
  local first_day="$3"
  local last_day="$4"
  local day

  for day in $(seq -w "$first_day" "$last_day"); do
    verify_item "${year}-${month}-${day}"
  done
}

verify_monthly_range() {
  local start_year="$1"
  local start_month="$2"
  local end_year="$3"
  local end_month="$4"
  local year="$start_year"
  local month="$start_month"

  while [[ "$year" -lt "$end_year" || "$month" -le "$end_month" ]]; do
    verify_item "$(printf "%04d-%02d" "$year" "$month")"
    month=$((month + 1))
    if [[ "$month" -eq 13 ]]; then
      year=$((year + 1))
      month=1
    fi
  done
}

download_batch() {
  local label="$1"
  local start_year="$2"
  local end_year="$3"
  local manifest

  manifest="$(mktemp)"

  echo "Preparing ${label}"
  add_daily_range "$manifest" "$start_year" "05" 22 31
  add_monthly_range "$manifest" "$start_year" 6 "$end_year" 4
  add_daily_range "$manifest" "$end_year" "05" 1 21

  if [[ ! -s "$manifest" ]]; then
    echo "Batch already complete: ${label}"
    rm -f "$manifest"
    return
  fi

  aria2c \
    --continue=true \
    --max-concurrent-downloads="$JOBS" \
    --split="$SPLIT" \
    --max-connection-per-server="$SPLIT" \
    --min-split-size=8M \
    --max-tries=0 \
    --retry-wait=10 \
    --auto-file-renaming=false \
    --allow-overwrite=true \
    --file-allocation=none \
    --summary-interval=30 \
    --input-file="$manifest"

  rm -f "$manifest"

  echo "Verifying ${label}"
  verify_daily_range "$start_year" "05" 22 31
  verify_monthly_range "$start_year" 6 "$end_year" 4
  verify_daily_range "$end_year" "05" 1 21
}

download_batch "2020-05-22_to_2021-05-21" 2020 2021
download_batch "2021-05-22_to_2022-05-21" 2021 2022
download_batch "2022-05-22_to_2023-05-21" 2022 2023
download_batch "2023-05-22_to_2024-05-21" 2023 2024
download_batch "2024-05-22_to_2025-05-21" 2024 2025
download_batch "2025-05-22_to_2026-05-21" 2025 2026

echo "Download complete: ${DEST}"
du -sh "$DEST"
