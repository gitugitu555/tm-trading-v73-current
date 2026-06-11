# V8.6 Final Recovery Decision

## Current Decision

- Reject promotion of all V8.5 profile/gate stacks based on current evidence.
- Keep profile exits and all gates shadow-only.
- Treat V8.4 positive results as unverified until reproduced under one runner with explicit lag and costs.
- Do not optimize the staged let-it-breathe matrix until measurement and controlled ablations complete.

## Confirmed Answers

| Question | Current answer |
|---|---|
| Was V8.4 reproducible under honest V8.5 execution? | Not yet established. |
| How much came from entry lag? | Unknown. Lag mode changes the signal/trade opportunity set, so historical labels do not isolate execution timing. |
| How much came from costs? | Pending 0x/1x/2x/3x ladder. |
| How much came from profile exits? | Pending one-rule-at-a-time ablation. |
| Which profile rule hurt most? | Realized losses are dominated by extended `BAR_EXIT`, `PROFILE_HARD_STOP`, and `STOP`; causal ablation remains pending. |
| Did POC reclaim clip winners? | Not proven. Its realized historical-ledger expectancy is positive, but later-target counterfactual fields are absent. |
| Did risk-state or market-profile gates add net value? | Market-profile-only blocked two losing trades for +0.96 shadow value; too small to promote. Risk-state causal value remains unestablished. |
| Did all-gates deserve promotion? | No. Existing all-gates configurations blocked all trades. |
| Best robust V8.6 candidate? | None yet. Baseline reproduction must precede candidate selection. |
| What remains shadow-only? | Profile exits, market-profile gate, risk-state gate, VPIN, anti-patterns, pressure confirmation. |

## Next Research Phase

Run the controlled V8.4 reproduction, then profile-exit ablation, then gate shadow value. Only surviving components enter staged parameter and robustness validation.
