#!/usr/bin/env python3
"""Targeted raw-to-existing parity audit for existing 750 BTC bars."""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
import zipfile
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

from features.v92_data_policy import discover_aggtrade_archives
from scripts.v92_tier2_cache_builder import build_features_lazy


EXISTING_BAR_RE = "BTCUSDT_tier2_750btc_*.parquet"
RAW_SUFFIX_PREFIX = "BTCUSDT-aggTrades-"
PRICE_TOL = 1e-6
VOLUME_TOL = 1e-6
VWAP_TOL = 1e-6
VOLUME_DELTA_TOL = 1e-6


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
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


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _resolve_raw_archive(raw_dir: Path, file_name: str) -> Path | None:
    suffix = file_name.removeprefix("BTCUSDT_tier2_750btc_").removesuffix(".parquet")
    candidate = raw_dir / f"BTCUSDT-aggTrades-{suffix}.zip"
    if candidate.exists():
        return candidate
    return None


def _extract_single_csv(archive_path: Path, temp_dir: Path) -> Path:
    with zipfile.ZipFile(archive_path, "r") as zf:
        csv_candidates = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if len(csv_candidates) != 1:
            if not csv_candidates:
                raise ValueError(f"No CSV payload found in {archive_path.name}")
            raise ValueError(f"Expected exactly one CSV payload in {archive_path.name}, found {len(csv_candidates)}")
        member = csv_candidates[0]
        zf.extract(member, path=temp_dir)
        return temp_dir / member


def _read_existing_bar(path: Path) -> pl.DataFrame:
    return pl.read_parquet(path).sort("open_time")


def _read_rebuilt_bar(archive_path: Path, *, volume_bucket_size: float = 750.0) -> pl.DataFrame:
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        csv_path = _extract_single_csv(archive_path, temp_dir)
        lazy_df = pl.scan_csv(
            csv_path,
            has_header=False,
            new_columns=[
                "agg_id",
                "price",
                "qty",
                "first_id",
                "last_id",
                "timestamp",
                "is_buyer_maker",
                "is_best_match",
            ],
        )
        rebuilt = build_features_lazy(lazy_df, volume_bucket_size=volume_bucket_size).collect(streaming=True)
        return rebuilt.sort("open_time")


def _to_numpy(series: pl.Series, *, dtype: str | None = None) -> np.ndarray:
    if dtype is not None:
        return series.cast(dtype).to_numpy()
    return series.to_numpy()


def _match_rate(old: pl.Series, new: pl.Series, *, kind: str) -> float:
    if len(old) == 0 or len(new) == 0:
        return 0.0
    if kind == "int":
        old_arr = _to_numpy(old, dtype=pl.Int64)
        new_arr = _to_numpy(new, dtype=pl.Int64)
        return float(np.mean(old_arr == new_arr))
    old_arr = _to_numpy(old, dtype=pl.Float64)
    new_arr = _to_numpy(new, dtype=pl.Float64)
    return float(np.mean(np.isclose(old_arr, new_arr, rtol=1e-8, atol=1e-6, equal_nan=True)))


def _sign_match_rate(old: pl.Series, new: pl.Series) -> float:
    old_arr = _to_numpy(old, dtype=pl.Float64)
    new_arr = _to_numpy(new, dtype=pl.Float64)
    old_sign = np.sign(old_arr)
    new_sign = np.sign(new_arr)
    return float(np.mean(old_sign == new_sign))


def _correlation(old: pl.Series, new: pl.Series) -> float:
    old_arr = _to_numpy(old, dtype=pl.Float64)
    new_arr = _to_numpy(new, dtype=pl.Float64)
    if len(old_arr) < 2 or len(new_arr) < 2:
        return 0.0
    if np.std(old_arr) == 0 or np.std(new_arr) == 0:
        return 1.0 if np.allclose(old_arr, new_arr, rtol=1e-8, atol=1e-6, equal_nan=True) else 0.0
    corr = float(np.corrcoef(old_arr, new_arr)[0, 1])
    if math.isnan(corr):
        return 0.0
    return corr


def _abs_diff_stats(old: pl.Series, new: pl.Series) -> tuple[float, float, float]:
    old_arr = _to_numpy(old, dtype=pl.Float64)
    new_arr = _to_numpy(new, dtype=pl.Float64)
    diffs = np.abs(old_arr - new_arr)
    if diffs.size == 0:
        return 0.0, 0.0, 0.0
    return float(diffs.mean()), float(np.median(diffs)), float(diffs.max())


