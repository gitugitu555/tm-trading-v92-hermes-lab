import polars as pl

def add_regime_labels(df: pl.DataFrame) -> pl.DataFrame:
    """
    Evaluates market regime at the close of every volume bar.
    Strictly past-only, no-leakage implementation.
    
    Expected input columns: open_time, close, high, low, open, volume
    Returns DataFrame with new 'regime' string column.
    """
    
    # 1. Convert timestamps to datetime for time-based rolling windows if needed
    if "open_time" in df.columns and df["open_time"].dtype in [pl.Int64, pl.Float64]:
        df = df.with_columns(pl.from_epoch("open_time", time_unit="ms").alias("datetime"))
    elif "start_ts_ns" in df.columns:
        df = df.with_columns(pl.from_epoch("start_ts_ns", time_unit="ns").alias("datetime"))
        
    df = df.sort("datetime")
    
    # 2. Daily Range (ADR) & Stretch calculation (using 14-day EMA of daily range)
    # Since we are on volume bars, we can approximate a "day" using time-based rolling
    # But for simplicity and pure no-leakage, let's use rolling windows based on bar count
    # Assuming ~500 bars per day on 300-BTC threshold, 14 days = ~7000 bars.
    
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("return"),
        (pl.col("high") - pl.col("low")).alias("bar_range"),
        (pl.col("close") - pl.col("open")).abs().alias("body_size")
    ])
    
    # Realized Volatility (e.g., 500-bar rolling ~ 1 day)
    df = df.with_columns(
        pl.col("return").rolling_std(window_size=500).alias("rv_1d")
    )
    
    # RV Percentile (rolling 30-day lookback ~ 15000 bars)
    df = df.with_columns(
        pl.col("rv_1d").rolling_quantile(quantile=0.15, window_size=15000).alias("rv_15th_pct")
    )
    
    # ADR (14-day average of daily high-low) -> approximated using rolling max/min over 500 bars
    df = df.with_columns(
        pl.col("high").rolling_max(window_size=500).alias("daily_high"),
        pl.col("low").rolling_min(window_size=500).alias("daily_low")
    )
    df = df.with_columns(
        (pl.col("daily_high") - pl.col("daily_low")).alias("daily_range")
    )
    df = df.with_columns(
        pl.col("daily_range").rolling_mean(window_size=7000).alias("adr_14d")
    )
    
    # ADR Stretch: how close is current price to the daily limits relative to ADR
    df = df.with_columns(
        ((pl.col("close") - pl.col("daily_low")) / pl.col("adr_14d")).alias("adr_stretch")
    )
    
    # Volume Percentile (rolling 7 days ~ 3500 bars)
    df = df.with_columns(
        pl.col("volume").rolling_quantile(quantile=0.80, window_size=3500).alias("vol_80th_pct")
    )
    
    # 3. Classify Regimes
    df = df.with_columns(
        pl.when(
            # TREND_BUILDUP: Volatility < 15th percentile
            pl.col("rv_1d") < pl.col("rv_15th_pct")
        ).then(pl.lit("TREND_BUILDUP"))
        .when(
            # EXHAUSTED: ADR Stretch > 85% or < 15% (extremes)
            (pl.col("adr_stretch") > 0.85) | (pl.col("adr_stretch") < 0.15)
        ).then(pl.lit("EXHAUSTED"))
        .when(
            # ABSORPTION: Volume > 80th pct, but body is tiny (< 25% of bar range)
            (pl.col("volume") > pl.col("vol_80th_pct")) & 
            (pl.col("body_size") < (0.25 * pl.col("bar_range")))
        ).then(pl.lit("ABSORPTION"))
        .otherwise(pl.lit("NOISE"))
        .alias("regime")
    )
    
    return df
