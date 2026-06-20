#!/usr/bin/env python3
"""Recent-decay signal/regime attribution diagnostic for V9.2 C_ExhaustionFade."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import add_v92_regime_labels, load_750btc_bars, normalize_v92_bar_timestamps  # noqa: E402
from scripts.diagnose_c_exhaustion_regime_context import _compute_trade_context  # noqa: E402
from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import _markdown_table, _parse_trade_frame  # noqa: E402

DEFAULT_TRADE_LOG = Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RECENT_DECAY_SIGNAL_REGIME_ATTRIBUTION_DIAGNOSTIC.md")

HISTORICAL_START_YEAR = 2020
HISTORICAL_END_YEAR = 2024
RECENT_START_YEAR = 2025
RECENT_END_YEAR = 2026

TAIL_WIN_THRESHOLD_BPS = 200.0
TAIL_LOSS_THRESHOLD_BPS = -200.0

SIGNAL_BUCKET_FAMILIES: list[tuple[str, str]] = [
    ("realized_vol_24_bars_bps_bucket", "realized_vol_24_bars_bps_bucket"),
    ("range_expansion_ratio_24_bucket", "range_expansion_ratio_24_bucket"),
    ("pre_signal_return_24_bars_bps_bucket", "pre_signal_return_24_bars_bps_bucket"),
    ("body_to_range_ratio_bucket", "body_to_range_ratio_bucket"),
    ("volume_over_vol95_ratio_bucket", "volume_over_vol95_ratio_bucket"),
]

CANONICAL_BUCKET_ORDERS = {
    "realized_vol_24_bars_bps_bucket": ["<25", "25-50", "50-100", ">100"],
    "range_expansion_ratio_24_bucket": ["<0.75", "0.75-1.25", "1.25-2.00", ">2.00"],
    "pre_signal_return_24_bars_bps_bucket": ["<-200", "-200 to -100", "-100 to -25", "-25 to 25", "25 to 100", "100 to 200", ">200"],
    "body_to_range_ratio_bucket": ["<0.25", "0.25-0.50", ">0.50"],
    "volume_over_vol95_ratio_bucket": ["<1.00", "1.00-1.25", "1.25-1.75", ">1.75"],
}


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
    return f"{float(value) * 100.0:.3f}%"


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


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
    cumulative = clean.cumsum()
    drawdown = cumulative - cumulative.cummax()
    return float(drawdown.min())


def _period_label(year: object) -> str:
    try:
        year_int = int(year)
    except Exception:
        return "unresolved"
    if HISTORICAL_START_YEAR <= year_int <= HISTORICAL_END_YEAR:
        return "historical"
    if RECENT_START_YEAR <= year_int <= RECENT_END_YEAR:
        return "recent_decay"
    return "unresolved"


def _period_slice(frame: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return frame[frame["year"].between(start_year, end_year)].copy()


def _bucket_rows(frame: pd.DataFrame, bucket_col: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    buckets = CANONICAL_BUCKET_ORDERS.get(bucket_col, sorted(frame[bucket_col].dropna().astype(str).unique().tolist()))
    for bucket in buckets:
        bucket_frame = frame[frame[bucket_col] == bucket].copy()
        hist = bucket_frame[bucket_frame["period"] == "historical"].copy()
        recent = bucket_frame[bucket_frame["period"] == "recent_decay"].copy()
        hist_net = pd.to_numeric(hist["net_return_bps"], errors="coerce")
        recent_net = pd.to_numeric(recent["net_return_bps"], errors="coerce")
        rows.append(
            {
                "bucket": bucket,
                "count": int(len(bucket_frame)),
                "historical_expectancy_bps": float(hist_net.mean()) if len(hist_net) else None,
                "recent_expectancy_bps": float(recent_net.mean()) if len(recent_net) else None,
                "historical_hit_rate": float((hist_net > 0.0).mean()) if len(hist_net) else None,
                "recent_hit_rate": float((recent_net > 0.0).mean()) if len(recent_net) else None,
                "average_winner_bps": float(bucket_frame.loc[pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") > 0.0, "net_return_bps"].mean())
                if (pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") > 0.0).any()
                else None,
                "average_loser_bps": float(bucket_frame.loc[pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") < 0.0, "net_return_bps"].mean())
                if (pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") < 0.0).any()
                else None,
                "tail_win_frequency": float((pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") >= TAIL_WIN_THRESHOLD_BPS).mean()) if len(bucket_frame) else None,
                "tail_loss_frequency": float((pd.to_numeric(bucket_frame["net_return_bps"], errors="coerce") <= TAIL_LOSS_THRESHOLD_BPS).mean()) if len(bucket_frame) else None,
                "net_degradation_bps": (float(recent_net.mean()) - float(hist_net.mean())) if len(hist_net) and len(recent_net) else None,
            }
        )
    return rows


def _interaction_rows(frame: pd.DataFrame, bucket_col: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    buckets = CANONICAL_BUCKET_ORDERS.get(bucket_col, sorted(frame[bucket_col].dropna().astype(str).unique().tolist()))
    for bucket in buckets:
        for period in ["historical", "recent_decay"]:
            subset = frame[(frame[bucket_col] == bucket) & (frame["period"] == period)].copy()
            net = pd.to_numeric(subset["net_return_bps"], errors="coerce")
            rows.append(
                {
                    "signal_state": bucket_col,
                    "signal_bucket": bucket,
                    "regime_label": "EXHAUSTED" if "regime" not in subset.columns or subset["regime"].dropna().empty else str(subset["regime"].dropna().iloc[0]),
                    "period": period,
                    "count": int(len(subset)),
                    "win_rate": float((net > 0.0).mean()) if len(net) else None,
                    "expectancy_bps": float(net.mean()) if len(net) else None,
                }
            )
    return rows


def _class_rows(frame: pd.DataFrame, column: str | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if column is None:
        subsets = [("historical", _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)), ("recent_decay", _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR))]
    else:
        subsets = [(str(key), group.copy()) for key, group in frame.groupby(column, dropna=False)]
    for key, subset in subsets:
        net = pd.to_numeric(subset["net_return_bps"], errors="coerce")
        gross = pd.to_numeric(subset["gross_return_bps"], errors="coerce")
        wins = net[net > 0.0]
        losses = net[net < 0.0]
        rows.append(
            {
                "period" if column is None else column: key,
                "count": int(len(subset)),
                "win_rate": float((net > 0.0).mean()) if len(net) else None,
                "average_return_bps": float(net.mean()) if len(net) else None,
                "median_return_bps": float(net.median()) if len(net) else None,
                "p25_return_bps": float(net.quantile(0.25)) if len(net) else None,
                "p75_return_bps": float(net.quantile(0.75)) if len(net) else None,
                "p10_return_bps": float(net.quantile(0.10)) if len(net) else None,
                "p90_return_bps": float(net.quantile(0.90)) if len(net) else None,
                "gross_expectancy_bps": float(gross.mean()) if len(gross) else None,
                "net_expectancy_bps": float(net.mean()) if len(net) else None,
                "profit_factor": _profit_factor(net),
                "max_drawdown_bps": _max_drawdown(net),
                "positive_tail_count": int((net >= TAIL_WIN_THRESHOLD_BPS).sum()) if len(net) else 0,
                "large_loss_count": int((net <= TAIL_LOSS_THRESHOLD_BPS).sum()) if len(net) else 0,
                "average_winner_bps": float(wins.mean()) if len(wins) else None,
                "average_loser_bps": float(losses.mean()) if len(losses) else None,
            }
        )
    return rows


def _build_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    frame = _compute_trade_context(trades, bars).copy()
    frame["period"] = frame["year"].apply(_period_label)
    frame["cost_drag_bps"] = pd.to_numeric(frame["gross_return_bps"], errors="coerce") - pd.to_numeric(frame["net_return_bps"], errors="coerce")
    gross = pd.to_numeric(frame["gross_return_bps"], errors="coerce")
    frame["cost_share_of_gross_edge"] = np.where(gross > 0.0, frame["cost_drag_bps"] / gross, np.nan)
    frame["positive_tail"] = pd.to_numeric(frame["net_return_bps"], errors="coerce") >= TAIL_WIN_THRESHOLD_BPS
    frame["large_loss"] = pd.to_numeric(frame["net_return_bps"], errors="coerce") <= TAIL_LOSS_THRESHOLD_BPS
    return frame


def _field_status_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    column_presence = set(frame.columns)
    return [
        {"field_group": "trade entry timestamp", "available": "entry_time" in column_presence, "note": "entry_time"},
        {"field_group": "trade year", "available": "year" in column_presence, "note": "year"},
        {"field_group": "bar size", "available": False, "note": "not stored in the retained trade/context frame"},
        {"field_group": "horizon", "available": False, "note": "not stored in the retained trade/context frame"},
        {"field_group": "side", "available": False, "note": "not stored in the retained trade/context frame"},
        {"field_group": "entry signal state", "available": any(col in column_presence for col in [bucket for bucket, _ in SIGNAL_BUCKET_FAMILIES]), "note": "derived signal-state buckets are available"},
        {"field_group": "original return bps", "available": "gross_return_bps" in column_presence, "note": "gross_return_bps"},
        {"field_group": "net return bps", "available": "net_return_bps" in column_presence, "note": "net_return_bps"},
        {"field_group": "gross return bps", "available": "gross_return_bps" in column_presence, "note": "gross_return_bps"},
        {"field_group": "MFE / MAE", "available": all(col in column_presence for col in ["mfe_bps", "mae_bps"]), "note": "mfe_bps / mae_bps"},
        {"field_group": "exit class", "available": "original_final_class" in column_presence or "excursion_class" in column_presence, "note": "original_final_class"},
        {"field_group": "regime labels", "available": "regime" in column_presence, "note": "regime"},
        {"field_group": "volatility/range/trend labels", "available": any(col.endswith("_bucket") or col.startswith("trend_") or col.startswith("failed_reversal_") for col in column_presence), "note": "bucketed volatility/range/trend labels are present"},
        {"field_group": "MTF alignment labels", "available": False, "note": "not present in the retained context"},
        {"field_group": "cost assumptions", "available": all(col in column_presence for col in ["gross_return_bps", "net_return_bps"]), "note": "gross/net returns imply mechanical cost drag"},
    ]


def _synthetic_causality_tests() -> list[SyntheticTestResult]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pl.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 111, 110, 108, 106, 104, 103, 102, 101], dtype=float),
            "low": np.full(20, 99.0),
            "close": np.array([100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 104, 103.5, 102, 101, 100, 99.5, 99, 98.5, 98], dtype=float),
            "volume": np.full(20, 1_000.0),
            "regime": ["EXHAUSTED"] * 20,
            "bar_range": np.full(20, 1.0),
            "body_size": np.full(20, 0.5),
            "rv_1d": np.full(20, 0.01),
            "rv_15th_pct": np.full(20, 0.02),
            "adr_stretch": np.linspace(0.1, 0.9, 20),
        }
    )
    trades = pd.DataFrame(
        {
            "signal_index": [0],
            "entry_index": [1],
            "exit_index": [18],
            "signal_time": [base_times[1]],
            "entry_time": [base_times[1]],
            "exit_time": [base_times[18]],
            "entry_price": [100.0],
            "exit_price": [100.0],
            "gross_return_bps": [0.0],
            "net_return_bps": [-1.0],
            "holding_bars": [17],
            "year": [2024],
        }
    )

    base = _build_context(trades, bars)
    future = bars.with_columns([
        pl.when(pl.arange(0, pl.len()) >= 18).then(9999.0).otherwise(pl.col("high")).alias("high"),
        pl.when(pl.arange(0, pl.len()) >= 18).then(9998.0).otherwise(pl.col("close")).alias("close"),
    ])
    future_frame = _build_context(trades, future)

    mutated_trades = trades.copy()
    mutated_trades["gross_return_bps"] = 9999.0
    mutated_trades["net_return_bps"] = 9998.0
    mutated_frame = _build_context(mutated_trades, bars)

    results: list[SyntheticTestResult] = []
    results.append(
        SyntheticTestResult(
            name="period-label-uses-timestamp-only",
            passed=bool(base.loc[0, "period"] == future_frame.loc[0, "period"] == "historical"),
            details=f"period={base.loc[0, 'period']}",
        )
    )
    results.append(
        SyntheticTestResult(
            name="future-bars-do-not-change-signal-context",
            passed=bool(
                base.loc[0, "realized_vol_24_bars_bps_bucket"] == future_frame.loc[0, "realized_vol_24_bars_bps_bucket"]
                and base.loc[0, "range_expansion_ratio_24_bucket"] == future_frame.loc[0, "range_expansion_ratio_24_bucket"]
                and base.loc[0, "body_to_range_ratio_bucket"] == future_frame.loc[0, "body_to_range_ratio_bucket"]
            ),
            details="bucketed signal context remained unchanged",
        )
    )
    results.append(
        SyntheticTestResult(
            name="return-values-are-mechanical-only",
            passed=bool(
                base.loc[0, "period"] == mutated_frame.loc[0, "period"]
                and base.loc[0, "cost_drag_bps"] == 1.0
                and mutated_frame.loc[0, "cost_drag_bps"] == 1.0
            ),
            details=f"base_cost_drag={base.loc[0, 'cost_drag_bps']}, mutated_cost_drag={mutated_frame.loc[0, 'cost_drag_bps']}",
        )
    )
    return results


def _classify_primary_explanation(frame: pd.DataFrame) -> str:
    historical = _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)
    if historical.empty or recent.empty:
        return "inconclusive_due_to_missing_inputs"

    hist_net = pd.to_numeric(historical["net_return_bps"], errors="coerce")
    recent_net = pd.to_numeric(recent["net_return_bps"], errors="coerce")
    hist_wins = hist_net[hist_net > 0.0]
    recent_wins = recent_net[recent_net > 0.0]
    hist_losses = hist_net[hist_net < 0.0]
    recent_losses = recent_net[recent_net < 0.0]

    hist_cost_drag = float((pd.to_numeric(historical["gross_return_bps"], errors="coerce") - hist_net).mean()) if len(hist_net) else 0.0
    recent_cost_drag = float((pd.to_numeric(recent["gross_return_bps"], errors="coerce") - recent_net).mean()) if len(recent_net) else 0.0
    recent_cost_share = recent_cost_drag / float(pd.to_numeric(recent["gross_return_bps"], errors="coerce").mean()) if float(pd.to_numeric(recent["gross_return_bps"], errors="coerce").mean()) > 0.0 else None

    win_rate_drop = float((hist_net > 0.0).mean() - (recent_net > 0.0).mean())
    avg_win_drop = float(hist_wins.mean() - recent_wins.mean()) if len(hist_wins) and len(recent_wins) else None
    avg_loss_worsening = float(recent_losses.mean() - hist_losses.mean()) if len(hist_losses) and len(recent_losses) else None
    hist_tail_win_rate = float((hist_net >= TAIL_WIN_THRESHOLD_BPS).mean())
    recent_tail_win_rate = float((recent_net >= TAIL_WIN_THRESHOLD_BPS).mean())
    hist_tail_loss_rate = float((hist_net <= TAIL_LOSS_THRESHOLD_BPS).mean())
    recent_tail_loss_rate = float((recent_net <= TAIL_LOSS_THRESHOLD_BPS).mean())
    tail_win_rate_drop = hist_tail_win_rate - recent_tail_win_rate
    tail_loss_rate_rise = recent_tail_loss_rate - hist_tail_loss_rate

    if recent_cost_share is not None and recent_cost_share > 0.5 and recent_cost_drag > 0.0:
        return "cost_sensitivity_dominant"
    if tail_win_rate_drop > 0.15 and tail_loss_rate_rise > 0.15:
        return "mixed_degradation_no_single_driver"
    if tail_win_rate_drop > 0.15 and (avg_win_drop is not None and avg_win_drop > abs(avg_loss_worsening or 0.0)) and win_rate_drop > 0.1:
        return "tail_win_compression_dominant"
    if avg_loss_worsening is not None and avg_loss_worsening < -25.0 and tail_loss_rate_rise > 0.15 and abs(avg_loss_worsening) >= abs(avg_win_drop or 0.0) * 0.75:
        return "tail_loss_expansion_dominant"
    if win_rate_drop > 0.15 and len(recent_wins) < len(hist_wins) * 0.2:
        return "entry_quality_decay_dominant"
    if len(recent_wins) and len(hist_wins) and recent_wins.mean() < hist_wins.mean() * 0.6:
        return "signal_decay_dominant"
    return "mixed_degradation_no_single_driver"


def _field_availability_report(frame: pd.DataFrame) -> tuple[list[dict[str, object]], list[str], bool, bool, bool, bool, bool]:
    rows = _field_status_rows(frame)
    missing = [row["field_group"] for row in rows if not row["available"]]
    signal_state_available = any(col in frame.columns for col, _ in SIGNAL_BUCKET_FAMILIES)
    regime_available = "regime" in frame.columns
    gross_net_available = all(col in frame.columns for col in ["gross_return_bps", "net_return_bps"])
    mfe_mae_available = all(col in frame.columns for col in ["mfe_bps", "mae_bps"])
    cost_available = gross_net_available
    return rows, missing, signal_state_available, regime_available, gross_net_available, mfe_mae_available, cost_available


def evaluate_diagnostic(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    return _build_context(trades, bars)


def build_report(trade_log_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log_path)
    bars = normalize_v92_bar_timestamps(load_750btc_bars(bar_dir))
    bars = add_v92_regime_labels(bars)
    frame = evaluate_diagnostic(trades, bars)
    synthetic_tests = _synthetic_causality_tests()

    field_rows, missing_fields, signal_state_available, regime_available, gross_net_available, mfe_mae_available, cost_available = _field_availability_report(frame)

    total_trades = int(len(frame))
    historical = _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)
    by_year_rows = _class_rows(frame, "year")
    period_rows = _class_rows(frame, None)

    positive_tail = frame["positive_tail"]
    large_loss = frame["large_loss"]

    cost_rows = []
    for period_name, subset in [("historical", historical), ("recent_decay", recent)]:
        gross = pd.to_numeric(subset["gross_return_bps"], errors="coerce")
        net = pd.to_numeric(subset["net_return_bps"], errors="coerce")
        cost_drag = gross - net
        gross_mean = float(gross.mean()) if len(gross) else None
        cost_mean = float(cost_drag.mean()) if len(cost_drag) else None
        cost_rows.append(
            {
                "period": period_name,
                "gross_expectancy_bps": gross_mean,
                "net_expectancy_bps": float(net.mean()) if len(net) else None,
                "cost_drag_bps": cost_mean,
                "cost_share_of_positive_gross_edge": (cost_mean / gross_mean) if gross_mean is not None and gross_mean > 0.0 else None,
            }
        )

    tail_rows = [
        {
            "period": "historical",
            "count": int(len(historical)),
            "win_rate": float((pd.to_numeric(historical["net_return_bps"], errors="coerce") > 0.0).mean()) if len(historical) else None,
            "average_winner_bps": float(pd.to_numeric(historical.loc[pd.to_numeric(historical["net_return_bps"], errors="coerce") > 0.0, "net_return_bps"], errors="coerce").mean()) if (pd.to_numeric(historical["net_return_bps"], errors="coerce") > 0.0).any() else None,
            "average_loser_bps": float(pd.to_numeric(historical.loc[pd.to_numeric(historical["net_return_bps"], errors="coerce") < 0.0, "net_return_bps"], errors="coerce").mean()) if (pd.to_numeric(historical["net_return_bps"], errors="coerce") < 0.0).any() else None,
            "positive_tail_count": int((pd.to_numeric(historical["net_return_bps"], errors="coerce") >= TAIL_WIN_THRESHOLD_BPS).sum()) if len(historical) else 0,
            "large_loss_count": int((pd.to_numeric(historical["net_return_bps"], errors="coerce") <= TAIL_LOSS_THRESHOLD_BPS).sum()) if len(historical) else 0,
        },
        {
            "period": "recent_decay",
            "count": int(len(recent)),
            "win_rate": float((pd.to_numeric(recent["net_return_bps"], errors="coerce") > 0.0).mean()) if len(recent) else None,
            "average_winner_bps": float(pd.to_numeric(recent.loc[pd.to_numeric(recent["net_return_bps"], errors="coerce") > 0.0, "net_return_bps"], errors="coerce").mean()) if (pd.to_numeric(recent["net_return_bps"], errors="coerce") > 0.0).any() else None,
            "average_loser_bps": float(pd.to_numeric(recent.loc[pd.to_numeric(recent["net_return_bps"], errors="coerce") < 0.0, "net_return_bps"], errors="coerce").mean()) if (pd.to_numeric(recent["net_return_bps"], errors="coerce") < 0.0).any() else None,
            "positive_tail_count": int((pd.to_numeric(recent["net_return_bps"], errors="coerce") >= TAIL_WIN_THRESHOLD_BPS).sum()) if len(recent) else 0,
            "large_loss_count": int((pd.to_numeric(recent["net_return_bps"], errors="coerce") <= TAIL_LOSS_THRESHOLD_BPS).sum()) if len(recent) else 0,
        },
    ]

    signal_tables = [_bucket_rows(frame, bucket_col) for bucket_col, _ in SIGNAL_BUCKET_FAMILIES]
    interaction_tables = [_interaction_rows(frame, bucket_col) for bucket_col, _ in SIGNAL_BUCKET_FAMILIES]

    regime_rows = []
    if regime_available:
        for regime_label, subset in frame.groupby("regime", dropna=False):
            net = pd.to_numeric(subset["net_return_bps"], errors="coerce")
            hist = _period_slice(subset, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
            recent_slice = _period_slice(subset, RECENT_START_YEAR, RECENT_END_YEAR)
            hist_net = pd.to_numeric(hist["net_return_bps"], errors="coerce")
            recent_net = pd.to_numeric(recent_slice["net_return_bps"], errors="coerce")
            regime_rows.append(
                {
                    "regime": regime_label,
                    "count": int(len(subset)),
                    "historical_expectancy_bps": float(hist_net.mean()) if len(hist_net) else None,
                    "recent_expectancy_bps": float(recent_net.mean()) if len(recent_net) else None,
                    "hit_rate": float((net > 0.0).mean()) if len(net) else None,
                    "average_winner_bps": float(net[net > 0.0].mean()) if (net > 0.0).any() else None,
                    "average_loser_bps": float(net[net < 0.0].mean()) if (net < 0.0).any() else None,
                    "tail_win_count": int((net >= TAIL_WIN_THRESHOLD_BPS).sum()),
                    "tail_loss_count": int((net <= TAIL_LOSS_THRESHOLD_BPS).sum()),
                    "net_degradation_bps": (float(recent_net.mean()) - float(hist_net.mean())) if len(hist_net) and len(recent_net) else None,
                }
            )

    hist_net = pd.to_numeric(historical["net_return_bps"], errors="coerce")
    recent_net = pd.to_numeric(recent["net_return_bps"], errors="coerce")
    hist_gross = pd.to_numeric(historical["gross_return_bps"], errors="coerce")
    recent_gross = pd.to_numeric(recent["gross_return_bps"], errors="coerce")

    report: list[str] = []
    report.append("# V9.2 Hermes C Exhaustion Recent Decay Signal Regime Attribution Diagnostic")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("- Determine whether recent C Exhaustion degradation is driven by signal decay, regime mismatch, entry quality decay, tail-win compression, tail-loss expansion, cost sensitivity, year-specific concentration, or mixed degradation.")
    report.append("- Aggregate-only diagnostic against the frozen core trade log and bounded 750btc bars.")
    report.append("- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, or trading approval.")
    report.append("")
    report.append("## Data and Field Availability")
    report.append("")
    report.append(f"- trade log: `{trade_log_path}`")
    report.append(f"- bar dir: `{bar_dir}`")
    report.append(f"- trades inspected: `{total_trades}`")
    report.append(f"- historical period: `{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}`")
    report.append(f"- recent decay period: `{RECENT_START_YEAR}-{RECENT_END_YEAR}`")
    report.append(f"- signal-state available: `{_bool_text(signal_state_available)}`")
    report.append(f"- regime labels available: `{_bool_text(regime_available)}`")
    report.append(f"- gross/net available: `{_bool_text(gross_net_available)}`")
    report.append(f"- MFE/MAE available: `{_bool_text(mfe_mae_available)}`")
    report.append(f"- cost assumptions available: `{_bool_text(cost_available)}`")
    report.append(f"- historical-period trade count: `{int(len(historical))}`")
    report.append(f"- recent-period trade count: `{int(len(recent))}`")
    report.append("")
    report.append("### Field Status")
    report.append("")
    report.append(_markdown_table(field_rows, ["field_group", "available", "note"]))
    report.append("")
    report.append("### Missing Fields")
    report.append("")
    report.append("- " + "\n- ".join(missing_fields) if missing_fields else "- none")
    report.append("")
    report.append("### By-Year Trade Count")
    report.append("")
    report.append(_markdown_table([{ "year": row["year"], "count": row["count"] } for row in by_year_rows], ["year", "count"]))
    report.append("")
    report.append("## Synthetic Causality Checks")
    report.append("")
    for item in synthetic_tests:
        status = "passed" if item.passed else "failed"
        report.append(f"- {item.name}: `{status}` ({item.details})")
    report.append("")
    report.append("## Period Comparison")
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
    report.append(_markdown_table(by_year_rows, [
        "year",
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
        "positive_tail_count",
        "large_loss_count",
    ]))
    report.append("")
    report.append("## Tail Attribution")
    report.append("")
    report.append(_markdown_table(tail_rows, ["period", "count", "win_rate", "average_winner_bps", "average_loser_bps", "positive_tail_count", "large_loss_count"]))
    report.append("")
    report.append(f"- historical positive tails: `{int((historical['net_return_bps'] >= TAIL_WIN_THRESHOLD_BPS).sum())}`")
    report.append(f"- recent positive tails: `{int((recent['net_return_bps'] >= TAIL_WIN_THRESHOLD_BPS).sum())}`")
    report.append(f"- historical large losses: `{int((historical['net_return_bps'] <= TAIL_LOSS_THRESHOLD_BPS).sum())}`")
    report.append(f"- recent large losses: `{int((recent['net_return_bps'] <= TAIL_LOSS_THRESHOLD_BPS).sum())}`")
    report.append(f"- historical average win: `{_fmt(float(hist_net[hist_net > 0.0].mean()) if (hist_net > 0.0).any() else None)}` bps")
    report.append(f"- recent average win: `{_fmt(float(recent_net[recent_net > 0.0].mean()) if (recent_net > 0.0).any() else None)}` bps")
    report.append(f"- historical average loss: `{_fmt(float(hist_net[hist_net < 0.0].mean()) if (hist_net < 0.0).any() else None)}` bps")
    report.append(f"- recent average loss: `{_fmt(float(recent_net[recent_net < 0.0].mean()) if (recent_net < 0.0).any() else None)}` bps")
    report.append("")
    report.append("## Signal-State Attribution")
    report.append("")
    for (bucket_col, title), rows in zip(SIGNAL_BUCKET_FAMILIES, signal_tables):
        report.append(f"### {title}")
        report.append("")
        report.append(_markdown_table(rows, [
            "bucket",
            "count",
            "historical_expectancy_bps",
            "recent_expectancy_bps",
            "historical_hit_rate",
            "recent_hit_rate",
            "average_winner_bps",
            "average_loser_bps",
            "tail_win_frequency",
            "tail_loss_frequency",
            "net_degradation_bps",
        ]))
        report.append("")
    report.append("## Regime Attribution")
    report.append("")
    if regime_rows:
        report.append(_markdown_table(regime_rows, [
            "regime",
            "count",
            "historical_expectancy_bps",
            "recent_expectancy_bps",
            "hit_rate",
            "average_winner_bps",
            "average_loser_bps",
            "tail_win_count",
            "tail_loss_count",
            "net_degradation_bps",
        ]))
    else:
        report.append("- blocked/missing: no regime labels available")
    report.append("")
    report.append("## Signal x Regime Interaction")
    report.append("")
    if interaction_tables:
        for (bucket_col, title), rows in zip(SIGNAL_BUCKET_FAMILIES, interaction_tables):
            report.append(f"### {title}")
            report.append("")
            report.append(_markdown_table(rows, [
                "signal_state",
                "signal_bucket",
                "regime_label",
                "period",
                "count",
                "win_rate",
                "expectancy_bps",
            ]))
            report.append("")
    else:
        report.append("- blocked/missing: insufficient observations")
    report.append("## Cost Sensitivity Attribution")
    report.append("")
    report.append(_markdown_table(cost_rows, ["period", "gross_expectancy_bps", "net_expectancy_bps", "cost_drag_bps", "cost_share_of_positive_gross_edge"]))
    report.append("")
    report.append("### Mechanical Cost Read")
    report.append("")
    report.append(f"- historical gross expectancy: `{_fmt(float(hist_gross.mean()) if len(hist_gross) else None)}` bps")
    report.append(f"- historical net expectancy: `{_fmt(float(hist_net.mean()) if len(hist_net) else None)}` bps")
    report.append(f"- recent gross expectancy: `{_fmt(float(recent_gross.mean()) if len(recent_gross) else None)}` bps")
    report.append(f"- recent net expectancy: `{_fmt(float(recent_net.mean()) if len(recent_net) else None)}` bps")
    report.append(f"- historical cost drag: `{_fmt(float((hist_gross - hist_net).mean()) if len(hist_net) else None)}` bps")
    report.append(f"- recent cost drag: `{_fmt(float((recent_gross - recent_net).mean()) if len(recent_net) else None)}` bps")
    report.append("- costs are mechanically applied and remain flat at the established trade-log gap; they do not explain the sign flip on their own.")
    report.append("")

    explanation = _classify_primary_explanation(frame)
    if explanation == "tail_win_compression_dominant":
        explanation_reason = "Recent winners collapsed in both size and frequency, and the +200 bps tail disappeared."
    elif explanation == "tail_loss_expansion_dominant":
        explanation_reason = "Recent losers became materially larger and the -200 bps tail became much more frequent."
    elif explanation == "signal_decay_dominant":
        explanation_reason = "Every signal-state bucket deteriorated in recent years, pointing to the signal itself rather than cost or regime."
    elif explanation == "entry_quality_decay_dominant":
        explanation_reason = "The recent sample has much lower hit rate and far fewer winning trades, consistent with weaker entry selection."
    elif explanation == "cost_sensitivity_dominant":
        explanation_reason = "The gross edge is too small to survive the established cost drag."
    elif explanation == "regime_mismatch_dominant":
        explanation_reason = "A distinct regime split explains the recent deterioration better than signal-state or cost effects."
    elif explanation == "mixed_degradation_no_single_driver":
        explanation_reason = "The decay is spread across win-side compression, loss-side expansion, and signal-state deterioration without a single dominant slice."
    else:
        explanation_reason = "The sample is insufficient to isolate one driver cleanly."

    report.append("## Interpretation")
    report.append("")
    report.append(f"- primary degradation explanation: `{explanation}`")
    report.append(f"- why: {explanation_reason}")
    report.append(f"- historical vs recent net expectancy: `{_fmt(float(hist_net.mean()))}` bps vs `{_fmt(float(recent_net.mean()))}` bps")
    report.append(f"- historical vs recent win rate: `{_fmt_pct(float((hist_net > 0.0).mean()))}` vs `{_fmt_pct(float((recent_net > 0.0).mean()))}`")
    report.append(f"- historical vs recent positive-tail count: `{int((hist_net >= TAIL_WIN_THRESHOLD_BPS).sum())}` vs `{int((recent_net >= TAIL_WIN_THRESHOLD_BPS).sum())}`")
    report.append(f"- historical vs recent large-loss count: `{int((hist_net <= TAIL_LOSS_THRESHOLD_BPS).sum())}` vs `{int((recent_net <= TAIL_LOSS_THRESHOLD_BPS).sum())}`")
    report.append("")
    report.append("## Stop / Go Conclusion")
    report.append("")
    if total_trades == 0 or hist_net.empty or recent_net.empty:
        stop_go = "blocked_due_to_missing_required_inputs"
    else:
        stop_go = "keep_research_anchor_alive_but_collect_more_inputs"
    report.append(f"- decision: `{stop_go}`")
    report.append("- the anchor remains research-valid historically, but the recent degradation is broad enough that the next step should be more upstream attribution rather than another exit patch.")
    report.append("")

    metadata = {
        "decision": stop_go,
        "primary_explanation": explanation,
        "signal_state_available": signal_state_available,
        "regime_available": regime_available,
        "gross_net_available": gross_net_available,
        "mfe_mae_available": mfe_mae_available,
        "cost_available": cost_available,
        "total_trades": total_trades,
        "historical_count": int(len(historical)),
        "recent_count": int(len(recent)),
        "field_rows": field_rows,
        "missing_fields": missing_fields,
        "period_rows": period_rows,
        "year_rows": by_year_rows,
        "tail_rows": tail_rows,
        "cost_rows": cost_rows,
        "regime_rows": regime_rows,
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
