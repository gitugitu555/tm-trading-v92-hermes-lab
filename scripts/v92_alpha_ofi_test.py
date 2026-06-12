#!/usr/bin/env python3
"""
V9.2 Alpha OFI Strategy Tester
Tests the OFI Absorption signal gated by the Regime Classifier.
Includes native rigorous statistical diagnostics (t-stat, CI, out-of-sample).
"""

import sys
import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path
from numba import njit
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.regime_classifier import add_regime_labels

COSTS_BPS = 5.0
BOOTSTRAP_SAMPLES = 1000

@njit
def bootstrap_mean_ci_tstat(signed_returns: np.ndarray, samples: int = 1000):
    n = len(signed_returns)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0
        
    mean_val = np.mean(signed_returns)
    std_val = np.std(signed_returns)
    t_stat = mean_val / (std_val / math.sqrt(n)) if std_val > 0 else 0.0
    
    # Numba bootstrap
    bs_means = np.zeros(samples)
    for i in range(samples):
        indices = np.random.randint(0, n, size=n)
        bs_means[i] = np.mean(signed_returns[indices])
        
    bs_means.sort()
    ci_low = bs_means[int(0.025 * samples)]
    ci_high = bs_means[int(0.975 * samples)]
    
    return mean_val, t_stat, ci_low, ci_high

def calculate_stats(df: pd.DataFrame, prefix: str = ""):
    """Calculates robust statistical metrics for a set of events."""
    n = len(df)
    if n == 0:
        return f"{prefix} Count: 0"
        
    signed_ret = df['signed_return_bps'].values
    median = np.median(signed_ret) - COSTS_BPS
    
    mean_raw, t_stat, ci_low_raw, ci_high_raw = bootstrap_mean_ci_tstat(signed_ret, BOOTSTRAP_SAMPLES)
    mean_net = mean_raw - COSTS_BPS
    ci_low = ci_low_raw - COSTS_BPS
    ci_high = ci_high_raw - COSTS_BPS
    
    return f"{prefix} Count: {n:<4} | Mean Net: {mean_net:>6.2f} bps | Median Net: {median:>6.2f} bps | t-stat: {t_stat:>5.2f} | 95% CI: [{ci_low:>6.2f}, {ci_high:>6.2f}]"

