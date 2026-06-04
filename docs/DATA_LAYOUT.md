# Data Layout

Canonical raw market data lives in a mirrored path layout so the same dataset can exist in cold storage and in a hot cache.

## Roots

- Cold storage: `/mnt/seagate/tm-trading-v555/data/raw`
- Hot cache: `/home/tokio/tm-trading-v555/data/raw`

You can override those roots with:

- `TM_DATA_COLD_ROOT`
- `TM_DATA_HOT_ROOT`

## Path Scheme

Use this relative structure for all Binance datasets:

`binance/<market>/<kind>/<symbol>/<range_label>`

Examples:

- `binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21`
- `binance/spot/aggTrades/ETHUSDT/2022-01-01_to_2022-12-31`
- `binance/futures/klines/BTCUSDT/2024-01-01_to_2024-12-31`

## Workflow

1. Download raw archives to the cold root when possible.
2. Use the hot cache only for the working set you are actively replaying.
3. Promote a finished hot dataset to cold storage and relink the hot path to the cold path.
4. Add new pairs or tick feeds by reusing the same relative layout.

## Manager

The helper script is:

`scripts/binance_data_manager.py`

Useful commands:

```bash
python scripts/binance_data_manager.py --market spot --kind aggTrades --symbol BTCUSDT --range-label 2020-05-22_to_2026-05-21 path
python scripts/binance_data_manager.py --market spot --kind aggTrades --symbol BTCUSDT --range-label 2020-05-22_to_2026-05-21 status
python scripts/binance_data_manager.py --market spot --kind aggTrades --symbol BTCUSDT --range-label 2020-05-22_to_2026-05-21 link --force
python scripts/binance_data_manager.py --market spot --kind aggTrades --symbol BTCUSDT --range-label 2020-05-22_to_2026-05-21 promote
```

