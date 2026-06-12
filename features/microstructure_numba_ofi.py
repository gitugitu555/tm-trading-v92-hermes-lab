import numpy as np
from numba import njit
from numba.typed import Dict
from numba.types import float64
import pandas as pd

@njit
def process_chunk_numba(sides: np.ndarray, prices: np.ndarray, quantities: np.ndarray) -> np.ndarray:
    n = len(prices)
    ofi_out = np.zeros(n, dtype=np.float64)
    
    prev_best_bid_price = 0.0
    prev_best_bid_qty = 0.0
    prev_best_ask_price = 1e15
    prev_best_ask_qty = 0.0
    
    bids = Dict.empty(key_type=float64, value_type=float64)
    asks = Dict.empty(key_type=float64, value_type=float64)
    
    # 0 = bid, 1 = ask
    for i in range(n):
        s = sides[i]
        p = prices[i]
        q = quantities[i]
        
        ofi = 0.0
        
        if s == 0: # BID
            # 1. Update Orderbook State
            if q == 0.0:
                if p in bids:
                    bids.pop(p)
            else:
                bids[p] = q
                
            # 2. Recompute Best Bid (Optimized)
            if len(bids) == 0:
                current_best_bid = 0.0
                current_best_bid_qty = 0.0
            else:
                if q > 0.0 and p >= prev_best_bid_price:
                    # The update improves or matches the best bid, it is the new best.
                    current_best_bid = p
                    current_best_bid_qty = q
                elif q == 0.0 and p == prev_best_bid_price:
                    # The best bid was deleted! We MUST rescan the entire side.
                    best_p = 0.0
                    for bp in bids:
                        if bp > best_p:
                            best_p = bp
                    current_best_bid = best_p
                    current_best_bid_qty = bids[best_p]
                else:
                    # Update was deep in the book, best bid is unchanged
                    current_best_bid = prev_best_bid_price
                    current_best_bid_qty = prev_best_bid_qty
                    
            # 3. Calculate Delta W
            if current_best_bid > prev_best_bid_price:
                delta_w = current_best_bid_qty
            elif current_best_bid == prev_best_bid_price:
                delta_w = current_best_bid_qty - prev_best_bid_qty
            else:
                delta_w = 0.0
                
            ofi = delta_w
            prev_best_bid_price = current_best_bid
            prev_best_bid_qty = current_best_bid_qty
            
        else: # ASK
            # 1. Update Orderbook State
            if q == 0.0:
                if p in asks:
                    asks.pop(p)
            else:
                asks[p] = q
                
            # 2. Recompute Best Ask (Optimized)
            if len(asks) == 0:
                current_best_ask = 1e15
                current_best_ask_qty = 0.0
            else:
                if q > 0.0 and p <= prev_best_ask_price:
                    # The update improves or matches the best ask, it is the new best.
                    current_best_ask = p
                    current_best_ask_qty = q
                elif q == 0.0 and p == prev_best_ask_price:
                    # The best ask was deleted! We MUST rescan the entire side.
                    best_p = 1e15
                    for ap in asks:
                        if ap < best_p:
                            best_p = ap
                    current_best_ask = best_p
                    current_best_ask_qty = asks[best_p]
                else:
                    # Update was deep in the book, best ask is unchanged
                    current_best_ask = prev_best_ask_price
                    current_best_ask_qty = prev_best_ask_qty
                    
            # 3. Calculate Delta V
            if current_best_ask < prev_best_ask_price:
                delta_v = current_best_ask_qty
            elif current_best_ask == prev_best_ask_price:
                delta_v = current_best_ask_qty - prev_best_ask_qty
            else:
                delta_v = 0.0
                
            ofi = -delta_v
            prev_best_ask_price = current_best_ask
            prev_best_ask_qty = current_best_ask_qty
            
        ofi_out[i] = ofi
        
    return ofi_out

def process_chunk_fast(df: pd.DataFrame) -> pd.DataFrame:
    """Wrapper that translates the dataframe to numpy arrays for Numba processing."""
    # Convert sides string to ints: 0 for 'bid', 1 for 'ask'
    sides_arr = (df['side'] == 'ask').astype(np.int8).values
    prices_arr = df['price'].astype(np.float64).values
    qty_arr = df['quantity'].astype(np.float64).values
    
    ofi_array = process_chunk_numba(sides_arr, prices_arr, qty_arr)
    df['ofi'] = ofi_array
    return df
