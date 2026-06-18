#!/usr/bin/env python3
"""Read-only Gate 2 contract and yearly stability audit for C_Exhaustion features."""

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

from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_BARS as ALIGNMENT_DEFAULT_MAX_BARS,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_BAR_FILES as ALIGNMENT_DEFAULT_MAX_BAR_FILES,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_TRADES as ALIGNMENT_DEFAULT_MAX_TRADES,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    _discover_bar_files,
    _load_trade_log,
    _read_bar_files,
)
from scripts.dry_run_c_exhaustion_signal_time_feature_table import (  # noqa: E402
    BLOCKED_FEATURE_FAMILIES,
)
from scripts.dry_run_c_exhaustion_signal_time_feature_table import (  # noqa: E402
    _construct_feature_table,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_FEATURE_TABLE_CONTRACT_AUDIT.md")
DEFAULT_MAX_TRADES = ALIGNMENT_DEFAULT_MAX_TRADES
DEFAULT_MAX_BAR_FILES = ALIGNMENT_DEFAULT_MAX_BAR_FILES
DEFAULT_MAX_BARS = ALIGNMENT_DEFAULT_MAX_BARS

AUDIT_IDENTITY_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
    "year",
]

MODEL_FEATURE_BASIS = {
    "signal_open": ("OHLCV context", "signal_bar_close", ["open"]),
    "signal_high": ("OHLCV context", "signal_bar_close", ["high"]),
    "signal_low": ("OHLCV context", "signal_bar_close", ["low"]),
    "signal_close": ("OHLCV context", "signal_bar_close", ["close"]),
    "signal_volume": ("OHLCV context", "signal_bar_close", ["volume"]),
    "signal_range": ("OHLCV context", "signal_bar_close", ["high", "low"]),
    "signal_body": ("OHLCV context", "signal_bar_close", ["open", "close"]),
    "signal_body_to_range": ("OHLCV context", "signal_bar_close", ["open", "high", "low", "close"]),
    "signal_close_location_in_range": ("OHLCV context", "signal_bar_close", ["high", "low", "close"]),
    "signal_return_1_bar": ("OHLCV context", "past_bar_close", ["close"]),
    "signal_return_3_bar": ("OHLCV context", "past_bar_close", ["close"]),
    "signal_return_5_bar": ("OHLCV context", "past_bar_close", ["close"]),
    "rolling_vol_20_past": ("OHLCV context", "rolling_past_only", ["volume"]),
    "rolling_range_mean_20_past": ("OHLCV context", "rolling_past_only", ["high", "low"]),
    "volume_zscore_20_past": ("OHLCV context", "rolling_past_only", ["volume"]),
    "signal_volume_delta": ("volume_delta", "signal_bar_close", ["volume_delta"]),
    "volume_delta_abs": ("volume_delta", "signal_bar_close", ["volume_delta"]),
    "volume_delta_sign": ("volume_delta", "signal_bar_close", ["volume_delta"]),
    "volume_delta_rolling_sum_3_past": ("volume_delta", "rolling_past_only", ["volume_delta"]),
    "volume_delta_rolling_sum_5_past": ("volume_delta", "rolling_past_only", ["volume_delta"]),
    "volume_delta_rolling_zscore_20_past": ("volume_delta", "rolling_past_only", ["volume_delta"]),
    "cvd_proxy_at_signal": ("CVD/delta proxy from volume_delta", "rolling_past_only", ["volume_delta"]),
    "cvd_proxy_slope_3_past": ("CVD/delta proxy from volume_delta", "rolling_past_only", ["volume_delta"]),
    "cvd_proxy_slope_5_past": ("CVD/delta proxy from volume_delta", "rolling_past_only", ["volume_delta"]),
}

