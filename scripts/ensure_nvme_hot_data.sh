#!/usr/bin/env bash
# Ensure BTCUSDT six-year aggTrades are on NVMe (not symlinked to Seagate).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOT="$REPO/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
COLD="/mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
NESTED="$HOT/2020-05-22_to_2026-05-21"

export TM_DATA_HOT_ROOT="$REPO/data/raw"
export TM_DATA_COLD_ROOT="/mnt/seagate/tm-trading-v555/data/raw"

echo "NVMe hot: $HOT"
echo "Seagate cold: $COLD"

if [[ -L "$NESTED" ]]; then
  echo "Removing nested Seagate symlink inside hot dir: $NESTED"
  rm "$NESTED"
fi

if [[ -L "$HOT" ]]; then
  echo "ERROR: Hot dataset path is symlinked to HDD. Sync to NVMe first:"
  echo "  rm '$HOT'"
  echo "  $REPO/.venv/bin/python scripts/binance_data_manager.py \\"
  echo "    --market spot --kind aggTrades --symbol BTCUSDT \\"
  echo "    --range-label 2020-05-22_to_2026-05-21 sync --direction cold-to-hot"
  exit 1
fi

count=$(find "$HOT" -maxdepth 1 -name 'BTCUSDT-aggTrades-*.zip' | wc -l)
echo "Zip archives on NVMe hot path: $count"

if [[ "$count" -lt 100 ]]; then
  echo "WARNING: expected ~134 zips. Consider cold-to-hot rsync."
fi

findmnt -T "$HOT" | head -2
echo "TM_DATA_HOT_ROOT=$TM_DATA_HOT_ROOT"