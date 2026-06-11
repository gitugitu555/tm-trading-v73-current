# V8.7 Alpha Decay Report

Results are stored in `results/v87_execution_rescue/alpha_decay/alpha_decay_summary.json`.

Current implementation is an honest signal-horizon diagnostic. Full strategy-state timing comparisons require entry timing support inside the backtester.

## Preliminary April 2026 Result

On one immutable 51-signal opportunity set, Lag 0 close and Lag 1 open were effectively identical because contiguous trade-built volume bars normally open at the prior close. Lag 1 close/Lag 2 open were worse. Historical Lag 0/Lag 1 strategy labels shared only 2,890 signal IDs, so their large performance difference is not a clean execution-price comparison.
