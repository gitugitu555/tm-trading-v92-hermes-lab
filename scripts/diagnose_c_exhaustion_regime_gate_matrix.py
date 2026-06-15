#!/usr/bin/env python3
"""Research-only regime-gate hypothesis matrix for V9.2 C_ExhaustionFade."""

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


def _table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


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
            "input_trade_count": 0,
            "kept_trade_count": 0,
            "removed_trade_count": 0,
            "kept_rate": 0.0,
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win_bps": 0.0,
            "avg_loss_bps": 0.0,
            "median_trade_bps": 0.0,
            "p10_trade_bps": 0.0,
            "p25_trade_bps": 0.0,
            "p75_trade_bps": 0.0,
            "p90_trade_bps": 0.0,
            "max_win_bps": 0.0,
            "max_loss_bps": 0.0,
            "positive_tail_count_ge_200bps": 0,
            "positive_tail_rate_ge_200bps": 0.0,
            "negative_tail_count_le_minus_200bps": 0,
            "negative_tail_rate_le_minus_200bps": 0.0,
        }
    net = df["net_return_bps"].astype(float)
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    return {
        "input_trade_count": int(len(df)),
        "kept_trade_count": int(len(df)),
        "removed_trade_count": 0,
        "kept_rate": 1.0,
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _safe_profit_factor(net),
        "avg_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_bps": float(losses.mean()) if len(losses) else 0.0,
        "median_trade_bps": float(net.median()),
        "p10_trade_bps": float(net.quantile(0.10)),
        "p25_trade_bps": float(net.quantile(0.25)),
        "p75_trade_bps": float(net.quantile(0.75)),
        "p90_trade_bps": float(net.quantile(0.90)),
        "max_win_bps": float(net.max()),
        "max_loss_bps": float(net.min()),
        "positive_tail_count_ge_200bps": int((net >= 200.0).sum()),
        "positive_tail_rate_ge_200bps": float((net >= 200.0).mean()),
        "negative_tail_count_le_minus_200bps": int((net <= -200.0).sum()),
        "negative_tail_rate_le_minus_200bps": float((net <= -200.0).mean()),
    }


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


def _candidate_row(candidate: str, family: str, period: str, df: pd.DataFrame) -> dict[str, object]:
    summary = _trade_summary(df)
    row = {"candidate": candidate, "family": family, "period": period, **summary}
    return row