def _compare_frames(old: pl.DataFrame, rebuilt: pl.DataFrame) -> dict[str, object]:
    common_rows = min(old.height, rebuilt.height)
    old_common = old.head(common_rows)
    rebuilt_common = rebuilt.head(common_rows)

    def col_or_none(df: pl.DataFrame, column: str) -> pl.Series | None:
        return df[column] if column in df.columns else None

    open_time_match_rate = _match_rate(old_common["open_time"], rebuilt_common["open_time"], kind="int") if common_rows else 0.0
    close_time_match_rate = _match_rate(old_common["close_time"], rebuilt_common["close_time"], kind="int") if common_rows else 0.0

    metrics: dict[str, object] = {
        "common_comparable_rows": common_rows,
        "open_time_match_rate": open_time_match_rate,
        "close_time_match_rate": close_time_match_rate,
    }

    for column, tol_name in [
        ("open", "price"),
        ("high", "price"),
        ("low", "price"),
        ("close", "price"),
        ("volume", "volume"),
        ("vwap", "vwap"),
        ("trade_count", "int"),
    ]:
        old_series = col_or_none(old_common, column)
        rebuilt_series = col_or_none(rebuilt_common, column)
        if old_series is None or rebuilt_series is None:
            metrics[f"{column}_match_rate"] = 0.0
            continue
        if tol_name == "int":
            metrics[f"{column}_match_rate"] = _match_rate(old_series, rebuilt_series, kind="int")
        else:
            metrics[f"{column}_match_rate"] = _match_rate(old_series, rebuilt_series, kind="float")

    volume_delta_old = old_common["volume_delta"] if "volume_delta" in old_common.columns else None
    volume_delta_new = rebuilt_common["volume_delta"] if "volume_delta" in rebuilt_common.columns else None
    if volume_delta_old is not None and volume_delta_new is not None and common_rows:
        volume_delta_exact = _match_rate(volume_delta_old, volume_delta_new, kind="float")
        volume_delta_sign = _sign_match_rate(volume_delta_old, volume_delta_new)
        volume_delta_corr = _correlation(volume_delta_old, volume_delta_new)
        mean_abs_diff, median_abs_diff, max_abs_diff = _abs_diff_stats(volume_delta_old, volume_delta_new)
    else:
        volume_delta_exact = 0.0
        volume_delta_sign = 0.0
        volume_delta_corr = 0.0
        mean_abs_diff = 0.0
        median_abs_diff = 0.0
        max_abs_diff = 0.0

    old_volume_delta_sum = float(old["volume_delta"].sum()) if "volume_delta" in old.columns else 0.0
    rebuilt_volume_delta_sum = float(rebuilt["volume_delta"].sum()) if "volume_delta" in rebuilt.columns else 0.0
    old_volume_sum = float(old["volume"].sum()) if "volume" in old.columns else 0.0
    rebuilt_volume_sum = float(rebuilt["volume"].sum()) if "volume" in rebuilt.columns else 0.0
    old_volume_delta_abs_over_volume_ratio = _safe_ratio(abs(old_volume_delta_sum), old_volume_sum)
    rebuilt_volume_delta_abs_over_volume_ratio = _safe_ratio(abs(rebuilt_volume_delta_sum), rebuilt_volume_sum)
    old_positive_rate = float((old["volume_delta"] > 0).mean()) if "volume_delta" in old.columns and old.height else 0.0
    rebuilt_positive_rate = float((rebuilt["volume_delta"] > 0).mean()) if "volume_delta" in rebuilt.columns and rebuilt.height else 0.0
    old_negative_rate = float((old["volume_delta"] < 0).mean()) if "volume_delta" in old.columns and old.height else 0.0
    rebuilt_negative_rate = float((rebuilt["volume_delta"] < 0).mean()) if "volume_delta" in rebuilt.columns and rebuilt.height else 0.0

    metrics.update(
        {
            "volume_delta_exact_match_rate": volume_delta_exact,
            "volume_delta_sign_match_rate": volume_delta_sign,
            "volume_delta_correlation": volume_delta_corr,
            "volume_delta_mean_abs_diff": mean_abs_diff,
            "volume_delta_median_abs_diff": median_abs_diff,
            "volume_delta_max_abs_diff": max_abs_diff,
            "old_volume_delta_sum": old_volume_delta_sum,
            "rebuilt_volume_delta_sum": rebuilt_volume_delta_sum,
            "old_volume_delta_abs_over_volume_ratio": old_volume_delta_abs_over_volume_ratio,
            "rebuilt_volume_delta_abs_over_volume_ratio": rebuilt_volume_delta_abs_over_volume_ratio,
            "old_positive_rate": old_positive_rate,
            "rebuilt_positive_rate": rebuilt_positive_rate,
            "old_negative_rate": old_negative_rate,
            "rebuilt_negative_rate": rebuilt_negative_rate,
        }
    )
    return metrics


