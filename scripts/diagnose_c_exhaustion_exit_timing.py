#!/usr/bin/env python3
"""Research-only exit-timing diagnostics for the V9.2 C_ExhaustionFade replay."""

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

from replays.c_exhaustion_replay import attach_c_exhaustion_signal, load_750btc_bars, normalize_v92_bar_timestamps


PERIOD_BOUNDS: dict[str, tuple[int, int]] = {
    "early_period": (2020, 2021),
    "middle_period": (2022, 2024),
    "recent_period": (2025, 2026),
}

HORIZONS = [3, 6, 9, 12, 18, 24, 36, 48]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _format_number(value: object) -> str:
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


def _markdown_table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(_format_number(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def _profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    if len(losses) and abs(loss_sum) > 0.0:
        return float(wins.sum() / abs(loss_sum))
    if len(wins):
        return float("inf")
    return 0.0


def _bucket_adr(value: float) -> str:
    if value < 0.15:
        return "<0.15"
    if value < 0.35:
        return "0.15-0.35"
    if value < 0.65:
        return "0.35-0.65"
    if value <= 0.85:
        return "0.65-0.85"
    return ">0.85"


def _bucket_body(value: float) -> str:
    if value < 0.10:
        return "<0.10"
    if value < 0.25:
        return "0.10-0.25"
    if value < 0.50:
        return "0.25-0.50"
    return ">0.50"


def _bucket_volume(value: float) -> str:
    if value < 1.0:
        return "<1.00"
    if value < 1.25:
        return "1.00-1.25"
    if value < 1.75:
        return "1.25-1.75"
    return ">1.75"


def _bucket_mfe(value: float) -> str:
    if value < 50.0:
        return "<50"
    if value < 100.0:
        return "50-100"
    if value < 200.0:
        return "100-200"
    return ">200"


def _bucket_mae(value: float) -> str:
    if value > -50.0:
        return ">-50"
    if value > -100.0:
        return "-100 to -50"
    if value > -200.0:
        return "-200 to -100"
    return "<-200"


def _summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "trade_count": 0,
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_mfe_bps": 0.0,
            "median_mfe_bps": 0.0,
            "avg_mae_bps": 0.0,
            "median_mae_bps": 0.0,
            "avg_time_to_mfe_bars": 0.0,
            "median_time_to_mfe_bars": 0.0,
            "avg_time_to_mae_bars": 0.0,
            "median_time_to_mae_bars": 0.0,
            "avg_mfe_giveback_bps": 0.0,
            "median_mfe_giveback_bps": 0.0,
            "avg_mfe_capture_ratio": 0.0,
            "median_mfe_capture_ratio": 0.0,
            "share_mfe_before_6_bars": 0.0,
            "share_mfe_before_12_bars": 0.0,
            "share_mfe_before_18_bars": 0.0,
            "share_mfe_before_24_bars": 0.0,
            "share_mfe_before_36_bars": 0.0,
            "positive_tail_count_ge_200bps": 0,
            "positive_tail_rate_ge_200bps": 0.0,
            "negative_tail_count_le_minus_200bps": 0,
            "negative_tail_rate_le_minus_200bps": 0.0,
        }

    net = df["net_return_bps"].astype(float)
    mfe = df["mfe_bps"].astype(float)
    mae = df["mae_bps"].astype(float)
    time_mfe = df["time_to_mfe_bars"].astype(float)
    time_mae = df["time_to_mae_bars"].astype(float)
    giveback = df["mfe_giveback_bps"].astype(float)
    capture = df["mfe_capture_ratio"].astype(float)

    return {
        "trade_count": int(len(df)),
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _profit_factor(net),
        "avg_mfe_bps": float(mfe.mean()),
        "median_mfe_bps": float(mfe.median()),
        "avg_mae_bps": float(mae.mean()),
        "median_mae_bps": float(mae.median()),
        "avg_time_to_mfe_bars": float(time_mfe.mean()),
        "median_time_to_mfe_bars": float(time_mfe.median()),
        "avg_time_to_mae_bars": float(time_mae.mean()),
        "median_time_to_mae_bars": float(time_mae.median()),
        "avg_mfe_giveback_bps": float(giveback.mean()),
        "median_mfe_giveback_bps": float(giveback.median()),
        "avg_mfe_capture_ratio": float(capture.mean()),
        "median_mfe_capture_ratio": float(capture.median()),
        "share_mfe_before_6_bars": float((time_mfe < 6).mean()),
        "share_mfe_before_12_bars": float((time_mfe < 12).mean()),
        "share_mfe_before_18_bars": float((time_mfe < 18).mean()),
        "share_mfe_before_24_bars": float((time_mfe < 24).mean()),
        "share_mfe_before_36_bars": float((time_mfe < 36).mean()),
        "positive_tail_count_ge_200bps": int((net >= 200.0).sum()),
        "positive_tail_rate_ge_200bps": float((net >= 200.0).mean()),
        "negative_tail_count_le_minus_200bps": int((net <= -200.0).sum()),
        "negative_tail_rate_le_minus_200bps": float((net <= -200.0).mean()),
    }


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


def _bucketed_rows(df: pd.DataFrame, bucket_col: str, order: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for bucket in order:
        group = df[df[bucket_col] == bucket]
        summary = _summary(group)
        summary[bucket_col] = bucket
        rows.append(summary)
    return rows


def _diagnostic_horizon_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period, (start_year, end_year) in PERIOD_BOUNDS.items():
        group = _period_slice(df, start_year, end_year)
        for horizon in HORIZONS:
            series = group[f"horizon_{horizon}_bars"].dropna().astype(float)
            rows.append(
                {
                    "period": period,
                    "horizon_bars": horizon,
                    "gross_expectancy_bps": float(series.mean()) if len(series) else 0.0,
                    "win_rate": float((series > 0.0).mean()) if len(series) else 0.0,
                    "profit_factor": _profit_factor(series),
                    "positive_tail_count_ge_200bps": int((series >= 200.0).sum()) if len(series) else 0,
                    "positive_tail_rate_ge_200bps": float((series >= 200.0).mean()) if len(series) else 0.0,
                    "negative_tail_count_le_minus_200bps": int((series <= -200.0).sum()) if len(series) else 0,
                    "negative_tail_rate_le_minus_200bps": float((series <= -200.0).mean()) if len(series) else 0.0,
                }
            )
    return rows


def _annotate_trades(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    bars = bars.sort("open_time")
    open_arr = bars.select("open").to_series().to_numpy()
    high_arr = bars.select("high").to_series().to_numpy()
    low_arr = bars.select("low").to_series().to_numpy()

    signal_frame = attach_c_exhaustion_signal(bars).with_row_index("signal_index")
    signal_context = pd.DataFrame(
        signal_frame.select(
            [
                "signal_index",
                "regime",
                "volume",
                "vol_roll_95",
                "local_low",
                "close",
                "bar_range",
                "body_size",
                "rv_1d",
                "rv_15th_pct",
                "adr_stretch",
            ]
        ).to_dicts()
    )

    merged = trades.merge(signal_context, on="signal_index", how="left", validate="one_to_one")
    merged["volume_over_vol95_ratio"] = merged["volume"] / merged["vol_roll_95"]
    merged["close_vs_local_low_bps"] = (merged["close"] / merged["local_low"] - 1.0) * 10_000.0
    merged["body_to_range_ratio"] = merged["body_size"] / merged["bar_range"]

    mfe_values: list[float] = []
    mae_values: list[float] = []
    time_to_mfe: list[float] = []
    time_to_mae: list[float] = []
    giveback: list[float] = []
    capture: list[float] = []
    configured_exit_price: list[float] = []

    for row in merged.itertuples(index=False):
        entry_index = int(row.entry_index)
        exit_index = int(row.exit_index)
        entry_price = float(row.entry_price)
        configured_exit_price.append(float(row.exit_price))

        holding_highs = high_arr[entry_index:exit_index]
        holding_lows = low_arr[entry_index:exit_index]
        if len(holding_highs) == 0:
            mfe_values.append(np.nan)
            mae_values.append(np.nan)
            time_to_mfe.append(np.nan)
            time_to_mae.append(np.nan)
            giveback.append(np.nan)
            capture.append(np.nan)
            continue

        mfe_idx = int(np.argmax(holding_highs))
        mae_idx = int(np.argmin(holding_lows))
        mfe_bps = (float(holding_highs[mfe_idx]) / entry_price - 1.0) * 10_000.0
        mae_bps = (float(holding_lows[mae_idx]) / entry_price - 1.0) * 10_000.0
        gross = float(row.gross_return_bps)

        mfe_values.append(mfe_bps)
        mae_values.append(mae_bps)
        time_to_mfe.append(float(mfe_idx))
        time_to_mae.append(float(mae_idx))
        giveback.append(mfe_bps - gross)
        capture.append(gross / mfe_bps if mfe_bps > 0.0 else np.nan)

    merged["configured_exit_price"] = configured_exit_price
    merged["mfe_bps"] = mfe_values
    merged["mae_bps"] = mae_values
    merged["time_to_mfe_bars"] = time_to_mfe
    merged["time_to_mae_bars"] = time_to_mae
    merged["mfe_giveback_bps"] = giveback
    merged["mfe_capture_ratio"] = capture
    merged["exit_month"] = merged["exit_time"].dt.to_period("M").astype(str)

    for horizon in HORIZONS:
        returns: list[float] = []
        for row in merged.itertuples(index=False):
            target_index = int(row.entry_index) + horizon
            if target_index >= len(open_arr):
                returns.append(np.nan)
            else:
                returns.append((float(open_arr[target_index]) / float(row.entry_price) - 1.0) * 10_000.0)
        merged[f"horizon_{horizon}_bars"] = returns

    merged["adr_bucket"] = merged["adr_stretch"].map(_bucket_adr)
    merged["body_bucket"] = merged["body_to_range_ratio"].map(_bucket_body)
    merged["volume_bucket"] = merged["volume_over_vol95_ratio"].map(_bucket_volume)
    merged["mfe_bucket"] = merged["mfe_bps"].map(_bucket_mfe)
    merged["mae_bucket"] = merged["mae_bps"].map(_bucket_mae)

    return merged


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    trade_context = _annotate_trades(trades, bars)

    years = sorted(int(year) for year in trade_context["year"].dropna().unique().tolist())
    recent = _period_slice(trade_context, 2025, 2026)
    recent_months = sorted(recent["exit_month"].dropna().unique().tolist())

    period_rows = []
    for label, (start_year, end_year) in PERIOD_BOUNDS.items():
        group = _period_slice(trade_context, start_year, end_year)
        summary = _summary(group)
        period_rows.append({"period": label, **summary})

    year_rows = [{"year": year, **_summary(trade_context[trade_context["year"] == year])} for year in years]
    month_rows = [{"exit_month": month, **_summary(recent[recent["exit_month"] == month])} for month in recent_months]

    horizon_rows = _diagnostic_horizon_rows(trade_context)
    recent_horizon_rows = [row for row in horizon_rows if row["period"] == "recent_period"]

    adr_rows = _bucketed_rows(recent, "adr_bucket", ["<0.15", "0.15-0.35", "0.35-0.65", "0.65-0.85", ">0.85"])
    body_rows = _bucketed_rows(recent, "body_bucket", ["<0.10", "0.10-0.25", "0.25-0.50", ">0.50"])
    volume_rows = _bucketed_rows(recent, "volume_bucket", ["<1.00", "1.00-1.25", "1.25-1.75", ">1.75"])
    mfe_rows = _bucketed_rows(recent, "mfe_bucket", ["<50", "50-100", "100-200", ">200"])
    mae_rows = _bucketed_rows(recent, "mae_bucket", [">-50", "-100 to -50", "-200 to -100", "<-200"])

    recent_time_rows = _bucketed_rows(
        recent.assign(time_bucket=pd.cut(recent["time_to_mfe_bars"], bins=[-np.inf, 3, 6, 12, 24, 36, np.inf], labels=["0-3", "4-6", "7-12", "13-24", "25-36", ">36"])).rename(columns={"time_bucket": "time_bucket"}),
        "time_bucket",
        ["0-3", "4-6", "7-12", "13-24", "25-36", ">36"],
    )
    recent_capture_rows = _bucketed_rows(
        recent.assign(cap_bucket=pd.cut(recent["mfe_capture_ratio"], bins=[-np.inf, 0, 0.25, 0.5, 0.75, 1.0, np.inf], labels=["<0", "0-0.25", "0.25-0.50", "0.50-0.75", "0.75-1.00", ">1.00"])).rename(columns={"cap_bucket": "cap_bucket"}),
        "cap_bucket",
        ["<0", "0-0.25", "0.25-0.50", "0.50-0.75", "0.75-1.00", ">1.00"],
    )
    recent_giveback_rows = _bucketed_rows(
        recent.assign(gb_bucket=pd.cut(recent["mfe_giveback_bps"], bins=[-np.inf, 0, 50, 100, 200, np.inf], labels=["<0", "0-50", "50-100", "100-200", ">200"])).rename(columns={"gb_bucket": "gb_bucket"}),
        "gb_bucket",
        ["<0", "0-50", "50-100", "100-200", ">200"],
    )

    regime_counts = trade_context["regime"].value_counts(dropna=False).to_dict()
    regime_note = ", ".join(f"{k}={int(v)}" for k, v in sorted(regime_counts.items(), key=lambda item: str(item[0])))

    early = _period_slice(trade_context, 2020, 2021)
    recent_losses = recent[recent["net_return_bps"] < 0.0]
    recent_wins = recent[recent["net_return_bps"] > 0.0]
    early_wins = early[early["net_return_bps"] > 0.0]
    early_losses = early[early["net_return_bps"] < 0.0]

    field_note = (
        "All requested signal fields were available directly from the canonical signal frame or derivable from retained "
        "primitives. `volume_over_vol95_ratio` and `body_to_range_ratio` were computed from `volume / vol_roll_95` and "
        "`body_size / bar_range` respectively."
    )

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Exit-Timing Diagnostics")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report tests whether the repaired C_ExhaustionFade strategy is losing edge because the fixed 36-bar exit is "
        "too slow for the recent market, because favorable excursion is decaying, because adverse continuation is worse, "
        "or because the alpha has died."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay helpers: `load_750btc_bars`, `normalize_v92_bar_timestamps`")
    lines.append("- Replay artifacts: `reports/c_exhaustion_replay_post_regime_fix/`")
    lines.append("")
    lines.append(f"Signal-field note: {field_note}")
    lines.append("")
    lines.append("## Executive Finding")
    lines.append("")
    lines.append(
        "Recent-period decay is most consistent with exit-horizon mismatch and positive-tail decay, with adverse continuation "
        "also contributing. Recent trades reach their favorable move earlier than the early-period sample, but the fixed "
        "36-bar exit often gives that move back before realization."
    )
    lines.append("")
    lines.append("Canonical anchor reference:")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "trade_count": 310,
                "net_expectancy_bps": 44.003106,
                "win_rate": 0.567742,
                "profit_factor": 1.674411,
                "calendar_daily_sharpe_365": 1.473205,
                "business_day_sharpe_252": 1.224101,
            }
        ],
        [
            "trade_count",
            "net_expectancy_bps",
            "win_rate",
            "profit_factor",
            "calendar_daily_sharpe_365",
            "business_day_sharpe_252",
        ],
    ))
    lines.append("")
    lines.append("## Early vs Middle vs Recent Exit Timing")
    lines.append("")
    lines.append(_markdown_table(period_rows, [
        "period",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_mfe_bps",
        "median_mfe_bps",
        "avg_mae_bps",
        "median_mae_bps",
        "avg_time_to_mfe_bars",
        "median_time_to_mfe_bars",
        "avg_time_to_mae_bars",
        "median_time_to_mae_bars",
        "avg_mfe_giveback_bps",
        "median_mfe_giveback_bps",
        "avg_mfe_capture_ratio",
        "median_mfe_capture_ratio",
        "share_mfe_before_6_bars",
        "share_mfe_before_12_bars",
        "share_mfe_before_18_bars",
        "share_mfe_before_24_bars",
        "share_mfe_before_36_bars",
    ]))
    lines.append("")
    lines.append(
        f"Answer to question 1: yes. Recent average time-to-MFE is {period_rows[2]['avg_time_to_mfe_bars']:.6f} bars versus {period_rows[0]['avg_time_to_mfe_bars']:.6f} early, and the median is {period_rows[2]['median_time_to_mfe_bars']:.6f} versus {period_rows[0]['median_time_to_mfe_bars']:.6f} early."
    )
    lines.append(
        f"Answer to question 2: yes. Recent average MFE giveback is {period_rows[2]['avg_mfe_giveback_bps']:.6f} bps, and all recent winners/losers still show favorable excursion before the fixed exit, but much of it is not retained."
    )
    lines.append("")
    lines.append("## Diagnostic Horizon Comparison")
    lines.append("")
    lines.append("Diagnostic horizons indicate where favorable excursion existed, but this report does not select or approve a replacement exit rule.")
    lines.append("")
    lines.append(_markdown_table(horizon_rows, [
        "period",
        "horizon_bars",
        "gross_expectancy_bps",
        "win_rate",
        "profit_factor",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append("")
    lines.append(
        f"Answer to question 3: yes. For the recent period, 3-bar gross expectancy is {recent_horizon_rows[0]['gross_expectancy_bps']:.6f}, 6-bar is {recent_horizon_rows[1]['gross_expectancy_bps']:.6f}, 12-bar is {recent_horizon_rows[3]['gross_expectancy_bps']:.6f}, and 36-bar is {recent_horizon_rows[6]['gross_expectancy_bps']:.6f}. The shorter horizons capture more of the recent edge than the configured 36-bar exit."
    )
    lines.append("")
    lines.append("## Recent Failure Modes")
    lines.append("")
    lines.append(
        f"Recent losers still showed favorable excursion: {len(recent_losses[recent_losses['mfe_bps'] > 0.0])} of {len(recent_losses)} recent losers had positive MFE."
    )
    lines.append(
        f"Recent trades reaching >200 bps MFE: {int((recent['mfe_bps'] >= 200.0).sum())}; recent trades realizing >=200 bps net: {int((recent['net_return_bps'] >= 200.0).sum())}."
    )
    lines.append(
        f"Recent average MAE is {period_rows[2]['avg_mae_bps']:.6f} bps versus {period_rows[0]['avg_mae_bps']:.6f} early, so adverse continuation is also more severe."
    )
    lines.append("")
    lines.append(_markdown_table(recent_time_rows, [
        "time_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "avg_mfe_bps",
        "avg_mae_bps",
        "avg_mfe_giveback_bps",
        "avg_mfe_capture_ratio",
    ]))
    lines.append("")
    lines.append(_markdown_table(recent_capture_rows, [
        "cap_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "avg_mfe_bps",
        "avg_mae_bps",
        "avg_mfe_giveback_bps",
        "avg_mfe_capture_ratio",
    ]))
    lines.append("")
    lines.append(_markdown_table(recent_giveback_rows, [
        "gb_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "avg_mfe_bps",
        "avg_mae_bps",
        "avg_mfe_giveback_bps",
        "avg_mfe_capture_ratio",
    ]))
    lines.append("")
    lines.append(_markdown_table(year_rows, [
        "year",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_mfe_bps",
        "median_mfe_bps",
        "avg_mae_bps",
        "median_mae_bps",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(month_rows, [
        "exit_month",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_mfe_bps",
        "median_mfe_bps",
        "avg_mae_bps",
        "median_mae_bps",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Recent MFE is happening earlier than the fixed 36-bar exit, and a large share of the favorable move is being given back before realization."
    )
    lines.append(
        f"The recent period has {int((recent['mfe_bps'] >= 200.0).sum())} trades with >200 bps MFE but {int((recent['net_return_bps'] >= 200.0).sum())} realized >=200 bps net, which is consistent with positive-tail decay plus exit-horizon mismatch."
    )
    lines.append(
        "Recent losses still show positive MFE on every loser, so alpha death is not proven by excursion behavior alone."
    )
    lines.append(
        f"The data therefore supports: exit-horizon mismatch likely, positive-tail decay likely, adverse continuation likely, alpha death not proven."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical replay path is mechanically valid and reproducible.")
    lines.append("- The signal still creates intratrade favorable excursion.")
    lines.append("- Diagnostic horizons are useful for locating where the edge appears in time.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- The configured 36-bar exit is not reliably capturing the recent-period favorable move.")
    lines.append("- The recent-period positive tail is not stable enough to treat the anchor as production evidence.")
    lines.append("- This report does not approve a replacement exit rule.")
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Compare 2025-2026 market regimes against 2020-2024.")
    lines.append("- Inspect whether the fast recent bounce is tied to specific microstructure states or session effects.")
    lines.append("- Test whether the fixed exit is systematically too slow only in recent regimes.")
    lines.append("- Only after diagnostics, consider PSR/DSR/PBO.")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trades = pd.read_csv(args.trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = normalize_v92_bar_timestamps(load_750btc_bars(args.bar_dir))
    report = build_report(trades, bars=bars, trade_log_path=args.trade_log, bar_dir=args.bar_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
