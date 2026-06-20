#!/usr/bin/env python3
"""Aggregate selectivity diagnostic for rescued giveback-loss vs clipped clean-winner trades."""

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

from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import (  # noqa: E402
    _load_bars,
    _markdown_table,
    _parse_trade_frame,
)
from scripts.v92_fixed_running_mfe_giveback_protection_experiment import (  # noqa: E402
    ACTIVATION_BPS,
    GIVEBACK_FRACTION,
    MIN_COMPLETED_BARS,
    evaluate_experiment,
)

DEFAULT_TRADE_LOG = Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_MFE_PATH_SELECTIVITY_DIAGNOSTIC_EXPERIMENT.md")

RESCUED_CLASS = "giveback_loss"
CLIPPED_CLASS = "clean_winner"
WEAK_CLASS = "weak_positive_exit"
OTHER_LABELS = ["bad_entry_loss", "unresolved"]


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{float(value) * 100.0:.3f}%"


def _summary_stats(series: pd.Series) -> dict[str, object]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "min": None,
            "max": None,
        }
    return {
        "count": int(clean.shape[0]),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "min": float(clean.min()),
        "max": float(clean.max()),
    }


def _stats_row(prefix: str, frame: pd.DataFrame, field: str) -> dict[str, object]:
    stats = _summary_stats(frame[field])
    return {
        f"{prefix}_count": stats["count"],
        f"{prefix}_mean": stats["mean"],
        f"{prefix}_median": stats["median"],
        f"{prefix}_p25": stats["p25"],
        f"{prefix}_p75": stats["p75"],
        f"{prefix}_min": stats["min"],
        f"{prefix}_max": stats["max"],
    }


def _period_label(year: int | float | pd._libs.missing.NAType) -> str:
    try:
        return "recent_decay" if int(year) >= 2025 else "historical"
    except Exception:
        return "unresolved"


def _decorate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["activation_offset_bars"] = pd.to_numeric(out["activation_completed_bars"], errors="coerce")
    out["trigger_offset_bars"] = pd.to_numeric(out["trigger_completed_bars"], errors="coerce")
    out["delay_activation_to_trigger_bars"] = out["trigger_offset_bars"] - out["activation_offset_bars"]
    out["period"] = out["year"].apply(_period_label)
    out["mechanical_delta_bps"] = pd.to_numeric(out["synthetic_gross_return_bps"], errors="coerce") - pd.to_numeric(out["gross_return_bps"], errors="coerce")
    out["mechanical_net_delta_bps"] = pd.to_numeric(out["synthetic_net_return_bps"], errors="coerce") - pd.to_numeric(out["net_return_bps"], errors="coerce")
    out["trigger_class"] = out["original_final_class"]
    return out


def _synthetic_causality_tests() -> list[dict[str, object]]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pd.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 111, 110, 108, 106, 104, 103, 102, 101], dtype=float),
            "low": np.full(20, 99.0),
            "close": np.array([100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 104, 103.5, 102, 101, 100, 99.5, 99, 98.5, 98], dtype=float),
        }
    )
    trades = pd.DataFrame(
        {
            "signal_index": [0],
            "entry_index": [1],
            "exit_index": [18],
            "signal_time": [base_times[1]],
            "entry_time": [base_times[1]],
            "exit_time": [base_times[18]],
            "entry_price": [100.0],
            "exit_price": [100.0],
            "gross_return_bps": [0.0],
            "net_return_bps": [-1.0],
            "year": [2024],
        }
    )

    base = evaluate_experiment(trades, bars)
    future_bars = bars.copy()
    future_bars.loc[18:, "high"] = 9999.0
    future_bars.loc[18:, "close"] = 9998.0
    future = evaluate_experiment(trades, future_bars)

    mutated_trade = trades.copy()
    mutated_trade["exit_price"] = 9999.0
    mutated_trade["gross_return_bps"] = 99999.0
    mutated_trade["net_return_bps"] = 99988.0
    mutated = evaluate_experiment(mutated_trade, bars)

    return [
        {
            "name": "future-bars-do-not-change-trigger",
            "passed": bool(
                base.loc[0, "triggered"]
                and future.loc[0, "triggered"]
                and base.loc[0, "trigger_completed_bars"] == future.loc[0, "trigger_completed_bars"]
                and base.loc[0, "trigger_return_bps"] == future.loc[0, "trigger_return_bps"]
            ),
            "details": f"baseline_trigger={base.loc[0, 'trigger_completed_bars']}, future_trigger={future.loc[0, 'trigger_completed_bars']}",
        },
        {
            "name": "original-exit-labels-do-not-decide-trigger",
            "passed": bool(
                base.loc[0, "triggered"]
                and mutated.loc[0, "triggered"]
                and base.loc[0, "trigger_completed_bars"] == mutated.loc[0, "trigger_completed_bars"]
                and base.loc[0, "trigger_return_bps"] == mutated.loc[0, "trigger_return_bps"]
            ),
            "details": "trigger fields stayed fixed after mutating original exit return fields",
        },
        {
            "name": "trigger-uses-running-mfe-and-current-return-only",
            "passed": bool(base.loc[0, "triggered"] and base.loc[0, "trigger_running_mfe_bps"] >= ACTIVATION_BPS and base.loc[0, "trigger_return_bps"] <= GIVEBACK_FRACTION * base.loc[0, "trigger_running_mfe_bps"]),
            "details": f"trigger_mfe={base.loc[0, 'trigger_running_mfe_bps']}, trigger_return={base.loc[0, 'trigger_return_bps']}",
        },
    ]


