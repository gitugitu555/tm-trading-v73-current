# D4 Scale Closeout & Verdict

## 1. Overview
The final D4 bar/horizon surface test was executed across volume bar sizes (300, 500, 750, 1000, 1500 BTC) and horizons (5, 10, 15, 24, 36, 48 bars).

The goal was to determine if D4 failed purely because the tested bar/horizon scale was wrong, or if the edge itself has decayed post-costs.

## 2. Execution Results
The surface script (`scripts/v91_d4_bar_horizon_surface.py`) was successfully run, computing the matrix against the verified catalog. 

**Top 10 Performers (2024-2026 Split):**
```text
1500 h=15 mtf_aligned n=    4 mean=224.087bps net1=223.087bps
1500 h=10 mtf_aligned n=    4 mean=210.558bps net1=209.558bps
1000 h=15 mtf_aligned n=    1 mean=177.998bps net1=176.998bps
1500 h= 5 mtf_aligned n=    4 mean=166.260bps net1=165.260bps
1000 h=24 mtf_aligned n=    1 mean=153.607bps net1=152.607bps
1000 h= 5 mtf_aligned n=    1 mean=152.363bps net1=151.363bps
1000 h=10 mtf_aligned n=    1 mean= 97.637bps net1= 96.637bps
 750 h=15 mtf_aligned n=    9 mean= 74.257bps net1= 73.257bps
 750 h=24 mtf_aligned n=    9 mean= 45.427bps net1= 44.427bps
1500 h=24 mtf_aligned n=    4 mean= 43.808bps net1= 42.808bps
```
*Results outputted to `results/v91_alpha_discovery/d4_bar_horizon_surface.json`.*

## 3. Verdict
**D4 is archived as a research feature only.**

While the raw expected returns look positive on paper, the event counts (`n=1` to `n=9` over a two year out-of-sample period) completely fail the "minimum viable event count" criteria. A strategy firing 4 times in 2 years is statistically meaningless and untradable.

D4's signal remains statistically real in the historical full sample but is economically useless in the current regime due to being too sparse at scales where the bps threshold beats taker costs. 

### Revival Status
- **Post-cost expectancy:** Passed (Technically)
- **Minimum viable event count:** FAILED
- **No single-year dependency:** FAILED (n=4 implies highly specific episodic triggers)

**Conclusion:** We proceed with Phase 2 (Data Foundation / Bybit Historical Inventory) and move toward New Microstructure Alpha Families (Phase 5). D4 will only be used as a contextual feature in future models.
