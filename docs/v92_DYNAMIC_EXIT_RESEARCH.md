# V9.2 Dynamic Exit Research

## Purpose
Fixed TP/SL geometries have consistently decayed or proven highly sensitive to parameter fitting. This research tracks the effectiveness of replacing static exits with dynamic, state-aware exits on Tier-2 alpha signals.

## Tested Exits
1. **CVD Reversal Exit**: Exits if the CVD return z-score flips past a specified threshold against the trade direction for N confirmation bars.
2. **POC / VAH / VAL Exit**: Profile-based exit utilizing volume nodes.
3. **Time Stop**: Exits if minimum favourable excursion (MFE) is not met within N bars.
4. **ATR Trailing Stop**: Dynamically trails the price from the highest/lowest level reached since entry.
5. **Partial + Dynamic Remainder**: Scale-out at 1x ATR, trail the rest by 2x ATR.

## Required Comparisons
Each dynamic exit MUST be compared against:
- Fixed TP/SL baseline
- No-exit horizon return
- Bar-exit baseline

## Success Criteria
A dynamic exit is deemed successful if it achieves:
1. Higher `MAE_avoidance_ratio` than fixed TP/SL
2. Higher `MFE_capture_ratio`
3. A statistically significant improvement in the 2024-2026 out-of-sample period.
