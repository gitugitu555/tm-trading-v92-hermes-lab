#!/usr/bin/env python3
"""Nonparametric failure attribution diagnostic for C_Exhaustion."""

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
    _final_return_basis,
    _interval_path,
    _load_bars,
    _markdown_table,
    _parse_trade_frame,
    _side_basis,
)

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_NONPARAMETRIC_FAILURE_ATTRIBUTION_DIAGNOSTIC.md")
INTERVAL_CONVENTION = "half_open_open_time_convention"
BAR_SIZE_BASIS = "750 BTC bars"
DECISION_LABELS = [
    "recent_failure_entry_degradation_dominated",
    "recent_failure_tail_opportunity_decay_dominated",
    "recent_failure_giveback_worsening_dominated",
    "recent_failure_regime_mismatch_dominated",
    "recent_failure_sample_era_dependence_dominated",
    "recent_failure_mixed_or_inconclusive",
]
ENTRY_CHECKPOINTS = (1, 3, 6)
FAVORABLE_THRESHOLDS_BPS = (25.0, 50.0, 100.0)
TAIL_THRESHOLDS_BPS = (50.0, 100.0, 200.0, 300.0)
CLASS_LABELS = [
    "no_favorable_excursion",
    "small_favorable_excursion_then_loss",
    "large_favorable_excursion_then_giveback",
    "weak_positive_exit",
    "strong_positive_exit",
    "immediate_adverse_path",
    "delayed_decay_path",
]
SPLITS = ["full sample", "2020-2023", "2024-2026", "2025", "2026"]
YEARS = list(range(2020, 2027))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


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
    equity = (1.0 + returns.astype(float) / 10_000.0).cumprod()
    peak = equity.cummax()
    drawdown_pct = ((equity - peak) / peak) * 100.0
    return float(abs(drawdown_pct.min())) if not drawdown_pct.empty else 0.0


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


def _checkpoint_return(entry_price: float, closes: np.ndarray, checkpoint: int) -> float | None:
    if len(closes) < checkpoint:
        return None
    value = closes[checkpoint - 1]
    if not np.isfinite(value):
        return None
    return (float(value) / float(entry_price) - 1.0) * 10_000.0


def _first_n_excursions(entry_price: float, highs: np.ndarray, lows: np.ndarray, checkpoint: int = 6) -> tuple[float | None, float | None]:
    if len(highs) == 0 or len(lows) == 0:
        return None, None
    hi = highs[: min(checkpoint, len(highs))]
    lo = lows[: min(checkpoint, len(lows))]
    hi = hi[np.isfinite(hi)]
    lo = lo[np.isfinite(lo)]
    if len(hi) == 0 or len(lo) == 0:
        return None, None
    early_favorable = (float(np.max(hi)) / float(entry_price) - 1.0) * 10_000.0
    early_adverse = (float(np.min(lo)) / float(entry_price) - 1.0) * 10_000.0
    return early_favorable, early_adverse


