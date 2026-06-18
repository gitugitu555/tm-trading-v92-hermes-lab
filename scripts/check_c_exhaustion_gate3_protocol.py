#!/usr/bin/env python3
"""Synthetic-only Gate 3 protocol checker for C_Exhaustion meta-label pre-registration."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pandas as pd

APPROVED_MODEL_FEATURES = [
    "signal_open",
    "signal_high",
    "signal_low",
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
]

AUDIT_IDENTITY_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
    "year",
]

FORBIDDEN_MODEL_FEATURES = [
    "entry_price",
    "exit_price",
    "gross_return_bps",
    "net_return_bps",
    "holding_bars",
    "exit_time",
    "exit_index",
    "entry_time",
    "entry_index",
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

PRIMARY_LABEL_NAME = "label_keep"
PRIMARY_LABEL_RULE = "net_return_bps > 0"

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_GATE3_PROTOCOL_CHECK.md")
SPLIT_BOUNDARIES = [pd.Timestamp("2024-01-01T00:00:00"), pd.Timestamp("2025-01-01T00:00:00")]
DEFAULT_EMBARGO = pd.Timedelta(days=1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _synthetic_fixture() -> pd.DataFrame:
    rows = [
        {
            "signal_index": 10,
            "entry_index": 11,
            "exit_index": 12,
            "signal_time": "2020-06-01T00:00:00Z",
            "entry_time": "2020-06-01T00:00:00Z",
            "exit_time": "2020-06-01T01:00:00Z",
            "year": 2020,
            "net_return_bps": 8.0,
        },
        {
            "signal_index": 20,
            "entry_index": 21,
            "exit_index": 22,
            "signal_time": "2021-06-01T00:00:00Z",
            "entry_time": "2021-06-01T00:00:00Z",
            "exit_time": "2021-06-01T01:00:00Z",
            "year": 2021,
            "net_return_bps": -4.0,
        },
        {
            "signal_index": 30,
            "entry_index": 31,
            "exit_index": 32,
            "signal_time": "2022-06-01T00:00:00Z",
            "entry_time": "2022-06-01T00:00:00Z",
            "exit_time": "2022-06-01T01:00:00Z",
            "year": 2022,
            "net_return_bps": 2.5,
        },
        {
            "signal_index": 40,
            "entry_index": 41,
            "exit_index": 42,
            "signal_time": "2023-12-31T18:00:00Z",
            "entry_time": "2023-12-31T18:00:00Z",
            "exit_time": "2024-06-01T06:00:00Z",
            "year": 2023,
            "net_return_bps": -1.0,
        },
        {
            "signal_index": 41,
            "entry_index": 42,
            "exit_index": 43,
            "signal_time": "2023-12-31T20:00:00Z",
            "entry_time": "2023-12-31T20:00:00Z",
            "exit_time": "2025-06-01T06:00:00Z",
            "year": 2023,
            "net_return_bps": 3.0,
        },
        {
            "signal_index": 50,
            "entry_index": 51,
            "exit_index": 52,
            "signal_time": "2024-06-01T00:00:00Z",
            "entry_time": "2024-06-01T00:00:00Z",
            "exit_time": "2024-06-01T02:00:00Z",
            "year": 2024,
            "net_return_bps": 5.0,
        },
        {
            "signal_index": 60,
            "entry_index": 61,
            "exit_index": 62,
            "signal_time": "2024-12-31T18:00:00Z",
            "entry_time": "2024-12-31T18:00:00Z",
            "exit_time": "2025-01-01T06:00:00Z",
            "year": 2024,
            "net_return_bps": -3.0,
        },
        {
            "signal_index": 70,
            "entry_index": 71,
            "exit_index": 72,
            "signal_time": "2025-06-01T00:00:00Z",
            "entry_time": "2025-06-01T00:00:00Z",
            "exit_time": "2025-06-01T01:00:00Z",
            "year": 2025,
            "net_return_bps": 12.0,
        },
        {
            "signal_index": 80,
            "entry_index": 81,
            "exit_index": 82,
            "signal_time": "2026-06-01T00:00:00Z",
            "entry_time": "2026-06-01T00:00:00Z",
            "exit_time": "2026-06-01T01:00:00Z",
            "year": 2026,
            "net_return_bps": -2.0,
        },
        {
            "signal_index": 90,
            "entry_index": 91,
            "exit_index": 92,
            "signal_time": "2027-06-01T00:00:00Z",
            "entry_time": "2027-06-01T00:00:00Z",
            "exit_time": "2027-06-01T01:00:00Z",
            "year": 2027,
            "net_return_bps": 1.0,
        },
    ]
    frame = pd.DataFrame(rows)
    time_cols = ["signal_time", "entry_time", "exit_time"]
    for column in time_cols:
        frame[column] = pd.to_datetime(frame[column], utc=True).dt.tz_convert(None)
    return frame


def _feature_columns() -> list[str]:
    return list(APPROVED_MODEL_FEATURES)


def _build_model_frame(df: pd.DataFrame, *, include_forbidden: bool = False) -> pd.DataFrame:
    frame = pd.DataFrame(index=df.index.copy())
    feature_columns = _feature_columns()
    for idx, column in enumerate(feature_columns):
        frame[column] = pd.Series([float(idx + 1 + row) for row in range(len(frame))], index=frame.index)
    if include_forbidden:
        frame["entry_price"] = [100.0 + idx for idx in range(len(frame))]
        frame["exit_price"] = [101.0 + idx for idx in range(len(frame))]
        frame["gross_return_bps"] = [2.0 + idx for idx in range(len(frame))]
        frame["OFI"] = [0.1 * idx for idx in range(len(frame))]
    return frame


def generate_primary_label(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame[PRIMARY_LABEL_NAME] = (pd.to_numeric(frame["net_return_bps"], errors="coerce") > 0).astype(int)
    return frame


def assign_chronological_split(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()

    def _assign(year: object) -> str:
        if pd.isna(year):
            return "out_of_protocol"
        value = int(year)
        if value in {2020, 2021, 2022, 2023}:
            return "train"
        if value == 2024:
            return "validation"
        if value in {2025, 2026}:
            return "holdout"
        return "out_of_protocol"

    frame["split"] = frame["year"].apply(_assign)
    return frame


def compute_purge_flags(df: pd.DataFrame, embargo_timedelta: pd.Timedelta) -> pd.DataFrame:
    frame = df.copy()
    if "split" not in frame.columns:
        frame = assign_chronological_split(frame)
    frame["purge_candidate"] = False
    frame["embargo_candidate"] = False

    validation_or_holdout = frame[frame["split"].isin(["validation", "holdout"])][["signal_time", "exit_time"]].copy()
    boundaries = SPLIT_BOUNDARIES

    for idx, row in frame.iterrows():
        signal_time = row["signal_time"]
        exit_time = row["exit_time"]
        if row["split"] == "train":
            for _, other in validation_or_holdout.iterrows():
                if _intervals_overlap(signal_time, exit_time, other["signal_time"], other["exit_time"]):
                    frame.at[idx, "purge_candidate"] = True
                    break
        for boundary in boundaries:
            if abs(signal_time - boundary) <= embargo_timedelta:
                frame.at[idx, "embargo_candidate"] = True
                break
    return frame


def _intervals_overlap(start_a: pd.Timestamp, end_a: pd.Timestamp, start_b: pd.Timestamp, end_b: pd.Timestamp) -> bool:
    return bool(start_a <= end_b and start_b <= end_a)


def validate_feature_contract(columns: list[str] | pd.Index) -> dict[str, object]:
    column_set = list(columns)
    approved_present = [column for column in APPROVED_MODEL_FEATURES if column in column_set]
    approved_missing = [column for column in APPROVED_MODEL_FEATURES if column not in column_set]
    forbidden_detected = [column for column in FORBIDDEN_MODEL_FEATURES if column in column_set]
    identity_overlap = [column for column in AUDIT_IDENTITY_COLUMNS if column in column_set and column != "year"]
    outcome_overlap = [column for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps", "holding_bars"] if column in column_set]
    l2_ofi_overlap = [column for column in ["OFI", "MLOFI", "microprice", "spread", "depth", "queue imbalance", "L2 imbalance", "spoofing", "iceberg", "whale pressure"] if column in column_set]
    return {
        "approved_features_present_count": len(approved_present),
        "approved_features_missing_count": len(approved_missing),
        "forbidden_features_detected_count": len(forbidden_detected),
        "identity_columns_excluded_from_model_features": len(identity_overlap) == 0,
        "outcome_columns_excluded_from_model_features": len(outcome_overlap) == 0,
        "l2_ofi_columns_excluded_from_model_features": len(l2_ofi_overlap) == 0,
        "approved_missing": approved_missing,
        "forbidden_detected": forbidden_detected,
        "identity_overlap": identity_overlap,
        "outcome_overlap": outcome_overlap,
        "l2_ofi_overlap": l2_ofi_overlap,
    }


def _summary_counts(frame: pd.DataFrame) -> dict[str, object]:
    label_counts = frame[PRIMARY_LABEL_NAME].value_counts().to_dict()
    split_counts = frame["split"].value_counts().to_dict()
    return {
        "synthetic_row_count": int(len(frame)),
        "years_covered": sorted(int(year) for year in frame["year"].dropna().unique()),
        "train_count_before_purge": int((frame["split"] == "train").sum()),
        "validation_count": int((frame["split"] == "validation").sum()),
        "holdout_count": int((frame["split"] == "holdout").sum()),
        "positive_label_count": int(label_counts.get(1, 0)),
        "negative_label_count": int(label_counts.get(0, 0)),
        "split_counts": {str(key): int(value) for key, value in split_counts.items()},
    }


def build_report(*, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    fixture = _synthetic_fixture()
    labelled = generate_primary_label(fixture)
    split_frame = assign_chronological_split(labelled)
    embargoed = compute_purge_flags(split_frame, DEFAULT_EMBARGO)

    model_frame = _build_model_frame(embargoed.drop(columns=[PRIMARY_LABEL_NAME], errors="ignore"), include_forbidden=False)
    contract = validate_feature_contract(model_frame.columns)
    contract_with_forbidden = validate_feature_contract(
        _build_model_frame(embargoed.drop(columns=[PRIMARY_LABEL_NAME], errors="ignore"), include_forbidden=True).columns
    )

    protocol_pass = (
        contract["approved_features_present_count"] == len(APPROVED_MODEL_FEATURES)
        and contract["approved_features_missing_count"] == 0
        and contract["identity_columns_excluded_from_model_features"]
        and contract["outcome_columns_excluded_from_model_features"]
        and contract["l2_ofi_columns_excluded_from_model_features"]
        and contract_with_forbidden["forbidden_features_detected_count"] > 0
    )

    summary = _summary_counts(embargoed)
    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Gate 3 Protocol Check")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Verify, using synthetic fixtures only, that the pre-registered Gate 3 meta-label protocol can be represented mechanically before any real-data experiment.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append("- synthetic_fixture_only: `true`")
    report.append("- real_trade_log_read: `false`")
    report.append("- real_bar_data_read: `false`")
    report.append("- raw_l2_data_read: `false`")
    report.append("- ofi_artifacts_read: `false`")
    report.append("")
    report.append("## Read-Only Guardrails")
    report.append("")
    report.append("- No real trade log was read.")
    report.append("- No real bar data was read.")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No feature-table artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No model was trained.")
    report.append("- No predictive metrics were computed.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Pre-Registered Protocol Encoded")
    report.append("")
    report.append(f"- primary_label_rule: `{PRIMARY_LABEL_RULE}`")
    report.append("- split_years: `train=2020-2023, validation=2024, holdout=2025-2026`")
    report.append("- purge_rule: `purge train rows whose holding interval overlaps validation or holdout intervals`")
    report.append(f"- embargo_rule: `mark rows within {DEFAULT_EMBARGO} of split boundaries`")
    report.append(f"- approved_feature_count: `{len(APPROVED_MODEL_FEATURES)}`")
    report.append(f"- audit_identity_count: `{len(AUDIT_IDENTITY_COLUMNS)}`")
    report.append(f"- forbidden_feature_count: `{len(FORBIDDEN_MODEL_FEATURES)}`")
    report.append("")
    report.append("## Synthetic Fixture Summary")
    report.append("")
    report.append(f"- synthetic_row_count: `{summary['synthetic_row_count']}`")
    report.append(f"- years_covered: `{summary['years_covered']}`")
    report.append(f"- train_count_before_purge: `{summary['train_count_before_purge']}`")
    report.append(f"- validation_count: `{summary['validation_count']}`")
    report.append(f"- holdout_count: `{summary['holdout_count']}`")
    report.append(f"- positive_label_count: `{summary['positive_label_count']}`")
    report.append(f"- negative_label_count: `{summary['negative_label_count']}`")
    report.append(f"- split_counts: `{summary['split_counts']}`")
    report.append("")
    report.append("## Feature Contract Check")
    report.append("")
    report.append(f"- approved_features_present_count: `{contract['approved_features_present_count']}`")
    report.append(f"- approved_features_missing_count: `{contract['approved_features_missing_count']}`")
    report.append(f"- forbidden_features_detected_count: `{contract_with_forbidden['forbidden_features_detected_count']}`")
    report.append(f"- identity_columns_excluded_from_model_features: `{_bool_str(contract['identity_columns_excluded_from_model_features'])}`")
    report.append(f"- outcome_columns_excluded_from_model_features: `{_bool_str(contract['outcome_columns_excluded_from_model_features'])}`")
    report.append(f"- l2_ofi_columns_excluded_from_model_features: `{_bool_str(contract['l2_ofi_columns_excluded_from_model_features'])}`")
    report.append("")
    report.append("## Purge / Embargo Check")
    report.append("")
    report.append(f"- purge_candidate_count: `{int(embargoed['purge_candidate'].sum())}`")
    report.append(f"- embargo_candidate_count: `{int(embargoed['embargo_candidate'].sum())}`")
    report.append("- overlap_detection_exercised: `true`")
    report.append("- split_boundary_embargo_exercised: `true`")
    report.append("")
    report.append("## What This Proves")
    report.append("")
    report.append("- The pre-registered protocol can be represented mechanically.")
    report.append("- Labels can be generated without adding outcome columns to model features.")
    report.append("- Splits can be assigned chronologically.")
    report.append("- Purge and embargo logic can detect synthetic overlap cases.")
    report.append("- Forbidden features can be detected.")
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
    report.append(f"- Gate 3 protocol checker: `{ 'pass' if protocol_pass else 'partial' }`")
    report.append("- Gate 3 real-data dry run: not started")
    report.append("- Gate 3 model training: not started")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if protocol_pass:
        report.append("Run a real-data Gate 3 label/split/purge dry run that reads the existing trade log and approved in-memory feature table construction, but still trains no model and computes no predictive metrics.")
    else:
        report.append("Fix the protocol issues first, then rerun the synthetic-only checker before any real-data Gate 3 work.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- synthetic protocol checking")
    report.append("- future real-data label/split/purge dry run")
    report.append("- feature contract verification")
    report.append("- leakage audit")
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
        "c_exhaustion_gate3_protocol_checker_created",
        "synthetic_fixture_only",
        "no_real_trade_log_read",
        "no_real_bar_data_read",
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
        "gate_3_real_data_not_started",
        "gate_3_protocol_checker_pass" if protocol_pass else "gate_3_protocol_checker_partial",
    ]
    for label in labels:
        report.append(f"- `{label}`")

    report_text = "\n".join(report) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report_text, encoding="utf-8")
    return report_text, {
        "synthetic_fixture_only": True,
        "fixture": embargoed,
        "summary": summary,
        "contract": contract,
        "contract_with_forbidden": contract_with_forbidden,
        "protocol_pass": protocol_pass,
        "purge_candidate_count": int(embargoed["purge_candidate"].sum()),
        "embargo_candidate_count": int(embargoed["embargo_candidate"].sum()),
        "approved_features_present_count": int(contract["approved_features_present_count"]),
        "forbidden_features_detected_count": int(contract_with_forbidden["forbidden_features_detected_count"]),
        "split_counts": summary["split_counts"],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(output_doc=args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