def _classify_parity(result: dict[str, object], raw_archive_found: bool) -> tuple[str, list[str], int]:
    reasons: list[str] = []
    parity_flag_count = 0

    if not raw_archive_found:
        reasons.append("raw_archive_missing")
        parity_flag_count += 1
        return "inconclusive_missing_raw", reasons, parity_flag_count

    if abs(int(result["row_count_delta"])) > 1:
        reasons.append("abs(row_count_delta) > 1")
        parity_flag_count += 1
    if float(result["open_time_match_rate"]) < 0.99:
        reasons.append("open_time_match_rate < 0.99")
        parity_flag_count += 1
    if float(result["close_time_match_rate"]) < 0.99:
        reasons.append("close_time_match_rate < 0.99")
        parity_flag_count += 1
    for column in ("open", "high", "low", "close", "volume", "vwap", "trade_count"):
        if float(result[f"{column}_match_rate"]) < 0.99:
            reasons.append(f"{column}_match_rate < 0.99")
            parity_flag_count += 1
    if float(result["volume_delta_sign_match_rate"]) < 0.95:
        reasons.append("volume_delta_sign_match_rate < 0.95")
        parity_flag_count += 1
    if float(result["volume_delta_correlation"]) < 0.95:
        reasons.append("volume_delta_correlation < 0.95")
        parity_flag_count += 1
    if float(result["volume_delta_mean_abs_diff"]) > 5.0:
        reasons.append("volume_delta_mean_abs_diff > 5.0")
        parity_flag_count += 1

    rel_sum_diff = abs(float(result["old_volume_delta_sum"]) - float(result["rebuilt_volume_delta_sum"])) / max(
        abs(float(result["rebuilt_volume_delta_sum"])),
        1.0,
    )
    if rel_sum_diff > 0.10:
        reasons.append("abs(old_volume_delta_sum - rebuilt_volume_delta_sum) / max(abs(rebuilt_volume_delta_sum), 1.0) > 0.10")
        parity_flag_count += 1

    ohlcv_ok = all(float(result[f"{column}_match_rate"]) >= 0.99 for column in ("open", "high", "low", "close", "volume"))
    signed_flow_ok = float(result["volume_delta_sign_match_rate"]) >= 0.95 and float(result["volume_delta_correlation"]) >= 0.95
    if ohlcv_ok and signed_flow_ok:
        return "parity_ok", reasons, parity_flag_count
    if ohlcv_ok and not signed_flow_ok:
        return "signed_flow_mismatch", reasons, parity_flag_count
    return "parity_mismatch", reasons, parity_flag_count


def _load_existing_files(bar_dir: Path) -> list[Path]:
    return sorted(bar_dir.glob(EXISTING_BAR_RE))


