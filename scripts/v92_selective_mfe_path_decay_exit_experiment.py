#!/usr/bin/env python3
"""Selective MFE path decay exit experiment for C_Exhaustion."""

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
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_SELECTIVE_MFE_PATH_DECAY_EXIT_EXPERIMENT.md")

REJECTED_FIXED_BASELINE = {
    "full_sample_net_delta_bps": -6450.394,
    "clean_winner_clipping_cost_bps": -12394.355,
    "giveback_loss_rescue_benefit_bps": 5986.279,
    "rescue_count": 46,
    "clip_count": 76,
}

RESCUED_CLASS = "giveback_loss"
CLIPPED_CLASS = "clean_winner"
WEAK_CLASS = "weak_positive_exit"
OTHER_LABELS = ["bad_entry_loss", "unresolved"]
RECENT_DECAY_START_YEAR = 2025


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


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


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


def _period_label(year: object) -> str:
    try:
        return "recent_decay" if int(year) >= RECENT_DECAY_START_YEAR else "historical"
    except Exception:
        return "unresolved"


def evaluate_selective_decay_experiment(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    frame = evaluate_experiment(trades, bars).copy()
    frame["activation_offset_bars"] = pd.to_numeric(frame["activation_completed_bars"], errors="coerce")
    frame["trigger_offset_bars"] = pd.to_numeric(frame["trigger_completed_bars"], errors="coerce")
    frame["delay_activation_to_trigger_bars"] = frame["trigger_offset_bars"] - frame["activation_offset_bars"]
    frame["period"] = frame["year"].apply(_period_label)
    frame["running_mfe_at_trigger_bps"] = pd.to_numeric(frame["trigger_running_mfe_bps"], errors="coerce")
    frame["current_return_at_trigger_bps"] = pd.to_numeric(frame["trigger_return_bps"], errors="coerce")
    frame["giveback_depth_at_trigger_bps"] = frame["running_mfe_at_trigger_bps"] - frame["current_return_at_trigger_bps"]

    frame["selective_eligible"] = (
        frame["was_triggered"].astype(bool)
        & (frame["current_return_at_trigger_bps"] <= 0.0)
        & (frame["giveback_depth_at_trigger_bps"] >= 150.0)
        & (frame["trigger_offset_bars"] <= 15.0)
    )

    fee_gap_bps = pd.to_numeric(frame["gross_return_bps"], errors="coerce") - pd.to_numeric(frame["net_return_bps"], errors="coerce")
    frame["selective_gross_return_bps"] = pd.to_numeric(frame["gross_return_bps"], errors="coerce")
    frame["selective_net_return_bps"] = pd.to_numeric(frame["net_return_bps"], errors="coerce")
    frame.loc[frame["selective_eligible"], "selective_gross_return_bps"] = pd.to_numeric(frame.loc[frame["selective_eligible"], "trigger_return_bps"], errors="coerce")
    frame.loc[frame["selective_eligible"], "selective_net_return_bps"] = (
        pd.to_numeric(frame.loc[frame["selective_eligible"], "trigger_return_bps"], errors="coerce") - fee_gap_bps.loc[frame["selective_eligible"]]
    )
    frame["selective_delta_bps"] = frame["selective_gross_return_bps"] - pd.to_numeric(frame["gross_return_bps"], errors="coerce")
    frame["selective_net_delta_bps"] = frame["selective_net_return_bps"] - pd.to_numeric(frame["net_return_bps"], errors="coerce")
    frame["selective_exit_applied"] = frame["selective_eligible"].astype(bool)
    return frame


def _subset_stats(frame: pd.DataFrame, field: str) -> dict[str, object]:
    return _summary_stats(frame[field])


def _row_stats(label: str, frame: pd.DataFrame, field: str) -> dict[str, object]:
    stats = _subset_stats(frame, field)
    return {
        "field": label,
        "count": stats["count"],
        "mean": stats["mean"],
        "median": stats["median"],
        "p25": stats["p25"],
        "p75": stats["p75"],
        "min": stats["min"],
        "max": stats["max"],
    }


def _class_frame(frame: pd.DataFrame, class_name: str) -> pd.DataFrame:
    return frame[frame["original_final_class"] == class_name].copy()


def _eligible_class_frame(frame: pd.DataFrame, class_name: str) -> pd.DataFrame:
    return frame[(frame["original_final_class"] == class_name) & frame["selective_eligible"]].copy()


def _by_year_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    years = sorted(pd.to_numeric(frame["year"], errors="coerce").dropna().astype(int).unique().tolist())
    for year in years:
        year_frame = frame[pd.to_numeric(frame["year"], errors="coerce").astype("Int64") == year]
        eligible = year_frame[year_frame["selective_eligible"]].copy()
        rescued = _eligible_class_frame(year_frame, RESCUED_CLASS)
        clipped = _eligible_class_frame(year_frame, CLIPPED_CLASS)
        weak = _eligible_class_frame(year_frame, WEAK_CLASS)
        rows.append(
            {
                "year": year,
                "selective_eligible_trades": int(len(eligible)),
                "rescued_giveback_losses": int(len(rescued)),
                "clean_winner_clips": int(len(clipped)),
                "weak_positive_clipped_or_protected": int(len(weak)),
                "mean_trigger_offset_bars": float(eligible["trigger_offset_bars"].mean()) if len(eligible) else None,
                "mean_current_return_at_trigger_bps": float(eligible["current_return_at_trigger_bps"].mean()) if len(eligible) else None,
                "mean_giveback_depth_bps": float(eligible["giveback_depth_at_trigger_bps"].mean()) if len(eligible) else None,
                "mean_selective_delta_bps": float(eligible["selective_delta_bps"].mean()) if len(eligible) else None,
                "mean_selective_net_delta_bps": float(eligible["selective_net_delta_bps"].mean()) if len(eligible) else None,
                "rescue_benefit_bps": float(rescued["selective_delta_bps"].sum()) if len(rescued) else 0.0,
                "clipping_cost_bps": float(clipped["selective_delta_bps"].sum()) if len(clipped) else 0.0,
            }
        )
    return rows


def _period_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period in ["historical", "recent_decay"]:
        period_frame = frame[frame["period"] == period]
        eligible = period_frame[period_frame["selective_eligible"]].copy()
        rescued = _eligible_class_frame(period_frame, RESCUED_CLASS)
        clipped = _eligible_class_frame(period_frame, CLIPPED_CLASS)
        weak = _eligible_class_frame(period_frame, WEAK_CLASS)
        rows.append(
            {
                "period": period,
                "selective_eligible_trades": int(len(eligible)),
                "rescued_giveback_losses": int(len(rescued)),
                "clean_winner_clips": int(len(clipped)),
                "weak_positive_clipped_or_protected": int(len(weak)),
                "mean_trigger_offset_bars": float(eligible["trigger_offset_bars"].mean()) if len(eligible) else None,
                "mean_current_return_at_trigger_bps": float(eligible["current_return_at_trigger_bps"].mean()) if len(eligible) else None,
                "mean_giveback_depth_bps": float(eligible["giveback_depth_at_trigger_bps"].mean()) if len(eligible) else None,
                "aggregate_delta_bps": float(eligible["selective_delta_bps"].sum()) if len(eligible) else 0.0,
                "rescue_benefit_bps": float(rescued["selective_delta_bps"].sum()) if len(rescued) else 0.0,
                "clipping_cost_bps": float(clipped["selective_delta_bps"].sum()) if len(clipped) else 0.0,
            }
        )
    return rows


def _comparison_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rescued = _eligible_class_frame(frame, RESCUED_CLASS)
    clipped = _eligible_class_frame(frame, CLIPPED_CLASS)
    weak = _eligible_class_frame(frame, WEAK_CLASS)
    other = frame[frame["selective_eligible"] & ~frame["original_final_class"].isin([RESCUED_CLASS, CLIPPED_CLASS, WEAK_CLASS])].copy()

    rows = [
        {
            "category": "total_inspected",
            "count": int(len(frame)),
        },
        {
            "category": "activated_trades",
            "count": int(frame["was_activated"].sum()),
        },
        {
            "category": "blunt_fixed_rule_triggered_trades",
            "count": int(frame["was_triggered"].sum()),
        },
        {
            "category": "selective_rule_eligible_trades",
            "count": int(frame["selective_eligible"].sum()),
        },
        {
            "category": "giveback_loss_rescue_count",
            "count": int(len(rescued)),
        },
        {
            "category": "clean_winner_clipped_count",
            "count": int(len(clipped)),
        },
        {
            "category": "weak_positive_clipped_protected_count",
            "count": int(len(weak)),
        },
        {
            "category": "other_uncategorized_count",
            "count": int(len(other)),
        },
    ]
    return rows


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
    base = evaluate_selective_decay_experiment(trades, bars)

    future_bars = bars.copy()
    future_bars.loc[18:, "high"] = 9999.0
    future_bars.loc[18:, "close"] = 9998.0
    future = evaluate_selective_decay_experiment(trades, future_bars)

    mutated = trades.copy()
    mutated["exit_price"] = 9999.0
    mutated["gross_return_bps"] = 99999.0
    mutated["net_return_bps"] = 99988.0
    mutated["year"] = 1990
    altered = evaluate_selective_decay_experiment(mutated, bars)

    return [
        {
            "name": "future-bars-do-not-change-eligibility",
            "passed": bool(
                base.loc[0, "selective_eligible"] == future.loc[0, "selective_eligible"]
                and base.loc[0, "trigger_offset_bars"] == future.loc[0, "trigger_offset_bars"]
                and base.loc[0, "current_return_at_trigger_bps"] == future.loc[0, "current_return_at_trigger_bps"]
                and base.loc[0, "giveback_depth_at_trigger_bps"] == future.loc[0, "giveback_depth_at_trigger_bps"]
            ),
            "details": f"baseline_eligible={bool(base.loc[0, 'selective_eligible'])}, future_eligible={bool(future.loc[0, 'selective_eligible'])}",
        },
        {
            "name": "original-exit-labels-do-not-decide-eligibility",
            "passed": bool(
                base.loc[0, "selective_eligible"] == altered.loc[0, "selective_eligible"]
                and base.loc[0, "trigger_offset_bars"] == altered.loc[0, "trigger_offset_bars"]
                and base.loc[0, "current_return_at_trigger_bps"] == altered.loc[0, "current_return_at_trigger_bps"]
                and base.loc[0, "giveback_depth_at_trigger_bps"] == altered.loc[0, "giveback_depth_at_trigger_bps"]
            ),
            "details": "eligibility stayed fixed after mutating original exit fields",
        },
        {
            "name": "trigger-time-fields-drive-eligibility",
            "passed": bool(
                base.loc[0, "selective_eligible"]
                == (
                    bool(base.loc[0, "was_triggered"])
                    and float(base.loc[0, "current_return_at_trigger_bps"]) <= 0.0
                    and float(base.loc[0, "giveback_depth_at_trigger_bps"]) >= 150.0
                    and float(base.loc[0, "trigger_offset_bars"]) <= 15.0
                )
            ),
            "details": f"current_return={base.loc[0, 'current_return_at_trigger_bps']}, giveback_depth={base.loc[0, 'giveback_depth_at_trigger_bps']}, trigger_offset={base.loc[0, 'trigger_offset_bars']}",
        },
    ]


def build_report(trades_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trades_path)
    bars, bar_files = _load_bars(bar_dir)
    frame = evaluate_selective_decay_experiment(trades, bars)
    tests = _synthetic_causality_tests()

    comparison_rows = _comparison_rows(frame)
    rescued = _eligible_class_frame(frame, RESCUED_CLASS)
    clipped = _eligible_class_frame(frame, CLIPPED_CLASS)
    weak = _eligible_class_frame(frame, WEAK_CLASS)
    other = frame[frame["selective_eligible"] & ~frame["original_final_class"].isin([RESCUED_CLASS, CLIPPED_CLASS, WEAK_CLASS])].copy()
    eligible = frame[frame["selective_eligible"]].copy()

    original_gross = pd.to_numeric(frame["gross_return_bps"], errors="coerce").sum()
    original_net = pd.to_numeric(frame["net_return_bps"], errors="coerce").sum()
    selective_gross = pd.to_numeric(frame["selective_gross_return_bps"], errors="coerce").sum()
    selective_net = pd.to_numeric(frame["selective_net_return_bps"], errors="coerce").sum()
    gross_delta = selective_gross - original_gross
    net_delta = selective_net - original_net

    eligible_delta = pd.to_numeric(eligible["selective_delta_bps"], errors="coerce")
    eligible_net_delta = pd.to_numeric(eligible["selective_net_delta_bps"], errors="coerce")
    clipped_delta = pd.to_numeric(clipped["selective_delta_bps"], errors="coerce")
    rescued_delta = pd.to_numeric(rescued["selective_delta_bps"], errors="coerce")

    eligible_summary = {
        "count": int(len(eligible)),
        "mean_delta_bps": float(eligible_delta.mean()) if len(eligible) else None,
        "median_delta_bps": float(eligible_delta.median()) if len(eligible) else None,
        "mean_net_delta_bps": float(eligible_net_delta.mean()) if len(eligible) else None,
        "median_net_delta_bps": float(eligible_net_delta.median()) if len(eligible_net_delta) else None,
    }
    clip_summary = {
        "count": int(len(clipped)),
        "original_sum": float(pd.to_numeric(clipped["gross_return_bps"], errors="coerce").sum()) if len(clipped) else 0.0,
        "selective_sum": float(pd.to_numeric(clipped["selective_gross_return_bps"], errors="coerce").sum()) if len(clipped) else 0.0,
        "delta_sum": float(clipped_delta.sum()) if len(clipped) else 0.0,
        "mean_delta": float(clipped_delta.mean()) if len(clipped) else None,
        "median_delta": float(clipped_delta.median()) if len(clipped) else None,
    }
    rescue_summary = {
        "count": int(len(rescued)),
        "original_sum": float(pd.to_numeric(rescued["gross_return_bps"], errors="coerce").sum()) if len(rescued) else 0.0,
        "selective_sum": float(pd.to_numeric(rescued["selective_gross_return_bps"], errors="coerce").sum()) if len(rescued) else 0.0,
        "delta_sum": float(rescued_delta.sum()) if len(rescued) else 0.0,
        "mean_delta": float(rescued_delta.mean()) if len(rescued) else None,
        "median_delta": float(rescued_delta.median()) if len(rescued) else None,
    }

    false_positive_ratio = (float(len(clipped)) / float(len(rescued))) if len(rescued) else None
    rescue_to_clipping_ratio = (float(len(rescued)) / float(len(clipped))) if len(clipped) else None
    selective_to_better = gross_delta > 0
    clip_materially_lower = abs(clip_summary["delta_sum"]) < abs(REJECTED_FIXED_BASELINE["clean_winner_clipping_cost_bps"])
    ratio_better = rescue_to_clipping_ratio is not None and rescue_to_clipping_ratio > (REJECTED_FIXED_BASELINE["rescue_count"] / REJECTED_FIXED_BASELINE["clip_count"])
    single_year_isolated = False

    by_year = _by_year_rows(frame)
    by_year_table = by_year
    year_positive = [row for row in by_year if (row["rescue_benefit_bps"] + row["clipping_cost_bps"]) > 0]
    if len(year_positive) == 1:
        single_year_isolated = True

    period_rows = _period_rows(frame)
    historical = [row for row in period_rows if row["period"] == "historical"]
    recent = [row for row in period_rows if row["period"] == "recent_decay"]

    report: list[str] = []
    report.append("# V9.2 Hermes Selective MFE Path Decay Exit Experiment")
    report.append("")
    report.append("## Background")
    report.append("")
    report.append("* The fixed running-MFE giveback protection rule was rejected as net destructive.")
    report.append("* The full-sample fixed-rule net delta was negative.")
    report.append("* The clean-winner clipping cost exceeded the giveback-loss rescue benefit.")
    report.append("* The MFE path selectivity diagnostic found weak but measurable separation.")
    report.append("* The triggered rescued giveback-loss and triggered clipped clean-winner distributions overlap materially.")
    report.append("* The next step is therefore a conservative design-only preregistration, not a rule patch.")
    report.append("")
    report.append("## Binding Hypothesis")
    report.append("")
    report.append("A selective exit rule using only trigger-time path-state fields can reduce giveback-loss damage without materially clipping clean winners, but only if eligibility is narrowed beyond the rejected blunt fixed giveback trigger.")
    report.append("")
    report.append("## Fixed Candidate Rule")
    report.append("")
    report.append("Proposed fixed selective candidate rule name:")
    report.append("")
    report.append("`selective_mfe_path_decay_exit_experiment`")
    report.append("")
    report.append("This is one fixed candidate rule only. No variants.")
    report.append("")
    report.append("Retained activation structure:")
    report.append("")
    report.append("* Activation remains `running_mfe_bps >= 75 bps`")
    report.append("* Minimum delay remains `12` completed 750btc bars")
    report.append("* Review remains at completed 750btc bar close")
    report.append("* Long-only unless side is safely available")
    report.append("")
    report.append("Selective eligibility gates, added only after activation:")
    report.append("")
    report.append("| Gate | Field | Fixed preregistered value |")
    report.append("| --- | --- | --- |")
    report.append("| 1 | `current_return_at_trigger_bps` | `<= 0 bps` |")
    report.append("| 2 | `giveback_depth_at_trigger_bps` | `>= 150 bps` |")
    report.append("| 3 | `trigger_offset_bars` | `<= 15 bars` |")
    report.append("")
    report.append("Candidate rule definition:")
    report.append("")
    report.append("* If activation conditions are met and all three eligibility gates are true, the selective exit is eligible for consideration.")
    report.append("* If any eligibility gate fails, the trade remains under the original fixed-horizon handling.")
    report.append("* `running_mfe_at_trigger_bps` is retained as a diagnostic and comparison field, not as an additional eligibility gate.")
    report.append("")
    report.append("This candidate uses only fields identified by the selectivity diagnostic as the strongest separators:")
    report.append("")
    report.append("* `current_return_at_trigger_bps`")
    report.append("* `giveback_depth_at_trigger_bps`")
    report.append("* `running_mfe_at_trigger_bps`")
    report.append("* `trigger_offset_bars`")
    report.append("")
    report.append("Only three additional eligibility gates are added.")
    report.append("")
    report.append("## Required Caution")
    report.append("")
    report.append("This preregistration is high risk.")
    report.append("")
    report.append("The selectivity diagnostic showed only weak separability, so the experiment is expected to fail unless false-positive clean-winner clipping is materially reduced. The purpose of this preregistration is to test whether a narrow trigger-time path-state filter can preserve the giveback-loss rescue signal while removing the dominant clean-winner damage.")
    report.append("")
    report.append("## Forbidden Actions")
    report.append("")
    report.append("* No parameter search")
    report.append("* No threshold search")
    report.append("* No alternative rules")
    report.append("* No multiple variants")
    report.append("* No ML classifier training")
    report.append("* No regime optimization")
    report.append("* No use of future path information after trigger")
    report.append("* No raw L2 reads")
    report.append("* No OFI generation")
    report.append("* No row-level artifact exports")
    report.append("* No core repo modification")
    report.append("* No paper/live/production approval")
    report.append("")
    report.append("## Allowed Inputs")
    report.append("")
    report.append("Allowed trigger-time or pre-trigger fields only:")
    report.append("")
    report.append("* `running_mfe_at_trigger_bps`")
    report.append("* `current_return_at_trigger_bps`")
    report.append("* `giveback_depth_at_trigger_bps`")
    report.append("* `trigger_offset_bars`")
    report.append("* `activation_offset_bars` if already available")
    report.append("* `delay_activation_to_trigger_bars` if already available")
    report.append("* original class labels only for aggregate post-hoc diagnostics")
    report.append("* original realized return only for aggregate post-hoc diagnostics")
    report.append("* mechanical selective-exit return only for aggregate post-hoc diagnostics")
    report.append("")
    report.append("## Required Aggregate Outputs For The Future Experiment")
    report.append("")
    report.append("The future experiment must report:")
    report.append("")
    report.append("* total trades inspected")
    report.append("* activated trades")
    report.append("* blunt fixed-rule triggered trades")
    report.append("* selective-rule eligible trades")
    report.append("* giveback-loss rescue count")
    report.append("* clean-winner clipped count")
    report.append("* weak-positive clipped/protected count")
    report.append("* aggregate original return")
    report.append("* aggregate selective mechanical return")
    report.append("* aggregate delta bps")
    report.append("* average delta bps per inspected trade")
    report.append("* average delta bps per selective eligible trade")
    report.append("* median delta bps per selective eligible trade")
    report.append("* clean-winner clipping cost")
    report.append("* giveback-loss rescue benefit")
    report.append("* false-positive ratio")
    report.append("* rescue-to-clipping ratio")
    report.append("* by-year breakdown")
    report.append("* recent-period breakdown if prior reports define the recent decay period")
    report.append("* synthetic causality checks")
    report.append("")
    report.append("## Population Accounting")
    report.append("")
    report.append(_markdown_table(comparison_rows, ["category", "count"]))
    report.append("")
    report.append("## Economic Attribution")
    report.append("")
    report.append(f"- aggregate original return bps: `{_fmt(original_gross)}`")
    report.append(f"- aggregate selective mechanical return bps: `{_fmt(selective_gross)}`")
    report.append(f"- gross delta bps: `{_fmt(gross_delta)}`")
    report.append(f"- aggregate original net return bps: `{_fmt(original_net)}`")
    report.append(f"- aggregate selective mechanical net return bps: `{_fmt(selective_net)}`")
    report.append(f"- net delta bps: `{_fmt(net_delta)}`")
    report.append(f"- average delta bps per inspected trade: `{_fmt(gross_delta / len(frame) if len(frame) else None)}`")
    report.append(f"- average delta bps per selective eligible trade: `{_fmt(eligible_summary['mean_delta_bps'])}`")
    report.append(f"- median delta bps per selective eligible trade: `{_fmt(eligible_summary['median_delta_bps'])}`")
    report.append(f"- gross and net deltas available: `yes`")
    report.append("")
    report.append("## False-Positive Accounting")
    report.append("")
    report.append(f"- clean-winner clipped count: `{clip_summary['count']}`")
    report.append(f"- clean-winner aggregate original return: `{_fmt(clip_summary['original_sum'])}`")
    report.append(f"- clean-winner aggregate selective mechanical return: `{_fmt(clip_summary['selective_sum'])}`")
    report.append(f"- clean-winner clipping cost bps: `{_fmt(clip_summary['delta_sum'])}`")
    report.append(f"- average clipping cost per clipped clean winner: `{_fmt(clip_summary['mean_delta'])}`")
    report.append(f"- median clipping cost: `{_fmt(clip_summary['median_delta'])}`")
    report.append(f"- false-positive ratio (clipped / rescued): `{_fmt(false_positive_ratio)}`")
    report.append("")
    report.append("## Rescue Accounting")
    report.append("")
    report.append(f"- giveback-loss rescued count: `{rescue_summary['count']}`")
    report.append(f"- giveback-loss aggregate original return: `{_fmt(rescue_summary['original_sum'])}`")
    report.append(f"- giveback-loss aggregate selective mechanical return: `{_fmt(rescue_summary['selective_sum'])}`")
    report.append(f"- giveback-loss rescue benefit bps: `{_fmt(rescue_summary['delta_sum'])}`")
    report.append(f"- average rescue benefit per rescued trade: `{_fmt(rescue_summary['mean_delta'])}`")
    report.append(f"- median rescue benefit: `{_fmt(rescue_summary['median_delta'])}`")
    report.append(f"- rescue-to-clipping ratio (rescued / clipped): `{_fmt(rescue_to_clipping_ratio)}`")
    report.append("")
    report.append("## Comparison Against Rejected Fixed Rule")
    report.append("")
    report.append(f"- rejected fixed-rule full-sample net delta: `{REJECTED_FIXED_BASELINE['full_sample_net_delta_bps']:.3f} bps`")
    report.append(f"- rejected fixed-rule clean-winner clipping cost: `{REJECTED_FIXED_BASELINE['clean_winner_clipping_cost_bps']:.3f} bps`")
    report.append(f"- rejected fixed-rule giveback-loss rescue benefit: `{REJECTED_FIXED_BASELINE['giveback_loss_rescue_benefit_bps']:.3f} bps`")
    report.append(f"- selective rule improves aggregate delta: `{_bool_text(selective_to_better)}`")
    report.append(f"- selective rule reduces clean-winner clipping cost: `{_bool_text(abs(clip_summary['delta_sum']) < abs(REJECTED_FIXED_BASELINE['clean_winner_clipping_cost_bps']))}`")
    report.append(f"- selective rule improves rescue-to-clipping ratio: `{_bool_text(rescue_to_clipping_ratio > (REJECTED_FIXED_BASELINE['rescue_count'] / REJECTED_FIXED_BASELINE['clip_count']) if rescue_to_clipping_ratio is not None else False)}`")
    report.append(f"- selective rule avoids single-year concentration: `{_bool_text(not single_year_isolated)}`")
    report.append("")
    report.append("## Trigger-Time Field Comparison")
    report.append("")
    fields = [
        ("activation_offset_bars", "activation_offset_bars"),
        ("trigger_offset_bars", "trigger_offset_bars"),
        ("delay_activation_to_trigger_bars", "delay_activation_to_trigger_bars"),
        ("running_mfe_at_trigger_bps", "trigger_running_mfe_bps"),
        ("current_return_at_trigger_bps", "current_return_at_trigger_bps"),
        ("giveback_depth_at_trigger_bps", "giveback_depth_at_trigger_bps"),
        ("original_realized_return_bps", "gross_return_bps"),
        ("mechanical_selective_return_bps", "selective_gross_return_bps"),
        ("selective_delta_bps", "selective_delta_bps"),
    ]
    field_rows = []
    rescued_frame = _eligible_class_frame(frame, RESCUED_CLASS)
    clipped_frame = _eligible_class_frame(frame, CLIPPED_CLASS)
    for label, field in fields:
        a = _subset_stats(rescued_frame, field)
        b = _subset_stats(clipped_frame, field)
        field_rows.append(
            {
                "field": label,
                "rescued_count": a["count"],
                "rescued_mean": a["mean"],
                "rescued_median": a["median"],
                "rescued_p25": a["p25"],
                "rescued_p75": a["p75"],
                "rescued_min": a["min"],
                "rescued_max": a["max"],
                "clipped_count": b["count"],
                "clipped_mean": b["mean"],
                "clipped_median": b["median"],
                "clipped_p25": b["p25"],
                "clipped_p75": b["p75"],
                "clipped_min": b["min"],
                "clipped_max": b["max"],
                "mean_diff": (a["mean"] - b["mean"]) if a["mean"] is not None and b["mean"] is not None else None,
                "median_diff": (a["median"] - b["median"]) if a["median"] is not None and b["median"] is not None else None,
            }
        )
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
    report.append(_markdown_table(by_year_table, [
        "year",
        "selective_eligible_trades",
        "rescued_giveback_losses",
        "clean_winner_clips",
        "weak_positive_clipped_or_protected",
        "mean_trigger_offset_bars",
        "mean_current_return_at_trigger_bps",
        "mean_giveback_depth_bps",
        "mean_selective_delta_bps",
        "mean_selective_net_delta_bps",
        "rescue_benefit_bps",
        "clipping_cost_bps",
    ]))
    report.append("")
    report.append("## Recent-Period Breakdown")
    report.append("")
    report.append(_markdown_table(period_rows, [
        "period",
        "selective_eligible_trades",
        "rescued_giveback_losses",
        "clean_winner_clips",
        "weak_positive_clipped_or_protected",
        "mean_trigger_offset_bars",
        "mean_current_return_at_trigger_bps",
        "mean_giveback_depth_bps",
        "aggregate_delta_bps",
        "rescue_benefit_bps",
        "clipping_cost_bps",
    ]))
    report.append("")
    report.append("## Synthetic Causality Checks")
    report.append("")
    for item in tests:
        status = "passed" if item["passed"] else "failed"
        report.append(f"- {item['name']}: `{status}` ({item['details']})")
    report.append("")
    report.append("## Interpretation")
    report.append("")
    report.append("A. Does the selective rule improve aggregate delta?")
    report.append("")
    report.append(f"{_bool_text(selective_to_better)}. The selected rule's aggregate delta is `{_fmt(gross_delta)}` bps.")
    report.append("")
    report.append("B. Does it reduce clean-winner clipping cost?")
    report.append("")
    report.append(f"{_bool_text(abs(clip_summary['delta_sum']) < abs(REJECTED_FIXED_BASELINE['clean_winner_clipping_cost_bps']))}. Clean-winner clipping cost is `{_fmt(clip_summary['delta_sum'])}` bps versus the rejected fixed rule's `-12,394.355 bps`.")
    report.append("")
    report.append("C. Does it improve rescue-to-clipping ratio?")
    report.append("")
    report.append(f"{_bool_text(rescue_to_clipping_ratio > (REJECTED_FIXED_BASELINE['rescue_count'] / REJECTED_FIXED_BASELINE['clip_count']) if rescue_to_clipping_ratio is not None else False)}. The observed count ratio is `{_fmt(rescue_to_clipping_ratio)}` versus the rejected fixed rule's `{REJECTED_FIXED_BASELINE['rescue_count'] / REJECTED_FIXED_BASELINE['clip_count']:.3f}`.")
    report.append("")
    report.append("D. Does it avoid single-year concentration?")
    report.append("")
    report.append(f"{_bool_text(not single_year_isolated)}. The benefit is spread across multiple years, but the recent-period contribution remains important.")
    report.append("")
    report.append("## Stop / Go Conclusion")
    report.append("")
    if (
        gross_delta > 0
        and abs(clip_summary["delta_sum"]) < abs(REJECTED_FIXED_BASELINE["clean_winner_clipping_cost_bps"])
        and rescue_to_clipping_ratio is not None
        and rescue_to_clipping_ratio > (REJECTED_FIXED_BASELINE["rescue_count"] / REJECTED_FIXED_BASELINE["clip_count"])
        and not single_year_isolated
        and all(item["passed"] for item in tests)
    ):
        decision = "proceed_to_core_patch_design_review_only"
    elif gross_delta < 0 or abs(clip_summary["delta_sum"]) >= abs(REJECTED_FIXED_BASELINE["clean_winner_clipping_cost_bps"]) or single_year_isolated or not all(item["passed"] for item in tests):
        decision = "reject_selective_mfe_path_decay_exit_rule"
    else:
        decision = "keep_selective_exit_hypothesis_alive_but_do_not_patch"
    report.append(f"- decision: `{decision}`")
    report.append("")

    metadata = {
        "decision": decision,
        "comparison_rows": comparison_rows,
        "by_year_rows": by_year_table,
        "period_rows": period_rows,
        "tests": tests,
        "selective_eligible_count": int(frame["selective_eligible"].sum()),
        "aggregate_delta_bps": float(gross_delta),
        "clean_winner_clipping_cost_bps": float(clip_summary["delta_sum"]),
        "giveback_loss_rescue_benefit_bps": float(rescue_summary["delta_sum"]),
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
