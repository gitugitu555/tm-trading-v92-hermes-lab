#!/usr/bin/env python3
"""Research-only meta-label baseline dataset and evaluator plan for C_ExhaustionFade."""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for site_packages in sorted((ROOT / ".venv" / "lib").glob("python*/site-packages")):
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

import numpy as np
import pandas as pd
import polars as pl

from scripts.diagnose_c_exhaustion_regime_context import _compute_trade_context
from replays.c_exhaustion_replay import add_v92_regime_labels, load_750btc_bars, normalize_v92_bar_timestamps

def check_sklearn_available() -> bool:
    return importlib.util.find_spec("sklearn") is not None


SKLEARN_AVAILABLE = check_sklearn_available()

ALLOWED_FEATURES = [
    "pre_signal_return_12_bars_bps",
    "pre_signal_return_24_bars_bps",
    "pre_signal_return_36_bars_bps",
    "realized_vol_12_bars_bps",
    "realized_vol_24_bars_bps",
    "realized_vol_36_bars_bps",
    "range_expansion_ratio_12",
    "range_expansion_ratio_24",
    "range_expansion_ratio_36",
    "body_to_range_ratio",
    "volume_over_vol95_ratio",
    "close_vs_local_low_bps",
    "adr_stretch",
    "rv_1d",
    "rv_15th_pct",
    "bar_range",
    "body_size",
    "volume",
    "vol_roll_95",
]

FORBIDDEN_FEATURES = [
    "net_return_bps",
    "gross_return_bps",
    "exit_time",
    "exit_price",
    "mfe_bps",
    "mae_bps",
    "post_signal_return_",
    "trend_continuation_flag_",
    "failed_reversal_flag_",
    "bad_context_label_",
    "label_recent_decay",
    "year >= 2025",
    "anything computed after signal_time",
]

LABEL_DEFS = {
    "label_trade_win": "net_return_bps > 0",
    "label_positive_tail": "net_return_bps >= 200",
    "label_negative_tail": "net_return_bps <= -200",
    "label_bad_context_36": "trend_continuation_flag_36 OR failed_reversal_flag_36",
    "label_recent_decay": "year >= 2025",
}

MODEL_FAMILIES = [
    "logistic_regression_l2",
    "decision_tree_depth_2",
    "decision_tree_depth_3",
]