def _suspicious_selection(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    suspicious = [row for row in rows if row["suspicious"]]
    top_abs_delta_ratio = sorted(
        rows,
        key=lambda row: abs(float(row["volume_delta_sum"])) / max(float(row["volume_sum"]), 1e-12),
        reverse=True,
    )[:10]
    top_abs_imbalance = sorted(rows, key=lambda row: float(row["volume_delta_abs_over_volume_ratio"]), reverse=True)[:10]
    selected: dict[str, dict[str, object]] = {}
    for row in suspicious + top_abs_delta_ratio + top_abs_imbalance:
        selected[row["file_name"]] = row
    return list(selected.values())


def _file_metrics(path: Path) -> dict[str, object]:
    df = pl.read_parquet(path)
    schema_columns = list(df.columns)
    has_volume_delta = "volume_delta" in df.columns
    has_is_complete = "is_complete" in df.columns
    volume = df["volume"] if "volume" in df.columns else None
    volume_delta = df["volume_delta"] if "volume_delta" in df.columns else None
    open_time = df["open_time"] if "open_time" in df.columns else None
    close_time = df["close_time"] if "close_time" in df.columns else None

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

    null_count_by_column = {col: int(df.select(pl.col(col).null_count()).item()) for col in df.columns}
    inf_count_by_column = {
        col: int(df.select(pl.col(col).is_infinite().sum()).item()) if df.schema[col] in (pl.Float32, pl.Float64) else 0
        for col in df.columns
    }
    required_nulls = {col: null_count_by_column.get(col, 0) for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "volume_delta")}

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
    if any(required_nulls.values()):
        suspicious_reasons.append("required OHLCV nulls")
    if any(count > 0 for count in inf_count_by_column.values()):
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
        "missing_required_columns": [col for col in required_nulls if col not in df.columns],
        "required_nulls": required_nulls,
        "suspicious_reasons": suspicious_reasons,
        "suspicious_flag_count": len(suspicious_reasons),
        "suspicious": bool(suspicious_reasons),
    }


def _aggregate_existing(rows: list[dict[str, object]]) -> dict[str, object]:
    total_positive = int(sum(int(row["volume_delta_positive_count"]) for row in rows))
    total_negative = int(sum(int(row["volume_delta_negative_count"]) for row in rows))
    total_zero = int(sum(int(row["volume_delta_zero_count"]) for row in rows))
    total_volume = float(sum(float(row["volume_sum"]) for row in rows))
    total_volume_delta = float(sum(float(row["volume_delta_sum"]) for row in rows if row["has_volume_delta"]))
    return {
        "file_count": len(rows),
        "total_rows": int(sum(int(row["row_count"]) for row in rows)),
        "global_min_open_time": min((row["min_open_time"] for row in rows if row["min_open_time"] is not None), default=None),
        "global_max_close_time": max((row["max_close_time"] for row in rows if row["max_close_time"] is not None), default=None),
        "total_volume": total_volume,
        "total_volume_delta": total_volume_delta,
        "global_volume_delta_positive_rate": _safe_ratio(total_positive, total_positive + total_negative + total_zero),
        "global_volume_delta_negative_rate": _safe_ratio(total_negative, total_positive + total_negative + total_zero),
        "global_volume_delta_zero_rate": _safe_ratio(total_zero, total_positive + total_negative + total_zero),
        "global_volume_delta_abs_over_volume_ratio": _safe_ratio(abs(total_volume_delta), total_volume),
        "suspicious_file_count": int(sum(1 for row in rows if row["suspicious"])),
        "suspicious_file_rate": _safe_ratio(int(sum(1 for row in rows if row["suspicious"])), len(rows)),
    }


