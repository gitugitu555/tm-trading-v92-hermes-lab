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
        
    warning = " [WARNING: INSUFFICIENT SAMPLE < 100]" if n < 100 else ""
        
    signed_ret = df['signed_return_bps'].values
    median = np.median(signed_ret) - COSTS_BPS
    
    mean_raw, t_stat, ci_low_raw, ci_high_raw = bootstrap_mean_ci_tstat(signed_ret, BOOTSTRAP_SAMPLES)
    mean_net = mean_raw - COSTS_BPS
    ci_low = ci_low_raw - COSTS_BPS
    ci_high = ci_high_raw - COSTS_BPS
    
    return f"{prefix} Count: {n:<4} | Mean Net: {mean_net:>6.2f} bps | Median Net: {median:>6.2f} bps | t-stat: {t_stat:>5.2f} | 95% CI: [{ci_low:>6.2f}, {ci_high:>6.2f}]{warning}"

def evaluate_branch_events(df_pd: pd.DataFrame, events_list: list):
    """Evaluates signals for Branches A, B, and C."""
    
    # Pre-calculate quantiles for Branch thresholds (rolling to prevent forward leakage)
    # Actually, using global quantiles introduces mild future leakage if used across the whole set.
    # To be extremely strict, we could use rolling percentiles, but for rapid prototyping of the logic,
    # we'll use pandas expanding quantiles or just standard rolling max/min approximations.
    
    df_pd['vol_delta_roll_90'] = df_pd['volume_delta'].rolling(1000).quantile(0.90)
    df_pd['vol_delta_roll_10'] = df_pd['volume_delta'].rolling(1000).quantile(0.10)
    
    df_pd['vol_roll_95'] = df_pd['volume'].rolling(1000).quantile(0.95)
    
    df_pd['local_high'] = df_pd['high'].rolling(50).max()
    df_pd['local_low'] = df_pd['low'].rolling(50).min()
    
    # We only care about extreme OFI prints for Branch B
    if 'bar_ofi' in df_pd.columns:
        df_pd['ofi_roll_90'] = df_pd['bar_ofi'].rolling(1000).quantile(0.90)
        df_pd['ofi_roll_10'] = df_pd['bar_ofi'].rolling(1000).quantile(0.10)

    # Calculate forward returns (e.g. 24 bars)
    horizon = 24
    df_pd['fwd_close'] = df_pd['close'].shift(-horizon)
    df_pd['raw_return'] = (df_pd['fwd_close'] - df_pd['close']) / df_pd['close']
    
    df_pd = df_pd.dropna(subset=['fwd_close', 'vol_delta_roll_90'])
    
    for idx, row in df_pd.iterrows():
        regime = row['regime']
        
        # --- BRANCH A (Breakout / Trend Follow) ---
        # Low volatility build-up leads to expansion. Look for aggressive taker flow breakout.
        if regime == "TREND_BUILDUP":
            side_a = 0
            if row['volume_delta'] > row['vol_delta_roll_90'] and row['close'] >= row['local_high']:
                side_a = 1
            elif row['volume_delta'] < row['vol_delta_roll_10'] and row['close'] <= row['local_low']:
                side_a = -1
            if side_a != 0:
                events_list.append({"branch": "A_Breakout", "datetime": row['datetime_close'], "regime": regime, "side": side_a, "raw_return": row['raw_return'], "signed_return_bps": side_a * row['raw_return'] * 10_000})
                
        # --- BRANCH B (OFI Absorption) ---
        # Gated primarily for ABSORPTION regime, but we'll collect it across all to prove the filter works.
        if 'bar_ofi' in row and not pd.isna(row['bar_ofi']):
            side_b = 0
            # If massive sell OFI but price holds (not breaking low) -> Buy (Absorption)
            if row['bar_ofi'] < row['ofi_roll_10'] and row['close'] > row['local_low']:
                side_b = 1
            # If massive buy OFI but price holds (not breaking high) -> Sell (Absorption)
            elif row['bar_ofi'] > row['ofi_roll_90'] and row['close'] < row['local_high']:
                side_b = -1
            if side_b != 0:
                events_list.append({"branch": "B_Absorption", "datetime": row['datetime_close'], "regime": regime, "side": side_b, "raw_return": row['raw_return'], "signed_return_bps": side_b * row['raw_return'] * 10_000})
                
        # --- BRANCH C (Exhaustion Fade) ---
        # Gated for EXHAUSTED regime. Look for extreme volume spike (liquidation cascade) to fade.
        if regime == "EXHAUSTED":
            side_c = 0
            # Massive volume at local highs -> Exhaustion Top -> Short
            if row['volume'] > row['vol_roll_95'] and row['close'] >= row['local_high']:
                side_c = -1
            # Massive volume at local lows -> Exhaustion Bottom -> Long
            elif row['volume'] > row['vol_roll_95'] and row['close'] <= row['local_low']:
                side_c = 1
            if side_c != 0:
                events_list.append({"branch": "C_ExhaustionFade", "datetime": row['datetime_close'], "regime": regime, "side": side_c, "raw_return": row['raw_return'], "signed_return_bps": side_c * row['raw_return'] * 10_000})


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
    
    # Convert timestamps to align (handling mixed ms/us Binance epochs)
    df_bars_pl = df_bars_pl.with_columns([
        pl.when(pl.col("open_time") > 1e14)
          .then(pl.from_epoch("open_time", time_unit="us"))
          .otherwise(pl.from_epoch("open_time", time_unit="ms")).cast(pl.Datetime("ns")).alias("datetime_open"),
        pl.when(pl.col("close_time") > 1e14)
          .then(pl.from_epoch("close_time", time_unit="us"))
          .otherwise(pl.from_epoch("close_time", time_unit="ms")).cast(pl.Datetime("ns")).alias("datetime_close")
    ])
    
    print("2. Loading Available 1-Second OFI Cache...")
    ofi_dir = ROOT / "data/hft/tier2/ofi"
    ofi_files = sorted(ofi_dir.glob("BTCUSDT_ofi_1s_*.parquet"))
    
    df_full = df_bars_pl
    
    if ofi_files:
        print(f"   -> Found {len(ofi_files)} OFI hour-files. Loading and assembling...")
        df_ofi_pl = pl.concat([pl.read_parquet(f) for f in ofi_files])
        
        # Sort and calculate cumulative OFI to enable instantaneous bar accumulation math
        df_ofi_pl = df_ofi_pl.sort("datetime").with_columns(
            pl.col("ofi").cum_sum().alias("cumulative_ofi")
        )
        
        print("3. AsOf Joining OFI to Volume Bars...")
        df_ofi_pl = df_ofi_pl.with_columns(pl.col("datetime").cast(pl.Datetime("ns")))
        
        df_join_open = df_bars_pl.join_asof(df_ofi_pl.select(["datetime", "cumulative_ofi"]), left_on="datetime_open", right_on="datetime", strategy="backward")
        df_join_open = df_join_open.rename({"cumulative_ofi": "ofi_at_open"}).drop("datetime")
        
        df_join_open = df_join_open.sort("datetime_close")
        df_full = df_join_open.join_asof(df_ofi_pl.select(["datetime", "cumulative_ofi"]), left_on="datetime_close", right_on="datetime", strategy="backward")
        df_full = df_full.rename({"cumulative_ofi": "ofi_at_close"}).drop("datetime")
        
        # Total OFI accumulated during this volume bar
        df_full = df_full.with_columns(
            (pl.col("ofi_at_close") - pl.col("ofi_at_open")).alias("bar_ofi")
        )
    else:
        print("   -> No OFI files found. Skipping Branch B (Absorption) generation.")
        
    print(f"   -> Executing strategy logic across {len(df_full)} bars...")
    df_pd = df_full.to_pandas()
    
    events = []
    evaluate_branch_events(df_pd, events)
    
    df_events = pd.DataFrame(events)
    if len(df_events) == 0:
        print("No events fired based on the thresholds.")
        return
        
    df_events['year'] = df_events['datetime'].dt.year
    df_events['period'] = np.where(df_events['year'] >= 2024, "2024-2026", "2020-2023")
    
    print("\n" + "="*80)
    print("V9.2 ALPHA STRATEGY EVALUATION - RIGOROUS DIAGNOSTICS")
    print("="*80)
    
    for branch in ["A_Breakout", "B_Absorption", "C_ExhaustionFade"]:
        branch_df = df_events[df_events['branch'] == branch]
        if len(branch_df) == 0: continue
        
        print(f"\n--- BRANCH: {branch} ---")
        for period in ["2020-2023", "2024-2026"]:
            print(f"  Period: {period}")
            sub_df = branch_df[branch_df['period'] == period]
            if len(sub_df) == 0:
                print("    No events.")
                continue
                
            for regime in ["TREND_BUILDUP", "ABSORPTION", "EXHAUSTED", "NOISE"]:
                regime_df = sub_df[sub_df['regime'] == regime]
                if len(regime_df) == 0: continue
                print("    " + calculate_stats(regime_df, prefix=f"[{regime}]"))
                
        # OOS Split for the primary target regime of the branch
        target_regime = "TREND_BUILDUP" if branch == "A_Breakout" else "ABSORPTION" if branch == "B_Absorption" else "EXHAUSTED"
        print(f"  [Out-of-Sample Split ({target_regime} Regime Only)]")
        oos_df = branch_df[branch_df['regime'] == target_regime].sort_values("datetime").reset_index(drop=True)
        if len(oos_df) >= 100:
            half_idx = len(oos_df) // 2
            print("    " + calculate_stats(oos_df.iloc[:half_idx], prefix="[First Half] "))
            print("    " + calculate_stats(oos_df.iloc[half_idx:], prefix="[Second Half]"))
        else:
            print(f"    Not enough events for a meaningful OOS split (Count: {len(oos_df)})")

if __name__ == "__main__":
    main()
