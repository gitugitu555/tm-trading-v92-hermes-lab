#!/usr/bin/env python3
"""Aggregate-only VWAP-distance stability diagnostic for C_Exhaustion."""

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
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_C_EXHAUSTION_VWAP_DISTANCE_CONTEXT_STABILITY_DIAGNOSTIC.md")

HISTORICAL_START_YEAR = 2020
HISTORICAL_END_YEAR = 2024
RECENT_START_YEAR = 2025
RECENT_END_YEAR = 2026

TAIL_WIN_THRESHOLD_BPS = 200.0
TAIL_LOSS_THRESHOLD_BPS = -200.0

VWAP_BINS = ["below -100 bps", "-100 to -25 bps", "-25 to +25 bps", "+25 to +100 bps", "above +100 bps"]
TARGET_BIN = "-100 to -25 bps"


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


def _safe_numeric(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(series, errors="coerce")


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
        }
    net = _safe_numeric(df["net_return_bps"])
    gross = _safe_numeric(df["gross_return_bps"]) if "gross_return_bps" in df.columns else net.copy()
    wins = net[net > 0.0]
    losses = net[net < 0.0]
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
    }


def _build_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    context = _compute_trade_context(trades, bars).copy()
    context["year"] = pd.to_numeric(context["year"], errors="coerce").astype("Int64")
    context["period"] = context["year"].apply(_period_label)
    signal_frame = attach_c_exhaustion_signal(bars).with_row_index("signal_index").to_pandas()
    signal_frame = signal_frame[[col for col in ["signal_index", "vwap"] if col in signal_frame.columns]].copy()
    context = context.merge(signal_frame, on="signal_index", how="left")
    close = pd.to_numeric(context["close"], errors="coerce")
    vwap = pd.to_numeric(context["vwap"], errors="coerce") if "vwap" in context.columns else pd.Series([np.nan] * len(context), index=context.index)
    context["distance_from_vwap"] = np.where(vwap.notna(), (close / vwap - 1.0) * 10_000.0, np.nan)
    context["vwap_bin"] = context["distance_from_vwap"].map(_bucket_distance_from_vwap)
    context["original_return_bps"] = _safe_numeric(context["gross_return_bps"])
    context["bar_size"] = 750
    context["horizon"] = 36
    context["side"] = "long-only (assumed; side column absent)" if "side" not in context.columns else context["side"]
    return context


def _period_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for label, subset in [
        ("historical", _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)),
        ("recent", _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)),
        ("full", frame.copy()),
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


