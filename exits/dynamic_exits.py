"""
V9.2 Dynamic Exits Research

Implementations of priority exits:
1. CVD reversal exit
2. Time stop
3. ATR trailing stop
"""

import pandas as pd
import numpy as np

def atr_trailing_stop(entry_price: float, side: str, atr_series: pd.Series, price_series: pd.Series, atr_multiplier: float = 2.0) -> pd.Series:
    """
    Calculates the trailing stop level for each bar while the trade is active.
    
    For long trades:
    trail stop = highest_price_since_entry - 2x ATR
    
    For short trades:
    trail stop = lowest_price_since_entry + 2x ATR
    """
    if side == "long":
        highest_since_entry = price_series.cummax()
        trail_levels = highest_since_entry - (atr_series * atr_multiplier)
        return trail_levels
    else:
        lowest_since_entry = price_series.cummin()
        trail_levels = lowest_since_entry + (atr_series * atr_multiplier)
        return trail_levels

def time_stop(entry_index: int, current_index: int, mfe_bps: float, max_bars: int = 12, required_mfe_bps: float = 5.0) -> bool:
    """
    Exit when trade has not reached minimum favourable excursion within N bars.
    """
    bars_in_trade = current_index - entry_index
    if bars_in_trade >= max_bars and mfe_bps < required_mfe_bps:
        return True
    return False

def cvd_reversal_exit(cvd_zscore: float, side: str, threshold: float = 1.0) -> bool:
    """
    Exit if CVD return z-score flips past the threshold against the trade direction.
    """
    if side == "long" and cvd_zscore < -threshold:
        return True
    if side == "short" and cvd_zscore > threshold:
        return True
    return False
