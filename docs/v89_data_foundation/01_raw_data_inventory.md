# V8.9 Raw Data Inventory

The local BTCUSDT aggTrades source contains 134 archives and 133 matching
volume-bar caches. Canonical selection uses 132 archives after excluding the
overlapping monthly `BTCUSDT-aggTrades-2021-05.zip` archive.

- Raw directory: `/home/tokio/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21`
- Raw size: approximately 51 GB
- Canonical rows from verified cache metadata: 3,662,935,692
- Raw manifest hash: `c8d9bf35456ed3570285f74c320d001059d610e2fea047d50a3976f91d67075e`

The inventory uses archive checksums and verified cache metadata so it does not
re-decompress 51 GB on every audit. A full raw trade-ID duplicate scan remains
pending and must not be implied by the cache-level duplicate checks.

