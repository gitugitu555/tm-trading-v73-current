#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${SYMBOL:-BTCUSDT}"
START_DATE="${START_DATE:-2020-05-22}"
END_DATE="${END_DATE:-2026-05-21}"
DATA_ROOT="${TM_DATA_COLD_ROOT:-/mnt/seagate/tm-trading-v555/data/raw}"
DEST="${DEST:-${DATA_ROOT}/binance/spot/aggTrades/${SYMBOL}/2020-05-22_to_2026-05-21}"
BASE="https://data.binance.vision/data/spot"

mkdir -p "$DEST"

download_one() {
  local kind="$1"
  local label="$2"
  local name="${SYMBOL}-aggTrades-${label}.zip"
  local url="${BASE}/${kind}/aggTrades/${SYMBOL}/${name}"
  local out="${DEST}/${name}"
  local checksum="${out}.CHECKSUM"

  if [[ -f "$out" && -f "$checksum" ]]; then
    if (cd "$DEST" && sha256sum -c "${name}.CHECKSUM" >/dev/null 2>&1); then
      echo "OK existing ${name}"
      return
    fi
  fi

  echo "Downloading ${name}"
  curl -fL --retry 5 --retry-delay 3 -C - "$url" -o "$out"
  curl -fL --retry 5 --retry-delay 3 "${url}.CHECKSUM" -o "$checksum"
  (cd "$DEST" && sha256sum -c "${name}.CHECKSUM")
}

# Edge days: 2020-05-22 through 2020-05-31.
for day in 22 23 24 25 26 27 28 29 30 31; do
  download_one "daily" "2020-05-${day}"
done

# Full months: 2020-06 through 2026-04.
year=2020
month=6
while [[ "$year" -lt 2026 || "$month" -le 4 ]]; do
  label="$(printf "%04d-%02d" "$year" "$month")"
  download_one "monthly" "$label"
  month=$((month + 1))
  if [[ "$month" -eq 13 ]]; then
    year=$((year + 1))
    month=1
  fi
done

# Edge days: 2026-05-01 through 2026-05-21.
for day in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21; do
  download_one "daily" "2026-05-${day}"
done

echo "Download complete: ${DEST}"
du -sh "$DEST"