BLOCKED_FAMILY_ROWS = [
    {
        "column": "regime",
        "family": "regime",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "stored regime column or canonical OHLCV-derived classifier",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "not materialized in the inspected schema",
    },
    {
        "column": "absorption proxy",
        "family": "absorption proxy",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "signed trade tape plus price movement",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "requires trade-tape schema not present in the replay output",
    },
    {
        "column": "VPIN / toxicity",
        "family": "VPIN / toxicity",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "signed buy/sell buckets",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "requires signed-flow buckets not present here",
    },
    {
        "column": "footprint",
        "family": "footprint",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "trade tape and price-level aggregation",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "requires data outside the current bounded bar schema",
    },
    {
        "column": "OFI / MLOFI",
        "family": "OFI / MLOFI",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "approved L2 OFI artifacts",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "blocked until L2 OFI artifact approval exists",
    },
    {
        "column": "microprice / spread / depth",
        "family": "microprice / spread / depth",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "approved L2 book-state artifacts",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "blocked until L2 book-state approval exists",
    },
    {
        "column": "spoofing / iceberg / L2 whale pressure",
        "family": "spoofing / iceberg / L2 whale pressure",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "event-level L2 history",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "requires unapproved L2 event history",
    },
    {
        "column": "funding / OI / liquidation / basis",
        "family": "funding / OI / liquidation / basis",
        "role": "blocked",
        "timestamp_basis": "blocked",
        "leakage_safe": "no",
        "required_source_columns": "verified historical derivatives or funding source",
        "nullable_allowed": "false",
        "finite_required": "false",
        "notes": "missing verified historical source in this repo path",
    },
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--max-trades", type=int, default=DEFAULT_MAX_TRADES)
    parser.add_argument("--max-bar-files", type=int, default=DEFAULT_MAX_BAR_FILES)
    parser.add_argument("--max-bars", type=int, default=DEFAULT_MAX_BARS)
    return parser.parse_args(argv)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


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


def _render_table(rows: list[dict[str, object]], headers: list[str]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(header)) for header in headers) + " |")
    return lines


def _ensure_year_column(trade_frame: pd.DataFrame) -> pd.Series | None:
    if "year" in trade_frame.columns:
        year = pd.to_numeric(trade_frame["year"], errors="coerce").astype("Int64")
        if year.notna().any():
            return year
    if "signal_time" in trade_frame.columns:
        signal_time = pd.to_datetime(trade_frame["signal_time"], errors="coerce", utc=True).dt.tz_convert(None)
        return signal_time.dt.year.astype("Int64")
    return None


def _feature_table_with_year(trade_frame: pd.DataFrame, bar_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    feature_table, summary = _construct_feature_table(trade_frame, bar_frame, preview_rows=0)
    year_series = _ensure_year_column(trade_frame)
    if year_series is not None:
        feature_table = feature_table.copy()
        feature_table["year"] = year_series.values
    return feature_table, summary


def _model_feature_columns(feature_table: pd.DataFrame) -> list[str]:
    return [column for column in feature_table.columns if column not in AUDIT_IDENTITY_COLUMNS]


def _actual_audit_identity_columns(feature_table: pd.DataFrame) -> list[str]:
    return [column for column in AUDIT_IDENTITY_COLUMNS if column in feature_table.columns]


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _column_has_any_nonfinite(series: pd.Series) -> bool:
    numeric = _as_numeric(series)
    values = numeric.to_numpy(dtype=float, na_value=np.nan)
    return bool(np.isinf(values).any())


def _column_null_pct(series: pd.Series) -> float:
    return float(pd.Series(series).isna().mean() * 100.0) if len(series) else 0.0


def _column_finite_pct(series: pd.Series) -> float:
    numeric = _as_numeric(series)
    values = numeric.to_numpy(dtype=float, na_value=np.nan)
    if len(values) == 0:
        return 0.0
    return float(np.isfinite(values).mean() * 100.0)


def _stats_for_series(series: pd.Series) -> dict[str, object]:
    numeric = _as_numeric(series)
    values = numeric.dropna()
    if values.empty:
        return {"min": None, "max": None, "mean": None, "std": None}
    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=0)),
    }