def _path_to_trade_record(row: pd.Series, bars: pd.DataFrame) -> dict[str, object]:
    record: dict[str, object] = dict(row._asdict())
    record.update(
        {
            "match_status": "unmatched",
            "path_available": False,
            "path_length": 0,
            "checkpoint_return_1_bps": np.nan,
            "checkpoint_return_3_bps": np.nan,
            "checkpoint_return_6_bps": np.nan,
            "early_favorable_excursion_6_bps": np.nan,
            "early_adverse_excursion_6_bps": np.nan,
            "never_positive_after_entry": False,
            "reached_25_bps_before_original_exit": False,
            "reached_50_bps_before_original_exit": False,
            "reached_100_bps_before_original_exit": False,
            "mfe_bps": np.nan,
            "giveback_bps": np.nan,
            "retained_mfe_ratio": np.nan,
            "lost_more_than_25pct_mfe": False,
            "lost_more_than_50pct_mfe": False,
            "lost_more_than_75pct_mfe": False,
            "positive_mfe_ended_negative": False,
            "attribution_class": "unmatched",
            "available_for_full_checkpoint_set": False,
        }
    )

    entry_time = record.get("entry_time")
    exit_time = record.get("exit_time")
    entry_price = record.get("entry_price")
    exit_price = record.get("exit_price")
    required = [entry_time, exit_time, entry_price, exit_price]
    if any(pd.isna(value) for value in required):
        record["match_status"] = "unmatched"
        return record

    path = _interval_path(bars, pd.Timestamp(entry_time), pd.Timestamp(exit_time))
    if path.empty:
        record["match_status"] = "unmatched"
        return record

    record["match_status"] = "matched"
    record["path_available"] = True
    record["path_length"] = int(len(path))
    record["available_for_full_checkpoint_set"] = bool(len(path) >= max(ENTRY_CHECKPOINTS))

    closes = pd.to_numeric(path["close"], errors="coerce").to_numpy(dtype=float)
    highs = pd.to_numeric(path["high"], errors="coerce").to_numpy(dtype=float)
    lows = pd.to_numeric(path["low"], errors="coerce").to_numpy(dtype=float)

    if len(path) < max(ENTRY_CHECKPOINTS) or len(highs[np.isfinite(highs)]) == 0 or len(lows[np.isfinite(lows)]) == 0:
        record["match_status"] = "unavailable"

    checkpoint_returns = {
        checkpoint: _checkpoint_return(float(entry_price), closes, checkpoint)
        for checkpoint in ENTRY_CHECKPOINTS
    }
    record["checkpoint_return_1_bps"] = checkpoint_returns[1]
    record["checkpoint_return_3_bps"] = checkpoint_returns[3]
    record["checkpoint_return_6_bps"] = checkpoint_returns[6]

    early_favorable, early_adverse = _first_n_excursions(float(entry_price), highs, lows, checkpoint=6)
    record["early_favorable_excursion_6_bps"] = early_favorable
    record["early_adverse_excursion_6_bps"] = early_adverse

    close_returns = closes[np.isfinite(closes)]
    if len(close_returns):
        close_returns_bps = (close_returns / float(entry_price) - 1.0) * 10_000.0
        record["never_positive_after_entry"] = bool(np.all(close_returns_bps <= 0.0))

    high_values = highs[np.isfinite(highs)]
    low_values = lows[np.isfinite(lows)]
    mfe_bps = (float(np.max(high_values)) / float(entry_price) - 1.0) * 10_000.0
    final_return_bps = float(record.get("gross_return_bps")) if pd.notna(record.get("gross_return_bps")) else float(record.get("net_return_bps"))
    record["mfe_bps"] = mfe_bps
    record["giveback_bps"] = final_return_bps - mfe_bps
    record["reached_25_bps_before_original_exit"] = bool(np.max(high_values) >= float(entry_price) * 1.0025)
    record["reached_50_bps_before_original_exit"] = bool(np.max(high_values) >= float(entry_price) * 1.0050)
    record["reached_100_bps_before_original_exit"] = bool(np.max(high_values) >= float(entry_price) * 1.0100)

    if mfe_bps > 0.0:
        retained_ratio = final_return_bps / mfe_bps
        record["retained_mfe_ratio"] = retained_ratio
        record["lost_more_than_25pct_mfe"] = bool(final_return_bps <= 0.75 * mfe_bps)
        record["lost_more_than_50pct_mfe"] = bool(final_return_bps <= 0.50 * mfe_bps)
        record["lost_more_than_75pct_mfe"] = bool(final_return_bps <= 0.25 * mfe_bps)
        record["positive_mfe_ended_negative"] = bool(final_return_bps < 0.0)

    first_bar_return = checkpoint_returns[1]
    if final_return_bps < 0.0 and mfe_bps <= 0.0 and (first_bar_return is not None and first_bar_return <= 0.0):
        record["attribution_class"] = "immediate_adverse_path"
    elif final_return_bps < 0.0 and mfe_bps <= 0.0:
        record["attribution_class"] = "no_favorable_excursion"
    elif final_return_bps < 0.0 and mfe_bps > 0.0 and mfe_bps < 50.0:
        record["attribution_class"] = "small_favorable_excursion_then_loss"
    elif final_return_bps < 0.0 and mfe_bps > 0.0 and (record["path_length"] >= 6 or (record["path_length"] - int(np.nanargmax(high_values))) >= 3):
        record["attribution_class"] = "delayed_decay_path"
    elif final_return_bps < 0.0 and mfe_bps > 0.0:
        record["attribution_class"] = "large_favorable_excursion_then_giveback"
    elif final_return_bps > 0.0 and mfe_bps > 0.0 and record["retained_mfe_ratio"] is not None and float(record["retained_mfe_ratio"]) >= 0.5 and mfe_bps >= 100.0:
        record["attribution_class"] = "strong_positive_exit"
    elif final_return_bps > 0.0 and mfe_bps > 0.0:
        record["attribution_class"] = "weak_positive_exit"
    else:
        record["attribution_class"] = "no_favorable_excursion"

    return record


