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

SKLEARN_AVAILABLE = importlib.util.find_spec("sklearn") is not None

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


def select_validation_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    if y_true.size == 0:
        return 0.5

    thresholds = np.unique(np.concatenate(([0.0, 0.5, 1.0], y_score)))
    best_threshold = 0.5
    best_key = (-1.0, -1.0, -1.0)
    for threshold in thresholds:
        pred = y_score >= threshold
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        key = (f1, precision, -float(threshold))
        if key > best_key:
            best_key = key
            best_threshold = float(threshold)
    return best_threshold


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


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
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


def _safe_profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    if len(wins) == 0 and len(losses) == 0:
        return 0.0
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    if len(losses) and abs(loss_sum) > 0.0:
        return float(wins.sum() / abs(loss_sum))
    return float("inf") if len(wins) else 0.0


def _trade_financial_metrics(df: pd.DataFrame) -> dict[str, object]:
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


def _train_and_evaluate_if_possible(
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

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.tree import DecisionTreeClassifier

    X_train, y_train = _prepare_xy(train_df, ALLOWED_FEATURES)
    X_validate, y_validate = _prepare_xy(validate_df, ALLOWED_FEATURES)
    X_test, y_test = _prepare_xy(test_df, ALLOWED_FEATURES)

    if model_name == "logistic_regression_l2":
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", LogisticRegression(max_iter=1000, penalty="l2", solver="liblinear")),
            ]
        )
    elif model_name == "decision_tree_depth_2":
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DecisionTreeClassifier(max_depth=2, random_state=42)),
            ]
        )
    elif model_name == "decision_tree_depth_3":
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DecisionTreeClassifier(max_depth=3, random_state=42)),
            ]
        )
    else:
        raise ValueError(f"Unknown model family: {model_name}")

    if y_train.nunique() < 2 or y_validate.nunique() < 2 or y_test.nunique() < 2:
        row["model_status"] = "blocked_single_class_split"
        return row

    model.fit(X_train, y_train)
    validate_scores = model.predict_proba(X_validate)[:, 1]
    threshold = select_validation_threshold(y_validate.to_numpy(), validate_scores)
    test_scores = model.predict_proba(X_test)[:, 1]
    test_keep = test_scores >= threshold
    test_pred = test_keep.astype(int)
    validate_pred = (validate_scores >= threshold).astype(int)

    validate_metrics = _binary_metrics(y_validate.to_numpy(), validate_pred)
    test_metrics = _binary_metrics(y_test.to_numpy(), test_pred)
    kept_df = test_df.loc[test_keep].copy()
    kept_financial = _trade_financial_metrics(kept_df)

    row.update(
        {
            "model_status": "evaluated",
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
        }
    )
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
        baseline_test_metrics = _trade_financial_metrics(test_df)
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
                    "model_family": model_name,
                    "train_count": int(len(train_df)),
                    "validate_count": int(len(validate_df)),
                    "test_count": int(len(test_df)),
                    **_train_and_evaluate_if_possible(
                        model_name,
                        train_df,
                        validate_df,
                        test_df,
                        baseline_test_metrics=baseline_test_metrics,
                    ),
                }
            )

    recent_period_rows = []
    for year in [2025, 2026]:
        year_df = dataset[dataset["year"] == year].copy()
        metrics = _trade_financial_metrics(year_df)
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

    baseline_summary = _trade_financial_metrics(dataset)
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
                "model_family",
                "model_status",
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
    lines.append("The task establishes the baseline dataset and evaluation protocol, but model results remain blocked until `sklearn` is available in the execution environment.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Run the same dataset and evaluator on an environment with `sklearn` installed, then compare validation-selected thresholds and test metrics against `baseline_no_gate` and the best simple ex-ante proxy gate.")
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
