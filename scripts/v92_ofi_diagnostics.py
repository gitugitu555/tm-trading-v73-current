#!/usr/bin/env python3
"""
V9.2 OFI Diagnostics

Extracts the first 10,000 rows of a highly-compressed L2 Orderbook file,
runs the OFI state machine, and outputs a diagnostic summary.
"""

import sys
import io
import pandas as pd
import zstandard as zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.microstructure_ofi import process_chunk

def load_zst_parquet(filepath: Path) -> pd.DataFrame:
    """Decompresses a .parquet.zst file into a Pandas DataFrame."""
    print(f"Decompressing {filepath.name} into memory...")
    with open(filepath, 'rb') as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            decompressed_data = reader.read()
            
    df = pd.read_parquet(io.BytesIO(decompressed_data), engine='pyarrow')
    return df

def main():
    print("V9.2 OFI Diagnostics Initialized.")
    
    # Target the first hour of March 14, 2026
    sample_file = Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-14/00/BTCUSDT_orderbook.parquet.zst")
    
    if not sample_file.exists():
        print(f"Sample file {sample_file} not found. Ensure Seagate drive is mounted.")
        return
        
    df = load_zst_parquet(sample_file)
    print(f"Loaded {len(df):,} L2 update events.")
    
    # Sort chronologically by transaction/event time
    df = df.sort_values(by=['transaction_time', 'event_time', 'first_update_id']).reset_index(drop=True)
    
    # For diagnostics, we only process the first 100,000 updates to save time
    chunk_size = 100000
    df_chunk = df.head(chunk_size).copy()
    
    print(f"\nProcessing {chunk_size:,} events through the OFI State Machine...")
    df_chunk = process_chunk(df_chunk)
    
    # Summary Metrics
    total_ofi = df_chunk['ofi'].sum()
    mean_ofi = df_chunk['ofi'].mean()
    non_zero_ofi = (df_chunk['ofi'] != 0.0).sum()
    
    print(f"\n--- OFI Diagnostic Summary ---")
    print(f"Total Cumulative OFI: {total_ofi:,.2f}")
    print(f"Mean Tick OFI:        {mean_ofi:,.6f}")
    print(f"Non-Zero OFI Ticks:   {non_zero_ofi:,} ({(non_zero_ofi/chunk_size)*100:.1f}%)")
    
    print("\nSample Output (First 5 Non-Zero OFI Ticks):")
    print(df_chunk[df_chunk['ofi'] != 0.0][['transaction_time', 'side', 'price', 'quantity', 'ofi']].head(5))
    
    # Save test results
    out_dir = ROOT / "results/v92_ofi_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ofi_diagnostics.json"
    
    import json
    out_file.write_text(json.dumps({
        "status": "success",
        "total_ofi": total_ofi,
        "non_zero_ticks": int(non_zero_ofi)
    }))
    print(f"\nSaved diagnostic report to {out_file}")

if __name__ == "__main__":
    sys.exit(main())
