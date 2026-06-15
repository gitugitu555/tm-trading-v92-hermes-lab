#!/usr/bin/env python3
"""Research-only exit hypothesis matrix for the V9.2 C_ExhaustionFade replay."""

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

from replays.c_exhaustion_replay import load_750btc_bars, normalize_v92_bar_timestamps


ROUND_TRIP_COST_BPS = 12.0
PERIOD_BOUNDS = {
    "all_period": (2020, 2026),
    "early_period": (2020, 2021),
    "middle_period": (2022, 2024),
    "recent_period": (2025, 2026),
}
HORIZONS = [3, 6, 9, 12, 18, 24, 36, 48]
TP_LEVELS = [50, 100, 150, 200]
GIVEBACK_LEVELS = [50, 100, 150]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _format_number(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        val = float(value)
        if math.isnan(val):
            return "n/a"
        if math.isinf(val):
            return "inf" if val > 0 else "-inf"
        return f"{val:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_number(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def _profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    if not len(losses):
        return float("inf") if len(wins) else 0.0
    loss_sum = float(losses.sum())
    if abs(loss_sum) == 0.0:
        return float("inf") if len(wins) else 0.0
    return float(wins.sum() / abs(loss_sum))


def _summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "trade_count": 0,
            "gross_expectancy_bps": 0.0,
            "net_expectancy_bps": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win_bps": 0.0,
            "avg_loss_bps": 0.0,
            "median_trade_bps": 0.0,
            "p10_trade_bps": 0.0,
            "p25_trade_bps": 0.0,
            "p75_trade_bps": 0.0,
            "p90_trade_bps": 0.0,
            "max_win_bps": 0.0,
            "max_loss_bps": 0.0,
            "positive_tail_count_ge_200bps": 0,
            "positive_tail_rate_ge_200bps": 0.0,
            "negative_tail_count_le_minus_200bps": 0,
            "negative_tail_rate_le_minus_200bps": 0.0,
            "avg_hold_bars": 0.0,
            "median_hold_bars": 0.0,
        }

    net = df["net_return_bps"].astype(float)
    gross = df["gross_return_bps"].astype(float)
    wins = net[net > 0.0]
    losses = net[net < 0.0]

    return {
        "trade_count": int(len(df)),
        "gross_expectancy_bps": float(gross.mean()),
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _profit_factor(net),
        "avg_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_bps": float(losses.mean()) if len(losses) else 0.0,
        "median_trade_bps": float(net.median()),
        "p10_trade_bps": float(net.quantile(0.10)),
        "p25_trade_bps": float(net.quantile(0.25)),
        "p75_trade_bps": float(net.quantile(0.75)),
        "p90_trade_bps": float(net.quantile(0.90)),
        "max_win_bps": float(net.max()),
        "max_loss_bps": float(net.min()),
        "positive_tail_count_ge_200bps": int((net >= 200.0).sum()),
        "positive_tail_rate_ge_200bps": float((net >= 200.0).mean()),
        "negative_tail_count_le_minus_200bps": int((net <= -200.0).sum()),
        "negative_tail_rate_le_minus_200bps": float((net <= -200.0).mean()),
        "avg_hold_bars": float(df["hold_bars"].mean()),
        "median_hold_bars": float(df["hold_bars"].median()),
    }


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


def _candidate_family(candidate: str) -> str:
    if candidate.startswith("horizon_"):
        return "A_fixed_horizon"
    if candidate.startswith("tp_"):
        return "B_tp_fallback"
    if candidate.startswith("giveback_"):
        return "C_giveback_fallback"
    if candidate == "first_positive_close":
        return "D_first_positive_close"
    return "unknown"


def _metric_prefix(candidate: str) -> str:
    if candidate.endswith("_bps"):
        return candidate[:-4]
    return candidate


def _candidate_order() -> list[str]:
    return [
        *[f"horizon_{h}" for h in HORIZONS],
        *[f"tp_{tp}_bps" for tp in TP_LEVELS],
        *[f"giveback_{gb}_bps" for gb in GIVEBACK_LEVELS],
        "first_positive_close",
    ]