def _build_report(selected_rows: list[dict[str, object]], aggregate: dict[str, object], parity_rows: list[dict[str, object]], raw_missing: list[dict[str, object]], bar_dir: Path, raw_dir: Path) -> str:
    lines: list[str] = []
    lines.append("# 750 BTC Raw Rebuild Parity Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This targeted audit checks whether high-risk existing 750 BTC bar outputs rebuild to the same OHLCV and signed-flow values from available raw aggTrades using the hardened builder."
    )
    lines.append(
        "This targeted audit does not prove all historical bars are perfect. It only tests whether high-risk existing bars match a hardened rebuild for available raw archives."
    )
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- Existing bar directory: `{bar_dir}`")
    lines.append(f"- Raw aggTrades directory: `{raw_dir}`")
    lines.append("- Existing 750 BTC parquet outputs only; no regeneration was written back to the bar directory")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "The selected existing files were rebuilt in memory from their matching raw aggTrades ZIP archives using `build_features_lazy(..., volume_bucket_size=750.0)` and compared row-by-row against the existing parquet outputs."
    )
    lines.append(
        "Exact rebuild parity was evaluated with strict tolerances for price, volume, VWAP, and signed flow, and files missing raw archives were recorded separately as inconclusive."
    )
    lines.append("")
    lines.append("## Selected Files")
    lines.append("")
    lines.append(
        "Selection includes all suspicious files from the existing audit plus the top 10 files by absolute `volume_delta_sum / volume_sum` and the top 10 by `volume_delta_abs_over_volume_ratio`, deduplicated."
    )
    lines.append("")
    lines.append(_markdown_table(selected_rows, [
        "file_name",
        "suspicious_flag_count",
        "suspicious_reasons",
        "volume_delta_abs_over_volume_ratio",
        "volume_delta_positive_rate",
        "volume_delta_negative_rate",
    ]))
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
    lines.append("## Per-File Parity Results")
    lines.append("")
    lines.append(_markdown_table(parity_rows, [
        "file_name",
        "raw_archive",
        "raw_archive_found",
        "old_row_count",
        "rebuilt_row_count",
        "row_count_delta",
        "old_min_open_time",
        "rebuilt_min_open_time",
        "old_max_close_time",
        "rebuilt_max_close_time",
        "common_comparable_rows",
        "open_time_match_rate",
        "close_time_match_rate",
        "open_match_rate",
        "high_match_rate",
        "low_match_rate",
        "close_match_rate",
        "volume_match_rate",
        "vwap_match_rate",
        "trade_count_match_rate",
        "volume_delta_exact_match_rate",
        "volume_delta_sign_match_rate",
        "volume_delta_correlation",
        "volume_delta_mean_abs_diff",
        "volume_delta_median_abs_diff",
        "volume_delta_max_abs_diff",
        "old_volume_delta_sum",
        "rebuilt_volume_delta_sum",
        "old_volume_delta_abs_over_volume_ratio",
        "rebuilt_volume_delta_abs_over_volume_ratio",
        "old_positive_rate",
        "rebuilt_positive_rate",
        "old_negative_rate",
        "rebuilt_negative_rate",
        "parity_flag_count",
        "parity_class",
        "parity_reasons",
    ]))
    lines.append("")
    lines.append("## Signed-Flow Parity")
    lines.append("")
    signed_flow_mismatch = [row for row in parity_rows if row["parity_class"] == "signed_flow_mismatch"]
    parity_ok = [row for row in parity_rows if row["parity_class"] == "parity_ok"]
    missing_raw = [row for row in parity_rows if row["parity_class"] == "inconclusive_missing_raw"]
    lines.append(
        f"- `parity_ok`: {len(parity_ok)} files"
    )
    lines.append(
        f"- `signed_flow_mismatch`: {len(signed_flow_mismatch)} files"
    )
    lines.append(
        f"- `inconclusive_missing_raw`: {len(missing_raw)} files"
    )
    lines.append("")
    lines.append("## OHLCV Parity")
    lines.append("")
    lines.append(
        "OHLCV parity is treated as the primary structural check. If OHLCV matches but signed flow diverges, that is strong evidence that the old `is_buyer_maker` handling affected `volume_delta` while leaving the candle shape intact."
    )
    lines.append("")
    lines.append("## Missing Raw Archives")
    lines.append("")
    if raw_missing:
        lines.append(_markdown_table(raw_missing, [
            "file_name",
            "raw_archive",
            "parity_class",
            "parity_reasons",
        ]))
    else:
        lines.append("No selected file was missing a matching raw archive.")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "1. Files that rebuild cleanly for OHLCV and signed flow are consistent with the hardened builder path for the sampled archives."
    )
    lines.append(
        "2. If rebuilt `volume_delta` deviates materially while OHLCV stays aligned, that is evidence the old `is_buyer_maker` parsing risk affected signed flow in the existing bars."
    )
    lines.append(
        "3. Missing raw archives keep the audit inconclusive for those files; the audit cannot claim full-historical proof from a partial sample."
    )
    lines.append(
        "4. The existing C anchor can remain a research baseline only if the sampled high-risk files do not show material signed-flow mismatch. It still should not be treated as production evidence from this audit alone."
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if signed_flow_mismatch:
        decision = "signed_flow_mismatch_detected"
        regen = "full_regeneration_recommended"
    elif missing_raw:
        decision = "inconclusive_missing_raw"
        regen = "full_regeneration_not_yet_required"
    else:
        decision = "parity_ok_for_sample"
        regen = "full_regeneration_not_yet_required"
    lines.append(
        f"Decision: {decision}. Regeneration status: {regen}. This targeted audit does not prove all historical bars are perfect. It only tests whether high-risk existing bars match a hardened rebuild for available raw archives."
    )
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append(
        "Run the same read-only parity check on any additional high-risk files if more raw archives become available, then decide whether a broader historical regeneration is warranted."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bar_dir = args.bar_dir
    raw_dir = args.raw_dir

    all_existing = _load_existing_files(bar_dir)
    existing_metrics = [_file_metrics(path) for path in all_existing]
    aggregate = _aggregate_existing(existing_metrics)
    selected_rows = _suspicious_selection(existing_metrics)

    parity_rows: list[dict[str, object]] = []
    raw_missing_rows: list[dict[str, object]] = []
    for row in selected_rows:
        file_name = row["file_name"]
        raw_archive = _resolve_raw_archive(raw_dir, file_name)
        parity_row: dict[str, object] = {
            "file_name": file_name,
            "raw_archive": raw_archive.name if raw_archive is not None else "raw_archive_missing",
            "raw_archive_found": raw_archive is not None,
            "old_row_count": row["row_count"],
            "rebuilt_row_count": None,
            "row_count_delta": None,
            "old_min_open_time": row["min_open_time"],
            "rebuilt_min_open_time": None,
            "old_max_close_time": row["max_close_time"],
            "rebuilt_max_close_time": None,
            "common_comparable_rows": 0,
            "open_time_match_rate": 0.0,
            "close_time_match_rate": 0.0,
            "open_match_rate": 0.0,
            "high_match_rate": 0.0,
            "low_match_rate": 0.0,
            "close_match_rate": 0.0,
            "volume_match_rate": 0.0,
            "vwap_match_rate": 0.0,
            "trade_count_match_rate": 0.0,
            "volume_delta_exact_match_rate": 0.0,
            "volume_delta_sign_match_rate": 0.0,
            "volume_delta_correlation": 0.0,
            "volume_delta_mean_abs_diff": 0.0,
            "volume_delta_median_abs_diff": 0.0,
            "volume_delta_max_abs_diff": 0.0,
            "old_volume_delta_sum": row["volume_delta_sum"],
            "rebuilt_volume_delta_sum": None,
            "old_volume_delta_abs_over_volume_ratio": row["volume_delta_abs_over_volume_ratio"],
            "rebuilt_volume_delta_abs_over_volume_ratio": None,
            "old_positive_rate": row["volume_delta_positive_rate"],
            "rebuilt_positive_rate": None,
            "old_negative_rate": row["volume_delta_negative_rate"],
            "rebuilt_negative_rate": None,
            "parity_flag_count": 0,
            "parity_reasons": [],
            "parity_class": "inconclusive_missing_raw" if raw_archive is None else None,
        }

        if raw_archive is None:
            parity_row["parity_reasons"] = ["raw_archive_missing"]
            parity_row["parity_flag_count"] = 1
            raw_missing_rows.append(parity_row)
            parity_rows.append(parity_row)
            continue

        try:
            rebuilt = _read_rebuilt_bar(raw_archive, volume_bucket_size=750.0)
            old_df = _read_existing_bar(bar_dir / file_name)
            compare = _compare_frames(old_df, rebuilt)
            parity_row.update(compare)
            parity_row["rebuilt_row_count"] = rebuilt.height
            parity_row["row_count_delta"] = rebuilt.height - old_df.height
            parity_row["rebuilt_min_open_time"] = int(rebuilt["open_time"].min()) if rebuilt.height else None
            parity_row["rebuilt_max_close_time"] = int(rebuilt["close_time"].max()) if rebuilt.height else None
            parity_class, reasons, parity_flag_count = _classify_parity(parity_row, raw_archive_found=True)
            parity_row["parity_class"] = parity_class
            parity_row["parity_reasons"] = reasons
            parity_row["parity_flag_count"] = parity_flag_count
        except Exception as exc:
            parity_row["parity_class"] = "signed_flow_mismatch"
            parity_row["parity_reasons"] = [f"rebuild_failed: {exc}"]
            parity_row["parity_flag_count"] = 1
        parity_rows.append(parity_row)
        if parity_row["parity_class"] == "inconclusive_missing_raw":
            raw_missing_rows.append(parity_row)

    report = _build_report(selected_rows, aggregate, parity_rows, raw_missing_rows, bar_dir, raw_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
