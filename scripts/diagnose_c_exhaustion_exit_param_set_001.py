#!/usr/bin/env python3
"""Diagnostic overlay for the fixed C_Exhaustion exit parameter set 001."""

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
    INTERVAL_CONVENTION,
    _interval_path,
    _load_bars,
    _markdown_table,
    _parse_trade_frame,
    _side_basis,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_EXIT_PARAM_SET_001_DIAGNOSTIC.md")
FIXED_PARAMETER_SET = "C_EXHAUSTION_EXIT_PARAM_SET_001_LIVE_PEAK_RETENTION_GUARD"
ACTIVATION_THRESHOLD_BPS = 50.0
RETENTION_FRACTION = 0.50
COST_LADDER_BPS = [1, 2, 3, 5, 8, 12]
SPLITS = ["full sample", "2020-2023", "2024-2026", "2025", "2026"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{float(value) * 100.0:.3f}%"


def _trade_years(trades: pd.DataFrame) -> pd.Series:
    if "year" in trades.columns and trades["year"].notna().any():
        return pd.to_numeric(trades["year"], errors="coerce").astype("Int64")
    return pd.to_datetime(trades["signal_time"], errors="coerce", utc=True).dt.tz_convert(None).dt.year.astype("Int64")


def _final_return_basis(trades: pd.DataFrame) -> str:
    if "gross_return_bps" in trades.columns and trades["gross_return_bps"].notna().any():
        return "gross_return_bps"
    return "computed_from_entry_exit_price"


def _gross_return_bps_from_prices(entry_price: float, exit_price: float) -> float:
    return (float(exit_price) / float(entry_price) - 1.0) * 10_000.0


def _safe_profit_factor(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    wins = returns[returns > 0.0]
    losses = returns[returns < 0.0]
    if len(losses) == 0:
        return float("inf") if len(wins) else 0.0
    loss_sum = float(losses.sum())
    if abs(loss_sum) <= 0.0:
        return float("inf") if len(wins) else 0.0
    return float(wins.sum() / abs(loss_sum)) if len(wins) else 0.0


def _safe_payoff_ratio(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    wins = returns[returns > 0.0]
    losses = returns[returns < 0.0]
    if len(wins) == 0 and len(losses) == 0:
        return 0.0
    if len(losses) == 0:
        return float("inf")
    if len(wins) == 0:
        return 0.0
    avg_loss = abs(float(losses.mean()))
    if avg_loss <= 0.0:
        return float("inf")
    return float(wins.mean() / avg_loss)


def _max_drawdown_pct(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    growth = (1.0 + returns.astype(float) / 10_000.0).cumprod()
    running_max = growth.cummax()
    drawdown_pct = ((growth - running_max) / running_max) * 100.0
    return float(abs(drawdown_pct.min())) if not drawdown_pct.empty else 0.0


def _summary_from_returns(returns: pd.Series) -> dict[str, object]:
    if returns.empty:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "gross_expectancy_bps": 0.0,
            "profit_factor": 0.0,
            "average_win_bps": 0.0,
            "average_loss_bps": 0.0,
            "payoff_ratio": 0.0,
            "max_drawdown_pct": 0.0,
        }
    wins = returns[returns > 0.0]
    losses = returns[returns < 0.0]
    return {
        "trade_count": int(len(returns)),
        "win_rate": float((returns > 0.0).mean()),
        "gross_expectancy_bps": float(returns.mean()),
        "profit_factor": _safe_profit_factor(returns),
        "average_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "average_loss_bps": float(losses.mean()) if len(losses) else 0.0,
        "payoff_ratio": _safe_payoff_ratio(returns),
        "max_drawdown_pct": _max_drawdown_pct(returns),
    }


def _split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    years = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    if split == "full sample":
        return frame.copy()
    if split == "2020-2023":
        return frame[years.between(2020, 2023)].copy()
    if split == "2024-2026":
        return frame[years.between(2024, 2026)].copy()
    if split == "2025":
        return frame[years == 2025].copy()
    if split == "2026":
        return frame[years == 2026].copy()
    raise ValueError(f"Unknown split: {split}")


def _net_expectancy_by_cost(returns: pd.Series, cost_bps: float) -> float:
    if returns.empty:
        return 0.0
    return float((returns.astype(float) - float(cost_bps)).mean())


def _year_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    years = pd.to_numeric(frame["year"], errors="coerce").dropna().astype(int).tolist()
    for year in sorted(set(years)):
        group = frame[pd.to_numeric(frame["year"], errors="coerce").astype("Int64") == year].copy()
        original = _summary_from_returns(group["original_return_bps"].astype(float))
        diagnostic = _summary_from_returns(group["diagnostic_return_bps"].astype(float))
        rows.append(
            {
                "year": year,
                "trade_count": int(len(group)),
                "activation_count": int(group["activation_triggered"].sum()),
                "protective_exit_count": int(group["protective_exit_triggered"].sum()),
                "unchanged_exit_count": int((~group["protective_exit_triggered"]).sum()),
                "original_gross_expectancy_bps": original["gross_expectancy_bps"],
                "diagnostic_gross_expectancy_bps": diagnostic["gross_expectancy_bps"],
                "gross_expectancy_delta_bps": float(diagnostic["gross_expectancy_bps"] - original["gross_expectancy_bps"]),
                "original_net_expectancy_bps_12bps": _net_expectancy_by_cost(group["original_return_bps"], 12.0),
                "diagnostic_net_expectancy_bps_12bps": _net_expectancy_by_cost(group["diagnostic_return_bps"], 12.0),
                "original_profit_factor": original["profit_factor"],
                "diagnostic_profit_factor": diagnostic["profit_factor"],
                "original_payoff_ratio": original["payoff_ratio"],
                "diagnostic_payoff_ratio": diagnostic["payoff_ratio"],
                "activation_rate": float(group["activation_triggered"].mean()) if len(group) else 0.0,
                "protective_exit_rate": float(group["protective_exit_triggered"].mean()) if len(group) else 0.0,
            }
        )
    return rows


def _cost_ladder_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for split in SPLITS:
        group = _split_frame(frame, split)
        row: dict[str, object] = {"split": split}
        for cost_bps in COST_LADDER_BPS:
            row[f"diagnostic_net_expectancy_bps_{cost_bps}bps"] = _net_expectancy_by_cost(group["diagnostic_return_bps"], float(cost_bps))
            row[f"original_net_expectancy_bps_{cost_bps}bps"] = _net_expectancy_by_cost(group["original_return_bps"], float(cost_bps))
        rows.append(row)
    return rows


def _evaluate_trades(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    trades = trades.copy()
    trades = trades.sort_values(
        ["signal_time", "entry_time", "exit_time", "signal_index", "entry_index", "exit_index"],
        kind="mergesort",
    ).reset_index(drop=True)
    if "year" not in trades.columns or not trades["year"].notna().any():
        trades["year"] = _trade_years(trades)
    else:
        trades["year"] = pd.to_numeric(trades["year"], errors="coerce").astype("Int64")

    evaluated: list[dict[str, object]] = []

    for row in trades.itertuples(index=False):
        entry_time = getattr(row, "entry_time", pd.NaT)
        exit_time = getattr(row, "exit_time", pd.NaT)
        entry_price = getattr(row, "entry_price", np.nan)
        exit_price = getattr(row, "exit_price", np.nan)
        gross_return_bps = getattr(row, "gross_return_bps", np.nan) if "gross_return_bps" in trades.columns else np.nan
        net_return_bps = getattr(row, "net_return_bps", np.nan)
        year = getattr(row, "year", pd.NA)

        original_return = float(gross_return_bps) if pd.notna(gross_return_bps) else _gross_return_bps_from_prices(entry_price, exit_price)
        record: dict[str, object] = {
            "signal_index": getattr(row, "signal_index", pd.NA),
            "entry_index": getattr(row, "entry_index", pd.NA),
            "exit_index": getattr(row, "exit_index", pd.NA),
            "signal_time": getattr(row, "signal_time", pd.NaT),
            "entry_time": entry_time,
            "exit_time": exit_time,
            "year": year,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_return_bps": gross_return_bps,
            "net_return_bps": net_return_bps,
            "original_return_bps": original_return,
            "diagnostic_return_bps": original_return,
            "live_peak_return_bps": np.nan,
            "activation_triggered": False,
            "protective_exit_triggered": False,
            "protective_exit_bar_index": pd.NA,
            "diagnostic_exit_basis": "original_exit",
            "source_status": "unmatched",
            "row_note": "interval_match_missing",
        }

        required_present = all(
            pd.notna(value)
            for value in [entry_time, exit_time, entry_price, exit_price]
        )
        if not required_present:
            record["source_status"] = "unavailable"
            record["row_note"] = "missing_required_trade_fields"
            evaluated.append(record)
            continue

        path = _interval_path(bars, pd.Timestamp(entry_time), pd.Timestamp(exit_time))
        if path.empty:
            record["source_status"] = "unmatched"
            record["row_note"] = "no_bars_in_half_open_interval"
            evaluated.append(record)
            continue

        guard = _simulate_live_peak_retention_guard(entry_price=float(entry_price), path=path)
        if guard["source_status"] != "matched":
            record.update(guard)
            record["original_return_bps"] = original_return
            record["diagnostic_return_bps"] = original_return
            evaluated.append(record)
            continue

        record.update(guard)
        record["original_return_bps"] = original_return
        record["diagnostic_return_bps"] = (
            float(guard["diagnostic_return_bps"]) if guard["protective_exit_triggered"] else original_return
        )
        evaluated.append(record)

    return pd.DataFrame(evaluated)


def _simulate_live_peak_retention_guard(*, entry_price: float, path: pd.DataFrame) -> dict[str, object]:
    """Simulate the fixed live peak-retention guard on a single matched trade path."""
    high_values = pd.to_numeric(path["high"], errors="coerce").to_numpy(dtype=float)
    close_values = pd.to_numeric(path["close"], errors="coerce").to_numpy(dtype=float)
    finite_mask = np.isfinite(high_values) & np.isfinite(close_values)
    if not finite_mask.any():
        return {
            "source_status": "unavailable",
            "row_note": "missing_finite_high_or_close",
            "live_peak_return_bps": np.nan,
            "activation_triggered": False,
            "protective_exit_triggered": False,
            "protective_exit_bar_index": pd.NA,
            "diagnostic_return_bps": np.nan,
            "diagnostic_exit_basis": "unavailable",
        }

    activated = False
    protective_exit = False
    live_peak_return_bps = -np.inf
    diagnostic_return_bps = np.nan
    protective_exit_bar_index: int | None = None

    for idx, (high, close) in enumerate(zip(high_values, close_values, strict=False)):
        if not (np.isfinite(high) and np.isfinite(close)):
            continue
        bar_high_return_bps = (float(high) / float(entry_price) - 1.0) * 10_000.0
        bar_close_return_bps = (float(close) / float(entry_price) - 1.0) * 10_000.0
        live_peak_return_bps = max(live_peak_return_bps, bar_high_return_bps)
        if not activated and live_peak_return_bps >= ACTIVATION_THRESHOLD_BPS:
            activated = True
        if activated and bar_close_return_bps <= RETENTION_FRACTION * live_peak_return_bps:
            protective_exit = True
            diagnostic_return_bps = bar_close_return_bps
            protective_exit_bar_index = idx
            break

    if not protective_exit:
        diagnostic_return_bps = np.nan

    return {
        "source_status": "matched",
        "row_note": "matched",
        "live_peak_return_bps": float(live_peak_return_bps) if np.isfinite(live_peak_return_bps) else np.nan,
        "activation_triggered": bool(activated),
        "protective_exit_triggered": bool(protective_exit),
        "protective_exit_bar_index": protective_exit_bar_index if protective_exit_bar_index is not None else pd.NA,
        "diagnostic_return_bps": diagnostic_return_bps,
        "diagnostic_exit_basis": "protective_close" if protective_exit else "original_exit",
    }


def _split_metrics(frame: pd.DataFrame, split: str) -> dict[str, object]:
    group = _split_frame(frame, split).copy()
    original = _summary_from_returns(group["original_return_bps"].astype(float))
    diagnostic = _summary_from_returns(group["diagnostic_return_bps"].astype(float))
    summary: dict[str, object] = {
        "split": split,
        "trade_count": int(len(group)),
        "activation_count": int(group["activation_triggered"].sum()),
        "protective_exit_count": int(group["protective_exit_triggered"].sum()),
        "unchanged_exit_count": int((~group["protective_exit_triggered"]).sum()),
        "unavailable_count": int((group["source_status"] == "unavailable").sum()),
        "unmatched_count": int((group["source_status"] == "unmatched").sum()),
        "original_win_rate": original["win_rate"],
        "diagnostic_win_rate": diagnostic["win_rate"],
        "original_gross_expectancy_bps": original["gross_expectancy_bps"],
        "diagnostic_gross_expectancy_bps": diagnostic["gross_expectancy_bps"],
        "gross_expectancy_delta_bps": float(diagnostic["gross_expectancy_bps"] - original["gross_expectancy_bps"]),
        "original_profit_factor": original["profit_factor"],
        "diagnostic_profit_factor": diagnostic["profit_factor"],
        "original_average_win_bps": original["average_win_bps"],
        "diagnostic_average_win_bps": diagnostic["average_win_bps"],
        "original_average_loss_bps": original["average_loss_bps"],
        "diagnostic_average_loss_bps": diagnostic["average_loss_bps"],
        "original_payoff_ratio": original["payoff_ratio"],
        "diagnostic_payoff_ratio": diagnostic["payoff_ratio"],
        "original_max_drawdown_pct": original["max_drawdown_pct"],
        "diagnostic_max_drawdown_pct": diagnostic["max_drawdown_pct"],
        "activation_rate": float(group["activation_triggered"].mean()) if len(group) else 0.0,
        "protective_exit_rate": float(group["protective_exit_triggered"].mean()) if len(group) else 0.0,
        "original_net_expectancy_bps_12bps": _net_expectancy_by_cost(group["original_return_bps"], 12.0),
        "diagnostic_net_expectancy_bps_12bps": _net_expectancy_by_cost(group["diagnostic_return_bps"], 12.0),
        "diagnostic_net_expectancy_bps": {
            f"{cost}bps": _net_expectancy_by_cost(group["diagnostic_return_bps"], float(cost))
            for cost in COST_LADDER_BPS
        },
        "original_net_expectancy_bps": {
            f"{cost}bps": _net_expectancy_by_cost(group["original_return_bps"], float(cost))
            for cost in COST_LADDER_BPS
        },
    }
    return summary


def build_diagnostics(*, trade_log: Path, bar_dir: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    trades = _parse_trade_frame(trade_log)
    bars, bar_files = _load_bars(bar_dir)
    evaluated = _evaluate_trades(trades, bars)

    total = int(len(evaluated))
    matched_rows = int((evaluated["source_status"] == "matched").sum())
    unavailable_rows = int((evaluated["source_status"] == "unavailable").sum())
    unmatched_rows = int((evaluated["source_status"] == "unmatched").sum())
    unresolved_rows = unavailable_rows + unmatched_rows
    original_returns = evaluated["original_return_bps"].astype(float)
    diagnostic_returns = evaluated["diagnostic_return_bps"].astype(float)

    summary: dict[str, object] = {
        "trade_rows_loaded": int(len(trades)),
        "bar_rows_loaded": int(len(bars)),
        "bar_files_read": int(len(bar_files)),
        "rows_with_matched_bars": matched_rows,
        "rows_without_matched_bars": total - matched_rows,
        "unresolved_rows": unresolved_rows,
        "unavailable_count": unavailable_rows,
        "unmatched_count": unmatched_rows,
        "year_min": int(pd.to_numeric(evaluated["year"], errors="coerce").dropna().min()) if evaluated["year"].notna().any() else None,
        "year_max": int(pd.to_numeric(evaluated["year"], errors="coerce").dropna().max()) if evaluated["year"].notna().any() else None,
        "side_basis": _side_basis(trades),
        "final_return_basis": _final_return_basis(trades),
        "trades_inspected": total,
        "activation_count": int(evaluated["activation_triggered"].sum()),
        "protective_exit_count": int(evaluated["protective_exit_triggered"].sum()),
        "activation_rate": float(evaluated["activation_triggered"].mean()) if total else 0.0,
        "protective_exit_rate": float(evaluated["protective_exit_triggered"].mean()) if total else 0.0,
        "unchanged_exit_count": int((~evaluated["protective_exit_triggered"]).sum()),
        "original_summary": _summary_from_returns(original_returns),
        "diagnostic_summary": _summary_from_returns(diagnostic_returns),
        "year_rows": _year_rows(evaluated),
        "cost_ladder_rows": _cost_ladder_rows(evaluated),
        "full_sample": _split_metrics(evaluated, "full sample"),
        "split_2020_2023": _split_metrics(evaluated, "2020-2023"),
        "split_2024_2026": _split_metrics(evaluated, "2024-2026"),
        "split_2025": _split_metrics(evaluated, "2025"),
        "split_2026": _split_metrics(evaluated, "2026"),
    }

    return evaluated, summary


def _interpretation_lines(summary: dict[str, object]) -> list[str]:
    full = summary["full_sample"]
    original = summary["original_summary"]
    diagnostic = summary["diagnostic_summary"]
    year_rows = summary["year_rows"]
    y2025 = summary["split_2025"]
    y2026 = summary["split_2026"]

    lines: list[str] = []
    gross_delta = float(diagnostic["gross_expectancy_bps"] - original["gross_expectancy_bps"])
    net12_delta = float(full["diagnostic_net_expectancy_bps_12bps"] - full["original_net_expectancy_bps_12bps"])
    if gross_delta > 0.0:
        lines.append("- The fixed rule improved gross expectancy on the full sample.")
    else:
        lines.append("- The fixed rule did not improve gross expectancy on the full sample.")
    if net12_delta > 0.0:
        lines.append("- The fixed rule improved net expectancy after 12 bps stress cost on the full sample.")
    else:
        lines.append("- The fixed rule did not improve net expectancy after 12 bps stress cost on the full sample.")
    if float(diagnostic["win_rate"]) > float(original["win_rate"]) and float(diagnostic["payoff_ratio"]) < float(original["payoff_ratio"]):
        lines.append("- The rule improved win rate while damaging payoff ratio, so the gain is not purely quality-preserving.")
    else:
        lines.append("- The rule did not show a pure win-rate-only improvement pattern.")
    year_deltas = [float(row["gross_expectancy_delta_bps"]) for row in year_rows]
    positive_years = sum(delta > 0.0 for delta in year_deltas)
    if positive_years <= 1:
        lines.append("- The improvement is concentrated in one year or less, so calendar-year stability remains weak.")
    else:
        lines.append("- The improvement is not concentrated in a single year only.")
    if float(y2025["diagnostic_net_expectancy_bps_12bps"]) <= 0.0 and float(y2026["diagnostic_net_expectancy_bps_12bps"]) <= 0.0:
        lines.append("- 2025 and 2026 remain structurally poor under the fixed rule after 12 bps stress.")
    else:
        lines.append("- At least one of 2025 or 2026 is not structurally poor under the fixed rule after 12 bps stress.")
    if int(summary["activation_count"]) >= max(10, int(0.1 * summary["trades_inspected"])):
        lines.append("- Activation count is large enough to be meaningful.")
    else:
        lines.append("- Activation count is too small to be strongly meaningful.")
    if int(summary["rows_without_matched_bars"]) == 0 and int(summary["unresolved_rows"]) == 0:
        lines.append("- No trades were dropped or left unresolved.")
    else:
        lines.append("- Some trades were unavailable or unmatched and were counted explicitly.")
    lines.append("- The diagnostic remains diagnostic-only and does not approve live execution.")
    lines.append("- Paper/live is still blocked.")
    return lines


def _yearly_stability_table(summary: dict[str, object]) -> str:
    return _markdown_table(
        summary["year_rows"],
        [
            "year",
            "trade_count",
            "activation_count",
            "protective_exit_count",
            "unchanged_exit_count",
            "original_gross_expectancy_bps",
            "diagnostic_gross_expectancy_bps",
            "gross_expectancy_delta_bps",
            "original_net_expectancy_bps_12bps",
            "diagnostic_net_expectancy_bps_12bps",
            "original_profit_factor",
            "diagnostic_profit_factor",
            "original_payoff_ratio",
            "diagnostic_payoff_ratio",
            "activation_rate",
            "protective_exit_rate",
        ],
    )


def _performance_table(summary: dict[str, object]) -> str:
    rows = [summary["full_sample"], summary["split_2020_2023"], summary["split_2024_2026"], summary["split_2025"], summary["split_2026"]]
    return _markdown_table(
        rows,
        [
            "split",
            "trade_count",
            "activation_count",
            "protective_exit_count",
            "unchanged_exit_count",
            "unavailable_count",
            "unmatched_count",
            "original_win_rate",
            "diagnostic_win_rate",
            "original_gross_expectancy_bps",
            "diagnostic_gross_expectancy_bps",
            "gross_expectancy_delta_bps",
            "original_profit_factor",
            "diagnostic_profit_factor",
            "original_average_win_bps",
            "diagnostic_average_win_bps",
            "original_average_loss_bps",
            "diagnostic_average_loss_bps",
            "original_payoff_ratio",
            "diagnostic_payoff_ratio",
            "original_max_drawdown_pct",
            "diagnostic_max_drawdown_pct",
        ],
    )


def _cost_ladder_table(summary: dict[str, object]) -> str:
    rows = []
    for row in summary["cost_ladder_rows"]:
        rows.append(
            {
                "split": row["split"],
                "original_net_expectancy_bps_12bps": row["original_net_expectancy_bps_12bps"],
                "diagnostic_net_expectancy_bps_1bps": row["diagnostic_net_expectancy_bps_1bps"],
                "diagnostic_net_expectancy_bps_2bps": row["diagnostic_net_expectancy_bps_2bps"],
                "diagnostic_net_expectancy_bps_3bps": row["diagnostic_net_expectancy_bps_3bps"],
                "diagnostic_net_expectancy_bps_5bps": row["diagnostic_net_expectancy_bps_5bps"],
                "diagnostic_net_expectancy_bps_8bps": row["diagnostic_net_expectancy_bps_8bps"],
                "diagnostic_net_expectancy_bps_12bps": row["diagnostic_net_expectancy_bps_12bps"],
            }
        )
    return _markdown_table(
        rows,
        [
            "split",
            "original_net_expectancy_bps_12bps",
            "diagnostic_net_expectancy_bps_1bps",
            "diagnostic_net_expectancy_bps_2bps",
            "diagnostic_net_expectancy_bps_3bps",
            "diagnostic_net_expectancy_bps_5bps",
            "diagnostic_net_expectancy_bps_8bps",
            "diagnostic_net_expectancy_bps_12bps",
        ],
    )


def build_report(*, trade_log: Path, bar_dir: Path, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    diagnostics, summary = build_diagnostics(trade_log=trade_log, bar_dir=bar_dir)

    lines: list[str] = []
    lines.append("# V9.2 C_Exhaustion Exit Param Set 001 Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is a diagnostic overlay only for the fixed C_Exhaustion exit parameter set 001. It applies the preregistered live peak-retention / giveback guard in memory, compares it against the existing post-regime-fix anchor, and writes only a Markdown summary.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- trade_log path: `{trade_log}`")
    lines.append(f"- bar_dir path: `{bar_dir}`")
    lines.append("- real_trade_log_read: `true`")
    lines.append("- real_bar_data_read: `true`")
    lines.append("- raw_l2_data_read: `false`")
    lines.append("- ofi_artifacts_read: `false`")
    lines.append("- row_level_artifacts_written: `false`")
    lines.append("- feature_table_artifacts_written: `false`")
    lines.append("- model_artifacts_written: `false`")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No strategy/replay logic changed.")
    lines.append("- No backtest engine changed.")
    lines.append("- No entry logic changed.")
    lines.append("- No model trained.")
    lines.append("- No thresholds tuned.")
    lines.append("- No alternative thresholds tested.")
    lines.append("- No alternative windows tested.")
    lines.append("- No row-level artifacts written.")
    lines.append("- No feature-table artifacts written.")
    lines.append("- No model artifacts written.")
    lines.append("- No OFI artifacts written.")
    lines.append("- Same-bar close diagnostic basis only.")
    lines.append("- Not paper/live executable.")
    lines.append("- Alpha remains blocked.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("- OFI reconstruction remains blocked unless separately approved elsewhere.")
    lines.append("")
    lines.append("## Fixed Parameter Set Applied")
    lines.append("")
    lines.append(f"- experiment name: `{FIXED_PARAMETER_SET}`")
    lines.append("- symbol: BTCUSDT")
    lines.append("- bar size: 750 BTC bars only")
    lines.append(f"- direction basis: `{summary['side_basis']}`")
    lines.append("- entry logic: unchanged from the existing post-regime-fix C Exhaustion replay anchor")
    lines.append("- baseline comparison: existing post-regime-fix C Exhaustion anchor")
    lines.append("- horizon: preserve existing 36-bar horizon")
    lines.append("- original stop/target: preserve existing baseline stop/target geometry")
    lines.append("- decision timing: completed bar close only")
    lines.append(f"- timestamp convention: `{INTERVAL_CONVENTION}`")
    lines.append("- entry price basis: existing trade-log `entry_price`")
    lines.append("- live peak return basis: completed-bar high relative to `entry_price`")
    lines.append("- decision return basis: completed-bar close relative to `entry_price`")
    lines.append(f"- activation condition: activate protection only after `live_peak_return_bps >= +{ACTIVATION_THRESHOLD_BPS:.1f} bps`")
    lines.append(f"- protective exit condition: after activation, diagnostic protective exit occurs on a completed bar close if `close_return_bps <= {RETENTION_FRACTION:.2f} * live_peak_return_bps`")
    lines.append("- protective exit execution basis: same completed-bar close diagnostic basis only")
    lines.append(f"- cost ladder: {', '.join(str(cost) for cost in COST_LADDER_BPS)} bps")
    lines.append("")
    lines.append("## Source Construction Summary")
    lines.append("")
    lines.append(f"- trade_rows_loaded: `{summary['trade_rows_loaded']}`")
    lines.append(f"- bar_rows_loaded: `{summary['bar_rows_loaded']}`")
    lines.append(f"- bar_files_read: `{summary['bar_files_read']}`")
    lines.append(f"- rows_with_matched_bars: `{summary['rows_with_matched_bars']}`")
    lines.append(f"- unresolved_rows: `{summary['unresolved_rows']}`")
    lines.append(f"- year_min: `{summary['year_min']}`")
    lines.append(f"- year_max: `{summary['year_max']}`")
    lines.append(f"- side_basis: `{summary['side_basis']}`")
    lines.append(f"- final_return_basis: `{summary['final_return_basis']}`")
    lines.append("")
    lines.append("## Rule Activation Summary")
    lines.append("")
    lines.append(f"- trades_inspected: `{summary['trades_inspected']}`")
    lines.append(f"- activation_count: `{summary['activation_count']}`")
    lines.append(f"- activation_rate: `{_fmt_pct(summary['activation_rate'])}`")
    lines.append(f"- protective_exit_count: `{summary['protective_exit_count']}`")
    lines.append(f"- protective_exit_rate: `{_fmt_pct(summary['protective_exit_rate'])}`")
    lines.append(f"- unchanged_exit_count: `{summary['unchanged_exit_count']}`")
    lines.append(f"- unavailable_count: `{summary['unavailable_count']}`")
    lines.append(f"- unmatched_count: `{summary['unmatched_count']}`")
    lines.append("")
    lines.append("## Performance Summary")
    lines.append("")
    lines.append(_performance_table(summary))
    lines.append("")
    lines.append("## Cost Stress Ladder")
    lines.append("")
    lines.append("The table below reports the original-anchor 12 bps stress benchmark alongside the diagnostic net expectancy at each fixed cost level.")
    lines.append("")
    lines.append(_cost_ladder_table(summary))
    lines.append("")
    lines.append("## Calendar-Year Stability")
    lines.append("")
    lines.append(_yearly_stability_table(summary))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.extend(_interpretation_lines(summary))
    lines.append("")
    lines.append("## What This Proves")
    lines.append("")
    if int(summary["rows_with_matched_bars"]) == int(summary["trade_rows_loaded"]) and int(summary["unresolved_rows"]) == 0:
        lines.append("- The fixed live-peak retention guard can be evaluated safely on the existing matched trade intervals and bounded bars.")
        lines.append("- The rule can be applied without changing strategy logic, replay logic, or entry logic.")
        lines.append("- The report can distinguish original-anchor exits from same-bar diagnostic protective exits.")
        lines.append("- Calendar-year behavior can be reviewed descriptively.")
    else:
        lines.append("- The diagnostic is still bounded, but some rows were unavailable or unmatched and were counted explicitly.")
        lines.append("- Any future review should address source completeness before concluding on the rule.")
    lines.append("")
    lines.append("## What This Does Not Prove")
    lines.append("")
    lines.append("- no alpha approval")
    lines.append("- no paper trading")
    lines.append("- no live trading")
    lines.append("- no production deployment")
    lines.append("- no execution approval")
    lines.append("- no strategy improvement claim")
    lines.append("- no guarantee that the same-bar close basis is executable live")
    lines.append("- no out-of-sample edge proof")
    lines.append("")
    lines.append("## Risk Register")
    lines.append("")
    lines.append("- Same-bar close basis is diagnostic only, not executable approval.")
    lines.append("- The live peak guard is still based on hindsight bar highs, so the parameter set must remain fixed before any future test.")
    lines.append(f"- Interval matching uses the verified `{INTERVAL_CONVENTION}` convention.")
    lines.append("- 750 BTC bars are not tick data.")
    lines.append("- 2025 and 2026 can remain structurally weak even if the full sample improves.")
    lines.append("- Activation count can be meaningful even when the later net expectancy remains negative after cost stress.")
    lines.append("- No row-level artifact persistence.")
    lines.append("- No OFI/L2 approval.")
    lines.append("")
    lines.append("## Stop / Go Assessment")
    lines.append("")
    lines.append("- This remains diagnostic-only.")
    lines.append("- If the full-sample 12 bps stress improves and the improvement is not concentrated in one year, it is suitable only for further review, not execution.")
    lines.append("- If 2025 and 2026 remain structurally poor or the payoff ratio deteriorates materially, the rule should not advance to execution approval.")
    lines.append("- If the source contains unresolved or unmatched rows, that must be fixed separately before any future test.")
    lines.append("")
    lines.append("## Recommended Next Step")
    lines.append("")
    if int(summary["rows_with_matched_bars"]) == int(summary["trade_rows_loaded"]) and int(summary["unresolved_rows"]) == 0:
        lines.append("Recommend a review-only decision note or a separately preregistered next experiment, not execution.")
    else:
        lines.append("Recommend a source-completeness review before any further exit research.")
    lines.append("")
    lines.append("## Explicitly Not Approved")
    lines.append("")
    lines.append("- No strategy/replay logic changed.")
    lines.append("- No backtest run.")
    lines.append("- No exit experiment run.")
    lines.append("- No model trained.")
    lines.append("- No thresholds tuned.")
    lines.append("- No alternative thresholds tested.")
    lines.append("- No alternative windows tested.")
    lines.append("- No row-level artifacts written.")
    lines.append("- No feature-table artifacts written.")
    lines.append("- No model artifacts written.")
    lines.append("- No OFI artifacts written.")
    lines.append("- Same-bar close diagnostic basis only.")
    lines.append("- Not paper/live executable.")
    lines.append("- Alpha remains blocked.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("- OFI reconstruction remains blocked unless separately approved elsewhere.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    full = summary["full_sample"]
    year_rows = summary["year_rows"]
    gross_delta = float(full["gross_expectancy_delta_bps"])
    net12_delta = float(full["diagnostic_net_expectancy_bps_12bps"] - full["original_net_expectancy_bps_12bps"])
    year_deltas = [float(row["gross_expectancy_delta_bps"]) for row in year_rows]
    positive_years = sum(delta > 0.0 for delta in year_deltas)
    structurally_poor = (
        float(summary["split_2025"]["diagnostic_net_expectancy_bps_12bps"]) <= 0.0
        and float(summary["split_2026"]["diagnostic_net_expectancy_bps_12bps"]) <= 0.0
    )
    meaningful_activation = int(summary["activation_count"]) >= max(10, int(0.1 * summary["trades_inspected"]))
    if int(summary["rows_without_matched_bars"]) > 0 or int(summary["unresolved_rows"]) > 0:
        decision = "fixed_param_set_001_diagnostic_inconclusive"
    elif gross_delta > 0.0 and net12_delta > 0.0 and positive_years > 1 and not structurally_poor and meaningful_activation and float(full["diagnostic_payoff_ratio"]) >= float(full["original_payoff_ratio"]) * 0.95:
        decision = "fixed_param_set_001_diagnostic_passed_for_review"
    elif gross_delta <= 0.0 or net12_delta <= 0.0 or positive_years <= 1 or structurally_poor or float(full["diagnostic_payoff_ratio"]) < float(full["original_payoff_ratio"]) * 0.95:
        decision = "fixed_param_set_001_diagnostic_failed"
    else:
        decision = "fixed_param_set_001_diagnostic_inconclusive"
    lines.append(f"Decision: `{decision}`")
    lines.append("")
    lines.append("## Decision Labels")
    lines.append("")
    labels = [
        "c_exhaustion_exit_param_set_001_diagnostic_created",
        "fixed_param_set_001_diagnostic_overlay",
        "fixed_param_set_001_preregistered_only",
        "no_strategy_replay_changes",
        "no_backtest_run",
        "no_exit_experiment_run",
        "no_model_trained",
        "no_thresholds_tuned",
        "no_alternative_thresholds_tested",
        "no_alternative_windows_tested",
        "no_row_level_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "no_ofi_artifacts_written",
        "same_bar_close_diagnostic_basis_only",
        "not_paper_live_executable",
        "alpha_remains_blocked",
        "full_reconstruction_remains_blocked",
        "ofi_reconstruction_blocked_unless_separately_approved_elsewhere",
        decision,
    ]
    for label in labels:
        lines.append(f"- `{label}`")

    report = "\n".join(lines) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report, encoding="utf-8")
    return report, {**summary, "decision": decision}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(trade_log=args.trade_log, bar_dir=args.bar_dir, output_doc=args.output_doc)
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