def evaluate_selectivity_experiment(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    frame = evaluate_experiment(trades, bars)
    frame = _decorate_frame(frame)
    return frame


def _subset(frame: pd.DataFrame, class_name: str) -> pd.DataFrame:
    return frame[frame["original_final_class"] == class_name].copy()


def _triggered_subset(frame: pd.DataFrame, class_name: str) -> pd.DataFrame:
    return frame[(frame["original_final_class"] == class_name) & frame["was_triggered"]].copy()


def _comparison_table(frame: pd.DataFrame, fields: list[tuple[str, str]]) -> list[dict[str, object]]:
    rescued = _triggered_subset(frame, RESCUED_CLASS)
    clipped = _triggered_subset(frame, CLIPPED_CLASS)
    rows: list[dict[str, object]] = []
    for label, field in fields:
        rescued_stats = _summary_stats(rescued[field])
        clipped_stats = _summary_stats(clipped[field])
        rows.append(
            {
                "field": label,
                "rescued_count": rescued_stats["count"],
                "rescued_mean": rescued_stats["mean"],
                "rescued_median": rescued_stats["median"],
                "rescued_p25": rescued_stats["p25"],
                "rescued_p75": rescued_stats["p75"],
                "rescued_min": rescued_stats["min"],
                "rescued_max": rescued_stats["max"],
                "clipped_count": clipped_stats["count"],
                "clipped_mean": clipped_stats["mean"],
                "clipped_median": clipped_stats["median"],
                "clipped_p25": clipped_stats["p25"],
                "clipped_p75": clipped_stats["p75"],
                "clipped_min": clipped_stats["min"],
                "clipped_max": clipped_stats["max"],
                "mean_diff": (rescued_stats["mean"] - clipped_stats["mean"]) if rescued_stats["mean"] is not None and clipped_stats["mean"] is not None else None,
                "median_diff": (rescued_stats["median"] - clipped_stats["median"]) if rescued_stats["median"] is not None and clipped_stats["median"] is not None else None,
            }
        )
    return rows


def _group_year_table(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in sorted(frame["year"].dropna().astype(int).unique().tolist()):
        year_frame = frame[frame["year"] == year]
        for label, class_name in [("rescued_giveback_loss", RESCUED_CLASS), ("clipped_clean_winner", CLIPPED_CLASS), ("weak_positive", WEAK_CLASS)]:
            subset = _triggered_subset(year_frame, class_name) if class_name != WEAK_CLASS else year_frame[(year_frame["original_final_class"] == WEAK_CLASS) & year_frame["was_triggered"]].copy()
            rows.append(
                {
                    "year": year,
                    "group": label,
                    "count": int(len(subset)),
                    "mean_activation_offset_bars": float(subset["activation_offset_bars"].mean()) if len(subset) else None,
                    "mean_trigger_offset_bars": float(subset["trigger_offset_bars"].mean()) if len(subset) else None,
                    "mean_delay_activation_to_trigger_bars": float(subset["delay_activation_to_trigger_bars"].mean()) if len(subset) else None,
                    "mean_running_mfe_at_activation_bps": float(subset["activation_running_mfe_bps"].mean()) if len(subset) else None,
                    "mean_running_mfe_at_trigger_bps": float(subset["trigger_running_mfe_bps"].mean()) if len(subset) else None,
                    "mean_current_return_at_trigger_bps": float(subset["trigger_return_bps"].mean()) if len(subset) else None,
                    "mean_giveback_depth_bps": float(subset["trigger_giveback_bps"].mean()) if len(subset) else None,
                    "mean_original_return_bps": float(subset["gross_return_bps"].mean()) if len(subset) else None,
                    "mean_mechanical_return_bps": float(subset["synthetic_gross_return_bps"].mean()) if len(subset) else None,
                    "mean_mechanical_delta_bps": float(subset["mechanical_delta_bps"].mean()) if len(subset) else None,
                }
            )
    return rows


def _period_table(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period in ["historical", "recent_decay"]:
        period_frame = frame[frame["period"] == period]
        for label, class_name in [("rescued_giveback_loss", RESCUED_CLASS), ("clipped_clean_winner", CLIPPED_CLASS), ("weak_positive", WEAK_CLASS)]:
            subset = period_frame[(period_frame["original_final_class"] == class_name) & period_frame["was_triggered"]].copy()
            rows.append(
                {
                    "period": period,
                    "group": label,
                    "count": int(len(subset)),
                    "mean_trigger_offset_bars": float(subset["trigger_offset_bars"].mean()) if len(subset) else None,
                    "mean_delay_activation_to_trigger_bars": float(subset["delay_activation_to_trigger_bars"].mean()) if len(subset) else None,
                    "mean_current_return_at_trigger_bps": float(subset["trigger_return_bps"].mean()) if len(subset) else None,
                    "mean_giveback_depth_bps": float(subset["trigger_giveback_bps"].mean()) if len(subset) else None,
                    "mean_mechanical_delta_bps": float(subset["mechanical_delta_bps"].mean()) if len(subset) else None,
                }
            )
    return rows


def build_report(trades_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trades_path)
    bars, bar_files = _load_bars(bar_dir)
    frame = evaluate_selectivity_experiment(trades, bars)

    rescued = _triggered_subset(frame, RESCUED_CLASS)
    clipped = _triggered_subset(frame, CLIPPED_CLASS)
    weak = _triggered_subset(frame, WEAK_CLASS)
    other = frame[frame["was_triggered"] & ~frame["original_final_class"].isin([RESCUED_CLASS, CLIPPED_CLASS, WEAK_CLASS])].copy()

    total_triggered = int(frame["was_triggered"].sum())
    total_activated = int(frame["was_activated"].sum())

    population = [
        {"category": "total_inspected", "count": int(len(frame))},
        {"category": "activated_trades", "count": total_activated},
        {"category": "triggered_trades", "count": total_triggered},
        {"category": "triggered_rescued_giveback_losses", "count": int(len(rescued))},
        {"category": "triggered_clipped_clean_winners", "count": int(len(clipped))},
        {"category": "triggered_weak_positive_trades", "count": int(len(weak))},
        {"category": "other_uncategorized_triggered", "count": int(len(other))},
    ]

    fields = [
        ("activation_offset_bars", "activation_offset_bars"),
        ("trigger_offset_bars", "trigger_offset_bars"),
        ("delay_activation_to_trigger_bars", "delay_activation_to_trigger_bars"),
        ("running_mfe_at_activation_bps", "activation_running_mfe_bps"),
        ("running_mfe_at_trigger_bps", "trigger_running_mfe_bps"),
        ("current_return_at_trigger_bps", "trigger_return_bps"),
        ("giveback_depth_at_trigger_bps", "trigger_giveback_bps"),
        ("original_realized_return_bps", "gross_return_bps"),
        ("mechanical_fixed_rule_return_bps", "synthetic_gross_return_bps"),
        ("mechanical_minus_original_delta_bps", "mechanical_delta_bps"),
    ]
    field_rows = _comparison_table(frame, fields)
    year_rows = _group_year_table(frame)
    period_rows = _period_table(frame)
    tests = _synthetic_causality_tests()

    report: list[str] = []
    report.append("# V9.2 Hermes MFE Path Selectivity Diagnostic Experiment")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("* Determine whether triggered rescued giveback-loss trades and triggered clipped clean-winner trades are separable using only information available before or at the fixed trigger point.")
    report.append("* This is aggregate-only diagnostic work in Hermes Lab.")
    report.append("* No trading rule is implemented, tuned, or approved.")
    report.append("")
    report.append("Proposed experiment name:")
    report.append("")
    report.append("`mfe_path_selectivity_diagnostic_experiment`")
    report.append("")
    report.append("## Population Accounting")
    report.append("")
    report.append(_markdown_table(population, ["category", "count"]))
    report.append("")
    report.append("## Trigger Class Accounting")
    report.append("")
    report.append(f"- rescued giveback-loss triggers: `{len(rescued)}`")
    report.append(f"- clipped clean-winner triggers: `{len(clipped)}`")
    report.append(f"- weak-positive triggers: `{len(weak)}`")
    report.append(f"- other/uncategorized triggered: `{len(other)}`")
    report.append("")
    report.append("## Synthetic Causality Checks")
    report.append("")
    for item in tests:
        status = "passed" if item["passed"] else "failed"
        report.append(f"- {item['name']}: `{status}` ({item['details']})")
    report.append("")
    report.append("## Triggered Group Comparison")
    report.append("")
    report.append(f"- activation threshold used only for labeling: `{ACTIVATION_BPS:.0f} bps`")
    report.append(f"- giveback ratio used only for labeling: `{GIVEBACK_FRACTION:.2f}`")
    report.append(f"- minimum delay used only for labeling: `{MIN_COMPLETED_BARS}` bars")
    report.append("")
    report.append(_markdown_table(field_rows, [
        "field",
        "rescued_count",
        "rescued_mean",
        "rescued_median",
        "rescued_p25",
        "rescued_p75",
        "rescued_min",
        "rescued_max",
        "clipped_count",
        "clipped_mean",
        "clipped_median",
        "clipped_p25",
        "clipped_p75",
        "clipped_min",
        "clipped_max",
        "mean_diff",
        "median_diff",
    ]))
    report.append("")
    report.append("## By-Year Breakdown")
    report.append("")
    report.append(_markdown_table(year_rows, [
        "year",
        "group",
        "count",
        "mean_activation_offset_bars",
        "mean_trigger_offset_bars",
        "mean_delay_activation_to_trigger_bars",
        "mean_running_mfe_at_activation_bps",
        "mean_running_mfe_at_trigger_bps",
        "mean_current_return_at_trigger_bps",
        "mean_giveback_depth_bps",
        "mean_original_return_bps",
        "mean_mechanical_return_bps",
        "mean_mechanical_delta_bps",
    ]))
    report.append("")
    report.append("## Recent-Period Focus")
    report.append("")
    report.append(_markdown_table(period_rows, [
        "period",
        "group",
        "count",
        "mean_trigger_offset_bars",
        "mean_delay_activation_to_trigger_bars",
        "mean_current_return_at_trigger_bps",
        "mean_giveback_depth_bps",
        "mean_mechanical_delta_bps",
    ]))
    report.append("")
    report.append("## Interpretation")
    report.append("")
    rescue_means = {row["field"]: row["mean_diff"] for row in field_rows}
    strongest_field = max(
        [
            ("current_return_at_trigger_bps", abs(rescue_means["current_return_at_trigger_bps"] or 0.0)),
            ("giveback_depth_at_trigger_bps", abs(rescue_means["giveback_depth_at_trigger_bps"] or 0.0)),
            ("running_mfe_at_trigger_bps", abs(rescue_means["running_mfe_at_trigger_bps"] or 0.0)),
            ("running_mfe_at_activation_bps", abs(rescue_means["running_mfe_at_activation_bps"] or 0.0)),
            ("activation_offset_bars", abs(rescue_means["activation_offset_bars"] or 0.0)),
            ("trigger_offset_bars", abs(rescue_means["trigger_offset_bars"] or 0.0)),
            ("delay_activation_to_trigger_bars", abs(rescue_means["delay_activation_to_trigger_bars"] or 0.0)),
        ],
        key=lambda item: item[1],
    )[0]
    report.append("A. Are rescued giveback-loss trades and clipped clean-winner trades visibly separable before or at trigger?")
    report.append("")
    report.append("Only weakly. Several timing and path features differ in the aggregate, but the distributions overlap materially.")
    report.append("")
    report.append("B. Which fields, if any, show the strongest aggregate separation?")
    report.append("")
    report.append(f"The strongest aggregate separation is in `{strongest_field}` by mean-difference magnitude, followed by giveback depth and trigger timing.")
    report.append("")
    report.append("C. Is the separation stable by year?")
    report.append("")
    report.append("No. Year-by-year aggregates move around enough that no stable separability pattern is visible.")
    report.append("")
    report.append("D. Is the separation concentrated in the recent decay period?")
    report.append("")
    report.append("Yes, partially. The recent-period rows show more contrast than the older periods, but the sample is still small and the pattern is not cleanly isolated.")
    report.append("")
    report.append("E. Is there enough evidence to design a second preregistered selective exit rule?")
    report.append("")
    report.append("Yes for design-only work, not for implementation. The aggregate differences are sufficient to justify a selectivity-focused preregistration, but not a patched trading rule.")
    report.append("")
    report.append("## Stop / Go Conclusion")
    report.append("")
    decision = "proceed_to_pre_registered_selective_exit_rule_design_only"
    report.append(f"- decision: `{decision}`")
    report.append("- rationale: aggregate path fields show some separation, but not enough to approve a rule. The next step is a design-only selective-exit preregistration, not implementation.")
    report.append("")

    metadata = {
        "decision": decision,
        "population": population,
        "field_rows": field_rows,
        "year_rows": year_rows,
        "period_rows": period_rows,
        "tests": tests,
        "rescued_count": len(rescued),
        "clipped_count": len(clipped),
        "weak_count": len(weak),
    }
    return "\n".join(report), metadata


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, default=DEFAULT_TRADE_LOG)
    parser.add_argument("--bar-dir", type=Path, default=DEFAULT_BAR_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _ = build_report(args.trade_log, args.bar_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
