#!/usr/bin/env python3
"""Research-only plan generator for C_ExhaustionFade meta-label baseline work."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for site_packages in sorted((ROOT / ".venv" / "lib").glob("python*/site-packages")):
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

import pandas as pd
import polars as pl

from scripts.diagnose_c_exhaustion_regime_context import REQUESTED_FEATURES, _compute_trade_context
from replays.c_exhaustion_replay import add_v92_regime_labels, load_750btc_bars, normalize_v92_bar_timestamps


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

TARGET_LABELS = [
    ("label_trade_win", "net_return_bps > 0"),
    ("label_positive_tail", "net_return_bps >= 200"),
    ("label_negative_tail", "net_return_bps <= -200"),
    ("label_bad_context_36", "trend_continuation_flag_36 OR failed_reversal_flag_36"),
    ("label_recent_decay", "year >= 2025"),
]

FORBIDDEN_FEATURES = [
    "net_return_bps",
    "gross_return_bps",
    "exit_time",
    "exit_price",
    "mfe_bps",
    "mae_bps",
    "post_signal_return_*",
    "trend_continuation_flag_*",
    "failed_reversal_flag_*",
    "anything computed after signal_time",
]

BASELINE_MODELS = [
    "logistic_regression_l1",
    "logistic_regression_l2",
    "decision_tree_depth_2",
    "decision_tree_depth_3",
    "calibrated_gradient_boosting_small",
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
    return str(value)


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def build_manifest(context: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    feature_rows: list[dict[str, object]] = []
    for feature in ALLOWED_FEATURES:
        feature_rows.append(
            {
                "feature": feature,
                "class": "allowed_ex_ante",
                "available": feature in context.columns,
                "null_count": int(context[feature].isna().sum()) if feature in context.columns else None,
            }
        )

    label_rows: list[dict[str, object]] = []
    bad_context = context["trend_continuation_flag_36"].fillna(False).astype(bool) | context["failed_reversal_flag_36"].fillna(False).astype(bool)
    label_values = {
        "label_trade_win": context["net_return_bps"] > 0,
        "label_positive_tail": context["net_return_bps"] >= 200,
        "label_negative_tail": context["net_return_bps"] <= -200,
        "label_bad_context_36": bad_context,
        "label_recent_decay": context["year"] >= 2025,
    }
    for label, rule in TARGET_LABELS:
        series = label_values[label]
        label_rows.append(
            {
                "label": label,
                "definition": rule,
                "positive_count": int(series.sum()),
                "positive_rate": float(series.mean()),
            }
        )
    return feature_rows, label_rows


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    context = _compute_trade_context(trades, bars)
    feature_rows, label_rows = build_manifest(context)

    missing_features = [feature for feature in REQUESTED_FEATURES if feature not in context.columns]
    feature_sample = context[["signal_time", "entry_time", "exit_time", "year", "net_return_bps", "trend_continuation_flag_36", "failed_reversal_flag_36"]].head(5).copy()
    feature_sample["bad_context_label_36"] = feature_sample["trend_continuation_flag_36"].fillna(False).astype(bool) | feature_sample["failed_reversal_flag_36"].fillna(False).astype(bool)

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Meta-Label Baseline Plan")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "Define a strictly ex-ante meta-label baseline for C_ExhaustionFade so future research can predict bad-context trades without leaking post-signal information."
    )
    lines.append("")
    lines.append("This is a plan only. No model is trained, no gate is selected, and no production or paper-trading approval is granted.")
    lines.append("")
    lines.append("## Why Meta-Labeling Is the Only Remaining C Path")
    lines.append("")
    lines.append(
        "The repaired replay, the fixed-exit diagnostics, the regime/context audit, the exit-hypothesis matrix, and the ex-ante proxy matrix all converged on the same conclusion: simple rule gates do not rescue the recent-period decay. A meta-label baseline is the only remaining path that can still use the canonical entries while learning to avoid the bad contexts ex-ante."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay context: existing C_ExhaustionFade replay helpers and regime labels")
    lines.append("")
    lines.append("## Candidate Labels")
    lines.append("")
    lines.append(_table(label_rows, ["label", "definition", "positive_count", "positive_rate"]))
    lines.append("")
    lines.append("## Allowed Ex-Ante Features")
    lines.append("")
    lines.append(_table(feature_rows, ["feature", "class", "available", "null_count"]))
    lines.append("")
    lines.append("## Forbidden Features / Leakage Guardrails")
    lines.append("")
    lines.append("The following are forbidden as model inputs:")
    for item in FORBIDDEN_FEATURES:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Time-Ordered Validation Design")
    lines.append("")
    lines.append(
        "Validation must be time-ordered only, with purged walk-forward splits and embargo. No random split, no shuffle split, and no same-period tuning."
    )
    lines.append("")
    lines.append(_table(
        [
            {"split": "walk_forward_1", "train": "2020-2021", "validate": "2022", "test": "2023"},
            {"split": "walk_forward_2", "train": "2020-2022", "validate": "2023", "test": "2024"},
            {"split": "walk_forward_3", "train": "2020-2023", "validate": "2024", "test": "2025"},
            {"split": "walk_forward_4", "train": "2020-2024", "validate": "2025", "test": "2026"},
        ],
        ["split", "train", "validate", "test"],
    ))
    lines.append("")
    lines.append("- purge window = 48 bars")
    lines.append("- embargo window = 48 bars")
    lines.append("- no random split")
    lines.append("- no shuffle split")
    lines.append("- no same-period tuning")
    lines.append("")
    lines.append("## Baseline Models For Later Evaluation")
    lines.append("")
    for model in BASELINE_MODELS:
        lines.append(f"- `{model}`")
    lines.append("")
    lines.append("## Acceptance Criteria")
    lines.append("")
    lines.append(
        "A future model is not useful unless it improves recent-period net expectancy after costs without destroying early/middle validation."
    )
    lines.append("A future model must beat `baseline_no_gate` and the best simple ex-ante proxy gate.")
    lines.append("A future model must pass PSR/DSR/PBO checks before being considered a serious research candidate.")
    lines.append("A future model must report calibration and confusion matrix by period.")
    lines.append("A future model must preserve minimum recent test sample count >= 10.")
    lines.append("A model cannot be promoted from this task.")
    lines.append("")
    lines.append("## Failure Criteria")
    lines.append("")
    lines.append("- The model leaks post-signal information.")
    lines.append("- The model fails to beat the canonical baseline and the best simple ex-ante proxy gate.")
    lines.append("- The model degrades early or middle validation materially.")
    lines.append("- The model cannot keep recent test sample count above the minimum threshold.")
    lines.append("- The model is not calibrated or cannot be summarized by period.")
    lines.append("")
    lines.append("## Decision Boundary")
    lines.append("")
    lines.append(
        "If the meta-label baseline does not improve recent-period performance with clean leakage controls, C_ExhaustionFade should be archived as a historical research anchor while infrastructure work moves to OFI/CVD."
    )
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Implement the first meta-label baseline exactly as planned, then evaluate it with the time-ordered validation design and the acceptance criteria above.")
    lines.append("")
    lines.append("## Feature / Label Manifest")
    lines.append("")
    lines.append(f"- Context rows evaluated: `{len(context)}`")
    lines.append(f"- Missing requested features in the current context builder: `{', '.join(missing_features) if missing_features else 'none'}`")
    lines.append("")
    lines.append("Sample context rows:")
    lines.append("")
    lines.append(_table(feature_sample.to_dict(orient="records"), list(feature_sample.columns)))
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
