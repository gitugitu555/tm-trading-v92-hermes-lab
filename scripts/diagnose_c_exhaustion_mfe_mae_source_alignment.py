#!/usr/bin/env python3
"""Bounded source-alignment diagnostic for the C_Exhaustion MFE/MAE source."""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import load_750btc_bars, normalize_v92_bar_timestamps  # noqa: E402

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_ALIGNMENT_DIAGNOSTIC.md")
REQUIRED_TRADE_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "net_return_bps",
]
OPTIONAL_TRADE_COLUMNS = ["year", "gross_return_bps", "holding_bars"]
REQUIRED_BAR_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]
OPTIONAL_BAR_COLUMNS = ["bar_id", "volume", "volume_delta"]
CONVENTION_LABELS = [
    "half_open_open_time_convention",
    "closed_open_time_convention",
    "close_time_convention",
    "broad_overlap_convention",
]
TRADE_TIMESTAMP_COLUMNS = ["signal_time", "entry_time", "exit_time"]
MATCH_COLUMNS = [
    ("signal_time", "signal_index", "open_time", "signal_time == bar open_time"),
    ("signal_time", "signal_index", "close_time", "signal_time == bar close_time"),
    ("entry_time", "entry_index", "open_time", "entry_time == bar open_time"),
    ("entry_time", "entry_index", "close_time", "entry_time == bar close_time"),
    ("exit_time", "exit_index", "open_time", "exit_time == bar open_time"),
    ("exit_time", "exit_index", "close_time", "exit_time == bar close_time"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    return str(value)


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def _parse_timestamp_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _normalized_timestamp_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if isinstance(parsed, pd.Series):
        return parsed.dt.tz_convert(None)
    return pd.Series(parsed).dt.tz_convert(None)


def _infer_precision(series: pd.Series) -> str:
    clean = pd.Series(series).dropna()
    if clean.empty:
        return "n/a"
    values = clean.sort_values().drop_duplicates()
    if len(values) < 2:
        return "unknown"
    diffs = values.diff().dropna().astype("timedelta64[ns]").astype(np.int64)
    positive = diffs[diffs > 0]
    if positive.empty:
        return "unknown"
    smallest = int(positive.min())
    units = [
        ("d", 86_400_000_000_000),
        ("h", 3_600_000_000_000),
        ("min", 60_000_000_000),
        ("s", 1_000_000_000),
        ("ms", 1_000_000),
        ("us", 1_000),
        ("ns", 1),
    ]
    for label, scale in units:
        if smallest % scale == 0:
            return f"{smallest // scale}{label}"
    return f"{smallest}ns"


def _tz_status(series: pd.Series) -> str:
    parsed = _parse_timestamp_series(series)
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return f"timezone-aware ({parsed.dt.tz})"
    if pd.api.types.is_datetime64_any_dtype(parsed.dtype):
        return "timezone-naive"
    return "mixed/unknown"


def _parse_trade_frame(trade_log: Path) -> pd.DataFrame:
    suffix = trade_log.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(trade_log)
    elif suffix == ".parquet":
        frame = pd.read_parquet(trade_log)
    else:  # pragma: no cover - not used in approved task
        raise ValueError(f"Unsupported trade-log type: {trade_log.suffix}")

    missing = [column for column in REQUIRED_TRADE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Trade log is missing required columns: {missing}")

    for column in TRADE_TIMESTAMP_COLUMNS:
        frame[column] = _normalized_timestamp_series(frame[column])
    for column in ["signal_index", "entry_index", "exit_index", "year", "holding_bars"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "year" not in frame.columns or not frame["year"].notna().any():
        frame["year"] = frame["signal_time"].dt.year.astype("Int64")
    return frame


def _load_bars(bar_dir: Path) -> tuple[pd.DataFrame, list[Path]]:
    bar_files = sorted(bar_dir.glob("BTCUSDT_tier2_750btc_*.parquet"))
    if not bar_files:
        raise FileNotFoundError(f"No 750 BTC parquet shards found in {bar_dir}")
    bars_pl = normalize_v92_bar_timestamps(load_750btc_bars(bar_dir))
    bars = bars_pl.to_pandas()
    if "datetime_open" in bars.columns and "datetime_close" in bars.columns:
        bars = bars.assign(
            open_time=bars["datetime_open"],
            close_time=bars["datetime_close"],
        ).drop(columns=["datetime_open", "datetime_close"])
    for column in ["open_time", "close_time"]:
        bars[column] = _normalized_timestamp_series(bars[column])
    sort_cols = [column for column in ["open_time", "close_time", "bar_id"] if column in bars.columns]
    if sort_cols:
        bars = bars.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    return bars, bar_files


def _nearest_delta_summary(values: pd.Series, reference: pd.Series) -> dict[str, object]:
    clean_values = pd.Series(values).dropna()
    clean_reference = pd.Series(reference).dropna()
    if clean_values.empty or clean_reference.empty:
        return {"median": None, "min": None, "max": None}

    ref_ns = clean_reference.sort_values().astype("datetime64[ns]").astype(np.int64).to_numpy()
    deltas: list[int] = []
    for value in clean_values.astype("datetime64[ns]").astype(np.int64).to_numpy():
        pos = int(np.searchsorted(ref_ns, value, side="left"))
        candidates = []
        if pos < len(ref_ns):
            candidates.append(abs(int(ref_ns[pos]) - int(value)))
        if pos > 0:
            candidates.append(abs(int(ref_ns[pos - 1]) - int(value)))
        if candidates:
            deltas.append(min(candidates))
    if not deltas:
        return {"median": None, "min": None, "max": None}
    delta_series = pd.to_timedelta(pd.Series(deltas), unit="ns")
    return {
        "median": delta_series.median(),
        "min": delta_series.min(),
        "max": delta_series.max(),
    }


def _range_coverage(trades: pd.DataFrame, bars: pd.DataFrame) -> dict[str, object]:
    bar_min = min(bars["open_time"].min(), bars["close_time"].min())
    bar_max = max(bars["open_time"].max(), bars["close_time"].max())
    result = {}
    for column in TRADE_TIMESTAMP_COLUMNS:
        inside = trades[column].between(bar_min, bar_max, inclusive="both")
        result[f"{column}_inside_bar_range_count"] = int(inside.sum())
    all_inside = (
        trades["signal_time"].between(bar_min, bar_max, inclusive="both")
        & trades["entry_time"].between(bar_min, bar_max, inclusive="both")
        & trades["exit_time"].between(bar_min, bar_max, inclusive="both")
    )
    result["all_interval_inside_bar_range_count"] = int(all_inside.sum())
    result["outside_range_count"] = int(len(trades) - result["all_interval_inside_bar_range_count"])
    result["bar_min"] = bar_min
    result["bar_max"] = bar_max
    return result


def _exact_match_rate(trades: pd.DataFrame, bars: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    bar_count = len(bars)
    for trade_col, index_col, bar_col, label in MATCH_COLUMNS:
        if bar_col not in bars.columns:
            rows.append({"label": label, "matched_count": 0, "match_rate": 0.0})
            continue
        matches = []
        for trade in trades.itertuples(index=False):
            idx = getattr(trade, index_col, pd.NA)
            if pd.isna(idx):
                matches.append(False)
                continue
            idx = int(idx)
            if idx < 0 or idx >= bar_count:
                matches.append(False)
                continue
            trade_value = getattr(trade, trade_col)
            bar_value = bars.iloc[idx][bar_col]
            matches.append(pd.notna(trade_value) and pd.notna(bar_value) and trade_value == bar_value)
        rows.append({"label": label, "matched_count": int(sum(matches)), "match_rate": float(sum(matches) / len(matches)) if matches else 0.0})
    return rows


def _count_interval_matches(trades: pd.DataFrame, bars: pd.DataFrame) -> list[dict[str, object]]:
    open_times = bars["open_time"].to_numpy(dtype="datetime64[ns]")
    close_times = bars["close_time"].to_numpy(dtype="datetime64[ns]")
    out: list[dict[str, object]] = []

    def half_open_count(entry: pd.Timestamp, exit_: pd.Timestamp) -> int:
        start = int(np.searchsorted(open_times, np.datetime64(entry), side="left"))
        end = int(np.searchsorted(open_times, np.datetime64(exit_), side="left"))
        return max(0, end - start)

    def closed_open_count(entry: pd.Timestamp, exit_: pd.Timestamp) -> int:
        start = int(np.searchsorted(open_times, np.datetime64(entry), side="left"))
        end = int(np.searchsorted(open_times, np.datetime64(exit_), side="right"))
        return max(0, end - start)

    def close_time_count(entry: pd.Timestamp, exit_: pd.Timestamp) -> int:
        start = int(np.searchsorted(close_times, np.datetime64(entry), side="right"))
        end = int(np.searchsorted(close_times, np.datetime64(exit_), side="right"))
        return max(0, end - start)

    def broad_overlap_count(entry: pd.Timestamp, exit_: pd.Timestamp) -> int:
        start = int(np.searchsorted(close_times, np.datetime64(entry), side="left"))
        end = int(np.searchsorted(open_times, np.datetime64(exit_), side="right"))
        return max(0, end - start)

    functions = {
        "half_open_open_time_convention": half_open_count,
        "closed_open_time_convention": closed_open_count,
        "close_time_convention": close_time_count,
        "broad_overlap_convention": broad_overlap_count,
    }
    for label, fn in functions.items():
        counts: list[int] = []
        per_year_2025 = 0
        per_year_2026 = 0
        for trade in trades.itertuples(index=False):
            count = fn(trade.entry_time, trade.exit_time)
            counts.append(count)
            if int(getattr(trade, "year", pd.NA)) == 2025 and count > 0:
                per_year_2025 += 1
            if int(getattr(trade, "year", pd.NA)) == 2026 and count > 0:
                per_year_2026 += 1
        matched = [count for count in counts if count > 0]
        out.append(
            {
                "convention": label,
                "matched_trade_count": int(sum(count > 0 for count in counts)),
                "zero_match_trade_count": int(sum(count == 0 for count in counts)),
                "median_matched_bar_count": float(np.median(matched)) if matched else None,
                "2025_matched_trade_count": int(per_year_2025),
                "2026_matched_trade_count": int(per_year_2026),
            }
        )
    return out


def _index_mapping_audit(trades: pd.DataFrame, bars: pd.DataFrame) -> dict[str, object]:
    audit: dict[str, object] = {
        "bar_id_available": "bar_id" in bars.columns,
        "entry_index_min": int(trades["entry_index"].min()) if trades["entry_index"].notna().any() else None,
        "entry_index_max": int(trades["entry_index"].max()) if trades["entry_index"].notna().any() else None,
        "exit_index_min": int(trades["exit_index"].min()) if trades["exit_index"].notna().any() else None,
        "exit_index_max": int(trades["exit_index"].max()) if trades["exit_index"].notna().any() else None,
        "bar_row_count": int(len(bars)),
        "indices_within_row_range": False,
        "entry_index_count_in_bar_id": None,
        "exit_index_count_in_bar_id": None,
        "both_indices_count_in_bar_id": None,
        "entry_index_le_exit_index_count": int((trades["entry_index"] <= trades["exit_index"]).sum()),
        "valid_bar_id_range_count": None,
    }

    within = (
        trades["entry_index"].between(0, len(bars) - 1, inclusive="both")
        & trades["exit_index"].between(0, len(bars) - 1, inclusive="both")
    )
    audit["indices_within_row_range"] = bool(within.all())

    if "bar_id" in bars.columns:
        bar_id_values = set(pd.to_numeric(bars["bar_id"], errors="coerce").dropna().astype(int).tolist())
        entry_present = trades["entry_index"].dropna().astype(int).isin(bar_id_values)
        exit_present = trades["exit_index"].dropna().astype(int).isin(bar_id_values)
        audit["entry_index_count_in_bar_id"] = int(entry_present.sum())
        audit["exit_index_count_in_bar_id"] = int(exit_present.sum())
        audit["both_indices_count_in_bar_id"] = int((entry_present & exit_present).sum())
        valid_range = trades["entry_index"].dropna().astype(int).between(int(min(bar_id_values)), int(max(bar_id_values)), inclusive="both") & trades["exit_index"].dropna().astype(int).between(int(min(bar_id_values)), int(max(bar_id_values)), inclusive="both")
        audit["valid_bar_id_range_count"] = int(valid_range.sum())
    return audit


def _shard_coverage(bar_files: list[Path], trades: pd.DataFrame) -> dict[str, object]:
    names = [path.name for path in bar_files]
    date_re = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)")
    date_tokens: list[str] = []
    day_shards = 0
    month_shards = 0
    for name in names:
        match = date_re.search(name)
        if match:
            token = match.group(1)
            date_tokens.append(token)
            if len(token) == 10:
                day_shards += 1
            else:
                month_shards += 1
    inferred_years = sorted({int(token[:4]) for token in date_tokens})
    coverage = {
        "number_of_bar_files_discovered": len(names),
        "number_loaded": len(bar_files),
        "first_shard_name": names[0] if names else None,
        "last_shard_name": names[-1] if names else None,
        "date_month_tokens": date_tokens[:10],
        "inferred_years": inferred_years,
        "trade_years_covered": all(year in inferred_years for year in sorted({int(y) for y in trades["year"].dropna().astype(int)})),
        "day_month_duplication_present": bool(day_shards and month_shards),
        "wrong_day_fallback_risk_detected": bool(len(set(date_tokens)) < len(date_tokens) or not inferred_years),
        "coverage_2026_05": any(token.startswith("2026-05") for token in date_tokens),
        "coverage_2026_05_09": any(token == "2026-05-09" for token in date_tokens),
    }
    return coverage


def _candidate_root_cause(summary: dict[str, object]) -> str:
    if summary["trade_time_inside"] is False:
        return "timestamp_range_mismatch"
    if summary["timezone_mismatch"] or summary["precision_mismatch"]:
        return "timestamp_precision_or_timezone_mismatch"
    if summary["best_convention_matched_trade_count"] > 0 and summary["exact_match_total"] == 0:
        return "open_close_convention_mismatch"
    if summary["index_mapping_feasible"]:
        return "index_mapping_required"
    if summary["trade_years_covered"] is False or summary["wrong_day_fallback_risk_detected"]:
        return "shard_selection_mismatch"
    if summary["interval_overlap_any"] is False:
        return "source_materialization_mismatch"
    if summary["bar_time_inside_trade"] is False:
        return "strict_boundary_filtering"
    return "unresolved_alignment_failure"


def _safe_matching_decision(summary: dict[str, object]) -> str:
    if summary["best_convention_matched_trade_count"] > 0:
        best = summary["best_convention_label"]
        if best == "half_open_open_time_convention":
            return "safe_timestamp_open_time_convention_identified"
        if best == "closed_open_time_convention":
            return "safe_timestamp_open_time_convention_identified"
        if best == "close_time_convention":
            return "safe_timestamp_close_time_convention_identified"
        if best == "broad_overlap_convention":
            return "safe_interval_overlap_convention_identified"
    if summary["index_mapping_feasible"]:
        return "safe_index_mapping_convention_identified"
    if summary["candidate_root_cause"] == "source_materialization_mismatch":
        return "source_materialization_mismatch_suspected"
    return "no_safe_matching_convention_identified"


def build_report(*, trade_log: Path, bar_dir: Path, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log)
    bars, bar_files = _load_bars(bar_dir)

    trade_min = {f"min_{col}": trades[col].min() for col in TRADE_TIMESTAMP_COLUMNS}
    trade_max = {f"max_{col}": trades[col].max() for col in TRADE_TIMESTAMP_COLUMNS}
    trade_info = {
        **trade_min,
        **trade_max,
        "signal_time_dtype": str(trades["signal_time"].dtype),
        "entry_time_dtype": str(trades["entry_time"].dtype),
        "exit_time_dtype": str(trades["exit_time"].dtype),
        "signal_time_timezone_status": _tz_status(pd.read_csv(trade_log)["signal_time"]),
        "entry_time_timezone_status": _tz_status(pd.read_csv(trade_log)["entry_time"]),
        "exit_time_timezone_status": _tz_status(pd.read_csv(trade_log)["exit_time"]),
        "signal_time_precision": _infer_precision(trades["signal_time"]),
        "entry_time_precision": _infer_precision(trades["entry_time"]),
        "exit_time_precision": _infer_precision(trades["exit_time"]),
    }

    bar_info = {
        "min_open_time": bars["open_time"].min(),
        "max_open_time": bars["open_time"].max(),
        "min_close_time": bars["close_time"].min(),
        "max_close_time": bars["close_time"].max(),
        "open_time_dtype": str(bars["open_time"].dtype),
        "close_time_dtype": str(bars["close_time"].dtype),
        "open_time_timezone_status": _tz_status(pd.Series(bars["open_time"])),
        "close_time_timezone_status": _tz_status(pd.Series(bars["close_time"])),
        "open_time_precision": _infer_precision(pd.Series(bars["open_time"])),
        "close_time_precision": _infer_precision(pd.Series(bars["close_time"])),
        "number_of_bar_files_loaded": len(bar_files),
        "number_of_bar_rows_loaded": int(len(bars)),
        "year_coverage": sorted({int(str(p.name).split("_")[-1].split(".")[0].split("-")[0]) for p in bar_files if re.search(r"\d{4}", p.name)}),
    }

    range_coverage = _range_coverage(trades, bars)
    exact_matches = _exact_match_rate(trades, bars)
    interval_conventions = _count_interval_matches(trades, bars)
    index_audit = _index_mapping_audit(trades, bars)
    shard_audit = _shard_coverage(bar_files, trades)

    nearest = {
        "signal_time_nearest_open": _nearest_delta_summary(trades["signal_time"], bars["open_time"]),
        "signal_time_nearest_close": _nearest_delta_summary(trades["signal_time"], bars["close_time"]),
        "entry_time_nearest_open": _nearest_delta_summary(trades["entry_time"], bars["open_time"]),
        "entry_time_nearest_close": _nearest_delta_summary(trades["entry_time"], bars["close_time"]),
        "exit_time_nearest_open": _nearest_delta_summary(trades["exit_time"], bars["open_time"]),
        "exit_time_nearest_close": _nearest_delta_summary(trades["exit_time"], bars["close_time"]),
    }

    exact_total = sum(item["matched_count"] for item in exact_matches)
    exact_rate_total = exact_total / (len(trades) * len(exact_matches)) if trades is not None and len(trades) else 0.0
    trade_time_inside = bool(range_coverage["all_interval_inside_bar_range_count"] == len(trades))
    bar_time_inside_trade = bool(range_coverage["signal_time_inside_bar_range_count"] > 0)
    timezone_mismatch = any(
        status.startswith("timezone-aware") for status in [
            trade_info["signal_time_timezone_status"],
            trade_info["entry_time_timezone_status"],
            trade_info["exit_time_timezone_status"],
        ]
    ) != any(status.startswith("timezone-aware") for status in [
        bar_info["open_time_timezone_status"],
        bar_info["close_time_timezone_status"],
    ])
    precision_mismatch = {trade_info["signal_time_precision"], trade_info["entry_time_precision"], trade_info["exit_time_precision"]} != {
        bar_info["open_time_precision"],
        bar_info["close_time_precision"],
    }
    best_conv = max(interval_conventions, key=lambda row: row["matched_trade_count"])
    interval_overlap_any = any(row["matched_trade_count"] > 0 for row in interval_conventions)
    index_mapping_feasible = bool(index_audit["indices_within_row_range"]) or (
        bool(index_audit["bar_id_available"]) and int(index_audit["both_indices_count_in_bar_id"] or 0) > 0
    )

    summary = {
        "trade_rows_loaded": int(len(trades)),
        "bar_rows_loaded": int(len(bars)),
        "bar_files_read": int(len(bar_files)),
        "trade_year_min": int(trades["year"].min()),
        "trade_year_max": int(trades["year"].max()),
        "trade_log_path": str(trade_log),
        "bar_dir_path": str(bar_dir),
        "trade_info": trade_info,
        "bar_info": bar_info,
        "range_coverage": range_coverage,
        "exact_matches": exact_matches,
        "nearest": nearest,
        "interval_conventions": interval_conventions,
        "index_audit": index_audit,
        "shard_audit": shard_audit,
        "trade_time_inside": trade_time_inside,
        "bar_time_inside_trade": bar_time_inside_trade,
        "timezone_mismatch": timezone_mismatch,
        "precision_mismatch": precision_mismatch,
        "exact_match_total": int(exact_total),
        "exact_match_rate_total": float(exact_rate_total),
        "best_convention_label": best_conv["convention"],
        "best_convention_matched_trade_count": int(best_conv["matched_trade_count"]),
        "interval_overlap_any": interval_overlap_any,
        "index_mapping_feasible": index_mapping_feasible,
    }
    summary["candidate_root_cause"] = _candidate_root_cause(summary)
    summary["safe_matching_convention_decision"] = _safe_matching_decision(summary)
    if summary["safe_matching_convention_decision"] in {
        "safe_timestamp_open_time_convention_identified",
        "safe_timestamp_close_time_convention_identified",
        "safe_interval_overlap_convention_identified",
        "safe_index_mapping_convention_identified",
    }:
        if summary["candidate_root_cause"] == "source_materialization_mismatch":
            summary["decision"] = "source_alignment_diagnostic_partial"
        else:
            summary["decision"] = "source_alignment_diagnostic_pass"
    elif summary["candidate_root_cause"] == "source_materialization_mismatch":
        summary["decision"] = "source_alignment_diagnostic_blocked"
    else:
        summary["decision"] = "source_alignment_diagnostic_partial" if interval_overlap_any else "source_alignment_diagnostic_blocked"

    lines: list[str] = []
    lines.append("# V9.2 C_Exhaustion MFE/MAE Source Alignment Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is a bounded source-remediation alignment diagnostic only. It inspects timestamp, index, and bar-shard matching feasibility after the MFE/MAE source-construction dry run failed to match any trade intervals.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- trade_log path: `{trade_log}`")
    lines.append(f"- bar_dir path: `{bar_dir}`")
    lines.append("- real_trade_log_read: `true`")
    lines.append("- real_bounded_bar_data_read: `true`")
    lines.append("- raw_l2_data_read: `false`")
    lines.append("- ofi_artifacts_read: `false`")
    lines.append("- row_level_artifacts_written: `false`")
    lines.append("- mfe_mae_computed: `false`")
    lines.append("- giveback_classified: `false`")
    lines.append("- source_script_patched: `false`")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No MFE/MAE was computed.")
    lines.append("- No giveback classification was performed.")
    lines.append("- No source-construction script was patched.")
    lines.append("- No exit horizon was optimized.")
    lines.append("- No target/stop tuning was performed.")
    lines.append("- No threshold tuning was performed.")
    lines.append("- No model was trained.")
    lines.append("- No strategy backtest was run.")
    lines.append("- No strategy/replay logic was changed.")
    lines.append("- No raw L2 data was read.")
    lines.append("- No OFI artifacts were read or written.")
    lines.append("- No row-level artifacts were written.")
    lines.append("- No feature-table artifacts were written.")
    lines.append("- No model artifacts were written.")
    lines.append("- No paper/live trading is approved.")
    lines.append("- No production approval is given.")
    lines.append("- Alpha is not approved.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("")
    lines.append("## Source-Construction Failure Recap")
    lines.append("")
    lines.append(f"- trade_rows_loaded: `{summary['trade_rows_loaded']}`")
    lines.append(f"- bar_rows_loaded: `{summary['bar_rows_loaded']}`")
    lines.append(f"- bar_files_read: `{summary['bar_files_read']}`")
    lines.append(f"- rows_with_matched_bars: `0`")
    lines.append(f"- unresolved_rows: `{summary['trade_rows_loaded']}`")
    lines.append(f"- decision from previous dry run: `bounded_mfe_mae_source_construction_blocked`")
    lines.append("")
    lines.append("## Trade Log Timestamp Audit")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "metric": "min_signal_time",
                "value": trade_info["min_signal_time"],
                "dtype": trade_info["signal_time_dtype"],
                "timezone": trade_info["signal_time_timezone_status"],
                "precision": trade_info["signal_time_precision"],
            },
            {
                "metric": "max_signal_time",
                "value": trade_info["max_signal_time"],
                "dtype": trade_info["signal_time_dtype"],
                "timezone": trade_info["signal_time_timezone_status"],
                "precision": trade_info["signal_time_precision"],
            },
            {
                "metric": "min_entry_time",
                "value": trade_info["min_entry_time"],
                "dtype": trade_info["entry_time_dtype"],
                "timezone": trade_info["entry_time_timezone_status"],
                "precision": trade_info["entry_time_precision"],
            },
            {
                "metric": "max_entry_time",
                "value": trade_info["max_entry_time"],
                "dtype": trade_info["entry_time_dtype"],
                "timezone": trade_info["entry_time_timezone_status"],
                "precision": trade_info["entry_time_precision"],
            },
            {
                "metric": "min_exit_time",
                "value": trade_info["min_exit_time"],
                "dtype": trade_info["exit_time_dtype"],
                "timezone": trade_info["exit_time_timezone_status"],
                "precision": trade_info["exit_time_precision"],
            },
            {
                "metric": "max_exit_time",
                "value": trade_info["max_exit_time"],
                "dtype": trade_info["exit_time_dtype"],
                "timezone": trade_info["exit_time_timezone_status"],
                "precision": trade_info["exit_time_precision"],
            },
        ],
        ["metric", "value", "dtype", "timezone", "precision"],
    ))
    lines.append("")
    lines.append("## Bar Timestamp Audit")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "metric": "min_open_time",
                "value": bar_info["min_open_time"],
                "dtype": bar_info["open_time_dtype"],
                "timezone": bar_info["open_time_timezone_status"],
                "precision": bar_info["open_time_precision"],
            },
            {
                "metric": "max_open_time",
                "value": bar_info["max_open_time"],
                "dtype": bar_info["open_time_dtype"],
                "timezone": bar_info["open_time_timezone_status"],
                "precision": bar_info["open_time_precision"],
            },
            {
                "metric": "min_close_time",
                "value": bar_info["min_close_time"],
                "dtype": bar_info["close_time_dtype"],
                "timezone": bar_info["close_time_timezone_status"],
                "precision": bar_info["close_time_precision"],
            },
            {
                "metric": "max_close_time",
                "value": bar_info["max_close_time"],
                "dtype": bar_info["close_time_dtype"],
                "timezone": bar_info["close_time_timezone_status"],
                "precision": bar_info["close_time_precision"],
            },
            {
                "metric": "number_of_bar_files_loaded",
                "value": bar_info["number_of_bar_files_loaded"],
                "dtype": bar_info["open_time_dtype"],
                "timezone": bar_info["open_time_timezone_status"],
                "precision": bar_info["open_time_precision"],
            },
            {
                "metric": "number_of_bar_rows_loaded",
                "value": bar_info["number_of_bar_rows_loaded"],
                "dtype": bar_info["open_time_dtype"],
                "timezone": bar_info["open_time_timezone_status"],
                "precision": bar_info["open_time_precision"],
            },
        ],
        ["metric", "value", "dtype", "timezone", "precision"],
    ))
    lines.append("")
    lines.append("## Time Range Coverage")
    lines.append("")
    lines.append(f"- signal_time_inside_bar_range_count: `{range_coverage['signal_time_inside_bar_range_count']}`")
    lines.append(f"- entry_time_inside_bar_range_count: `{range_coverage['entry_time_inside_bar_range_count']}`")
    lines.append(f"- exit_time_inside_bar_range_count: `{range_coverage['exit_time_inside_bar_range_count']}`")
    lines.append(f"- all_interval_inside_bar_range_count: `{range_coverage['all_interval_inside_bar_range_count']}`")
    lines.append(f"- outside_range_count: `{range_coverage['outside_range_count']}`")
    lines.append("")
    lines.append("## Exact Timestamp Match Rates")
    lines.append("")
    lines.append(_markdown_table(exact_matches, ["label", "matched_count", "match_rate"]))
    lines.append("")
    lines.append("## Nearest Timestamp Distance Summary")
    lines.append("")
    nearest_rows = []
    for label, summary_row in nearest.items():
        nearest_rows.append(
            {
                "label": label,
                "median": summary_row["median"],
                "min": summary_row["min"],
                "max": summary_row["max"],
            }
        )
    lines.append(_markdown_table(nearest_rows, ["label", "median", "min", "max"]))
    lines.append("")
    lines.append("## Interval Overlap Convention Audit")
    lines.append("")
    lines.append(_markdown_table(interval_conventions, ["convention", "matched_trade_count", "zero_match_trade_count", "median_matched_bar_count", "2025_matched_trade_count", "2026_matched_trade_count"]))
    lines.append("")
    lines.append("## Index Mapping Feasibility")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "metric": "bar_id_available",
                "value": index_audit["bar_id_available"],
            },
            {
                "metric": "entry_index_min",
                "value": index_audit["entry_index_min"],
            },
            {
                "metric": "entry_index_max",
                "value": index_audit["entry_index_max"],
            },
            {
                "metric": "exit_index_min",
                "value": index_audit["exit_index_min"],
            },
            {
                "metric": "exit_index_max",
                "value": index_audit["exit_index_max"],
            },
            {
                "metric": "bar_row_count",
                "value": index_audit["bar_row_count"],
            },
            {
                "metric": "indices_within_row_range",
                "value": index_audit["indices_within_row_range"],
            },
            {
                "metric": "entry_index_count_in_bar_id",
                "value": index_audit["entry_index_count_in_bar_id"],
            },
            {
                "metric": "exit_index_count_in_bar_id",
                "value": index_audit["exit_index_count_in_bar_id"],
            },
            {
                "metric": "both_indices_count_in_bar_id",
                "value": index_audit["both_indices_count_in_bar_id"],
            },
            {
                "metric": "entry_index_le_exit_index_count",
                "value": index_audit["entry_index_le_exit_index_count"],
            },
            {
                "metric": "valid_bar_id_range_count",
                "value": index_audit["valid_bar_id_range_count"],
            },
        ],
        ["metric", "value"],
    ))
    lines.append("")
    lines.append("## Shard Coverage Audit")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "metric": "number_of_bar_files_discovered",
                "value": shard_audit["number_of_bar_files_discovered"],
            },
            {
                "metric": "number_loaded",
                "value": shard_audit["number_loaded"],
            },
            {
                "metric": "first_shard_name",
                "value": shard_audit["first_shard_name"],
            },
            {
                "metric": "last_shard_name",
                "value": shard_audit["last_shard_name"],
            },
            {
                "metric": "date_month_tokens",
                "value": ", ".join(shard_audit["date_month_tokens"]),
            },
            {
                "metric": "trade_years_covered",
                "value": shard_audit["trade_years_covered"],
            },
            {
                "metric": "day_month_duplication_present",
                "value": shard_audit["day_month_duplication_present"],
            },
            {
                "metric": "wrong_day_fallback_risk_detected",
                "value": shard_audit["wrong_day_fallback_risk_detected"],
            },
            {
                "metric": "coverage_2026_05",
                "value": shard_audit["coverage_2026_05"],
            },
            {
                "metric": "coverage_2026_05_09",
                "value": shard_audit["coverage_2026_05_09"],
            },
        ],
        ["metric", "value"],
    ))
    lines.append("")
    lines.append("## Candidate Root Cause")
    lines.append("")
    lines.append(f"- candidate_root_cause: `{summary['candidate_root_cause']}`")
    lines.append("")
    lines.append("Explanation:")
    if summary["candidate_root_cause"] == "timestamp_range_mismatch":
        lines.append("- Trade intervals fall outside the loaded bar time range.")
    elif summary["candidate_root_cause"] == "timestamp_precision_or_timezone_mismatch":
        lines.append("- The timestamps appear parseable but differ in timezone or precision normalization.")
    elif summary["candidate_root_cause"] == "open_close_convention_mismatch":
        lines.append("- Exact and interval checks point to a convention mismatch between open/close endpoints.")
    elif summary["candidate_root_cause"] == "index_mapping_required":
        lines.append("- Timestamp matching is weak, but the indices appear feasible for a fixed mapping convention.")
    elif summary["candidate_root_cause"] == "bar_materialization_mismatch":
        lines.append("- The bars are readable, but the loaded materialization likely does not correspond to the replay intervals.")
    elif summary["candidate_root_cause"] == "shard_selection_mismatch":
        lines.append("- The loaded shards do not appear to cover the needed replay dates cleanly.")
    elif summary["candidate_root_cause"] == "strict_boundary_filtering":
        lines.append("- The failure is consistent with overly strict endpoint handling.")
    else:
        lines.append("- The alignment failure remains unresolved after the bounded checks.")
    lines.append("")
    lines.append("## Safe Matching Convention Decision")
    lines.append("")
    lines.append(f"- decision: `{summary['safe_matching_convention_decision']}`")
    lines.append("")
    lines.append("## What This Proves")
    lines.append("")
    lines.append("- whether trade and bar sources overlap in time")
    lines.append("- whether exact timestamp matching is viable")
    lines.append("- whether interval overlap is viable")
    lines.append("- whether index mapping is viable")
    lines.append("- whether source construction can be retried safely")
    lines.append("")
    lines.append("## What This Does Not Prove")
    lines.append("")
    lines.append("- no MFE/MAE")
    lines.append("- no giveback classification")
    lines.append("- no exit optimization")
    lines.append("- no strategy improvement")
    lines.append("- no alpha approval")
    lines.append("- no paper/live readiness")
    lines.append("- no production readiness")
    lines.append("")
    lines.append("## Recommended Next Step")
    lines.append("")
    if summary["safe_matching_convention_decision"] in {
        "safe_timestamp_open_time_convention_identified",
        "safe_timestamp_close_time_convention_identified",
        "safe_interval_overlap_convention_identified",
        "safe_index_mapping_convention_identified",
    }:
        lines.append("Recommend a separate preregistered patch to the MFE/MAE source-construction script using the fixed convention, followed by a bounded rerun.")
    elif summary["candidate_root_cause"] == "source_materialization_mismatch":
        lines.append("Recommend a materialization lineage audit, not patching.")
    else:
        lines.append("Recommend stopping source construction until source materialization is clarified.")
    lines.append("")
    lines.append("## Explicitly Not Approved")
    lines.append("")
    lines.append("- No MFE/MAE computation.")
    lines.append("- No giveback classification.")
    lines.append("- No paper trading.")
    lines.append("- No live trading.")
    lines.append("- No production deployment.")
    lines.append("- No additional model classes.")
    lines.append("- No threshold tuning.")
    lines.append("- No feature fishing.")
    lines.append("- No OFI/L2 integration.")
    lines.append("- No full reconstruction.")
    lines.append("- No claims of alpha.")
    lines.append("- No strategy/replay changes.")
    lines.append("- No exit-horizon optimization.")
    lines.append("- No target/stop tuning.")
    lines.append("- No backtest reruns.")
    lines.append("- No row-level artifact persistence.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"Decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Decision Labels")
    lines.append("")
    labels = [
        "c_exhaustion_mfe_mae_source_alignment_diagnostic_created",
        "source_alignment_only",
        "real_trade_log_read",
        "real_bounded_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_mfe_mae_computed",
        "no_giveback_classification",
        "no_source_script_patch",
        "no_row_level_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "no_strategy_backtest_run",
        "no_strategy_replay_changes",
        "no_exit_optimization",
        "no_target_stop_tuning",
        "no_threshold_tuning",
        "no_new_model_trained",
        "full_reconstruction_not_approved",
        "alpha_not_approved",
        "paper_live_blocked",
        "production_not_approved",
        summary["decision"],
    ]
    for label in labels:
        lines.append(f"- `{label}`")

    report = "\n".join(lines) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report)
    return report, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _summary = build_report(trade_log=args.trade_log, bar_dir=args.bar_dir, output_doc=args.output_doc)
    print(args.output_doc)
    _ = report
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
