# V8.7 Signal Observability Audit

Raw-tick partial-bar results are in `results/v87_execution_rescue/signal_observability/observability_summary.json`.

This audit evaluates only information observable at each replayed tick. L2-dependent features are unavailable in aggTrades.

## Preliminary April 2026 Result

The audit reconstructed 1,574 completed 300-BTC bars and 18,240 partial states. Precision/recall rose from 71.4%/19.6% at 10% volume to 91.3%/82.4% at 90%, but average time remaining fell from 1.48 seconds to 0.16 seconds.
