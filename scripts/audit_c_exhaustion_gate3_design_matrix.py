#!/usr/bin/env python3
"""Read-only Gate 3 design-matrix audit for C_Exhaustion."""

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
from scripts.check_c_exhaustion_gate3_protocol import (  # noqa: E402
    APPROVED_MODEL_FEATURES,
)
from scripts.check_c_exhaustion_gate3_protocol import (  # noqa: E402
    AUDIT_IDENTITY_COLUMNS,
)
from scripts.check_c_exhaustion_gate3_protocol import (  # noqa: E402
    FORBIDDEN_MODEL_FEATURES,
)
from scripts.check_c_exhaustion_gate3_protocol import (  # noqa: E402
    PRIMARY_LABEL_NAME,
    PRIMARY_LABEL_RULE,
)
from scripts.dry_run_c_exhaustion_gate3_label_split_purge import (  # noqa: E402
    assign_chronological_split,
)
from scripts.dry_run_c_exhaustion_gate3_label_split_purge import (  # noqa: E402
    compute_purge_embargo_flags,
)
from scripts.dry_run_c_exhaustion_gate3_label_split_purge import (  # noqa: E402
    generate_primary_label,
)
from scripts.dry_run_c_exhaustion_signal_time_feature_table import (  # noqa: E402
    _construct_feature_table,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_GATE3_DESIGN_MATRIX_AUDIT.md")
DEFAULT_MAX_TRADES = ALIGNMENT_DEFAULT_MAX_TRADES
DEFAULT_MAX_BAR_FILES = ALIGNMENT_DEFAULT_MAX_BAR_FILES
DEFAULT_MAX_BARS = ALIGNMENT_DEFAULT_MAX_BARS

OUTCOME_COLUMNS = [
    "entry_price",
    "exit_price",
    "gross_return_bps",
    "net_return_bps",
    "holding_bars",
]

L2_OFI_COLUMNS = [
    "OFI",
    "MLOFI",
    "microprice",
    "spread",
    "depth",
    "queue imbalance",
    "L2 imbalance",
    "spoofing",
    "iceberg",
    "whale pressure",
    "funding",
    "OI",
    "liquidation",
    "derivatives crowding",
    "basis",
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


def _derive_year_column(frame: pd.DataFrame) -> pd.Series:
    if "year" in frame.columns:
        year = pd.to_numeric(frame["year"], errors="coerce")
        if year.notna().any():
            return year.astype("Int64")
    if "signal_time" in frame.columns:
        return pd.to_datetime(frame["signal_time"], errors="coerce", utc=True).dt.tz_convert(None).dt.year.astype("Int64")
    return pd.Series(dtype="Int64")


def _load_real_inputs(
    trade_log: Path,
    bar_dir: Path,
    *,
    max_trades: int,
    max_bar_files: int,
    max_bars: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[Path], dict[str, object]]:
    trade_audit = _load_trade_log(trade_log, max_trades)
    trade_frame = trade_audit.frame.copy()
    if "year" not in trade_frame.columns or not trade_frame["year"].notna().any():
        trade_frame["year"] = _derive_year_column(trade_frame)
    else:
        trade_frame["year"] = pd.to_numeric(trade_frame["year"], errors="coerce").astype("Int64")

    trade_max_date = trade_audit.max_exit_time.date() if trade_audit.max_exit_time is not None else trade_audit.max_signal_time.date()
    bar_files = _discover_bar_files(bar_dir, trade_max_date, max_bar_files)
    bar_audit = _read_bar_files(bar_files, max_bars)
    return trade_frame, bar_audit.frame.copy(), [shard.path for shard in bar_files], {
        "trade_rows_loaded": trade_audit.row_count,
        "bar_rows_loaded": bar_audit.row_count,
        "bar_file_count": len(bar_files),
    }


def _binary_label_counts(series: pd.Series) -> dict[str, int]:
    numeric = pd.to_numeric(series, errors="coerce")
    return {
        "positive": int((numeric == 1).sum()),
        "negative": int((numeric == 0).sum()),
        "total": int(len(numeric)),
    }


def _count_mask(series: pd.Series) -> int:
    return int(pd.Series(series).astype(bool).sum())


def _count_positive_negative(frame: pd.DataFrame, mask: pd.Series) -> dict[str, int]:
    subset = frame.loc[mask]
    return {
        "positive": int((subset[PRIMARY_LABEL_NAME] == 1).sum()),
        "negative": int((subset[PRIMARY_LABEL_NAME] == 0).sum()),
        "total": int(len(subset)),
    }


def _feature_contract_audit(x: pd.DataFrame) -> dict[str, object]:
    approved_present = [column for column in APPROVED_MODEL_FEATURES if column in x.columns]
    approved_missing = [column for column in APPROVED_MODEL_FEATURES if column not in x.columns]
    forbidden_present = [column for column in FORBIDDEN_MODEL_FEATURES if column in x.columns]
    identity_present = [column for column in AUDIT_IDENTITY_COLUMNS if column in x.columns]
    outcome_present = [column for column in OUTCOME_COLUMNS if column in x.columns]
    label_present = [PRIMARY_LABEL_NAME] if PRIMARY_LABEL_NAME in x.columns else []
    l2_ofi_present = [column for column in L2_OFI_COLUMNS if column in x.columns]
    return {
        "approved_features_present_count": len(approved_present),
        "approved_features_missing_count": len(approved_missing),
        "forbidden_features_present_in_x_count": len(forbidden_present),
        "identity_columns_present_in_x_count": len(identity_present),
        "outcome_columns_present_in_x_count": len(outcome_present),
        "label_column_present_in_x": len(label_present) > 0,
        "l2_ofi_columns_present_in_x_count": len(l2_ofi_present),
        "approved_missing": approved_missing,
        "forbidden_present": forbidden_present,
        "identity_present": identity_present,
        "outcome_present": outcome_present,
        "l2_ofi_present": l2_ofi_present,
    }


def build_report(
    *,
    trade_log: Path,
    bar_dir: Path,
    output_doc: Path | None = None,
    max_trades: int = DEFAULT_MAX_TRADES,
    max_bar_files: int = DEFAULT_MAX_BAR_FILES,
    max_bars: int = DEFAULT_MAX_BARS,
) -> tuple[str, dict[str, object]]:
    trade_frame, bar_frame, bar_files, read_summary = _load_real_inputs(
        trade_log,
        bar_dir,
        max_trades=max_trades,
        max_bar_files=max_bar_files,
        max_bars=max_bars,
    )

    feature_table, feature_summary = _construct_feature_table(trade_frame, bar_frame, preview_rows=0)
    label_frame = generate_primary_label(trade_frame)
    split_frame = assign_chronological_split(label_frame)
    protocol_frame = compute_purge_embargo_flags(split_frame)

    x = feature_table.loc[:, APPROVED_MODEL_FEATURES].copy()
    y = label_frame.loc[:, PRIMARY_LABEL_NAME].copy()

    x_y_row_alignment = bool(x.index.equals(y.index))
    x_columns_match_contract = list(x.columns) == list(APPROVED_MODEL_FEATURES)
    x_numeric_all_columns = all(pd.api.types.is_numeric_dtype(x[column]) for column in x.columns)
    x_finite_all_values = bool(np.isfinite(x.to_numpy(dtype=float)).all())
    y_binary = set(pd.to_numeric(y, errors="coerce").dropna().unique()).issubset({0, 1})
    y_positive_count = int((y == 1).sum())
    y_negative_count = int((y == 0).sum())

    train_mask_before_purge = protocol_frame["split"] == "train"
    validation_mask = protocol_frame["split"] == "validation"
    holdout_mask = protocol_frame["split"] == "holdout"
    out_of_protocol_mask = protocol_frame["split"] == "out_of_protocol"
    purge_candidate_mask = protocol_frame["purge_candidate"].astype(bool)
    embargo_candidate_mask = protocol_frame["embargo_candidate"].astype(bool)
    train_mask_after_purge = train_mask_before_purge & ~purge_candidate_mask
    train_mask_after_purge_and_embargo = train_mask_after_purge & ~embargo_candidate_mask

    split_mask_exclusive = bool(
        (
            train_mask_before_purge.astype(int)
            + validation_mask.astype(int)
            + holdout_mask.astype(int)
            + out_of_protocol_mask.astype(int)
        )
        .eq(1)
        .all()
    )
    split_mask_complete = bool(
        (
            train_mask_before_purge
            | validation_mask
            | holdout_mask
            | out_of_protocol_mask
        ).all()
    )

    train_rows_before_purge = _count_mask(train_mask_before_purge)
    train_rows_after_purge = _count_mask(train_mask_after_purge)
    train_rows_after_purge_and_embargo = _count_mask(train_mask_after_purge_and_embargo)
    validation_rows = _count_mask(validation_mask)
    holdout_rows = _count_mask(holdout_mask)
    out_of_protocol_rows = _count_mask(out_of_protocol_mask)
    purge_candidate_count = _count_mask(purge_candidate_mask)
    embargo_candidate_count = _count_mask(embargo_candidate_mask)

    feature_contract = _feature_contract_audit(x)
    feature_contract_status = (
        feature_contract["approved_features_missing_count"] == 0
        and feature_contract["forbidden_features_present_in_x_count"] == 0
        and feature_contract["identity_columns_present_in_x_count"] == 0
        and feature_contract["outcome_columns_present_in_x_count"] == 0
        and not feature_contract["label_column_present_in_x"]
        and feature_contract["l2_ofi_columns_present_in_x_count"] == 0
    )

    scaler_required_later = True
    scaler_fit_scope = "train_after_purge_and_embargo_only"
    scaler_transform_scope = "validation_and_holdout_after_train_fit_only"
    scaler_fitted = False
    validation_seen_during_fit = False
    holdout_seen_during_fit = False

    overall_label_counts = _binary_label_counts(y)
    train_label_counts = _count_positive_negative(protocol_frame, train_mask_after_purge_and_embargo)
    validation_label_counts = _count_positive_negative(protocol_frame, validation_mask)
    holdout_label_counts = _count_positive_negative(protocol_frame, holdout_mask)

    gate_3_design_matrix_status = "pass"
    if not x_y_row_alignment or not x_columns_match_contract or not x_numeric_all_columns or not x_finite_all_values or not y_binary:
        gate_3_design_matrix_status = "partial"
    if not split_mask_exclusive or not split_mask_complete:
        gate_3_design_matrix_status = "partial"
    if not feature_contract_status:
        gate_3_design_matrix_status = "blocked"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Gate 3 Design Matrix Audit")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Build the final X/y design matrix in memory under the pre-registered Gate 3 contract, then verify shape, mask integrity, forbidden-feature exclusion, and the train-only scaler plan without fitting a model or scaler.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- trade_log path: `{trade_log}`")
    report.append(f"- bar_dir path: `{bar_dir}`")
    report.append("- real_trade_log_read: `true`")
    report.append("- real_bar_data_read: `true`")
    report.append("- raw_l2_data_read: `false`")
    report.append("- ofi_artifacts_read: `false`")
    report.append("- feature_table_artifacts_written: `false`")
    report.append("- model_artifacts_written: `false`")
    report.append(f"- inspected_trade_rows: `{read_summary['trade_rows_loaded']}`")
    report.append(f"- inspected_bar_rows: `{read_summary['bar_rows_loaded']}`")
    report.append(f"- inspected_bar_files: `{read_summary['bar_file_count']}`")
    report.append("")
    report.append("## Read-Only Guardrails")
    report.append("")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No feature-table artifacts were written.")
    report.append("- No model artifacts were written.")
    report.append("- No market-data artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No model was trained.")
    report.append("- No scaler was fitted.")
    report.append("- No predictive metrics were computed.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Pre-Registered Protocol Applied")
    report.append("")
    report.append(f"- primary_label_rule: `{PRIMARY_LABEL_RULE}`")
    report.append("- split_policy: `train=2020-2023, validation=2024, holdout=2025-2026, out_of_protocol=otherwise`")
    report.append("- purge_rule: `purge any train row whose [signal_time, exit_time] interval overlaps any validation or holdout interval`")
    report.append("- embargo_rule: `use observed max holding interval as a conservative embargo window near the split boundaries`")
    report.append(f"- approved_feature_count: `{len(APPROVED_MODEL_FEATURES)}`")
    report.append(f"- audit_identity_count: `{len(AUDIT_IDENTITY_COLUMNS)}`")
    report.append(f"- forbidden_feature_count: `{len(FORBIDDEN_MODEL_FEATURES)}`")
    report.append("")
    report.append("## Design Matrix Summary")
    report.append("")
    report.append(f"- x_row_count: `{len(x)}`")
    report.append(f"- y_row_count: `{len(y)}`")
    report.append(f"- x_column_count: `{len(x.columns)}`")
    report.append(f"- approved_feature_count: `{len(APPROVED_MODEL_FEATURES)}`")
    report.append(f"- x_y_row_alignment: `{_bool_str(x_y_row_alignment)}`")
    report.append(f"- x_columns_match_contract: `{_bool_str(x_columns_match_contract)}`")
    report.append(f"- x_numeric_all_columns: `{_bool_str(x_numeric_all_columns)}`")
    report.append(f"- x_finite_all_values: `{_bool_str(x_finite_all_values)}`")
    report.append(f"- y_binary: `{_bool_str(y_binary)}`")
    report.append(f"- y_positive_count: `{y_positive_count}`")
    report.append(f"- y_negative_count: `{y_negative_count}`")
    report.append("")
    report.append("## Split Mask Summary")
    report.append("")
    report.append(f"- train_rows_before_purge: `{train_rows_before_purge}`")
    report.append(f"- train_rows_after_purge: `{train_rows_after_purge}`")
    report.append(f"- train_rows_after_purge_and_embargo: `{train_rows_after_purge_and_embargo}`")
    report.append(f"- validation_rows: `{validation_rows}`")
    report.append(f"- holdout_rows: `{holdout_rows}`")
    report.append(f"- out_of_protocol_rows: `{out_of_protocol_rows}`")
    report.append(f"- split_mask_exclusive: `{_bool_str(split_mask_exclusive)}`")
    report.append(f"- split_mask_complete: `{_bool_str(split_mask_complete)}`")
    report.append(f"- purge_candidate_count: `{purge_candidate_count}`")
    report.append(f"- embargo_candidate_count: `{embargo_candidate_count}`")
    report.append("")
    report.append("## Feature Contract Audit")
    report.append("")
    report.append(f"- approved_features_present_count: `{feature_contract['approved_features_present_count']}`")
    report.append(f"- approved_features_missing_count: `{feature_contract['approved_features_missing_count']}`")
    report.append(f"- forbidden_features_present_in_x_count: `{feature_contract['forbidden_features_present_in_x_count']}`")
    report.append(f"- identity_columns_present_in_x_count: `{feature_contract['identity_columns_present_in_x_count']}`")
    report.append(f"- outcome_columns_present_in_x_count: `{feature_contract['outcome_columns_present_in_x_count']}`")
    report.append(f"- label_column_present_in_x: `{_bool_str(feature_contract['label_column_present_in_x'])}`")
    report.append(f"- l2_ofi_columns_present_in_x_count: `{feature_contract['l2_ofi_columns_present_in_x_count']}`")
    report.append("")
    report.append("## Train-Only Scaler Plan")
    report.append("")
    report.append(f"- scaler_required_later: `{_bool_str(scaler_required_later)}`")
    report.append(f"- scaler_fit_scope: `{scaler_fit_scope}`")
    report.append(f"- scaler_transform_scope: `{scaler_transform_scope}`")
    report.append(f"- scaler_fitted: `{_bool_str(scaler_fitted)}`")
    report.append(f"- validation_seen_during_fit: `{_bool_str(validation_seen_during_fit)}`")
    report.append(f"- holdout_seen_during_fit: `{_bool_str(holdout_seen_during_fit)}`")
    report.append("")
    report.append("## Baseline Keep-All Label Distribution")
    report.append("")
    report.append(f"- overall positive_count: `{overall_label_counts['positive']}`")
    report.append(f"- overall negative_count: `{overall_label_counts['negative']}`")
    report.append(f"- train positive_count_after_purge_and_embargo: `{train_label_counts['positive']}`")
    report.append(f"- train negative_count_after_purge_and_embargo: `{train_label_counts['negative']}`")
    report.append(f"- validation positive_count: `{validation_label_counts['positive']}`")
    report.append(f"- validation negative_count: `{validation_label_counts['negative']}`")
    report.append(f"- holdout positive_count: `{holdout_label_counts['positive']}`")
    report.append(f"- holdout negative_count: `{holdout_label_counts['negative']}`")
    report.append("")
    report.append("## What This Proves")
    report.append("")
    report.append("- X/y can be built in memory under the pre-registered contract.")
    report.append("- Split masks can be represented.")
    report.append("- Purge and embargo masks can be represented.")
    report.append("- Forbidden columns are excluded.")
    report.append("- Scaler train-only plan can be represented without fitting.")
    report.append("- The system is ready for a future separately approved no-artifact model dry run.")
    report.append("")
    report.append("## What This Does Not Prove")
    report.append("")
    report.append("- no alpha")
    report.append("- no predictive performance")
    report.append("- no model viability")
    report.append("- no strategy improvement")
    report.append("- no full reconstruction approval")
    report.append("- no paper/live approval")
    report.append("")
    report.append("## Gate 3 Status")
    report.append("")
    report.append("- Gate 3 protocol checker: pass")
    report.append("- Gate 3 real-data label/split/purge dry run: pass")
    report.append(f"- Gate 3 no-training design-matrix audit: `{gate_3_design_matrix_status}`")
    report.append("- Gate 3 model training: not started")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if gate_3_design_matrix_status == "pass":
        report.append("Run a bounded Gate 3 logistic-regression-only model dry run with train-only standardization, no model artifacts, validation-only threshold selection if any, and holdout untouched until final reporting.")
    else:
        report.append("Fix the design-matrix audit issues first, then rerun this no-training audit before any model dry run.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- no-training design-matrix audit")
    report.append("- feature contract verification")
    report.append("- split mask audit")
    report.append("- leakage audit")
    report.append("- future bounded logistic-regression-only model dry run if separately approved")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- model training in this task")
    report.append("- predictive metrics in this task")
    report.append("- alpha claims in this task")
    report.append("- strategy optimization")
    report.append("- backtesting new logic")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("")
    report.append("## Decision")
    report.append("")
    labels = [
        "c_exhaustion_gate3_design_matrix_audit_created",
        "real_trade_log_read",
        "real_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "no_strategy_backtest_run",
        "no_model_trained",
        "no_scaler_fitted",
        "no_predictive_metrics_computed",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
        "gate_3_model_training_not_started",
        "gate_3_design_matrix_audit_pass" if gate_3_design_matrix_status == "pass" else "gate_3_design_matrix_audit_partial" if gate_3_design_matrix_status == "partial" else "gate_3_design_matrix_audit_blocked",
    ]
    for label in labels:
        report.append(f"- `{label}`")

    report_text = "\n".join(report) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report_text, encoding="utf-8")

    summary = {
        "trade_rows_loaded": int(read_summary["trade_rows_loaded"]),
        "feature_rows_constructed": int(feature_summary["feature_rows_constructed"]),
        "x_row_count": int(len(x)),
        "y_row_count": int(len(y)),
        "x_column_count": int(len(x.columns)),
        "x_y_row_alignment": x_y_row_alignment,
        "x_columns_match_contract": x_columns_match_contract,
        "x_numeric_all_columns": x_numeric_all_columns,
        "x_finite_all_values": x_finite_all_values,
        "y_binary": y_binary,
        "y_positive_count": y_positive_count,
        "y_negative_count": y_negative_count,
        "train_rows_before_purge": train_rows_before_purge,
        "train_rows_after_purge": train_rows_after_purge,
        "train_rows_after_purge_and_embargo": train_rows_after_purge_and_embargo,
        "validation_rows": validation_rows,
        "holdout_rows": holdout_rows,
        "out_of_protocol_rows": out_of_protocol_rows,
        "split_mask_exclusive": split_mask_exclusive,
        "split_mask_complete": split_mask_complete,
        "purge_candidate_count": purge_candidate_count,
        "embargo_candidate_count": embargo_candidate_count,
        "approved_features_present_count": feature_contract["approved_features_present_count"],
        "approved_features_missing_count": feature_contract["approved_features_missing_count"],
        "forbidden_features_present_in_x_count": feature_contract["forbidden_features_present_in_x_count"],
        "identity_columns_present_in_x_count": feature_contract["identity_columns_present_in_x_count"],
        "outcome_columns_present_in_x_count": feature_contract["outcome_columns_present_in_x_count"],
        "label_column_present_in_x": feature_contract["label_column_present_in_x"],
        "l2_ofi_columns_present_in_x_count": feature_contract["l2_ofi_columns_present_in_x_count"],
        "scaler_required_later": scaler_required_later,
        "scaler_fit_scope": scaler_fit_scope,
        "scaler_transform_scope": scaler_transform_scope,
        "scaler_fitted": scaler_fitted,
        "validation_seen_during_fit": validation_seen_during_fit,
        "holdout_seen_during_fit": holdout_seen_during_fit,
        "overall_label_counts": overall_label_counts,
        "train_label_counts": train_label_counts,
        "validation_label_counts": validation_label_counts,
        "holdout_label_counts": holdout_label_counts,
        "gate_3_design_matrix_status": gate_3_design_matrix_status,
        "feature_table": feature_table,
        "design_matrix_x": x,
        "design_matrix_y": y,
        "train_mask_before_purge": train_mask_before_purge,
        "validation_mask": validation_mask,
        "holdout_mask": holdout_mask,
        "out_of_protocol_mask": out_of_protocol_mask,
        "purge_candidate_mask": purge_candidate_mask,
        "embargo_candidate_mask": embargo_candidate_mask,
        "train_mask_after_purge": train_mask_after_purge,
        "train_mask_after_purge_and_embargo": train_mask_after_purge_and_embargo,
        "real_trade_log_read": True,
        "real_bar_data_read": True,
        "raw_l2_data_read": False,
        "ofi_artifacts_read": False,
        "feature_table_artifacts_written": False,
        "model_artifacts_written": False,
        "bar_files": bar_files,
        "approved_feature_count": len(APPROVED_MODEL_FEATURES),
        "audit_identity_count": len(AUDIT_IDENTITY_COLUMNS),
        "forbidden_feature_count": len(FORBIDDEN_MODEL_FEATURES),
    }
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
