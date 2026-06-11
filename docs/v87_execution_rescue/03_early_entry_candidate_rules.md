# V8.7 Early Entry Candidate Rules

Results: `results/v87_execution_rescue/early_entry/early_entry_candidates.json`.

Trade-flow confirmation is an aggTrades proxy, not OFI/MLOFI from an order book. Maker-first and microprice rules remain unavailable until L2 is aligned to signals.

All honest partial-entry thresholds tested were negative after costs in the April 2026 sample. Evaluation includes false positives and does not condition entry on later final-signal confirmation.
