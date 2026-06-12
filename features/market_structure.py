"""
V9.2 Market Structure Feature Extractors

Calculates swing highs, swing lows, and structural distance metrics.
Adheres to V9.2 Leakage Rules: 
- No future-confirmed swing used at the pivot bar.
"""

import pandas as pd
import numpy as np

def calculate_swing_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Calculates swing highs and lows with STRICT delayed confirmation.
    A swing high is only known at `pivot_index + window`.
    """
    out = df.copy()
    
    # Forward rolling to find the max/min in the window AFTER the pivot
    # Backward rolling to find the max/min in the window BEFORE the pivot
    # A pivot is confirmed only when the current bar is 'window' bars past the pivot.
    
    # For a high to be valid at index i, it must be the highest in [i-window, i+window]
    # To prevent leakage, this fact is only known at i+window.
    
    # Using shift to ensure we only look at completed data
    highs = out['high'].values
    lows = out['low'].values
    
    swing_high = np.full(len(out), np.nan)
    swing_low = np.full(len(out), np.nan)
    
    for i in range(window * 2, len(out)):
        pivot = i - window
        
        # Check Swing High
        if highs[pivot] == np.max(highs[pivot - window : i + 1]):
            swing_high[i] = highs[pivot]
        else:
            swing_high[i] = swing_high[i-1] # Carry forward the last known swing high
            
        # Check Swing Low
        if lows[pivot] == np.min(lows[pivot - window : i + 1]):
            swing_low[i] = lows[pivot]
        else:
            swing_low[i] = swing_low[i-1] # Carry forward the last known swing low
            
    out['last_confirmed_swing_high'] = swing_high
    out['last_confirmed_swing_low'] = swing_low
    out['distance_to_swing_high_bps'] = (out['last_confirmed_swing_high'] - out['close']) / out['close'] * 10000
    out['distance_to_swing_low_bps'] = (out['close'] - out['last_confirmed_swing_low']) / out['close'] * 10000
    
    return out
