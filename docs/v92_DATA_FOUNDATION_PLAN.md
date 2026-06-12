# V9.2 Data Foundation Plan (HFT Pivot)

## Purpose
Originally, the V9.2 roadmap planned to ingest historical data from the Bybit public API. However, an institutional-grade HFT dataset in compressed Zstandard Parquet format was discovered in cold storage (`/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata`). This drastically improves data fidelity (providing true L2 metrics).

## 1. Storage & Caching Architecture
Due to NVME space constraints (110GB available vs. 132GB highly-compressed raw data), we are adopting a **Two-Tier Cache Strategy**:

### Tier 1: Heavy Cache (Seagate HDD)
- **Location:** `/mnt/seagate/tm-trading-v555/...`
- **Role:** Holds the full compressed raw history.
- **Operations:** Feature engineering, dataset aggregation, and heavy bar compilation utilizing parallel processing (Polars/Dask) sequentially streaming the `.parquet.zst` files to minimize HDD random read penalties.

### Tier 2: Light Cache (NVME SSD)
- **Location:** `/home/tokio/tm-trading-v73-current/data/hft/...`
- **Role:** Lightning-fast backtest ingestion.
- **Operations:** Holds specific extracted datasets (e.g., top-of-book only, downsampled horizons, pre-calculated alpha features) that easily fit inside the 110 GB space limit.

## 2. Immediate Next Steps
1. **Inventory:** Run `scripts/v92_hft_inventory.py` to build a manifest of the available HFT data and identify any missing hours/gaps.
2. **Schema Audit:** Sample the Parquet schemas to understand exactly what L2 fields are available (e.g., depth levels, local vs exchange timestamps).
3. **Pipeline Construction:** Build a Polars-based streaming pipeline to derive the Level 2 Light Cache.
