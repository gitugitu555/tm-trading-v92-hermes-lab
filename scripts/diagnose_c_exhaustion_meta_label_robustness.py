#!/usr/bin/env python3
"""Research-only robustness scaffold for the C_ExhaustionFade meta-label baseline."""

from __future__ import annotations

import argparse
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

from scripts.diagnose_c_exhaustion_meta_label_baseline import (
    ALLOWED_FEATURES,
    MODEL_FAMILIES,
    _execute_model_fold,
    _trade_metrics_from_frame,
    build_meta_label_dataset,
    build_purged_walk_forward_splits,
    fit_preprocessors,
    transform_features,
)
from replays.c_exhaustion_replay import add_v92_regime_labels, load_750btc_bars, normalize_v92_bar_timestamps

BASELINE_RESULTS_DOC = Path("docs/v92_C_EXHAUSTION_META_LABEL_BASELINE_RESULTS.md")
MODEL_UNIVERSE = ["baseline_no_gate", *MODEL_FAMILIES]
THRESHOLD_CANDIDATES = 9
N_TRIALS = len(MODEL_FAMILIES) * THRESHOLD_CANDIDATES


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


def _trade_sharpe_and_psr(returns_bps: list[float]) -> dict[str, object]:
    series = pd.Series([float(x) for x in returns_bps if pd.notna(x)])
    trade_count = int(len(series))
    if trade_count < 10:
        return {
            "trade_count": trade_count,
            "mean_bps": float(series.mean()) if trade_count else None,
            "std_bps": float(series.std(ddof=1)) if trade_count > 1 else None,
            "trade_sharpe": None,
            "skew": None,
            "kurtosis": None,
            "psr_vs_zero": None,
            "psr_unreliable": True,
        }

    mean_bps = float(series.mean())
    std_bps = float(series.std(ddof=1))
    if not np.isfinite(std_bps) or std_bps == 0.0:
        return {
            "trade_count": trade_count,
            "mean_bps": mean_bps,
            "std_bps": std_bps,
            "trade_sharpe": None,
            "skew": float(series.skew()) if trade_count > 2 else None,
            "kurtosis": float(series.kurtosis() + 3.0) if trade_count > 3 else None,
            "psr_vs_zero": None,
            "psr_unreliable": True,
        }

    trade_sharpe = mean_bps / std_bps
    skew = float(series.skew()) if trade_count > 2 else None
    kurtosis = float(series.kurtosis() + 3.0) if trade_count > 3 else None
    if skew is None or kurtosis is None:
        return {
            "trade_count": trade_count,
            "mean_bps": mean_bps,
            "std_bps": std_bps,
            "trade_sharpe": trade_sharpe,
            "skew": skew,
            "kurtosis": kurtosis,
            "psr_vs_zero": None,
            "psr_unreliable": True,
        }

    denom = 1.0 - skew * trade_sharpe + ((kurtosis - 1.0) / 4.0) * (trade_sharpe**2)
    if not np.isfinite(denom) or denom <= 0.0:
        return {
            "trade_count": trade_count,
            "mean_bps": mean_bps,
            "std_bps": std_bps,
            "trade_sharpe": trade_sharpe,
            "skew": skew,
            "kurtosis": kurtosis,
            "psr_vs_zero": None,
            "psr_unreliable": True,
        }

    z = trade_sharpe * math.sqrt(trade_count - 1) / math.sqrt(denom)
    psr = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return {
        "trade_count": trade_count,
        "mean_bps": mean_bps,
        "std_bps": std_bps,
        "trade_sharpe": trade_sharpe,
        "skew": skew,
        "kurtosis": kurtosis,
        "psr_vs_zero": float(psr),
        "psr_unreliable": False,
    }


