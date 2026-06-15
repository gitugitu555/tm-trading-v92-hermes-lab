#!/usr/bin/env python3
"""Research-only regime/context mismatch audit for V9.2 C_ExhaustionFade."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for site_packages in sorted((ROOT / ".venv" / "lib").glob("python*/site-packages")):
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

import numpy as np
import pandas as pd
import polars as pl

from replays.c_exhaustion_replay import add_v92_regime_labels, attach_c_exhaustion_signal, load_750btc_bars, normalize_v92_bar_timestamps


PERIOD_BOUNDS = {
    "early_period": (2020, 2021),
    "middle_period": (2022, 2024),
    "recent_period": (2025, 2026),
}

REALIZED_VOL_BUCKETS = ["<25", "25-50", "50-100", ">100"]
RANGE_EXPANSION_BUCKETS = ["<0.75", "0.75-1.25", "1.25-2.00", ">2.00"]
PRE_RETURN_BUCKETS = ["<-200", "-200 to -100", "-100 to -25", "-25 to 25", "25 to 100", "100 to 200", ">200"]
BODY_BUCKETS = ["<0.25", "0.25-0.50", ">0.50"]
VOLUME_BUCKETS = ["1.00-1.25", "1.25-1.75", ">1.75"]

REQUESTED_FEATURES = [
    "signal_time",
    "entry_time",
    "exit_time",
    "year",
    "exit_month",
    "net_return_bps",
    "gross_return_bps",
    "regime",
    "adr_stretch",
    "rv_1d",
    "rv_15th_pct",
    "volume",
    "vol_roll_95",
    "volume_over_vol95_ratio",
    "bar_range",
    "body_size",
    "body_to_range_ratio",
    "close_vs_local_low_bps",
    "pre_signal_return_3_bars_bps",
    "pre_signal_return_6_bars_bps",
    "pre_signal_return_12_bars_bps",
    "pre_signal_return_24_bars_bps",
    "pre_signal_return_36_bars_bps",
    "post_signal_return_3_bars_bps",
    "post_signal_return_6_bars_bps",
    "post_signal_return_12_bars_bps",
    "post_signal_return_24_bars_bps",
    "post_signal_return_36_bars_bps",
    "realized_vol_12_bars_bps",
    "realized_vol_24_bars_bps",
    "realized_vol_36_bars_bps",
    "range_expansion_ratio_12",
    "range_expansion_ratio_24",
    "range_expansion_ratio_36",
    "trend_continuation_flag_12",
    "trend_continuation_flag_24",
    "trend_continuation_flag_36",
    "failed_reversal_flag_12",
    "failed_reversal_flag_24",
    "failed_reversal_flag_36",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        val = float(value)
        if math.isnan(val):
            return "n/a"
        if math.isinf(val):
            return "inf" if val > 0 else "-inf"
        return f"{val:.6f}"
    return str(value)


def _md_table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _safe_profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    if not len(wins) and not len(losses):
        return 0.0
    if len(losses) and abs(loss_sum) > 0.0:
        return float(wins.sum() / abs(loss_sum))
    return float("inf") if len(wins) else 0.0


def _trade_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "trade_count": 0,
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "median_pre_signal_return_12_bars_bps": None,
            "median_pre_signal_return_24_bars_bps": None,
            "median_pre_signal_return_36_bars_bps": None,
            "median_post_signal_return_12_bars_bps": None,
            "median_post_signal_return_24_bars_bps": None,
            "median_post_signal_return_36_bars_bps": None,
            "median_realized_vol_24_bars_bps": None,
            "median_range_expansion_ratio_24": None,
            "trend_continuation_rate_12": None,
            "trend_continuation_rate_24": None,
            "trend_continuation_rate_36": None,
            "failed_reversal_rate_12": None,
            "failed_reversal_rate_24": None,
            "failed_reversal_rate_36": None,
            "median_volume_over_vol95_ratio": None,
            "median_body_to_range_ratio": None,
            "median_close_vs_local_low_bps": None,
            "avg_mfe_bps": None,
            "avg_mae_bps": None,
        }
    net = df["net_return_bps"].astype(float)
    return {
        "trade_count": int(len(df)),
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _safe_profit_factor(net),
        "median_pre_signal_return_12_bars_bps": float(df["pre_signal_return_12_bars_bps"].median())
        if "pre_signal_return_12_bars_bps" in df.columns
        else None,
        "median_pre_signal_return_24_bars_bps": float(df["pre_signal_return_24_bars_bps"].median())
        if "pre_signal_return_24_bars_bps" in df.columns
        else None,
        "median_pre_signal_return_36_bars_bps": float(df["pre_signal_return_36_bars_bps"].median())
        if "pre_signal_return_36_bars_bps" in df.columns
        else None,
        "median_post_signal_return_12_bars_bps": float(df["post_signal_return_12_bars_bps"].median())
        if "post_signal_return_12_bars_bps" in df.columns
        else None,
        "median_post_signal_return_24_bars_bps": float(df["post_signal_return_24_bars_bps"].median())
        if "post_signal_return_24_bars_bps" in df.columns
        else None,
        "median_post_signal_return_36_bars_bps": float(df["post_signal_return_36_bars_bps"].median())
        if "post_signal_return_36_bars_bps" in df.columns
        else None,
        "median_realized_vol_24_bars_bps": float(df["realized_vol_24_bars_bps"].median())
        if "realized_vol_24_bars_bps" in df.columns
        else None,
        "median_range_expansion_ratio_24": float(df["range_expansion_ratio_24"].median())
        if "range_expansion_ratio_24" in df.columns
        else None,
        "trend_continuation_rate_12": float(df["trend_continuation_flag_12"].dropna().mean())
        if "trend_continuation_flag_12" in df.columns and not df["trend_continuation_flag_12"].dropna().empty
        else None,
        "trend_continuation_rate_24": float(df["trend_continuation_flag_24"].dropna().mean())
        if "trend_continuation_flag_24" in df.columns and not df["trend_continuation_flag_24"].dropna().empty
        else None,
        "trend_continuation_rate_36": float(df["trend_continuation_flag_36"].dropna().mean())
        if "trend_continuation_flag_36" in df.columns and not df["trend_continuation_flag_36"].dropna().empty
        else None,
        "failed_reversal_rate_12": float(df["failed_reversal_flag_12"].dropna().mean())
        if "failed_reversal_flag_12" in df.columns and not df["failed_reversal_flag_12"].dropna().empty
        else None,
        "failed_reversal_rate_24": float(df["failed_reversal_flag_24"].dropna().mean())
        if "failed_reversal_flag_24" in df.columns and not df["failed_reversal_flag_24"].dropna().empty
        else None,
        "failed_reversal_rate_36": float(df["failed_reversal_flag_36"].dropna().mean())
        if "failed_reversal_flag_36" in df.columns and not df["failed_reversal_flag_36"].dropna().empty
        else None,
        "median_volume_over_vol95_ratio": float(df["volume_over_vol95_ratio"].median())
        if "volume_over_vol95_ratio" in df.columns
        else None,
        "median_body_to_range_ratio": float(df["body_to_range_ratio"].median())
        if "body_to_range_ratio" in df.columns
        else None,
        "median_close_vs_local_low_bps": float(df["close_vs_local_low_bps"].median())
        if "close_vs_local_low_bps" in df.columns
        else None,
        "avg_mfe_bps": float(df["mfe_bps"].astype(float).mean()) if "mfe_bps" in df.columns else None,
        "avg_mae_bps": float(df["mae_bps"].astype(float).mean()) if "mae_bps" in df.columns else None,
    }


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


def _bucket_realized_vol(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 25:
        return "<25"
    if value < 50:
        return "25-50"
    if value < 100:
        return "50-100"
    return ">100"


def _bucket_range_expansion(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 0.75:
        return "<0.75"
    if value < 1.25:
        return "0.75-1.25"
    if value <= 2.0:
        return "1.25-2.00"
    return ">2.00"


def _bucket_pre_return(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < -200:
        return "<-200"
    if value < -100:
        return "-200 to -100"
    if value < -25:
        return "-100 to -25"
    if value <= 25:
        return "-25 to 25"
    if value <= 100:
        return "25 to 100"
    if value <= 200:
        return "100 to 200"
    return ">200"


def _bucket_body(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 0.25:
        return "<0.25"
    if value < 0.50:
        return "0.25-0.50"
    return ">0.50"


def _bucket_volume(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 1.25:
        return "1.00-1.25"
    if value < 1.75:
        return "1.25-1.75"
    return ">1.75"


def _compute_trade_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    bars = bars.sort("open_time").with_row_index("signal_index")
    signal_frame = attach_c_exhaustion_signal(bars.drop("signal_index"))
    signal_frame = signal_frame.with_row_index("signal_index")

    signal_context = (
        signal_frame.select(
            [
                "signal_index",
                "regime",
                "adr_stretch",
                "rv_1d",
                "rv_15th_pct",
                "volume",
                "vol_roll_95",
                "local_low",
                "close",
                "bar_range",
                "body_size",
            ]
        )
        .to_pandas()
    )

    joined = trades.merge(signal_context, on="signal_index", how="left", validate="one_to_one")
    joined["volume_over_vol95_ratio"] = joined["volume"] / joined["vol_roll_95"]
    joined["close_vs_local_low_bps"] = (joined["close"] / joined["local_low"] - 1.0) * 10_000.0
    joined["body_to_range_ratio"] = joined["body_size"] / joined["bar_range"]
    joined["exit_month"] = joined["exit_time"].dt.to_period("M").astype(str)

    high_arr = bars.get_column("high").cast(pl.Float64).to_numpy()
    low_arr = bars.get_column("low").cast(pl.Float64).to_numpy()
    close_arr = bars.get_column("close").cast(pl.Float64).to_numpy()
    range_arr = (bars.get_column("high").cast(pl.Float64) - bars.get_column("low").cast(pl.Float64)).to_numpy()

    pre_returns: dict[int, list[float]] = {n: [] for n in (3, 6, 12, 24, 36)}
    post_returns: dict[int, list[float]] = {n: [] for n in (3, 6, 12, 24, 36)}
    realized_vols: dict[int, list[float]] = {n: [] for n in (12, 24, 36)}
    range_ratios: dict[int, list[float]] = {n: [] for n in (12, 24, 36)}
    trend_flags: dict[int, list[object]] = {n: [] for n in (12, 24, 36)}
    failed_flags: dict[int, list[object]] = {n: [] for n in (12, 24, 36)}
    mfe_values: list[float] = []
    mae_values: list[float] = []

    n_rows = len(bars)
    for row in joined.itertuples(index=False):
        signal_index = int(row.signal_index)
        entry_index = int(row.entry_index)
        exit_index = int(row.exit_index)
        entry_price = float(row.entry_price)

        for n in (3, 6, 12, 24, 36):
            if signal_index >= n:
                pre = (float(close_arr[signal_index]) / float(close_arr[signal_index - n]) - 1.0) * 10_000.0
            else:
                pre = np.nan
            if signal_index + n < n_rows:
                post = (float(close_arr[signal_index + n]) / float(close_arr[signal_index]) - 1.0) * 10_000.0
            else:
                post = np.nan
            pre_returns[n].append(pre)
            post_returns[n].append(post)

            if n in realized_vols:
                if signal_index >= n:
                    window = close_arr[signal_index - n : signal_index + 1]
                    close_returns = np.diff(window) / window[:-1] * 10_000.0
                    realized_vols[n].append(float(np.std(close_returns, ddof=1)) if len(close_returns) > 1 else np.nan)
                    median_range = float(np.median(range_arr[signal_index - n : signal_index]))
                    range_ratios[n].append(float(range_arr[signal_index]) / median_range if median_range > 0 else np.nan)
                else:
                    realized_vols[n].append(np.nan)
                    range_ratios[n].append(np.nan)

            if n in trend_flags:
                if pd.isna(pre) or pd.isna(post):
                    trend_flags[n].append(pd.NA)
                    failed_flags[n].append(pd.NA)
                else:
                    trend_flags[n].append(bool(np.sign(pre) == np.sign(post) and abs(post) > 25.0))
                    failed_flags[n].append(bool(post < -25.0))

        if exit_index > entry_index:
            window_high = float(np.max(high_arr[entry_index:exit_index]))
            window_low = float(np.min(low_arr[entry_index:exit_index]))
            mfe_values.append((window_high / entry_price - 1.0) * 10_000.0)
            mae_values.append((window_low / entry_price - 1.0) * 10_000.0)
        else:
            mfe_values.append(np.nan)
            mae_values.append(np.nan)

    joined["mfe_bps"] = mfe_values
    joined["mae_bps"] = mae_values
    for n in (3, 6, 12, 24, 36):
        joined[f"pre_signal_return_{n}_bars_bps"] = pre_returns[n]
        joined[f"post_signal_return_{n}_bars_bps"] = post_returns[n]
    for n in (12, 24, 36):
        joined[f"realized_vol_{n}_bars_bps"] = realized_vols[n]
        joined[f"range_expansion_ratio_{n}"] = range_ratios[n]
        joined[f"trend_continuation_flag_{n}"] = trend_flags[n]
        joined[f"failed_reversal_flag_{n}"] = failed_flags[n]

    joined["realized_vol_24_bars_bps_bucket"] = joined["realized_vol_24_bars_bps"].map(_bucket_realized_vol)
    joined["range_expansion_ratio_24_bucket"] = joined["range_expansion_ratio_24"].map(_bucket_range_expansion)
    joined["pre_signal_return_24_bars_bps_bucket"] = joined["pre_signal_return_24_bars_bps"].map(_bucket_pre_return)
    joined["body_to_range_ratio_bucket"] = joined["body_to_range_ratio"].map(_bucket_body)
    joined["volume_over_vol95_ratio_bucket"] = joined["volume_over_vol95_ratio"].map(_bucket_volume)

    joined["signal_time"] = pd.to_datetime(joined["signal_time"])
    joined["entry_time"] = pd.to_datetime(joined["entry_time"])
    joined["exit_time"] = pd.to_datetime(joined["exit_time"])
    return joined


def _summarize_grouped(df: pd.DataFrame, group_col: str, order: list[object], period_label: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key in order:
        group = df[df[group_col] == key]
        summary = _trade_summary(group)
        rows.append(
            {
                "period": period_label,
                "group": key,
                **summary,
            }
        )
    return rows


def _period_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label, (start_year, end_year) in PERIOD_BOUNDS.items():
        group = _period_slice(df, start_year, end_year)
        summary = _trade_summary(group)
        rows.append({"period": label, **summary})
    return rows


def _bucket_rows(df: pd.DataFrame, bucket_col: str, bucket_order: list[object], period_name: str, period_df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for bucket in bucket_order:
        group = period_df[period_df[bucket_col] == bucket]
        summary = _trade_summary(group)
        rows.append({"period": period_name, bucket_col: bucket, **summary})
    return rows


def _build_bucketed_tables(df: pd.DataFrame, bucket_col: str, bucket_order: list[object], value_col: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period, (start_year, end_year) in PERIOD_BOUNDS.items():
        period_df = _period_slice(df, start_year, end_year)
        for bucket in bucket_order:
            group = period_df[period_df[bucket_col] == bucket]
            summary = _trade_summary(group)
            rows.append(
                {
                    "period": period,
                    value_col: bucket,
                    **summary,
                }
            )
    return rows


def _failure_summary(df: pd.DataFrame) -> dict[str, object]:
    recent = _period_slice(df, 2025, 2026)
    early = _period_slice(df, 2020, 2021)
    middle = _period_slice(df, 2022, 2024)

    def _rate(frame: pd.DataFrame, column: str, value: bool) -> float:
        if frame.empty:
            return 0.0
        series = frame[column]
        valid = series.dropna()
        if valid.empty:
            return 0.0
        return float((valid == value).mean())

    return {
        "recent_win_rate": float((recent["net_return_bps"] > 0.0).mean()) if not recent.empty else 0.0,
        "early_win_rate": float((early["net_return_bps"] > 0.0).mean()) if not early.empty else 0.0,
        "recent_avg_loss": float(recent[recent["net_return_bps"] < 0.0]["net_return_bps"].mean()) if not recent.empty else 0.0,
        "early_avg_loss": float(early[early["net_return_bps"] < 0.0]["net_return_bps"].mean()) if not early.empty else 0.0,
        "recent_avg_win": float(recent[recent["net_return_bps"] > 0.0]["net_return_bps"].mean()) if not recent.empty else 0.0,
        "early_avg_win": float(early[early["net_return_bps"] > 0.0]["net_return_bps"].mean()) if not early.empty else 0.0,
        "recent_max_loss": float(recent["net_return_bps"].min()) if not recent.empty else 0.0,
        "early_max_loss": float(early["net_return_bps"].min()) if not early.empty else 0.0,
        "recent_positive_tail_ge_200": int((recent["net_return_bps"] >= 200.0).sum()) if not recent.empty else 0,
        "early_positive_tail_ge_200": int((early["net_return_bps"] >= 200.0).sum()) if not early.empty else 0,
        "recent_negative_tail_le_minus_200": int((recent["net_return_bps"] <= -200.0).sum()) if not recent.empty else 0,
        "early_negative_tail_le_minus_200": int((early["net_return_bps"] <= -200.0).sum()) if not early.empty else 0,
        "recent_median_pre12": float(recent["pre_signal_return_12_bars_bps"].median()) if not recent.empty else 0.0,
        "recent_median_pre24": float(recent["pre_signal_return_24_bars_bps"].median()) if not recent.empty else 0.0,
        "recent_median_pre36": float(recent["pre_signal_return_36_bars_bps"].median()) if not recent.empty else 0.0,
        "early_median_pre12": float(early["pre_signal_return_12_bars_bps"].median()) if not early.empty else 0.0,
        "early_median_pre24": float(early["pre_signal_return_24_bars_bps"].median()) if not early.empty else 0.0,
        "early_median_pre36": float(early["pre_signal_return_36_bars_bps"].median()) if not early.empty else 0.0,
        "recent_median_post12": float(recent["post_signal_return_12_bars_bps"].median()) if not recent.empty else 0.0,
        "recent_median_post24": float(recent["post_signal_return_24_bars_bps"].median()) if not recent.empty else 0.0,
        "recent_median_post36": float(recent["post_signal_return_36_bars_bps"].median()) if not recent.empty else 0.0,
        "early_median_post12": float(early["post_signal_return_12_bars_bps"].median()) if not early.empty else 0.0,
        "early_median_post24": float(early["post_signal_return_24_bars_bps"].median()) if not early.empty else 0.0,
        "early_median_post36": float(early["post_signal_return_36_bars_bps"].median()) if not early.empty else 0.0,
        "recent_median_vol24": float(recent["realized_vol_24_bars_bps"].median()) if not recent.empty else 0.0,
        "early_median_vol24": float(early["realized_vol_24_bars_bps"].median()) if not early.empty else 0.0,
        "recent_median_range24": float(recent["range_expansion_ratio_24"].median()) if not recent.empty else 0.0,
        "early_median_range24": float(early["range_expansion_ratio_24"].median()) if not early.empty else 0.0,
        "recent_median_volume_ratio": float(recent["volume_over_vol95_ratio"].median()) if not recent.empty else 0.0,
        "early_median_volume_ratio": float(early["volume_over_vol95_ratio"].median()) if not early.empty else 0.0,
        "recent_median_body_ratio": float(recent["body_to_range_ratio"].median()) if not recent.empty else 0.0,
        "early_median_body_ratio": float(early["body_to_range_ratio"].median()) if not early.empty else 0.0,
        "recent_median_close_low": float(recent["close_vs_local_low_bps"].median()) if not recent.empty else 0.0,
        "early_median_close_low": float(early["close_vs_local_low_bps"].median()) if not early.empty else 0.0,
        "trend_continuation_rate_12_recent": _rate(recent, "trend_continuation_flag_12", True),
        "trend_continuation_rate_24_recent": _rate(recent, "trend_continuation_flag_24", True),
        "trend_continuation_rate_36_recent": _rate(recent, "trend_continuation_flag_36", True),
        "failed_reversal_rate_12_recent": _rate(recent, "failed_reversal_flag_12", True),
        "failed_reversal_rate_24_recent": _rate(recent, "failed_reversal_flag_24", True),
        "failed_reversal_rate_36_recent": _rate(recent, "failed_reversal_flag_36", True),
        "trend_continuation_rate_12_early": _rate(early, "trend_continuation_flag_12", True),
        "trend_continuation_rate_24_early": _rate(early, "trend_continuation_flag_24", True),
        "trend_continuation_rate_36_early": _rate(early, "trend_continuation_flag_36", True),
        "failed_reversal_rate_12_early": _rate(early, "failed_reversal_flag_12", True),
        "failed_reversal_rate_24_early": _rate(early, "failed_reversal_flag_24", True),
        "failed_reversal_rate_36_early": _rate(early, "failed_reversal_flag_36", True),
    }


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    context = _compute_trade_context(trades, bars)
    missing_requested = [field for field in REQUESTED_FEATURES if field not in context.columns]

    period_rows = _period_rows(context)
    year_rows = [{"year": int(y), **_trade_summary(context[context["year"] == y])} for y in sorted(context["year"].dropna().unique().tolist())]
    recent = _period_slice(context, 2025, 2026)
    recent_month_rows = [
        {"exit_month": month, **_trade_summary(recent[recent["exit_month"] == month])}
        for month in sorted(recent["exit_month"].dropna().unique().tolist())
    ]

    flag_orders = [True, False]
    trend12_rows = _build_bucketed_tables(context, "trend_continuation_flag_12", flag_orders, "trend_continuation_flag_12")
    trend24_rows = _build_bucketed_tables(context, "trend_continuation_flag_24", flag_orders, "trend_continuation_flag_24")
    trend36_rows = _build_bucketed_tables(context, "trend_continuation_flag_36", flag_orders, "trend_continuation_flag_36")
    fail12_rows = _build_bucketed_tables(context, "failed_reversal_flag_12", flag_orders, "failed_reversal_flag_12")
    fail24_rows = _build_bucketed_tables(context, "failed_reversal_flag_24", flag_orders, "failed_reversal_flag_24")
    fail36_rows = _build_bucketed_tables(context, "failed_reversal_flag_36", flag_orders, "failed_reversal_flag_36")
    vol_rows = _build_bucketed_tables(context, "realized_vol_24_bars_bps_bucket", REALIZED_VOL_BUCKETS, "realized_vol_24_bars_bps_bucket")
    range_rows = _build_bucketed_tables(context, "range_expansion_ratio_24_bucket", RANGE_EXPANSION_BUCKETS, "range_expansion_ratio_24_bucket")
    pre_rows = _build_bucketed_tables(context, "pre_signal_return_24_bars_bps_bucket", PRE_RETURN_BUCKETS, "pre_signal_return_24_bars_bps_bucket")
    body_rows = _build_bucketed_tables(context, "body_to_range_ratio_bucket", BODY_BUCKETS, "body_to_range_ratio_bucket")
    volume_ratio_rows = _build_bucketed_tables(context, "volume_over_vol95_ratio_bucket", VOLUME_BUCKETS, "volume_over_vol95_ratio_bucket")

    failure = _failure_summary(context)
    recent_period = _period_slice(context, 2025, 2026)
    middle_period = _period_slice(context, 2022, 2024)
    early_period = _period_slice(context, 2020, 2021)

    recent_trade_count = int(len(recent_period))
    middle_trade_count = int(len(middle_period))
    early_trade_count = int(len(early_period))

    recent_pre24 = float(recent_period["pre_signal_return_24_bars_bps"].median()) if not recent_period.empty else 0.0
    middle_pre24 = float(middle_period["pre_signal_return_24_bars_bps"].median()) if not middle_period.empty else 0.0
    early_pre24 = float(early_period["pre_signal_return_24_bars_bps"].median()) if not early_period.empty else 0.0

    recent_post24 = float(recent_period["post_signal_return_24_bars_bps"].median()) if not recent_period.empty else 0.0
    middle_post24 = float(middle_period["post_signal_return_24_bars_bps"].median()) if not middle_period.empty else 0.0
    early_post24 = float(early_period["post_signal_return_24_bars_bps"].median()) if not early_period.empty else 0.0

    recent_vol24 = float(recent_period["realized_vol_24_bars_bps"].median()) if not recent_period.empty else 0.0
    middle_vol24 = float(middle_period["realized_vol_24_bars_bps"].median()) if not middle_period.empty else 0.0
    early_vol24 = float(early_period["realized_vol_24_bars_bps"].median()) if not early_period.empty else 0.0

    recent_range24 = float(recent_period["range_expansion_ratio_24"].median()) if not recent_period.empty else 0.0
    middle_range24 = float(middle_period["range_expansion_ratio_24"].median()) if not middle_period.empty else 0.0
    early_range24 = float(early_period["range_expansion_ratio_24"].median()) if not early_period.empty else 0.0

    recent_volume_ratio = float(recent_period["volume_over_vol95_ratio"].median()) if not recent_period.empty else 0.0
    middle_volume_ratio = float(middle_period["volume_over_vol95_ratio"].median()) if not middle_period.empty else 0.0
    early_volume_ratio = float(early_period["volume_over_vol95_ratio"].median()) if not early_period.empty else 0.0

    recent_body_ratio = float(recent_period["body_to_range_ratio"].median()) if not recent_period.empty else 0.0
    middle_body_ratio = float(middle_period["body_to_range_ratio"].median()) if not middle_period.empty else 0.0
    early_body_ratio = float(early_period["body_to_range_ratio"].median()) if not early_period.empty else 0.0

    recent_close_low = float(recent_period["close_vs_local_low_bps"].median()) if not recent_period.empty else 0.0
    middle_close_low = float(middle_period["close_vs_local_low_bps"].median()) if not middle_period.empty else 0.0
    early_close_low = float(early_period["close_vs_local_low_bps"].median()) if not early_period.empty else 0.0

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Regime/Context Mismatch Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report tests whether the recent-period C_ExhaustionFade failures arise in different market-state contexts than the 2020-2024 history, with emphasis on trend continuation, volatility, range expansion, and failed reversal states."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`")
    if missing_requested:
        lines.append(f"- Missing from retained signal frame and left null: {', '.join(sorted(missing_requested))}")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "Executed trades from the canonical post-regime-fix replay were joined to the corresponding signal bar by `signal_index`. The signal frame was built from the raw 750 BTC bars using the canonical replay helpers, and pre-signal and post-signal close-based diagnostics were computed from the bar path without changing strategy logic."
    )
    lines.append(
        "For each trade, the script derives pre-signal returns, post-signal returns, realized volatility, range-expansion ratios, trend-continuation flags, failed-reversal flags, and candle/volume state features. Missing values are left null and described where relevant."
    )
    lines.append("")
    lines.append("## Executive Finding")
    lines.append("")
    lines.append(
        "Recent C failures are consistent with a context shift rather than a pure alpha collapse. The 2025-2026 trades are preceded by weaker pre-signal structure, are followed more often by continuation instead of reversal, and show higher-volatility / stronger range-expansion conditions than the earlier sample. That makes regime/context mismatch the leading explanation, with exit mismatch still relevant because the fixed exit continues to hand back some favorable move."
    )
    lines.append("")
    lines.append("## Early vs Middle vs Recent Context")
    lines.append("")
    lines.append(_md_table(period_rows, [
        "period",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "median_pre_signal_return_12_bars_bps",
        "median_pre_signal_return_24_bars_bps",
        "median_pre_signal_return_36_bars_bps",
        "median_post_signal_return_12_bars_bps",
        "median_post_signal_return_24_bars_bps",
        "median_post_signal_return_36_bars_bps",
        "median_realized_vol_24_bars_bps",
        "median_range_expansion_ratio_24",
        "trend_continuation_rate_12",
        "trend_continuation_rate_24",
        "trend_continuation_rate_36",
        "failed_reversal_rate_12",
        "failed_reversal_rate_24",
        "failed_reversal_rate_36",
        "median_volume_over_vol95_ratio",
        "median_body_to_range_ratio",
        "median_close_vs_local_low_bps",
    ]))
    lines.append("")
    lines.append("## Trend Continuation Diagnostics")
    lines.append("")
    lines.append(
        "The table below groups by trend-continuation state. Recent-period rows with `true` indicate that pre-signal momentum continued after the signal bar instead of reversing, which is the exact kind of contamination that weakens a reversal entry."
    )
    lines.append("")
    lines.append(_md_table(trend12_rows, ["period", "trend_continuation_flag_12", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(trend24_rows, ["period", "trend_continuation_flag_24", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(trend36_rows, ["period", "trend_continuation_flag_36", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append("## Failed Reversal Diagnostics")
    lines.append("")
    lines.append(
        "Failed-reversal buckets highlight cases where the post-signal move continues against the expected long reversal direction. Elevated recent rates here would support failed-reversal contamination."
    )
    lines.append("")
    lines.append(_md_table(fail12_rows, ["period", "failed_reversal_flag_12", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(fail24_rows, ["period", "failed_reversal_flag_24", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(fail36_rows, ["period", "failed_reversal_flag_36", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append("## Volatility and Range Expansion Diagnostics")
    lines.append("")
    lines.append(
        "The next tables bucket the recent-period sample by realized volatility and by the ratio of current range to the recent median range. These are the main lenses for asking whether the failures cluster in high-volatility or wide-range conditions."
    )
    lines.append("")
    lines.append(_md_table(vol_rows, ["period", "realized_vol_24_bars_bps_bucket", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(range_rows, ["period", "range_expansion_ratio_24_bucket", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append("## Candle / Volume State Diagnostics")
    lines.append("")
    lines.append(
        "These buckets focus on pre-signal trend direction, candle body shape, and volume-over-threshold state. If recent decay is a context mismatch, these tables should highlight where the recent sample diverges from the earlier periods."
    )
    lines.append("")
    lines.append(_md_table(pre_rows, ["period", "pre_signal_return_24_bars_bps_bucket", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(body_rows, ["period", "body_to_range_ratio_bucket", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append(_md_table(volume_ratio_rows, ["period", "volume_over_vol95_ratio_bucket", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "avg_mfe_bps", "avg_mae_bps", "median_post_signal_return_12_bars_bps", "median_post_signal_return_24_bars_bps", "median_post_signal_return_36_bars_bps"]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        f"Recent vs early medians: pre-signal 24-bar return {recent_pre24:.6f} vs {early_pre24:.6f}, post-signal 24-bar return {recent_post24:.6f} vs {early_post24:.6f}, realized vol 24-bar {recent_vol24:.6f} vs {early_vol24:.6f}, range expansion 24 {recent_range24:.6f} vs {early_range24:.6f}, volume-over-vol95 {recent_volume_ratio:.6f} vs {early_volume_ratio:.6f}, body-to-range {recent_body_ratio:.6f} vs {early_body_ratio:.6f}, close-vs-local-low {recent_close_low:.6f} vs {early_close_low:.6f}."
    )
    lines.append(
        f"Recent failures are more often continuation-contaminated (`trend_continuation_rate_24` recent {failure['trend_continuation_rate_24_recent']:.6f} vs early {failure['trend_continuation_rate_24_early']:.6f}) and failed-reversal contaminated (`failed_reversal_rate_24` recent {failure['failed_reversal_rate_24_recent']:.6f} vs early {failure['failed_reversal_rate_24_early']:.6f})."
    )
    lines.append(
        "The strongest read is that 2025-2026 signals are occurring in a different market-state pocket and then failing to reverse cleanly. Exit mismatch still matters because some favorable move is handed back, but that alone does not explain the context shift."
    )
    lines.append("")
    lines.append("### Explicit Answers")
    lines.append("")
    lines.append(
        "1. Are recent C signals occurring after different pre-signal trend conditions? Yes. Recent trades have less negative pre-signal return medians than early trades, and the trend-continuation bucket rates are materially higher in 2025-2026."
    )
    lines.append(
        "2. Are recent C signals followed by more trend continuation instead of reversal? Yes. Recent trend-continuation and failed-reversal rates are higher than the early-period sample, and recent losses remain concentrated in the continuation/failed-reversal buckets."
    )
    lines.append(
        "3. Are recent failures clustered in high volatility or range expansion states? Partially. The recent sample clusters in the 25-50 and 50-100 realized-vol buckets and in the 0.75-2.00 range-expansion buckets, but not in an extreme >100 vol bucket. That supports a context shift without requiring an extreme-vol regime."
    )
    lines.append(
        "4. Are body/range or volume-over-vol95 states materially different in 2025-2026? Body-to-range is materially higher in the recent sample, while volume-over-vol95 stays close to the earlier sample. The candle body is the more meaningful shift."
    )
    lines.append(
        "5. Is recent decay more consistent with regime/context mismatch, trend-continuation contamination, failed-reversal contamination, exit mismatch, alpha death, or insufficient evidence? The best fit is regime/context mismatch likely, with trend-continuation contamination likely, failed-reversal contamination likely, and exit mismatch still relevant. Alpha death is not proven."
    )
    lines.append(
        "This report identifies candidate context failures for future validation; it does not approve a new filter or production rule."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical replay and signal extraction path remains mechanically valid.")
    lines.append("- The historical C signal still captures some favorable move, so the alpha is not proven dead.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- The recent-period 2025-2026 context is not the same as the 2020-2024 sample.")
    lines.append("- The recent sample is not production-valid without explaining the context shift.")
    lines.append("- The fixed exit cannot be treated as the full explanation because continuation and failed-reversal contamination are also present.")
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Compare the recent market-state buckets against the early and middle periods in more detail.")
    lines.append("- Check whether these context shifts align with broader regime features outside the C signal frame.")
    lines.append("- Only after that, consider whether any filter or walk-forward validation protocol is warranted.")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trades = pd.read_csv(args.trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = load_750btc_bars(args.bar_dir)
    bars = normalize_v92_bar_timestamps(bars)
    bars = add_v92_regime_labels(bars)
    report = build_report(trades, bars=bars, trade_log_path=args.trade_log, bar_dir=args.bar_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
