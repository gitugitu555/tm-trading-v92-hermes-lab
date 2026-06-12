import sys
import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.regime_classifier import add_regime_labels

def main():
    tier2_dir = ROOT / "data/hft/tier2"
    files = sorted(tier2_dir.glob("BTCUSDT_tier2_500btc_*.parquet"))
    df_pl = pl.concat([pl.scan_parquet(f) for f in files]).collect()
    df_pl = df_pl.sort("open_time")
    df_pl = add_regime_labels(df_pl)
    
    df_pd = df_pl.to_pandas()
    
    # Handle mixed ms/us timestamps
    is_us = df_pd['open_time'] > 1e14
    df_pd['dt'] = pd.NaT
    df_pd.loc[is_us, 'dt'] = pd.to_datetime(df_pd.loc[is_us, 'open_time'], unit='us')
    df_pd.loc[~is_us, 'dt'] = pd.to_datetime(df_pd.loc[~is_us, 'open_time'], unit='ms')
    df_pd['year'] = df_pd['dt'].dt.year
    
    print("\n--- REGIME FREQUENCY BY YEAR ---")
    counts = df_pd.groupby(['year', 'regime']).size().unstack(fill_value=0)
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100
    
    print("Counts:")
    print(counts)
    print("\nPercentages (% of all bars that year):")
    print(percentages.round(2))

if __name__ == "__main__":
    main()
