#!/bin/bash
# Run footprint F1-F5 diagnostic in parallel shards

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR/.."

SHARD_COUNT=16
OUTPUT_DIR="results"
SCRIPT="scripts/footprint_f1_f5_diagnostic.py"
DEST="data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"

echo "Starting footprint F1-F5 backtest with $SHARD_COUNT shards..."
echo "Output directory: $OUTPUT_DIR"

# Run shards in background
for SHARD_INDEX in $(seq 0 $((SHARD_COUNT - 1))); do
    OUTPUT="${OUTPUT_DIR}/footprint_f1_f5_6y_shard${SHARD_INDEX}_of_${SHARD_COUNT}.json"
    echo "Starting shard $SHARD_INDEX/$((SHARD_COUNT - 1))... -> $OUTPUT"
    python3 $SCRIPT \
        --all-archives \
        --dest $DEST \
        --shard-count $SHARD_COUNT \
        --shard-index $SHARD_INDEX \
        --output $OUTPUT \
        --progress &
done

echo "All $SHARD_COUNT shards started. Wait for completion..."
wait
echo "All shards completed!"

# Aggregate results
echo "Aggregating results..."
python3 -c "
import json
import glob
from collections import defaultdict

files = sorted(glob.glob('${OUTPUT_DIR}/footprint_f1_f5_6y_shard*_of_${SHARD_COUNT}.json'))
print(f'Aggregating {len(files)} shard files...')

# For now just print summary
for f in files:
    with open(f) as fh:
        data = json.load(fh)
    print(f'{f}: archives={data.get(\"archives_processed\", 0)}, rows={data.get(\"rows_seen\", 0):,}')
"