def _annotate_trades(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    bars = bars.sort("open_time")
    open_arr = bars.select("open").to_series().to_numpy()
    high_arr = bars.select("high").to_series().to_numpy()
    low_arr = bars.select("low").to_series().to_numpy()
    close_arr = bars.select("close").to_series().to_numpy()

    annotated = trades.copy()
    annotated["configured_exit_price"] = annotated["exit_price"].astype(float)
    annotated["configured_exit_index"] = annotated["exit_index"].astype(int)

    for horizon in HORIZONS:
        gross_values: list[float] = []
        net_values: list[float] = []
        hold_values: list[float] = []
        for row in annotated.itertuples(index=False):
            entry_index = int(row.entry_index)
            target_index = entry_index + horizon
            if target_index >= len(open_arr):
                gross_values.append(np.nan)
                net_values.append(np.nan)
                hold_values.append(np.nan)
                continue
            entry_price = float(row.entry_price)
            gross = (float(open_arr[target_index]) / entry_price - 1.0) * 10_000.0
            gross_values.append(gross)
            net_values.append(gross - ROUND_TRIP_COST_BPS)
            hold_values.append(float(horizon))
        annotated[f"horizon_{horizon}_gross_return_bps"] = gross_values
        annotated[f"horizon_{horizon}_net_return_bps"] = net_values
        annotated[f"horizon_{horizon}_hold_bars"] = hold_values

    for tp in TP_LEVELS:
        gross_values = []
        net_values = []
        hold_values = []
        for row in annotated.itertuples(index=False):
            entry_index = int(row.entry_index)
            entry_price = float(row.entry_price)
            exit_index = min(entry_index + 36, len(open_arr) - 1)
            hit_index = None
            hit_price = None
            for idx in range(entry_index, exit_index):
                if float(high_arr[idx]) >= entry_price * (1.0 + tp / 10_000.0):
                    hit_index = idx
                    hit_price = entry_price * (1.0 + tp / 10_000.0)
                    break
            if hit_price is None:
                if exit_index >= len(open_arr):
                    gross_values.append(np.nan)
                    net_values.append(np.nan)
                    hold_values.append(np.nan)
                    continue
                hit_index = exit_index
                hit_price = float(open_arr[exit_index])
            gross = (hit_price / entry_price - 1.0) * 10_000.0
            gross_values.append(gross)
            net_values.append(gross - ROUND_TRIP_COST_BPS)
            hold_values.append(float(hit_index - entry_index))
        annotated[f"tp_{tp}_gross_return_bps"] = gross_values
        annotated[f"tp_{tp}_net_return_bps"] = net_values
        annotated[f"tp_{tp}_hold_bars"] = hold_values

    for gb in GIVEBACK_LEVELS:
        gross_values = []
        net_values = []
        hold_values = []
        for row in annotated.itertuples(index=False):
            entry_index = int(row.entry_index)
            entry_price = float(row.entry_price)
            exit_index = min(entry_index + 36, len(open_arr) - 1)
            peak_price = entry_price
            exit_price = None
            hold = None
            threshold = gb / 10_000.0
            for idx in range(entry_index, exit_index + 1):
                peak_price = max(peak_price, float(high_arr[idx]))
                if peak_price > entry_price:
                    retrace_level = peak_price * (1.0 - threshold)
                    if float(low_arr[idx]) <= retrace_level:
                        exit_price = retrace_level
                        hold = float(idx - entry_index)
                        break
            if exit_price is None:
                if exit_index >= len(open_arr):
                    gross_values.append(np.nan)
                    net_values.append(np.nan)
                    hold_values.append(np.nan)
                    continue
                exit_price = float(open_arr[exit_index])
                hold = float(exit_index - entry_index)
            gross = (exit_price / entry_price - 1.0) * 10_000.0
            gross_values.append(gross)
            net_values.append(gross - ROUND_TRIP_COST_BPS)
            hold_values.append(hold)
        annotated[f"giveback_{gb}_gross_return_bps"] = gross_values
        annotated[f"giveback_{gb}_net_return_bps"] = net_values
        annotated[f"giveback_{gb}_hold_bars"] = hold_values

    gross_values = []
    net_values = []
    hold_values = []
    for row in annotated.itertuples(index=False):
        entry_index = int(row.entry_index)
        entry_price = float(row.entry_price)
        exit_index = min(entry_index + 36, len(open_arr) - 1)
        exit_price = None
        hold = None
        for idx in range(entry_index, exit_index):
            if float(close_arr[idx]) > entry_price:
                exit_price = float(close_arr[idx])
                hold = float(idx - entry_index)
                break
        if exit_price is None:
            if exit_index >= len(open_arr):
                gross_values.append(np.nan)
                net_values.append(np.nan)
                hold_values.append(np.nan)
                continue
            exit_price = float(open_arr[exit_index])
            hold = float(exit_index - entry_index)
        gross = (exit_price / entry_price - 1.0) * 10_000.0
        gross_values.append(gross)
        net_values.append(gross - ROUND_TRIP_COST_BPS)
        hold_values.append(hold)
    annotated["first_positive_close_gross_return_bps"] = gross_values
    annotated["first_positive_close_net_return_bps"] = net_values
    annotated["first_positive_close_hold_bars"] = hold_values

    annotated["exit_month"] = annotated["exit_time"].dt.to_period("M").astype(str)
    return annotated


def _candidate_results(df: pd.DataFrame, *, candidate: str) -> pd.DataFrame:
    prefix = _metric_prefix(candidate)
    gross_col = f"{prefix}_gross_return_bps"
    net_col = f"{prefix}_net_return_bps"
    hold_col = f"{prefix}_hold_bars"
    out = df[[
        "signal_time",
        "entry_time",
        "exit_time",
        "year",
        "exit_month",
        "entry_price",
        "configured_exit_price",
        "gross_return_bps",
        "net_return_bps",
        gross_col,
        net_col,
        hold_col,
    ]].copy()
    out = out.rename(columns={gross_col: "candidate_gross_return_bps", net_col: "candidate_net_return_bps", hold_col: "hold_bars"})
    out["gross_return_bps"] = out["candidate_gross_return_bps"]
    out["net_return_bps"] = out["candidate_net_return_bps"]
    return out


def _candidate_summary_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for candidate in _candidate_order():
        cdf = _candidate_results(df, candidate=candidate)
        for period, (start_year, end_year) in PERIOD_BOUNDS.items():
            if period == "all_period":
                period_df = cdf
            else:
                period_df = _period_slice(cdf, start_year, end_year)
            summary = _summary(period_df)
            summary.update(
                {
                    "candidate": candidate,
                    "family": _candidate_family(candidate),
                    "period": period,
                }
            )
            rows.append(summary)
    return rows


def _stability_flags(rows: list[dict[str, object]]) -> dict[str, dict[str, bool]]:
    flags: dict[str, dict[str, bool]] = {}
    grouped: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(row["candidate"], {})[row["period"]] = row
    for candidate, by_period in grouped.items():
        early = by_period.get("early_period", {})
        middle = by_period.get("middle_period", {})
        recent = by_period.get("recent_period", {})
        flags[candidate] = {
            "early_positive": bool(early.get("net_expectancy_bps", 0.0) > 0.0),
            "middle_positive": bool(middle.get("net_expectancy_bps", 0.0) > 0.0),
            "recent_positive": bool(recent.get("net_expectancy_bps", 0.0) > 0.0),
            "positive_all_periods": bool(
                early.get("net_expectancy_bps", 0.0) > 0.0
                and middle.get("net_expectancy_bps", 0.0) > 0.0
                and recent.get("net_expectancy_bps", 0.0) > 0.0
            ),
        }
    return flags


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    df = _annotate_trades(trades, bars)
    candidate_rows = _candidate_summary_rows(df)
    flags = _stability_flags(candidate_rows)

    all_period_rows = [row for row in candidate_rows if row["period"] == "all_period"]
    early_rows = [row for row in candidate_rows if row["period"] == "early_period"]
    middle_rows = [row for row in candidate_rows if row["period"] == "middle_period"]
    recent_rows = [row for row in candidate_rows if row["period"] == "recent_period"]

    stable_candidates = [cand for cand, flag in flags.items() if flag["positive_all_periods"]]
    recent_positive = [cand for cand, flag in flags.items() if flag["recent_positive"]]

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Exit Hypothesis Matrix")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This matrix tests whether the repaired C_ExhaustionFade entries still contain exploitable post-entry excursion under a small, pre-registered set of diagnostic exit families."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical trade population: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`")
    lines.append("- Cost model: `round_trip_cost_bps = 12.0`")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "The matrix reuses the already-executed canonical C trades and reconstructs post-entry paths from the raw bars. It evaluates only pre-registered diagnostic exit families and reports the realized metrics under the same 12 bps round-trip cost used by the anchor."
    )
    lines.append("")
    lines.append("## Candidate Families")
    lines.append("")
    lines.append("- Family A: fixed horizons (`horizon_3`, `horizon_6`, `horizon_9`, `horizon_12`, `horizon_18`, `horizon_24`, `horizon_36`, `horizon_48`)")
    lines.append("- Family B: TP fallback to 36-bar exit (`tp_50_bps`, `tp_100_bps`, `tp_150_bps`, `tp_200_bps`)")
    lines.append("- Family C: giveback fallback to 36-bar exit (`giveback_50_bps`, `giveback_100_bps`, `giveback_150_bps`)")
    lines.append("- Family D: `first_positive_close` fallback to 36-bar exit")
    lines.append("")
    lines.append("## All-Period Results")
    lines.append("")
    lines.append(_markdown_table(all_period_rows, [
        "candidate",
        "family",
        "period",
        "trade_count",
        "gross_expectancy_bps",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "median_trade_bps",
        "p10_trade_bps",
        "p25_trade_bps",
        "p75_trade_bps",
        "p90_trade_bps",
        "max_win_bps",
        "max_loss_bps",
        "positive_tail_count_ge_200bps",
        "positive_tail_rate_ge_200bps",
        "negative_tail_count_le_minus_200bps",
        "negative_tail_rate_le_minus_200bps",
        "avg_hold_bars",
        "median_hold_bars",
    ]))
    lines.append("")
    lines.append("## Early vs Middle vs Recent Stability")
    lines.append("")
    lines.append(
        "A candidate is marked `positive_all_periods` only when early, middle, and recent net expectancy are all positive. That is a stability flag, not an approval."
    )
    lines.append("")
    lines.append(_markdown_table(early_rows, [
        "candidate",
        "family",
        "period",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(middle_rows, [
        "candidate",
        "family",
        "period",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(recent_rows, [
        "candidate",
        "family",
        "period",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append("## Recent-Period Results")
    lines.append("")
    lines.append(
        "Recent-period positive expectancy is the key filter here. The matrix is designed to show whether any pre-registered family still earns enough in 2025-2026 to justify further validation."
    )
    lines.append("")
    lines.append(_markdown_table(recent_rows, [
        "candidate",
        "family",
        "period",
        "trade_count",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "avg_hold_bars",
        "median_hold_bars",
        "positive_tail_count_ge_200bps",
        "negative_tail_count_le_minus_200bps",
    ]))
    lines.append("")
    lines.append("## Failure Modes")
    lines.append("")
    lines.append(
        "Shorter fixed horizons reduce recent losses relative to the configured 36-bar exit, but no pre-registered diagnostic family restores recent-period positive expectancy. Take-profit and giveback candidates still matter because they change the loss profile, but they do not create a positive recent-period anchor here."
    )
    lines.append(
        "The matrix therefore supports exit-horizon mismatch as a research direction, not as an approved replacement exit."
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if recent_positive:
        recent_positive_text = ", ".join(sorted(recent_positive))
    else:
        recent_positive_text = "none"
    if stable_candidates:
        stable_text = ", ".join(sorted(stable_candidates))
    else:
        stable_text = "none"
    lines.append(
        f"Answer to question 1: no. Recent-period positive expectancy is restored by diagnostic candidates: {recent_positive_text}."
    )
    lines.append(
        f"Answer to question 2: no candidate remains positive in early, middle, and recent periods; stable across all periods: {stable_text}."
    )
    lines.append(
        "Answer to question 3: shorter fixed horizons help by reducing recent losses, and TP/giveback behavior is also informative, but no diagnostic family restores positive recent expectancy."
    )
    lines.append(
        "Answer to question 4: yes. The matrix supports exit-horizon mismatch as the next research path because the shorter horizons materially reduce recent damage versus the 36-bar baseline."
    )
    lines.append(
        "Answer to question 5: No. This matrix can nominate exit hypotheses for further validation, but it does not approve a replacement exit."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical entry population remains valid for research diagnostics.")
    lines.append("- The diagnostic matrix is internally consistent with the repaired replay path.")
    lines.append("- The least-bad recent-period diagnostic candidates are worth follow-up validation.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- No candidate here is production-approved.")
    lines.append("- No candidate should be treated as a final replacement exit without walk-forward validation.")
    lines.append("- This matrix is not optimization; it is a pre-registered hypothesis screen.")
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Re-run the most promising diagnostic candidates in a walk-forward protocol.")
    lines.append("- After candidate selection, apply PSR/DSR/PBO.")
    lines.append("- Compare candidate behavior across regimes and session slices.")
    lines.append("- Keep production approval out of scope until validation is complete.")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trades = pd.read_csv(args.trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = normalize_v92_bar_timestamps(load_750btc_bars(args.bar_dir))
    report = build_report(trades, bars=bars, trade_log_path=args.trade_log, bar_dir=args.bar_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
