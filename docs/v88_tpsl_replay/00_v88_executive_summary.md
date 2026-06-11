# V8.8 Executive Summary

V8.8 separates immutable signal generation, forward paths, TPSL, occupancy, filters, and capital allocation.

Preliminary evidence uses the consolidated catalog named `btcusdt_trade_ticks_6y`, but its actual timestamp range is May-August 2020. It is not six-year validation.

Results:

- Immutable signals: 827
- Complete 96-bar paths: 820
- Policies tested: 66
- Best policy: breakeven after 0.1% MFE, lock 0.1%
- Best net expectancy after costs: -0.000597
- Best profit factor: 0.503
- Positive-MFE-before-loss rate at 96 bars: 58.78%

Conclusion: MFE protection reduces losses but does not make the immutable raw signal profitable. Promote nothing.
