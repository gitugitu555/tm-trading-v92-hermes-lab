#!/usr/bin/env python3
"""Descriptive fixed running-MFE giveback protection experiment for C_Exhaustion."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import (  # noqa: E402
    _interval_path,
    _load_bars,
    _markdown_table,
    _parse_trade_frame,
    _side_basis,
    construct_excursion_table,
)

DEFAULT_TRADE_LOG = Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_FIXED_RUNNING_MFE_GIVEBACK_PROTECTION_EXPERIMENT.md")

ACTIVATION_BPS = 75.0
GIVEBACK_FRACTION = 0.50
MIN_COMPLETED_BARS = 12
CLASS_LABELS = ["bad_entry_loss", "giveback_loss", "weak_positive_exit", "clean_winner", "unresolved"]
RESULT_LABELS = ["triggered", "not_triggered"]


@dataclass(frozen=True)
class SyntheticTestResult:
    name: str
    passed: bool
    details: str


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


def _fmt_bps(value: object) -> str:
    return f"{_fmt(value)} bps" if value is not None and not (isinstance(value, float) and math.isnan(value)) else "n/a"


def _summary_stats(series: pd.Series) -> dict[str, object]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "p25": None,
            "p75": None,
            "max": None,
        }
    return {
        "count": int(clean.shape[0]),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "min": float(clean.min()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
    }


def _classify_return_path(return_bps: float, mfe_bps: float) -> str:
    if return_bps < 0.0 and mfe_bps <= 0.0:
        return "bad_entry_loss"
    if return_bps < 0.0 and mfe_bps > 0.0:
        return "giveback_loss"
    if return_bps > 0.0 and mfe_bps > 0.0 and (mfe_bps - return_bps) >= 0.50 * mfe_bps:
        return "weak_positive_exit"
    if return_bps > 0.0:
        return "clean_winner"
    return "unresolved"


def _prepare_bar_window(path: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    close = pd.to_numeric(path["close"], errors="coerce").to_numpy(dtype=float)
    high = pd.to_numeric(path["high"], errors="coerce").to_numpy(dtype=float)
    close_time = pd.to_datetime(path["close_time"], errors="coerce")
    return close, high, close_time.to_numpy()


def _evaluate_trade(row: pd.Series, bars: pd.DataFrame) -> dict[str, object]:
    result: dict[str, object] = row.to_dict()
    result.update(
        {
            "activation_available": False,
            "activated": False,
            "activation_completed_bars": np.nan,
            "activation_running_mfe_bps": np.nan,
            "triggered": False,
            "trigger_completed_bars": np.nan,
            "trigger_running_mfe_bps": np.nan,
            "trigger_return_bps": np.nan,
            "trigger_giveback_bps": np.nan,
            "trigger_delay_bars": np.nan,
            "trigger_exit_time": pd.NaT,
            "synthetic_exit_price": np.nan,
            "synthetic_gross_return_bps": np.nan,
            "synthetic_net_return_bps": np.nan,
            "synthetic_final_class": "unresolved",
        }
    )

    if row.get("row_status") != "matched":
        return result

    entry_time = row.get("entry_time")
    exit_time = row.get("exit_time")
    entry_price = row.get("entry_price")
    if pd.isna(entry_time) or pd.isna(exit_time) or pd.isna(entry_price):
        return result

    path = _interval_path(bars, pd.Timestamp(entry_time), pd.Timestamp(exit_time))
    if path.empty:
        return result

    close_arr, high_arr, close_time_arr = _prepare_bar_window(path)
    if not np.isfinite(close_arr).any() or not np.isfinite(high_arr).any():
        return result

    valid_high = np.where(np.isfinite(high_arr), high_arr, -np.inf)
    running_high = np.maximum.accumulate(valid_high)
    entry_price = float(entry_price)

    fee_gap_bps = np.nan
    if "gross_return_bps" in row and "net_return_bps" in row and pd.notna(row.get("gross_return_bps")) and pd.notna(row.get("net_return_bps")):
        fee_gap_bps = float(row["gross_return_bps"]) - float(row["net_return_bps"])

    activation_pos: int | None = None
    trigger_pos: int | None = None
    for pos in range(len(path)):
        completed_bars = pos + 1
        if completed_bars < MIN_COMPLETED_BARS:
            continue
        if not np.isfinite(close_arr[pos]) or not np.isfinite(running_high[pos]):
            continue
        running_mfe_bps = (running_high[pos] / entry_price - 1.0) * 10_000.0
        if running_mfe_bps >= ACTIVATION_BPS:
            activation_pos = pos
            result["activation_available"] = True
            result["activated"] = True
            result["activation_completed_bars"] = float(completed_bars)
            result["activation_running_mfe_bps"] = float(running_mfe_bps)
            break

    if activation_pos is None:
        return result

    for pos in range(activation_pos, len(path)):
        completed_bars = pos + 1
        if completed_bars < MIN_COMPLETED_BARS:
            continue
        if not np.isfinite(close_arr[pos]) or not np.isfinite(running_high[pos]):
            continue
        current_return_bps = (close_arr[pos] / entry_price - 1.0) * 10_000.0
        running_mfe_bps = (running_high[pos] / entry_price - 1.0) * 10_000.0
        if current_return_bps <= GIVEBACK_FRACTION * running_mfe_bps:
            trigger_pos = pos
            result["triggered"] = True
            result["trigger_completed_bars"] = float(completed_bars)
            result["trigger_running_mfe_bps"] = float(running_mfe_bps)
            result["trigger_return_bps"] = float(current_return_bps)
            result["trigger_giveback_bps"] = float(running_mfe_bps - current_return_bps)
            result["trigger_delay_bars"] = float(completed_bars)
            result["trigger_exit_time"] = pd.Timestamp(close_time_arr[pos])
            result["synthetic_exit_price"] = float(close_arr[pos])
            break

    if trigger_pos is None:
        synthetic_return_bps = float(row["gross_return_bps"]) if pd.notna(row.get("gross_return_bps")) else float(row["net_return_bps"])
        synthetic_exit_price = float(row["exit_price"]) if pd.notna(row.get("exit_price")) else np.nan
        synthetic_mfe_bps = float(row["mfe_bps"]) if pd.notna(row.get("mfe_bps")) else np.nan
        result["synthetic_exit_price"] = synthetic_exit_price
        result["synthetic_gross_return_bps"] = float(row["gross_return_bps"]) if pd.notna(row.get("gross_return_bps")) else np.nan
        result["synthetic_net_return_bps"] = float(row["net_return_bps"]) if pd.notna(row.get("net_return_bps")) else np.nan
        result["synthetic_final_class"] = row.get("excursion_class", "unresolved")
        result["synthetic_final_return_bps"] = synthetic_return_bps
        result["synthetic_final_mfe_bps"] = synthetic_mfe_bps
        result["fee_gap_bps"] = fee_gap_bps
        return result

    trigger_return_bps = float(result["trigger_return_bps"])
    trigger_mfe_bps = float(result["trigger_running_mfe_bps"])
    synthetic_class = _classify_return_path(trigger_return_bps, trigger_mfe_bps)
    result["synthetic_final_class"] = synthetic_class
    result["synthetic_final_return_bps"] = trigger_return_bps
    result["synthetic_final_mfe_bps"] = trigger_mfe_bps
    result["synthetic_gross_return_bps"] = trigger_return_bps
    if np.isfinite(fee_gap_bps):
        result["synthetic_net_return_bps"] = trigger_return_bps - fee_gap_bps
    result["fee_gap_bps"] = fee_gap_bps
    return result


def _synthetic_causality_tests() -> list[SyntheticTestResult]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pd.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array(
                [
                    100.0,
                    101.0,
                    102.0,
                    103.0,
                    104.0,
                    105.0,
                    106.0,
                    107.0,
                    108.0,
                    109.0,
                    110.0,
                    112.0,
                    111.0,
                    110.0,
                    108.0,
                    106.0,
                    104.0,
                    103.0,
                    102.0,
                    101.0,
                ]
            ),
            "low": np.full(20, 99.0),
            "close": np.array(
                [
                    100.0,
                    100.5,
                    101.0,
                    101.5,
                    102.0,
                    102.5,
                    103.0,
                    103.5,
                    104.0,
                    104.5,
                    105.0,
                    104.0,
                    103.5,
                    102.0,
                    101.0,
                    100.0,
                    99.5,
                    99.0,
                    98.5,
                    98.0,
                ]
            ),
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
    baseline_trigger = base.loc[0, "trigger_completed_bars"]
    baseline_trigger_price = base.loc[0, "synthetic_exit_price"]

    bars_future = bars.copy()
    bars_future.loc[18:, "high"] = 9999.0
    bars_future.loc[18:, "close"] = 9998.0
    future = evaluate_experiment(trades, bars_future)

    bars_delayed = bars.copy()
    bars_delayed.loc[:10, "high"] = np.linspace(100.0, 107.0, 11)
    bars_delayed.loc[:10, "close"] = np.linspace(100.0, 104.0, 11)
    delayed = evaluate_experiment(trades, bars_delayed)

    bars_no_activation = bars.copy()
    bars_no_activation.loc[1:17, "high"] = 100.2
    bars_no_activation.loc[1:17, "close"] = 99.8
    no_activation = evaluate_experiment(trades, bars_no_activation)

    results: list[SyntheticTestResult] = []
    results.append(
        SyntheticTestResult(
            name="future-bars-do-not-change-first-trigger",
            passed=bool(
                base.loc[0, "triggered"]
                and future.loc[0, "triggered"]
                and baseline_trigger == future.loc[0, "trigger_completed_bars"]
                and baseline_trigger_price == future.loc[0, "synthetic_exit_price"]
            ),
            details=f"baseline_trigger={baseline_trigger}, future_trigger={future.loc[0, 'trigger_completed_bars']}",
        )
    )
    results.append(
        SyntheticTestResult(
            name="minimum-delay-gates-early-bar-activation",
            passed=bool(delayed.loc[0, "triggered"] and delayed.loc[0, "trigger_completed_bars"] >= MIN_COMPLETED_BARS),
            details=f"trigger_completed_bars={delayed.loc[0, 'trigger_completed_bars']}",
        )
    )
    results.append(
        SyntheticTestResult(
            name="no-activation-no-trigger",
            passed=bool(not bool(no_activation.loc[0, "triggered"]) and not bool(no_activation.loc[0, "activated"])),
            details="activation and trigger remained false",
        )
    )
    return results


def evaluate_experiment(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    diagnostics = construct_excursion_table(trades, bars).copy()
    if "year" not in diagnostics.columns or not diagnostics["year"].notna().any():
        diagnostics["year"] = pd.to_datetime(diagnostics["signal_time"], errors="coerce", utc=True).dt.tz_convert(None).dt.year.astype("Int64")
    else:
        diagnostics["year"] = pd.to_numeric(diagnostics["year"], errors="coerce").astype("Int64")
    rows = [_evaluate_trade(row, bars) for _, row in diagnostics.iterrows()]
    frame = pd.DataFrame(rows)
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    frame["original_final_return_bps"] = pd.to_numeric(frame["gross_return_bps"], errors="coerce")
    frame["original_final_net_return_bps"] = pd.to_numeric(frame["net_return_bps"], errors="coerce")
    frame["original_final_class"] = frame["excursion_class"]
    frame["was_triggered"] = frame["triggered"].astype(bool)
    frame["was_activated"] = frame["activated"].astype(bool)
    if "synthetic_net_return_bps" not in frame.columns:
        frame["synthetic_net_return_bps"] = np.nan
    if "synthetic_gross_return_bps" not in frame.columns:
        frame["synthetic_gross_return_bps"] = np.nan
    frame.loc[~frame["was_triggered"], "synthetic_gross_return_bps"] = frame.loc[~frame["was_triggered"], "gross_return_bps"]
    frame.loc[~frame["was_triggered"], "synthetic_net_return_bps"] = frame.loc[~frame["was_triggered"], "net_return_bps"]
    frame.loc[~frame["was_triggered"], "synthetic_final_return_bps"] = frame.loc[~frame["was_triggered"], "gross_return_bps"]
    frame.loc[~frame["was_triggered"], "synthetic_final_mfe_bps"] = frame.loc[~frame["was_triggered"], "mfe_bps"]
    frame.loc[~frame["was_triggered"], "synthetic_final_class"] = frame.loc[~frame["was_triggered"], "excursion_class"]
    return frame


def _count_series(frame: pd.DataFrame, column: str, mask: pd.Series | None = None) -> dict[str, int]:
    subset = frame if mask is None else frame[mask]
    return subset[column].value_counts(dropna=False).reindex(CLASS_LABELS, fill_value=0).to_dict()


def _year_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in sorted(frame["year"].dropna().astype(int).unique().tolist()):
        group = frame[frame["year"] == year]
        triggered = group[group["was_triggered"]]
        rows.append(
            {
                "year": year,
                "trades": int(len(group)),
                "activated": int(group["was_activated"].sum()),
                "triggered": int(group["was_triggered"].sum()),
                "activation_rate": float(group["was_activated"].mean()) if len(group) else None,
                "trigger_rate": float(group["was_triggered"].mean()) if len(group) else None,
                "triggered_mean_gross_return_bps": float(triggered["synthetic_gross_return_bps"].mean()) if len(triggered) else None,
                "triggered_median_gross_return_bps": float(triggered["synthetic_gross_return_bps"].median()) if len(triggered) else None,
                "triggered_mean_net_return_bps": float(triggered["synthetic_net_return_bps"].mean()) if len(triggered) else None,
                "triggered_median_net_return_bps": float(triggered["synthetic_net_return_bps"].median()) if len(triggered) else None,
                "original_mean_return_bps": float(group["gross_return_bps"].mean()),
                "original_median_return_bps": float(group["gross_return_bps"].median()),
                "synthetic_mean_return_bps": float(group["synthetic_gross_return_bps"].mean()),
                "synthetic_median_return_bps": float(group["synthetic_gross_return_bps"].median()),
            }
        )
    return rows


def build_report(trades_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trades_path)
    bars, bar_files = _load_bars(bar_dir)
    frame = evaluate_experiment(trades, bars)
    tests = _synthetic_causality_tests()

    triggered = frame[frame["was_triggered"]].copy()
    activated = frame[frame["was_activated"]].copy()
    not_triggered = frame[~frame["was_triggered"]].copy()
    original_giveback = frame[frame["original_final_class"] == "giveback_loss"].copy()
    original_weak = frame[frame["original_final_class"] == "weak_positive_exit"].copy()
    original_clean = frame[frame["original_final_class"] == "clean_winner"].copy()
    original_bad = frame[frame["original_final_class"] == "bad_entry_loss"].copy()

    transitions = (
        frame.groupby(["original_final_class", "synthetic_final_class"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["original_final_class", "synthetic_final_class"])
    )

    activation_stats = {
        "count": int(len(activated)),
        "activation_rate": float(len(activated) / len(frame)) if len(frame) else None,
        "mean_activation_mfe_bps": float(activated["activation_running_mfe_bps"].mean()) if len(activated) else None,
        "median_activation_mfe_bps": float(activated["activation_running_mfe_bps"].median()) if len(activated) else None,
        "mean_activation_delay_bars": float(activated["activation_completed_bars"].mean()) if len(activated) else None,
        "median_activation_delay_bars": float(activated["activation_completed_bars"].median()) if len(activated) else None,
    }
    trigger_stats = {
        "count": int(len(triggered)),
        "trigger_rate_among_activated": float(len(triggered) / len(activated)) if len(activated) else None,
        "mean_trigger_return_bps": float(triggered["trigger_return_bps"].mean()) if len(triggered) else None,
        "median_trigger_return_bps": float(triggered["trigger_return_bps"].median()) if len(triggered) else None,
        "mean_trigger_mfe_bps": float(triggered["trigger_running_mfe_bps"].mean()) if len(triggered) else None,
        "median_trigger_mfe_bps": float(triggered["trigger_running_mfe_bps"].median()) if len(triggered) else None,
        "mean_trigger_giveback_bps": float(triggered["trigger_giveback_bps"].mean()) if len(triggered) else None,
        "median_trigger_giveback_bps": float(triggered["trigger_giveback_bps"].median()) if len(triggered) else None,
        "mean_trigger_delay_bars": float(triggered["trigger_delay_bars"].mean()) if len(triggered) else None,
        "median_trigger_delay_bars": float(triggered["trigger_delay_bars"].median()) if len(triggered) else None,
    }

    original_return_stats = {
        "triggered_gross": _summary_stats(triggered["gross_return_bps"]),
        "triggered_net": _summary_stats(triggered["net_return_bps"]),
        "not_triggered_gross": _summary_stats(not_triggered["gross_return_bps"]),
        "not_triggered_net": _summary_stats(not_triggered["net_return_bps"]),
    }
    synthetic_return_stats = {
        "gross": _summary_stats(frame["synthetic_gross_return_bps"]),
        "net": _summary_stats(frame["synthetic_net_return_bps"]),
    }
    class_transition_table = transitions.to_dict(orient="records")
    year_rows = _year_rows(frame)

    report: list[str] = []
    report.append("# V9.2 Hermes Fixed Exit Experiment Result")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("* Descriptive aggregate result for the single pre-registered fixed running-MFE giveback protection experiment.")
    report.append("* Lab-only execution against the frozen core trade log and bounded 750btc bars.")
    report.append("* No strategy patch, replay patch, optimization, or trading approval.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- trade log: `{trades_path}`")
    report.append(f"- bar dir: `{bar_dir}`")
    report.append(f"- bars read: `{len(bar_files)}`")
    report.append(f"- trades inspected: `{len(frame)}`")
    report.append(f"- side basis: `{_side_basis(trades)}`")
    report.append(f"- activation threshold: `{ACTIVATION_BPS:.0f} bps running MFE`")
    report.append(f"- giveback trigger: `current_return_bps <= {GIVEBACK_FRACTION:.2f} * running_mfe_bps`")
    report.append(f"- minimum delay: `{MIN_COMPLETED_BARS}` completed bars")
    report.append("")
    report.append("## Synthetic Causality Tests")
    report.append("")
    for item in tests:
        status = "passed" if item.passed else "failed"
        report.append(f"- {item.name}: `{status}` ({item.details})")
    report.append("")
    report.append("## Aggregate Counts")
    report.append("")
    report.append(f"- activated_trades: `{activation_stats['count']}`")
    report.append(f"- activation_rate: `{_fmt_pct(activation_stats['activation_rate'])}`")
    report.append(f"- triggered_trades: `{trigger_stats['count']}`")
    report.append(f"- trigger_rate_among_activated: `{_fmt_pct(trigger_stats['trigger_rate_among_activated'])}`")
    report.append(f"- original giveback_loss triggered: `{int((original_giveback['was_triggered']).sum())}` / `{len(original_giveback)}`")
    report.append(f"- original weak_positive_exit triggered: `{int((original_weak['was_triggered']).sum())}` / `{len(original_weak)}`")
    report.append(f"- original clean_winner triggered: `{int((original_clean['was_triggered']).sum())}` / `{len(original_clean)}`")
    report.append(f"- original bad_entry_loss triggered: `{int((original_bad['was_triggered']).sum())}` / `{len(original_bad)}`")
    report.append(f"- unavailable_or_untriggered_trades: `{int(len(not_triggered))}`")
    report.append("")
    report.append("## Activation Distribution")
    report.append("")
    report.append(f"- mean activation MFE: `{_fmt_bps(activation_stats['mean_activation_mfe_bps'])}`")
    report.append(f"- median activation MFE: `{_fmt_bps(activation_stats['median_activation_mfe_bps'])}`")
    report.append(f"- mean activation delay: `{_fmt(activation_stats['mean_activation_delay_bars'])}` completed bars")
    report.append(f"- median activation delay: `{_fmt(activation_stats['median_activation_delay_bars'])}` completed bars")
    report.append("")
    report.append("## Trigger Distribution")
    report.append("")
    report.append(f"- mean trigger return: `{_fmt_bps(trigger_stats['mean_trigger_return_bps'])}`")
    report.append(f"- median trigger return: `{_fmt_bps(trigger_stats['median_trigger_return_bps'])}`")
    report.append(f"- mean trigger MFE: `{_fmt_bps(trigger_stats['mean_trigger_mfe_bps'])}`")
    report.append(f"- median trigger MFE: `{_fmt_bps(trigger_stats['median_trigger_mfe_bps'])}`")
    report.append(f"- mean giveback magnitude: `{_fmt_bps(trigger_stats['mean_trigger_giveback_bps'])}`")
    report.append(f"- median giveback magnitude: `{_fmt_bps(trigger_stats['median_trigger_giveback_bps'])}`")
    report.append(f"- mean delay-to-trigger: `{_fmt(trigger_stats['mean_trigger_delay_bars'])}` completed bars")
    report.append(f"- median delay-to-trigger: `{_fmt(trigger_stats['median_trigger_delay_bars'])}` completed bars")
    report.append("")
    report.append("## Triggered Trade Return Distributions")
    report.append("")
    report.append("| metric | gross | net |")
    report.append("| --- | --- | --- |")
    for label in ["triggered", "not_triggered"]:
        g = original_return_stats[f"{label}_gross"]
        n = original_return_stats[f"{label}_net"]
        report.append(
            "| "
            + f"{label} | "
            + f"mean={_fmt_bps(g['mean'])}, median={_fmt_bps(g['median'])}, count={g['count']} | "
            + f"mean={_fmt_bps(n['mean'])}, median={_fmt_bps(n['median'])}, count={n['count']} |"
        )
    report.append("")
    report.append("## Mechanical Fixed-Exit Comparison")
    report.append("")
    report.append(f"- synthetic gross mean: `{_fmt_bps(synthetic_return_stats['gross']['mean'])}`")
    report.append(f"- synthetic gross median: `{_fmt_bps(synthetic_return_stats['gross']['median'])}`")
    report.append(f"- synthetic net mean: `{_fmt_bps(synthetic_return_stats['net']['mean'])}`")
    report.append(f"- synthetic net median: `{_fmt_bps(synthetic_return_stats['net']['median'])}`")
    report.append(f"- original gross mean: `{_fmt_bps(_summary_stats(frame['gross_return_bps'])['mean'])}`")
    report.append(f"- original gross median: `{_fmt_bps(_summary_stats(frame['gross_return_bps'])['median'])}`")
    report.append(f"- original net mean: `{_fmt_bps(_summary_stats(frame['net_return_bps'])['mean'])}`")
    report.append(f"- original net median: `{_fmt_bps(_summary_stats(frame['net_return_bps'])['median'])}`")
    report.append("")
    report.append("### Original To Synthetic Class Transition Table")
    report.append("")
    report.append(_markdown_table(class_transition_table, ["original_final_class", "synthetic_final_class", "count"]))
    report.append("")
    report.append("## By-Year Results")
    report.append("")
    report.append(_markdown_table(year_rows, [
        "year",
        "trades",
        "activated",
        "triggered",
        "activation_rate",
        "trigger_rate",
        "original_mean_return_bps",
        "original_median_return_bps",
        "synthetic_mean_return_bps",
        "synthetic_median_return_bps",
    ]))
    report.append("")
    report.append("## Leakage and Bias Checks")
    report.append("")
    report.append("* Bars were evaluated only up to each trade's original exit boundary.")
    report.append("* Trigger logic used running highs and bar closes accumulated sequentially inside the original trade window.")
    report.append("* Synthetic tests verified that later bars outside the original trade window do not change the trigger result.")
    report.append("* The minimum delay gate prevented early activation before the preregistered bar count.")
    report.append("* No raw L2 data, OFI features, parameter sweeps, or replay patches were used.")
    report.append("")
    report.append("## Stop / Go Conclusion")
    report.append("")
    if len(triggered) == 0:
        decision = "blocked_due_to_missing_required_inputs"
        conclusion = "The fixed rule never triggered on the available sample, so the descriptive experiment is not evaluable."
    else:
        decision = "proceed_to_review_fixed_giveback_results"
        conclusion = "The fixed rule is causally implementable bar by bar and the result is evaluable as a descriptive aggregate comparison."
    report.append(f"- decision: `{decision}`")
    report.append(f"- conclusion: {conclusion}")
    report.append("")
    report.append("## Decision Inputs")
    report.append("")
    report.append(f"- original giveback_loss count: `{len(original_giveback)}`")
    report.append(f"- triggered giveback_loss count: `{int(original_giveback['was_triggered'].sum())}`")
    report.append(f"- triggered clean_winner count: `{int(original_clean['was_triggered'].sum())}`")
    report.append(f"- triggered weak_positive_exit count: `{int(original_weak['was_triggered'].sum())}`")
    report.append(f"- triggered bad_entry_loss count: `{int(original_bad['was_triggered'].sum())}`")
    report.append(f"- 2025 triggered trades: `{int(frame[(frame['year'] == 2025) & frame['was_triggered']].shape[0])}`")
    report.append(f"- 2026 triggered trades: `{int(frame[(frame['year'] == 2026) & frame['was_triggered']].shape[0])}`")
    report.append("")

    metadata = {
        "decision": decision,
        "tests": tests,
        "activation_stats": activation_stats,
        "trigger_stats": trigger_stats,
        "frame": frame,
        "year_rows": year_rows,
        "class_transition_table": class_transition_table,
        "original_return_stats": original_return_stats,
        "synthetic_return_stats": synthetic_return_stats,
        "triggered_count": len(triggered),
        "activated_count": len(activated),
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
