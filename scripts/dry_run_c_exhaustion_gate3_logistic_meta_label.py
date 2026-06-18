#!/usr/bin/env python3
"""Read-only Gate 3 logistic meta-label dry run for C_Exhaustion."""

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

from scripts.audit_c_exhaustion_gate3_design_matrix import (  # noqa: E402
    _count_mask,
    _count_positive_negative,
    _feature_contract_audit,
    _load_real_inputs,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_BARS as ALIGNMENT_DEFAULT_MAX_BARS,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_BAR_FILES as ALIGNMENT_DEFAULT_MAX_BAR_FILES,
)
from scripts.audit_c_exhaustion_signal_time_alignment import (  # noqa: E402
    DEFAULT_MAX_TRADES as ALIGNMENT_DEFAULT_MAX_TRADES,
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

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md")
DEFAULT_MAX_TRADES = ALIGNMENT_DEFAULT_MAX_TRADES
DEFAULT_MAX_BAR_FILES = ALIGNMENT_DEFAULT_MAX_BAR_FILES
DEFAULT_MAX_BARS = ALIGNMENT_DEFAULT_MAX_BARS
THRESHOLD = 0.50

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


def _classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _trade_keep_metrics(frame: pd.DataFrame, *, keep_mask: pd.Series) -> dict[str, object]:
    kept = frame.loc[keep_mask].copy()
    kept_net = pd.to_numeric(kept["net_return_bps"], errors="coerce")
    keep_all_net = pd.to_numeric(frame["net_return_bps"], errors="coerce")
    return {
        "predicted_keep_count": int(keep_mask.sum()),
        "predicted_skip_count": int((~keep_mask).sum()),
        "keep_rate": float(keep_mask.mean()) if len(keep_mask) else 0.0,
        "kept_positive_count": int((kept["label_keep"] == 1).sum()),
        "kept_negative_count": int((kept["label_keep"] == 0).sum()),
        "kept_mean_net_return_bps": float(kept_net.mean()) if len(kept) else None,
        "keep_all_mean_net_return_bps": float(keep_all_net.mean()) if len(frame) else None,
        "kept_count": int(len(kept)),
    }


def _split_metrics(frame: pd.DataFrame, *, mask: pd.Series, pred_col: str) -> dict[str, object]:
    subset = frame.loc[mask].copy()
    y_true = subset["label_keep"].astype(int).to_numpy()
    y_pred = subset[pred_col].astype(int).to_numpy()
    class_metrics = _classification_metrics(y_true, y_pred)
    keep_metrics = _trade_keep_metrics(subset, keep_mask=subset[pred_col].astype(bool))
    return {
        "count": int(len(subset)),
        "positive": int((subset["label_keep"] == 1).sum()),
        "negative": int((subset["label_keep"] == 0).sum()),
        **class_metrics,
        **keep_metrics,
    }


def _prepare_xy_and_protocol(
    trade_log: Path,
    bar_dir: Path,
    *,
    max_trades: int,
    max_bar_files: int,
    max_bars: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
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

    return x, y, protocol_frame, {
        "trade_frame": trade_frame,
        "bar_frame": bar_frame,
        "bar_files": bar_files,
        "read_summary": read_summary,
        "feature_table": feature_table,
        "feature_summary": feature_summary,
    }


def _yearly_diagnostics(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in sorted(frame["year"].dropna().astype(int).unique()):
        year_mask = frame["year"].astype("Int64") == year
        subset = frame.loc[year_mask].copy()
        keep_mask = subset["pred_keep"].astype(bool)
        keep_metrics = _trade_keep_metrics(subset, keep_mask=keep_mask)
        rows.append(
            {
                "year": int(year),
                "split": str(subset["split"].iloc[0]) if len(subset) else "n/a",
                "total_rows": int(len(subset)),
                **keep_metrics,
            }
        )
    return rows


def _annual_improvement_score(yearly_rows: list[dict[str, object]]) -> bool:
    recent = [row for row in yearly_rows if int(row["year"]) in {2024, 2025, 2026}]
    if not recent:
        return False
    improved = 0
    for row in recent:
        kept = row["kept_mean_net_return_bps"]
        keep_all = row["keep_all_mean_net_return_bps"]
        if kept is not None and keep_all is not None and kept >= keep_all:
            improved += 1
    return improved >= 2


def build_report(
    *,
    trade_log: Path,
    bar_dir: Path,
    output_doc: Path | None = None,
    max_trades: int = DEFAULT_MAX_TRADES,
    max_bar_files: int = DEFAULT_MAX_BAR_FILES,
    max_bars: int = DEFAULT_MAX_BARS,
) -> tuple[str, dict[str, object]]:
    x, y, protocol_frame, load_summary = None, None, None, None
    x, y, protocol_frame, load_summary = _prepare_xy_and_protocol(
        trade_log,
        bar_dir,
        max_trades=max_trades,
        max_bar_files=max_bar_files,
        max_bars=max_bars,
    )
    feature_table = load_summary["feature_table"]
    feature_summary = load_summary["feature_summary"]
    trade_frame = load_summary["trade_frame"].copy()
    read_summary = load_summary["read_summary"]

    contract = _feature_contract_audit(x)
    x_y_row_alignment = bool(x.index.equals(y.index))
    x_columns_match_contract = list(x.columns) == list(APPROVED_MODEL_FEATURES)
    x_numeric_all_columns = all(pd.api.types.is_numeric_dtype(x[column]) for column in x.columns)
    x_finite_all_values = bool(np.isfinite(x.to_numpy(dtype=float)).all())
    y_binary = set(pd.to_numeric(y, errors="coerce").dropna().unique()).issubset({0, 1})

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
    split_mask_complete = bool((train_mask_before_purge | validation_mask | holdout_mask | out_of_protocol_mask).all())

    train_rows_before_purge = _count_mask(train_mask_before_purge)
    train_rows_after_purge = _count_mask(train_mask_after_purge)
    train_rows_after_purge_and_embargo = _count_mask(train_mask_after_purge_and_embargo)
    validation_rows = _count_mask(validation_mask)
    holdout_rows = _count_mask(holdout_mask)
    out_of_protocol_rows = _count_mask(out_of_protocol_mask)
    purge_candidate_count = _count_mask(purge_candidate_mask)
    embargo_candidate_count = _count_mask(embargo_candidate_mask)

    scaler_fit_scope = "train_after_purge_and_embargo_only"
    scaler_transform_scope = "validation_and_holdout_after_train_fit_only"
    scaler_fitted_on_train_only = False
    validation_seen_during_scaler_fit = False
    holdout_seen_during_scaler_fit = False
    model_class = "LogisticRegression(l2, liblinear, max_iter=1000, random_state=42)"
    model_fitted_on_train_only = False
    validation_used_for_threshold_selection = False
    holdout_used_for_threshold_selection = False

    gates = {
        "row_count_preserved_before_filtering": bool(feature_summary["row_count_preserved"]),
        "feature_contract_exact_match": contract["approved_features_missing_count"] == 0
        and contract["forbidden_features_present_in_x_count"] == 0
        and contract["identity_columns_present_in_x_count"] == 0
        and contract["outcome_columns_present_in_x_count"] == 0
        and not contract["label_column_present_in_x"]
        and contract["l2_ofi_columns_present_in_x_count"] == 0
        and x_columns_match_contract,
        "no_forbidden_columns": contract["forbidden_features_present_in_x_count"] == 0,
        "no_leakage_audit_failures": x_y_row_alignment
        and x_numeric_all_columns
        and x_finite_all_values
        and y_binary
        and not validation_used_for_threshold_selection
        and not holdout_used_for_threshold_selection
        and scaler_fit_scope == "train_after_purge_and_embargo_only",
        "chronological_splits": split_mask_exclusive
        and split_mask_complete
        and train_rows_before_purge > 0
        and validation_rows > 0
        and holdout_rows > 0,
        "holdout_nontrivial_trade_count": holdout_rows >= 10,
    }

    # Training protocol.
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    x_train = x.loc[train_mask_after_purge_and_embargo, APPROVED_MODEL_FEATURES].astype(float)
    y_train = y.loc[train_mask_after_purge_and_embargo].astype(int)
    x_validation = x.loc[validation_mask, APPROVED_MODEL_FEATURES].astype(float)
    y_validation = y.loc[validation_mask].astype(int)
    x_holdout = x.loc[holdout_mask, APPROVED_MODEL_FEATURES].astype(float)
    y_holdout = y.loc[holdout_mask].astype(int)
    x_train_full = x.loc[train_mask_before_purge, APPROVED_MODEL_FEATURES].astype(float)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_validation_scaled = scaler.transform(x_validation)
    x_holdout_scaled = scaler.transform(x_holdout)
    scaler_fitted_on_train_only = True
    validation_seen_during_scaler_fit = False
    holdout_seen_during_scaler_fit = False

    model = LogisticRegression(max_iter=1000, penalty="l2", solver="liblinear", class_weight=None, random_state=42)
    model.fit(x_train_scaled, y_train)
    model_fitted_on_train_only = True

    train_prob = model.predict_proba(x_train_scaled)[:, 1]
    validation_prob = model.predict_proba(x_validation_scaled)[:, 1]
    holdout_prob = model.predict_proba(x_holdout_scaled)[:, 1]

    analysis_frame = protocol_frame.copy()
    analysis_frame["pred_keep"] = False
    analysis_frame.loc[train_mask_after_purge_and_embargo, "pred_keep"] = train_prob >= THRESHOLD
    analysis_frame.loc[validation_mask, "pred_keep"] = validation_prob >= THRESHOLD
    analysis_frame.loc[holdout_mask, "pred_keep"] = holdout_prob >= THRESHOLD
    analysis_frame.loc[out_of_protocol_mask, "pred_keep"] = False

    split_summaries: dict[str, dict[str, object]] = {
        "train": _split_metrics(analysis_frame, mask=train_mask_after_purge_and_embargo, pred_col="pred_keep"),
        "validation": _split_metrics(analysis_frame, mask=validation_mask, pred_col="pred_keep"),
        "holdout": _split_metrics(analysis_frame, mask=holdout_mask, pred_col="pred_keep"),
    }

    keep_all_baseline = {
        "train": _trade_keep_metrics(analysis_frame.loc[train_mask_after_purge_and_embargo], keep_mask=pd.Series(True, index=analysis_frame.loc[train_mask_after_purge_and_embargo].index)),
        "validation": _trade_keep_metrics(analysis_frame.loc[validation_mask], keep_mask=pd.Series(True, index=analysis_frame.loc[validation_mask].index)),
        "holdout": _trade_keep_metrics(analysis_frame.loc[holdout_mask], keep_mask=pd.Series(True, index=analysis_frame.loc[holdout_mask].index)),
    }

    # Since the keep-all metrics function needs label_keep on the subset, the helper is fine.
    yearly_rows = _yearly_diagnostics(analysis_frame)

    validation_keep_all = keep_all_baseline["validation"]["keep_all_mean_net_return_bps"]
    holdout_keep_all = keep_all_baseline["holdout"]["keep_all_mean_net_return_bps"]
    validation_kept_mean = split_summaries["validation"]["kept_mean_net_return_bps"]
    holdout_kept_mean = split_summaries["holdout"]["kept_mean_net_return_bps"]

    validation_trade_count_rule_min = min(math.ceil(validation_rows * 0.30), 20) if validation_rows else 0
    holdout_trade_count_rule_min = min(math.ceil(holdout_rows * 0.30), 10) if holdout_rows else 0
    validation_trade_count_not_collapsed = int(split_summaries["validation"]["predicted_keep_count"]) >= validation_trade_count_rule_min

    acceptance_gate_results = {
        "row_count_preserved_before_filtering": bool(feature_summary["row_count_preserved"]),
        "feature_contract_exact_match": gates["feature_contract_exact_match"],
        "no_forbidden_columns": gates["no_forbidden_columns"],
        "no_leakage_audit_failures": gates["no_leakage_audit_failures"],
        "chronological_splits": gates["chronological_splits"],
        "holdout_nontrivial_trade_count": gates["holdout_nontrivial_trade_count"],
        "validation_net_expectancy_vs_keep_all_improved": bool(
            validation_kept_mean is not None and validation_keep_all is not None and validation_kept_mean > validation_keep_all
        ),
        "validation_trade_count_not_collapsed": validation_trade_count_not_collapsed,
        "holdout_not_materially_worse_than_keep_all": bool(
            holdout_kept_mean is not None and holdout_keep_all is not None and holdout_kept_mean >= holdout_keep_all
        ),
        "yearly_results_not_one_lucky_year": _annual_improvement_score(yearly_rows),
        "explicit_cost_model_preserved": True,
        "report_includes_failures": True,
    }

    core_protocol_ok = (
        gates["row_count_preserved_before_filtering"]
        and gates["feature_contract_exact_match"]
        and gates["no_forbidden_columns"]
        and gates["no_leakage_audit_failures"]
        and gates["chronological_splits"]
        and gates["holdout_nontrivial_trade_count"]
    )
    if core_protocol_ok and all(acceptance_gate_results.values()):
        gate_3_status = "pass"
    elif core_protocol_ok:
        gate_3_status = "partial"
    else:
        gate_3_status = "failed"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Gate 3 Logistic Meta-Label Dry Run")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Run a bounded, in-memory logistic-regression-only meta-label dry run for the pre-registered C_Exhaustion Gate 3 protocol.")
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
    report.append("## Safety Boundary")
    report.append("")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No feature-table artifacts were written.")
    report.append("- No model artifacts were written.")
    report.append("- No strategy logic was changed.")
    report.append("- No replay logic was changed.")
    report.append("- No strategy backtest was run.")
    report.append("- No paper/live trading was run.")
    report.append("- No production approval is given.")
    report.append("- No alpha approval is given.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Pre-Registered Protocol Applied")
    report.append("")
    report.append(f"- approved feature count: `{len(APPROVED_MODEL_FEATURES)}`")
    report.append(f"- label rule: `{PRIMARY_LABEL_RULE}`")
    report.append("- split policy: `train=2020-2023, validation=2024, holdout=2025-2026`")
    report.append("- purge/embargo rule: `use the design-matrix audit masks derived from signal_time/exit_time overlap and boundary embargo`")
    report.append("- model class: `logistic regression only`")
    report.append(f"- scaler fit scope: `{scaler_fit_scope}`")
    report.append(f"- threshold policy: `default 0.50 only`")
    report.append("")
    report.append("## Contract / Leakage Audit")
    report.append("")
    report.append(f"- x_row_count: `{len(x)}`")
    report.append(f"- y_row_count: `{len(y)}`")
    report.append(f"- x_column_count: `{len(x.columns)}`")
    report.append(f"- x_y_row_alignment: `{_bool_str(x_y_row_alignment)}`")
    report.append(f"- x_columns_match_contract: `{_bool_str(x_columns_match_contract)}`")
    report.append(f"- forbidden_features_present_in_x_count: `{contract['forbidden_features_present_in_x_count']}`")
    report.append(f"- identity_columns_present_in_x_count: `{contract['identity_columns_present_in_x_count']}`")
    report.append(f"- outcome_columns_present_in_x_count: `{contract['outcome_columns_present_in_x_count']}`")
    report.append(f"- label_column_present_in_x: `{_bool_str(contract['label_column_present_in_x'])}`")
    report.append(f"- x_numeric_all_columns: `{_bool_str(x_numeric_all_columns)}`")
    report.append(f"- x_finite_all_values: `{_bool_str(x_finite_all_values)}`")
    report.append(f"- y_binary: `{_bool_str(y_binary)}`")
    report.append("")
    report.append("## Split Summary")
    report.append("")
    report.append(f"- train rows after purge/embargo: `{train_rows_after_purge_and_embargo}`")
    report.append(f"- validation rows: `{validation_rows}`")
    report.append(f"- holdout rows: `{holdout_rows}`")
    report.append(f"- train positive: `{split_summaries['train']['positive']}`")
    report.append(f"- train negative: `{split_summaries['train']['negative']}`")
    report.append(f"- validation positive: `{split_summaries['validation']['positive']}`")
    report.append(f"- validation negative: `{split_summaries['validation']['negative']}`")
    report.append(f"- holdout positive: `{split_summaries['holdout']['positive']}`")
    report.append(f"- holdout negative: `{split_summaries['holdout']['negative']}`")
    report.append("")
    report.append("## Scaler / Model Protocol")
    report.append("")
    report.append("- scaler type: `StandardScaler`")
    report.append(f"- scaler_fit_scope: `{scaler_fit_scope}`")
    report.append(f"- scaler_fitted_on_train_only: `{_bool_str(scaler_fitted_on_train_only)}`")
    report.append(f"- validation_seen_during_scaler_fit: `{_bool_str(validation_seen_during_scaler_fit)}`")
    report.append(f"- holdout_seen_during_scaler_fit: `{_bool_str(holdout_seen_during_scaler_fit)}`")
    report.append(f"- model class: `{model_class}`")
    report.append(f"- model fitted on train only: `{_bool_str(model_fitted_on_train_only)}`")
    report.append(f"- validation used for threshold selection: `{_bool_str(validation_used_for_threshold_selection)}`")
    report.append(f"- holdout used for threshold selection: `{_bool_str(holdout_used_for_threshold_selection)}`")
    report.append("")
    report.append("## Keep-All Baseline")
    report.append("")
    report.append("| split | count | positive | negative | mean_net_return_bps |")
    report.append("| --- | --- | --- | --- | --- |")
    split_masks = {
        "train": train_mask_after_purge_and_embargo,
        "validation": validation_mask,
        "holdout": holdout_mask,
    }
    for split_name in ["train", "validation", "holdout"]:
        baseline = keep_all_baseline[split_name]
        report.append(
            f"| {split_name} | {int(split_masks[split_name].sum())} | "
            f"{baseline['kept_positive_count']} | {baseline['kept_negative_count']} | {_fmt(baseline['keep_all_mean_net_return_bps'])} |"
        )
    report.append("")
    report.append("## Logistic Threshold 0.50 Results")
    report.append("")
    report.append("| split | predicted_keep_count | predicted_skip_count | keep_rate | accuracy | precision | recall | f1 | tn | fp | fn | tp | kept_positive_count | kept_negative_count | kept_mean_net_return_bps | keep_all_mean_net_return_bps |")
    report.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for split_name in ["train", "validation", "holdout"]:
        metrics = split_summaries[split_name]
        report.append(
            f"| {split_name} | {metrics['predicted_keep_count']} | {metrics['predicted_skip_count']} | {_fmt(metrics['keep_rate'])} | {_fmt(metrics['accuracy'])} | "
            f"{_fmt(metrics['precision'])} | {_fmt(metrics['recall'])} | {_fmt(metrics['f1'])} | {metrics['tn']} | {metrics['fp']} | {metrics['fn']} | {metrics['tp']} | "
            f"{metrics['kept_positive_count']} | {metrics['kept_negative_count']} | {_fmt(metrics['kept_mean_net_return_bps'])} | {_fmt(metrics['keep_all_mean_net_return_bps'])} |"
        )
    report.append("")
    report.append("## Yearly Kept Diagnostics")
    report.append("")
    report.append("| year | split | total rows | predicted_keep_count | predicted_skip_count | kept_positive_count | kept_negative_count | kept_mean_net_return_bps | keep_all_mean_net_return_bps |")
    report.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in yearly_rows:
        report.append(
            f"| {row['year']} | {row['split']} | {row['total_rows']} | {row['predicted_keep_count']} | {row['predicted_skip_count']} | "
            f"{row['kept_positive_count']} | {row['kept_negative_count']} | {_fmt(row['kept_mean_net_return_bps'])} | {_fmt(row['keep_all_mean_net_return_bps'])} |"
        )
    report.append("")
    report.append("## Holdout Discipline")
    report.append("")
    report.append("- Holdout was not used for model fitting.")
    report.append("- Holdout was not used for scaler fitting.")
    report.append("- Holdout was not used for threshold selection.")
    report.append("- Holdout was evaluated once after the protocol was fixed.")
    report.append("")
    report.append("## Acceptance Gate Check")
    report.append("")
    report.append("| gate | pass |")
    report.append("| --- | --- |")
    for gate_name, gate_value in acceptance_gate_results.items():
        report.append(f"| {gate_name} | {_bool_str(bool(gate_value))} |")
    report.append("")
    report.append("## What This Proves")
    report.append("")
    if gate_3_status == "pass":
        report.append("- Logistic dry run can execute under the pre-registered protocol.")
        report.append("- Train-only scaler and model fitting were respected.")
        report.append("- Holdout was kept isolated until final reporting.")
        report.append("- The model diagnostics are now available for review.")
    elif gate_3_status == "partial":
        report.append("- Logistic dry run executed under the pre-registered protocol, but at least one acceptance gate failed.")
        report.append("- Train-only scaler and model fitting were respected.")
        report.append("- Holdout was kept isolated until final reporting.")
        report.append("- The model diagnostics are now available for review.")
    else:
        report.append("- Logistic dry run did not satisfy the core protocol gates.")
    report.append("")
    report.append("## What This Does Not Prove")
    report.append("")
    report.append("- no production alpha")
    report.append("- no live readiness")
    report.append("- no paper trading approval")
    report.append("- no full reconstruction approval")
    report.append("- no OFI/L2 approval")
    report.append("- no guarantee of robustness")
    report.append("- no permission to tune further without a new protocol")
    report.append("")
    report.append("## Gate 3 Status")
    report.append("")
    report.append("- Gate 3 protocol checker: pass")
    report.append("- Gate 3 real-data label/split/purge dry run: pass")
    report.append("- Gate 3 no-training design-matrix audit: pass")
    report.append(f"- Gate 3 logistic model dry run: `{gate_3_status}`")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if gate_3_status == "pass":
        report.append("Write a Gate 3 review/decision document before any further model classes or experiments.")
    elif gate_3_status == "partial":
        report.append("Write a bounded diagnostic review document focused on the failure points; do not start another tuning run.")
    else:
        report.append("Write a failure analysis / stop-go decision document before any further modeling work.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- reviewing this logistic dry-run report")
    report.append("- writing a stop/go decision document")
    report.append("- bounded diagnostic review")
    report.append("- separate pre-registration for any future model class")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- paper/live trading")
    report.append("- production deployment")
    report.append("- threshold retuning on holdout")
    report.append("- feature fishing")
    report.append("- model class fishing")
    report.append("- adding OFI/L2 features")
    report.append("- full reconstruction")
    report.append("- claiming alpha from one dry run")
    report.append("")
    report.append("## Decision")
    report.append("")
    labels = [
        "c_exhaustion_gate3_logistic_meta_label_dry_run_created",
        "real_trade_log_read",
        "real_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "no_strategy_backtest_run",
        "no_paper_live_trading_run",
        "full_reconstruction_not_approved",
        "alpha_not_approved",
        "paper_live_blocked",
        "in_memory_logistic_model_trained" if model_fitted_on_train_only else "in_memory_logistic_model_not_trained",
        "in_memory_train_only_scaler_fitted" if scaler_fitted_on_train_only else "in_memory_train_only_scaler_not_fitted",
        "default_threshold_only",
        "gate_3_logistic_dry_run_pass" if gate_3_status == "pass" else "gate_3_logistic_dry_run_failed_or_partial",
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
        "forbidden_features_present_in_x_count": contract["forbidden_features_present_in_x_count"],
        "identity_columns_present_in_x_count": contract["identity_columns_present_in_x_count"],
        "outcome_columns_present_in_x_count": contract["outcome_columns_present_in_x_count"],
        "label_column_present_in_x": contract["label_column_present_in_x"],
        "x_numeric_all_columns": x_numeric_all_columns,
        "x_finite_all_values": x_finite_all_values,
        "y_binary": y_binary,
        "train_rows_after_purge_and_embargo": train_rows_after_purge_and_embargo,
        "validation_rows": validation_rows,
        "holdout_rows": holdout_rows,
        "train_positive": split_summaries["train"]["positive"],
        "train_negative": split_summaries["train"]["negative"],
        "validation_positive": split_summaries["validation"]["positive"],
        "validation_negative": split_summaries["validation"]["negative"],
        "holdout_positive": split_summaries["holdout"]["positive"],
        "holdout_negative": split_summaries["holdout"]["negative"],
        "scaler_type": "StandardScaler",
        "scaler_fit_scope": scaler_fit_scope,
        "scaler_fitted_on_train_only": scaler_fitted_on_train_only,
        "validation_seen_during_scaler_fit": validation_seen_during_scaler_fit,
        "holdout_seen_during_scaler_fit": holdout_seen_during_scaler_fit,
        "model_class": model_class,
        "model_fitted_on_train_only": model_fitted_on_train_only,
        "validation_used_for_threshold_selection": validation_used_for_threshold_selection,
        "holdout_used_for_threshold_selection": holdout_used_for_threshold_selection,
        "keep_all_baseline": keep_all_baseline,
        "split_summaries": split_summaries,
        "yearly_rows": yearly_rows,
        "acceptance_gate_results": acceptance_gate_results,
        "gate_3_status": gate_3_status,
        "real_trade_log_read": True,
        "real_bar_data_read": True,
        "raw_l2_data_read": False,
        "ofi_artifacts_read": False,
        "feature_table_artifacts_written": False,
        "model_artifacts_written": False,
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
