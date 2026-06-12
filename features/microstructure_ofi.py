"""
V9.2 Order Flow Imbalance (OFI) Calculator

Processes raw L2 Orderbook diffs to compute tick-level Order Flow Imbalance.
Maintains a lightweight BBO (Best Bid/Offer) state machine.

OFI Formula (Cont):
ΔW = 
  if P_bid_t > P_bid_{t-1}: V_bid_t
  if P_bid_t == P_bid_{t-1}: V_bid_t - V_bid_{t-1}
  if P_bid_t < P_bid_{t-1}: 0

ΔV = 
  if P_ask_t < P_ask_{t-1}: V_ask_t
  if P_ask_t == P_ask_{t-1}: V_ask_t - V_ask_{t-1}
  if P_ask_t > P_ask_{t-1}: 0

OFI = ΔW - ΔV
"""

import pandas as pd
import numpy as np

class OFIEngine:
    def __init__(self):
        # Best Bid State
        self.prev_best_bid_price = 0.0
        self.prev_best_bid_qty = 0.0
        
        # Best Ask State
        self.prev_best_ask_price = float('inf')
        self.prev_best_ask_qty = 0.0
        
        # We need a small dictionary to track top 10 levels for accurate BBO tracking
        # when the best level is completely deleted (qty=0).
        self.bids = {}
        self.asks = {}

    def process_update(self, side: str, price: float, qty: float) -> float:
        """
        Processes a single L2 update and returns the instantaneous OFI.
        Returns 0.0 if there is no top-of-book change.
        """
        ofi = 0.0
        
        if side == "bid":
            # Update local orderbook state
            if qty == 0.0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = qty
            
            # Recompute best bid
            if not self.bids:
                current_best_bid = 0.0
                current_best_bid_qty = 0.0
            else:
                current_best_bid = max(self.bids.keys())
                current_best_bid_qty = self.bids[current_best_bid]
                
            # Calculate Delta W
            if current_best_bid > self.prev_best_bid_price:
                delta_w = current_best_bid_qty
            elif current_best_bid == self.prev_best_bid_price:
                delta_w = current_best_bid_qty - self.prev_best_bid_qty
            else:
                delta_w = 0.0
                
            ofi = delta_w
            
            self.prev_best_bid_price = current_best_bid
            self.prev_best_bid_qty = current_best_bid_qty
            
        elif side == "ask":
            # Update local orderbook state
            if qty == 0.0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = qty
                
            # Recompute best ask
            if not self.asks:
                current_best_ask = float('inf')
                current_best_ask_qty = 0.0
            else:
                current_best_ask = min(self.asks.keys())
                current_best_ask_qty = self.asks[current_best_ask]
                
            # Calculate Delta V
            if current_best_ask < self.prev_best_ask_price:
                delta_v = current_best_ask_qty
            elif current_best_ask == self.prev_best_ask_price:
                delta_v = current_best_ask_qty - self.prev_best_ask_qty
            else:
                delta_v = 0.0
                
            # OFI = Delta W - Delta V (Note: Delta W is 0 here since it's an ask update)
            ofi = -delta_v
            
            self.prev_best_ask_price = current_best_ask
            self.prev_best_ask_qty = current_best_ask_qty
            
        return ofi

def process_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame of L2 updates (must be ordered by event_time),
    calculates the tick-level OFI and returns the annotated DataFrame.
    """
    engine = OFIEngine()
    ofi_list = []
    
    # Fast iteration using namedtuples or numpy arrays is preferred for production
    for row in df.itertuples(index=False):
        # We assume columns: side, price, quantity
        # Price and quantity might be strings in the raw data, ensure they are casted beforehand
        p = float(row.price)
        q = float(row.quantity)
        
        tick_ofi = engine.process_update(row.side, p, q)
        ofi_list.append(tick_ofi)
        
    df['ofi'] = ofi_list
    return df