def _evaluate_trades(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    trades = trades.copy()
    if "year" not in trades.columns or not trades["year"].notna().any():
        trades["year"] = _trade_years(trades)
    else:
        trades["year"] = pd.to_numeric(trades["year"], errors="coerce").astype("Int64")
    trades = trades.sort_values(
        ["signal_time", "entry_time", "exit_time", "signal_index", "entry_index", "exit_index"],
        kind="mergesort",
    ).reset_index(drop=True)

    evaluated = [_path_to_trade_record(row, bars) for row in trades.itertuples(index=False)]
    return pd.DataFrame(evaluated)


def _summary_for_group(group: pd.DataFrame) -> dict[str, object]:
    if group.empty:
        return {
            "trade_count": 0,
            "matched_rows": 0,
            "unmatched_rows": 0,
            "unavailable_path_rows": 0,
            "win_rate": 0.0,
            "gross_expectancy_bps": 0.0,
            "net_expectancy_bps_12bps": 0.0,
            "profit_factor": 0.0,
            "avg_win_bps": 0.0,
            "avg_loss_bps": 0.0,
            "payoff_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "median_mfe_bps": None,
            "p75_mfe_bps": None,
            "p90_mfe_bps": None,
            "p95_mfe_bps": None,
            "median_giveback_bps": None,
            "pct_never_positive_after_entry": 0.0,
            "pct_reaching_25_bps_before_original_exit": 0.0,
            "pct_reaching_50_bps_before_original_exit": 0.0,
            "pct_reaching_100_bps_before_original_exit": 0.0,
            "pct_positive_mfe_ended_negative": 0.0,
            "pct_lost_more_than_25pct_mfe": 0.0,
            "pct_lost_more_than_50pct_mfe": 0.0,
            "pct_lost_more_than_75pct_mfe": 0.0,
            "avg_checkpoint_return_1_bps": None,
            "avg_checkpoint_return_3_bps": None,
            "avg_checkpoint_return_6_bps": None,
            "avg_early_favorable_excursion_6_bps": None,
            "avg_early_adverse_excursion_6_bps": None,
            "pct_unavailable_path": 0.0,
        }

    matched = group[group["match_status"] == "matched"].copy()
    unavailable = group[group["match_status"] == "unavailable"].copy()
    unmatched = group[group["match_status"] == "unmatched"].copy()
    gross = pd.to_numeric(group.get("gross_return_bps"), errors="coerce")
    net = pd.to_numeric(group.get("net_return_bps"), errors="coerce")

    wins = gross[gross > 0.0]
    losses = gross[gross < 0.0]
    avg_loss = float(losses.mean()) if len(losses) else 0.0

    def _mean_or_none(series: pd.Series) -> float | None:
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return float(valid.mean()) if len(valid) else None

    def _quantile_or_none(series: pd.Series, q: float) -> float | None:
        valid = pd.to_numeric(series, errors="coerce").dropna()
        return float(valid.quantile(q)) if len(valid) else None

    return {
        "trade_count": int(len(group)),
        "matched_rows": int(len(matched)),
        "unmatched_rows": int(len(unmatched)),
        "unavailable_path_rows": int(len(unavailable)),
        "win_rate": float((gross > 0.0).mean()) if len(gross.dropna()) else 0.0,
        "gross_expectancy_bps": float(gross.mean()) if len(gross.dropna()) else 0.0,
        "net_expectancy_bps_12bps": float(net.mean()) if len(net.dropna()) else 0.0,
        "profit_factor": _safe_profit_factor(gross.dropna()),
        "avg_win_bps": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_bps": avg_loss,
        "payoff_ratio": _safe_payoff_ratio(gross.dropna()),
        "max_drawdown_pct": _max_drawdown_pct(net.dropna()),
        "median_mfe_bps": _quantile_or_none(matched["mfe_bps"], 0.50),
        "p75_mfe_bps": _quantile_or_none(matched["mfe_bps"], 0.75),
        "p90_mfe_bps": _quantile_or_none(matched["mfe_bps"], 0.90),
        "p95_mfe_bps": _quantile_or_none(matched["mfe_bps"], 0.95),
        "median_giveback_bps": _quantile_or_none(matched["giveback_bps"], 0.50),
        "pct_never_positive_after_entry": float(matched["never_positive_after_entry"].mean()) if len(matched) else 0.0,
        "pct_reaching_25_bps_before_original_exit": float(matched["reached_25_bps_before_original_exit"].mean()) if len(matched) else 0.0,
        "pct_reaching_50_bps_before_original_exit": float(matched["reached_50_bps_before_original_exit"].mean()) if len(matched) else 0.0,
        "pct_reaching_100_bps_before_original_exit": float(matched["reached_100_bps_before_original_exit"].mean()) if len(matched) else 0.0,
        "pct_positive_mfe_ended_negative": float(matched["positive_mfe_ended_negative"].mean()) if len(matched) else 0.0,
        "pct_lost_more_than_25pct_mfe": float(matched["lost_more_than_25pct_mfe"].mean()) if len(matched) else 0.0,
        "pct_lost_more_than_50pct_mfe": float(matched["lost_more_than_50pct_mfe"].mean()) if len(matched) else 0.0,
        "pct_lost_more_than_75pct_mfe": float(matched["lost_more_than_75pct_mfe"].mean()) if len(matched) else 0.0,
        "avg_checkpoint_return_1_bps": _mean_or_none(matched["checkpoint_return_1_bps"]),
        "avg_checkpoint_return_3_bps": _mean_or_none(matched["checkpoint_return_3_bps"]),
        "avg_checkpoint_return_6_bps": _mean_or_none(matched["checkpoint_return_6_bps"]),
        "avg_early_favorable_excursion_6_bps": _mean_or_none(matched["early_favorable_excursion_6_bps"]),
        "avg_early_adverse_excursion_6_bps": _mean_or_none(matched["early_adverse_excursion_6_bps"]),
        "pct_unavailable_path": float(len(unavailable) / len(group)) if len(group) else 0.0,
    }


def _split_metrics(frame: pd.DataFrame, split: str) -> dict[str, object]:
    group = _split_frame(frame, split).copy()
    return {"split": split, **_summary_for_group(group)}


def _year_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    years = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    for year in YEARS:
        group = frame[years == year].copy()
        rows.append({"year": year, **_summary_for_group(group)})
    return rows


def _class_rows(frame: pd.DataFrame, *, key_col: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if key_col == "split":
        keys = SPLITS
        selector = lambda item: _split_frame(frame, item).copy()
    else:
        years = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
        keys = YEARS
        selector = lambda item: frame[years == item].copy()
    for key in keys:
        group = selector(key)
        total = len(group)
        row: dict[str, object] = {"split" if key_col == "split" else "year": key, "trade_count": total}
        for label in CLASS_LABELS:
            count = int((group["attribution_class"] == label).sum()) if total else 0
            pct = float(count / total) if total else 0.0
            row[label] = f"{count} ({pct:.3f})" if total else "0 (0.000)"
        rows.append(row)
    return rows


def _context_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    candidates = [
        "regime",
        "signal_state",
        "trend",
        "range",
        "volatility",
        "context",
        "signal_label",
        "regime_label",
    ]
    rows: list[dict[str, object]] = []
    for column in candidates:
        if column not in frame.columns:
            rows.append({"column": column, "status": "missing", "missing_count": int(len(frame)), "trade_count": 0})
            continue
        values = frame[column].copy()
        missing_count = int(values.isna().sum())
        rows.append({"column": column, "status": "present", "missing_count": missing_count, "trade_count": int(len(frame) - missing_count)})
    return rows


def _infer_decision(summary: dict[str, object]) -> str:
    recent = summary["splits"]["2025"] if "splits" in summary else None
    recent_2 = summary["splits"]["2026"] if "splits" in summary else None
    if not recent or not recent_2:
        return "recent_failure_mixed_or_inconclusive"

    combined_trade_count = int(recent["trade_count"]) + int(recent_2["trade_count"])
    if combined_trade_count == 0:
        return "recent_failure_mixed_or_inconclusive"

    recent_unavailable = float(recent["pct_unavailable_path"]) + float(recent_2["pct_unavailable_path"])
    recent_giveback = float(recent["pct_positive_mfe_ended_negative"]) + float(recent_2["pct_positive_mfe_ended_negative"])
    recent_tail = float(recent["p90_mfe_bps"] or 0.0) + float(recent_2["p90_mfe_bps"] or 0.0)
    recent_entry = float(recent["pct_never_positive_after_entry"]) + float(recent_2["pct_never_positive_after_entry"])
    if recent_unavailable > 1.0:
        return "recent_failure_mixed_or_inconclusive"
    if recent_entry >= 1.0 and float(recent["avg_checkpoint_return_1_bps"] or 0.0) < 0.0:
        return "recent_failure_entry_degradation_dominated"
    if recent_tail < 100.0 and recent_giveback < 0.75:
        return "recent_failure_tail_opportunity_decay_dominated"
    if recent_giveback >= 1.0:
        return "recent_failure_giveback_worsening_dominated"
    return "recent_failure_mixed_or_inconclusive"


def build_report(*, trade_log: Path, bar_dir: Path, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log)
    bars, bar_files = _load_bars(bar_dir)
    diagnostics = _evaluate_trades(trades, bars)
    summary: dict[str, object] = {
        "trade_rows_loaded": int(len(trades)),
        "bar_rows_loaded": int(len(bars)),
        "bar_files_read": int(len(bar_files)),
        "rows_with_matched_bars": int(diagnostics["path_available"].sum()),
        "unresolved_rows": int((~diagnostics["path_available"]).sum() + (diagnostics["match_status"] == "unavailable").sum()),
        "unmatched_rows": int((diagnostics["match_status"] == "unmatched").sum()),
        "unavailable_path_rows": int((diagnostics["match_status"] == "unavailable").sum()),
        "year_min": int(pd.to_numeric(diagnostics["year"], errors="coerce").dropna().min()) if diagnostics["year"].notna().any() else None,
        "year_max": int(pd.to_numeric(diagnostics["year"], errors="coerce").dropna().max()) if diagnostics["year"].notna().any() else None,
        "side_basis": _side_basis(trades),
        "final_return_basis": _final_return_basis(trades),
        "bar_size_basis": BAR_SIZE_BASIS,
        "convention_basis": INTERVAL_CONVENTION,
        "splits": {},
        "years": {},
        "context_rows": _context_rows(trades),
    }

    for split in SPLITS:
        summary["splits"][split] = _split_metrics(diagnostics, split)

    summary["years"] = {year: row for year, row in zip(YEARS, _year_rows(diagnostics), strict=False)}
    summary["decision"] = _infer_decision(summary)

    split_rows = [summary["splits"][split] for split in SPLITS]
    year_rows = [summary["years"][year] for year in YEARS]
    class_split_rows = _class_rows(diagnostics, key_col="split")
    class_year_rows = _class_rows(diagnostics, key_col="year")

    lines: list[str] = []
    lines.append("# C_Exhaustion Nonparametric Failure Attribution Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is the `nonparametric_failure_attribution_diagnostic` for C_Exhaustion. It is a diagnostic only, not a trading rule, and it uses the existing post-regime-fix trade log with the same 750 BTC bars to attribute recent failure modes without changing any execution logic.")
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
    lines.append("- This is not a trading rule.")
    lines.append("- No strategy logic was changed.")
    lines.append("- No replay logic was changed.")
    lines.append("- No entry logic was changed.")
    lines.append("- No exit logic was changed.")
    lines.append("- No OFI logic was changed.")
    lines.append("- No OFI reconstruction was performed.")
    lines.append("- No external data was added.")
    lines.append("- No model was trained.")
    lines.append("- No thresholds were optimized.")
    lines.append("- No exit parameters were tuned.")
    lines.append("- No Param Set 001 nearby variants were tested.")
    lines.append("- No row-level artifacts were created.")
    lines.append("- No feature artifacts were created.")
    lines.append("- No model artifacts were created.")
    lines.append("- No workflows were created.")
    lines.append("- Alpha remains blocked.")
    lines.append("- Paper/live remains blocked.")
    lines.append("- Full OFI reconstruction remains blocked.")
    lines.append("")
    lines.append("## Source Summary")
    lines.append("")
    lines.append(f"- trade_rows_loaded: `{summary['trade_rows_loaded']}`")
    lines.append(f"- bar_rows_loaded: `{summary['bar_rows_loaded']}`")
    lines.append(f"- bar_files_read: `{summary['bar_files_read']}`")
    lines.append(f"- rows_with_matched_bars: `{summary['rows_with_matched_bars']}`")
    lines.append(f"- unresolved_rows: `{summary['unresolved_rows']}`")
    lines.append(f"- unmatched_rows: `{summary['unmatched_rows']}`")
    lines.append(f"- unavailable_path_rows: `{summary['unavailable_path_rows']}`")
    lines.append(f"- year_min: `{summary['year_min']}`")
    lines.append(f"- year_max: `{summary['year_max']}`")
    lines.append(f"- side_basis: `{summary['side_basis']}`")
    lines.append(f"- final_return_basis: `{summary['final_return_basis']}`")
    lines.append(f"- bar_size_basis: `{summary['bar_size_basis']}`")
    lines.append(f"- convention_basis: `{summary['convention_basis']}`")
    lines.append("")
    lines.append("## Method Notes")
    lines.append("")
    lines.append("- Half-open matching convention: `bar.open_time >= entry_time and bar.open_time < exit_time`.")
    lines.append("- Completed bars only are used for checkpoint returns.")
    lines.append("- MFE and attribution labels are hindsight-only diagnostic labels, not live-tradable signals.")
    lines.append("- Entry checkpoints use the first 1, 3, and 6 completed bars only.")
    lines.append("- Any missing regime or context columns are reported explicitly rather than treated as a failure.")
    lines.append("")

    lines.append("## 1. Entry Degradation")
    lines.append("")
    lines.append("Checkpoint returns and early excursion measures use completed bars only.")
    lines.append("")
    lines.append(
        _markdown_table(
            split_rows,
            [
                "split",
                "trade_count",
                "matched_rows",
                "unmatched_rows",
                "unavailable_path_rows",
                "avg_checkpoint_return_1_bps",
                "avg_checkpoint_return_3_bps",
                "avg_checkpoint_return_6_bps",
                "avg_early_favorable_excursion_6_bps",
                "avg_early_adverse_excursion_6_bps",
                "pct_never_positive_after_entry",
                "pct_reaching_25_bps_before_original_exit",
                "pct_reaching_50_bps_before_original_exit",
                "pct_reaching_100_bps_before_original_exit",
            ],
        )
    )
    lines.append("")
    lines.append(_markdown_table(year_rows, [
        "year",
        "trade_count",
        "matched_rows",
        "unmatched_rows",
        "unavailable_path_rows",
        "avg_checkpoint_return_1_bps",
        "avg_checkpoint_return_3_bps",
        "avg_checkpoint_return_6_bps",
        "avg_early_favorable_excursion_6_bps",
        "avg_early_adverse_excursion_6_bps",
        "pct_never_positive_after_entry",
        "pct_reaching_25_bps_before_original_exit",
        "pct_reaching_50_bps_before_original_exit",
        "pct_reaching_100_bps_before_original_exit",
    ]))
    lines.append("")

    lines.append("## 2. Tail Opportunity Decay")
    lines.append("")
    lines.append("MFE is hindsight-only diagnostic information and not a live-tradable signal.")
    lines.append("")
    lines.append(_markdown_table(split_rows, [
        "split",
        "trade_count",
        "median_mfe_bps",
        "p75_mfe_bps",
        "p90_mfe_bps",
        "p95_mfe_bps",
        "pct_reaching_25_bps_before_original_exit",
        "pct_reaching_50_bps_before_original_exit",
        "pct_reaching_100_bps_before_original_exit",
        "pct_unavailable_path",
    ]))
    lines.append("")
    lines.append(_markdown_table(year_rows, [
        "year",
        "trade_count",
        "median_mfe_bps",
        "p75_mfe_bps",
        "p90_mfe_bps",
        "p95_mfe_bps",
        "pct_reaching_25_bps_before_original_exit",
        "pct_reaching_50_bps_before_original_exit",
        "pct_reaching_100_bps_before_original_exit",
        "pct_unavailable_path",
    ]))
    lines.append("")

    lines.append("## 3. Giveback Worsening")
    lines.append("")
    lines.append("Giveback is computed as `final_return_bps - mfe_bps`; retained MFE ratio is `final_return_bps / mfe_bps` when `mfe_bps > 0`.")
    lines.append("")
    lines.append(_markdown_table(split_rows, [
        "split",
        "trade_count",
        "median_mfe_bps",
        "median_giveback_bps",
        "pct_positive_mfe_ended_negative",
        "pct_lost_more_than_25pct_mfe",
        "pct_lost_more_than_50pct_mfe",
        "pct_lost_more_than_75pct_mfe",
        "pct_unavailable_path",
        "net_expectancy_bps_12bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(year_rows, [
        "year",
        "trade_count",
        "median_mfe_bps",
        "median_giveback_bps",
        "pct_positive_mfe_ended_negative",
        "pct_lost_more_than_25pct_mfe",
        "pct_lost_more_than_50pct_mfe",
        "pct_lost_more_than_75pct_mfe",
        "pct_unavailable_path",
        "net_expectancy_bps_12bps",
    ]))
    lines.append("")

    lines.append("## 4. Exit vs Entry Attribution Classes")
    lines.append("")
    lines.append("These attribution bins are descriptive only. They are not execution rules and must not be used as live exits.")
    lines.append("")
    lines.append(_markdown_table(class_split_rows, ["split", "trade_count", *CLASS_LABELS]))
    lines.append("")
    lines.append(_markdown_table(class_year_rows, ["year", "trade_count", *CLASS_LABELS]))
    lines.append("")

    lines.append("## 5. Era and Year Stability")
    lines.append("")
    lines.append("The tables below summarize performance and path-shape stability across the requested splits and years.")
    lines.append("")
    lines.append(_markdown_table(split_rows, [
        "split",
        "trade_count",
        "win_rate",
        "gross_expectancy_bps",
        "net_expectancy_bps_12bps",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "payoff_ratio",
        "max_drawdown_pct",
        "median_mfe_bps",
        "median_giveback_bps",
    ]))
    lines.append("")
    lines.append(_markdown_table(year_rows, [
        "year",
        "trade_count",
        "win_rate",
        "gross_expectancy_bps",
        "net_expectancy_bps_12bps",
        "profit_factor",
        "avg_win_bps",
        "avg_loss_bps",
        "payoff_ratio",
        "max_drawdown_pct",
        "median_mfe_bps",
        "median_giveback_bps",
    ]))
    lines.append("")

    lines.append("## 6. Existing Context / Regime Attribution")
    lines.append("")
    lines.append("Only columns already present in the trade log were considered. No new features were reconstructed, no OFI was rebuilt, and no classifier or threshold optimization was performed.")
    lines.append("")
    lines.append(_markdown_table(summary["context_rows"], ["column", "status", "missing_count", "trade_count"]))
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(f"- Is recent failure more consistent with entry degradation? `{summary['decision'] == 'recent_failure_entry_degradation_dominated'}`")
    lines.append(f"- Is recent failure more consistent with tail opportunity decay? `{summary['decision'] == 'recent_failure_tail_opportunity_decay_dominated'}`")
    lines.append(f"- Is recent failure more consistent with giveback worsening? `{summary['decision'] == 'recent_failure_giveback_worsening_dominated'}`")
    lines.append(f"- Is recent failure more consistent with regime mismatch? `{summary['decision'] == 'recent_failure_regime_mismatch_dominated'}`")
    lines.append(f"- Is recent failure more consistent with sample-era dependence? `{summary['decision'] == 'recent_failure_sample_era_dependence_dominated'}`")
    lines.append(f"- Is the result mixed or inconclusive? `{summary['decision'] == 'recent_failure_mixed_or_inconclusive'}`")
    lines.append("- Did any diagnostic rely on hindsight-only labels? `true`")
    lines.append("- Are any labels live-tradable? `no`")
    lines.append("- Does this approve any exit rule? `no`")
    lines.append("- Does this approve alpha? `no`")
    lines.append("- Does this approve paper/live trading? `no`")
    lines.append("- Does this unblock OFI reconstruction? `no`")
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(f"decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Safety Notes")
    lines.append("")
    lines.append("- Hindsight-only labels are explicitly not live-tradable.")
    lines.append("- No row-level artifacts were written.")
    lines.append("- No scripts outside this diagnostic were changed.")
    lines.append("- Alpha remains blocked.")
    lines.append("- Paper/live remains blocked.")
    lines.append("- Full OFI reconstruction remains blocked.")

    report = "\n".join(lines) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report, encoding="utf-8")
    return report, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(trade_log=args.trade_log, bar_dir=args.bar_dir, output_doc=args.output_doc)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