def main():
    print("1. Loading 500-BTC Base Bars & Applying Regime Classifier...")
    tier2_dir = ROOT / "data/hft/tier2"
    bar_files = sorted(tier2_dir.glob("BTCUSDT_tier2_500btc_*.parquet"))
    
    if not bar_files:
        print("No Volume Bar files found.")
        return
        
    df_bars_pl = pl.concat([pl.scan_parquet(f) for f in bar_files]).collect()
    df_bars_pl = df_bars_pl.sort("open_time")
    
    # Apply regime classifier
    df_bars_pl = add_regime_labels(df_bars_pl)
    
    print("2. Loading Available 1-Second OFI Cache...")
    ofi_dir = ROOT / "data/hft/tier2/ofi"
    ofi_files = sorted(ofi_dir.glob("BTCUSDT_ofi_1s_*.parquet"))
    
    if not ofi_files:
        print("No OFI files found in cache.")
        return
        
    print(f"   -> Found {len(ofi_files)} OFI hour-files. Loading and assembling...")
    df_ofi_pl = pl.concat([pl.read_parquet(f) for f in ofi_files])
    
    # Sort and calculate cumulative OFI to enable instantaneous bar accumulation math
    df_ofi_pl = df_ofi_pl.sort("datetime").with_columns(
        pl.col("ofi").cum_sum().alias("cumulative_ofi")
    )
    
    print("3. AsOf Joining OFI to Volume Bars...")
    df_ofi_pl = df_ofi_pl.with_columns(pl.col("datetime").cast(pl.Datetime("ns")))
    
    # Convert timestamps to align
    df_bars_pl = df_bars_pl.with_columns([
        pl.from_epoch("open_time", time_unit="us").cast(pl.Datetime("ns")).alias("datetime_open"),
        pl.from_epoch("close_time", time_unit="us").cast(pl.Datetime("ns")).alias("datetime_close")
    ])
    
    df_join_open = df_bars_pl.join_asof(df_ofi_pl.select(["datetime", "cumulative_ofi"]), left_on="datetime_open", right_on="datetime", strategy="backward")
    df_join_open = df_join_open.rename({"cumulative_ofi": "ofi_at_open"}).drop("datetime")
    
    df_join_open = df_join_open.sort("datetime_close")
    df_full = df_join_open.join_asof(df_ofi_pl.select(["datetime", "cumulative_ofi"]), left_on="datetime_close", right_on="datetime", strategy="backward")
    df_full = df_full.rename({"cumulative_ofi": "ofi_at_close"}).drop("datetime")
    
    # Total OFI accumulated during this volume bar
    df_full = df_full.with_columns(
        (pl.col("ofi_at_close") - pl.col("ofi_at_open")).alias("bar_ofi")
    ).drop_nulls("bar_ofi")
    
    if len(df_full) == 0:
        print("No overlapping dates between OFI cache and Volume Bars.")
        return
        
    print(f"   -> Valid overlapping bars extracted: {len(df_full)}")
    
    # 4. Strategy Logic: Branch B (OFI Absorption)
    # Define significant OFI skew threshold (e.g., top/bottom 10%)
    df_pd = df_full.to_pandas()
    
    # We only care about extreme OFI prints
    q_top = df_pd['bar_ofi'].quantile(0.90)
    q_bot = df_pd['bar_ofi'].quantile(0.10)
    
    # Calculate forward returns (e.g. 24 bars)
    horizon = 24
    df_pd['fwd_close'] = df_pd['close'].shift(-horizon)
    df_pd['raw_return'] = (df_pd['fwd_close'] - df_pd['close']) / df_pd['close']
    df_pd = df_pd.dropna(subset=['fwd_close'])
    
    # Define events
    events = []
    for idx, row in df_pd.iterrows():
        side = 0
        
        # Branch B: Microstructure Absorption
        # If massive sell OFI but price holds -> Buy (Absorption)
        if row['bar_ofi'] < q_bot:
            side = 1 # Long
        # If massive buy OFI but price holds -> Sell (Absorption)
        elif row['bar_ofi'] > q_top:
            side = -1 # Short
            
        if side != 0:
            events.append({
                "datetime": row['datetime_close'],
                "regime": row['regime'],
                "side": side,
                "raw_return": row['raw_return'],
                "signed_return_bps": side * row['raw_return'] * 10_000
            })
            
    df_events = pd.DataFrame(events)
    if len(df_events) == 0:
        print("No events fired based on the thresholds.")
        return
        
    df_events['year'] = df_events['datetime'].dt.year
    df_events['period'] = np.where(df_events['year'] >= 2024, "2024-2026", "2020-2023")
    
    print("\n" + "="*60)
    print("V9.2 ALPHA OFI STRATEGY - RIGOROUS DIAGNOSTICS")
    print("="*60)
    
    for period in ["2020-2023", "2024-2026"]:
        print(f"\n--- Period: {period} ---")
        sub_df = df_events[df_events['period'] == period]
        if len(sub_df) == 0:
            print("No events.")
            continue
            
        for regime in ["ABSORPTION", "EXHAUSTED", "TREND_BUILDUP", "NOISE"]:
            regime_df = sub_df[sub_df['regime'] == regime]
            print(calculate_stats(regime_df, prefix=f"[{regime}]"))
            
    # Out of Sample Split for ABSORPTION (since this is an Absorption signal)
    print("\n--- Out-of-Sample Split (ABSORPTION Regime Only) ---")
    abs_df = df_events[df_events['regime'] == "ABSORPTION"].sort_values("datetime").reset_index(drop=True)
    if len(abs_df) > 10:
        half_idx = len(abs_df) // 2
        print(calculate_stats(abs_df.iloc[:half_idx], prefix="[First Half] "))
        print(calculate_stats(abs_df.iloc[half_idx:], prefix="[Second Half]"))
    else:
        print(f"Not enough events for a meaningful OOS split (Count: {len(abs_df)})")

if __name__ == "__main__":
    main()
