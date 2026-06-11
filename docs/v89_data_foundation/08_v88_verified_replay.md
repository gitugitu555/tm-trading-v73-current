# V8.9 Verified V8.8 Replay

The fixed 66-policy replay completed over the verified immutable ledger.

Best full-sample policy:

- Policy: `trail_0.002_0.25`
- Trail starts at 0.2% MFE and permits 25% MFE giveback
- Trades: 27,978
- Net expectancy: -0.00023704
- Profit factor: 0.8660
- Sharpe: -0.7279
- Win rate: 81.62%

Yearly net expectancy for this full-sample-selected policy is positive in
2021, 2024, and 2025, and negative in 2020, 2022, 2023, and 2026.

This is evidence of regime dependence, not promotion evidence. The inherited
replay currently reports zero fee and slippage fields, so after-cost validation
is incomplete. Because the best result is already negative, this limitation
cannot reverse the rejection decision.