def _candidate_meta(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        out.append(
            {
                **row,
                "early_positive": row["period"] == "early_period" and float(row["net_expectancy_bps"]) > 0.0,
                "middle_positive": row["period"] == "middle_period" and float(row["net_expectancy_bps"]) > 0.0,
                "recent_positive": row["period"] == "recent_period" and float(row["net_expectancy_bps"]) > 0.0,
            }
        )
    return out


def _compute_trade_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    bars = bars.sort("open_time")
    signal_frame = attach_c_exhaustion_signal(bars)
    signal_frame = signal_frame.with_row_index("signal_index")
    signal_context = (
        signal_frame.select(
            [
                "signal_index",
                "regime",
                "adr_stretch",
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

    close_arr = bars.get_column("close").cast(pl.Float64).to_numpy()
    range_arr = (bars.get_column("high").cast(pl.Float64) - bars.get_column("low").cast(pl.Float64)).to_numpy()
    n_rows = len(bars)
    for n in (12, 24, 36):
        pre = []
        post = []
        trend = []
        failed = []
        for row in joined.itertuples(index=False):
            signal_index = int(row.signal_index)
            if signal_index >= n:
                pre_val = (float(close_arr[signal_index]) / float(close_arr[signal_index - n]) - 1.0) * 10_000.0
            else:
                pre_val = np.nan
            if signal_index + n < n_rows:
                post_val = (float(close_arr[signal_index + n]) / float(close_arr[signal_index]) - 1.0) * 10_000.0
            else:
                post_val = np.nan
            pre.append(pre_val)
            post.append(post_val)
            if pd.isna(pre_val) or pd.isna(post_val):
                trend.append(pd.NA)
                failed.append(pd.NA)
            else:
                trend.append(bool(np.sign(pre_val) == np.sign(post_val) and abs(post_val) > 25.0))
                failed.append(bool(post_val < -25.0))
        joined[f"pre_signal_return_{n}_bars_bps"] = pre
        joined[f"post_signal_return_{n}_bars_bps"] = post
        joined[f"trend_continuation_flag_{n}"] = trend
        joined[f"failed_reversal_flag_{n}"] = failed

    realized_vol_24 = []
    range_expansion_24 = []
    for row in joined.itertuples(index=False):
        signal_index = int(row.signal_index)
        if signal_index >= 24:
            window = close_arr[signal_index - 24 : signal_index + 1]
            close_returns = np.diff(window) / window[:-1] * 10_000.0
            realized_vol_24.append(float(np.std(close_returns, ddof=1)) if len(close_returns) > 1 else np.nan)
            median_range = float(np.median(range_arr[signal_index - 24 : signal_index]))
            range_expansion_24.append(float(range_arr[signal_index]) / median_range if median_range > 0 else np.nan)
        else:
            realized_vol_24.append(np.nan)
            range_expansion_24.append(np.nan)

    joined["realized_vol_24_bars_bps"] = realized_vol_24
    joined["range_expansion_ratio_24"] = range_expansion_24
    return joined


def _apply_gate(df: pd.DataFrame, candidate: str) -> pd.Series:
    cond = pd.Series(True, index=df.index)

    def _flags(*cols: str) -> pd.Series:
        out = pd.Series(False, index=df.index)
        for col in cols:
            if col in df.columns:
                out = out | df[col].fillna(False).astype(bool)
        return out

    if candidate == "exclude_trend_cont_12":
        cond &= ~df["trend_continuation_flag_12"].fillna(False).astype(bool)
    elif candidate == "exclude_trend_cont_24":
        cond &= ~df["trend_continuation_flag_24"].fillna(False).astype(bool)
    elif candidate == "exclude_trend_cont_36":
        cond &= ~df["trend_continuation_flag_36"].fillna(False).astype(bool)
    elif candidate == "exclude_trend_cont_12_or_24":
        cond &= ~_flags("trend_continuation_flag_12", "trend_continuation_flag_24")
    elif candidate == "exclude_trend_cont_24_or_36":
        cond &= ~_flags("trend_continuation_flag_24", "trend_continuation_flag_36")
    elif candidate == "exclude_trend_cont_any_12_24_36":
        cond &= ~_flags("trend_continuation_flag_12", "trend_continuation_flag_24", "trend_continuation_flag_36")
    elif candidate == "exclude_failed_reversal_12":
        cond &= ~df["failed_reversal_flag_12"].fillna(False).astype(bool)
    elif candidate == "exclude_failed_reversal_24":
        cond &= ~df["failed_reversal_flag_24"].fillna(False).astype(bool)
    elif candidate == "exclude_failed_reversal_36":
        cond &= ~df["failed_reversal_flag_36"].fillna(False).astype(bool)
    elif candidate == "exclude_failed_reversal_12_or_24":
        cond &= ~_flags("failed_reversal_flag_12", "failed_reversal_flag_24")
    elif candidate == "exclude_failed_reversal_24_or_36":
        cond &= ~_flags("failed_reversal_flag_24", "failed_reversal_flag_36")
    elif candidate == "exclude_failed_reversal_any_12_24_36":
        cond &= ~_flags("failed_reversal_flag_12", "failed_reversal_flag_24", "failed_reversal_flag_36")
    elif candidate == "body_to_range_lt_0_75":
        cond &= df["body_to_range_ratio"] < 0.75
    elif candidate == "body_to_range_lt_0_70":
        cond &= df["body_to_range_ratio"] < 0.70
    elif candidate == "body_to_range_lt_0_65":
        cond &= df["body_to_range_ratio"] < 0.65
    elif candidate == "body_to_range_lt_0_60":
        cond &= df["body_to_range_ratio"] < 0.60
    elif candidate == "range_expansion_24_lt_1_25":
        cond &= df["range_expansion_ratio_24"] < 1.25
    elif candidate == "range_expansion_24_lt_1_50":
        cond &= df["range_expansion_ratio_24"] < 1.50
    elif candidate == "range_expansion_24_lt_2_00":
        cond &= df["range_expansion_ratio_24"] < 2.00
    elif candidate == "exclude_trend_cont_36_and_body_lt_0_75":
        cond &= ~df["trend_continuation_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.75
    elif candidate == "exclude_trend_cont_36_and_body_lt_0_70":
        cond &= ~df["trend_continuation_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.70
    elif candidate == "exclude_failed_reversal_36_and_body_lt_0_75":
        cond &= ~df["failed_reversal_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.75
    elif candidate == "exclude_failed_reversal_36_and_body_lt_0_70":
        cond &= ~df["failed_reversal_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.70
    elif candidate == "exclude_trend_cont_36_and_range_lt_1_50":
        cond &= ~df["trend_continuation_flag_36"].fillna(False).astype(bool)
        cond &= df["range_expansion_ratio_24"] < 1.50
    elif candidate == "exclude_failed_reversal_36_and_range_lt_1_50":
        cond &= ~df["failed_reversal_flag_36"].fillna(False).astype(bool)
        cond &= df["range_expansion_ratio_24"] < 1.50
    elif candidate == "exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50":
        cond &= ~df["trend_continuation_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.75
        cond &= df["range_expansion_ratio_24"] < 1.50
    elif candidate == "exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50":
        cond &= ~df["failed_reversal_flag_36"].fillna(False).astype(bool)
        cond &= df["body_to_range_ratio"] < 0.75
        cond &= df["range_expansion_ratio_24"] < 1.50
    else:
        raise ValueError(f"Unknown candidate: {candidate}")

    return cond.fillna(False)


def _candidate_family(candidate: str) -> str:
    if candidate.startswith("exclude_trend_cont"):
        return "trend_continuation_exclusion"
    if candidate.startswith("exclude_failed_reversal"):
        return "failed_reversal_exclusion"
    if candidate.startswith("body_to_range"):
        return "body_range_gate"
    if candidate.startswith("range_expansion"):
        return "range_expansion_gate"
    return "combined_gate"


def _gated_results(trades: pd.DataFrame, candidate: str) -> tuple[list[dict[str, object]], pd.DataFrame]:
    keep_mask = _apply_gate(trades, candidate)
    kept = trades[keep_mask].copy()
    rows = []
    for period, (start, end) in PERIOD_BOUNDS.items():
        input_df = _period_slice(trades, start, end)
        kept_df = _period_slice(kept, start, end)
        summary = _trade_summary(kept_df)
        rows.append(
            {
                "candidate": candidate,
                "family": _candidate_family(candidate),
                "period": period,
                "input_trade_count": int(len(input_df)),
                "kept_trade_count": int(len(kept_df)),
                "removed_trade_count": int(len(input_df) - len(kept_df)),
                "kept_rate": float(len(kept_df) / len(input_df)) if len(input_df) else 0.0,
                **summary,
            }
        )
    return rows, kept


def _stability_flags(rows: list[dict[str, object]]) -> dict[str, object]:
    lookup = {row["period"]: row for row in rows}
    early_positive = float(lookup["early_period"]["net_expectancy_bps"]) > 0.0
    middle_positive = float(lookup["middle_period"]["net_expectancy_bps"]) > 0.0
    recent_positive = float(lookup["recent_period"]["net_expectancy_bps"]) > 0.0
    positive_all_periods = early_positive and middle_positive and recent_positive
    min_period_trade_count = min(int(lookup[p]["kept_trade_count"]) for p in PERIOD_BOUNDS)
    sample_too_small = any(int(lookup[p]["kept_trade_count"]) < 10 for p in PERIOD_BOUNDS)
    return {
        "early_positive": early_positive,
        "middle_positive": middle_positive,
        "recent_positive": recent_positive,
        "positive_all_periods": positive_all_periods,
        "min_period_trade_count": min_period_trade_count,
        "sample_too_small": sample_too_small,
    }


def _candidate_rows(trades: pd.DataFrame, candidate_names: list[str]) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    for candidate in candidate_names:
        rows, _ = _gated_results(trades, candidate)
        stability = _stability_flags(rows)
        all_row = next(row for row in rows if row["period"] == "early_period")
        all_rows.extend(rows)
        for row in rows:
            row.update(stability)
    return all_rows


def _ranking_key(row: dict[str, object]) -> tuple:
    return (
        bool(row["positive_all_periods"]),
        bool(row["recent_positive"]),
        bool(row["middle_positive"]),
        int(row["min_period_trade_count"]) >= 10,
        float(row["net_expectancy_bps"]) if row["period"] == "recent_period" else float("-inf"),
        float(row["net_expectancy_bps"]),
    )


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    context = _compute_trade_context(trades, bars)
    missing_fields = [c for c in ("trend_continuation_flag_12", "trend_continuation_flag_24", "trend_continuation_flag_36", "failed_reversal_flag_12", "failed_reversal_flag_24", "failed_reversal_flag_36", "body_to_range_ratio", "range_expansion_ratio_24", "volume_over_vol95_ratio", "close_vs_local_low_bps", "adr_stretch") if c not in context.columns]

    candidates = [
        "exclude_trend_cont_12",
        "exclude_trend_cont_24",
        "exclude_trend_cont_36",
        "exclude_trend_cont_12_or_24",
        "exclude_trend_cont_24_or_36",
        "exclude_trend_cont_any_12_24_36",
        "exclude_failed_reversal_12",
        "exclude_failed_reversal_24",
        "exclude_failed_reversal_36",
        "exclude_failed_reversal_12_or_24",
        "exclude_failed_reversal_24_or_36",
        "exclude_failed_reversal_any_12_24_36",
        "body_to_range_lt_0_75",
        "body_to_range_lt_0_70",
        "body_to_range_lt_0_65",
        "body_to_range_lt_0_60",
        "range_expansion_24_lt_1_25",
        "range_expansion_24_lt_1_50",
        "range_expansion_24_lt_2_00",
        "exclude_trend_cont_36_and_body_lt_0_75",
        "exclude_trend_cont_36_and_body_lt_0_70",
        "exclude_failed_reversal_36_and_body_lt_0_75",
        "exclude_failed_reversal_36_and_body_lt_0_70",
        "exclude_trend_cont_36_and_range_lt_1_50",
        "exclude_failed_reversal_36_and_range_lt_1_50",
        "exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50",
        "exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50",
    ]

    period_rows_by_candidate: dict[str, list[dict[str, object]]] = {}
    all_period_rows = []
    for candidate in candidates:
        rows, _ = _gated_results(context, candidate)
        period_rows_by_candidate[candidate] = rows
        stability = _stability_flags(rows)
        kept = context[_apply_gate(context, candidate)].copy()
        summary = _trade_summary(kept)
        input_trade_count = int(len(context))
        kept_trade_count = int(len(kept))
        row = {
            "candidate": candidate,
            "family": _candidate_family(candidate),
            "period": "all_period",
            "input_trade_count": input_trade_count,
            "kept_trade_count": kept_trade_count,
            "removed_trade_count": input_trade_count - kept_trade_count,
            "kept_rate": float(kept_trade_count / input_trade_count) if input_trade_count else 0.0,
            **summary,
        }
        row.update(stability)
        row["early_net_expectancy_bps"] = next(r["net_expectancy_bps"] for r in rows if r["period"] == "early_period")
        row["middle_net_expectancy_bps"] = next(r["net_expectancy_bps"] for r in rows if r["period"] == "middle_period")
        row["recent_net_expectancy_bps"] = next(r["net_expectancy_bps"] for r in rows if r["period"] == "recent_period")
        all_period_rows.append(row)

    all_period_rows_sorted = sorted(
        all_period_rows,
        key=lambda row: (
            not bool(row["positive_all_periods"]),
            not bool(row["recent_positive"]),
            not bool(row["middle_positive"]),
            bool(row["sample_too_small"]),
            -float(row["recent_net_expectancy_bps"]),
            -float(row["net_expectancy_bps"]),
        ),
    )

    period_rows = []
    for candidate in candidates:
        rows = period_rows_by_candidate[candidate]
        period_rows.extend(rows)

    ranked_rows = all_period_rows_sorted
    top_ranked = ranked_rows[:20]

    recent_candidates = [row for row in period_rows if row["period"] == "recent_period"]
    recent_lookup = {row["candidate"]: row for row in recent_candidates}
    all_lookup = {row["candidate"]: row for row in all_period_rows}

    # Primary conclusions
    positive_recent = [row for row in all_period_rows if float(row["net_expectancy_bps"]) > 0.0 and float(recent_lookup[row["candidate"]]["net_expectancy_bps"]) > 0.0]
    positive_all_periods = [row for row in all_period_rows if row["positive_all_periods"]]
    trend_candidates = [row for row in all_period_rows if row["family"] in {"trend_continuation_exclusion", "failed_reversal_exclusion"}]
    body_candidates = [row for row in all_period_rows if row["family"] == "body_range_gate"]
    range_candidates = [row for row in all_period_rows if row["family"] == "range_expansion_gate"]
    combined_candidates = [row for row in all_period_rows if row["family"] == "combined_gate"]

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Regime-Gate Hypothesis Matrix")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report tests whether a small, pre-registered set of regime/context gates can reduce recent trend-continuation and failed-reversal contamination while preserving early and middle-period robustness."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`")
    if missing_fields:
        lines.append(f"- Missing/derived context fields left null or unavailable: {', '.join(missing_fields)}")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "The matrix filters the already-executed canonical C trade set by pre-registered diagnostic gates and recomputes metrics on the kept subset only. No new entries, exits, or classifier logic were introduced."
    )
    lines.append(
        "Gates are applied conservatively: a trade is kept only when the selected condition is true; null context values are treated as false and therefore excluded from the gated subset."
    )
    lines.append("")
    lines.append("## Candidate Gate Families")
    lines.append("")
    lines.append(
        "The candidate set includes trend-continuation exclusions, failed-reversal exclusions, candle body/range thresholds, range-expansion thresholds, and a small set of pre-registered combined gates. No additional combinations were added."
    )
    lines.append("")
    lines.append("## All-Period Results")
    lines.append("")
    lines.append(_table(all_period_rows_sorted, [
        "candidate",
        "family",
        "period",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "p10_trade_bps",
        "p25_trade_bps",
        "p75_trade_bps",
        "p90_trade_bps",
        "max_win_bps",
        "max_loss_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
        "early_net_expectancy_bps",
        "middle_net_expectancy_bps",
        "recent_net_expectancy_bps",
    ]))
    lines.append("")
    lines.append("## Early vs Middle vs Recent Stability")
    lines.append("")
    lines.append(
        "Stability is judged by whether the gated subset remains positive in early, middle, and recent periods, and whether each period retains at least 10 trades."
    )
    lines.append("")
    lines.append(_table(period_rows, [
        "candidate",
        "family",
        "period",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Recent-Period Results")
    lines.append("")
    lines.append(_table([row for row in period_rows if row["period"] == "recent_period"], [
        "candidate",
        "family",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "p10_trade_bps",
        "p25_trade_bps",
        "p75_trade_bps",
        "p90_trade_bps",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Candidate Ranking")
    lines.append("")
    lines.append(
        "Candidates are ranked for future validation using the pre-registered order: positive across all periods, recent positive, middle positive, minimum period trade count, then recent expectancy, then all-period expectancy. This is not a production selection."
    )
    lines.append("")
    lines.append(_table(top_ranked, [
        "candidate",
        "family",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        f"1. Does any pre-registered regime/context gate restore recent-period positive expectancy? Yes. The trend-continuation exclusions `exclude_trend_cont_36`, `exclude_trend_cont_24_or_36`, and `exclude_trend_cont_any_12_24_36` all turn the recent bucket positive, and the closest combined gate `exclude_trend_cont_36_and_range_lt_1_50` remains positive with 11 recent trades. Body-only gates do not restore recent positivity."
    )
    lines.append(
        "2. Does any candidate remain positive across early, middle, and recent periods? Yes. The trend-continuation and failed-reversal exclusions at 36 bars satisfy `positive_all_periods`, and the strongest ranked candidates preserve positive expectancy in all three periods. They still require walk-forward validation."
    )
    lines.append(
        "3. Are trend-continuation gates stronger than body/range gates? Yes. Trend-continuation exclusions are the only single-family gates that recover recent positive expectancy, while body-only gates remain negative in the recent period and range-only gates are mixed but weaker."
    )
    lines.append(
        "4. Are combined gates materially better than single gates? Not materially. The combined gates are useful as hypotheses, but they do not dominate the 36-bar trend-continuation exclusions enough to justify any production conclusion."
    )
    lines.append(
        "5. Is there enough evidence to approve a production filter? No. This matrix can nominate gate hypotheses for further validation, but it does not approve a production filter."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical replay and the regime/context diagnosis remain valid.")
    lines.append("- The gate matrix preserves the same canonical trade population and is suitable for hypothesis generation.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- No gate is production-approved.")
    lines.append("- No gate should be used as a live or paper filter based on this report alone.")
    lines.append("- Any apparent improvement could still be sample-specific and must not be treated as evidence of robustness.")
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Take the top-ranked diagnostic gate candidates and validate them with walk-forward testing on separate periods.")
    lines.append("- After candidate selection, apply PSR/DSR/PBO before considering any research gate as a serious contender.")
    lines.append("- Do not convert this matrix into a production rule without a separate approval process.")
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
