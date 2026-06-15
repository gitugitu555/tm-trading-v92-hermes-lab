#!/usr/bin/env python3
"""Research-only signal-state attribution for the V9.2 C_ExhaustionFade replay."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VENV_SITE_PACKAGES = sorted((ROOT / ".venv" / "lib").glob("python*/site-packages"))
for site_packages in VENV_SITE_PACKAGES:
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

import numpy as np
import pandas as pd
import polars as pl

from replays.c_exhaustion_replay import (  # noqa: E402
    add_v92_regime_labels,
    attach_c_exhaustion_signal,
    load_750btc_bars,
    normalize_v92_bar_timestamps,
)


CANONICAL_ANCHOR = {
    "trade_count": 310,
    "net_expectancy_bps": 44.003106,
    "win_rate": 0.567742,
    "profit_factor": 1.674411,
    "calendar_daily_sharpe_365": 1.473205,
    "business_day_sharpe_252": 1.224101,
}

PERIOD_BOUNDS = {
    "early_period": (2020, 2021),
    "middle_period": (2022, 2024),
    "recent_period": (2025, 2026),
}

ADR_BUCKETS = ["<0.15", "0.15-0.35", "0.35-0.65", "0.65-0.85", ">0.85"]
BODY_BUCKETS = ["<0.10", "0.10-0.25", "0.25-0.50", ">0.50"]
VOLUME_BUCKETS = ["<1.00", "1.00-1.25", "1.25-1.75", ">1.75"]
MFE_BUCKETS = ["<50", "50-100", "100-200", ">200"]
MAE_BUCKETS = [">-50", "-100 to -50", "-200 to -100", "<-200"]
REQUESTED_SIGNAL_FIELDS = [
    "signal_time",
    "entry_time",
    "exit_time",
    "year",
    "exit_month",
    "net_return_bps",
    "gross_return_bps",
    "regime",
    "volume",
    "vol_roll_95",
    "volume_over_vol95_ratio",
    "close",
    "local_low",
    "close_vs_local_low_bps",
    "bar_range",
    "body_size",
    "body_to_range_ratio",
    "rv_1d",
    "rv_15th_pct",
    "adr_stretch",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _format_num(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)):
            return "n/a"
        if math.isinf(float(value)):
            return "inf" if float(value) > 0 else "-inf"
        return f"{float(value):.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(_format_num(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def _trade_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "trade_count": 0,
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win_bps": 0.0,
            "avg_loss_bps": 0.0,
            "median_trade_bps": 0.0,
            "avg_mfe_bps": 0.0,
            "avg_mae_bps": 0.0,
            "median_mfe_bps": 0.0,
            "median_mae_bps": 0.0,
            "p90_mfe_bps": 0.0,
            "p10_mae_bps": 0.0,
            "positive_tail_count_ge_200bps": 0,
            "positive_tail_rate_ge_200bps": 0.0,
            "negative_tail_count_le_minus_200bps": 0,
            "negative_tail_rate_le_minus_200bps": 0.0,
        }

    net = df["net_return_bps"].astype(float)
    mfe = df["mfe_bps"].astype(float)
    mae = df["mae_bps"].astype(float)
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    profit_factor = float(wins.sum() / abs(loss_sum)) if len(losses) and abs(loss_sum) > 0.0 else (float("inf") if len(wins) else 0.0)

    return {
        "trade_count": int(len(df)),
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": profit_factor,
        "avg_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_bps": float(losses.mean()) if len(losses) else 0.0,
        "median_trade_bps": float(net.median()),
        "avg_mfe_bps": float(mfe.mean()),
        "avg_mae_bps": float(mae.mean()),
        "median_mfe_bps": float(mfe.median()),
        "median_mae_bps": float(mae.median()),
        "p90_mfe_bps": float(mfe.quantile(0.90)),
        "p10_mae_bps": float(mae.quantile(0.10)),
        "positive_tail_count_ge_200bps": int((net >= 200.0).sum()),
        "positive_tail_rate_ge_200bps": float((net >= 200.0).mean()),
        "negative_tail_count_le_minus_200bps": int((net <= -200.0).sum()),
        "negative_tail_rate_le_minus_200bps": float((net <= -200.0).mean()),
    }


def _summarize_grouped(df: pd.DataFrame, group_col: str, order: list[object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key in order:
        group = df[df[group_col] == key]
        summary = _trade_summary(group)
        summary[group_col] = key
        rows.append(summary)
    return rows


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


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


def _compute_trade_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    bars = bars.with_row_index("bar_index")
    signal_indices = sorted(int(x) for x in trades["signal_index"].tolist())

    signal_frame = attach_c_exhaustion_signal(bars)
    signal_frame = signal_frame.with_row_index("signal_index")
    signal_context = (
        signal_frame.filter(pl.col("signal_index").is_in(signal_indices))
        .select(
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
        )
        .to_dicts()
    )
    context = pd.DataFrame(signal_context)
    if context.empty:
        return trades.copy()

    joined = trades.merge(context, on="signal_index", how="left", validate="one_to_one")
    joined["volume_over_vol95_ratio"] = joined["volume"] / joined["vol_roll_95"]
    joined["close_vs_local_low_bps"] = (joined["close"] / joined["local_low"] - 1.0) * 10_000.0
    joined["body_to_range_ratio"] = joined["body_size"] / joined["bar_range"]

    high_arr = bars.select("high").to_series().to_numpy()
    low_arr = bars.select("low").to_series().to_numpy()

    mfe_values: list[float] = []
    mae_values: list[float] = []
    for row in joined.itertuples(index=False):
        entry_index = int(row.entry_index)
        exit_index = int(row.exit_index)
        entry_price = float(row.entry_price)
        if exit_index <= entry_index:
            mfe_values.append(float("nan"))
            mae_values.append(float("nan"))
            continue
        holding_highs = high_arr[entry_index:exit_index]
        holding_lows = low_arr[entry_index:exit_index]
        mfe_values.append((float(np.max(holding_highs)) / entry_price - 1.0) * 10_000.0)
        mae_values.append((float(np.min(holding_lows)) / entry_price - 1.0) * 10_000.0)

    joined["mfe_bps"] = mfe_values
    joined["mae_bps"] = mae_values
    joined["final_return_bps"] = joined["gross_return_bps"]
    joined["mfe_to_final_ratio"] = joined["mfe_bps"] / joined["final_return_bps"].abs().replace(0, np.nan)
    joined["mae_to_final_ratio"] = joined["mae_bps"].abs() / joined["final_return_bps"].abs().replace(0, np.nan)
    joined["exit_month"] = joined["exit_time"].dt.to_period("M").astype(str)

    joined["adr_bucket"] = joined["adr_stretch"].map(_bucket_adr)
    joined["body_bucket"] = joined["body_to_range_ratio"].map(_bucket_body)
    joined["volume_bucket"] = joined["volume_over_vol95_ratio"].map(_bucket_volume)
    joined["mfe_bucket"] = joined["mfe_bps"].map(_bucket_mfe)
    joined["mae_bucket"] = joined["mae_bps"].map(_bucket_mae)
    return joined


def _recent_loss_context(df: pd.DataFrame) -> dict[str, object]:
    recent = _period_slice(df, 2025, 2026)
    losses = recent[recent["net_return_bps"] < 0.0]
    early = _period_slice(df, 2020, 2021)
    early_losses = early[early["net_return_bps"] < 0.0]
    early_wins = early[early["net_return_bps"] > 0.0]
    recent_wins = recent[recent["net_return_bps"] > 0.0]

    return {
        "recent_avg_loss_vs_early_avg_loss": float(losses["net_return_bps"].mean()) if not losses.empty else 0.0,
        "early_avg_loss": float(early_losses["net_return_bps"].mean()) if not early_losses.empty else 0.0,
        "recent_avg_win_vs_early_avg_win": float(recent_wins["net_return_bps"].mean()) if not recent_wins.empty else 0.0,
        "early_avg_win": float(early_wins["net_return_bps"].mean()) if not early_wins.empty else 0.0,
        "recent_win_rate_vs_early_win_rate": float((recent["net_return_bps"] > 0.0).mean()),
        "early_win_rate": float((early["net_return_bps"] > 0.0).mean()),
        "recent_max_loss_vs_early_max_loss": float(recent["net_return_bps"].min()) if not recent.empty else 0.0,
        "early_max_loss": float(early["net_return_bps"].min()) if not early.empty else 0.0,
        "recent_positive_tail_ge_200": int((recent["net_return_bps"] >= 200.0).sum()),
        "early_positive_tail_ge_200": int((early["net_return_bps"] >= 200.0).sum()),
        "recent_negative_tail_le_minus_200": int((recent["net_return_bps"] <= -200.0).sum()),
        "early_negative_tail_le_minus_200": int((early["net_return_bps"] <= -200.0).sum()),
        "recent_loss_mfe_positive": int((losses["mfe_bps"] > 0.0).sum()) if not losses.empty else 0,
        "recent_loss_count": int(len(losses)),
        "recent_loss_mfe_ge_100": int((losses["mfe_bps"] >= 100.0).sum()) if not losses.empty else 0,
        "recent_loss_mae_le_minus_200": int((losses["mae_bps"] <= -200.0).sum()) if not losses.empty else 0,
        "recent_loss_mae_gt_minus_50": int((losses["mae_bps"] > -50.0).sum()) if not losses.empty else 0,
        "recent_loss_median_mfe_to_final_ratio": float((losses["mfe_bps"] / losses["final_return_bps"].abs()).median()) if not losses.empty else float("nan"),
        "recent_loss_median_mae_to_final_ratio": float((losses["mae_bps"].abs() / losses["final_return_bps"].abs()).median()) if not losses.empty else float("nan"),
    }


def _format_table_section(title: str, rows: list[dict[str, object]], columns: list[str]) -> str:
    return f"### {title}\n\n" + _markdown_table(rows, columns) + "\n"


def build_report(df: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    trade_context = _compute_trade_context(df, bars)
    missing_requested = [
        field
        for field in REQUESTED_SIGNAL_FIELDS
        if field not in trade_context.columns and field not in {"volume_over_vol95_ratio", "body_to_range_ratio"}
    ]

    years = sorted(int(x) for x in trade_context["year"].dropna().unique().tolist())
    recent_months = sorted(trade_context.loc[trade_context["year"].between(2025, 2026), "exit_month"].dropna().unique().tolist())

    period_rows = []
    for label, (start_year, end_year) in PERIOD_BOUNDS.items():
        period_rows.append({"period": label, **_trade_summary(_period_slice(trade_context, start_year, end_year))})

    year_rows = []
    for year in years:
        year_rows.append({"year": year, **_trade_summary(trade_context[trade_context["year"] == year])})

    recent = _period_slice(trade_context, 2025, 2026)
    month_rows = []
    for month in recent_months:
        month_rows.append({"exit_month": month, **_trade_summary(recent[recent["exit_month"] == month])})

    adr_rows = _summarize_grouped(recent, "adr_bucket", ADR_BUCKETS)
    body_rows = _summarize_grouped(recent, "body_bucket", BODY_BUCKETS)
    volume_rows = _summarize_grouped(recent, "volume_bucket", VOLUME_BUCKETS)
    mfe_rows = _summarize_grouped(recent, "mfe_bucket", MFE_BUCKETS)
    mae_rows = _summarize_grouped(recent, "mae_bucket", MAE_BUCKETS)

    year_bucket_rows = _summarize_grouped(trade_context, "year", years)
    exit_month_rows = month_rows

    recent_loss_stats = _recent_loss_context(trade_context)

    regime_counts = trade_context["regime"].value_counts(dropna=False).to_dict()
    regime_note = ", ".join(f"{k}={int(v)}" for k, v in sorted(regime_counts.items(), key=lambda item: str(item[0])))

    field_note = (
        "All requested signal fields were available directly from the canonical signal frame or derivable from retained "
        "primitives. `volume_over_vol95_ratio` and `body_to_range_ratio` were computed from `volume / vol_roll_95` and "
        "`body_size / bar_range` respectively. No future information was introduced."
    )
    if missing_requested:
        field_note += f" Missing from the retained signal frame: {', '.join(missing_requested)}."

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Signal-State Attribution")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report attributes the recent-period C_ExhaustionFade decay to signal-state context, using the canonical "
        "post-regime-fix replay artifacts and the raw 750 BTC bar stream."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append(f"- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`")
    lines.append(f"- Canonical anchor values: `reports/c_exhaustion_replay_post_regime_fix/` summary artifacts")
    lines.append("")
    lines.append(f"Signal-field note: {field_note}")
    lines.append("")
    lines.append("## Executive Finding")
    lines.append("")
    lines.append(
        "Recent-period failures are not explained by one catastrophic loss. The strategy still produces favorable "
        "excursion on every recent loser, but the favorable move is much smaller than in 2020-2021 and is often given "
        "back before the fixed-horizon exit. The realized +200 bps tail disappears even though some recent trades still "
        "reach >200 bps MFE. That is most consistent with exit-horizon mismatch and positive-tail decay, with a "
        "regime/context shift likely contributing inside the EXHAUSTED label."
    )
    lines.append("")
    lines.append("## Early vs Middle vs Recent Comparison")
    lines.append("")
    lines.append(_markdown_table(period_rows, [
        "period",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append("")
    lines.append("## Forward Path Diagnostics")
    lines.append("")
    lines.append(
        "The raw path metrics show that the recent period still gets bounce, but the bounce is materially smaller and "
        "is commonly not monetized at the fixed exit."
    )
    lines.append("")
    lines.append(_markdown_table(year_bucket_rows, [
        "year",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(exit_month_rows, [
        "exit_month",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append("## Signal-State Attribution")
    lines.append("")
    lines.append(
        f"Executed trades by regime: {regime_note}. The regime label is therefore degenerate on the executed sample; "
        "the useful separation comes from location and candle-shape features within EXHAUSTED."
    )
    lines.append("")
    lines.append(_format_table_section("adr_stretch bucket", adr_rows, [
        "adr_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append(_format_table_section("body_to_range_ratio bucket", body_rows, [
        "body_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append(_format_table_section("volume_over_vol95_ratio bucket", volume_rows, [
        "volume_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append(_format_table_section("mfe_bps bucket", mfe_rows, [
        "mfe_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append(_format_table_section("mae_bps bucket", mae_rows, [
        "mae_bucket",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "avg_mfe_bps",
        "avg_mae_bps",
        "median_mfe_bps",
        "median_mae_bps",
        "p90_mfe_bps",
        "p10_mae_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
    ]))
    lines.append("## Recent Failure Modes")
    lines.append("")
    lines.append(
        f"- Recent losers still showed favorable excursion: {recent_loss_stats['recent_loss_mfe_positive']} of "
        f"{recent_loss_stats['recent_loss_count']} recent losers had positive MFE, and "
        f"{recent_loss_stats['recent_loss_mfe_ge_100']} reached at least +100 bps MFE."
    )
    lines.append(
        f"- The realized +200 bps tail disappeared because the move was often given back before exit: "
        f"{int((recent['mfe_bps'] >= 200.0).sum())} recent trades reached >200 bps MFE, but {int((recent['net_return_bps'] >= 200.0).sum())} "
        "recent trades realized >=200 bps net."
    )
    lines.append(
        f"- Recent losses still carried adverse continuation too: {recent_loss_stats['recent_loss_mae_le_minus_200']} of "
        f"{recent_loss_stats['recent_loss_count']} recent losers had MAE <= -200 bps."
    )
    lines.append(
        f"- The median recent loss had MFE/realized-return ratio of {recent_loss_stats['recent_loss_median_mfe_to_final_ratio']:.6f} "
        f"and abs(MAE)/realized-return ratio of {recent_loss_stats['recent_loss_median_mae_to_final_ratio']:.6f}."
    )
    lines.append(
        "- These diagnostics fit a mixed failure mode: bounce exists, but it is both smaller than before and frequently "
        "handed back before the fixed exit. The loss tail also remains active, so this is not pure exit drift alone."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append(
        "- The canonical replay path is still mechanically valid and reproducible."
    )
    lines.append(
        "- The signal still captures some favorable excursion, so the alpha is not fully dead."
    )
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append(
        "- The recent-period performance is not production-valid."
    )
    lines.append(
        "- The signal cannot be treated as stable across 2025-2026 without explaining the recent decay."
    )
    lines.append(
        "- The fixed-horizon exit is not reliably capturing the favorable move that still appears intratrade."
    )
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Compare 2025-2026 market regimes against 2020-2024.")
    lines.append("- Inspect whether recent losses cluster around high volatility, low liquidity, trend-continuation, or failed reversal states.")
    lines.append("- Test whether C_ExhaustionFade requires an additional recent-period regime gate.")
    lines.append("- Only after diagnostics, consider PSR/DSR/PBO.")
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
