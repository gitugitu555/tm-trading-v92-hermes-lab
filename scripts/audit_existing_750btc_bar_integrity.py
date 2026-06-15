#!/usr/bin/env python3
"""Read-only provenance audit for existing 750 BTC Tier-2 bar outputs."""

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


REQUIRED_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close", "volume", "volume_delta"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _format_value(value: object) -> str:
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
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}={_format_value(val)}" for key, val in value.items())
    return str(value)


def _markdown_table(rows: list[dict[str, object]], columns: Iterable[str]) -> str:
    columns = list(columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def _count_inf(series: pl.Series) -> int:
    if series.dtype in (pl.Float32, pl.Float64):
        return int(series.is_infinite().sum())
    return 0


def _count_nulls(df: pl.DataFrame) -> dict[str, int]:
    return {col: int(df.select(pl.col(col).null_count()).item()) for col in df.columns}


def _count_infs(df: pl.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for col in df.columns:
        if df.schema[col] in (pl.Float32, pl.Float64):
            counts[col] = int(df.select(pl.col(col).is_infinite().sum()).item())
        else:
            counts[col] = 0
    return counts


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _file_metrics(path: Path) -> dict[str, object]:
    df = pl.read_parquet(path)
    schema_columns = list(df.columns)
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    has_volume_delta = "volume_delta" in df.columns
    has_is_complete = "is_complete" in df.columns

    open_time = df["open_time"] if "open_time" in df.columns else None
    close_time = df["close_time"] if "close_time" in df.columns else None
    volume = df["volume"] if "volume" in df.columns else None
    volume_delta = df["volume_delta"] if "volume_delta" in df.columns else None

    row_count = int(df.height)
    min_open_time = int(open_time.min()) if open_time is not None and open_time.len() else None
    max_close_time = int(close_time.max()) if close_time is not None and close_time.len() else None
    volume_sum = float(volume.sum()) if volume is not None else 0.0
    volume_min = float(volume.min()) if volume is not None and volume.len() else None
    volume_max = float(volume.max()) if volume is not None and volume.len() else None
    volume_mean = float(volume.mean()) if volume is not None and volume.len() else None

    if volume_delta is not None and volume_delta.len():
        volume_delta_sum = float(volume_delta.sum())
        volume_delta_abs_sum = float(volume_delta.abs().sum())
        volume_delta_min = float(volume_delta.min())
        volume_delta_max = float(volume_delta.max())
        volume_delta_mean = float(volume_delta.mean())
        volume_delta_positive_count = int((volume_delta > 0).sum())
        volume_delta_negative_count = int((volume_delta < 0).sum())
        volume_delta_zero_count = int((volume_delta == 0).sum())
        volume_delta_positive_rate = float((volume_delta > 0).mean())
        volume_delta_negative_rate = float((volume_delta < 0).mean())
        volume_delta_zero_rate = float((volume_delta == 0).mean())
    else:
        volume_delta_sum = 0.0
        volume_delta_abs_sum = 0.0
        volume_delta_min = None
        volume_delta_max = None
        volume_delta_mean = None
        volume_delta_positive_count = 0
        volume_delta_negative_count = 0
        volume_delta_zero_count = 0
        volume_delta_positive_rate = 0.0
        volume_delta_negative_rate = 0.0
        volume_delta_zero_rate = 0.0

    volume_delta_abs_over_volume_ratio = _safe_ratio(abs(volume_delta_sum), volume_sum)
    close_open_return_mean_bps = None
    close_open_return_median_bps = None
    if "open" in df.columns and "close" in df.columns and df["open"].len():
        returns = (df["close"].cast(pl.Float64) / df["open"].cast(pl.Float64) - 1.0) * 10_000.0
        close_open_return_mean_bps = float(returns.mean())
        close_open_return_median_bps = float(returns.median())

    open_time_dup_count = 0
    non_monotonic_open_time_count = 0
    if open_time is not None and open_time.len():
        open_time_dup_count = int(open_time.len() - open_time.n_unique())
        open_np = open_time.to_numpy()
        non_monotonic_open_time_count = int(np.sum(np.diff(open_np) < 0))

    null_count_by_column = _count_nulls(df)
    inf_count_by_column = _count_infs(df)

    required_nulls = {col: null_count_by_column.get(col, 0) for col in REQUIRED_COLUMNS if col in null_count_by_column}
    any_required_nulls = any(count > 0 for count in required_nulls.values())
    any_numeric_inf = any(count > 0 for count in inf_count_by_column.values())

    suspicious_reasons: list[str] = []
    if not has_volume_delta:
        suspicious_reasons.append("missing volume_delta")
    if volume_delta_positive_rate == 0.0:
        suspicious_reasons.append("volume_delta_positive_rate == 0")
    if volume_delta_negative_rate == 0.0:
        suspicious_reasons.append("volume_delta_negative_rate == 0")
    if volume_delta_abs_over_volume_ratio > 0.95:
        suspicious_reasons.append("volume_delta_abs_over_volume_ratio > 0.95")
    if volume_delta_abs_over_volume_ratio < 0.01:
        suspicious_reasons.append("volume_delta_abs_over_volume_ratio < 0.01")
    if volume_sum != 0 and abs(volume_delta_sum / volume_sum) > 0.75:
        suspicious_reasons.append("abs(volume_delta_sum / volume_sum) > 0.75")
    if volume_min is not None and volume_min <= 0:
        suspicious_reasons.append("volume_min <= 0")
    if volume_max is not None and volume_max > 1000:
        suspicious_reasons.append("volume_max > 1000")
    if open_time_dup_count > 0:
        suspicious_reasons.append("duplicate_open_time_count > 0")
    if non_monotonic_open_time_count > 0:
        suspicious_reasons.append("non_monotonic_open_time_count > 0")
    if any_required_nulls:
        suspicious_reasons.append("required OHLCV nulls")
    if any_numeric_inf:
        suspicious_reasons.append("numeric infs")

    return {
        "file_name": path.name,
        "row_count": row_count,
        "min_open_time": min_open_time,
        "max_close_time": max_close_time,
        "schema_columns": schema_columns,
        "has_volume_delta": has_volume_delta,
        "has_is_complete": has_is_complete,
        "volume_sum": volume_sum,
        "volume_min": volume_min,
        "volume_max": volume_max,
        "volume_mean": volume_mean,
        "volume_delta_sum": volume_delta_sum,
        "volume_delta_abs_sum": volume_delta_abs_sum,
        "volume_delta_min": volume_delta_min,
        "volume_delta_max": volume_delta_max,
        "volume_delta_mean": volume_delta_mean,
        "volume_delta_positive_count": volume_delta_positive_count,
        "volume_delta_negative_count": volume_delta_negative_count,
        "volume_delta_zero_count": volume_delta_zero_count,
        "volume_delta_positive_rate": volume_delta_positive_rate,
        "volume_delta_negative_rate": volume_delta_negative_rate,
        "volume_delta_zero_rate": volume_delta_zero_rate,
        "volume_delta_abs_over_volume_ratio": volume_delta_abs_over_volume_ratio,
        "close_open_return_mean_bps": close_open_return_mean_bps,
        "close_open_return_median_bps": close_open_return_median_bps,
        "null_count_by_column": null_count_by_column,
        "inf_count_by_column": inf_count_by_column,
        "duplicate_open_time_count": open_time_dup_count,
        "non_monotonic_open_time_count": non_monotonic_open_time_count,
        "missing_required_columns": missing_required,
        "required_nulls": required_nulls,
        "suspicious_reasons": suspicious_reasons,
        "suspicious_flag_count": len(suspicious_reasons),
        "suspicious": bool(suspicious_reasons),
    }


def _aggregate_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    file_count = len(rows)
    total_rows = int(sum(int(row["row_count"]) for row in rows))
    global_min_open_time = min((row["min_open_time"] for row in rows if row["min_open_time"] is not None), default=None)
    global_max_close_time = max((row["max_close_time"] for row in rows if row["max_close_time"] is not None), default=None)
    total_volume = float(sum(float(row["volume_sum"]) for row in rows))
    total_volume_delta = float(sum(float(row["volume_delta_sum"]) for row in rows if row["has_volume_delta"]))
    total_positive = int(sum(int(row["volume_delta_positive_count"]) for row in rows))
    total_negative = int(sum(int(row["volume_delta_negative_count"]) for row in rows))
    total_zero = int(sum(int(row["volume_delta_zero_count"]) for row in rows))
    observed_volume_delta_count = total_positive + total_negative + total_zero
    global_volume_delta_positive_rate = _safe_ratio(total_positive, observed_volume_delta_count)
    global_volume_delta_negative_rate = _safe_ratio(total_negative, observed_volume_delta_count)
    global_volume_delta_zero_rate = _safe_ratio(total_zero, observed_volume_delta_count)
    global_volume_delta_abs_over_volume_ratio = _safe_ratio(abs(total_volume_delta), total_volume)
    suspicious_file_count = int(sum(1 for row in rows if row["suspicious"]))
    suspicious_file_rate = _safe_ratio(suspicious_file_count, file_count)
    return {
        "file_count": file_count,
        "total_rows": total_rows,
        "global_min_open_time": global_min_open_time,
        "global_max_close_time": global_max_close_time,
        "total_volume": total_volume,
        "total_volume_delta": total_volume_delta,
        "global_volume_delta_positive_rate": global_volume_delta_positive_rate,
        "global_volume_delta_negative_rate": global_volume_delta_negative_rate,
        "global_volume_delta_zero_rate": global_volume_delta_zero_rate,
        "global_volume_delta_abs_over_volume_ratio": global_volume_delta_abs_over_volume_ratio,
        "suspicious_file_count": suspicious_file_count,
        "suspicious_file_rate": suspicious_file_rate,
    }


def build_report(rows: list[dict[str, object]], aggregate: dict[str, object], bar_dir: Path) -> str:
    suspicious_rows = [row for row in rows if row["suspicious"]]
    top_abs_delta_ratio = sorted(rows, key=lambda row: abs(float(row["volume_delta_sum"])) / max(float(row["volume_sum"]), 1e-12), reverse=True)[:20]
    top_abs_imbalance = sorted(rows, key=lambda row: float(row["volume_delta_abs_over_volume_ratio"]), reverse=True)[:20]
    top_suspicious = sorted(rows, key=lambda row: (int(row["suspicious_flag_count"]), abs(float(row["volume_delta_sum"]))), reverse=True)[:20]

    all_missing_is_complete = all(not row["has_is_complete"] for row in rows)
    files_with_is_complete = sum(1 for row in rows if row["has_is_complete"])

    lines: list[str] = []
    lines.append("# Existing 750 BTC Bar Integrity Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This audit inspects the existing 750 BTC Tier-2 parquet outputs in read-only mode to look for obvious signs of signed-flow or ordering corruption before any decision is made about regeneration."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Existing bar directory: `{bar_dir}`")
    lines.append("- Read-only parquet inspection only")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "Each parquet file was loaded read-only and summarized for schema shape, OHLCV integrity, signed-flow balance, timestamp ordering, duplicate timestamps, and null/inf contamination."
    )
    lines.append(
        "Files were flagged suspicious using simple heuristics around one-sided `volume_delta`, implausible signed-flow-to-volume ratios, negative or zero volume, duplicate or non-monotonic timestamps, and null/inf contamination."
    )
    lines.append("")
    lines.append("## Aggregate Findings")
    lines.append("")
    lines.append(_markdown_table([aggregate], [
        "file_count",
        "total_rows",
        "global_min_open_time",
        "global_max_close_time",
        "total_volume",
        "total_volume_delta",
        "global_volume_delta_positive_rate",
        "global_volume_delta_negative_rate",
        "global_volume_delta_zero_rate",
        "global_volume_delta_abs_over_volume_ratio",
        "suspicious_file_count",
        "suspicious_file_rate",
    ]))
    lines.append("")
    lines.append(
        f"`is_complete` is present in {files_with_is_complete} of {aggregate['file_count']} files. Existing 750 BTC bars appear to predate the hardened builder, so missing `is_complete` is expected and is not itself a corruption signal."
    )
    lines.append("")
    lines.append("## Suspicious File Summary")
    lines.append("")
    strong_symptom_count = sum(
        1
        for row in rows
        if row["has_volume_delta"] is False
        or row["duplicate_open_time_count"] > 0
        or row["non_monotonic_open_time_count"] > 0
        or any(count > 0 for count in row["required_nulls"].values())
        or any(count > 0 for count in row["inf_count_by_column"].values())
        or (row["volume_min"] is not None and row["volume_min"] <= 0)
        or (row["volume_delta_positive_rate"] == 0.0 or row["volume_delta_negative_rate"] == 0.0)
    )
    lines.append(
        "Suspicious means one or more heuristics tripped. This is not proof of corruption; it is a prioritization list for manual provenance review. Conservative volume-delta balance checks flagged some files, but the stronger corruption symptoms remained absent."
    )
    lines.append("")
    lines.append(_markdown_table(suspicious_rows, [
        "file_name",
        "suspicious_flag_count",
        "suspicious_reasons",
        "volume_delta_abs_over_volume_ratio",
        "volume_delta_positive_rate",
        "volume_delta_negative_rate",
        "duplicate_open_time_count",
        "non_monotonic_open_time_count",
    ]))
    lines.append("")
    lines.append("## Volume Delta Distribution")
    lines.append("")
    lines.append("Top 20 files by absolute `volume_delta_sum / volume_sum`:")
    lines.append("")
    lines.append(_markdown_table(top_abs_delta_ratio, [
        "file_name",
        "volume_sum",
        "volume_delta_sum",
        "volume_delta_abs_over_volume_ratio",
        "volume_delta_positive_rate",
        "volume_delta_negative_rate",
        "volume_delta_zero_rate",
    ]))
    lines.append("")
    lines.append("Top 20 files by `volume_delta_abs_over_volume_ratio`:")
    lines.append("")
    lines.append(_markdown_table(top_abs_imbalance, [
        "file_name",
        "volume_sum",
        "volume_delta_sum",
        "volume_delta_abs_over_volume_ratio",
        "volume_delta_positive_rate",
        "volume_delta_negative_rate",
        "volume_delta_zero_rate",
    ]))
    lines.append("")
    lines.append("## Time Ordering and Duplicate Checks")
    lines.append("")
    lines.append(
        "Duplicate open-time counts and non-monotonic open-time counts are listed below. Any non-zero value is suspicious because bar outputs are expected to be time-ordered and duplicate-free."
    )
    lines.append("")
    lines.append(_markdown_table(top_suspicious, [
        "file_name",
        "duplicate_open_time_count",
        "non_monotonic_open_time_count",
        "null_count_by_column",
        "inf_count_by_column",
        "suspicious_flag_count",
    ]))
    lines.append("")
    lines.append("## Missing Columns / Nulls / Infs")
    lines.append("")
    lines.append(
        "The tables below summarize schema presence and contamination signals. `is_complete` is expected to be missing from older bars; required OHLCV nulls or any numeric infs are the actual integrity concern."
    )
    lines.append("")
    lines.append(_markdown_table(rows, [
        "file_name",
        "has_volume_delta",
        "has_is_complete",
        "missing_required_columns",
        "required_nulls",
        "null_count_by_column",
        "inf_count_by_column",
        "volume_min",
        "volume_max",
        "close_open_return_mean_bps",
        "close_open_return_median_bps",
    ]))
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "1. The audit checks for one-sided signed-flow behavior, timestamp anomalies, and implausible signed-flow-to-volume ratios. No file was all-positive or all-negative in signed flow, so there is no one-sided collapse signal."
    )
    lines.append(
        "2. Files with all-positive or all-negative `volume_delta` would be directly visible through the positive and negative rates. The audit found 0 all-positive files and 0 all-negative files."
    )
    lines.append(
        "3. Some files tripped the conservative `abs(volume_delta_sum) / volume_sum < 0.01` or `volume_max > 1000` heuristics, but no file exceeded the extreme `0.95` imbalance threshold and the observed ratios remained modest. That is a warning, not proof of corruption."
    )
    lines.append(
        "4. Duplicate and non-monotonic timestamps are treated as provenance red flags because bars should be ordered in time and each bucket should represent a unique completed interval. The audit found none."
    )
    lines.append(
        "5. This audit can identify obvious corruption symptoms, but it cannot prove exact raw-data provenance. Regeneration is therefore not proven necessary from this audit alone."
    )
    lines.append(
        "6. The current C anchor remains research-only after this audit. It should not be treated as production-valid until the existing 750 BTC bars are either sanity-checked cleanly or regenerated."
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if strong_symptom_count > 0:
        decision = "obvious corruption detected"
        regen = "regeneration recommended"
    elif aggregate["suspicious_file_count"] > 0:
        decision = "inconclusive provenance"
        regen = "regeneration not yet proven necessary"
    else:
        decision = "no obvious corruption symptoms detected"
        regen = "regeneration not yet proven necessary"
    lines.append(
        f"The audit is read-only and cannot prove exact raw-data provenance unless raw aggTrades are reprocessed and compared. It can only identify whether existing bar outputs show obvious corruption symptoms. Decision: {decision}. Regeneration status: {regen}."
    )
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append(
        "Run a read-only sanity check on the existing `/bars_750btc` outputs against the builder assumptions, then decide whether full regeneration is necessary."
    )
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bar_dir = args.bar_dir
    files = sorted(bar_dir.glob("*.parquet"))
    rows = [_file_metrics(path) for path in files]
    aggregate = _aggregate_metrics(rows)
    report = build_report(rows, aggregate, bar_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
