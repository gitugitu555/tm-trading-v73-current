"""
V9.2 Contextual Filters (Regime Classifiers)

These are not entry signals, but regime classifiers for trade eligibility.
Adheres to V9.2 Leakage Rules:
- Higher timeframe indicators must use completed candles only.
"""

import pandas as pd
import numpy as np

def calculate_atr_regime(df: pd.DataFrame, period: int = 14, threshold_pct: float = 0.002) -> pd.DataFrame:
    """
    Calculates the ATR and flags the volatility regime.
    Uses shifted closes to ensure calculation is based on completed bars.
    """
    out = df.copy()
    
    prev_close = out['close'].shift(1)
    tr1 = out['high'] - out['low']
    tr2 = (out['high'] - prev_close).abs()
    tr3 = (out['low'] - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out['atr'] = tr.rolling(window=period).mean()
    out['atr_pct'] = out['atr'] / out['close']
    
    out['regime_high_vol'] = out['atr_pct'] > threshold_pct
    return out

def calculate_adr_exhaustion(daily_df: pd.DataFrame, intraday_df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    ADR (Average Daily Range) must use previous COMPLETED daily ranges only.
    Matches the completed daily ADR to the intraday dataframe.
    """
    daily = daily_df.copy()
    daily['daily_range'] = daily['high'] - daily['low']
    # SHIFT 1 is critical here to prevent same-day leakage
    daily['adr'] = daily['daily_range'].shift(1).rolling(window=period).mean()
    
    # Map back to intraday by date
    intraday_df['date'] = intraday_df.index.normalize()
    merged = intraday_df.merge(daily[['adr']], left_on='date', right_index=True, how='left')
    
    # Calculate exhaustion
    merged['intraday_range'] = merged['high'].groupby(merged['date']).cummax() - merged['low'].groupby(merged['date']).cummin()
    merged['adr_exhaustion_pct'] = merged['intraday_range'] / merged['adr']
    
    merged['regime_adr_exhausted'] = merged['adr_exhaustion_pct'] > 0.85
    
    return merged.drop(columns=['date'])