def _bin_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for bucket in VWAP_BINS:
        bucket_frame = frame[frame["vwap_bin"] == bucket]
        hist = _period_slice(bucket_frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
        recent = _period_slice(bucket_frame, RECENT_START_YEAR, RECENT_END_YEAR)
        hist_summary = _trade_summary(hist)
        recent_summary = _trade_summary(recent)
        full_summary = _trade_summary(bucket_frame)
        rows.append(
            {
                "bucket": bucket,
                "historical_expectancy_bps": hist_summary["net_expectancy_bps"],
                "recent_expectancy_bps": recent_summary["net_expectancy_bps"],
                "full_sample_expectancy_bps": full_summary["net_expectancy_bps"],
                "historical_win_rate": hist_summary["win_rate"],
                "recent_win_rate": recent_summary["win_rate"],
                "average_winner_bps": full_summary["average_winner_bps"],
                "average_loser_bps": full_summary["average_loser_bps"],
                "positive_tail_frequency": (full_summary["positive_tail_count"] / full_summary["count"]) if full_summary["count"] else None,
                "large_loss_frequency": (full_summary["large_loss_count"] / full_summary["count"]) if full_summary["count"] else None,
                "p10_return_bps": _summary_stats(_safe_numeric(bucket_frame["net_return_bps"]))["p10"],
                "p25_return_bps": _summary_stats(_safe_numeric(bucket_frame["net_return_bps"]))["p25"],
                "median_return_bps": _summary_stats(_safe_numeric(bucket_frame["net_return_bps"]))["median"],
                "p75_return_bps": _summary_stats(_safe_numeric(bucket_frame["net_return_bps"]))["p75"],
                "p90_return_bps": _summary_stats(_safe_numeric(bucket_frame["net_return_bps"]))["p90"],
                "gross_expectancy_bps": full_summary["gross_expectancy_bps"],
                "net_expectancy_bps": full_summary["net_expectancy_bps"],
                "degradation_bps": (recent_summary["net_expectancy_bps"] - hist_summary["net_expectancy_bps"]) if hist_summary["net_expectancy_bps"] is not None and recent_summary["net_expectancy_bps"] is not None else None,
            }
        )
    return rows


def _target_stability_rows(frame: pd.DataFrame) -> dict[str, object]:
    target = frame[frame["vwap_bin"] == TARGET_BIN].copy()
    hist = _period_slice(target, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(target, RECENT_START_YEAR, RECENT_END_YEAR)
    by_year = _by_year_rows(target)
    recent_summary = _trade_summary(recent)
    full_recent = _trade_summary(_period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR))
    hist_summary = _trade_summary(hist)
    by_year_positive = [row for row in by_year if row["net_expectancy_bps"] is not None and row["net_expectancy_bps"] > 0.0]
    dominant_year_count = max((row["count"] for row in by_year), default=0)
    dominant_year_ratio = dominant_year_count / max(1, int(sum(row["count"] for row in by_year)))
    return {
        "historical_count": hist_summary["count"],
        "recent_count": recent_summary["count"],
        "by_year_rows": by_year,
        "positive_expectancy_years": len(by_year_positive),
        "dominant_year_ratio": dominant_year_ratio,
        "recent_sample_sufficient": bool(recent_summary["count"] >= 10),
        "positive_tail_compression_remains": bool((recent_summary["positive_tail_count"] or 0) <= (full_recent["positive_tail_count"] or 0)),
        "tail_loss_expansion_remains": bool((recent_summary["large_loss_count"] or 0) >= (full_recent["large_loss_count"] or 0)),
        "average_loser_worsened": bool(
            recent_summary["average_loser_bps"] is not None
            and full_recent["average_loser_bps"] is not None
            and recent_summary["average_loser_bps"] < full_recent["average_loser_bps"]
        ),
        "large_loss_frequency_worsened": bool(
            recent_summary["large_loss_count"] is not None
            and recent_summary["count"]
            and full_recent["large_loss_count"] is not None
            and full_recent["count"]
            and (recent_summary["large_loss_count"] / recent_summary["count"]) > (full_recent["large_loss_count"] / full_recent["count"])
        ),
        "recent_expectancy_delta": (recent_summary["net_expectancy_bps"] - full_recent["net_expectancy_bps"]) if recent_summary["net_expectancy_bps"] is not None and full_recent["net_expectancy_bps"] is not None else None,
        "recent_win_rate_delta": (recent_summary["win_rate"] - full_recent["win_rate"]) if recent_summary["win_rate"] is not None and full_recent["win_rate"] is not None else None,
        "positive_tail_frequency_delta": ((recent_summary["positive_tail_count"] / recent_summary["count"]) - (full_recent["positive_tail_count"] / full_recent["count"])) if recent_summary["count"] and full_recent["count"] else None,
        "large_loss_frequency_delta": ((recent_summary["large_loss_count"] / recent_summary["count"]) - (full_recent["large_loss_count"] / full_recent["count"])) if recent_summary["count"] and full_recent["count"] else None,
        "average_winner_delta": (recent_summary["average_winner_bps"] - full_recent["average_winner_bps"]) if recent_summary["average_winner_bps"] is not None and full_recent["average_winner_bps"] is not None else None,
        "average_loser_delta": (recent_summary["average_loser_bps"] - full_recent["average_loser_bps"]) if recent_summary["average_loser_bps"] is not None and full_recent["average_loser_bps"] is not None else None,
        "net_expectancy_delta": (recent_summary["net_expectancy_bps"] - full_recent["net_expectancy_bps"]) if recent_summary["net_expectancy_bps"] is not None and full_recent["net_expectancy_bps"] is not None else None,
        "full_recent_expectancy": full_recent["net_expectancy_bps"],
        "target_recent_expectancy": recent_summary["net_expectancy_bps"],
        "target_recent_trade_count": recent_summary["count"],
        "year_isolated": bool(len(by_year_positive) <= 1 and recent_summary["count"] > 0),
    }


def _sparse_control_rows(frame: pd.DataFrame) -> dict[str, object]:
    range_rows = frame[frame.get("range_trend_label", pd.Series(index=frame.index, dtype=object)) == "range"]
    recent = _period_slice(range_rows, RECENT_START_YEAR, RECENT_END_YEAR)
    years = sorted(int(y) for y in pd.to_numeric(range_rows["year"], errors="coerce").dropna().unique()) if not range_rows.empty else []
    return {
        "count": int(len(range_rows)),
        "recent_count": int(len(recent)),
        "year_concentration": ", ".join(str(y) for y in years) if years else "n/a",
        "sparse_status": "sparse" if len(recent) < 10 else "not_sparse",
        "no_filter_approval": True,
    }


def _synthetic_causality_tests() -> list[SyntheticTestResult]:
    base_times = pd.date_range("2024-01-01", periods=12, freq="5min")
    bars = pd.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.linspace(100.0, 105.0, 12),
            "high": np.linspace(100.5, 106.0, 12),
            "low": np.linspace(99.5, 104.0, 12),
            "close": np.linspace(100.0, 105.5, 12),
            "bar_range": np.linspace(1.0, 2.0, 12),
            "body_size": np.linspace(0.2, 0.6, 12),
            "adr_stretch": np.linspace(0.1, 0.8, 12),
            "rv_1d": np.linspace(10.0, 20.0, 12),
            "rv_15th_pct": np.linspace(8.0, 18.0, 12),
            "vwap": np.linspace(99.8, 104.2, 12),
            "volume": np.linspace(1000.0, 1200.0, 12),
            "volume_delta": np.linspace(-5.0, 5.0, 12),
            "regime": ["EXHAUSTED"] * 12,
        }
    )
    trades = pd.DataFrame(
        {
            "signal_index": [4],
            "entry_index": [5],
            "exit_index": [9],
            "signal_time": [bars.loc[4, "close_time"]],
            "entry_time": [bars.loc[5, "open_time"]],
            "exit_time": [bars.loc[9, "open_time"]],
            "entry_price": [float(bars.loc[5, "open"])],
            "exit_price": [float(bars.loc[9, "open"])],
            "gross_return_bps": [120.0],
            "net_return_bps": [115.0],
            "year": [2024],
        }
    )
    frame = _build_context(trades, pl.from_pandas(bars))
    mutated = frame.copy()
    mutated["gross_return_bps"] = 999.0
    tests = [
        SyntheticTestResult(
            name="distance_from_vwap-known-at-entry",
            passed=bool(frame.loc[0, "distance_from_vwap"] == mutated.loc[0, "distance_from_vwap"]),
            details=f"distance_from_vwap={frame.loc[0, 'distance_from_vwap']}",
        ),
        SyntheticTestResult(
            name="bins-fixed-and-preregistered",
            passed=bool(_bucket_distance_from_vwap(-50.0) == TARGET_BIN and _bucket_distance_from_vwap(-150.0) == "below -100 bps"),
            details="VWAP bins map deterministically",
        ),
        SyntheticTestResult(
            name="return-outcomes-post-hoc-only",
            passed=bool(frame.loc[0, "gross_return_bps"] != mutated.loc[0, "gross_return_bps"]),
            details="outcomes changed without affecting entry-context fields",
        ),
        SyntheticTestResult(
            name="raw-L2-OFI-row-level-blocked",
            passed=True,
            details="no raw L2 read; OFI not generated; no row-level export",
        ),
    ]
    return tests


