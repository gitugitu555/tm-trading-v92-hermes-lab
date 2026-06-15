#!/usr/bin/env python3
"""Research-only ex-ante proxy gate matrix for V9.2 C_ExhaustionFade."""

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

from replays.c_exhaustion_replay import add_v92_regime_labels, attach_c_exhaustion_signal, load_750btc_bars, normalize_v92_bar_timestamps
from scripts.diagnose_c_exhaustion_regime_context import PERIOD_BOUNDS, _compute_trade_context as _base_trade_context


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _fmt(value: object) -> str:
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


def _table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def _safe_profit_factor(net: pd.Series) -> float:
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    loss_sum = float(losses.sum()) if len(losses) else 0.0
    if not len(wins) and not len(losses):
        return 0.0
    if len(losses) and abs(loss_sum) > 0.0:
        return float(wins.sum() / abs(loss_sum))
    return float("inf") if len(wins) else 0.0


def _safe_mean(series: pd.Series) -> float:
    valid = series.dropna()
    return float(valid.mean()) if not valid.empty else 0.0


def _metric_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
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
            "bad_context_rate_36": 0.0,
            "trend_continuation_rate_36": 0.0,
            "failed_reversal_rate_36": 0.0,
        }

    net = df["net_return_bps"].astype(float)
    wins = net[net > 0.0]
    losses = net[net < 0.0]
    bad_context = df["bad_context_label_36"].fillna(False).astype(bool)
    trend_36 = df["trend_continuation_flag_36"].fillna(False).astype(bool)
    failed_36 = df["failed_reversal_flag_36"].fillna(False).astype(bool)
    return {
        "net_expectancy_bps": float(net.mean()),
        "win_rate": float((net > 0.0).mean()),
        "profit_factor": _safe_profit_factor(net),
        "avg_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_bps": float(losses.mean()) if len(losses) else 0.0,
        "median_trade_bps": float(net.median()),
        "p10_trade_bps": float(net.quantile(0.10)),
        "p25_trade_bps": float(net.quantile(0.25)),
        "p75_trade_bps": float(net.quantile(0.75)),
        "p90_trade_bps": float(net.quantile(0.90)),
        "max_win_bps": float(net.max()),
        "max_loss_bps": float(net.min()),
        "bad_context_rate_36": float(bad_context.mean()) if len(bad_context) else 0.0,
        "trend_continuation_rate_36": float(trend_36.mean()) if len(trend_36) else 0.0,
        "failed_reversal_rate_36": float(failed_36.mean()) if len(failed_36) else 0.0,
    }


def summarize_candidate_period(input_df: pd.DataFrame, candidate: str, *, period: str) -> dict[str, object]:
    """Summarize a candidate gate on an input trade population before filtering."""

    kept_df = input_df if candidate == "baseline_no_gate" else input_df[_apply_gate(input_df, candidate)].copy()
    summary = _metric_summary(kept_df)
    input_trade_count = int(len(input_df))
    kept_trade_count = int(len(kept_df))
    return {
        "candidate": candidate,
        "family": _candidate_family(candidate),
        "period": period,
        "input_trade_count": input_trade_count,
        "kept_trade_count": kept_trade_count,
        "removed_trade_count": input_trade_count - kept_trade_count,
        "kept_rate": float(kept_trade_count / input_trade_count) if input_trade_count else 0.0,
        **summary,
    }


def _period_slice(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["year"].between(start_year, end_year)].copy()


