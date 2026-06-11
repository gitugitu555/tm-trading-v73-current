# V8.7 Exit Loss Repair

Historical-ledger diagnostics: `results/v87_execution_rescue/exit_loss_repair/exit_loss_diagnostics.json`.

Counterfactual hold/stop variants require fresh path replay; MAE/MFE alone cannot establish stop recovery after exit.

Historical BAR_EXIT and hard-stop losses recorded positive MFE in roughly 95% to 98% of cases. MFE-protecting/breakeven research should precede wider-stop promotion.

Historical loss-path evidence:

- `v85_apples_lag_only` BAR_EXIT: 4,938 trades, net -5,199.24; 97.3% recorded positive MFE.
- `v85_profile_exit` BAR_EXIT: 1,526 trades, net -2,561.53; 97.4% recorded positive MFE.
- `v85_profile_exit` PROFILE_HARD_STOP: 276 trades, net -2,092.07; 94.6% recorded positive MFE.

MFE-protecting/breakeven research should precede wider-stop promotion.
