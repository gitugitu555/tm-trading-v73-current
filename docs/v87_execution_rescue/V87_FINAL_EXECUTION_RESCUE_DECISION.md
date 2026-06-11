# V8.7 Final Execution Rescue Decision

## Decision

Do not promote an early-entry strategy yet. First repair the runner so signal generation is independent of position/execution state, then compare execution timing against one immutable signal stream.

## Answers

| Question | Current answer |
|---|---|
| How much Lag 0 edge can be recovered honestly? | Not yet measurable from the historical lag labels because they use different signal streams. |
| Which timing method works best? | Lag 0 close and Lag 1 open are effectively identical on the fixed signal stream. All honest partial-entry thresholds tested were negative after costs. |
| Can early signals predict final divergence? | Yes partially. Precision rises from 71.4% at 10% volume to 91.3% at 90%; recall rises from 19.6% to 82.4%. |
| Does pressure confirmation help? | Signed trade-flow proxy did not rescue expectancy in the preliminary sample. True OFI/MLOFI needs aligned L2. |
| Does passive/pullback execution help? | Not established. Trade-only data cannot prove maker fills. |
| Is BAR_EXIT still a major loss source? | Yes. Historical BAR_EXIT losses dominate, and about 97% had positive MFE before exit. |
| Is the final candidate robust after costs? | No candidate qualifies. |

## Critical Correction

`lag1_open` is normally the same trade price as `lag0_close` for contiguous volume bars. The historical Lag 0/Lag 1 runs share only 2,890 signal IDs, so their performance gap is dominated by runner path/selection semantics rather than a clean entry-price delay experiment.

## Promote / Shadow / Delete

- Promote: none.
- Shadow: partial-bar observability, MFE-protecting exit research, signed-flow pressure proxy.
- Delete/reject: all-gates live mode and any claim that historical Lag 0 versus Lag 1 alone proves entry-price alpha decay.

## Next Required Engineering Phase

Build a signal-first replay:

1. Emit every final and partial signal into an immutable signal ledger regardless of open positions.
2. Apply Lag 0, Lag 1, latency, overlap, and position-allocation policies to that same ledger.
3. Compare entry timing only after signal IDs and opportunity sets are fixed.
