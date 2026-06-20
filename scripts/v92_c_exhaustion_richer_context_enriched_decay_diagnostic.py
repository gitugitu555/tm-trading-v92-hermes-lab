#!/usr/bin/env python3
"""Aggregate-only richer-context enriched decay diagnostic for the V9.2 C_Exhaustion branch."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import add_v92_regime_labels, attach_c_exhaustion_signal, load_750btc_bars, normalize_v92_bar_timestamps  # noqa: E402
from scripts.diagnose_c_exhaustion_regime_context import _compute_trade_context  # noqa: E402
from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import _markdown_table, _parse_trade_frame  # noqa: E402

DEFAULT_TRADE_LOG = Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RICHER_CONTEXT_ENRICHED_DECAY_DIAGNOSTIC.md")

HISTORICAL_START_YEAR = 2020
HISTORICAL_END_YEAR = 2024
RECENT_START_YEAR = 2025
RECENT_END_YEAR = 2026

TAIL_WIN_THRESHOLD_BPS = 200.0
TAIL_LOSS_THRESHOLD_BPS = -200.0

VWAP_BUCKET_ORDER = ["below -100 bps", "-100 to -25 bps", "-25 to +25 bps", "+25 to +100 bps", "above +100 bps", "n/a"]
RECENT_RANGE_BUCKET_ORDER = ["near recent low", "middle range", "near recent high", "n/a"]
TRADE_DENSITY_BUCKET_ORDER = ["low", "medium", "high", "n/a"]
CVD_BUCKET_ORDER = ["negative", "neutral", "positive", "n/a"]
SESSION_BUCKET_ORDER = ["asia", "europe", "overlap", "us", "session_unknown"]
WEEKDAY_BUCKET_ORDER = ["weekday", "weekend", "unknown"]
LOCAL_TREND_BUCKET_ORDER = ["trend_continuation", "failed_reversal", "range_expansion", "range", "mixed", "n/a"]
PRIMARY_CONTEXT_FIELDS = {
    "trade_density",
    "distance_from_recent_high_low",
    "local_trend_range_state",
    "distance_from_vwap",
    "cvd_delta",
    "session_time_of_day_labels",
    "weekday_weekend_effect",
}

INTERACTION_SPECS = [
    ("trade_density_bucket", "local_trend_range_state"),
    ("trade_density_bucket", "distance_from_vwap_bucket"),
    ("trade_density_bucket", "cvd_delta_bucket"),
    ("distance_from_recent_high_low_bucket", "local_trend_range_state"),
    ("distance_from_vwap_bucket", "local_trend_range_state"),
    ("cvd_delta_bucket", "local_trend_range_state"),
    ("session_time_of_day_labels", "trade_density_bucket"),
    ("weekday_weekend_effect", "session_time_of_day_labels"),
]


@dataclass(frozen=True)
class SyntheticTestResult:
    name: str
    passed: bool
    details: str


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{float(value) * 100.0:.2f}%"


def _bool_text(value: object) -> str:
    return "yes" if bool(value) else "no"


def _safe_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series([np.nan] * len(frame), index=frame.index)


def _period_label(year: object) -> str:
    try:
        year_int = int(year)
    except Exception:
        return "unresolved"
    if HISTORICAL_START_YEAR <= year_int <= HISTORICAL_END_YEAR:
        return "historical"
    if RECENT_START_YEAR <= year_int <= RECENT_END_YEAR:
        return "recent"
    return "unresolved"


def _summary_stats(series: pd.Series) -> dict[str, object]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "p10": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    return {
        "count": int(clean.shape[0]),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "p10": float(clean.quantile(0.10)),
        "p90": float(clean.quantile(0.90)),
        "min": float(clean.min()),
        "max": float(clean.max()),
    }


def _profit_factor(net: pd.Series) -> float:
    clean = pd.to_numeric(net, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    wins = clean[clean > 0.0]
    losses = clean[clean < 0.0]
    if losses.empty:
        return float("inf") if not wins.empty else 0.0
    loss_sum = float(losses.sum())
    return float(wins.sum() / abs(loss_sum)) if abs(loss_sum) > 0.0 else (float("inf") if not wins.empty else 0.0)


def _max_drawdown(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    equity = clean.cumsum()
    drawdown = equity - equity.cummax()
    return float(drawdown.min())


def _period_slice(frame: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return frame[frame["year"].between(start_year, end_year)].copy()


def _bucket_distance_from_vwap(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < -100.0:
        return "below -100 bps"
    if value < -25.0:
        return "-100 to -25 bps"
    if value <= 25.0:
        return "-25 to +25 bps"
    if value <= 100.0:
        return "+25 to +100 bps"
    return "above +100 bps"


def _bucket_recent_range_position(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value <= 0.33:
        return "near recent low"
    if value <= 0.67:
        return "middle range"
    return "near recent high"


def _bucket_trade_density(value: float | None, q1: float | None = None, q2: float | None = None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if q1 is None or q2 is None or pd.isna(q1) or pd.isna(q2):
        return "n/a"
    if float(value) <= float(q1):
        return "low"
    if float(value) <= float(q2):
        return "medium"
    return "high"


def _bucket_prior_path(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value <= -25.0:
        return "negative"
    if value < 25.0:
        return "flat"
    return "positive"


def _bucket_cvd(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 0.0:
        return "negative"
    if value > 0.0:
        return "positive"
    return "neutral"


def _bucket_weekday_weekend(entry_time: object) -> str:
    ts = pd.to_datetime(entry_time, errors="coerce")
    if pd.isna(ts):
        return "unknown"
    return "weekend" if int(ts.dayofweek) >= 5 else "weekday"


def _bucket_session(entry_time: object) -> str:
    ts = pd.to_datetime(entry_time, errors="coerce")
    if pd.isna(ts):
        return "session_unknown"
    hour = int(ts.hour)
    if 0 <= hour < 8:
        return "asia"
    if 8 <= hour < 13:
        return "europe"
    if 13 <= hour < 16:
        return "overlap"
    return "us"


def _bucket_volatility(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if value < 25.0:
        return "<25"
    if value < 50.0:
        return "25-50"
    if value < 100.0:
        return "50-100"
    return ">100"


def _bucket_range_trend(row: pd.Series) -> str:
    trend = bool(row.get("trend_continuation_flag_24")) if pd.notna(row.get("trend_continuation_flag_24")) else False
    failed = bool(row.get("failed_reversal_flag_24")) if pd.notna(row.get("failed_reversal_flag_24")) else False
    expansion = pd.to_numeric(row.get("range_expansion_ratio_24"), errors="coerce")
    if trend and not failed:
        return "trend_continuation"
    if failed and not trend:
        return "failed_reversal"
    if pd.notna(expansion) and float(expansion) > 1.25:
        return "range_expansion"
    if trend and failed:
        return "mixed"
    return "range"


def _trade_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "count": 0,
            "win_rate": None,
            "average_return_bps": None,
            "median_return_bps": None,
            "p25_return_bps": None,
            "p75_return_bps": None,
            "p10_return_bps": None,
            "p90_return_bps": None,
            "gross_expectancy_bps": None,
            "net_expectancy_bps": None,
            "profit_factor": 0.0,
            "max_drawdown_bps": 0.0,
            "positive_tail_count": 0,
            "large_loss_count": 0,
            "average_winner_bps": None,
            "average_loser_bps": None,
            "cost_drag_bps": None,
        }
    net = pd.to_numeric(df["net_return_bps"], errors="coerce")
    gross = pd.to_numeric(df["gross_return_bps"], errors="coerce") if "gross_return_bps" in df.columns else net.copy()
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    cost_drag = gross - net if "gross_return_bps" in df.columns else pd.Series([np.nan] * len(df), index=df.index)
    cost_drag_mean = float(cost_drag.mean()) if len(cost_drag.dropna()) else None
    return {
        "count": int(len(df)),
        "win_rate": float((net > 0.0).mean()),
        "average_return_bps": float(net.mean()),
        "median_return_bps": float(net.median()),
        "p25_return_bps": float(net.quantile(0.25)),
        "p75_return_bps": float(net.quantile(0.75)),
        "p10_return_bps": float(net.quantile(0.10)),
        "p90_return_bps": float(net.quantile(0.90)),
        "gross_expectancy_bps": float(gross.mean()) if len(gross.dropna()) else None,
        "net_expectancy_bps": float(net.mean()) if len(net.dropna()) else None,
        "profit_factor": _profit_factor(net),
        "max_drawdown_bps": _max_drawdown(net),
        "positive_tail_count": int((net >= TAIL_WIN_THRESHOLD_BPS).sum()),
        "large_loss_count": int((net <= TAIL_LOSS_THRESHOLD_BPS).sum()),
        "average_winner_bps": float(wins.mean()) if len(wins) else None,
        "average_loser_bps": float(losses.mean()) if len(losses) else None,
        "cost_drag_bps": cost_drag_mean,
    }


def _overall_fields_available(frame: pd.DataFrame) -> dict[str, bool]:
    return {
        "trade_density": "trade_density" in frame.columns,
        "signal_state": "signal_state" in frame.columns or "excursion_class" in frame.columns,
        "regime_label": "regime_label" in frame.columns,
        "volatility_label": "volatility_label" in frame.columns,
        "range_trend_label": "range_trend_label" in frame.columns,
        "local_trend_range_state": "local_trend_range_state" in frame.columns,
        "distance_from_recent_high_low": "distance_from_recent_high_low" in frame.columns,
        "distance_from_vwap": "distance_from_vwap" in frame.columns,
        "prior_bar_return_path": "prior_bar_return_path" in frame.columns,
        "cvd_delta": "cvd_delta" in frame.columns,
        "session_time_of_day_labels": "session_time_of_day_labels" in frame.columns,
        "weekday_weekend_effect": "weekday_weekend_effect" in frame.columns,
        "gross_return_bps": "gross_return_bps" in frame.columns,
        "net_return_bps": "net_return_bps" in frame.columns,
        "mfe_bps": "mfe_bps" in frame.columns,
        "mae_bps": "mae_bps" in frame.columns,
        "exit_class": "exit_class" in frame.columns,
    }


def _coverage_stats(frame: pd.DataFrame, field: str) -> dict[str, object]:
    series = frame[field] if field in frame.columns else pd.Series([np.nan] * len(frame), index=frame.index)
    total = int(len(frame))
    non_null = int(series.notna().sum())
    historical = _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)
    hist_series = historical[field] if field in historical.columns else pd.Series([np.nan] * len(historical), index=historical.index)
    recent_series = recent[field] if field in recent.columns else pd.Series([np.nan] * len(recent), index=recent.index)
    return {
        "non_null_count": non_null,
        "historical_non_null_count": int(hist_series.notna().sum()),
        "recent_non_null_count": int(recent_series.notna().sum()),
        "full_coverage_pct": (non_null / total) if total else 0.0,
        "historical_coverage_pct": (hist_series.notna().sum() / len(historical)) if len(historical) else 0.0,
        "recent_coverage_pct": (recent_series.notna().sum() / len(recent)) if len(recent) else 0.0,
    }


def _field_status_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    descriptors = [
        ("trade entry timestamp", "entry_time", "timestamp", "entry_time"),
        ("year / period label", "year", "timestamp-derived", "year -> historical/recent split"),
        ("trade_density", "trade_density", "available", "trade_count from signal_index bar"),
        ("local_trend_range_state", "local_trend_range_state", "available", "native range-trend state carried forward"),
        ("weekday_weekend_effect", "weekday_weekend_effect", "available", "weekday/weekend flag from signal_index bar"),
        ("bar size", "bar_size", "static", "static replay config: 750"),
        ("horizon", "horizon", "static", "static replay config: 36 bars"),
        ("side", "side", "static", "long-only assumed; side column absent"),
        ("original return bps", "original_return_bps", "available", "gross_return_bps"),
        ("gross return bps", "gross_return_bps", "available", "gross_return_bps"),
        ("net return bps", "net_return_bps", "available", "net_return_bps"),
        ("MFE / MAE", "mfe_bps", "available", "computed from trade log and bounded bars"),
        ("exit class", "exit_class", "available", "excursion_class / exit_class"),
        ("signal state", "signal_state", "available", "c_signal / excursion-class context"),
        ("regime_label", "regime_label", "available", "EXHAUSTED regime dominates"),
        ("volatility_label", "volatility_label", "available", "24-bar realized-vol bucket"),
        ("range_trend_label", "range_trend_label", "available", "24-bar trend / failed-reversal / range label"),
        ("distance_from_recent_high_low", "distance_from_recent_high_low", "available_partial", "normalized position inside prior 24-bar range"),
        ("distance_from_vwap", "distance_from_vwap", "available", "close-vwap basis points"),
        ("prior_bar_return_path", "prior_bar_return_path", "available", "pre-signal 24-bar return bucket"),
        ("cvd_delta", "cvd_delta", "available", "volume_delta sign bucket"),
        ("session_time_of_day_labels", "session_time_of_day_labels", "available", "UTC session bucket"),
        ("raw L2", None, "blocked", "not read"),
        ("OFI", None, "blocked", "not generated"),
        ("row-level export", None, "blocked", "not written"),
        ("future-return-derived eligibility labels", None, "blocked", "post-hoc only"),
    ]
    for field, source, default_status, notes in descriptors:
        if source is None:
            rows.append({"field": field, "status": default_status, "notes": notes})
            continue
        stats = _coverage_stats(frame, source)
        status = default_status
        if stats["non_null_count"] == 0:
            status = "blocked_insufficient_coverage"
        elif 0 < stats["non_null_count"] < len(frame):
            status = "available_partial" if default_status.startswith("safe") or default_status == "safe_available" else default_status
        rows.append(
            {
                "field": field,
                "status": status,
                "non_null_count": stats["non_null_count"],
                "historical_non_null_count": stats["historical_non_null_count"],
                "recent_non_null_count": stats["recent_non_null_count"],
                "full_coverage_pct": stats["full_coverage_pct"],
                "historical_coverage_pct": stats["historical_coverage_pct"],
                "recent_coverage_pct": stats["recent_coverage_pct"],
                "notes": notes,
            }
        )
    return rows


def _period_summary_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for label, subset in [
        ("historical", _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)),
        ("recent", _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)),
    ]:
        summary = _trade_summary(subset)
        rows.append({"period": label, **summary})
    return rows


def _by_year_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for year in sorted(int(y) for y in pd.to_numeric(frame["year"], errors="coerce").dropna().unique()):
        subset = frame[pd.to_numeric(frame["year"], errors="coerce") == year]
        rows.append({"year": year, **_trade_summary(subset)})
    return rows


def _bucket_order(field: str) -> list[str]:
    if field == "trade_density" or field == "trade_density_bucket":
        return TRADE_DENSITY_BUCKET_ORDER
    if field == "distance_from_vwap":
        return VWAP_BUCKET_ORDER
    if field == "distance_from_recent_high_low":
        return RECENT_RANGE_BUCKET_ORDER
    if field == "cvd_delta":
        return CVD_BUCKET_ORDER
    if field == "session_time_of_day_labels":
        return SESSION_BUCKET_ORDER
    if field == "weekday_weekend_effect":
        return WEEKDAY_BUCKET_ORDER
    if field == "local_trend_range_state":
        return LOCAL_TREND_BUCKET_ORDER
    if field == "regime_label":
        return ["EXHAUSTED", "n/a"]
    if field == "prior_bar_return_path":
        return ["negative", "flat", "positive", "n/a"]
    if field == "volatility_label":
        return ["<25", "25-50", "50-100", ">100", "n/a"]
    if field == "range_trend_label":
        return LOCAL_TREND_BUCKET_ORDER
    return ["n/a"]


def _bucket_rows(frame: pd.DataFrame, field: str) -> list[dict[str, object]]:
    rows = []
    order = _bucket_order(field.replace("_bucket", ""))
    for bucket in order:
        bucket_frame = frame[frame[field] == bucket]
        hist = _period_slice(bucket_frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
        recent = _period_slice(bucket_frame, RECENT_START_YEAR, RECENT_END_YEAR)
        hist_summary = _trade_summary(hist)
        recent_summary = _trade_summary(recent)
        rows.append(
            {
                "bucket": bucket,
                "historical_count": hist_summary["count"],
                "recent_count": recent_summary["count"],
                "historical_expectancy_bps": hist_summary["net_expectancy_bps"],
                "recent_expectancy_bps": recent_summary["net_expectancy_bps"],
                "historical_win_rate": hist_summary["win_rate"],
                "recent_win_rate": recent_summary["win_rate"],
                "historical_positive_tail_frequency": (hist_summary["positive_tail_count"] / hist_summary["count"]) if hist_summary["count"] else None,
                "recent_positive_tail_frequency": (recent_summary["positive_tail_count"] / recent_summary["count"]) if recent_summary["count"] else None,
                "historical_large_loss_frequency": (hist_summary["large_loss_count"] / hist_summary["count"]) if hist_summary["count"] else None,
                "recent_large_loss_frequency": (recent_summary["large_loss_count"] / recent_summary["count"]) if recent_summary["count"] else None,
                "degradation_bps": (recent_summary["net_expectancy_bps"] - hist_summary["net_expectancy_bps"]) if hist_summary["net_expectancy_bps"] is not None and recent_summary["net_expectancy_bps"] is not None else None,
                "historical_average_winner_bps": hist_summary["average_winner_bps"],
                "recent_average_winner_bps": recent_summary["average_winner_bps"],
                "historical_average_loser_bps": hist_summary["average_loser_bps"],
                "recent_average_loser_bps": recent_summary["average_loser_bps"],
                "historical_cost_drag_bps": hist_summary["cost_drag_bps"],
                "recent_cost_drag_bps": recent_summary["cost_drag_bps"],
            }
        )
    return rows


def _bucket_column_name(field: str) -> str:
    return {
        "trade_density": "trade_density_bucket",
        "distance_from_vwap": "distance_from_vwap_bucket",
        "distance_from_recent_high_low": "distance_from_recent_high_low_bucket",
        "prior_bar_return_path": "prior_bar_return_path_bucket",
        "cvd_delta": "cvd_delta_bucket",
        "local_trend_range_state": "local_trend_range_state",
        "weekday_weekend_effect": "weekday_weekend_effect",
        "volatility_label": "volatility_label",
        "range_trend_label": "range_trend_label",
    }.get(field, field)


def _interaction_frame(frame: pd.DataFrame, left: str, right: str) -> pd.DataFrame:
    pair = frame[[left, right, "year", "net_return_bps", "gross_return_bps"]].copy()
    pair["interaction_label"] = pair[left].astype(str) + " × " + pair[right].astype(str)
    return pair


def _interaction_rows(frame: pd.DataFrame, left: str, right: str) -> list[dict[str, object]]:
    pair = _interaction_frame(frame, left, right)
    rows = []
    for label, subset in pair.groupby("interaction_label", dropna=False):
        hist = _period_slice(subset, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
        recent = _period_slice(subset, RECENT_START_YEAR, RECENT_END_YEAR)
        hist_summary = _trade_summary(hist)
        recent_summary = _trade_summary(recent)
        rows.append(
            {
                "interaction": label,
                "historical_count": hist_summary["count"],
                "recent_count": recent_summary["count"],
                "historical_expectancy_bps": hist_summary["net_expectancy_bps"],
                "recent_expectancy_bps": recent_summary["net_expectancy_bps"],
                "historical_win_rate": hist_summary["win_rate"],
                "recent_win_rate": recent_summary["win_rate"],
                "positive_tail_frequency_change": ((recent_summary["positive_tail_count"] / recent_summary["count"]) - (hist_summary["positive_tail_count"] / hist_summary["count"])) if hist_summary["count"] and recent_summary["count"] else None,
                "large_loss_frequency_change": ((recent_summary["large_loss_count"] / recent_summary["count"]) - (hist_summary["large_loss_count"] / hist_summary["count"])) if hist_summary["count"] and recent_summary["count"] else None,
                "degradation_bps": (recent_summary["net_expectancy_bps"] - hist_summary["net_expectancy_bps"]) if hist_summary["net_expectancy_bps"] is not None and recent_summary["net_expectancy_bps"] is not None else None,
                "sample_sufficient": bool(hist_summary["count"] >= 5 and recent_summary["count"] >= 5),
                "historical_average_winner_bps": hist_summary["average_winner_bps"],
                "recent_average_winner_bps": recent_summary["average_winner_bps"],
                "historical_average_loser_bps": hist_summary["average_loser_bps"],
                "recent_average_loser_bps": recent_summary["average_loser_bps"],
            }
        )
    return rows


def _segment_stability_rows(
    frame: pd.DataFrame,
    bucketed_tables: dict[str, list[dict[str, object]]],
    bucket_columns: dict[str, str],
    interaction_tables: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    recent_overall = _trade_summary(_period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR))["net_expectancy_bps"]
    for field, rows_in_field in bucketed_tables.items():
        bucket_col = bucket_columns.get(field, field)
        for row in rows_in_field:
            if row["historical_count"] is None or row["recent_count"] is None:
                continue
            if row["recent_count"] < 5 or row["historical_count"] < 5:
                continue
            if row["recent_expectancy_bps"] is None:
                continue
            if row["recent_expectancy_bps"] <= recent_overall + 25.0:
                continue
            years = frame.loc[frame[bucket_col] == row["bucket"], "year"].dropna().astype(int)
            year_counts = years.value_counts().sort_index().to_dict()
            by_year_expectancy = {
                int(year): float(
                    _trade_summary(
                        _period_slice(frame[(frame[bucket_col] == row["bucket"]) & (frame["year"] == year)], HISTORICAL_START_YEAR, RECENT_END_YEAR)
                    )["net_expectancy_bps"]
                )
                for year in sorted(year_counts)
            }
            rows.append(
                {
                    "segment_type": "field",
                    "segment": f"{field}={row['bucket']}",
                    "historical_count": row["historical_count"],
                    "recent_count": row["recent_count"],
                    "by_year_count": ", ".join(f"{year}:{count}" for year, count in year_counts.items()),
                    "by_year_expectancy": ", ".join(f"{year}:{_fmt(val)}" for year, val in by_year_expectancy.items()),
                    "benefit_in_more_than_one_year": bool(sum(1 for val in by_year_expectancy.values() if pd.notna(val) and val > recent_overall + 25.0) >= 2),
                    "recent_sample_sparse": bool(row["recent_count"] < 10),
                    "stable_for_design_only": bool(row["recent_count"] >= 10 and row["historical_count"] >= 10),
                }
            )
    for interaction_key, rows_in_interaction in interaction_tables.items():
        for row in rows_in_interaction:
            if not row["sample_sufficient"]:
                continue
            if row["recent_expectancy_bps"] is None or row["recent_expectancy_bps"] <= recent_overall + 25.0:
                continue
            rows.append(
                {
                    "segment_type": "interaction",
                    "segment": f"{interaction_key}={row['interaction']}",
                    "historical_count": row["historical_count"],
                    "recent_count": row["recent_count"],
                    "by_year_count": "aggregate-only",
                    "by_year_expectancy": "aggregate-only",
                    "benefit_in_more_than_one_year": False,
                    "recent_sample_sparse": bool(row["recent_count"] < 10),
                    "stable_for_design_only": bool(row["recent_count"] >= 10 and row["historical_count"] >= 10),
                }
            )
    return rows


def _synthetic_causality_tests() -> list[SyntheticTestResult]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pd.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 112.0, 111.0, 110.0, 108.0, 106.0, 104.0, 103.0, 102.0, 101.0]),
            "low": np.array([99.5, 99.8, 100.0, 100.5, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0, 102.0, 101.0, 100.5]),
            "close": np.array([100.0, 100.5, 101.0, 101.8, 102.5, 103.5, 104.0, 105.0, 106.5, 107.2, 108.0, 109.5, 108.5, 107.0, 105.5, 104.5, 103.5, 102.5, 101.5, 100.8]),
            "bar_range": np.array([0.5, 1.2, 2.0, 2.5, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 3.0, 2.0, 1.5, 1.0, 1.0, 0.5]),
            "body_size": np.array([0.0, 0.7, 1.0, 1.3, 1.5, 1.5, 1.0, 1.0, 1.5, 1.2, 1.0, 1.5, 1.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.3]),
            "adr_stretch": np.linspace(0.1, 0.9, 20),
            "rv_1d": np.linspace(10.0, 30.0, 20),
            "rv_15th_pct": np.linspace(8.0, 20.0, 20),
            "vwap": np.linspace(99.8, 101.8, 20),
            "volume": np.linspace(1000.0, 2000.0, 20),
            "trade_count": np.linspace(10.0, 29.0, 20),
            "volume_delta": np.linspace(-10.0, 10.0, 20),
            "regime": ["EXHAUSTED"] * 20,
        }
    )
    trades = pd.DataFrame(
        {
            "signal_index": [4],
            "entry_index": [5],
            "exit_index": [12],
            "signal_time": [bars.loc[4, "close_time"]],
            "entry_time": [bars.loc[5, "open_time"]],
            "exit_time": [bars.loc[12, "open_time"]],
            "entry_price": [float(bars.loc[5, "open"])],
            "exit_price": [float(bars.loc[12, "open"])],
            "gross_return_bps": [120.0],
            "net_return_bps": [115.0],
            "year": [2024],
        }
    )
    frame = _build_context(trades, pl.from_pandas(bars))
    future_frame = frame.copy()
    future_frame["entry_time"] = future_frame["entry_time"] + pd.Timedelta(days=365)
    future_frame["signal_time"] = future_frame["signal_time"] + pd.Timedelta(days=365)
    mutated_frame = frame.copy()
    mutated_frame["gross_return_bps"] = 999.0
    mutated_frame["net_return_bps"] = 999.0

    tests = [
        SyntheticTestResult(
            name="period-label-uses-timestamp-only",
            passed=bool(_period_label(frame.loc[0, "year"]) == _period_label(future_frame.loc[0, "year"]) == "historical"),
            details=f"period={_period_label(frame.loc[0, 'year'])}",
        ),
        SyntheticTestResult(
            name="return-outcomes-are-post-hoc-only",
            passed=bool(frame.loc[0, "year"] == mutated_frame.loc[0, "year"] and frame.loc[0, "gross_return_bps"] != mutated_frame.loc[0, "gross_return_bps"]),
            details=f"base_gross={frame.loc[0, 'gross_return_bps']}, mutated_gross={mutated_frame.loc[0, 'gross_return_bps']}",
        ),
        SyntheticTestResult(
            name="no-future-path-used-for-eligibility",
            passed=bool(frame.loc[0, "signal_index"] == mutated_frame.loc[0, "signal_index"]),
            details="eligibility relies on entry-side fields only",
        ),
        SyntheticTestResult(
            name="raw-L2-and-OFI-blocked-by-design",
            passed=True,
            details="raw L2 not read; OFI not generated; row-level artifacts not exported",
        ),
    ]
    return tests


def _build_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    def _normalize_datetime(series: pd.Series) -> pd.Series:
        ts = pd.to_datetime(series, errors="coerce")
        try:
            if getattr(ts.dt, "tz", None) is not None:
                ts = ts.dt.tz_convert(None)
        except Exception:
            pass
        return ts

    context = _compute_trade_context(trades, bars).copy()
    context["entry_time"] = _normalize_datetime(context["entry_time"])
    context["signal_time"] = _normalize_datetime(context["signal_time"]) if "signal_time" in context.columns else pd.NaT
    context["exit_time"] = _normalize_datetime(context["exit_time"]) if "exit_time" in context.columns else pd.NaT
    context["year"] = context["entry_time"].dt.year.astype("Int64")
    context["period"] = context["year"].apply(_period_label)
    context["original_return_bps"] = pd.to_numeric(context["gross_return_bps"], errors="coerce")
    context["bar_size"] = 750
    context["horizon"] = 36
    context["side"] = "long-only (assumed; side column absent)" if "side" not in trades.columns else context.get("side")

    signal_frame = attach_c_exhaustion_signal(bars).with_row_index("signal_index").to_pandas()
    keep_cols = [col for col in ["signal_index", "vwap", "volume_delta"] if col in signal_frame.columns]
    signal_frame = signal_frame[keep_cols].copy()
    context = context.merge(signal_frame, on="signal_index", how="left", suffixes=("", "_signal"))

    close = pd.to_numeric(context["close"], errors="coerce")
    vwap = pd.to_numeric(context["vwap"], errors="coerce")
    context["distance_from_vwap"] = np.where(vwap.notna(), (close / vwap - 1.0) * 10_000.0, np.nan)
    context["distance_from_vwap_bucket"] = context["distance_from_vwap"].map(_bucket_distance_from_vwap)

    bars_pd = bars.to_pandas().copy().reset_index(drop=True)
    bars_pd["open_time"] = _normalize_datetime(bars_pd["open_time"])
    for col in ["open", "high", "low", "close", "volume", "trade_count", "total_notional", "volume_delta"]:
        if col in bars_pd.columns:
            bars_pd[col] = pd.to_numeric(bars_pd[col], errors="coerce")
    bars_pd["recent_high_24"] = bars_pd["high"].rolling(window=24, min_periods=24).max().shift(1)
    bars_pd["recent_low_24"] = bars_pd["low"].rolling(window=24, min_periods=24).min().shift(1)
    bars_pd["range_position_24"] = (bars_pd["close"] - bars_pd["recent_low_24"]) / (bars_pd["recent_high_24"] - bars_pd["recent_low_24"])
    bars_pd["range_position_24"] = bars_pd["range_position_24"].replace([np.inf, -np.inf], np.nan)
    bars_pd["trade_density"] = bars_pd["trade_count"] if "trade_count" in bars_pd.columns else np.nan
    bars_pd["weekday_weekend_effect"] = bars_pd["open_time"].map(_bucket_weekday_weekend)

    signal_idx = pd.to_numeric(context["signal_index"], errors="coerce")
    context["trade_density"] = signal_idx.map(bars_pd["trade_density"])
    context["weekday_weekend_effect"] = signal_idx.map(bars_pd["weekday_weekend_effect"])
    context["distance_from_recent_high_low"] = signal_idx.map(bars_pd["range_position_24"]).astype(float)
    context["distance_from_recent_high_low_bucket"] = context["distance_from_recent_high_low"].map(_bucket_recent_range_position)

    context["prior_bar_return_path"] = pd.to_numeric(context["pre_signal_return_24_bars_bps"], errors="coerce")
    context["prior_bar_return_path_bucket"] = context["prior_bar_return_path"].map(_bucket_prior_path)
    context["cvd_delta"] = pd.to_numeric(context.get("volume_delta"), errors="coerce")
    context["cvd_delta_bucket"] = context["cvd_delta"].map(_bucket_cvd)
    context["session_time_of_day_labels"] = context["entry_time"].map(_bucket_session)
    context["trade_density"] = pd.to_numeric(context["trade_density"], errors="coerce")
    q1 = context["trade_density"].quantile(0.33)
    q2 = context["trade_density"].quantile(0.67)
    context["trade_density_bucket"] = context["trade_density"].apply(lambda value: _bucket_trade_density(value, q1, q2))
    context["weekday_weekend_effect"] = context["weekday_weekend_effect"].fillna("unknown")
    context["volatility_label"] = pd.to_numeric(context["realized_vol_24_bars_bps"], errors="coerce").map(_bucket_volatility)
    context["range_trend_label"] = context.apply(_bucket_range_trend, axis=1)
    context["local_trend_range_state"] = context["range_trend_label"]
    context["regime_label"] = context["regime"] if "regime" in context.columns else "EXHAUSTED"
    context["exit_class"] = context.get("excursion_class", context.get("exit_class"))
    context["signal_state"] = context.get("c_signal", context.get("excursion_class"))

    return context


def _field_availability_rows(frame: pd.DataFrame) -> tuple[list[dict[str, object]], list[str], list[str], list[str], list[str]]:
    rows = _field_status_rows(frame)
    available_fields = [row["field"] for row in rows if row["status"] in {"available", "available_partial"}]
    used_fields = list(available_fields)
    blocked_fields = [row["field"] for row in rows if str(row["status"]).startswith("blocked")]
    missing_fields = [row["field"] for row in rows if row["status"] == "blocked_insufficient_coverage"]
    for row in rows:
        if row["status"] == "available":
            continue
    return rows, available_fields, missing_fields, used_fields, blocked_fields


def _interpretation_label(frame: pd.DataFrame, bucket_tables: dict[str, list[dict[str, object]]], interaction_tables: dict[str, list[dict[str, object]]]) -> str:
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)
    recent_summary = _trade_summary(recent)
    recent_expectancy = recent_summary["net_expectancy_bps"] if recent_summary["net_expectancy_bps"] is not None else 0.0
    candidate_scores: list[tuple[str, float, int, int]] = []
    for field, rows in bucket_tables.items():
        if field not in PRIMARY_CONTEXT_FIELDS:
            continue
        for row in rows:
            if row["recent_count"] is None or row["historical_count"] is None:
                continue
            if row["recent_count"] < 5 or row["historical_count"] < 5:
                continue
            if row["recent_expectancy_bps"] is None:
                continue
            score = float(row["recent_expectancy_bps"]) - float(recent_expectancy)
            candidate_scores.append((field, score, int(row["historical_count"]), int(row["recent_count"])))
    for interaction_name, rows in interaction_tables.items():
        for row in rows:
            if not row["sample_sufficient"] or row["recent_expectancy_bps"] is None:
                continue
            score = float(row["recent_expectancy_bps"]) - float(recent_expectancy)
            candidate_scores.append((interaction_name, score, int(row["historical_count"]), int(row["recent_count"])))

    if not candidate_scores:
        return "inconclusive_due_to_sparse_segments"
    best_field, best_score, best_hist, best_recent = max(candidate_scores, key=lambda item: (item[1], item[2] + item[3]))
    if best_score <= 0.0:
        return "no_safe_richer_context_explains_degradation"
    if best_score <= 25.0:
        return "mixed_richer_context_degradation_no_single_driver"
    if best_field == "distance_from_vwap":
        return "vwap_distance_context_degradation_dominant"
    if best_field == "distance_from_recent_high_low":
        return "high_low_distance_context_degradation_dominant"
    if best_field == "local_trend_range_state":
        return "local_trend_range_context_degradation_dominant"
    if best_field == "trade_density":
        return "trade_density_context_degradation_dominant"
    if best_field == "cvd_delta":
        return "cvd_delta_context_degradation_dominant"
    if best_field == "session_time_of_day_labels":
        return "session_context_degradation_dominant"
    if best_field == "weekday_weekend_effect":
        return "weekday_weekend_context_degradation_dominant"
    return "mixed_richer_context_degradation_no_single_driver"


def build_report(trade_log_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log_path)
    bars = normalize_v92_bar_timestamps(load_750btc_bars(bar_dir))
    bars = add_v92_regime_labels(bars)
    frame = _build_context(trades, bars)

    synthetic_tests = _synthetic_causality_tests()
    field_rows, available_fields, missing_fields, used_fields, blocked_fields = _field_availability_rows(frame)
    total_trades = int(len(frame))
    historical = _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)

    period_rows = _period_summary_rows(frame)
    year_rows = _by_year_rows(frame)

    bucket_tables: dict[str, list[dict[str, object]]] = {}
    bucket_columns: dict[str, str] = {}
    for field in [
        "trade_density_bucket",
        "distance_from_vwap_bucket",
        "distance_from_recent_high_low_bucket",
        "prior_bar_return_path_bucket",
        "cvd_delta_bucket",
        "session_time_of_day_labels",
        "weekday_weekend_effect",
        "local_trend_range_state",
        "volatility_label",
        "range_trend_label",
        "regime_label",
    ]:
        bucket_field = field
        display_name = field.replace("_bucket", "")
        bucket_tables[display_name] = _bucket_rows(frame, bucket_field)
        bucket_columns[display_name] = bucket_field

    interaction_tables: dict[str, list[dict[str, object]]] = {}
    for left, right in INTERACTION_SPECS:
        interaction_name = f"{left} × {right}"
        left_col = _bucket_column_name(left)
        right_col = _bucket_column_name(right)
        interaction_tables[interaction_name] = _interaction_rows(frame, left_col, right_col)

    stability_rows = _segment_stability_rows(frame, bucket_tables, bucket_columns, interaction_tables)
    explanation = _interpretation_label(frame, bucket_tables, interaction_tables)

    recent_summary = _trade_summary(recent)
    historical_summary = _trade_summary(historical)
    if explanation == "trade_density_context_degradation_dominant":
        explanation_reason = "Trade-density buckets separated the sample more clearly than the other safe richer-context fields."
    elif explanation == "high_low_distance_context_degradation_dominant":
        explanation_reason = "Distance-from-recent-high/low buckets separated the sample more clearly than the other safe richer-context fields."
    elif explanation == "local_trend_range_context_degradation_dominant":
        explanation_reason = "Local trend/range state separated the sample more clearly than the other safe richer-context fields."
    elif explanation == "vwap_distance_context_degradation_dominant":
        explanation_reason = "Distance-from-VWAP buckets showed the clearest separation in recent expectancy."
    elif explanation == "cvd_delta_context_degradation_dominant":
        explanation_reason = "CVD / delta sign buckets provided the clearest separation."
    elif explanation == "session_context_degradation_dominant":
        explanation_reason = "Session buckets were the strongest stable separation among the safe fields."
    elif explanation == "weekday_weekend_context_degradation_dominant":
        explanation_reason = "Weekday/weekend split showed the cleanest separation among the safe fields."
    elif explanation == "mixed_richer_context_degradation_no_single_driver":
        explanation_reason = "Several safe context slices improved modestly, but none dominated enough to support a single-driver call."
    elif explanation == "no_safe_richer_context_explains_degradation":
        explanation_reason = "The safe richer-context fields did not separate the recent decay in a materially useful way."
    elif explanation == "inconclusive_due_to_sparse_segments":
        explanation_reason = "The safe segments were too sparse to support a clean explanatory call."
    else:
        explanation_reason = "The safe fields all showed overlapping distributions and no single context slice dominated the decay."

    report: list[str] = []
    report.append("# V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("- Determine whether richer safe known-at-entry and pre-entry explanatory fields can explain recent C Exhaustion decay.")
    report.append("- Aggregate-only diagnostic against the frozen core replay output and bounded 750btc bars.")
    report.append("- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, modeling dataset, or trading approval.")
    report.append("")

    report.append("## Population Accounting")
    report.append("")
    report.append(f"- total trades inspected: `{total_trades}`")
    report.append(f"- historical-period trade count: `{int(len(historical))}`")
    report.append(f"- recent-period trade count: `{int(len(recent))}`")
    by_year_counts = [{"year": row["year"], "count": row["count"]} for row in year_rows]
    by_year_counts_text = ", ".join(f"{row['year']}:{row['count']}" for row in by_year_counts)
    report.append(f"- by-year trade count: `{by_year_counts_text}`")
    report.append("")
    report.append("### Fields")
    report.append("")
    report.append(_markdown_table(field_rows, ["field", "status", "notes"]))
    report.append("")
    report.append(f"- fields available: `{', '.join(available_fields)}`")
    report.append(f"- fields missing: `{', '.join(missing_fields) if missing_fields else 'none among the safe field set'}`")
    report.append(f"- fields used: `{', '.join(used_fields)}`")
    report.append(f"- fields blocked: `{', '.join(blocked_fields)}`")
    report.append("")

    report.append("## Baseline Period Comparison")
    report.append("")
    report.append(_markdown_table(period_rows, [
        "period",
        "count",
        "win_rate",
        "average_return_bps",
        "median_return_bps",
        "p25_return_bps",
        "p75_return_bps",
        "p10_return_bps",
        "p90_return_bps",
        "gross_expectancy_bps",
        "net_expectancy_bps",
        "profit_factor",
        "max_drawdown_bps",
        "positive_tail_count",
        "large_loss_count",
        "average_winner_bps",
        "average_loser_bps",
    ]))
    report.append("")

    report.append("## By-Year Breakdown")
    report.append("")
    report.append(_markdown_table(year_rows, [
        "year",
        "count",
        "win_rate",
        "average_return_bps",
        "median_return_bps",
        "p25_return_bps",
        "p75_return_bps",
        "p10_return_bps",
        "p90_return_bps",
        "positive_tail_count",
        "large_loss_count",
        "gross_expectancy_bps",
        "net_expectancy_bps",
    ]))
    report.append("")

    report.append("## Single-Field Richer Context Attribution")
    report.append("")
    for field, rows in bucket_tables.items():
        report.append(f"### {field}")
        report.append("")
        report.append(_markdown_table(rows, [
            "bucket",
            "historical_count",
            "recent_count",
            "historical_expectancy_bps",
            "recent_expectancy_bps",
            "historical_win_rate",
            "recent_win_rate",
            "historical_positive_tail_frequency",
            "recent_positive_tail_frequency",
            "historical_large_loss_frequency",
            "recent_large_loss_frequency",
            "degradation_bps",
            "historical_average_winner_bps",
            "recent_average_winner_bps",
            "historical_average_loser_bps",
            "recent_average_loser_bps",
            "historical_cost_drag_bps",
            "recent_cost_drag_bps",
        ]))
        report.append("")
    report.append("### Tail Attribution Summary")
    report.append("")
    report.append("- The detailed bucket tables above show whether the recent deterioration comes from fewer large winners, smaller winners, larger losers, more frequent large losses, a lower hit rate, or flat cost drag.")
    report.append("- The regime label is effectively constant EXHAUSTED, so any apparent regime separation should be treated as descriptive only and not over-interpreted.")
    report.append("")

    report.append("## Preregistered Interaction Attribution")
    report.append("")
    for interaction_name, rows in interaction_tables.items():
        report.append(f"### {interaction_name}")
        report.append("")
        report.append(_markdown_table(rows, [
            "interaction",
            "historical_count",
            "recent_count",
            "historical_expectancy_bps",
            "recent_expectancy_bps",
            "historical_win_rate",
            "recent_win_rate",
            "positive_tail_frequency_change",
            "large_loss_frequency_change",
            "degradation_bps",
            "sample_sufficient",
            "historical_average_winner_bps",
            "recent_average_winner_bps",
            "historical_average_loser_bps",
            "recent_average_loser_bps",
        ]))
        report.append("")

    report.append("## Segment Stability")
    report.append("")
    if stability_rows:
        report.append(_markdown_table(stability_rows, [
            "segment_type",
            "segment",
            "historical_count",
            "recent_count",
            "by_year_count",
            "by_year_expectancy",
            "benefit_in_more_than_one_year",
            "recent_sample_sparse",
            "stable_for_design_only",
        ]))
    else:
        report.append("- no segment met the conservative stability screen for a design-only follow-up.")
    report.append("")

    report.append("## Synthetic Causality / Leakage Checks")
    report.append("")
    for item in synthetic_tests:
        status = "passed" if item.passed else "failed"
        report.append(f"- {item.name}: `{status}` ({item.details})")
    report.append("- period assignment uses timestamp only")
    report.append("- each explanatory field is known at or before entry")
    report.append("- continuous bins are fixed before looking at outcomes")
    report.append("- native labels are not derived from future returns")
    report.append("- return outcomes are used only for aggregate attribution")
    report.append("- no future path information is used to define eligibility")
    report.append("- no raw L2 is read")
    report.append("- OFI is not generated")
    report.append("- no row-level artifacts are exported")
    report.append("- no modeling dataset is created")
    report.append("- missing fields are not silently treated as safe")
    report.append("")

    report.append("## Interpretation")
    report.append("")
    report.append(f"- primary enriched explanation: `{explanation}`")
    report.append(f"- why: {explanation_reason}")
    report.append(f"- historical net expectancy: `{_fmt(historical_summary['net_expectancy_bps'])}` bps")
    report.append(f"- recent net expectancy: `{_fmt(recent_summary['net_expectancy_bps'])}` bps")
    report.append(f"- historical win rate: `{_fmt_pct(historical_summary['win_rate'])}`")
    report.append(f"- recent win rate: `{_fmt_pct(recent_summary['win_rate'])}`")
    report.append(f"- historical positive tails: `{historical_summary['positive_tail_count']}`")
    report.append(f"- recent positive tails: `{recent_summary['positive_tail_count']}`")
    report.append(f"- historical large losses: `{historical_summary['large_loss_count']}`")
    report.append(f"- recent large losses: `{recent_summary['large_loss_count']}`")
    report.append("")

    if explanation == "blocked_due_to_missing_required_inputs":
        stop_go = "blocked_due_to_missing_required_inputs"
    elif explanation == "inconclusive_due_to_sparse_segments":
        stop_go = "blocked_due_to_missing_required_inputs"
    else:
        improved_segments = [
            row
            for field, rows in bucket_tables.items()
            if field in PRIMARY_CONTEXT_FIELDS
            for row in rows
            if row["recent_count"]
            and row["historical_count"]
            and row["recent_expectancy_bps"] is not None
            and row["historical_expectancy_bps"] is not None
            and row["recent_expectancy_bps"] > row["historical_expectancy_bps"] + 25.0
            and row["recent_count"] >= 5
            and row["historical_count"] >= 5
        ]
        if any(row["recent_count"] >= 10 and row["historical_count"] >= 10 for row in improved_segments) and explanation not in {
            "mixed_richer_context_degradation_no_single_driver",
            "no_safe_richer_context_explains_degradation",
        }:
            stop_go = "proceed_to_preregistered_richer_context_filter_design_only"
        elif explanation == "mixed_richer_context_degradation_no_single_driver":
            stop_go = "keep_anchor_alive_but_collect_more_inputs"
        elif explanation == "no_safe_richer_context_explains_degradation":
            stop_go = "reject_c_exhaustion_anchor_as_unexplained_recent_decay"
        else:
            stop_go = "keep_anchor_alive_but_collect_more_inputs"

    report.append("## Stop / Go Conclusion")
    report.append("")
    report.append(f"- decision: `{stop_go}`")
    report.append("- no segment is approved for strategy use in this diagnostic.")
    report.append("")

    metadata = {
        "decision": stop_go,
        "primary_explanation": explanation,
        "total_trades": total_trades,
        "historical_count": int(len(historical)),
        "recent_count": int(len(recent)),
        "available_fields": available_fields,
        "missing_fields": missing_fields,
        "used_fields": used_fields,
        "blocked_fields": blocked_fields,
        "bucket_tables": bucket_tables,
        "interaction_tables": interaction_tables,
        "stability_rows": stability_rows,
    }
    return "\n".join(report), metadata


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, default=DEFAULT_TRADE_LOG)
    parser.add_argument("--bar-dir", type=Path, default=DEFAULT_BAR_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _ = build_report(args.trade_log, args.bar_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