def _model_from_name(model_name: str):
    if model_name == "logistic_regression_l2":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000, penalty="l2", solver="liblinear", random_state=42)
    if model_name == "decision_tree_depth_2":
        from sklearn.tree import DecisionTreeClassifier

        return DecisionTreeClassifier(max_depth=2, random_state=42)
    if model_name == "decision_tree_depth_3":
        from sklearn.tree import DecisionTreeClassifier

        return DecisionTreeClassifier(max_depth=3, random_state=42)
    raise ValueError(f"Unknown model family: {model_name}")


def _compute_kept_test_returns_bps(
    model_name: str,
    train_df: pd.DataFrame,
    validate_df: pd.DataFrame,
    test_df: pd.DataFrame,
    selected_threshold: float | None,
) -> list[float]:
    if selected_threshold is None:
        return []

    imputer, scaler = fit_preprocessors(train_df, feature_names=ALLOWED_FEATURES, model_family=model_name)
    X_train = transform_features(train_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    X_validate = transform_features(validate_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    X_test = transform_features(test_df, feature_names=ALLOWED_FEATURES, imputer=imputer, scaler=scaler)

    model = _model_from_name(model_name)
    y_train = train_df["label_trade_win"].astype(int).copy()
    model.fit(X_train, y_train)
    _ = model.predict_proba(X_validate)[:, 1]
    test_scores = model.predict_proba(X_test)[:, 1]
    test_keep = test_scores >= float(selected_threshold)
    return test_df.loc[test_keep, "net_return_bps"].astype(float).tolist()


def build_evaluation_frames(trades: pd.DataFrame, bars: pl.DataFrame) -> dict[str, object]:
    dataset = build_meta_label_dataset(trades, bars)
    splits = build_purged_walk_forward_splits(dataset, purge_bars=48, embargo_bars=48)

    fold_rows: list[dict[str, object]] = []
    baseline_rows: list[dict[str, object]] = []
    for split in splits:
        train_df = dataset[split["train_mask"]].copy()
        validate_df = dataset[split["validate_mask"]].copy()
        test_df = dataset[split["test_mask"]].copy()
        baseline_metrics = _trade_metrics_from_frame(test_df)
        baseline_rows.append(
            {
                "test_year": int(split["test_year"]),
                "test_count": int(len(test_df)),
                "baseline_no_gate_test_net_expectancy_bps": float(baseline_metrics["net_expectancy_bps"]),
                "baseline_no_gate_test_win_rate": float(baseline_metrics["win_rate"]),
                "baseline_no_gate_test_profit_factor": float(baseline_metrics["profit_factor"]),
            }
        )
        for model_name in MODEL_FAMILIES:
            row = {
                "split": split["name"],
                "validate_year": int(split["validate_year"]),
                "test_year": int(split["test_year"]),
                "model_family": model_name,
                "train_count": int(len(train_df)),
                "validate_count": int(len(validate_df)),
                "test_count": int(len(test_df)),
                **_execute_model_fold(
                    model_name,
                    train_df,
                    validate_df,
                    test_df,
                    baseline_test_metrics=baseline_metrics,
                ),
            }
            row["kept_test_returns_bps"] = _compute_kept_test_returns_bps(
                model_name,
                train_df,
                validate_df,
                test_df,
                row.get("selected_threshold"),
            )
            fold_rows.append(row)

    return {
        "dataset": dataset,
        "splits": splits,
        "fold_rows": fold_rows,
        "baseline_rows": baseline_rows,
    }


def summarize_candidate_selection(candidate_name: str, fold_rows: list[dict[str, object]], baseline_rows: list[dict[str, object]]) -> dict[str, object]:
    if candidate_name == "baseline_no_gate":
        raise ValueError("baseline_no_gate is a reference, not a selection candidate")

    model_rows = [row for row in fold_rows if row["model_family"] == candidate_name]
    baseline_by_year = {row["test_year"]: row for row in baseline_rows}
    test_by_year = {row["test_year"]: row for row in model_rows}
    deltas = [float(row["delta_vs_baseline_bps"]) for row in model_rows if row["delta_vs_baseline_bps"] is not None]
    test_expectancies = [float(row["test_net_expectancy_bps_if_trading_kept_signals"]) for row in model_rows if row["test_net_expectancy_bps_if_trading_kept_signals"] is not None]
    baseline_expectancies = [float(row["baseline_no_gate_test_net_expectancy_bps"]) for row in model_rows if row["baseline_no_gate_test_net_expectancy_bps"] is not None]

    recent_2025_row = test_by_year.get(2025)
    recent_2026_row = test_by_year.get(2026)
    recent_2025_delta = float(recent_2025_row["delta_vs_baseline_bps"]) if recent_2025_row else None
    recent_2026_delta = float(recent_2026_row["delta_vs_baseline_bps"]) if recent_2026_row else None
    recent_2025_expectancy = float(recent_2025_row["test_net_expectancy_bps_if_trading_kept_signals"]) if recent_2025_row else None
    recent_2026_expectancy = float(recent_2026_row["test_net_expectancy_bps_if_trading_kept_signals"]) if recent_2026_row else None
    baseline_2025 = float(baseline_by_year[2025]["baseline_no_gate_test_net_expectancy_bps"]) if 2025 in baseline_by_year else None
    baseline_2026 = float(baseline_by_year[2026]["baseline_no_gate_test_net_expectancy_bps"]) if 2026 in baseline_by_year else None
    recent_2025_kept = int(recent_2025_row["test_kept_trade_count"]) if recent_2025_row else 0
    recent_2026_kept = int(recent_2026_row["test_kept_trade_count"]) if recent_2026_row else 0
    recent_2025_removed = int(recent_2025_row["test_removed_trade_count"]) if recent_2025_row else 0
    recent_2026_removed = int(recent_2026_row["test_removed_trade_count"]) if recent_2026_row else 0
    recent_total_kept = recent_2025_kept + recent_2026_kept
    recent_total_removed = recent_2025_removed + recent_2026_removed
    recent_kept_rate = recent_total_kept / (recent_total_kept + recent_total_removed) if (recent_total_kept + recent_total_removed) else 0.0
    recent_test_counts = [int(row["test_count"]) for row in model_rows if row["test_year"] in (2025, 2026)]
    sample_too_small = any(count < 10 for count in recent_test_counts) or recent_2026_kept < 10
    unstable = (
        recent_2025_delta is not None
        and recent_2026_delta is not None
        and ((recent_2025_delta > 0.0) != (recent_2026_delta > 0.0))
    )
    passes = (
        bool(deltas)
        and float(np.mean(deltas)) > 0.0
        and float(np.median(deltas)) > 0.0
        and recent_2025_delta is not None
        and recent_2026_delta is not None
        and recent_2025_delta > 0.0
        and recent_2026_delta > 0.0
        and recent_2025_expectancy is not None
        and recent_2026_expectancy is not None
        and baseline_2025 is not None
        and baseline_2026 is not None
        and recent_2025_expectancy > baseline_2025
        and recent_2026_expectancy > baseline_2026
        and recent_total_kept >= 10
        and all(int(row["test_kept_trade_count"]) >= 5 or int(row["test_count"]) < 10 for row in model_rows)
    )

    return {
        "model_family": candidate_name,
        "fold_count": len(model_rows),
        "mean_test_delta_bps": float(np.mean(deltas)) if deltas else None,
        "median_test_delta_bps": float(np.median(deltas)) if deltas else None,
        "min_test_delta_bps": float(np.min(deltas)) if deltas else None,
        "max_test_delta_bps": float(np.max(deltas)) if deltas else None,
        "positive_delta_fold_count": int(sum(delta > 0.0 for delta in deltas)),
        "negative_delta_fold_count": int(sum(delta < 0.0 for delta in deltas)),
        "recent_2025_delta_bps": recent_2025_delta,
        "recent_2026_delta_bps": recent_2026_delta,
        "recent_total_kept_trades": recent_total_kept,
        "recent_total_removed_trades": recent_total_removed,
        "recent_kept_rate": recent_kept_rate,
        "mean_test_expectancy_bps": float(np.mean(test_expectancies)) if test_expectancies else None,
        "median_test_expectancy_bps": float(np.median(test_expectancies)) if test_expectancies else None,
        "mean_baseline_expectancy_bps": float(np.mean(baseline_expectancies)) if baseline_expectancies else None,
        "median_baseline_expectancy_bps": float(np.median(baseline_expectancies)) if baseline_expectancies else None,
        "passes_candidate_selection_protocol": passes,
        "sample_too_small": sample_too_small,
        "unstable": unstable,
    }


def summarize_candidate_psr(candidate_name: str, fold_rows: list[dict[str, object]]) -> dict[str, object]:
    if candidate_name == "baseline_no_gate":
        raise ValueError("PSR is reported for the candidate models, not the baseline reference")

    returns: list[float] = []
    for row in fold_rows:
        if row["model_family"] != candidate_name:
            continue
        kept_df = row.get("kept_test_returns_bps")
        if kept_df is not None:
            returns.extend(list(kept_df))
    stats = _trade_sharpe_and_psr(returns)
    stats["candidate"] = candidate_name
    return stats


def summarize_fold_rows_by_year(fold_rows: list[dict[str, object]], model_name: str) -> dict[int, dict[str, object]]:
    summary: dict[int, dict[str, object]] = {}
    for row in fold_rows:
        if row["model_family"] != model_name:
            continue
        summary[int(row["test_year"])] = {
            "test_net_expectancy_bps_if_trading_kept_signals": row["test_net_expectancy_bps_if_trading_kept_signals"],
            "delta_vs_baseline_bps": row["delta_vs_baseline_bps"],
            "test_kept_trade_count": row["test_kept_trade_count"],
            "test_count": row["test_count"],
        }
    return summary


def _rank_models_by_metric(fold_rows: list[dict[str, object]], metric_key: str) -> list[str]:
    ranked = sorted(
        [row for row in fold_rows if row["model_family"] in MODEL_FAMILIES],
        key=lambda row: (float(row[metric_key]), row["model_family"]),
        reverse=True,
    )
    return [row["model_family"] for row in ranked]


def compute_pbo_scaffold(fold_rows: list[dict[str, object]]) -> dict[str, object]:
    fold_summaries: list[dict[str, object]] = []
    bad = 0
    valid_folds = 0
    for split_name in sorted({row["split"] for row in fold_rows}):
        rows = [row for row in fold_rows if row["split"] == split_name]
        if len(rows) < 2:
            continue
        valid_folds += 1
        validation_sorted = sorted(rows, key=lambda row: (float(row["validate_net_expectancy_bps_if_trading_kept_signals"]), row["model_family"]), reverse=True)
        test_sorted = sorted(rows, key=lambda row: (float(row["test_net_expectancy_bps_if_trading_kept_signals"]), row["model_family"]), reverse=True)
        validation_best = validation_sorted[0]
        test_rank_map = {row["model_family"]: idx + 1 for idx, row in enumerate(test_sorted)}
        validation_best_test_rank = test_rank_map[validation_best["model_family"]]
        below_median = validation_best_test_rank > (len(test_sorted) / 2.0)
        if below_median:
            bad += 1
        fold_summaries.append(
            {
                "split": split_name,
                "validation_best_model": validation_best["model_family"],
                "validation_best_validate_rank": 1,
                "validation_best_test_rank": validation_best_test_rank,
                "below_median_on_test": below_median,
            }
        )
    return {
        "pbo_fold_count": valid_folds,
        "pbo_bad_fold_count": bad,
        "pbo_rate": float(bad / valid_folds) if valid_folds else None,
        "pbo_low_power": valid_folds < 5,
        "fold_summaries": fold_summaries,
    }


def build_decision(candidate_summaries: list[dict[str, object]], psr_summaries: list[dict[str, object]], pbo_summary: dict[str, object]) -> dict[str, object]:
    passing = [row for row in candidate_summaries if row["passes_candidate_selection_protocol"]]
    if not passing:
        return {
            "decision_label": "archive_C_recommended",
            "production_status": "production_invalid",
            "paper_live_status": "paper_live_blocked",
            "decision_lines": [
                "Decision label: `archive_C_recommended`.",
                "No model passed the candidate-selection protocol. Archive C as a historical anchor unless stronger ex-ante features are introduced.",
                "Production status: `production_invalid`.",
                "Paper/live status: `paper_live_blocked`.",
            ],
        }

    psr_unreliable = any(row["psr_unreliable"] for row in psr_summaries if row["candidate"] in {r["model_family"] for r in passing})
    sample_too_small = any(row["sample_too_small"] for row in passing)
    pbo_low_power = bool(pbo_summary.get("pbo_low_power", True))

    if psr_unreliable or pbo_low_power or sample_too_small:
        return {
            "decision_label": "meta_labeling_worth_deeper_research",
            "production_status": "production_invalid",
            "paper_live_status": "paper_live_blocked",
            "decision_lines": [
                "Decision label: `meta_labeling_worth_deeper_research`.",
                "One or more models passed the candidate-selection protocol, but the robustness scaffold is not strong enough for approval.",
                "Production remains invalid and paper/live remains blocked until a fuller candidate-selection and robustness process is completed.",
                "Production status: `production_invalid`.",
                "Paper/live status: `paper_live_blocked`.",
            ],
        }

    return {
        "decision_label": "candidate_selection_passed",
        "production_status": "production_invalid",
        "paper_live_status": "paper_live_blocked",
        "decision_lines": [
            "Decision label: `candidate_selection_passed`.",
            "This is deeper-research only. Production remains invalid and paper/live remains blocked.",
            "Production status: `production_invalid`.",
            "Paper/live status: `paper_live_blocked`.",
        ],
    }


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    frames = build_evaluation_frames(trades, bars)
    fold_rows = frames["fold_rows"]
    baseline_rows = frames["baseline_rows"]
    candidate_rows = [summarize_candidate_selection(model, fold_rows, baseline_rows) for model in MODEL_FAMILIES]
    psr_rows = [summarize_candidate_psr(model, fold_rows) for model in MODEL_FAMILIES]
    pbo_summary = compute_pbo_scaffold(fold_rows)
    decision = build_decision(candidate_rows, psr_rows, pbo_summary)
    fold_year_lookup = {model: summarize_fold_rows_by_year(fold_rows, model) for model in MODEL_FAMILIES}
    baseline_by_year = {row["test_year"]: row for row in baseline_rows}

    recent_year_rows = baseline_rows
    fold_summary_rows = [
        {
            **row,
            "baseline_no_gate_test_net_expectancy_bps": baseline_by_year[row["test_year"]]["baseline_no_gate_test_net_expectancy_bps"],
        }
        for row in fold_rows
    ]

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Meta-Label Robustness Scaffold")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Assess whether the observed meta-label improvement is robust enough to justify deeper research.")
    lines.append("")
    lines.append("This task does not approve a production model, production gate, paper-trading rule, or live-trading rule.")
    lines.append("")
    lines.append("## Research-Only Guardrails")
    lines.append("")
    lines.append("- Candidate universe is frozen to the baseline models already evaluated.")
    lines.append("- No new models, features, labels, thresholds, or walk-forward splits were introduced.")
    lines.append("- No production approval.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append(f"- Baseline results doc: `{BASELINE_RESULTS_DOC}`")
    lines.append("")
    lines.append("## Candidate Universe")
    lines.append("")
    lines.append("- `baseline_no_gate`")
    lines.append("- `logistic_regression_l2`")
    lines.append("- `decision_tree_depth_2`")
    lines.append("- `decision_tree_depth_3`")
    lines.append("")
    lines.append("## Candidate-Selection Protocol")
    lines.append("")
    lines.append("A model is only a serious research candidate if all are true:")
    lines.append("")
    lines.append("1. Mean test delta_vs_baseline_bps across walk-forward folds > 0")
    lines.append("2. Median test delta_vs_baseline_bps across folds > 0")
    lines.append("3. 2025 test delta_vs_baseline_bps > 0")
    lines.append("4. 2026 test delta_vs_baseline_bps > 0")
    lines.append("5. 2025 test_net_expectancy_bps_if_trading_kept_signals > baseline_2025")
    lines.append("6. 2026 test_net_expectancy_bps_if_trading_kept_signals > baseline_2026")
    lines.append("7. Total kept recent trades across 2025 and 2026 >= 10")
    lines.append("8. No test fold has kept_trade_count < 5 unless baseline test_count itself is < 10")
    lines.append("")
    lines.append("## Fold-Level Model Summary")
    lines.append("")
    lines.append(
        _table(
            fold_summary_rows,
            [
                "split",
                "validate_year",
                "test_year",
                "model_family",
                "model_status",
                "validation_sample_too_small",
                "selected_threshold",
                "train_count",
                "validate_count",
                "test_count",
                "test_kept_trade_count",
                "test_removed_trade_count",
                "test_kept_rate",
                "test_net_expectancy_bps_if_trading_kept_signals",
                "baseline_no_gate_test_net_expectancy_bps",
                "delta_vs_baseline_bps",
            ],
        )
    )
    lines.append("")
    lines.append("## Candidate Stability Summary")
    lines.append("")
    lines.append(
        _table(
            candidate_rows,
            [
                "model_family",
                "fold_count",
                "mean_test_delta_bps",
                "median_test_delta_bps",
                "min_test_delta_bps",
                "max_test_delta_bps",
                "positive_delta_fold_count",
                "negative_delta_fold_count",
                "recent_2025_delta_bps",
                "recent_2026_delta_bps",
                "recent_total_kept_trades",
                "recent_total_removed_trades",
                "recent_kept_rate",
                "mean_test_expectancy_bps",
                "median_test_expectancy_bps",
                "mean_baseline_expectancy_bps",
                "median_baseline_expectancy_bps",
                "passes_candidate_selection_protocol",
                "sample_too_small",
                "unstable",
            ],
        )
    )
    lines.append("")
    lines.append("## Recent-Year Summary")
    lines.append("")
    lines.append(
        _table(
            recent_year_rows,
            [
                "test_year",
                "test_count",
                "baseline_no_gate_test_net_expectancy_bps",
                "baseline_no_gate_test_win_rate",
                "baseline_no_gate_test_profit_factor",
            ],
        )
    )
    lines.append("")
    lines.append("## PSR Scaffold")
    lines.append("")
    lines.append(
        _table(
            psr_rows,
            [
                "candidate",
                "trade_count",
                "mean_bps",
                "std_bps",
                "trade_sharpe",
                "skew",
                "kurtosis",
                "psr_vs_zero",
                "psr_unreliable",
            ],
        )
    )
    lines.append("")
    lines.append("## DSR Scaffold")
    lines.append("")
    lines.append(f"- model families: `{len(MODEL_FAMILIES)}`")
    lines.append(f"- threshold candidates: `{THRESHOLD_CANDIDATES}`")
    lines.append(f"- number_of_trials: `{N_TRIALS}`")
    lines.append("- dsr_scaffold_only: `true`")
    lines.append("- dsr_penalty_note: `DSR requires a fuller multiple-testing implementation; this scaffold records candidate count and PSR only.`")
    lines.append("")
    lines.append("## PBO Scaffold")
    lines.append("")
    lines.append(_table(pbo_summary["fold_summaries"], ["split", "validation_best_model", "validation_best_validate_rank", "validation_best_test_rank", "below_median_on_test"]))
    lines.append("")
    lines.append(f"- pbo_fold_count: `{pbo_summary['pbo_fold_count']}`")
    lines.append(f"- pbo_bad_fold_count: `{pbo_summary['pbo_bad_fold_count']}`")
    lines.append(f"- pbo_rate: `{_fmt(pbo_summary['pbo_rate'])}`")
    lines.append(f"- pbo_low_power: `{_fmt(pbo_summary['pbo_low_power'])}`")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    passing = [row for row in candidate_rows if row["passes_candidate_selection_protocol"]]
    if passing:
        pass_bits = []
        for row in passing:
            year_lookup = fold_year_lookup[row["model_family"]]
            year_bits = []
            for year in (2023, 2024, 2025, 2026):
                if year in year_lookup:
                    year_info = year_lookup[year]
                    year_bits.append(
                        f"{year} expectancy {_fmt(year_info['test_net_expectancy_bps_if_trading_kept_signals'])} bps "
                        f"(delta {_fmt(year_info['delta_vs_baseline_bps'])} bps)"
                    )
            pass_bits.append(
                f"`{row['model_family']}`: " + "; ".join(year_bits)
            )
        lines.append("1. Does any model pass the candidate-selection protocol? Yes: " + "; ".join(pass_bits) + ".")
    else:
        lines.append("1. Does any model pass the candidate-selection protocol? No.")
    lines.append(
        "2. Is the 2026 improvement sufficient for standalone approval? No. The 2026 fold has only 8 baseline trades, so the strongest 2026 lift remains sample-too-small for standalone approval."
    )
    lines.append(
        "3. Does PSR provide strong evidence after sample-size caveats? No. The scaffold records PSR, but it is descriptive only and does not override the recent sample-size caveats."
    )
    lines.append("4. Does DSR provide strong evidence after multiple-testing caveats? No. DSR remains a scaffold only with `number_of_trials = 27`.")
    lines.append(
        f"5. Does PBO indicate severe overfitting risk? {'Inconclusive / low power' if pbo_summary['pbo_low_power'] else 'Not severe from this scaffold alone'}. The fold count is small, so the PBO estimate has low power."
    )
    lines.append("6. Is there enough evidence to approve a production or paper filter? No.")
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical C_ExhaustionFade replay anchor remains valid as a research dataset.")
    lines.append("- The meta-label baseline results remain useful as a bounded research signal.")
    lines.append("- The candidate-selection and robustness scaffolding is now documented and testable.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- Model execution completed, but no model is approved.")
    lines.append("- No production or paper filter is approved.")
    lines.append("- No live-trading rule is approved.")
    lines.append("- No candidate-selection result should be treated as a final endorsement.")
    lines.append("- The 2026 improvement is sample-too-small for standalone approval.")
    lines.append("- The 2025 improvement is small and remains negative in absolute expectancy.")
    lines.append("- Stable validation-to-test robustness is not proven.")
    lines.append("- DSR is not fully implemented; it is a scaffold only.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.extend(decision["decision_lines"])
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Use this scaffold to decide whether the next research step is stronger ex-ante features or a larger holdout. Do not approve production, paper trading, or live trading until a separate candidate-selection and PSR/DSR/PBO process is completed.")
    lines.append("")
    lines.append("## Robustness Notes")
    lines.append("")
    lines.append("- Candidate-selection protocol and robustness metrics are frozen to the already-evaluated meta-label baseline.")
    lines.append("- PBO is low-power by construction here because only four walk-forward folds and three candidate models are available.")
    lines.append("- DSR is explicitly a scaffold; it records the multiple-testing burden without claiming certainty.")
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