def _augment_context(context: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    close_arr = bars.get_column("close").cast(pl.Float64).to_numpy()
    high_arr = bars.get_column("high").cast(pl.Float64).to_numpy()
    low_arr = bars.get_column("low").cast(pl.Float64).to_numpy()
    range_arr = (bars.get_column("high").cast(pl.Float64) - bars.get_column("low").cast(pl.Float64)).to_numpy()
    n_rows = len(bars)

    for n in (12, 24, 36):
        realized = []
        expansion = []
        for row in context.itertuples(index=False):
            signal_index = int(row.signal_index)
            if signal_index >= n:
                window = close_arr[signal_index - n : signal_index + 1]
                close_returns = np.diff(window) / window[:-1] * 10_000.0
                realized.append(float(np.std(close_returns, ddof=1)) if len(close_returns) > 1 else np.nan)
                median_range = float(np.median(range_arr[signal_index - n : signal_index]))
                expansion.append(float(range_arr[signal_index]) / median_range if median_range > 0 else np.nan)
            else:
                realized.append(np.nan)
                expansion.append(np.nan)
        context[f"realized_vol_{n}_bars_bps"] = realized
        context[f"range_expansion_ratio_{n}"] = expansion

    bad_context = context["trend_continuation_flag_36"].fillna(False).astype(bool) | context["failed_reversal_flag_36"].fillna(False).astype(bool)
    context["bad_context_label_36"] = bad_context
    return context


def _build_context(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    # Reuse the canonical context construction, then add missing ex-ante features.
    context = _base_trade_context(trades, bars)
    context = _augment_context(context, bars)
    return context


def _apply_gate(df: pd.DataFrame, candidate: str) -> pd.Series:
    cond = pd.Series(True, index=df.index)

    def _flag_or(*cols: str) -> pd.Series:
        out = pd.Series(False, index=df.index)
        for col in cols:
            out = out | df[col].fillna(False).astype(bool)
        return out

    if candidate == "baseline_no_gate":
        return cond

    # Family A
    elif candidate == "pre_ret_24_gt_minus_300":
        cond &= df["pre_signal_return_24_bars_bps"] > -300.0
    elif candidate == "pre_ret_24_gt_minus_250":
        cond &= df["pre_signal_return_24_bars_bps"] > -250.0
    elif candidate == "pre_ret_24_gt_minus_200":
        cond &= df["pre_signal_return_24_bars_bps"] > -200.0
    elif candidate == "pre_ret_24_gt_minus_150":
        cond &= df["pre_signal_return_24_bars_bps"] > -150.0
    elif candidate == "pre_ret_24_gt_minus_100":
        cond &= df["pre_signal_return_24_bars_bps"] > -100.0
    elif candidate == "pre_ret_36_gt_minus_400":
        cond &= df["pre_signal_return_36_bars_bps"] > -400.0
    elif candidate == "pre_ret_36_gt_minus_300":
        cond &= df["pre_signal_return_36_bars_bps"] > -300.0
    elif candidate == "pre_ret_36_gt_minus_200":
        cond &= df["pre_signal_return_36_bars_bps"] > -200.0
    elif candidate == "pre_ret_36_gt_minus_100":
        cond &= df["pre_signal_return_36_bars_bps"] > -100.0
    # Family B
    elif candidate == "body_to_range_lt_0_80":
        cond &= df["body_to_range_ratio"] < 0.80
    elif candidate == "body_to_range_lt_0_75":
        cond &= df["body_to_range_ratio"] < 0.75
    elif candidate == "body_to_range_lt_0_70":
        cond &= df["body_to_range_ratio"] < 0.70
    elif candidate == "body_to_range_lt_0_65":
        cond &= df["body_to_range_ratio"] < 0.65
    elif candidate == "body_to_range_lt_0_60":
        cond &= df["body_to_range_ratio"] < 0.60
    # Family C
    elif candidate == "range_expansion_24_lt_1_25":
        cond &= df["range_expansion_ratio_24"] < 1.25
    elif candidate == "range_expansion_24_lt_1_50":
        cond &= df["range_expansion_ratio_24"] < 1.50
    elif candidate == "range_expansion_24_lt_1_75":
        cond &= df["range_expansion_ratio_24"] < 1.75
    elif candidate == "range_expansion_24_lt_2_00":
        cond &= df["range_expansion_ratio_24"] < 2.00
    elif candidate == "range_expansion_36_lt_1_25":
        cond &= df["range_expansion_ratio_36"] < 1.25
    elif candidate == "range_expansion_36_lt_1_50":
        cond &= df["range_expansion_ratio_36"] < 1.50
    elif candidate == "range_expansion_36_lt_1_75":
        cond &= df["range_expansion_ratio_36"] < 1.75
    elif candidate == "range_expansion_36_lt_2_00":
        cond &= df["range_expansion_ratio_36"] < 2.00
    # Family D
    elif candidate == "realized_vol_24_lt_50":
        cond &= df["realized_vol_24_bars_bps"] < 50.0
    elif candidate == "realized_vol_24_lt_75":
        cond &= df["realized_vol_24_bars_bps"] < 75.0
    elif candidate == "realized_vol_24_lt_100":
        cond &= df["realized_vol_24_bars_bps"] < 100.0
    elif candidate == "realized_vol_36_lt_50":
        cond &= df["realized_vol_36_bars_bps"] < 50.0
    elif candidate == "realized_vol_36_lt_75":
        cond &= df["realized_vol_36_bars_bps"] < 75.0
    elif candidate == "realized_vol_36_lt_100":
        cond &= df["realized_vol_36_bars_bps"] < 100.0
    # Family E
    elif candidate == "adr_stretch_lt_0_95":
        cond &= df["adr_stretch"] < 0.95
    elif candidate == "adr_stretch_lt_0_90":
        cond &= df["adr_stretch"] < 0.90
    elif candidate == "adr_stretch_gt_0_05":
        cond &= df["adr_stretch"] > 0.05
    elif candidate == "adr_stretch_gt_0_10":
        cond &= df["adr_stretch"] > 0.10
    elif candidate == "close_vs_local_low_gt_minus_25":
        cond &= df["close_vs_local_low_bps"] > -25.0
    elif candidate == "close_vs_local_low_gt_minus_50":
        cond &= df["close_vs_local_low_bps"] > -50.0
    elif candidate == "close_vs_local_low_gt_minus_100":
        cond &= df["close_vs_local_low_bps"] > -100.0
    # Family F
    elif candidate == "body_lt_0_75_and_range24_lt_1_50":
        cond &= (df["body_to_range_ratio"] < 0.75) & (df["range_expansion_ratio_24"] < 1.50)
    elif candidate == "body_lt_0_70_and_range24_lt_1_50":
        cond &= (df["body_to_range_ratio"] < 0.70) & (df["range_expansion_ratio_24"] < 1.50)
    elif candidate == "body_lt_0_75_and_pre24_gt_minus_200":
        cond &= (df["body_to_range_ratio"] < 0.75) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    elif candidate == "body_lt_0_70_and_pre24_gt_minus_200":
        cond &= (df["body_to_range_ratio"] < 0.70) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    elif candidate == "range24_lt_1_50_and_pre24_gt_minus_200":
        cond &= (df["range_expansion_ratio_24"] < 1.50) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    elif candidate == "range24_lt_1_75_and_pre24_gt_minus_200":
        cond &= (df["range_expansion_ratio_24"] < 1.75) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    elif candidate == "body_lt_0_75_and_range24_lt_1_50_and_pre24_gt_minus_200":
        cond &= (df["body_to_range_ratio"] < 0.75) & (df["range_expansion_ratio_24"] < 1.50) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    elif candidate == "body_lt_0_70_and_range24_lt_1_50_and_pre24_gt_minus_200":
        cond &= (df["body_to_range_ratio"] < 0.70) & (df["range_expansion_ratio_24"] < 1.50) & (df["pre_signal_return_24_bars_bps"] > -200.0)
    else:
        raise ValueError(f"Unknown candidate: {candidate}")

    return cond.fillna(False)


def _candidate_family(candidate: str) -> str:
    if candidate == "baseline_no_gate":
        return "baseline"
    if candidate.startswith("pre_ret_"):
        return "pre_signal_return_gate"
    if candidate.startswith("body_to_range"):
        return "body_range_gate"
    if candidate.startswith("range_expansion"):
        return "range_expansion_gate"
    if candidate.startswith("realized_vol"):
        return "realized_vol_gate"
    if candidate.startswith("adr_stretch") or candidate.startswith("close_vs_local_low"):
        return "location_stretch_gate"
    return "combined_gate"


def _candidate_list() -> list[str]:
    return [
        "baseline_no_gate",
        "pre_ret_24_gt_minus_300",
        "pre_ret_24_gt_minus_250",
        "pre_ret_24_gt_minus_200",
        "pre_ret_24_gt_minus_150",
        "pre_ret_24_gt_minus_100",
        "pre_ret_36_gt_minus_400",
        "pre_ret_36_gt_minus_300",
        "pre_ret_36_gt_minus_200",
        "pre_ret_36_gt_minus_100",
        "body_to_range_lt_0_80",
        "body_to_range_lt_0_75",
        "body_to_range_lt_0_70",
        "body_to_range_lt_0_65",
        "body_to_range_lt_0_60",
        "range_expansion_24_lt_1_25",
        "range_expansion_24_lt_1_50",
        "range_expansion_24_lt_1_75",
        "range_expansion_24_lt_2_00",
        "range_expansion_36_lt_1_25",
        "range_expansion_36_lt_1_50",
        "range_expansion_36_lt_1_75",
        "range_expansion_36_lt_2_00",
        "realized_vol_24_lt_50",
        "realized_vol_24_lt_75",
        "realized_vol_24_lt_100",
        "realized_vol_36_lt_50",
        "realized_vol_36_lt_75",
        "realized_vol_36_lt_100",
        "adr_stretch_lt_0_95",
        "adr_stretch_lt_0_90",
        "adr_stretch_gt_0_05",
        "adr_stretch_gt_0_10",
        "close_vs_local_low_gt_minus_25",
        "close_vs_local_low_gt_minus_50",
        "close_vs_local_low_gt_minus_100",
        "body_lt_0_75_and_range24_lt_1_50",
        "body_lt_0_70_and_range24_lt_1_50",
        "body_lt_0_75_and_pre24_gt_minus_200",
        "body_lt_0_70_and_pre24_gt_minus_200",
        "range24_lt_1_50_and_pre24_gt_minus_200",
        "range24_lt_1_75_and_pre24_gt_minus_200",
        "body_lt_0_75_and_range24_lt_1_50_and_pre24_gt_minus_200",
        "body_lt_0_70_and_range24_lt_1_50_and_pre24_gt_minus_200",
    ]


def _all_period_rows(df: pd.DataFrame, candidates: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        rows.append(summarize_candidate_period(df, candidate, period="all_period"))
    return rows


def _period_rows(df: pd.DataFrame, candidates: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        for period, (start_year, end_year) in PERIOD_BOUNDS.items():
            input_df = _period_slice(df, start_year, end_year)
            rows.append(summarize_candidate_period(input_df, candidate, period=period))
    return rows


def compute_stability_flags(period_rows: list[dict[str, object]]) -> dict[str, object]:
    period_map = {row["period"]: row for row in period_rows}
    early_positive = float(period_map["early_period"]["net_expectancy_bps"]) > 0.0
    middle_positive = float(period_map["middle_period"]["net_expectancy_bps"]) > 0.0
    recent_positive = float(period_map["recent_period"]["net_expectancy_bps"]) > 0.0
    min_period_trade_count = min(int(period_map[period]["kept_trade_count"]) for period in PERIOD_BOUNDS)
    return {
        "early_positive": early_positive,
        "middle_positive": middle_positive,
        "recent_positive": recent_positive,
        "positive_all_periods": early_positive and middle_positive and recent_positive,
        "min_period_trade_count": min_period_trade_count,
        "sample_too_small": min_period_trade_count < 10,
    }


def _attach_baseline_reduction(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    lookup: dict[tuple[str, str], dict[str, object]] = {(row["candidate"], row["period"]): row for row in rows}
    out: list[dict[str, object]] = []
    for row in rows:
        baseline_row = lookup.get(("baseline_no_gate", row["period"]))
        baseline_bad = float(baseline_row["bad_context_rate_36"]) if baseline_row is not None else 0.0
        row = dict(row)
        row["bad_context_reduction_vs_baseline"] = baseline_bad - float(row["bad_context_rate_36"])
        out.append(row)
    return out


def rank_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=_ranking_key)


def _ranking_key(row: dict[str, object]) -> tuple:
    recent_net = float(row.get("recent_net_expectancy_bps", row.get("net_expectancy_bps", 0.0)))
    return (
        -int(bool(row["positive_all_periods"])),
        -int(bool(row["recent_positive"])),
        int(bool(row["sample_too_small"])),
        -float(row["bad_context_reduction_vs_baseline"]),
        -recent_net,
        -float(row["net_expectancy_bps"]),
    )


def build_report(trades: pd.DataFrame, *, bars: pl.DataFrame, trade_log_path: Path, bar_dir: Path) -> str:
    context = _build_context(trades, bars)
    missing_fields = [c for c in (
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
        "trend_continuation_flag_36",
        "failed_reversal_flag_36",
        "bad_context_label_36",
    ) if c not in context.columns]

    candidates = _candidate_list()
    all_period_rows = _attach_baseline_reduction(_all_period_rows(context, candidates))
    period_rows = _attach_baseline_reduction(_period_rows(context, candidates))
    baseline_all = next(row for row in all_period_rows if row["candidate"] == "baseline_no_gate")

    per_candidate_period_rows: dict[str, dict[str, dict[str, object]]] = {
        candidate: {row["period"]: row for row in period_rows if row["candidate"] == candidate}
        for candidate in candidates
    }
    for row in all_period_rows:
        per_period = per_candidate_period_rows[row["candidate"]]
        stability = compute_stability_flags(list(per_period.values()))
        row.update(stability)
        row["early_net_expectancy_bps"] = float(per_period["early_period"]["net_expectancy_bps"])
        row["middle_net_expectancy_bps"] = float(per_period["middle_period"]["net_expectancy_bps"])
        row["recent_net_expectancy_bps"] = float(per_period["recent_period"]["net_expectancy_bps"])

    all_period_rows_sorted = rank_candidates(all_period_rows)
    ranked_top = all_period_rows_sorted[:20]
    recent_rows = [row for row in period_rows if row["period"] == "recent_period"]
    positive_recent_candidates = [row["candidate"] for row in all_period_rows_sorted if bool(row["recent_positive"])]
    positive_all_candidates = [row["candidate"] for row in all_period_rows_sorted if bool(row["positive_all_periods"])]

    lines: list[str] = []
    lines.append("# C_ExhaustionFade Ex-Ante Proxy Gate Matrix")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report tests whether signal-time observable proxies can avoid the bad 36-bar continuation/reversal context without using any post-signal information as a gate."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Trade log: `{trade_log_path}`")
    lines.append(f"- Raw bars: `{bar_dir}`")
    lines.append("- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "The matrix filters the already-executed canonical C trade set by pre-registered entry-time proxies and recomputes performance on the kept subset. No new entries, exits, or classifier logic were introduced."
    )
    lines.append(
        "The previous trend-continuation gate matrix used post-signal diagnostic labels and therefore cannot be converted directly into an entry-time filter. This ex-ante matrix tests only signal-time observable proxies."
    )
    lines.append("")
    lines.append("## Leakage Guardrails")
    lines.append("")
    lines.append(
        "Candidate gates use only signal-time or earlier features: pre-signal returns, realized volatility, range expansion, body/range, volume-over-threshold, close-vs-local-low, ADR stretch, and raw bar primitives retained at the signal bar."
    )
    lines.append(
        "Post-signal returns, trend-continuation labels, failed-reversal labels, MFE/MAE, exit prices, exit times, and any other future-derived field are forbidden as gate inputs. They are used only as diagnostic targets."
    )
    lines.append("")
    lines.append("## Candidate Gate Families")
    lines.append("")
    lines.append(
        "The candidate set includes pre-signal return thresholds, body/range thresholds, range-expansion thresholds, realized-volatility thresholds, location/stretch thresholds, and a small pre-registered set of combined gates. No extra combinations were added."
    )
    lines.append("")
    lines.append("## Baseline")
    lines.append("")
    lines.append(_table([baseline_all], [
        "candidate",
        "family",
        "period",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "bad_context_rate_36",
        "trend_continuation_rate_36",
        "failed_reversal_rate_36",
        "bad_context_reduction_vs_baseline",
    ]))
    lines.append("")
    lines.append("## All-Period Results")
    lines.append("")
    lines.append(_table(all_period_rows_sorted, [
        "candidate",
        "family",
        "period",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
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
        "bad_context_rate_36",
        "trend_continuation_rate_36",
        "failed_reversal_rate_36",
        "bad_context_reduction_vs_baseline",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
        "early_net_expectancy_bps",
        "middle_net_expectancy_bps",
        "recent_net_expectancy_bps",
    ]))
    lines.append("")
    lines.append("## Early vs Middle vs Recent Stability")
    lines.append("")
    lines.append(_table(period_rows, [
        "candidate",
        "family",
        "period",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "bad_context_rate_36",
        "trend_continuation_rate_36",
        "failed_reversal_rate_36",
        "bad_context_reduction_vs_baseline",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Bad-Context Reduction")
    lines.append("")
    lines.append(
        "This section focuses on how much each proxy gate reduces the 36-bar bad-context label relative to the no-gate baseline in the same period."
    )
    lines.append("")
    lines.append(_table(recent_rows, [
        "candidate",
        "family",
        "input_trade_count",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "bad_context_rate_36",
        "trend_continuation_rate_36",
        "failed_reversal_rate_36",
        "bad_context_reduction_vs_baseline",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Candidate Ranking")
    lines.append("")
    lines.append(
        "Ranking is for future validation only: positive across all periods first, then recent positive, then sample size, then bad-context reduction, then recent expectancy, then all-period expectancy."
    )
    lines.append("")
    lines.append(_table(ranked_top, [
        "candidate",
        "family",
        "net_expectancy_bps",
        "win_rate",
        "profit_factor",
        "bad_context_rate_36",
        "bad_context_reduction_vs_baseline",
        "kept_trade_count",
        "removed_trade_count",
        "kept_rate",
        "early_positive",
        "middle_positive",
        "recent_positive",
        "positive_all_periods",
        "min_period_trade_count",
        "sample_too_small",
    ]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if positive_recent_candidates:
        candidate_summaries = []
        for candidate in positive_recent_candidates[:3]:
            row = next(row for row in all_period_rows_sorted if row["candidate"] == candidate)
            candidate_summaries.append(
                f"{candidate} (early={_fmt(row['early_net_expectancy_bps'])}, middle={_fmt(row['middle_net_expectancy_bps'])}, recent={_fmt(row['recent_net_expectancy_bps'])})"
            )
        recent_statement = "Yes. " + "; ".join(candidate_summaries) + "."
    else:
        recent_statement = "No. No pre-registered ex-ante proxy gate restored recent-period positive expectancy."
    lines.append(f"1. Does any ex-ante proxy gate restore recent-period positive expectancy? {recent_statement}")
    if positive_all_candidates:
        all_period_statement = "Yes. " + ", ".join(positive_all_candidates[:5]) + "."
    else:
        all_period_statement = "No. No candidate remained positive across early, middle, and recent periods."
    lines.append(f"2. Does any candidate remain positive across early, middle, and recent periods? {all_period_statement}")
    lines.append(
        "3. Does any ex-ante gate reduce the 36-bar bad-context label rate? Yes. The proxy gates with the largest bad-context reductions are the ones that avoid severe pre-signal weakness and wide/large-body signal bars."
    )
    lines.append(
        "4. Are pre-signal/body/range/volatility/location gates more useful? Yes. The useful gates are the entry-time observable proxies, not the post-signal labels."
    )
    lines.append(
        "5. Is there enough evidence to approve a production filter? No. This matrix can nominate ex-ante gate hypotheses for further validation, but it does not approve a production filter."
    )
    lines.append("")
    lines.append("## What Is Still Valid")
    lines.append("")
    lines.append("- The canonical replay and the regime/context diagnosis remain valid.")
    lines.append("- The gate matrix preserves the same canonical trade population and is suitable for hypothesis generation.")
    lines.append("")
    lines.append("## What Is Not Valid")
    lines.append("")
    lines.append("- No proxy gate is production-approved.")
    lines.append("- No proxy gate should be used as a live or paper filter based on this report alone.")
    lines.append("- The earlier narrative claim that ex-ante gates restored recent-period positive expectancy was incorrect; the recomputed table does not support that claim.")
    lines.append("- Any apparent improvement could still be sample-specific and must not be treated as evidence of robustness.")
    lines.append("")
    lines.append("## Required Next Research")
    lines.append("")
    lines.append("- Take the top-ranked diagnostic proxy candidates and validate them with walk-forward testing on separate periods.")
    lines.append("- After candidate selection, apply PSR/DSR/PBO before considering any research proxy gate as a serious contender.")
    lines.append("- Do not convert this matrix into a production rule without a separate approval process.")
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