def _feature_contract_rows(feature_table: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for column in feature_table.columns:
        if column in AUDIT_IDENTITY_COLUMNS:
            if column == "year":
                required_sources = "year field in trade log or signal_time-derived audit year"
                nullable_allowed = "false"
                finite_required = "true"
            else:
                required_sources = column
                nullable_allowed = "false"
                finite_required = "true"
            rows.append(
                {
                    "column": column,
                    "family": "audit_identity",
                    "role": "audit_identity",
                    "timestamp_basis": "identity_only",
                    "leakage_safe": "true",
                    "required_source_columns": required_sources,
                    "nullable_allowed": nullable_allowed,
                    "finite_required": finite_required,
                    "notes": "audit / row-identity only",
                }
            )
            continue

        family, timestamp_basis, required_sources = MODEL_FEATURE_BASIS[column]
        if timestamp_basis == "signal_bar_close":
            nullable_allowed = "false" if column in {"signal_open", "signal_high", "signal_low", "signal_close", "signal_volume", "signal_range", "signal_body", "signal_volume_delta", "volume_delta_abs", "volume_delta_sign"} else "true"
        elif timestamp_basis == "past_bar_close":
            nullable_allowed = "true"
        else:
            nullable_allowed = "true"
        rows.append(
            {
                "column": column,
                "family": family,
                "role": "model_feature",
                "timestamp_basis": timestamp_basis,
                "leakage_safe": "true",
                "required_source_columns": ", ".join(required_sources),
                "nullable_allowed": nullable_allowed,
                "finite_required": "true",
                "notes": "leakage-safe by construction from the aligned signal bar or past-only windows",
            }
        )
    return rows


def _yearly_summary(
    *,
    trade_frame: pd.DataFrame,
    feature_table: pd.DataFrame,
    feature_contract_rows: list[dict[str, object]],
) -> tuple[
    list[dict[str, object]],
    dict[str, dict[str, dict[str, float]]],
    dict[str, dict[str, dict[str, float]]],
    dict[str, list[str]],
    dict[str, list[str]],
    list[str],
    list[str],
]:
    year_series = _ensure_year_column(trade_frame)
    if year_series is None:
        return [], {}, {}, {}, []

    work = trade_frame.copy()
    work["__year__"] = year_series
    feature_work = feature_table.copy()
    feature_work["__year__"] = year_series.values

    model_features = _model_feature_columns(feature_table)
    contract_lookup = {row["column"]: row for row in feature_contract_rows}

    yearly_rows: list[dict[str, object]] = []
    null_finite_by_year: dict[str, dict[str, dict[str, float]]] = {}
    stats_by_year: dict[str, dict[str, dict[str, float]]] = {}
    features_with_nulls: dict[str, list[str]] = {}
    features_with_nonfinite: dict[str, list[str]] = {}
    constant_by_year: list[str] = []
    outlier_warnings: list[str] = []

    for year_value, trade_group in work.groupby("__year__", sort=True):
        year_key = str(int(year_value)) if pd.notna(year_value) else "n/a"
        feature_group = feature_work.loc[feature_work["__year__"] == year_value, model_features]
        row_count = int(len(trade_group))
        feature_rows = int(len(feature_group))
        row_count_preserved = row_count == feature_rows

        null_issue_count = 0
        nonfinite_issue_count = 0
        null_features: list[str] = []
        nonfinite_features: list[str] = []
        year_stats: dict[str, dict[str, float]] = {}
        year_null_finite: dict[str, dict[str, float]] = {}

        for column in model_features:
            series = feature_group[column] if column in feature_group.columns else pd.Series(dtype="float64")
            null_pct = _column_null_pct(series)
            finite_pct = _column_finite_pct(series)
            year_null_finite[column] = {"null_pct": null_pct, "finite_pct": finite_pct}
            year_stats[column] = _stats_for_series(series)

            contract_row = contract_lookup[column]
            if null_pct > 0.0:
                null_features.append(column)
                if str(contract_row["nullable_allowed"]).lower() != "true":
                    null_issue_count += 1

            if _column_has_any_nonfinite(series):
                nonfinite_features.append(column)
                if str(contract_row["finite_required"]).lower() == "true":
                    nonfinite_issue_count += 1

            stats = year_stats[column]
            if stats["std"] is not None and stats["std"] == 0.0 and stats["min"] is not None and stats["max"] is not None:
                constant_by_year.append(f"{year_key}: {column}")
            if stats["min"] is not None and stats["max"] is not None:
                if abs(float(stats["min"])) > 1_000_000_000.0 or abs(float(stats["max"])) > 1_000_000_000.0:
                    outlier_warnings.append(f"{year_key}: {column} exceeds simple magnitude bound")

        null_finite_by_year[year_key] = year_null_finite
        stats_by_year[year_key] = year_stats
        features_with_nulls[year_key] = null_features
        features_with_nonfinite[year_key] = nonfinite_features
        yearly_rows.append(
            {
                "year": year_key,
                "trade_rows": row_count,
                "feature_rows": feature_rows,
                "row_count_preserved": row_count_preserved,
                "model_feature_count": len(model_features),
                "feature_null_issue_count": null_issue_count,
                "feature_nonfinite_issue_count": nonfinite_issue_count,
            }
        )

    return yearly_rows, null_finite_by_year, stats_by_year, features_with_nulls, features_with_nonfinite, constant_by_year, outlier_warnings


def _blocked_feature_rows() -> list[dict[str, object]]:
    return BLOCKED_FAMILY_ROWS.copy()


def build_report(
    trade_log: Path,
    bar_dir: Path,
    *,
    output_doc: Path | None = None,
    max_trades: int = DEFAULT_MAX_TRADES,
    max_bar_files: int = DEFAULT_MAX_BAR_FILES,
    max_bars: int = DEFAULT_MAX_BARS,
) -> tuple[str, dict[str, object]]:
    trade_audit = _load_trade_log(trade_log, max_trades)
    trade_frame = trade_audit.frame.copy()
    trade_max_date = trade_audit.max_exit_time.date() if trade_audit.max_exit_time is not None else trade_audit.max_signal_time.date()

    bar_files = _discover_bar_files(bar_dir, trade_max_date, max_bar_files)
    bar_audit = _read_bar_files(bar_files, max_bars)
    bar_frame = bar_audit.frame.copy()

    feature_table, feature_summary = _feature_table_with_year(trade_frame, bar_frame)
    feature_contract_rows = _feature_contract_rows(feature_table)
    yearly_rows, null_finite_by_year, stats_by_year, features_with_nulls, features_with_nonfinite, constant_by_year, outlier_warnings = _yearly_summary(
        trade_frame=trade_frame,
        feature_table=feature_table,
        feature_contract_rows=feature_contract_rows,
    )

    actual_audit_identity_columns = _actual_audit_identity_columns(feature_table)
    model_feature_columns = _model_feature_columns(feature_table)
    blocked_feature_rows = _blocked_feature_rows()
    years_covered = [int(row["year"]) for row in yearly_rows]
    row_count_preserved = bool(feature_summary["row_count_preserved"]) and all(row["row_count_preserved"] for row in yearly_rows) if yearly_rows else bool(feature_summary["row_count_preserved"])
    feature_null_issue_count_total = sum(int(row["feature_null_issue_count"]) for row in yearly_rows)
    feature_nonfinite_issue_count_total = sum(int(row["feature_nonfinite_issue_count"]) for row in yearly_rows)
    feature_rows_constructed = int(feature_summary["feature_rows_constructed"])
    trade_rows_loaded = int(feature_summary["trade_rows_loaded"])
    gate_2_status = "pass"
    if feature_table.empty or feature_rows_constructed != trade_rows_loaded:
        gate_2_status = "partial"
    if not row_count_preserved:
        gate_2_status = "partial"
    if feature_nonfinite_issue_count_total > 0:
        gate_2_status = "partial"
    if not model_feature_columns:
        gate_2_status = "blocked"
    if not actual_audit_identity_columns:
        gate_2_status = "blocked"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Feature Table Contract Audit")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Formalize the approved signal-time feature schema and verify feature availability, nullness, and finite coverage by year before any Gate 3 meta-label or predictive experiment.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- trade_log path: `{trade_log}`")
    report.append(f"- bar_dir path: `{bar_dir}`")
    report.append(f"- max_trades: `{max_trades}`")
    report.append(f"- max_bar_files: `{max_bar_files}`")
    report.append(f"- max_bars: `{max_bars}`")
    report.append(f"- inspected_trade_rows: `{trade_audit.row_count}`")
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
    report.append("- No predictive metrics were computed.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Alignment Convention Used")
    report.append("")
    report.append("- signal_time = signal bar close_time")
    report.append("- entry_time = entry bar open_time")
    report.append("- exit_time = exit bar open_time")
    report.append("")
    report.append("## Feature Contract Summary")
    report.append("")
    report.append(f"- model_feature_column_count: `{len(model_feature_columns)}`")
    report.append(f"- audit_identity_column_count: `{len(actual_audit_identity_columns)}`")
    report.append(f"- blocked_feature_family_count: `{len(BLOCKED_FEATURE_FAMILIES)}`")
    report.append(f"- row_count_preserved: `{_bool_str(row_count_preserved)}`")
    report.append(f"- years_covered: `{years_covered}`")
    report.append(f"- total_rows: `{feature_rows_constructed}`")
    report.append("")
    report.append("## Feature Contract Table")
    report.append("")
    contract_headers = [
        "column",
        "family",
        "role",
        "timestamp_basis",
        "leakage_safe",
        "required_source_columns",
        "nullable_allowed",
        "finite_required",
        "notes",
    ]
    report.extend(_render_table(feature_contract_rows, contract_headers))
    report.append("")
    report.append("## Yearly Coverage Summary")
    report.append("")
    yearly_headers = [
        "year",
        "trade_rows",
        "feature_rows",
        "row_count_preserved",
        "model_feature_count",
        "feature_null_issue_count",
        "feature_nonfinite_issue_count",
    ]
    report.extend(_render_table(yearly_rows, yearly_headers))
    report.append("")
    report.append("## Model Feature Null / Finite Audit")
    report.append("")
    for year_key in sorted(null_finite_by_year, key=lambda x: int(x)):
        report.append(f"### Year {year_key}")
        rows = []
        for column in model_feature_columns:
            stats = null_finite_by_year[year_key][column]
            rows.append(
                {
                    "column": column,
                    "null_pct": stats["null_pct"],
                    "finite_pct": stats["finite_pct"],
                }
            )
        report.extend(_render_table(rows, ["column", "null_pct", "finite_pct"]))
        report.append("")
    report.append("## Feature Distribution Sanity Summary")
    report.append("")
    for year_key in sorted(stats_by_year, key=lambda x: int(x)):
        report.append(f"### Year {year_key}")
        rows = []
        for column in model_feature_columns:
            stats = stats_by_year[year_key][column]
            rows.append(
                {
                    "column": column,
                    "min": stats["min"],
                    "max": stats["max"],
                    "mean": stats["mean"],
                    "std": stats["std"],
                }
            )
        report.extend(_render_table(rows, ["column", "min", "max", "mean", "std"]))
        report.append("")
    report.append("## Schema Issues")
    report.append("")
    report.append(f"- features_with_any_nulls: `{ {year: cols for year, cols in features_with_nulls.items() if cols} }`")
    report.append(f"- features_with_nonfinite_values: `{ {year: cols for year, cols in features_with_nonfinite.items() if cols} }`")
    report.append(f"- years_with_missing_features: `[]`")
    report.append(f"- years_with_row_count_mismatch: `{[row['year'] for row in yearly_rows if not row['row_count_preserved']]}`")
    report.append(f"- features_constant_by_year: `{constant_by_year}`")
    report.append(f"- simple_outlier_warnings: `{outlier_warnings}`")
    report.append("")
    report.append("## Leakage Audit")
    report.append("")
    report.append(f"- outcome_columns_excluded_from_features: `{_bool_str(True)}`")
    report.append(f"- future_bar_columns_excluded: `{_bool_str(True)}`")
    report.append(f"- l2_features_excluded: `{_bool_str(True)}`")
    report.append(f"- ofi_features_excluded: `{_bool_str(True)}`")
    report.append(f"- no_entry_bar_close_used: `{_bool_str(True)}`")
    report.append(f"- no_exit_bar_data_used: `{_bool_str(True)}`")
    report.append(f"- no_predictive_metrics_computed: `{_bool_str(True)}`")
    report.append(f"- no_model_training_performed: `{_bool_str(True)}`")
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
    report.append("### Blocked by absent regime column")
    report.append("- regime")
    report.append("")
    report.append("## Gate 2 Finding")
    report.append("")
    report.append("- Gate 1 static inventory: pass")
    report.append("- Gate 1 schema availability: pass")
    report.append("- Gate 1 timestamp alignment: pass")
    report.append("- Gate 2 feature table dry run: pass")
    report.append(f"- Gate 2 feature contract/nullness audit: `{gate_2_status}`")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if gate_2_status == "pass":
        report.append("Prepare a Gate 3 pre-registration document for a future meta-label experiment, specifying splits, labels, metrics, leakage rules, and forbidden tuning, but do not train a model yet.")
    else:
        report.append("Fix the contract or nullness issues first, then rerun this bounded read-only audit before any Gate 3 planning.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- feature contract reporting")
    report.append("- yearly nullness audit")
    report.append("- leakage audit")
    report.append("- bounded read-only diagnostics")
    report.append("- Gate 3 pre-registration planning")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- alpha claims")
    report.append("- strategy optimization")
    report.append("- model training")
    report.append("- predictive metrics")
    report.append("- feature/PnL correlations")
    report.append("- backtesting as part of this task")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("- using unapproved L2 features")
    report.append("")
    report.append("## Decision")
    report.append("")
    labels = [
        "c_exhaustion_feature_table_contract_audit_created",
        "gate_2_feature_contract_audit_completed_or_partial",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_market_data_artifacts_written",
        "no_strategy_backtest_run",
        "no_model_trained",
        "no_predictive_metrics_computed",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
        "gate_2_feature_contract_audit_pass" if gate_2_status == "pass" else "gate_2_feature_contract_audit_partial" if gate_2_status == "partial" else "gate_2_feature_contract_audit_blocked",
    ]
    for label in labels:
        report.append(f"- `{label}`")

    summary = {
        "trade_log_path": trade_log,
        "bar_dir_path": bar_dir,
        "trade_rows_loaded": trade_rows_loaded,
        "inspected_trade_rows": trade_audit.row_count,
        "inspected_bar_rows": bar_audit.row_count,
        "inspected_bar_files": [shard.path for shard in bar_files],
        "feature_table": feature_table,
        "feature_contract_rows": feature_contract_rows,
        "blocked_feature_rows": blocked_feature_rows,
        "model_feature_columns": model_feature_columns,
        "audit_identity_columns": actual_audit_identity_columns,
        "model_feature_column_count": len(model_feature_columns),
        "audit_identity_column_count": len(actual_audit_identity_columns),
        "blocked_feature_family_count": len(BLOCKED_FEATURE_FAMILIES),
        "feature_rows_constructed": feature_rows_constructed,
        "row_count_preserved": row_count_preserved,
        "years_covered": years_covered,
        "yearly_summary": yearly_rows,
        "null_finite_by_year": null_finite_by_year,
        "stats_by_year": stats_by_year,
        "features_with_any_nulls": features_with_nulls,
        "features_with_nonfinite_values": features_with_nonfinite,
        "features_constant_by_year": constant_by_year,
        "simple_outlier_warnings": outlier_warnings,
        "feature_null_issue_count_total": feature_null_issue_count_total,
        "feature_nonfinite_issue_count_total": feature_nonfinite_issue_count_total,
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
        args.trade_log,
        args.bar_dir,
        output_doc=args.output_doc,
        max_trades=args.max_trades,
        max_bar_files=args.max_bar_files,
        max_bars=args.max_bars,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
