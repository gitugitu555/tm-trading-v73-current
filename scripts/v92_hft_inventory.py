#!/usr/bin/env python3
"""
V9.2 HFT Data Inventory & Validation Script

Crawls the raw HFT data directory on the Seagate drive to build an exhaustive manifest of available 
files, extracting metadata such as symbol, date, hour, and file size. It detects any missing hours 
(gaps) and writes the resulting manifest to disk.
"""

import json
import os
import glob
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

RAW_DATA_ROOT = Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata")
MANIFEST_OUT = Path(__file__).resolve().parents[1] / "data" / "hft" / "hft_inventory_manifest.json"

def get_expected_hours():
    return [f"{i:02d}" for i in range(24)]

def main():
    if not RAW_DATA_ROOT.exists():
        print(f"Error: Data root {RAW_DATA_ROOT} does not exist.")
        return
        
    print(f"Crawling HFT data at {RAW_DATA_ROOT}...")
    
    inventory = []
    # Structure to check gaps: coverage[data_type][exchange][symbol][date] = set(hours)
    coverage = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(set))))
    total_size_bytes = 0
    
    # We expect paths like: orderbook/binance_futures/BTCUSDT/2026-03-14/14/BTCUSDT_orderbook.parquet.zst
    # Using glob to recursively find all files
    search_pattern = str(RAW_DATA_ROOT / "**" / "*.*")
    
    for filepath_str in glob.iglob(search_pattern, recursive=True):
        filepath = Path(filepath_str)
        if not filepath.is_file():
            continue
            
        rel_path = filepath.relative_to(RAW_DATA_ROOT)
        parts = rel_path.parts
        
        # Expecting at least: data_type / exchange / symbol / date / hour / filename
        if len(parts) >= 6:
            data_type = parts[0]
            exchange = parts[1]
            symbol = parts[2]
            date_str = parts[3]
            hour_str = parts[4]
            filename = parts[-1]
        else:
            # Fallback for unrecognized structure
            data_type = "unknown"
            exchange = "unknown"
            symbol = "unknown"
            date_str = "unknown"
            hour_str = "unknown"
            filename = filepath.name
            
        size = filepath.stat().st_size
        total_size_bytes += size
        
        file_meta = {
            "rel_path": str(rel_path),
            "data_type": data_type,
            "exchange": exchange,
            "symbol": symbol,
            "date": date_str,
            "hour": hour_str,
            "size_bytes": size,
            "filename": filename
        }
        
        inventory.append(file_meta)
        
        if date_str != "unknown" and hour_str != "unknown":
            coverage[data_type][exchange][symbol][date_str].add(hour_str)
            
    print(f"Found {len(inventory)} files totaling {total_size_bytes / (1024**3):.2f} GB.")
    
    # Gap detection
    print("\nRunning gap detection...")
    gaps = []
    expected_hours_set = set(get_expected_hours())
    
    for dt, ex_dict in coverage.items():
        for ex, sym_dict in ex_dict.items():
            for sym, date_dict in sym_dict.items():
                for date, hours in date_dict.items():
                    missing_hours = expected_hours_set - hours
                    if missing_hours:
                        gaps.append({
                            "data_type": dt,
                            "exchange": ex,
                            "symbol": sym,
                            "date": date,
                            "missing_hours": sorted(list(missing_hours))
                        })
    
    if gaps:
        print(f"Detected {len(gaps)} dates with missing hourly files.")
    else:
        print("No hourly gaps detected in available dates!")
        
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "raw_root": str(RAW_DATA_ROOT),
        "total_files": len(inventory),
        "total_size_bytes": total_size_bytes,
        "gaps_detected": gaps,
        "files": inventory
    }
    
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"\nManifest successfully written to {MANIFEST_OUT}")

if __name__ == "__main__":
    main()
