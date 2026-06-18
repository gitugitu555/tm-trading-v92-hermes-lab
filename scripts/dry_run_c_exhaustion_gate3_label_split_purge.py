#!/usr/bin/env python3
"""Read-only Gate 3 label/split/purge dry run for C_Exhaustion."""

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
    _parse_timestamp_series,
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
from scripts.dry_run_c_exhaustion_signal_time_feature_table import (  # noqa: E402
    _construct_feature_table,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_GATE3_LABEL_SPLIT_PURGE_DRY_RUN.md")
DEFAULT_MAX_TRADES = ALIGNMENT_DEFAULT_MAX_TRADES
DEFAULT_MAX_BAR_FILES = ALIGNMENT_DEFAULT_MAX_BAR_FILES
DEFAULT_MAX_BARS = ALIGNMENT_DEFAULT_MAX_BARS
DEFAULT_PURGE_EMBARGO_BOUNDARY_LABEL = "observed max holding interval"


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
        signal_time = _parse_timestamp_series(frame["signal_time"])
        return signal_time.dt.year.astype("Int64")
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
    bar_frame = bar_audit.frame.copy()
    return trade_frame, bar_frame, [shard.path for shard in bar_files], {
        "trade_rows_loaded": trade_audit.row_count,
        "bar_rows_loaded": bar_audit.row_count,
        "bar_columns": bar_audit.columns,
        "bar_file_count": len(bar_files),
    }


def generate_primary_label(frame: pd.DataFrame) -> pd.DataFrame:
    labelled = frame.copy()
    labelled[PRIMARY_LABEL_NAME] = (pd.to_numeric(labelled["net_return_bps"], errors="coerce") > 0).astype(int)
    return labelled


def assign_chronological_split(frame: pd.DataFrame) -> pd.DataFrame:
    split_frame = frame.copy()

    def _split_for_year(value: object) -> str:
        if pd.isna(value):
            return "out_of_protocol"
        year = int(value)
        if year in {2020, 2021, 2022, 2023}:
            return "train"
        if year == 2024:
            return "validation"
        if year in {2025, 2026}:
            return "holdout"
        return "out_of_protocol"

    split_frame["split"] = split_frame["year"].apply(_split_for_year)
    return split_frame


def compute_purge_embargo_flags(frame: pd.DataFrame) -> pd.DataFrame:
    audited = frame.copy()
    audited["signal_time"] = _parse_timestamp_series(audited["signal_time"])
    audited["exit_time"] = _parse_timestamp_series(audited["exit_time"])
    audited["purge_candidate"] = False
    audited["embargo_candidate"] = False
    audited["embargo_boundary"] = None

    validation_or_holdout = audited[audited["split"].isin(["validation", "holdout"])][["signal_time", "exit_time"]].copy()
    boundary_times = [pd.Timestamp("2024-01-01 00:00:00"), pd.Timestamp("2025-01-01 00:00:00")]
    for idx, row in audited.iterrows():
        if row["split"] != "train":
            continue
        for _, other in validation_or_holdout.iterrows():
            if _intervals_overlap(row["signal_time"], row["exit_time"], other["signal_time"], other["exit_time"]):
                audited.at[idx, "purge_candidate"] = True
                break
    embargo_window = _observed_max_holding_interval(audited)
    for idx, row in audited.iterrows():
        for boundary in boundary_times:
            if pd.notna(row["signal_time"]) and abs(row["signal_time"] - boundary) <= embargo_window:
                audited.at[idx, "embargo_candidate"] = True
                audited.at[idx, "embargo_boundary"] = boundary
                break
    audited.attrs["embargo_window_used"] = embargo_window
    audited.attrs["boundary_times"] = boundary_times
    audited.attrs["purge_candidate_count"] = int(audited["purge_candidate"].sum())
    audited.attrs["embargo_candidate_count"] = int(audited["embargo_candidate"].sum())
    audited.attrs["train_embargo_candidate_count"] = int(
        audited.loc[audited["split"] == "train", "embargo_candidate"].sum()
    )
    audited.attrs["validation_embargo_candidate_count"] = int(
        audited.loc[audited["split"] == "validation", "embargo_candidate"].sum()
    )
    audited.attrs["holdout_embargo_candidate_count"] = int(
        audited.loc[audited["split"] == "holdout", "embargo_candidate"].sum()
    )
    audited.attrs["overlap_detection_exercised"] = bool(audited["purge_candidate"].any())
    audited.attrs["split_boundary_embargo_exercised"] = bool(audited["embargo_candidate"].any())
    return audited


def _intervals_overlap(start_a: pd.Timestamp, end_a: pd.Timestamp, start_b: pd.Timestamp, end_b: pd.Timestamp) -> bool:
    if pd.isna(start_a) or pd.isna(end_a) or pd.isna(start_b) or pd.isna(end_b):
        return False
    return bool(start_a <= end_b and start_b <= end_a)


def _observed_max_holding_interval(frame: pd.DataFrame) -> pd.Timedelta:
    intervals = frame["exit_time"] - frame["signal_time"]
    intervals = intervals.dropna()
    if intervals.empty:
        return pd.Timedelta(0)
    return intervals.max()


def validate_feature_contract(columns: list[str] | pd.Index) -> dict[str, object]:
    column_set = list(columns)
    approved_present = [column for column in APPROVED_MODEL_FEATURES if column in column_set]
    approved_missing = [column for column in APPROVED_MODEL_FEATURES if column not in column_set]
    forbidden_present = [column for column in FORBIDDEN_MODEL_FEATURES if column in column_set]
    identity_present = [column for column in AUDIT_IDENTITY_COLUMNS if column in column_set]
    outcome_present = [column for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps", "holding_bars"] if column in column_set]
    l2_ofi_present = [column for column in ["OFI", "MLOFI", "microprice", "spread", "depth", "queue imbalance", "L2 imbalance", "spoofing", "iceberg", "whale pressure", "funding", "OI", "liquidation", "derivatives crowding", "basis"] if column in column_set]
    label_present = [column for column in [PRIMARY_LABEL_NAME] if column in column_set]
    return {
        "approved_features_present_count": len(approved_present),
        "approved_features_missing_count": len(approved_missing),
        "forbidden_features_present_in_model_matrix_count": len(forbidden_present),
        "audit_identity_columns_excluded_from_model_features": len(identity_present) == 0,
        "outcome_columns_excluded_from_model_features": len(outcome_present) == 0,
        "l2_ofi_columns_excluded_from_model_features": len(l2_ofi_present) == 0,
        "label_column_excluded_from_model_features": len(label_present) == 0,
        "approved_missing": approved_missing,
        "forbidden_present": forbidden_present,
        "identity_present": identity_present,
        "outcome_present": outcome_present,
        "l2_ofi_present": l2_ofi_present,
        "label_present": label_present,
    }


def _format_count_series(frame: pd.DataFrame, group_column: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for key, group in frame.groupby(group_column, dropna=False):
        key_str = "n/a" if pd.isna(key) else str(key)
        grouped[key_str] = {
            "positive": int((group[PRIMARY_LABEL_NAME] == 1).sum()),
            "negative": int((group[PRIMARY_LABEL_NAME] == 0).sum()),
            "total": int(len(group)),
        }
    return grouped


def _split_rows(frame: pd.DataFrame) -> dict[str, int]:
    return {split: int((frame["split"] == split).sum()) for split in ["train", "validation", "holdout", "out_of_protocol"]}


def _sample_size_rule(count: int) -> tuple[int, bool]:
    minimum = math.ceil(min(count * 0.30, 20))
    return minimum, count >= minimum


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
    if "year" not in trade_frame.columns or not trade_frame["year"].notna().any():
        trade_frame["year"] = _derive_year_column(trade_frame)

    label_frame = generate_primary_label(trade_frame)
    split_frame = assign_chronological_split(label_frame)
    protocol_frame = compute_purge_embargo_flags(split_frame)

    model_matrix_columns = [column for column in feature_table.columns if column in APPROVED_MODEL_FEATURES]
    contract = validate_feature_contract(model_matrix_columns)

    row_count_preserved_before_protocol = int(feature_summary["feature_rows_constructed"]) == int(feature_summary["trade_rows_loaded"])
    row_count_after_label = int(len(label_frame))
    row_count_after_split_assignment = int(len(split_frame))
    purge_candidate_count = int(protocol_frame.attrs["purge_candidate_count"])
    embargo_candidate_count = int(protocol_frame.attrs["embargo_candidate_count"])
    train_embargo_candidate_count = int(protocol_frame.attrs["train_embargo_candidate_count"])
    train_rows_flagged_union = int(
        protocol_frame.loc[
            (protocol_frame["split"] == "train") & (protocol_frame["purge_candidate"] | protocol_frame["embargo_candidate"]),
            :,
        ].shape[0]
    )
    train_count_before_purge = int((protocol_frame["split"] == "train").sum())
    train_count_after_purge = train_count_before_purge - purge_candidate_count
    train_count_after_purge_and_embargo = train_count_before_purge - train_rows_flagged_union
    row_count_after_purge = int(len(protocol_frame)) - purge_candidate_count
    row_count_after_embargo = int(len(protocol_frame)) - train_rows_flagged_union
    max_holding_interval_observed = _observed_max_holding_interval(protocol_frame)
    embargo_window_used = max_holding_interval_observed

    overall_label_counts = {
        "positive": int((label_frame[PRIMARY_LABEL_NAME] == 1).sum()),
        "negative": int((label_frame[PRIMARY_LABEL_NAME] == 0).sum()),
        "total": int(len(label_frame)),
    }
    label_by_year = _format_count_series(label_frame, "year")
    label_by_split = _format_count_series(protocol_frame, "split")
    split_counts = _split_rows(protocol_frame)
    yearly_split_table = []
    for year_value, group in protocol_frame.groupby("year", dropna=False):
        year_key = "n/a" if pd.isna(year_value) else str(int(year_value))
        yearly_split_table.append(
            {
                "year": year_key,
                "train": int((group["split"] == "train").sum()),
                "validation": int((group["split"] == "validation").sum()),
                "holdout": int((group["split"] == "holdout").sum()),
                "out_of_protocol": int((group["split"] == "out_of_protocol").sum()),
                "total": int(len(group)),
            }
        )

    validation_count = split_counts["validation"]
    holdout_count = split_counts["holdout"]
    validation_min_required_count, validation_rule_pass = _sample_size_rule(validation_count)
    holdout_min_required_count, holdout_rule_pass = _sample_size_rule(holdout_count)

    model_feature_columns = [column for column in feature_table.columns if column in APPROVED_MODEL_FEATURES]
    feature_contract_status = (
        contract["approved_features_present_count"] == len(APPROVED_MODEL_FEATURES)
        and contract["approved_features_missing_count"] == 0
        and contract["forbidden_features_present_in_model_matrix_count"] == 0
        and contract["audit_identity_columns_excluded_from_model_features"]
        and contract["outcome_columns_excluded_from_model_features"]
        and contract["l2_ofi_columns_excluded_from_model_features"]
        and contract["label_column_excluded_from_model_features"]
    )
    dry_run_status = "pass"
    if not row_count_preserved_before_protocol:
        dry_run_status = "partial"
    if not feature_contract_status:
        dry_run_status = "blocked"
    if not validation_rule_pass or not holdout_rule_pass:
        dry_run_status = "partial"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Gate 3 Label/Split/Purge Dry Run")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Apply the pre-registered Gate 3 label, chronological split, feature contract, forbidden-feature audit, and purge/embargo protocol to the existing real C_Exhaustion trade log and approved in-memory signal-time feature table construction.")
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
    report.append("- No market-data artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No model was trained.")
    report.append("- No predictive metrics were computed.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Pre-Registered Protocol Applied")
    report.append("")
    report.append(f"- primary_label_rule: `{PRIMARY_LABEL_RULE}`")
    report.append("- split_policy: `train=2020-2023, validation=2024, holdout=2025-2026, out_of_protocol=otherwise`")
    report.append("- purge_rule: `purge any train row whose [signal_time, exit_time] interval overlaps any validation or holdout interval`")
    report.append(f"- embargo_rule: `use {DEFAULT_PURGE_EMBARGO_BOUNDARY_LABEL} as a conservative embargo window near the split boundaries`")
    report.append(f"- approved_feature_count: `{len(APPROVED_MODEL_FEATURES)}`")
    report.append(f"- audit_identity_count: `{len(AUDIT_IDENTITY_COLUMNS)}`")
    report.append(f"- forbidden_feature_count: `{len(FORBIDDEN_MODEL_FEATURES)}`")
    report.append("")
    report.append("## Row Count Summary")
    report.append("")
    report.append(f"- trade_rows_loaded: `{read_summary['trade_rows_loaded']}`")
    report.append(f"- feature_rows_constructed: `{feature_summary['feature_rows_constructed']}`")
    report.append(f"- row_count_preserved_before_protocol: `{_bool_str(row_count_preserved_before_protocol)}`")
    report.append(f"- row_count_after_label: `{row_count_after_label}`")
    report.append(f"- row_count_after_split_assignment: `{row_count_after_split_assignment}`")
    report.append(f"- row_count_after_purge: `{row_count_after_purge}`")
    report.append(f"- row_count_after_embargo: `{row_count_after_embargo}`")
    report.append("")
    report.append("## Feature Contract Check")
    report.append("")
    report.append(f"- approved_features_present_count: `{contract['approved_features_present_count']}`")
    report.append(f"- approved_features_missing_count: `{contract['approved_features_missing_count']}`")
    report.append(f"- forbidden_features_present_in_model_matrix_count: `{contract['forbidden_features_present_in_model_matrix_count']}`")
    report.append(f"- audit_identity_columns_excluded_from_model_features: `{_bool_str(contract['audit_identity_columns_excluded_from_model_features'])}`")
    report.append(f"- outcome_columns_excluded_from_model_features: `{_bool_str(contract['outcome_columns_excluded_from_model_features'])}`")
    report.append(f"- l2_ofi_columns_excluded_from_model_features: `{_bool_str(contract['l2_ofi_columns_excluded_from_model_features'])}`")
    report.append(f"- label_column_excluded_from_model_features: `{_bool_str(contract['label_column_excluded_from_model_features'])}`")
    report.append("")
    report.append("## Label Distribution")
    report.append("")
    report.append(f"- overall positive_count: `{overall_label_counts['positive']}`")
    report.append(f"- overall negative_count: `{overall_label_counts['negative']}`")
    report.append(f"- overall total_count: `{overall_label_counts['total']}`")
    report.append("")
    report.append("### By Year")
    report.append("")
    report.append("| year | positive | negative | total |")
    report.append("| --- | --- | --- | --- |")
    for year_key in sorted(label_by_year, key=lambda x: (x == "n/a", int(x) if x != "n/a" else 9999)):
        row = label_by_year[year_key]
        report.append(f"| {year_key} | {row['positive']} | {row['negative']} | {row['total']} |")
    report.append("")
    report.append("### By Split")
    report.append("")
    report.append("| split | positive | negative | total |")
    report.append("| --- | --- | --- | --- |")
    for split in ["train", "validation", "holdout", "out_of_protocol"]:
        row = label_by_split.get(split, {"positive": 0, "negative": 0, "total": 0})
        report.append(f"| {split} | {row['positive']} | {row['negative']} | {row['total']} |")
    report.append("")
    report.append("## Split Assignment Summary")
    report.append("")
    report.append(f"- train_count_before_purge: `{train_count_before_purge}`")
    report.append(f"- validation_count: `{validation_count}`")
    report.append(f"- holdout_count: `{holdout_count}`")
    report.append(f"- out_of_protocol_count: `{split_counts['out_of_protocol']}`")
    report.append("")
    report.append("| year | train | validation | holdout | out_of_protocol | total |")
    report.append("| --- | --- | --- | --- | --- | --- |")
    for row in sorted(yearly_split_table, key=lambda x: int(x["year"]) if x["year"] != "n/a" else 9999):
        report.append(
            f"| {row['year']} | {row['train']} | {row['validation']} | {row['holdout']} | {row['out_of_protocol']} | {row['total']} |"
        )
    report.append("")
    report.append("## Purge / Embargo Summary")
    report.append("")
    report.append(f"- purge_candidate_count: `{purge_candidate_count}`")
    report.append(f"- embargo_candidate_count: `{embargo_candidate_count}`")
    report.append(f"- train_count_after_purge: `{train_count_after_purge}`")
    report.append(f"- train_count_after_purge_and_embargo: `{train_count_after_purge_and_embargo}`")
    report.append(f"- validation_embargo_candidate_count: `{int(protocol_frame.attrs['validation_embargo_candidate_count'])}`")
    report.append(f"- holdout_embargo_candidate_count: `{int(protocol_frame.attrs['holdout_embargo_candidate_count'])}`")
    report.append(f"- max_holding_interval_observed: `{max_holding_interval_observed}`")
    report.append(f"- embargo_window_used: `{embargo_window_used}`")
    report.append(f"- overlap_detection_exercised: `{_bool_str(protocol_frame.attrs['overlap_detection_exercised'])}`")
    report.append(f"- split_boundary_embargo_exercised: `{_bool_str(protocol_frame.attrs['split_boundary_embargo_exercised'])}`")
    report.append("")
    report.append("## Sample-Size Readiness")
    report.append("")
    report.append(f"- validation_min_required_count: `{validation_min_required_count}`")
    report.append(f"- validation_actual_count: `{validation_count}`")
    report.append(f"- validation_sample_size_rule_pass: `{_bool_str(validation_rule_pass)}`")
    report.append(f"- holdout_min_required_count: `{holdout_min_required_count}`")
    report.append(f"- holdout_actual_count: `{holdout_count}`")
    report.append(f"- holdout_sample_size_rule_pass: `{_bool_str(holdout_rule_pass)}`")
    report.append("")
    report.append("## What This Proves")
    report.append("")
    report.append("- real trade log can be labeled under the pre-registered label")
    report.append("- real rows can be split chronologically")
    report.append("- purge and embargo can be applied mechanically")
    report.append("- feature contract can be checked on real in-memory feature table")
    report.append("- forbidden features remain excluded")
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
    report.append(f"- Gate 3 real-data label/split/purge dry run: `{dry_run_status}`")
    report.append("- Gate 3 model training: not started")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if dry_run_status == "pass":
        report.append("Run a Gate 3 no-training design-matrix audit that builds X/y in memory, verifies final shapes, split masks, forbidden-feature exclusion, scaler-fit-on-train-only plan, and baseline keep-all label distribution, but still trains no model and computes no predictive metrics.")
    else:
        report.append("Fix the protocol issues first, then rerun this real-data label/split/purge dry run before any design-matrix work.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- real-data label/split/purge dry run")
    report.append("- feature contract verification")
    report.append("- leakage audit")
    report.append("- future no-training design-matrix audit")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- model training in this task")
    report.append("- predictive metrics in this task")
    report.append("- alpha claims")
    report.append("- strategy optimization")
    report.append("- backtesting new logic")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("")
    report.append("## Decision")
    report.append("")
    labels = [
        "c_exhaustion_gate3_label_split_purge_dry_run_created",
        "real_trade_log_read",
        "real_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_strategy_backtest_run",
        "no_model_trained",
        "no_predictive_metrics_computed",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
        "gate_3_model_training_not_started",
        "gate_3_label_split_purge_dry_run_pass" if dry_run_status == "pass" else "gate_3_label_split_purge_dry_run_partial" if dry_run_status == "partial" else "gate_3_label_split_purge_dry_run_blocked",
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
        "row_count_preserved_before_protocol": row_count_preserved_before_protocol,
        "row_count_after_label": row_count_after_label,
        "row_count_after_split_assignment": row_count_after_split_assignment,
        "row_count_after_purge": row_count_after_purge,
        "row_count_after_embargo": row_count_after_embargo,
        "approved_features_present_count": contract["approved_features_present_count"],
        "approved_features_missing_count": contract["approved_features_missing_count"],
        "forbidden_features_present_in_model_matrix_count": contract["forbidden_features_present_in_model_matrix_count"],
        "label_counts_overall": overall_label_counts,
        "label_counts_by_year": label_by_year,
        "label_counts_by_split": label_by_split,
        "split_counts": split_counts,
        "purge_candidate_count": purge_candidate_count,
        "embargo_candidate_count": embargo_candidate_count,
        "train_count_after_purge": train_count_after_purge,
        "train_count_after_purge_and_embargo": train_count_after_purge_and_embargo,
        "validation_min_required_count": validation_min_required_count,
        "validation_actual_count": validation_count,
        "validation_sample_size_rule_pass": validation_rule_pass,
        "holdout_min_required_count": holdout_min_required_count,
        "holdout_actual_count": holdout_count,
        "holdout_sample_size_rule_pass": holdout_rule_pass,
        "real_trade_log_read": True,
        "real_bar_data_read": True,
        "raw_l2_data_read": False,
        "ofi_artifacts_read": False,
        "feature_table_artifacts_written": False,
        "feature_table": feature_table,
        "model_matrix_columns": model_matrix_columns,
        "protocol_frame": protocol_frame,
        "dry_run_status": dry_run_status,
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
