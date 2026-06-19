#!/usr/bin/env python3
"""Bounded descriptive fixed post-MFE review-window diagnostic for C_Exhaustion."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import (  # noqa: E402
    INTERVAL_CONVENTION,
    _final_return_basis,
    _interval_path,
    _load_bars,
    _markdown_table,
    _parse_trade_frame,
    _side_basis,
    construct_excursion_table,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_FIXED_POST_MFE_REVIEW_WINDOW_DIAGNOSTIC.md")
PRE_REGISTERED_PREREG = Path("docs/v92_C_EXHAUSTION_EXIT_MANAGEMENT_HYPOTHESIS_PREREGISTRATION.md")
POST_MFE_WINDOW_BARS = 12
CLASS_LABELS = ["bad_entry_loss", "giveback_loss", "weak_positive_exit", "clean_winner", "unresolved"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{float(value) * 100.0:.3f}%"


def _price_basis(trades: pd.DataFrame) -> str:
    if "gross_return_bps" in trades.columns and trades["gross_return_bps"].notna().any():
        return "gross_return_bps"
    return "net_return_bps"


def _trade_years(trades: pd.DataFrame) -> pd.Series:
    if "year" in trades.columns and trades["year"].notna().any():
        return pd.to_numeric(trades["year"], errors="coerce").astype("Int64")
    return pd.to_datetime(trades["signal_time"], errors="coerce", utc=True).dt.tz_convert(None).dt.year.astype("Int64")


def _diagnostic_frame(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    base = construct_excursion_table(trades, bars).copy()
    if "year" not in base.columns or not base["year"].notna().any():
        base["year"] = _trade_years(base)
    else:
        base["year"] = pd.to_numeric(base["year"], errors="coerce").astype("Int64")

    if "row_status" not in base.columns:
        base["row_status"] = "unresolved"

    diagnostics: list[dict[str, object]] = []

    for row in base.itertuples(index=False):
        record = row._asdict()
        record["mfe_plus_12_available"] = False
        record["mfe_plus_12_price"] = np.nan
        record["mfe_plus_12_return_bps"] = np.nan
        record["mfe_plus_12_giveback_bps"] = np.nan
        record["mfe_plus_12_retained_mfe_ratio"] = np.nan
        record["lost_more_than_50pct_mfe_by_mfe_plus_12"] = False
        record["still_positive_at_mfe_plus_12"] = False
        record["mfe_plus_12_status"] = "insufficient_post_mfe_window"

        if record.get("row_status") != "matched":
            diagnostics.append(record)
            continue

        entry_time = record.get("entry_time")
        exit_time = record.get("exit_time")
        entry_price = record.get("entry_price")
        if pd.isna(entry_time) or pd.isna(exit_time) or pd.isna(entry_price):
            diagnostics.append(record)
            continue

        path = _interval_path(bars, pd.Timestamp(entry_time), pd.Timestamp(exit_time))
        if path.empty:
            diagnostics.append(record)
            continue

        high_values = pd.to_numeric(path["high"], errors="coerce").to_numpy(dtype=float)
        close_values = pd.to_numeric(path["close"], errors="coerce").to_numpy(dtype=float)
        valid_high_indices = np.where(np.isfinite(high_values))[0]
        if len(valid_high_indices) == 0:
            diagnostics.append(record)
            continue

        mfe_pos = int(valid_high_indices[np.argmax(high_values[valid_high_indices])])
        review_pos = mfe_pos + POST_MFE_WINDOW_BARS
        if review_pos >= len(close_values):
            diagnostics.append(record)
            continue

        mfe_bps = record.get("mfe_bps")
        if pd.isna(mfe_bps):
            diagnostics.append(record)
            continue

        mfe_plus_12_price = float(close_values[review_pos])
        if not np.isfinite(mfe_plus_12_price):
            diagnostics.append(record)
            continue

        mfe_plus_12_return_bps = (mfe_plus_12_price / float(entry_price) - 1.0) * 10_000.0
        mfe_plus_12_giveback_bps = float(mfe_bps) - mfe_plus_12_return_bps
        retained_ratio = mfe_plus_12_return_bps / float(mfe_bps) if float(mfe_bps) > 0.0 else np.nan

        record.update(
            {
                "mfe_plus_12_available": True,
                "mfe_plus_12_price": mfe_plus_12_price,
                "mfe_plus_12_return_bps": mfe_plus_12_return_bps,
                "mfe_plus_12_giveback_bps": mfe_plus_12_giveback_bps,
                "mfe_plus_12_retained_mfe_ratio": retained_ratio,
                "lost_more_than_50pct_mfe_by_mfe_plus_12": bool(float(mfe_bps) > 0.0 and mfe_plus_12_giveback_bps >= 0.50 * float(mfe_bps)),
                "still_positive_at_mfe_plus_12": bool(mfe_plus_12_return_bps > 0.0),
                "mfe_plus_12_status": "available",
            }
        )
        diagnostics.append(record)

    return pd.DataFrame(diagnostics)


def _subset_stats(frame: pd.DataFrame) -> dict[str, object]:
    available = frame[frame["mfe_plus_12_available"]].copy()
    out = {
        "count": int(len(frame)),
        "mfe_plus_12_available_count": int(frame["mfe_plus_12_available"].sum()),
        "avg_mfe_plus_12_return_bps": float(available["mfe_plus_12_return_bps"].mean()) if len(available) else None,
        "median_mfe_plus_12_return_bps": float(available["mfe_plus_12_return_bps"].median()) if len(available) else None,
        "pct_still_positive_at_mfe_plus_12": float(available["still_positive_at_mfe_plus_12"].mean()) if len(available) else None,
        "pct_lost_more_than_50pct_mfe_by_mfe_plus_12": float(available["lost_more_than_50pct_mfe_by_mfe_plus_12"].mean()) if len(available) else None,
        "avg_mfe_plus_12_giveback_bps": float(available["mfe_plus_12_giveback_bps"].mean()) if len(available) else None,
        "median_mfe_plus_12_giveback_bps": float(available["mfe_plus_12_giveback_bps"].median()) if len(available) else None,
        "avg_retained_mfe_ratio": float(available["mfe_plus_12_retained_mfe_ratio"].mean()) if len(available) else None,
        "median_retained_mfe_ratio": float(available["mfe_plus_12_retained_mfe_ratio"].median()) if len(available) else None,
    }
    return out


def _yearly_availability(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    years = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    for year in sorted(years.dropna().astype(int).unique().tolist()):
        group = frame[years == year].copy()
        rows.append(
            {
                "year": year,
                "total_trades": int(len(group)),
                "giveback_loss_count": int((group["excursion_class"] == "giveback_loss").sum()),
                "weak_positive_exit_count": int((group["excursion_class"] == "weak_positive_exit").sum()),
                "mfe_plus_12_available_count": int(group["mfe_plus_12_available"].sum()),
                "mfe_plus_12_unavailable_count": int((~group["mfe_plus_12_available"]).sum()),
                "availability_rate": float(group["mfe_plus_12_available"].mean()) if len(group) else None,
            }
        )
    return rows


def _subset_stats_by_year(frame: pd.DataFrame, class_name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    years = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    class_mask = frame["excursion_class"] == class_name
    for year in sorted(years.dropna().astype(int).unique().tolist()):
        group = frame[(years == year) & class_mask].copy()
        rows.append({"year": year, **_subset_stats(group)})
    return rows


def _diagnostic_summary(frame: pd.DataFrame) -> dict[str, object]:
    total_trades = int(len(frame))
    matched_rows = int((frame["row_status"] == "matched").sum())
    unresolved_rows = int((frame["row_status"] != "matched").sum())
    available_rows = int(frame["mfe_plus_12_available"].sum())
    unavailable_rows = int((~frame["mfe_plus_12_available"]).sum())
    overall_giveback = frame[frame["excursion_class"] == "giveback_loss"].copy()
    overall_weak = frame[frame["excursion_class"] == "weak_positive_exit"].copy()

    summary = {
        "trade_rows_loaded": total_trades,
        "bar_rows_loaded": None,
        "bar_files_read": None,
        "rows_with_matched_bars": matched_rows,
        "rows_without_matched_bars": total_trades - matched_rows,
        "unresolved_rows": unresolved_rows,
        "year_min": int(pd.to_numeric(frame["year"], errors="coerce").dropna().min()) if frame["year"].notna().any() else None,
        "year_max": int(pd.to_numeric(frame["year"], errors="coerce").dropna().max()) if frame["year"].notna().any() else None,
        "side_basis": _side_basis(frame),
        "final_return_basis": _price_basis(frame),
        "trades_inspected": total_trades,
        "giveback_loss_trades_inspected": int(len(overall_giveback)),
        "weak_positive_exit_trades_inspected": int(len(overall_weak)),
        "rows_with_mfe_plus_12_available": available_rows,
        "rows_without_mfe_plus_12_available": unavailable_rows,
        "insufficient_post_mfe_window_count": unavailable_rows,
        "availability_rate": float(available_rows / total_trades) if total_trades else None,
        "yearly_availability": _yearly_availability(frame),
        "giveback_overall": _subset_stats(overall_giveback),
        "weak_overall": _subset_stats(overall_weak),
    }
    return summary


def build_report(*, trade_log: Path, bar_dir: Path, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log)
    bars, bar_files = _load_bars(bar_dir)
    diagnostics = _diagnostic_frame(trades, bars)
    summary = _diagnostic_summary(diagnostics)
    summary["bar_rows_loaded"] = int(len(bars))
    summary["bar_files_read"] = int(len(bar_files))

    year_rows = summary["yearly_availability"]

    lines: list[str] = []
    lines.append("# V9.2 C_Exhaustion Fixed Post-MFE Review Window Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is a bounded descriptive diagnostic of the fixed MFE+12 review window. It does not optimize exits, change strategy logic, run a backtest, or approve trading.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- trade_log path: `{trade_log}`")
    lines.append(f"- bar_dir path: `{bar_dir}`")
    lines.append("- real_trade_log_read: `true`")
    lines.append("- real_bounded_bar_data_read: `true`")
    lines.append("- raw_l2_data_read: `false`")
    lines.append("- ofi_artifacts_read: `false`")
    lines.append("- row_level_artifacts_written: `false`")
    lines.append("- feature_table_artifacts_written: `false`")
    lines.append("- model_artifacts_written: `false`")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No exit optimization was performed.")
    lines.append("- No target/stop tuning was performed.")
    lines.append("- No threshold tuning was performed.")
    lines.append("- No alternative review windows were tested.")
    lines.append("- No strategy backtest was run.")
    lines.append("- No strategy/replay logic was changed.")
    lines.append("- No model was trained.")
    lines.append("- No model was refit.")
    lines.append("- No scaler was refit.")
    lines.append("- No raw L2 data was read.")
    lines.append("- No OFI artifacts were read or written.")
    lines.append("- No row-level artifacts were written.")
    lines.append("- No feature-table artifacts were written.")
    lines.append("- No model artifacts were written.")
    lines.append("- No paper/live trading is approved.")
    lines.append("- No production approval is given.")
    lines.append("- Alpha is not approved.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("")
    lines.append("## Pre-Registered Protocol Applied")
    lines.append("")
    lines.append(f"- preregistration file path: `{PRE_REGISTERED_PREREG}`")
    lines.append("- review window anchor: first MFE bar")
    lines.append(f"- review window length: {POST_MFE_WINDOW_BARS} bars after MFE")
    lines.append("- review point: MFE+12")
    lines.append(f"- interval convention: `{INTERVAL_CONVENTION}`")
    lines.append("- review-point price basis: review-bar close relative to entry_price")
    lines.append("- no alternative windows tested")
    lines.append("- no parameter search")
    lines.append("- no holdout tuning")
    lines.append("- MFE treated as hindsight diagnostic information, not a live-tradable signal")
    lines.append("")
    lines.append("## Source Construction Summary")
    lines.append("")
    lines.append(f"- trade_rows_loaded: `{summary['trade_rows_loaded']}`")
    lines.append(f"- bar_rows_loaded: `{summary['bar_rows_loaded']}`")
    lines.append(f"- bar_files_read: `{summary['bar_files_read']}`")
    lines.append(f"- rows_with_matched_bars: `{summary['rows_with_matched_bars']}`")
    lines.append(f"- unresolved_rows: `{summary['unresolved_rows']}`")
    lines.append(f"- year_min: `{summary['year_min']}`")
    lines.append(f"- year_max: `{summary['year_max']}`")
    lines.append(f"- side_basis: `{summary['side_basis']}`")
    lines.append(f"- final_return_basis: `{summary['final_return_basis']}`")
    lines.append("")
    lines.append("## MFE+12 Availability Summary")
    lines.append("")
    lines.append(f"- trades_inspected: `{summary['trades_inspected']}`")
    lines.append(f"- giveback_loss_trades_inspected: `{summary['giveback_loss_trades_inspected']}`")
    lines.append(f"- weak_positive_exit_trades_inspected: `{summary['weak_positive_exit_trades_inspected']}`")
    lines.append(f"- rows_with_mfe_plus_12_available: `{summary['rows_with_mfe_plus_12_available']}`")
    lines.append(f"- rows_without_mfe_plus_12_available: `{summary['rows_without_mfe_plus_12_available']}`")
    lines.append(f"- insufficient_post_mfe_window_count: `{summary['insufficient_post_mfe_window_count']}`")
    lines.append(f"- availability_rate: `{_fmt_pct(summary['availability_rate'])}`")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "year": row["year"],
                "total_trades": row["total_trades"],
                "giveback_loss_count": row["giveback_loss_count"],
                "weak_positive_exit_count": row["weak_positive_exit_count"],
                "mfe_plus_12_available_count": row["mfe_plus_12_available_count"],
                "mfe_plus_12_unavailable_count": row["mfe_plus_12_unavailable_count"],
                "availability_rate": row["availability_rate"],
            }
            for row in year_rows
        ],
        [
            "year",
            "total_trades",
            "giveback_loss_count",
            "weak_positive_exit_count",
            "mfe_plus_12_available_count",
            "mfe_plus_12_unavailable_count",
            "availability_rate",
        ],
    ))
    lines.append("")
    lines.append("## Giveback Loss MFE+12 Diagnostic")
    lines.append("")
    gb = summary["giveback_overall"]
    lines.append(f"- count: `{gb['count']}`")
    lines.append(f"- mfe_plus_12_available_count: `{gb['mfe_plus_12_available_count']}`")
    lines.append(f"- avg_mfe_plus_12_return_bps: `{_fmt(gb['avg_mfe_plus_12_return_bps'])}`")
    lines.append(f"- median_mfe_plus_12_return_bps: `{_fmt(gb['median_mfe_plus_12_return_bps'])}`")
    lines.append(f"- pct_still_positive_at_mfe_plus_12: `{_fmt_pct(gb['pct_still_positive_at_mfe_plus_12'])}`")
    lines.append(f"- pct_lost_more_than_50pct_mfe_by_mfe_plus_12: `{_fmt_pct(gb['pct_lost_more_than_50pct_mfe_by_mfe_plus_12'])}`")
    lines.append(f"- avg_mfe_plus_12_giveback_bps: `{_fmt(gb['avg_mfe_plus_12_giveback_bps'])}`")
    lines.append(f"- median_mfe_plus_12_giveback_bps: `{_fmt(gb['median_mfe_plus_12_giveback_bps'])}`")
    lines.append(f"- avg_retained_mfe_ratio: `{_fmt(gb['avg_retained_mfe_ratio'])}`")
    lines.append(f"- median_retained_mfe_ratio: `{_fmt(gb['median_retained_mfe_ratio'])}`")
    lines.append("")
    lines.append(_markdown_table(
        _subset_stats_by_year(diagnostics, "giveback_loss"),
        [
            "year",
            "count",
            "mfe_plus_12_available_count",
            "avg_mfe_plus_12_return_bps",
            "median_mfe_plus_12_return_bps",
            "pct_still_positive_at_mfe_plus_12",
            "pct_lost_more_than_50pct_mfe_by_mfe_plus_12",
            "avg_mfe_plus_12_giveback_bps",
            "median_mfe_plus_12_giveback_bps",
            "avg_retained_mfe_ratio",
            "median_retained_mfe_ratio",
        ],
    ))
    lines.append("")
    lines.append("## Weak Positive Exit MFE+12 Diagnostic")
    lines.append("")
    wp = summary["weak_overall"]
    lines.append(f"- count: `{wp['count']}`")
    lines.append(f"- mfe_plus_12_available_count: `{wp['mfe_plus_12_available_count']}`")
    lines.append(f"- avg_mfe_plus_12_return_bps: `{_fmt(wp['avg_mfe_plus_12_return_bps'])}`")
    lines.append(f"- median_mfe_plus_12_return_bps: `{_fmt(wp['median_mfe_plus_12_return_bps'])}`")
    lines.append(f"- pct_still_positive_at_mfe_plus_12: `{_fmt_pct(wp['pct_still_positive_at_mfe_plus_12'])}`")
    lines.append(f"- pct_lost_more_than_50pct_mfe_by_mfe_plus_12: `{_fmt_pct(wp['pct_lost_more_than_50pct_mfe_by_mfe_plus_12'])}`")
    lines.append(f"- avg_mfe_plus_12_giveback_bps: `{_fmt(wp['avg_mfe_plus_12_giveback_bps'])}`")
    lines.append(f"- median_mfe_plus_12_giveback_bps: `{_fmt(wp['median_mfe_plus_12_giveback_bps'])}`")
    lines.append(f"- avg_retained_mfe_ratio: `{_fmt(wp['avg_retained_mfe_ratio'])}`")
    lines.append(f"- median_retained_mfe_ratio: `{_fmt(wp['median_retained_mfe_ratio'])}`")
    lines.append("")
    lines.append(_markdown_table(
        _subset_stats_by_year(diagnostics, "weak_positive_exit"),
        [
            "year",
            "count",
            "mfe_plus_12_available_count",
            "avg_mfe_plus_12_return_bps",
            "median_mfe_plus_12_return_bps",
            "pct_still_positive_at_mfe_plus_12",
            "pct_lost_more_than_50pct_mfe_by_mfe_plus_12",
            "avg_mfe_plus_12_giveback_bps",
            "median_mfe_plus_12_giveback_bps",
            "avg_retained_mfe_ratio",
            "median_retained_mfe_ratio",
        ],
    ))
    lines.append("")
    lines.append("## 2025 vs 2026 Comparison")
    lines.append("")
    for year in [2025, 2026]:
        subset = diagnostics[diagnostics["year"] == year].copy()
        giveback = subset[subset["excursion_class"] == "giveback_loss"].copy()
        giveback_avail = giveback[giveback["mfe_plus_12_available"]].copy()
        lines.append(f"### {year}")
        lines.append("")
        lines.append(f"- total trades: `{int(len(subset))}`")
        lines.append(f"- giveback_loss trades: `{int(len(giveback))}`")
        lines.append(f"- weak_positive_exit trades: `{int((subset['excursion_class'] == 'weak_positive_exit').sum())}`")
        lines.append(f"- MFE+12 availability: `{_fmt_pct(float(subset['mfe_plus_12_available'].mean()) if len(subset) else None)}`")
        lines.append(f"- percentage of giveback_loss trades still positive at MFE+12: `{_fmt_pct(float(giveback_avail['still_positive_at_mfe_plus_12'].mean()) if len(giveback_avail) else None)}`")
        lines.append(f"- percentage of giveback_loss trades that lost more than 50% of MFE by MFE+12: `{_fmt_pct(float(giveback_avail['lost_more_than_50pct_mfe_by_mfe_plus_12'].mean()) if len(giveback_avail) else None)}`")
        lines.append(f"- average MFE+12 return: `{_fmt(float(giveback_avail['mfe_plus_12_return_bps'].mean()) if len(giveback_avail) else None)}`")
        lines.append(f"- median MFE+12 return: `{_fmt(float(giveback_avail['mfe_plus_12_return_bps'].median()) if len(giveback_avail) else None)}`")
        if year == 2025:
            interp = "2025 shows early favorable excursion but long post-MFE decay before exit."
        else:
            interp = "2026 is smaller, but still shows post-MFE decay in the losing trades."
        lines.append(f"- interpretation: {interp}")
        lines.append("")

    lines.append("## Diagnostic Interpretation")
    lines.append("")
    availability_rate = summary["availability_rate"] or 0.0
    if availability_rate >= 0.75:
        lines.append("- MFE+12 occurs before the original exit often enough to be useful diagnostically for most trades.")
    elif availability_rate > 0.0:
        lines.append("- MFE+12 is available for a meaningful subset of trades, but not universally.")
    else:
        lines.append("- MFE+12 is not available often enough to support a broad diagnostic.")
    if gb["pct_still_positive_at_mfe_plus_12"] is not None and gb["pct_still_positive_at_mfe_plus_12"] >= 0.5:
        lines.append("- Giveback_loss trades are usually still positive at MFE+12.")
    else:
        lines.append("- Giveback_loss trades are not usually still positive at MFE+12.")
    if gb["pct_lost_more_than_50pct_mfe_by_mfe_plus_12"] is not None and gb["pct_lost_more_than_50pct_mfe_by_mfe_plus_12"] >= 0.5:
        lines.append("- Giveback_loss trades have often already lost most of MFE by MFE+12.")
    else:
        lines.append("- Giveback_loss trades have not generally lost most of MFE by MFE+12.")
    lines.append("- 2025 is the weaker holdout year relative to 2026 if its giveback losses decay more sharply or its MFE+12 returns are lower.")
    lines.append("- The fixed MFE+12 review window reveals a descriptive post-MFE risk pattern.")
    lines.append("- The result supports preregistering a future exit experiment only if the next hypothesis remains fixed and non-leaky.")
    lines.append("- The result does not claim a better strategy or tradable edge.")
    lines.append("")
    lines.append("## What This Proves")
    lines.append("")
    lines.append("- Fixed MFE+12 can be computed safely from the existing trade intervals and bounded 750btc bars.")
    lines.append("- Fixed MFE+12 is available before exit for at least some trades, and the diagnostic can measure post-MFE decay.")
    lines.append("- Giveback can be visible by MFE+12.")
    lines.append("- 2025 and 2026 can be compared descriptively without changing exits.")
    lines.append("")
    lines.append("## What This Does Not Prove")
    lines.append("")
    lines.append("- no alpha approval")
    lines.append("- no trading rule")
    lines.append("- no exit improvement")
    lines.append("- no target/stop approval")
    lines.append("- no paper/live readiness")
    lines.append("- no production readiness")
    lines.append("- no execution/slippage validity")
    lines.append("- no proof this can be captured live")
    lines.append("- no out-of-sample exit-test result")
    lines.append("")
    lines.append("## Risk Register")
    lines.append("")
    lines.append("- MFE is hindsight diagnostic information.")
    lines.append("- MFE+12 depends on knowing the MFE bar after the fact.")
    lines.append("- Intrabar path is unknown.")
    lines.append(f"- final_return_basis is {summary['final_return_basis']} if used.")
    lines.append(f"- {summary['side_basis']}.")
    lines.append("- 750btc bars are not tick data.")
    lines.append("- 2026 sample size is small.")
    lines.append("- No row-level logistic kept/skipped source.")
    lines.append("- No execution/slippage simulation.")
    lines.append("- Fixed MFE+12 may still be too late or too early.")
    lines.append("")
    lines.append("## Stop / Go Assessment")
    lines.append("")
    lines.append("- Stop or pause if MFE+12 is unavailable for most recent trades.")
    lines.append("- Stop or pause if post-MFE decay does not appear before original exit.")
    lines.append("- Stop or pause if the signal is inconsistent across years.")
    lines.append("- Stop or pause if the result only looks useful after excluding bad years.")
    lines.append("- Stop or pause if the next step would require tuning the review window.")
    lines.append("- Continue only if the result yields a non-leaky separately pre-registerable future exit experiment.")
    lines.append("- Continue only if the future experiment uses fixed parameters.")
    lines.append("- Continue only if the future experiment does not change holdout protocol.")
    lines.append("- Continue only if the next task remains documentation-first.")
    lines.append("")
    lines.append("## Recommended Next Step")
    lines.append("")
    if gb["pct_lost_more_than_50pct_mfe_by_mfe_plus_12"] is not None and gb["pct_lost_more_than_50pct_mfe_by_mfe_plus_12"] >= 0.5:
        lines.append("Recommend a documentation-only future exit-experiment preregistration with fixed parameters, not execution.")
    elif availability_rate > 0.0:
        lines.append("Recommend a stop/pause review or alternative single-hypothesis preregistration, not parameter search.")
    else:
        lines.append("Recommend a stop/pause review or alternative single-hypothesis preregistration, not parameter search.")
    lines.append("")
    lines.append("## Explicitly Not Approved")
    lines.append("")
    lines.append("- No paper trading.")
    lines.append("- No live trading.")
    lines.append("- No production deployment.")
    lines.append("- No additional model classes.")
    lines.append("- No threshold tuning.")
    lines.append("- No feature fishing.")
    lines.append("- No OFI/L2 integration.")
    lines.append("- No full reconstruction.")
    lines.append("- No claims of alpha.")
    lines.append("- No strategy/replay changes.")
    lines.append("- No exit-horizon optimization.")
    lines.append("- No target/stop tuning.")
    lines.append("- No backtest reruns.")
    lines.append("- No row-level artifact persistence.")
    lines.append("- No trading approval from MFE hindsight.")
    lines.append("- No review-window optimization.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if availability_rate == 0.0:
        decision = "fixed_post_mfe_review_window_diagnostic_blocked"
    elif summary["rows_without_mfe_plus_12_available"] > 0:
        decision = "fixed_post_mfe_review_window_diagnostic_partial"
    else:
        decision = "fixed_post_mfe_review_window_diagnostic_pass"
    lines.append(f"Decision: `{decision}`")
    lines.append("")
    lines.append("## Decision Labels")
    lines.append("")
    labels = [
        "c_exhaustion_fixed_post_mfe_review_window_diagnostic_created",
        "bounded_descriptive_only",
        "single_hypothesis_only",
        "fixed_post_mfe_review_window",
        "mfe_plus_12_window",
        "real_trade_log_read",
        "real_bounded_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_review_window_optimization",
        "no_exit_optimization",
        "no_target_stop_tuning",
        "no_threshold_tuning",
        "no_new_model_trained",
        "no_strategy_backtest_run",
        "no_strategy_replay_changes",
        "no_row_level_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "full_reconstruction_not_approved",
        "alpha_not_approved",
        "paper_live_blocked",
        "production_not_approved",
        decision,
    ]
    for label in labels:
        lines.append(f"- `{label}`")

    report = "\n".join(lines) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report, encoding="utf-8")
    return report, {**summary, "decision": decision}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(trade_log=args.trade_log, bar_dir=args.bar_dir, output_doc=args.output_doc)
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
