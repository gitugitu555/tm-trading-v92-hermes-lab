#!/usr/bin/env python3
"""
V9.2 Regime Classifier Validation
Tests the new Regime Classifier retroactively against the D4 signal.
"""

import sys
import pandas as pd
import polars as pl
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.regime_classifier import add_regime_labels

# Import old v73 prime functions for D4 logic
OLD_ROOT = ROOT.parent / "tm-trading-v73-current"
sys.path.insert(0, str(OLD_ROOT))
from prime.volume_bars import VolumeBar
from prime.volume_bar_cvd import divergence_side_at
from research.v91_signal_purity import historical_flat_thresholds, htf_allows, one_hour_cvd_changes

def main():
    print("Loading New 500-BTC Volume Bars (Full 6 Years)...")
    tier2_dir = ROOT / "data/hft/tier2"
    files = sorted(tier2_dir.glob("BTCUSDT_tier2_500btc_*.parquet"))
    
    if not files:
        print("No Tier-2 files found!")
        return
        
    df_list = [pd.read_parquet(f) for f in files]
    df_pd = pd.concat(df_list, ignore_index=True)
    df_pd = df_pd.sort_values("open_time").reset_index(drop=True)
    
    print(f"Loaded {len(df_pd)} 500-BTC base bars. Applying V9.2 Regime Classifier...")
    df_pl = pl.from_pandas(df_pd)
    df_pl = add_regime_labels(df_pl)
    
    # Calculate cumulative delta for the VolumeBar initialization
    df_pd["cumulative_delta"] = df_pd["volume_delta"].cumsum()
    
    # We need to run the D4 logic, which expects a list of VolumeBar objects
    bars = []
    regimes = df_pl["regime"].to_list()
    
    for row in df_pd.itertuples():
        # open_time is in microseconds
        start_ns = row.open_time * 1000
        end_ns = row.close_time * 1000
        buy_v = (row.volume + row.volume_delta) / 2.0
        sell_v = (row.volume - row.volume_delta) / 2.0
        
        bars.append(VolumeBar(
            start_ts_ns=start_ns,
            end_ts_ns=end_ns,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            buy_volume=buy_v,
            sell_volume=sell_v,
            delta=row.volume_delta,
            cumulative_delta=row.cumulative_delta,
            ticks=row.trade_count
        ))
        
    print("Calculating D4 Signal Events...")
    lookback_bars = 40
    horizon = 24
    
    htf_changes = one_hour_cvd_changes(bars)
    flat_thresholds = historical_flat_thresholds(htf_changes)
    
    results = []
    
    for idx in range(lookback_bars, len(bars) - horizon):
        side = divergence_side_at(bars[idx - lookback_bars : idx + 1], lookback_bars, lookback_bars)
        if side is None or not htf_allows(side, htf_changes[idx], flat_thresholds[idx]):
            continue
            
        # D4 Event Triggered!
        regime = regimes[idx]
        raw_return = (bars[idx + horizon].close - bars[idx].close) / bars[idx].close
        signed_return_bps = side * raw_return * 10_000
        net_return_bps = signed_return_bps - 5.0 # 5 bps taker cost
        
        # Check period
        year = pd.to_datetime(bars[idx].end_ts_ns, unit='ns').year
        period = "2024-2026" if year >= 2024 else "2020-2023"
        
        results.append({
            "idx": idx,
            "period": period,
            "regime": regime,
            "net_bps": net_return_bps
        })
        
    df_res = pd.DataFrame(results)
    
    print("\n=== D4 Signal Performance by V9.2 Regime ===")
    
    for period in ["2020-2023", "2024-2026"]:
        print(f"\n--- Period: {period} ---")
        sub_df = df_res[df_res["period"] == period]
        
        if len(sub_df) == 0:
            print("No events.")
            continue
            
        grouped = sub_df.groupby("regime")["net_bps"].agg(["count", "mean", "sum"])
        
        # Sort by mean
        grouped = grouped.sort_values("mean", ascending=False)
        print(grouped)
        
        print(f"\nTotal Overall Net Expectancy: {sub_df['net_bps'].mean():.2f} bps (Count: {len(sub_df)})")

if __name__ == "__main__":
    main()
