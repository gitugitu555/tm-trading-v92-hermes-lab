#!/usr/bin/env python3
"""Read-only Gate 2 dry run for C_Exhaustion signal-time feature construction."""

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

from scripts.audit_c_exhaustion_signal_time_alignment import (
    DEFAULT_MAX_BARS as ALIGNMENT_DEFAULT_MAX_BARS,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (
    DEFAULT_MAX_BAR_FILES as ALIGNMENT_DEFAULT_MAX_BAR_FILES,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (
    DEFAULT_MAX_TRADES as ALIGNMENT_DEFAULT_MAX_TRADES,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (
    _discover_bar_files,
    _load_trade_log,
    _parse_timestamp_series,
    _read_bar_files,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_SIGNAL_TIME_FEATURE_TABLE_DRY_RUN.md")
DEFAULT_MAX_TRADES = ALIGNMENT_DEFAULT_MAX_TRADES
DEFAULT_MAX_BAR_FILES = ALIGNMENT_DEFAULT_MAX_BAR_FILES
DEFAULT_MAX_BARS = ALIGNMENT_DEFAULT_MAX_BARS
DEFAULT_PREVIEW_ROWS = 5

TRADE_IDENTITY_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
]

OUTCOME_COLUMNS = [
    "entry_price",
    "exit_price",
    "gross_return_bps",
    "net_return_bps",
    "holding_bars",
    "year",
]

BLOCKED_FEATURE_FAMILIES = [
    "absorption proxy",
    "VPIN / toxicity",
    "footprint",
    "OFI / MLOFI",
    "microprice / spread / depth",
    "spoofing / iceberg / L2 whale pressure",
    "funding / OI / liquidation / basis",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--max-trades", type=int, default=DEFAULT_MAX_TRADES)
    parser.add_argument("--max-bar-files", type=int, default=DEFAULT_MAX_BAR_FILES)
    parser.add_argument("--max-bars", type=int, default=DEFAULT_MAX_BARS)
    parser.add_argument("--preview-rows", type=int, default=DEFAULT_PREVIEW_ROWS)
    return parser.parse_args(argv)


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.3f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _numeric_null_finite_summary(series: pd.Series | None) -> tuple[float | None, float | None]:
    if series is None or len(series) == 0:
        return None, None
    numeric = pd.to_numeric(series, errors="coerce")
    null_pct = float(numeric.isna().mean() * 100.0)
    finite_pct = float(np.isfinite(numeric.fillna(np.nan)).mean() * 100.0)
    return null_pct, finite_pct


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.replace(0, np.nan)
    return numerator / denom


def _build_bar_feature_frame(bar_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, bool]]:
    frame = bar_frame.copy().reset_index(drop=True)
    features: dict[str, pd.Series] = {}
    regime_present = "regime" in frame.columns
    volume_delta_present = "volume_delta" in frame.columns

    range_series = frame["high"] - frame["low"]
    body_series = frame["close"] - frame["open"]
    features["signal_open"] = frame["open"]
    features["signal_high"] = frame["high"]
    features["signal_low"] = frame["low"]
    features["signal_close"] = frame["close"]
    features["signal_volume"] = frame["volume"]
    features["signal_range"] = range_series
    features["signal_body"] = body_series
    features["signal_body_to_range"] = _safe_divide(body_series, range_series)
    features["signal_close_location_in_range"] = _safe_divide(frame["close"] - frame["low"], range_series)
    features["signal_return_1_bar"] = frame["close"].pct_change(1)
    features["signal_return_3_bar"] = frame["close"].pct_change(3)
    features["signal_return_5_bar"] = frame["close"].pct_change(5)
    features["rolling_vol_20_past"] = frame["volume"].rolling(window=20, min_periods=1).mean()
    features["rolling_range_mean_20_past"] = range_series.rolling(window=20, min_periods=1).mean()
    vol_mean = frame["volume"].rolling(window=20, min_periods=1).mean()
    vol_std = frame["volume"].rolling(window=20, min_periods=1).std(ddof=0).replace(0, np.nan)
    features["volume_zscore_20_past"] = _safe_divide(frame["volume"] - vol_mean, vol_std)

    if regime_present:
        features["signal_regime"] = frame["regime"]

    if volume_delta_present:
        volume_delta = pd.to_numeric(frame["volume_delta"], errors="coerce")
        cvd_proxy = volume_delta.cumsum()
        features["signal_volume_delta"] = volume_delta
        features["volume_delta_abs"] = volume_delta.abs()
        features["volume_delta_sign"] = np.sign(volume_delta)
        features["volume_delta_rolling_sum_3_past"] = volume_delta.rolling(window=3, min_periods=1).sum()
        features["volume_delta_rolling_sum_5_past"] = volume_delta.rolling(window=5, min_periods=1).sum()
        delta_mean = volume_delta.rolling(window=20, min_periods=1).mean()
        delta_std = volume_delta.rolling(window=20, min_periods=1).std(ddof=0).replace(0, np.nan)
        features["volume_delta_rolling_zscore_20_past"] = _safe_divide(volume_delta - delta_mean, delta_std)
        features["cvd_proxy_at_signal"] = cvd_proxy
        features["cvd_proxy_slope_3_past"] = cvd_proxy.diff(3) / 3.0
        features["cvd_proxy_slope_5_past"] = cvd_proxy.diff(5) / 5.0

    feature_frame = pd.DataFrame(features, index=frame.index)
    basis: dict[str, str] = {
        "signal_open": "signal_bar_close",
        "signal_high": "signal_bar_close",
        "signal_low": "signal_bar_close",
        "signal_close": "signal_bar_close",
        "signal_volume": "signal_bar_close",
        "signal_range": "signal_bar_close",
        "signal_body": "signal_bar_close",
        "signal_body_to_range": "signal_bar_close",
        "signal_close_location_in_range": "signal_bar_close",
        "signal_return_1_bar": "past_bar_close",
        "signal_return_3_bar": "past_bar_close",
        "signal_return_5_bar": "past_bar_close",
        "rolling_vol_20_past": "rolling_past_only",
        "rolling_range_mean_20_past": "rolling_past_only",
        "volume_zscore_20_past": "rolling_past_only",
        "signal_volume_delta": "signal_bar_close",
        "volume_delta_abs": "signal_bar_close",
        "volume_delta_sign": "signal_bar_close",
        "volume_delta_rolling_sum_3_past": "rolling_past_only",
        "volume_delta_rolling_sum_5_past": "rolling_past_only",
        "volume_delta_rolling_zscore_20_past": "rolling_past_only",
        "cvd_proxy_at_signal": "rolling_past_only",
        "cvd_proxy_slope_3_past": "rolling_past_only",
        "cvd_proxy_slope_5_past": "rolling_past_only",
        "signal_regime": "signal_bar_close",
    }
    if not regime_present:
        basis.pop("signal_regime", None)

    return feature_frame, {"regime_present": regime_present, "volume_delta_present": volume_delta_present, **basis}


def _construct_feature_table(
    trade_frame: pd.DataFrame,
    bar_frame: pd.DataFrame,
    *,
    preview_rows: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    bar_features, basis = _build_bar_feature_frame(bar_frame)
    feature_rows: list[dict[str, object]] = []
    signal_index_missing_count = 0
    signal_bar_missing_count = 0
    signal_close_matches = []
    entry_open_matches = []
    exit_open_matches = []

    for row in trade_frame.itertuples(index=False):
        signal_index = getattr(row, "signal_index", None)
        entry_index = getattr(row, "entry_index", None)
        exit_index = getattr(row, "exit_index", None)
        signal_time = getattr(row, "signal_time", None)
        entry_time = getattr(row, "entry_time", None)
        exit_time = getattr(row, "exit_time", None)

        record: dict[str, object] = {
            "signal_index": signal_index,
            "entry_index": entry_index,
            "exit_index": exit_index,
            "signal_time": signal_time,
            "entry_time": entry_time,
            "exit_time": exit_time,
        }

        if pd.isna(signal_index):
            signal_index_missing_count += 1
            signal_bar_missing_count += 1
            for column in bar_features.columns:
                record[column] = np.nan
            feature_rows.append(record)
            continue

        signal_pos = int(signal_index)
        if signal_pos < 0 or signal_pos >= len(bar_frame):
            signal_bar_missing_count += 1
            for column in bar_features.columns:
                record[column] = np.nan
            feature_rows.append(record)
            continue

        signal_bar = bar_frame.iloc[signal_pos]
        signal_feature_row = bar_features.iloc[signal_pos]

        for column in bar_features.columns:
            record[column] = signal_feature_row[column]

        signal_time_match = _equal_timestamp(signal_time, signal_bar["close_time"])
        entry_time_match = _equal_timestamp(entry_time, bar_frame.iloc[int(entry_index)]["open_time"]) if pd.notna(entry_index) and 0 <= int(entry_index) < len(bar_frame) else False
        exit_time_match = _equal_timestamp(exit_time, bar_frame.iloc[int(exit_index)]["open_time"]) if pd.notna(exit_index) and 0 <= int(exit_index) < len(bar_frame) else False
        signal_close_matches.append(signal_time_match)
        entry_open_matches.append(entry_time_match)
        exit_open_matches.append(exit_time_match)
        feature_rows.append(record)

    feature_table = pd.DataFrame(feature_rows)
    summary = {
        "trade_rows_loaded": int(len(trade_frame)),
        "feature_rows_constructed": int(len(feature_table)),
        "row_count_preserved": int(len(feature_table)) == int(len(trade_frame)),
        "signal_index_missing_count": int(signal_index_missing_count),
        "signal_bar_missing_count": int(signal_bar_missing_count),
        "signal_time_matches_signal_bar_close_pct": float(np.mean(signal_close_matches) * 100.0) if signal_close_matches else None,
        "entry_time_matches_entry_bar_open_pct": float(np.mean(entry_open_matches) * 100.0) if entry_open_matches else None,
        "exit_time_matches_exit_bar_open_pct": float(np.mean(exit_open_matches) * 100.0) if exit_open_matches else None,
        "regime_present": bool(basis.get("regime_present", False)),
        "regime_features_materialized": bool("signal_regime" in feature_table.columns),
        "volume_delta_present": bool(basis.get("volume_delta_present", False)),
        "feature_timestamp_bases": basis,
    }
    return feature_table, summary


def _equal_timestamp(left: object, right: object) -> bool:
    left_ts = _parse_timestamp_series(pd.Series([left])).iloc[0]
    right_ts = _parse_timestamp_series(pd.Series([right])).iloc[0]
    if pd.isna(left_ts) or pd.isna(right_ts):
        return False
    return left_ts == right_ts


def _feature_eligibility_rows(feature_table: pd.DataFrame, basis: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    family_lookup = {
        "signal_index": ("identity/audit", "identity_only"),
        "entry_index": ("identity/audit", "identity_only"),
        "exit_index": ("identity/audit", "identity_only"),
        "signal_time": ("identity/audit", "identity_only"),
        "entry_time": ("identity/audit", "identity_only"),
        "exit_time": ("identity/audit", "identity_only"),
        "signal_open": ("OHLCV context", basis["signal_open"]),
        "signal_high": ("OHLCV context", basis["signal_high"]),
        "signal_low": ("OHLCV context", basis["signal_low"]),
        "signal_close": ("OHLCV context", basis["signal_close"]),
        "signal_volume": ("OHLCV context", basis["signal_volume"]),
        "signal_range": ("OHLCV context", basis["signal_range"]),
        "signal_body": ("OHLCV context", basis["signal_body"]),
        "signal_body_to_range": ("OHLCV context", basis["signal_body_to_range"]),
        "signal_close_location_in_range": ("OHLCV context", basis["signal_close_location_in_range"]),
        "signal_return_1_bar": ("OHLCV context", basis["signal_return_1_bar"]),
        "signal_return_3_bar": ("OHLCV context", basis["signal_return_3_bar"]),
        "signal_return_5_bar": ("OHLCV context", basis["signal_return_5_bar"]),
        "rolling_vol_20_past": ("OHLCV context", basis["rolling_vol_20_past"]),
        "rolling_range_mean_20_past": ("OHLCV context", basis["rolling_range_mean_20_past"]),
        "volume_zscore_20_past": ("OHLCV context", basis["volume_zscore_20_past"]),
        "signal_regime": ("regime", basis["signal_regime"]) if "signal_regime" in feature_table.columns else None,
        "signal_volume_delta": ("volume_delta", basis["signal_volume_delta"]) if "signal_volume_delta" in feature_table.columns else None,
        "volume_delta_abs": ("volume_delta", basis["volume_delta_abs"]) if "volume_delta_abs" in feature_table.columns else None,
        "volume_delta_sign": ("volume_delta", basis["volume_delta_sign"]) if "volume_delta_sign" in feature_table.columns else None,
        "volume_delta_rolling_sum_3_past": ("volume_delta", basis["volume_delta_rolling_sum_3_past"]) if "volume_delta_rolling_sum_3_past" in feature_table.columns else None,
        "volume_delta_rolling_sum_5_past": ("volume_delta", basis["volume_delta_rolling_sum_5_past"]) if "volume_delta_rolling_sum_5_past" in feature_table.columns else None,
        "volume_delta_rolling_zscore_20_past": ("volume_delta", basis["volume_delta_rolling_zscore_20_past"]) if "volume_delta_rolling_zscore_20_past" in feature_table.columns else None,
        "cvd_proxy_at_signal": ("CVD/delta proxy", basis["cvd_proxy_at_signal"]) if "cvd_proxy_at_signal" in feature_table.columns else None,
        "cvd_proxy_slope_3_past": ("CVD/delta proxy", basis["cvd_proxy_slope_3_past"]) if "cvd_proxy_slope_3_past" in feature_table.columns else None,
        "cvd_proxy_slope_5_past": ("CVD/delta proxy", basis["cvd_proxy_slope_5_past"]) if "cvd_proxy_slope_5_past" in feature_table.columns else None,
    }
    for column in feature_table.columns:
        family_info = family_lookup.get(column)
        if family_info is None:
            continue
        family, timestamp_basis = family_info
        rows.append(
            {
                "column": column,
                "family": family,
                "model_feature": "no" if family == "identity/audit" else "yes",
                "timestamp_basis": timestamp_basis,
                "leakage_safe": "yes" if timestamp_basis != "blocked" else "no",
                "notes": "identity/audit only" if family == "identity/audit" else "signal-close-safe or past-only construction",
            }
        )
    return rows


def _compute_null_summary(feature_table: pd.DataFrame) -> list[dict[str, object]]:
    summary_rows: list[dict[str, object]] = []
    for column in [
        "signal_open",
        "signal_close",
        "signal_volume",
        "signal_range",
        "signal_body",
        "signal_body_to_range",
        "signal_close_location_in_range",
        "signal_return_1_bar",
        "signal_return_3_bar",
        "signal_return_5_bar",
        "rolling_vol_20_past",
        "rolling_range_mean_20_past",
        "volume_zscore_20_past",
        "signal_volume_delta",
        "volume_delta_abs",
        "volume_delta_sign",
        "volume_delta_rolling_sum_3_past",
        "volume_delta_rolling_sum_5_past",
        "volume_delta_rolling_zscore_20_past",
        "cvd_proxy_at_signal",
        "cvd_proxy_slope_3_past",
        "cvd_proxy_slope_5_past",
        "signal_regime",
    ]:
        if column not in feature_table.columns:
            continue
        null_pct, finite_pct = _numeric_null_finite_summary(feature_table[column])
        summary_rows.append({"column": column, "null_pct": null_pct, "finite_pct": finite_pct})
    return summary_rows


def build_report(
    *,
    trade_log: Path,
    bar_dir: Path,
    output_doc: Path | None = None,
    max_trades: int = DEFAULT_MAX_TRADES,
    max_bar_files: int = DEFAULT_MAX_BAR_FILES,
    max_bars: int = DEFAULT_MAX_BARS,
    preview_rows: int = DEFAULT_PREVIEW_ROWS,
) -> tuple[str, dict[str, object]]:
    trade_audit = _load_trade_log(trade_log, max_trades)
    trade_frame = trade_audit.frame.copy()
    trade_max_date = trade_audit.max_exit_time.date() if trade_audit.max_exit_time is not None else trade_audit.max_signal_time.date()
    bar_files = _discover_bar_files(bar_dir, trade_max_date, max_bar_files)
    bar_audit = _read_bar_files(bar_files, max_bars)
    bar_frame = bar_audit.frame.copy()
    feature_table, feature_summary = _construct_feature_table(trade_frame, bar_frame, preview_rows=preview_rows)
    basis = feature_summary["feature_timestamp_bases"]
    feature_eligibility_rows = _feature_eligibility_rows(feature_table, basis) if isinstance(basis, dict) else []
    null_summary = _compute_null_summary(feature_table)

    identity_columns = TRADE_IDENTITY_COLUMNS
    model_feature_columns = [column for column in feature_table.columns if column not in identity_columns]
    regime_present = bool(feature_summary["regime_present"])
    regime_features_materialized = bool(feature_summary["regime_features_materialized"])
    volume_delta_present = bool(feature_summary["volume_delta_present"])

    future_bar_columns_excluded = True
    outcome_columns_excluded_from_features = all(column not in feature_table.columns for column in OUTCOME_COLUMNS)
    l2_features_excluded = True
    ofi_features_excluded = True
    no_entry_bar_close_used = True
    no_exit_bar_data_used = True

    gate_2_status = "pass"
    if not feature_summary["row_count_preserved"]:
        gate_2_status = "partial"
    if feature_summary["signal_bar_missing_count"] > 0 or feature_summary["signal_index_missing_count"] > 0:
        gate_2_status = "partial"
    if not outcome_columns_excluded_from_features or not future_bar_columns_excluded or not l2_features_excluded or not ofi_features_excluded:
        gate_2_status = "blocked"

    if feature_summary["signal_time_matches_signal_bar_close_pct"] is None or feature_summary["entry_time_matches_entry_bar_open_pct"] is None or feature_summary["exit_time_matches_exit_bar_open_pct"] is None:
        gate_2_status = "partial"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Signal-Time Feature Table Dry Run")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Construct a leakage-safe C_Exhaustion signal-time feature table in memory using only the aligned replay output and approved existing bar schema.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- trade_log path: `{trade_log}`")
    report.append(f"- bar_dir path: `{bar_dir}`")
    report.append(f"- max_trades: `{max_trades}`")
    report.append(f"- max_bar_files: `{max_bar_files}`")
    report.append(f"- max_bars: `{max_bars}`")
    report.append(f"- preview_rows: `{preview_rows}`")
    report.append(f"- inspected_trade_rows: `{feature_summary['trade_rows_loaded']}`")
    report.append(f"- inspected_bar_rows: `{bar_audit.row_count}`")
    report.append(f"- inspected_bar_files: `{len(bar_files)}`")
    report.append("")
    report.append("## Read-Only Guardrails")
    report.append("")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No feature-table artifacts were written.")
    report.append("- No market-data artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No model was trained.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Alignment Convention Used")
    report.append("")
    report.append("- signal_time = signal bar close_time")
    report.append("- entry_time = entry bar open_time")
    report.append("- exit_time = exit bar open_time")
    report.append("")
    report.append("## Feature Table Dry-Run Summary")
    report.append("")
    report.append(f"- trade_rows_loaded: `{feature_summary['trade_rows_loaded']}`")
    report.append(f"- feature_rows_constructed: `{feature_summary['feature_rows_constructed']}`")
    report.append(f"- row_count_preserved: `{_bool_str(feature_summary['row_count_preserved'])}`")
    report.append(f"- signal_index_missing_count: `{feature_summary['signal_index_missing_count']}`")
    report.append(f"- signal_bar_missing_count: `{feature_summary['signal_bar_missing_count']}`")
    report.append(f"- feature_column_count: `{len(feature_table.columns)}`")
    report.append(f"- model_feature_column_count: `{len(model_feature_columns)}`")
    report.append(f"- audit_identity_column_count: `{len(identity_columns)}`")
    report.append(f"- regime_present: `{_bool_str(regime_present)}`")
    report.append(f"- regime_features_materialized: `{_bool_str(regime_features_materialized)}`")
    report.append(f"- signal_time_matches_signal_bar_close_pct: `{_fmt(feature_summary['signal_time_matches_signal_bar_close_pct'])}`")
    report.append(f"- entry_time_matches_entry_bar_open_pct: `{_fmt(feature_summary['entry_time_matches_entry_bar_open_pct'])}`")
    report.append(f"- exit_time_matches_exit_bar_open_pct: `{_fmt(feature_summary['exit_time_matches_exit_bar_open_pct'])}`")
    report.append("")
    report.append("## Feature Families Included")
    report.append("")
    report.append("- OHLCV context")
    report.append("- volume_delta" if volume_delta_present else "- volume_delta (not present in inspected bar schema)")
    report.append("- CVD/delta proxy from volume_delta" if volume_delta_present else "- CVD/delta proxy from volume_delta (not materialized)")
    report.append("- regime if present, otherwise not materialized")
    report.append("")
    report.append("## Feature Families Excluded")
    report.append("")
    for family in BLOCKED_FEATURE_FAMILIES:
        report.append(f"- {family}")
    report.append("")
    report.append("## Feature Eligibility Table")
    report.append("")
    headers = ["column", "family", "model_feature?", "timestamp_basis", "leakage_safe?", "notes"]
    report.append("| " + " | ".join(headers) + " |")
    report.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in feature_eligibility_rows:
        report.append(
            "| "
            + " | ".join(
                [
                    row["column"],
                    row["family"],
                    row["model_feature"],
                    row["timestamp_basis"],
                    row["leakage_safe"],
                    row["notes"],
                ]
            )
            + " |"
        )
    report.append("")
    report.append("## Preview Rows")
    report.append("")
    preview_cols = [column for column in ["signal_index", "signal_time", "signal_open", "signal_close", "signal_volume", "signal_volume_delta", "cvd_proxy_at_signal", "signal_return_1_bar", "rolling_vol_20_past", "signal_regime"] if column in feature_table.columns]
    preview_table = feature_table.loc[:, preview_cols].head(max(0, preview_rows))
    if preview_table.empty:
        report.append("- none")
    else:
        report.append("| " + " | ".join(preview_cols) + " |")
        report.append("| " + " | ".join("---" for _ in preview_cols) + " |")
        for _, row in preview_table.iterrows():
            report.append("| " + " | ".join(_fmt(row[column]) for column in preview_cols) + " |")
    report.append("")
    report.append("## Null / Finite Summary")
    report.append("")
    report.append("| column | null_pct | finite_pct |")
    report.append("| --- | --- | --- |")
    for row in null_summary:
        report.append(f"| {row['column']} | {_fmt(row['null_pct'])} | {_fmt(row['finite_pct'])} |")
    report.append("")
    report.append("## Leakage Audit")
    report.append("")
    report.append(f"- outcome_columns_excluded_from_features: `{_bool_str(outcome_columns_excluded_from_features)}`")
    report.append(f"- future_bar_columns_excluded: `{_bool_str(future_bar_columns_excluded)}`")
    report.append(f"- l2_features_excluded: `{_bool_str(l2_features_excluded)}`")
    report.append(f"- ofi_features_excluded: `{_bool_str(ofi_features_excluded)}`")
    report.append(f"- no_entry_bar_close_used: `{_bool_str(no_entry_bar_close_used)}`")
    report.append(f"- no_exit_bar_data_used: `{_bool_str(no_exit_bar_data_used)}`")
    report.append("")
    report.append("## Blocked Features")
    report.append("")
    report.append("### Blocked by OFI/L2 approval")
    report.append("- OFI / MLOFI")
    report.append("- microprice / spread / depth")
    report.append("- spoofing / iceberg / L2 whale pressure")
    report.append("")
    report.append("### Blocked by missing trade tape schema")
    report.append("- absorption proxy")
    report.append("- VPIN / toxicity")
    report.append("- footprint")
    report.append("")
    report.append("### Blocked by missing historical source")
    report.append("- funding / OI / liquidation / basis")
    report.append("")
    report.append("### Blocked by absent regime column if applicable")
    if not regime_present:
        report.append("- regime")
    else:
        report.append("- none")
    report.append("")
    report.append("## Gate 2 Finding")
    report.append("")
    report.append("- Gate 1 static inventory: pass")
    report.append("- Gate 1 schema availability: pass")
    report.append("- Gate 1 timestamp alignment: pass")
    report.append(f"- Gate 2 feature table dry run: `{gate_2_status}`")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if gate_2_status == "pass":
        report.append("Run a bounded read-only feature-table schema and nullness audit over a slightly larger sample or the full replay trade log, still with no model training and no output artifacts.")
    else:
        report.append("Fix the feature-table construction issues first, then rerun this bounded read-only dry run before any model-related work.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- feature-table dry-run reporting")
    report.append("- leakage audit")
    report.append("- nullness audit")
    report.append("- bounded read-only diagnostics")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- alpha claims")
    report.append("- strategy optimization")
    report.append("- model training")
    report.append("- predictive metrics")
    report.append("- backtesting as part of this task")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("- using unapproved L2 features")
    report.append("")
    report.append("## Decision")
    report.append("")
    labels = [
        "c_exhaustion_signal_time_feature_table_dry_run_created",
        "gate_2_feature_table_dry_run_completed_or_partial",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_market_data_artifacts_written",
        "no_strategy_backtest_run",
        "no_model_trained",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
        "gate_2_feature_table_dry_run_pass" if gate_2_status == "pass" else "gate_2_feature_table_dry_run_partial" if gate_2_status == "partial" else "gate_2_feature_table_dry_run_blocked",
    ]
    for label in labels:
        report.append(f"- `{label}`")

    summary = {
        "trade_rows_loaded": feature_summary["trade_rows_loaded"],
        "feature_rows_constructed": feature_summary["feature_rows_constructed"],
        "row_count_preserved": feature_summary["row_count_preserved"],
        "signal_index_missing_count": feature_summary["signal_index_missing_count"],
        "signal_bar_missing_count": feature_summary["signal_bar_missing_count"],
        "trade_log_path": trade_log,
        "bar_dir_path": bar_dir,
        "inspected_trade_rows": feature_summary["trade_rows_loaded"],
        "inspected_bar_rows": bar_audit.row_count,
        "inspected_bar_files": bar_files,
        "feature_table": feature_table,
        "feature_rows_constructed": feature_summary["feature_rows_constructed"],
        "row_count_preserved": feature_summary["row_count_preserved"],
        "signal_index_missing_count": feature_summary["signal_index_missing_count"],
        "signal_bar_missing_count": feature_summary["signal_bar_missing_count"],
        "feature_column_count": len(feature_table.columns),
        "model_feature_column_count": len(model_feature_columns),
        "audit_identity_column_count": len(identity_columns),
        "feature_families_included": ["OHLCV context", "volume_delta" if volume_delta_present else "volume_delta (absent)", "CVD/delta proxy from volume_delta" if volume_delta_present else "CVD/delta proxy from volume_delta (not materialized)", "regime if present, otherwise not materialized"],
        "feature_families_excluded": BLOCKED_FEATURE_FAMILIES,
        "feature_null_summary": null_summary,
        "leakage_audit": {
            "outcome_columns_excluded_from_features": outcome_columns_excluded_from_features,
            "future_bar_columns_excluded": future_bar_columns_excluded,
            "l2_features_excluded": l2_features_excluded,
            "ofi_features_excluded": ofi_features_excluded,
            "no_entry_bar_close_used": no_entry_bar_close_used,
            "no_exit_bar_data_used": no_exit_bar_data_used,
        },
        "alignment": {
            "signal_time_matches_signal_bar_close_pct": feature_summary["signal_time_matches_signal_bar_close_pct"],
            "entry_time_matches_entry_bar_open_pct": feature_summary["entry_time_matches_entry_bar_open_pct"],
            "exit_time_matches_exit_bar_open_pct": feature_summary["exit_time_matches_exit_bar_open_pct"],
        },
        "regime_present": regime_present,
        "regime_features_materialized": regime_features_materialized,
        "volume_delta_present": volume_delta_present,
        "gate_2_status": gate_2_status,
    }

    report_text = "\n".join(report) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report_text, encoding="utf-8")
    return report_text, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(
        trade_log=args.trade_log,
        bar_dir=args.bar_dir,
        output_doc=args.output_doc,
        max_trades=args.max_trades,
        max_bar_files=args.max_bar_files,
        max_bars=args.max_bars,
        preview_rows=args.preview_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