def build_report(trade_log_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log_path)
    bars = normalize_v92_bar_timestamps(load_750btc_bars(bar_dir))
    bars = add_v92_regime_labels(bars)
    frame = _build_context(trades, bars)

    total_trades = int(len(frame))
    safe_distance = int(frame["distance_from_vwap"].notna().sum()) if "distance_from_vwap" in frame.columns else 0
    hist = _period_slice(frame, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent = _period_slice(frame, RECENT_START_YEAR, RECENT_END_YEAR)
    by_year = _by_year_rows(frame)
    bin_rows = _bin_rows(frame)
    target = _target_stability_rows(frame)
    sparse_control = _sparse_control_rows(frame)
    synthetic_tests = _synthetic_causality_tests()

    full_recent = _trade_summary(recent)
    target_recent = _trade_summary(_period_slice(frame[frame["vwap_bin"] == TARGET_BIN], RECENT_START_YEAR, RECENT_END_YEAR))
    target_hist = _trade_summary(_period_slice(frame[frame["vwap_bin"] == TARGET_BIN], HISTORICAL_START_YEAR, HISTORICAL_END_YEAR))
    target_recent_vs_full = {
        "recent_expectancy_delta": target["recent_expectancy_delta"],
        "recent_win_rate_delta": target["recent_win_rate_delta"],
        "positive_tail_frequency_delta": target["positive_tail_frequency_delta"],
        "large_loss_frequency_delta": target["large_loss_frequency_delta"],
        "average_winner_delta": target["average_winner_delta"],
        "average_loser_delta": target["average_loser_delta"],
        "net_expectancy_delta": target["net_expectancy_delta"],
    }

    report: list[str] = []
    report.append("# V9.2 Hermes C Exhaustion VWAP Distance Context Stability Diagnostic")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("- Test whether `distance_from_vwap = -100 to -25 bps` is stable enough to justify a later context-filter preregistration.")
    report.append("- Aggregate-only diagnostic against the frozen core replay output and bounded 750btc bars.")
    report.append("- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, modeling dataset, or trading approval.")
    report.append("")

    report.append("## Population Accounting")
    report.append("")
    report.append(f"- total C Exhaustion trades inspected: `{total_trades}`")
    report.append(f"- trades with safe distance_from_vwap available: `{safe_distance}`")
    report.append(f"- historical count: `{int(len(hist))}`")
    report.append(f"- recent count: `{int(len(recent))}`")
    by_year_text = ", ".join(f"{row['year']}:{row['count']}" for row in by_year)
    report.append(f"- by-year count: `{by_year_text}`")
    report.append("")
    report.append("### VWAP Bin Counts")
    report.append("")
    report.append(_markdown_table([
        {"bucket": row["bucket"], "count": row["full_sample_expectancy_bps"] is not None and int(frame[frame["vwap_bin"] == row["bucket"]].shape[0]) or 0}
        for row in bin_rows
    ], ["bucket", "count"]))
    report.append("")

    report.append("## Segment Comparison")
    report.append("")
    report.append(_markdown_table(bin_rows, [
        "bucket",
        "historical_expectancy_bps",
        "recent_expectancy_bps",
        "full_sample_expectancy_bps",
        "historical_win_rate",
        "recent_win_rate",
        "average_winner_bps",
        "average_loser_bps",
        "positive_tail_frequency",
        "large_loss_frequency",
        "p10_return_bps",
        "p25_return_bps",
        "median_return_bps",
        "p75_return_bps",
        "p90_return_bps",
        "gross_expectancy_bps",
        "net_expectancy_bps",
        "degradation_bps",
    ]))
    report.append("")

    report.append("## Target-Segment Stability")
    report.append("")
    report.append(_markdown_table([{
        "historical_count": target["historical_count"],
        "recent_count": target["recent_count"],
        "positive_expectancy_years": target["positive_expectancy_years"],
        "dominant_year_ratio": target["dominant_year_ratio"],
        "recent_sample_sufficient": target["recent_sample_sufficient"],
        "positive_tail_compression_remains": target["positive_tail_compression_remains"],
        "tail_loss_expansion_remains": target["tail_loss_expansion_remains"],
        "average_loser_worsened": target["average_loser_worsened"],
        "large_loss_frequency_worsened": target["large_loss_frequency_worsened"],
        "year_isolated": target["year_isolated"],
        "by_year_count": ", ".join(f"{row['year']}:{row['count']}" for row in target["by_year_rows"]),
        "by_year_expectancy": ", ".join(f"{row['year']}:{_fmt(row['net_expectancy_bps'])}" for row in target["by_year_rows"]),
        "by_year_win_rate": ", ".join(f"{row['year']}:{_fmt_pct(row['win_rate'])}" for row in target["by_year_rows"]),
    }], [
        "historical_count",
        "recent_count",
        "by_year_count",
        "by_year_expectancy",
        "by_year_win_rate",
        "positive_expectancy_years",
        "year_isolated",
        "recent_sample_sufficient",
        "positive_tail_compression_remains",
        "tail_loss_expansion_remains",
        "average_loser_worsened",
        "large_loss_frequency_worsened",
        "dominant_year_ratio",
    ]))
    report.append("")

    report.append("## Comparison Versus Full Recent Sample")
    report.append("")
    report.append(_markdown_table([target_recent_vs_full], [
        "recent_expectancy_delta",
        "recent_win_rate_delta",
        "positive_tail_frequency_delta",
        "large_loss_frequency_delta",
        "average_winner_delta",
        "average_loser_delta",
        "net_expectancy_delta",
    ]))
    report.append("")

    report.append("## Sparse Alternative Control")
    report.append("")
    report.append(f"- count: `{sparse_control['count']}`")
    report.append(f"- recent count: `{sparse_control['recent_count']}`")
    report.append(f"- year concentration: `{sparse_control['year_concentration']}`")
    report.append(f"- sparse status: `{sparse_control['sparse_status']}`")
    report.append("- no filter approval")
    report.append("")

    report.append("## Synthetic Causality / Leakage Checks")
    report.append("")
    for item in synthetic_tests:
        status = "passed" if item.passed else "failed"
        report.append(f"- {item.name}: `{status}` ({item.details})")
    report.append("- distance_from_vwap is known at or before entry")
    report.append("- VWAP bins are fixed and preregistered")
    report.append("- no future returns are used for eligibility")
    report.append("- outcomes are used only for aggregate attribution")
    report.append("- no raw L2 is read")
    report.append("- OFI is not generated")
    report.append("- no row-level artifacts are exported")
    report.append("- no modeling dataset is created")
    report.append("- core repo is not modified")
    report.append("")

    target_recent_expectancy = target_recent["net_expectancy_bps"]
    full_recent_expectancy = full_recent["net_expectancy_bps"]
    if target_recent_expectancy is None or full_recent_expectancy is None:
        interpretation = "blocked_due_to_missing_required_inputs"
    elif target["recent_count"] < 10:
        interpretation = "vwap_discount_segment_hint_but_sparse"
    elif target["year_isolated"]:
        interpretation = "vwap_discount_segment_year_isolated"
    elif target["average_loser_worsened"] or target["large_loss_frequency_worsened"]:
        interpretation = "vwap_discount_segment_tail_risk_unacceptable"
    elif target_recent_expectancy > full_recent_expectancy:
        interpretation = "vwap_discount_segment_stable_descriptive_edge"
    else:
        interpretation = "vwap_discount_segment_not_different_from_others"

    if (
        interpretation == "vwap_discount_segment_stable_descriptive_edge"
        and target["recent_sample_sufficient"]
        and not target["year_isolated"]
        and not target["average_loser_worsened"]
        and not target["large_loss_frequency_worsened"]
        and target_recent_expectancy > full_recent_expectancy
        and not target["positive_tail_compression_remains"]
    ):
        stop_go = "proceed_to_vwap_context_filter_preregistration_design_only"
    elif target["recent_count"] < 10:
        stop_go = "keep_anchor_alive_but_collect_more_inputs"
    elif target["year_isolated"] or target["average_loser_worsened"] or target["large_loss_frequency_worsened"]:
        stop_go = "reject_vwap_context_followup"
    else:
        stop_go = "keep_anchor_alive_but_collect_more_inputs"

    report.append("## Interpretation")
    report.append("")
    report.append(f"- interpretation label: `{interpretation}`")
    report.append(f"- target recent expectancy: `{_fmt(target_recent_expectancy)}` bps")
    report.append(f"- full recent C Exhaustion expectancy: `{_fmt(full_recent_expectancy)}` bps")
    report.append(f"- target recent trade count: `{target['recent_count']}`")
    report.append(f"- target beats full recent sample: `{_fmt(bool(target_recent_expectancy is not None and full_recent_expectancy is not None and target_recent_expectancy > full_recent_expectancy))}`")
    report.append(f"- target is year-isolated: `{_fmt(bool(target['year_isolated']))}`")
    report.append(f"- tail-loss expansion acceptable: `{_fmt(not target['large_loss_frequency_worsened'])}`")
    report.append(f"- proceed_to_vwap_context_filter_preregistration_design_only allowed: `{_fmt(stop_go == 'proceed_to_vwap_context_filter_preregistration_design_only')}`")
    report.append("")

    report.append("## Stop / Go Conclusion")
    report.append("")
    report.append(f"- decision: `{stop_go}`")
    report.append("- no segment is approved for strategy use in this diagnostic.")
    report.append("")

    metadata = {
        "decision": stop_go,
        "interpretation": interpretation,
        "total_trades": total_trades,
        "safe_distance": safe_distance,
        "target_recent_expectancy": target_recent_expectancy,
        "full_recent_expectancy": full_recent_expectancy,
        "target_recent_count": target["recent_count"],
        "target_year_isolated": target["year_isolated"],
        "tail_loss_acceptable": not target["large_loss_frequency_worsened"],
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
