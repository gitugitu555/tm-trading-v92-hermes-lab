import polars as pl

from features.v92_data_policy import epoch_to_datetime_expr


def add_regime_labels(df: pl.DataFrame) -> pl.DataFrame:
    """
    Evaluates market regime at the close of every volume bar.
    Strictly past-only, no-leakage implementation.

    Expected input columns: open_time, close, high, low, open, volume
    Returns DataFrame with new 'regime' string column.
    """

    # Centralized ms/us timestamp normalization. Do not reimplement timestamp
    # conversion locally in scripts; use epoch_to_datetime_expr everywhere.
    if "datetime" not in df.columns:
        if "open_time" in df.columns and df["open_time"].dtype in [pl.Int64, pl.Float64, pl.UInt64, pl.UInt32, pl.Int32]:
            df = df.with_columns(epoch_to_datetime_expr("open_time").alias("datetime"))
        elif "start_ts_ns" in df.columns:
            df = df.with_columns(pl.from_epoch("start_ts_ns", time_unit="ns").alias("datetime"))

    df = df.sort("datetime")

    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("return"),
        (pl.col("high") - pl.col("low")).alias("bar_range"),
        (pl.col("close") - pl.col("open")).abs().alias("body_size"),
    ])

    # Realized Volatility (e.g., 500-bar rolling ~ 1 day)
    df = df.with_columns(
        pl.col("return").rolling_std(window_size=500).alias("rv_1d")
    )

    # RV Percentile (rolling 30-day lookback ~ 15000 bars)
    df = df.with_columns(
        pl.col("rv_1d").rolling_quantile(quantile=0.15, window_size=15000).alias("rv_15th_pct")
    )

    # ADR (14-day average of daily high-low) approximated with bar-count windows.
    df = df.with_columns(
        pl.col("high").rolling_max(window_size=500).alias("daily_high"),
        pl.col("low").rolling_min(window_size=500).alias("daily_low"),
    )
    df = df.with_columns(
        (pl.col("daily_high") - pl.col("daily_low")).alias("daily_range")
    )
    df = df.with_columns(
        pl.col("daily_range").rolling_mean(window_size=7000).alias("adr_14d")
    )

    # ADR Stretch: how close is current price to the daily limits relative to ADR.
    df = df.with_columns(
        ((pl.col("close") - pl.col("daily_low")) / pl.col("adr_14d")).alias("adr_stretch")
    )

    # Volume Percentile (rolling 7 days ~ 3500 bars)
    df = df.with_columns(
        pl.col("volume").rolling_quantile(quantile=0.80, window_size=3500).alias("vol_80th_pct")
    )

    # Classify regimes. This remains a v0.1 heuristic classifier; the spec can
    # evolve without changing the safety contract around timestamps and leakage.
    df = df.with_columns(
        pl.when(
            pl.col("rv_1d") < pl.col("rv_15th_pct")
        ).then(pl.lit("TREND_BUILDUP"))
        .when(
            (pl.col("adr_stretch") > 0.85) | (pl.col("adr_stretch") < 0.15)
        ).then(pl.lit("EXHAUSTED"))
        .when(
            (pl.col("volume") > pl.col("vol_80th_pct"))
            & (pl.col("body_size") < (0.25 * pl.col("bar_range")))
        ).then(pl.lit("ABSORPTION"))
        .otherwise(pl.lit("NOISE"))
        .alias("regime")
    )

    return df
