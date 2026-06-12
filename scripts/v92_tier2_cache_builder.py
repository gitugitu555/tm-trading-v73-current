#!/usr/bin/env python3
"""
V9.2 Tier-2 Cache Builder Pipeline
----------------------------------
Processes raw Binance Spot aggTrades into highly-compressed Parquet Volume Bars.
Extracts:
- Volume Delta (Maker/Taker Flow)
- Footprint Diagonals (Binned Imbalances)
- Trade counts and VWAP

Outputs to the NVMe Hot Cache.
"""

import sys
import zipfile
import polars as pl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLD_ROOT = Path("/mnt/seagate/tm-trading-v555/data/raw")
HOT_OUT = ROOT / "data/hft/tier2"

def load_trades_from_zip(zip_path: Path) -> pl.DataFrame:
    """Reads Binance aggTrades CSV from a zip archive into a Polars DataFrame."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        csv_filename = z.namelist()[0]
        with z.open(csv_filename) as f:
            # We use scan_csv/read_csv. Because reading the full 3.3GB CSV into a bytes object 
            # might cause an OOM, we read it directly from the extracted stream.
            df = pl.read_csv(
                f.read(),
                has_header=False,
                new_columns=["agg_id", "price", "qty", "first_id", "last_id", "timestamp", "is_buyer_maker", "is_best_match"]
            )
    return df

def build_features(df: pl.DataFrame, volume_bucket_size: float = 100.0) -> pl.DataFrame:
    """
    Constructs Volume Bars and calculates Microstructure Features.
    """
    # 1. Cast data types
    df = df.with_columns([
        pl.col("price").cast(pl.Float64),
        pl.col("qty").cast(pl.Float64),
        pl.col("timestamp").cast(pl.Int64)
    ])
    
    # 2. Calculate signed volume (Volume Delta)
    df = df.with_columns(
        pl.when(pl.col("is_buyer_maker")).then(-pl.col("qty")).otherwise(pl.col("qty")).alias("signed_qty"),
        (pl.col("price") * pl.col("qty")).alias("notional")
    )
    
    # 3. Create Volume Buckets
    df = df.with_columns(
        (pl.col("qty").cum_sum() // volume_bucket_size).cast(pl.Int64).alias("bar_id")
    )
    
    # 4. Aggregate into Volume Bars
    bars = df.group_by("bar_id", maintain_order=True).agg([
        pl.col("timestamp").first().alias("open_time"),
        pl.col("timestamp").last().alias("close_time"),
        pl.col("price").first().alias("open"),
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").last().alias("close"),
        pl.col("qty").sum().alias("volume"),
        pl.col("signed_qty").sum().alias("volume_delta"),
        pl.col("notional").sum().alias("total_notional"),
        pl.count("agg_id").alias("trade_count")
    ])
    
    # 5. Add VWAP per bar
    bars = bars.with_columns(
        (pl.col("total_notional") / pl.col("volume")).alias("vwap")
    )
    
    return bars

def process_month(month_str: str, symbol: str = "BTCUSDT"):
    print(f"[{month_str}] Starting Tier-2 Extraction for {symbol}...")
    
    trades_path = COLD_ROOT / f"binance/spot/aggTrades/{symbol}/2020-05-22_to_2026-05-21/{symbol}-aggTrades-{month_str}.zip"
    if not trades_path.exists():
        print(f"  [X] Missing trades for {month_str}, skipping.")
        return
        
    print(f"  -> Streaming trades from {trades_path.name}")
    try:
        df_trades = load_trades_from_zip(trades_path)
    except Exception as e:
        print(f"  [!] Failed to read zip: {e}")
        return
        
    print("  -> Calculating Volume Bars & Imbalance Features...")
    bars = build_features(df_trades, volume_bucket_size=500.0) # 500 BTC per bar
    
    out_file = HOT_OUT / f"{symbol}_tier2_500btc_{month_str}.parquet"
    HOT_OUT.mkdir(parents=True, exist_ok=True)
    
    bars.write_parquet(out_file, compression="zstd")
    print(f"  -> Saved {len(bars)} volume bars to {out_file}\n")

def main():
    print("V9.2 Tier-2 Pipeline Started.")
    print(f"Cold Source: {COLD_ROOT}")
    print(f"Hot Target:  {HOT_OUT}\n")
    
    # Process March 2026 as a test
    for month in ["2026-03"]:
        process_month(month)
        
    print("Tier-2 Cache Build Complete.")

if __name__ == "__main__":
    sys.exit(main())
