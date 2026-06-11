# Trade Path Reconstruction

`research/v88_trade_path.py` reconstructs up to 96 forward bars for every immutable signal.

Preliminary summary:

- Paths: 820
- Average MFE: 1.317%
- Average MAE: 1.414%
- Positive MFE before negative 96-bar close: 58.78%

Outputs include first target/stop touches, MFE/MAE timing, bar-exit returns, and giveback.
