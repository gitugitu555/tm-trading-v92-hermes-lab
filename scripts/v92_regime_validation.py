#!/usr/bin/env python3
"""
V9.2 Regime Classifier Validation
Tests the new Regime Classifier retroactively against the D4 signal.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.regime_classifier import add_regime_labels
from features.v92_data_policy import discover_tier2_bar_files, epoch_to_ns_value

# Import old v73 prime functions for D4 logic.
OLD_ROOT = ROOT.parent / "tm-trading-v73-current"
sys.path.insert(0, str(OLD_ROOT))
from prime.volume_bars import VolumeBar
from prime.volume_bar_cvd import divergence_side_at
from research.v91_signal_purity import historical_flat_thresholds, htf_allows, one_hour_cvd_changes


def main():
    print("Loading New 500-BTC Volume Bars (Full 6 Years)...")
    tier2_dir = ROOT / "data/hft/tier2"
    files = discover_tier2_bar_files(tier2_dir, symbol="BTCUSDT", all_mode="all_wins")

    if not files:
        print("No Tier-2 files found!")
        return

    df_list = [pd.read_parquet(f) for f in files]
    df_pd = pd.concat(df_list, ignore_index=True)
    df_pd = df_pd.sort_values("open_time").reset_index(drop=True)

    print(f"Loaded {len(df_pd)} 500-BTC base bars. Applying V9.2 Regime Classifier...")
    df_pl = pl.from_pandas(df_pd)
    df_pl = add_regime_labels(df_pl)

    df_pd["cumulative_delta"] = df_pd["volume_delta"].cumsum()

    bars = []
    regimes = df_pl["regime"].to_list()

    for row in df_pd.itertuples():
        start_ns = epoch_to_ns_value(row.open_time)
        end_ns = epoch_to_ns_value(row.close_time)
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
            ticks=row.trade_count,
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

        regime = regimes[idx]
        raw_return = (bars[idx + horizon].close - bars[idx].close) / bars[idx].close
        signed_return_bps = side * raw_return * 10_000
        net_return_bps = signed_return_bps - 5.0

        year = pd.to_datetime(bars[idx].end_ts_ns, unit="ns").year
        period = "2024-2026" if year >= 2024 else "2020-2023"

        results.append({
            "idx": idx,
            "period": period,
            "regime": regime,
            "side": side,
            "raw_return": raw_return,
            "net_bps": net_return_bps,
        })

    df_res = pd.DataFrame(results)

    print("\n=== D4 Signal Performance by V9.2 Regime (Rigorous Diagnostics) ===")

    from research.v91_d4_surface import surface_metrics

    for period in ["2020-2023", "2024-2026"]:
        print(f"\n--- Period: {period} ---")
        sub_df = df_res[df_res["period"] == period]

        if len(sub_df) == 0:
            print("No events.")
            continue

        for regime in ["EXHAUSTED", "TREND_BUILDUP", "ABSORPTION", "NOISE"]:
            regime_df = sub_df[sub_df["regime"] == regime]
            if len(regime_df) == 0:
                continue

            tuples = list(zip(regime_df["side"], regime_df["raw_return"]))
            metrics = surface_metrics(tuples, bootstrap_samples=1000)

            mean_net = metrics["net_expectancy_bps"]["5"]
            t_stat = metrics["t_stat"]
            median = metrics["median_signed_return_bps"] - 5.0
            ci_low = metrics["bootstrap_mean_bps_ci_95"][0] - 5.0
            ci_high = metrics["bootstrap_mean_bps_ci_95"][1] - 5.0

            print(f"[{regime}] Count: {len(tuples):<4} | Mean Net: {mean_net:>6.2f} bps | Median Net: {median:>6.2f} bps | "
                  f"t-stat: {t_stat:>5.2f} | 95% CI: [{ci_low:>6.2f}, {ci_high:>6.2f}]")

    print("\n--- 2024-2026 Out-of-Sample Split (EXHAUSTED Regime Only) ---")
    recent_exh = df_res[(df_res["period"] == "2024-2026") & (df_res["regime"] == "EXHAUSTED")].copy()
    if len(recent_exh) > 0:
        half_idx = len(recent_exh) // 2
        h1 = recent_exh.iloc[:half_idx]
        h2 = recent_exh.iloc[half_idx:]

        for name, h_df in [("First Half", h1), ("Second Half", h2)]:
            tuples = list(zip(h_df["side"], h_df["raw_return"]))
            metrics = surface_metrics(tuples, bootstrap_samples=1000)
            print(f"[{name}] Count: {len(tuples):<3} | Mean Net: {metrics['net_expectancy_bps']['5']:>6.2f} bps | "
                  f"Median Net: {metrics['median_signed_return_bps'] - 5.0:>6.2f} bps | t-stat: {metrics['t_stat']:>5.2f}")


if __name__ == "__main__":
    main()