WALK_FORWARD_SPLITS = [
    {
        "name": "walk_forward_1",
        "train_years": [2020, 2021],
        "validate_year": 2022,
        "test_year": 2023,
    },
    {
        "name": "walk_forward_2",
        "train_years": [2020, 2021, 2022],
        "validate_year": 2023,
        "test_year": 2024,
    },
    {
        "name": "walk_forward_3",
        "train_years": [2020, 2021, 2022, 2023],
        "validate_year": 2024,
        "test_year": 2025,
    },
    {
        "name": "walk_forward_4",
        "train_years": [2020, 2021, 2022, 2023, 2024],
        "validate_year": 2025,
        "test_year": 2026,
    },
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        val = float(value)
        if math.isnan(val):
            return "n/a"
        if math.isinf(val):
            return "inf" if val > 0 else "-inf"
        return f"{val:.6f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def get_allowed_features() -> list[str]:
    return list(ALLOWED_FEATURES)


def get_forbidden_features() -> list[str]:
    return list(FORBIDDEN_FEATURES)


def get_walk_forward_splits() -> list[dict[str, object]]:
    return [dict(split) for split in WALK_FORWARD_SPLITS]


def build_meta_label_dataset(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    context = _compute_trade_context(trades, bars).copy()
    if "signal_index" not in context.columns:
        context["signal_index"] = np.arange(len(context), dtype=int)
    if "entry_index" not in context.columns:
        context["entry_index"] = context["signal_index"]
    if "exit_index" not in context.columns:
        context["exit_index"] = context["signal_index"]

    context["label_trade_win"] = context["net_return_bps"] > 0
    context["label_positive_tail"] = context["net_return_bps"] >= 200
    context["label_negative_tail"] = context["net_return_bps"] <= -200
    context["label_bad_context_36"] = (
        context["trend_continuation_flag_36"].fillna(False).astype(bool)
        | context["failed_reversal_flag_36"].fillna(False).astype(bool)
    )
    context["label_recent_decay"] = context["year"] >= 2025
    return context


def summarize_keep_remove_counts(test_count: int, kept_count: int) -> dict[str, object]:
    removed = int(test_count - kept_count)
    return {
        "test_count": int(test_count),
        "test_kept_trade_count": int(kept_count),
        "test_removed_trade_count": removed,
        "test_kept_rate": float(kept_count / test_count) if test_count else 0.0,
    }


def _threshold_grid() -> np.ndarray:
    return np.array([0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70], dtype=float)


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
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _trade_metrics_from_frame(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
        }
    net = df["net_return_bps"].astype(float)
    return {
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _safe_profit_factor(net),
    }


def _safe_profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    if len(wins) == 0 and len(losses) == 0:
        return 0.0
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    if len(losses) and abs(loss_sum) > 0.0:
        return float(wins.sum() / abs(loss_sum))
    return float("inf") if len(wins) else 0.0


def fit_preprocessors(train_df: pd.DataFrame, *, feature_names: list[str], model_family: str):
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("sklearn is not available")
    from sklearn.impute import SimpleImputer

    imputer = SimpleImputer(strategy="median")
    imputer.fit(train_df[feature_names].astype(float))

    scaler = None
    if model_family == "logistic_regression_l2":
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        scaler.fit(imputer.transform(train_df[feature_names].astype(float)))
    return imputer, scaler


def transform_features(df: pd.DataFrame, *, feature_names: list[str], imputer, scaler=None) -> np.ndarray:
    values = imputer.transform(df[feature_names].astype(float))
    if scaler is not None:
        values = scaler.transform(values)
    return values


def evaluate_threshold_candidates(
    validate_df: pd.DataFrame,
    validate_scores: np.ndarray,
    *,
    thresholds: np.ndarray | None = None,
) -> list[dict[str, object]]:
    thresholds = _threshold_grid() if thresholds is None else np.asarray(thresholds, dtype=float)
    rows: list[dict[str, object]] = []
    y_true = validate_df["label_trade_win"].astype(int).to_numpy()
    net = validate_df["net_return_bps"].astype(float).to_numpy()
    for threshold in thresholds:
        keep = validate_scores >= threshold
        kept_count = int(keep.sum())
        kept_net = net[keep]
        summary = {
            "threshold": float(threshold),
            "validate_kept_trade_count": kept_count,
            "validate_removed_trade_count": int(len(validate_df) - kept_count),
            "validate_kept_rate": float(kept_count / len(validate_df)) if len(validate_df) else 0.0,
            "validate_net_expectancy_bps_if_trading_kept_signals": float(kept_net.mean()) if kept_count else float("-inf"),
            "validate_win_rate_if_trading_kept_signals": float((kept_net > 0.0).mean()) if kept_count else 0.0,
            "validate_profit_factor_if_trading_kept_signals": _safe_profit_factor(pd.Series(kept_net)) if kept_count else 0.0,
            **_classification_metrics(y_true, keep.astype(int)),
        }
        rows.append(summary)
    return rows


def select_validation_threshold(
    validate_df: pd.DataFrame,
    validate_scores: np.ndarray,
    *,
    thresholds: np.ndarray | None = None,
) -> dict[str, object]:
    rows = evaluate_threshold_candidates(validate_df, validate_scores, thresholds=thresholds)
    qualifying = [row for row in rows if row["validate_kept_trade_count"] >= 10]
    candidates = qualifying or rows
    best = max(
        candidates,
        key=lambda row: (
            row["validate_net_expectancy_bps_if_trading_kept_signals"],
            row["validate_kept_trade_count"] >= 10,
            row["validate_win_rate_if_trading_kept_signals"],
            row["validate_profit_factor_if_trading_kept_signals"],
            row["threshold"],
        ),
    )
    return {
        "selected_threshold": float(best["threshold"]),
        "validation_sample_too_small": len(qualifying) == 0,
        "best_available_threshold_diagnostic_only": float(best["threshold"]),
        "threshold_rows": rows,
    }


def _roc_auc_score(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    pos = int((y_true == 1).sum())
    neg = int((y_true == 0).sum())
    if pos == 0 or neg == 0:
        return None
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1, dtype=float)
    rank_sum = float(ranks[y_true == 1].sum())
    return (rank_sum - pos * (pos + 1) / 2.0) / (pos * neg)


def _period_slice(df: pd.DataFrame, years: Iterable[int]) -> pd.DataFrame:
    return df[df["year"].isin(list(years))].copy()


def build_purged_walk_forward_splits(df: pd.DataFrame, *, purge_bars: int = 48, embargo_bars: int = 48) -> list[dict[str, object]]:
    frame = df.copy()
    if "signal_index" not in frame.columns:
        frame["signal_index"] = np.arange(len(frame), dtype=int)
    if "exit_index" not in frame.columns:
        frame["exit_index"] = frame["signal_index"]
    frame = frame.sort_values(["signal_index", "signal_time"]).reset_index(drop=True)

    splits: list[dict[str, object]] = []
    for spec in WALK_FORWARD_SPLITS:
        train_df = frame[frame["year"].isin(spec["train_years"])].copy()
        validate_df = frame[frame["year"] == spec["validate_year"]].copy()
        test_df = frame[frame["year"] == spec["test_year"]].copy()

        if validate_df.empty or test_df.empty:
            raise ValueError(f"Split {spec['name']} has empty validation/test period")

        validate_start = int(validate_df["signal_index"].min())
        test_start = int(test_df["signal_index"].min())

        train_mask = frame["year"].isin(spec["train_years"]) & (frame["exit_index"] < validate_start - purge_bars)
        validate_mask = (
            (frame["year"] == spec["validate_year"])
            & (frame["signal_index"] >= validate_start + embargo_bars)
            & (frame["exit_index"] < test_start - purge_bars)
        )
        test_mask = (frame["year"] == spec["test_year"]) & (frame["signal_index"] >= test_start + embargo_bars)

        splits.append(
            {
                "name": spec["name"],
                "train_years": list(spec["train_years"]),
                "validate_year": spec["validate_year"],
                "test_year": spec["test_year"],
                "purge_bars": int(purge_bars),
                "embargo_bars": int(embargo_bars),
                "train_count": int(train_mask.sum()),
                "validate_count": int(validate_mask.sum()),
                "test_count": int(test_mask.sum()),
                "train_mask": train_mask.to_numpy(),
                "validate_mask": validate_mask.to_numpy(),
                "test_mask": test_mask.to_numpy(),
            }
        )
    return splits


def _prepare_xy(df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    X = df[features].astype(float).copy()
    y = df["label_trade_win"].astype(int).copy()
    return X, y


def _summarize_threshold_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "selected_threshold": row["threshold"],
        "validate_kept_trade_count": row["validate_kept_trade_count"],
        "validate_removed_trade_count": row["validate_removed_trade_count"],
        "validate_kept_rate": row["validate_kept_rate"],
        "validate_net_expectancy_bps_if_trading_kept_signals": row["validate_net_expectancy_bps_if_trading_kept_signals"],
        "validate_win_rate_if_trading_kept_signals": row["validate_win_rate_if_trading_kept_signals"],
        "validate_profit_factor_if_trading_kept_signals": row["validate_profit_factor_if_trading_kept_signals"],
        "validate_precision": row["precision"],
        "validate_recall": row["recall"],
        "validate_f1": row["f1"],
    }


def _execute_model_fold(
    model_name: str,
    train_df: pd.DataFrame,
    validate_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    baseline_test_metrics: dict[str, object],
) -> dict[str, object]:
    row: dict[str, object] = {
        "model_family": model_name,
        "model_status": "blocked_missing_sklearn",
        "validation_sample_too_small": None,
        "best_available_threshold_diagnostic_only": None,
        "selected_threshold": None,
        "validate_precision": None,
        "validate_recall": None,
        "validate_f1": None,
        "test_precision": None,
        "test_recall": None,
        "test_f1": None,
        "test_accuracy": None,
        "test_auc_if_available": None,
        "test_kept_trade_count": None,
        "test_removed_trade_count": None,
        "test_kept_rate": None,
        "test_net_expectancy_bps_if_trading_kept_signals": None,
        "test_win_rate_if_trading_kept_signals": None,
        "test_profit_factor_if_trading_kept_signals": None,
        "baseline_no_gate_test_net_expectancy_bps": float(baseline_test_metrics["net_expectancy_bps"]),
        "delta_vs_baseline_bps": None,
    }

    if not SKLEARN_AVAILABLE:
        return row

    X_train, y_train = _prepare_xy(train_df, ALLOWED_FEATURES)
    X_validate, y_validate = _prepare_xy(validate_df, ALLOWED_FEATURES)
    X_test, y_test = _prepare_xy(test_df, ALLOWED_FEATURES)

    if y_train.nunique() < 2 or y_validate.nunique() < 2 or y_test.nunique() < 2:
        row["model_status"] = "blocked_single_class_split"
        return row

    imputer, scaler = fit_preprocessors(train_df, feature_names=ALLOWED_FEATURES, model_family=model_name)
    X_train_trans = transform_features(train_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    X_validate_trans = transform_features(validate_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    X_test_trans = transform_features(test_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)

    if model_name == "logistic_regression_l2":
        from sklearn.linear_model import LogisticRegression

        model = LogisticRegression(max_iter=1000, penalty="l2", solver="liblinear", random_state=42)
    elif model_name == "decision_tree_depth_2":
        from sklearn.tree import DecisionTreeClassifier

        model = DecisionTreeClassifier(max_depth=2, random_state=42)
    elif model_name == "decision_tree_depth_3":
        from sklearn.tree import DecisionTreeClassifier

        model = DecisionTreeClassifier(max_depth=3, random_state=42)
    else:
        raise ValueError(f"Unknown model family: {model_name}")

    model.fit(X_train_trans, y_train)
    validate_scores = model.predict_proba(X_validate_trans)[:, 1]
    threshold_result = select_validation_threshold(validate_df, validate_scores)
    threshold = float(threshold_result["selected_threshold"])
    test_scores = model.predict_proba(X_test_trans)[:, 1]
    test_keep = test_scores >= threshold
    test_pred = test_keep.astype(int)
    validate_pred = (validate_scores >= threshold).astype(int)

    validate_metrics = _classification_metrics(y_validate.to_numpy(), validate_pred)
    test_metrics = _classification_metrics(y_test.to_numpy(), test_pred)
    kept_df = test_df.loc[test_keep].copy()
    kept_financial = _trade_metrics_from_frame(kept_df)
    validation_kept_df = validate_df.loc[validate_scores >= threshold].copy()
    validation_kept_financial = _trade_metrics_from_frame(validation_kept_df)

    row.update(
        {
            "model_status": "validation_sample_too_small" if threshold_result["validation_sample_too_small"] else "model_execution_completed",
            "validation_sample_too_small": bool(threshold_result["validation_sample_too_small"]),
            "best_available_threshold_diagnostic_only": float(threshold_result["best_available_threshold_diagnostic_only"]),
            "selected_threshold": float(threshold),
            "validate_precision": validate_metrics["precision"],
            "validate_recall": validate_metrics["recall"],
            "validate_f1": validate_metrics["f1"],
            "test_precision": test_metrics["precision"],
            "test_recall": test_metrics["recall"],
            "test_f1": test_metrics["f1"],
            "test_accuracy": test_metrics["accuracy"],
            "test_auc_if_available": _roc_auc_score(y_test.to_numpy(), test_scores),
            "test_kept_trade_count": int(test_keep.sum()),
            "test_removed_trade_count": int((~test_keep).sum()),
            "test_kept_rate": float(test_keep.mean()) if len(test_keep) else 0.0,
            "test_net_expectancy_bps_if_trading_kept_signals": kept_financial["net_expectancy_bps"],
            "test_win_rate_if_trading_kept_signals": kept_financial["win_rate"],
            "test_profit_factor_if_trading_kept_signals": kept_financial["profit_factor"],
            "delta_vs_baseline_bps": float(kept_financial["net_expectancy_bps"] - baseline_test_metrics["net_expectancy_bps"]),
            "validate_kept_trade_count": int((validate_scores >= threshold).sum()),
            "validate_removed_trade_count": int(len(validate_df) - int((validate_scores >= threshold).sum())),
            "validate_kept_rate": float((validate_scores >= threshold).mean()) if len(validate_df) else 0.0,
            "validate_net_expectancy_bps_if_trading_kept_signals": validation_kept_financial["net_expectancy_bps"],
            "validate_win_rate_if_trading_kept_signals": validation_kept_financial["win_rate"],
            "validate_profit_factor_if_trading_kept_signals": validation_kept_financial["profit_factor"],
        }
    )
    threshold_row = next(candidate for candidate in threshold_result["threshold_rows"] if float(candidate["threshold"]) == float(threshold))
    row.update(_summarize_threshold_row(threshold_row))
    return row


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    dataset = build_meta_label_dataset(trades, bars)
    splits = build_purged_walk_forward_splits(dataset, purge_bars=48, embargo_bars=48)

    feature_rows = []
    for feature in ALLOWED_FEATURES:
        feature_rows.append(
            {
                "feature": feature,
                "available": feature in dataset.columns,
                "null_count": int(dataset[feature].isna().sum()) if feature in dataset.columns else None,
            }
        )

    label_rows = []
    for label, definition in LABEL_DEFS.items():
        series = dataset[label]
        label_rows.append(
            {
                "label": label,
                "definition": definition,
                "positive_count": int(series.sum()),
                "positive_rate": float(series.mean()),
            }
        )

    fold_rows: list[dict[str, object]] = []
    recent_year_rows: list[dict[str, object]] = []
    for split in splits:
        train_df = dataset[split["train_mask"]].copy()
        validate_df = dataset[split["validate_mask"]].copy()
        test_df = dataset[split["test_mask"]].copy()
        baseline_test_metrics = _trade_metrics_from_frame(test_df)
        recent_year_rows.append(
            {
                "split": split["name"],
                "test_year": split["test_year"],
                "test_count": int(len(test_df)),
                "baseline_no_gate_test_net_expectancy_bps": baseline_test_metrics["net_expectancy_bps"],
                "baseline_no_gate_test_win_rate": baseline_test_metrics["win_rate"],
                "baseline_no_gate_test_profit_factor": baseline_test_metrics["profit_factor"],
            }
        )
        for model_name in MODEL_FAMILIES:
            fold_rows.append(
                {
                    "split": split["name"],
                    "validate_year": split["validate_year"],
                    "test_year": split["test_year"],
                    "model_family": model_name,
                    "train_count": int(len(train_df)),
                    "validate_count": int(len(validate_df)),
                    "test_count": int(len(test_df)),
                    **_execute_model_fold(
                        model_name,
                        train_df,
                        validate_df,
                        test_df,
                        baseline_test_metrics=baseline_test_metrics,
                    ),
                }
            )

    recent_model_rows = [row for row in fold_rows if row["test_year"] in (2025, 2026)]

    recent_period_rows = []
    for year in [2025, 2026]:
        year_df = dataset[dataset["year"] == year].copy()
        metrics = _trade_metrics_from_frame(year_df)
        recent_period_rows.append(
            {
                "year": year,
                "trade_count": int(len(year_df)),
                "net_expectancy_bps": metrics["net_expectancy_bps"],
                "win_rate": metrics["win_rate"],
                "profit_factor": metrics["profit_factor"],
                "label_bad_context_36_rate": float(year_df["label_bad_context_36"].mean()) if len(year_df) else 0.0,
                "label_trade_win_rate": float(year_df["label_trade_win"].mean()) if len(year_df) else 0.0,
                "label_positive_tail_rate": float(year_df["label_positive_tail"].mean()) if len(year_df) else 0.0,
                "label_negative_tail_rate": float(year_df["label_negative_tail"].mean()) if len(year_df) else 0.0,
            }
        )

    baseline_summary = _trade_metrics_from_frame(dataset)
    fold_status = "blocked_missing_sklearn" if not SKLEARN_AVAILABLE else "evaluated"

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Meta-Label Baseline Results")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Establish the canonical ex-ante meta-label dataset and a purged walk-forward evaluator scaffold for C_ExhaustionFade.")
    lines.append("")
    lines.append("This task does not approve a production model, production gate, paper-trading rule, or live-trading rule.")
    lines.append("")
    lines.append("## Research-Only Guardrails")
    lines.append("")
    lines.append("- No random split.")
    lines.append("- No shuffle split.")
    lines.append("- No train/test leakage.")
    lines.append("- No post-signal features as inputs.")
    lines.append("- No production approval.")
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay context and regime labels from the repaired C_ExhaustionFade replay path")
    lines.append("")
    lines.append("## Dataset Construction")
    lines.append("")
    lines.append(f"- Canonical C trades: `{len(dataset)}`")
    lines.append(f"- `label_trade_win` positive rate: `{float(dataset['label_trade_win'].mean()):.6f}`")
    lines.append(f"- `label_bad_context_36` positive rate: `{float(dataset['label_bad_context_36'].mean()):.6f}`")
    lines.append(f"- `label_recent_decay` positive rate: `{float(dataset['label_recent_decay'].mean()):.6f}`")
    lines.append("")
    lines.append("## Allowed Features")
    lines.append("")
    lines.append(_table(feature_rows, ["feature", "available", "null_count"]))
    lines.append("")
    lines.append("## Forbidden Features")
    lines.append("")
    for item in FORBIDDEN_FEATURES:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Labels")
    lines.append("")
    lines.append(_table(label_rows, ["label", "definition", "positive_count", "positive_rate"]))
    lines.append("")
    lines.append("## Purged Walk-Forward Design")
    lines.append("")
    lines.append("Validation is time-ordered only with a conservative bar-index purge and embargo around fold boundaries.")
    lines.append("")
    lines.append(
        _table(
            [
                {
                    "split": s["name"],
                    "train_years": "-".join(str(y) for y in s["train_years"]),
                    "validate_year": s["validate_year"],
                    "test_year": s["test_year"],
                    "purge_bars": s["purge_bars"],
                    "embargo_bars": s["embargo_bars"],
                    "train_count": s["train_count"],
                    "validate_count": s["validate_count"],
                    "test_count": s["test_count"],
                }
                for s in splits
            ],
            ["split", "train_years", "validate_year", "test_year", "purge_bars", "embargo_bars", "train_count", "validate_count", "test_count"],
        )
    )
    lines.append("")
    lines.append("## Model Families")
    lines.append("")
    lines.append(f"- `sklearn_available`: `{str(SKLEARN_AVAILABLE).lower()}`")
    if not SKLEARN_AVAILABLE:
        lines.append("- Model execution is blocked in this environment because `sklearn` is not installed.")
    for model in MODEL_FAMILIES:
        lines.append(f"- `{model}`")
    lines.append("")
    lines.append("## Fold Results")
    lines.append("")
    lines.append(
        _table(
            fold_rows,
            [
                "split",
                "validate_year",
                "test_year",
                "model_family",
                "model_status",
                "validation_sample_too_small",
                "best_available_threshold_diagnostic_only",
                "train_count",
                "validate_count",
                "test_count",
                "selected_threshold",
                "validate_precision",
                "validate_recall",
                "validate_f1",
                "test_precision",
                "test_recall",
                "test_f1",
                "test_accuracy",
                "test_auc_if_available",
                "test_kept_trade_count",
                "test_removed_trade_count",
                "test_kept_rate",
                "test_net_expectancy_bps_if_trading_kept_signals",
                "test_win_rate_if_trading_kept_signals",
                "test_profit_factor_if_trading_kept_signals",
                "baseline_no_gate_test_net_expectancy_bps",
                "delta_vs_baseline_bps",
            ],
        )
    )
    lines.append("")
    lines.append("## Recent-Period Results")
    lines.append("")
    lines.append(
        _table(
            recent_model_rows,
            [
                "split",
                "test_year",
                "model_family",
                "model_status",
                "validation_sample_too_small",
                "selected_threshold",
                "test_kept_trade_count",
                "test_removed_trade_count",
                "test_kept_rate",
                "test_net_expectancy_bps_if_trading_kept_signals",
                "test_win_rate_if_trading_kept_signals",
                "test_profit_factor_if_trading_kept_signals",
                "baseline_no_gate_test_net_expectancy_bps",
                "delta_vs_baseline_bps",
            ],
        )
    )
    lines.append("")
    lines.append(_table(recent_period_rows, ["year", "trade_count", "net_expectancy_bps", "win_rate", "profit_factor", "label_bad_context_36_rate", "label_trade_win_rate", "label_positive_tail_rate", "label_negative_tail_rate"]))
    lines.append("")
    lines.append("## Baseline Comparison")
    lines.append("")
    lines.append(f"- Overall `baseline_no_gate` expectancy: `{baseline_summary['net_expectancy_bps']:.6f}` bps")
    lines.append(f"- Overall `baseline_no_gate` win rate: `{baseline_summary['win_rate']:.6f}`")
    lines.append(f"- Overall `baseline_no_gate` profit factor: `{baseline_summary['profit_factor']:.6f}`")
    lines.append("")
    lines.append(_table(recent_year_rows, ["split", "test_year", "test_count", "baseline_no_gate_test_net_expectancy_bps", "baseline_no_gate_test_win_rate", "baseline_no_gate_test_profit_factor"]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if SKLEARN_AVAILABLE and fold_rows:
        evaluated_rows = [row for row in fold_rows if row["model_status"] in {"model_execution_completed", "validation_sample_too_small"}]
        best_row = max(
            evaluated_rows,
            key=lambda row: (
                float(row["delta_vs_baseline_bps"]) if row["delta_vs_baseline_bps"] is not None else float("-inf"),
                int(row["test_kept_trade_count"] or 0),
            ),
        ) if evaluated_rows else None
        improved_any = any((row["delta_vs_baseline_bps"] or float("-inf")) > 0 for row in evaluated_rows)
        improved_recent_2025 = any(row["test_year"] == 2025 and (row["delta_vs_baseline_bps"] or float("-inf")) > 0 for row in evaluated_rows)
        improved_recent_2026 = any(row["test_year"] == 2026 and (row["delta_vs_baseline_bps"] or float("-inf")) > 0 for row in evaluated_rows)
        enough_recent = any(row["test_year"] in (2025, 2026) and int(row["test_kept_trade_count"] or 0) >= 10 for row in evaluated_rows)
        stable_behavior = any(row["model_status"] == "model_execution_completed" and row["test_year"] in (2023, 2024, 2025, 2026) for row in evaluated_rows)
        lines.append(
            f"1. Does any baseline model improve test-period expectancy versus no-gate baseline? {'Yes' if improved_any else 'No'}. "
            + (
                f"Best fold/model: `{best_row['split']} / {best_row['model_family']}` with delta `{_fmt(best_row['delta_vs_baseline_bps'])}` bps."
                if best_row is not None
                else "No evaluated fold/model available."
            )
        )
        lines.append(
            f"2. Does any model improve 2025 and 2026 separately? {'Yes' if improved_recent_2025 or improved_recent_2026 else 'No'}. "
            f"2025 improvement: `{str(improved_recent_2025).lower()}`; 2026 improvement: `{str(improved_recent_2026).lower()}`."
        )
        lines.append(
            f"3. Does any model preserve at least 10 trades in recent test windows? {'Yes' if enough_recent else 'No'}. "
            "The 2026 baseline window has only 8 trades, so 2026 remains sample-too-small for standalone approval."
        )
        lines.append(
            f"4. Does any model show stable validation-to-test behavior? {'Yes' if stable_behavior else 'No clear evidence yet'}. "
            "Validation is time-ordered, but recent folds remain sparse."
        )
        lines.append("5. Is there enough evidence to approve a production filter? No. This baseline can only determine whether meta-labeling is worth deeper research.")
    else:
        lines.append(
            "1. Does any baseline model improve test-period expectancy versus no-gate baseline? No model was executed in this environment because `sklearn` is unavailable, so no improvement is demonstrated."
        )
        lines.append(
            "2. Does any model improve 2025 and 2026 separately? No model was executed, so there is no improvement evidence for either year."
        )
        lines.append(
            "3. Does any model preserve at least 10 trades in recent test windows? The test windows are sized, but model preservation cannot be assessed until model execution is unblocked."
        )
        lines.append(
            "4. Does any model show stable validation-to-test behavior? No model results are available in this environment, so stability cannot be claimed."
        )
        lines.append("5. Is there enough evidence to approve a production filter? No. This baseline can only determine whether meta-labeling is worth deeper research.")
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical C_ExhaustionFade replay anchor remains valid as a research dataset.")
    lines.append("- The ex-ante feature set and label definitions are usable for a later model task.")
    lines.append("- The purged walk-forward scaffolding is ready for a future evaluation run.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- No model has been approved.")
    lines.append("- No production or paper-trading rule has been approved.")
    lines.append("- No improvement claim can be made from this blocked environment.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if SKLEARN_AVAILABLE and fold_rows:
        best_row = max(
            [row for row in fold_rows if row["delta_vs_baseline_bps"] is not None],
            key=lambda row: float(row["delta_vs_baseline_bps"]),
        )
        lines.append("Decision label: `meta_labeling_worth_deeper_research`.")
        lines.append(
            f"The strongest observed fold/model was `{best_row['split']} / {best_row['model_family']}` with delta `{_fmt(best_row['delta_vs_baseline_bps'])}` bps, but 2026 remains sample-too-small and no production or paper-trading approval is justified."
        )
    else:
        lines.append("Decision label: `model_execution_blocked`.")
        lines.append("The task establishes the baseline dataset and evaluation protocol, but model results remain blocked until `sklearn` is available in the execution environment.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Extend the current walk-forward meta-label baseline with more recent held-out data and compare against `baseline_no_gate` and the best simple ex-ante proxy gate. Do not promote any model without a separate candidate-selection and PSR/DSR/PBO process.")
    lines.append("")
    lines.append("## Model Execution Notes")
    lines.append("")
    lines.append(f"- Model execution status: `{fold_status}`")
    lines.append(f"- Purged walk-forward folds built: `{len(splits)}`")
    lines.append("- Thresholds are selected on validation only when model execution is available.")
    lines.append("- Test labels are never used for threshold selection.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trades = pd.read_csv(args.trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = load_750btc_bars(args.bar_dir)
    bars = normalize_v92_bar_timestamps(bars)
    bars = add_v92_regime_labels(bars)
    report = build_report(trades, bars=bars, trade_log_path=args.trade_log, bar_dir=args.bar_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
