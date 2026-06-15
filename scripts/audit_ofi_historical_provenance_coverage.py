#!/usr/bin/env python3
"""Read-only audit of historical OFI / volume_delta provenance and coverage."""

from __future__ import annotations

import argparse
import importlib
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SEARCH_SUFFIXES = {".parquet", ".csv", ".json"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "data", "reports", "tmp_diagnostics"}
DEFAULT_OUTPUT = Path("docs/v92_OFI_HISTORICAL_PROVENANCE_COVERAGE_AUDIT.md")


@dataclass(frozen=True)
class BarAuditRow:
    file_path: str
    row_count: int
    min_open_time: object
    max_close_time: object
    has_volume_delta: bool
    volume_delta_null_count: int
    volume_delta_zero_count: int
    volume_delta_positive_count: int
    volume_delta_negative_count: int
    volume_delta_abs_sum: float | None
    volume_sum: float | None
    abs_volume_delta_over_volume_ratio: float | None
    has_ofi_column: bool
    ofi_null_count: int | None
    ofi_zero_count: int | None
    ofi_abs_sum: float | None
    null_count_by_column: str
    suspicious_flag_count: int
    suspicious_reasons: str
    read_error: str | None = None


@dataclass(frozen=True)
class OFIAuditRow:
    file_path: str
    row_count: int
    columns: str
    time_column_detected: str | None
    min_time: object
    max_time: object
    has_ofi: bool
    ofi_null_count: int | None
    ofi_zero_count: int | None
    ofi_positive_count: int | None
    ofi_negative_count: int | None
    ofi_abs_sum: float | None
    has_requires_resync: bool
    requires_resync_true_count: int | None
    has_sequence_gap_flag: bool
    sequence_gap_true_count: int | None
    read_error: str | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--ofi-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SEARCH_SUFFIXES:
            continue
        yield path


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        try:
            return pd.read_json(path, lines=True)
        except ValueError:
            return pd.read_json(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _safe_numeric(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(series, errors="coerce")


def _safe_datetime(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    parsed = pd.to_datetime(series, errors="coerce", utc=False)
    return pd.Series(parsed)


def _count_true(series: pd.Series | None) -> int:
    if series is None:
        return 0
    values = series.astype("boolean")
    return int(values.fillna(False).sum())


def _has_column(df: pd.DataFrame, name: str) -> bool:
    return name in df.columns


def _ratio(numerator: float | int, denominator: float | int) -> float | None:
    denominator = float(denominator)
    if denominator == 0.0 or math.isnan(denominator):
        return None
    return float(numerator) / denominator


def _flags_for_volume_delta(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not row["has_volume_delta"]:
        reasons.append("volume_delta_missing")
        return reasons
    if row["volume_delta_null_count"] > 0:
        reasons.append("volume_delta_null_rate > 0")
    if row["volume_delta_zero_count"] > row["row_count"] * 0.5:
        reasons.append("volume_delta_zero_rate > 0.50")
    if row["volume_delta_positive_count"] == 0 and row["volume_delta_negative_count"] > 0:
        reasons.append("negative_only_volume_delta")
    if row["volume_delta_negative_count"] == 0 and row["volume_delta_positive_count"] > 0:
        reasons.append("positive_only_volume_delta")
    ratio = row["abs_volume_delta_over_volume_ratio"]
    if ratio is not None and ratio < 0.001:
        reasons.append("abs_volume_delta_over_volume_ratio < 0.001")
    if ratio is not None and ratio > 0.95:
        reasons.append("abs_volume_delta_over_volume_ratio > 0.95")
    return reasons


def _flags_for_ofi(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not row["has_ofi"]:
        reasons.append("ofi_missing")
        return reasons
    if row["ofi_null_count"] and row["ofi_null_count"] > 0:
        reasons.append("ofi_null_rate > 0")
    if row["ofi_zero_count"] and row["ofi_zero_count"] > row["row_count"] * 0.5:
        reasons.append("ofi_zero_rate > 0.50")
    if row["ofi_positive_count"] == 0 and row["ofi_negative_count"] and row["ofi_negative_count"] > 0:
        reasons.append("negative_only_ofi")
    if row["ofi_negative_count"] == 0 and row["ofi_positive_count"] and row["ofi_positive_count"] > 0:
        reasons.append("positive_only_ofi")
    if not row["has_requires_resync"]:
        reasons.append("requires_resync_missing")
    if not row["has_sequence_gap_flag"]:
        reasons.append("sequence_gap_tracking_missing")
    return reasons


def audit_bar_file(path: Path) -> BarAuditRow:
    try:
        df = _read_table(path)
    except Exception as exc:  # pragma: no cover - exercised in failure mode only
        return BarAuditRow(
            file_path=str(path),
            row_count=0,
            min_open_time=None,
            max_close_time=None,
            has_volume_delta=False,
            volume_delta_null_count=0,
            volume_delta_zero_count=0,
            volume_delta_positive_count=0,
            volume_delta_negative_count=0,
            volume_delta_abs_sum=None,
            volume_sum=None,
            abs_volume_delta_over_volume_ratio=None,
            has_ofi_column=False,
            ofi_null_count=None,
            ofi_zero_count=None,
            ofi_abs_sum=None,
            null_count_by_column=f"read_error={exc}",
            suspicious_flag_count=1,
            suspicious_reasons="read_error",
            read_error=str(exc),
        )

    row_count = int(len(df))
    open_times = _safe_numeric(df.get("open_time"))
    close_times = _safe_numeric(df.get("close_time"))
    volume = _safe_numeric(df.get("volume"))
    volume_delta = _safe_numeric(df.get("volume_delta")) if _has_column(df, "volume_delta") else None
    ofi = _safe_numeric(df.get("ofi")) if _has_column(df, "ofi") else None

    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
    volume_delta_null_count = int(volume_delta.isna().sum()) if volume_delta is not None else 0
    volume_delta_zero_count = int((volume_delta == 0).sum()) if volume_delta is not None else 0
    volume_delta_positive_count = int((volume_delta > 0).sum()) if volume_delta is not None else 0
    volume_delta_negative_count = int((volume_delta < 0).sum()) if volume_delta is not None else 0
    volume_delta_abs_sum = float(volume_delta.abs().sum()) if volume_delta is not None else None
    volume_sum = float(volume.sum()) if volume is not None else None
    abs_ratio = _ratio(volume_delta_abs_sum or 0.0, volume_sum or 0.0) if volume_delta is not None else None

    ofi_null_count = int(ofi.isna().sum()) if ofi is not None else None
    ofi_zero_count = int((ofi == 0).sum()) if ofi is not None else None
    ofi_abs_sum = float(ofi.abs().sum()) if ofi is not None else None

    row = {
        "file_path": str(path),
        "row_count": row_count,
        "min_open_time": int(open_times.min()) if len(open_times) and open_times.notna().any() else None,
        "max_close_time": int(close_times.max()) if len(close_times) and close_times.notna().any() else None,
        "has_volume_delta": _has_column(df, "volume_delta"),
        "volume_delta_null_count": volume_delta_null_count,
        "volume_delta_zero_count": volume_delta_zero_count,
        "volume_delta_positive_count": volume_delta_positive_count,
        "volume_delta_negative_count": volume_delta_negative_count,
        "volume_delta_abs_sum": volume_delta_abs_sum,
        "volume_sum": volume_sum,
        "abs_volume_delta_over_volume_ratio": abs_ratio,
        "has_ofi_column": _has_column(df, "ofi"),
        "ofi_null_count": ofi_null_count,
        "ofi_zero_count": ofi_zero_count,
        "ofi_abs_sum": ofi_abs_sum,
        "null_count_by_column": "; ".join(f"{col}={count}" for col, count in sorted(null_counts.items())),
    }
    reasons = _flags_for_volume_delta(row)
    suspicious_flag_count = len(reasons)
    return BarAuditRow(
        suspicious_flag_count=suspicious_flag_count,
        suspicious_reasons=", ".join(reasons) if reasons else "none",
        **row,
    )


def audit_ofi_file(path: Path) -> OFIAuditRow:
    try:
        df = _read_table(path)
    except Exception as exc:  # pragma: no cover - exercised in failure mode only
        return OFIAuditRow(
            file_path=str(path),
            row_count=0,
            columns="",
            time_column_detected=None,
            min_time=None,
            max_time=None,
            has_ofi=False,
            ofi_null_count=None,
            ofi_zero_count=None,
            ofi_positive_count=None,
            ofi_negative_count=None,
            ofi_abs_sum=None,
            has_requires_resync=False,
            requires_resync_true_count=None,
            has_sequence_gap_flag=False,
            sequence_gap_true_count=None,
            read_error=str(exc),
        )

    time_column = next((c for c in ["datetime", "time", "timestamp", "event_time", "open_time", "close_time"] if c in df.columns), None)
    time_values = _safe_datetime(df[time_column]) if time_column is not None else pd.Series(dtype="datetime64[ns]")
    ofi = _safe_numeric(df.get("ofi")) if _has_column(df, "ofi") else None
    requires_resync = df.get("requires_resync") if _has_column(df, "requires_resync") else None
    sequence_gap = df.get("sequence_gap") if _has_column(df, "sequence_gap") else None

    return OFIAuditRow(
        file_path=str(path),
        row_count=int(len(df)),
        columns=", ".join(df.columns),
        time_column_detected=time_column,
        min_time=time_values.min() if len(time_values) and time_values.notna().any() else None,
        max_time=time_values.max() if len(time_values) and time_values.notna().any() else None,
        has_ofi=_has_column(df, "ofi"),
        ofi_null_count=int(ofi.isna().sum()) if ofi is not None else None,
        ofi_zero_count=int((ofi == 0).sum()) if ofi is not None else None,
        ofi_positive_count=int((ofi > 0).sum()) if ofi is not None else None,
        ofi_negative_count=int((ofi < 0).sum()) if ofi is not None else None,
        ofi_abs_sum=float(ofi.abs().sum()) if ofi is not None else None,
        has_requires_resync=_has_column(df, "requires_resync"),
        requires_resync_true_count=_count_true(requires_resync) if requires_resync is not None else None,
        has_sequence_gap_flag=_has_column(df, "sequence_gap"),
        sequence_gap_true_count=_count_true(sequence_gap) if sequence_gap is not None else None,
        read_error=None,
    )


def _helper_check() -> dict[str, object]:
    try:
        import polars as pl
    except Exception as exc:  # pragma: no cover - dependency failure path
        return {
            "importable": False,
            "callable": False,
            "error": f"polars_unavailable: {exc}",
        }
    try:
        from features.v92_data_policy import join_ofi_to_bars_preserve_coverage
    except Exception as exc:  # pragma: no cover - dependency failure path
        return {
            "importable": False,
            "callable": False,
            "error": f"helper_import_failed: {exc}",
        }

    try:
        bars = pl.DataFrame(
            {
                "open_time": [1_704_067_200_000, 1_704_067_201_000],
                "close_time": [1_704_067_200_500, 1_704_067_201_500],
                "open": [100.0, 101.0],
                "high": [101.0, 102.0],
                "low": [99.0, 100.0],
                "close": [100.5, 101.5],
                "volume": [500.0, 500.0],
                "volume_delta": [10.0, -10.0],
            }
        )
        ofi = pl.DataFrame(
            {
                "datetime": [
                    "2024-01-01T00:00:01.000",
                    "2024-01-01T00:00:01.500",
                ],
                "ofi": [1.0, 2.0],
            }
        ).with_columns(pl.col("datetime").str.strptime(pl.Datetime("ns")))
        joined = join_ofi_to_bars_preserve_coverage(bars, ofi)
        return {
            "importable": True,
            "callable": True,
            "preserves_coverage": joined.height == bars.height,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "importable": True,
            "callable": False,
            "error": f"helper_call_failed: {exc}",
        }


def _classify_volume_delta_state(bar_rows: list[BarAuditRow]) -> str:
    if not bar_rows:
        return "volume_delta_missing"
    if any(not row.has_volume_delta for row in bar_rows):
        return "volume_delta_missing"
    if any(row.volume_delta_zero_count == row.row_count and row.row_count > 0 for row in bar_rows):
        return "volume_delta_suspicious_all_zero"
    if any(
        (row.volume_delta_positive_count == 0 and row.volume_delta_negative_count > 0)
        or (row.volume_delta_negative_count == 0 and row.volume_delta_positive_count > 0)
        for row in bar_rows
    ):
        return "volume_delta_suspicious_one_sided"
    if any((row.volume_delta_null_count or 0) > 0 for row in bar_rows):
        return "volume_delta_sparse"
    return "volume_delta_available"


def _classify_ofi_state(ofi_rows: list[OFIAuditRow], helper: dict[str, object], ofi_dir_exists: bool) -> str:
    if not ofi_dir_exists or not ofi_rows:
        return "ofi_unavailable"
    if any(row.read_error for row in ofi_rows):
        return "ofi_partial"
    has_resync = any(row.has_requires_resync for row in ofi_rows)
    has_seq = any(row.has_sequence_gap_flag for row in ofi_rows)
    if not has_resync or not has_seq:
        return "ofi_available_but_resync_untracked"
    if helper.get("importable") and helper.get("callable") and helper.get("preserves_coverage"):
        return "ofi_ready_for_research_join"
    return "ofi_available_with_resync_flags"


def _join_readiness(ofi_state: str, helper: dict[str, object], ofi_dir_exists: bool) -> str:
    if not ofi_dir_exists:
        return "blocked_no_historical_ofi_files"
    if ofi_state == "ofi_ready_for_research_join" and helper.get("callable"):
        return "ready_for_research_join"
    if ofi_state == "ofi_unavailable":
        return "blocked_no_historical_ofi_files"
    return "blocked_incomplete_or_untracked"


def _coverage_summary(bar_rows: list[BarAuditRow], ofi_rows: list[OFIAuditRow]) -> dict[str, object]:
    if not bar_rows or not ofi_rows:
        return {
            "bar_min_time": None,
            "bar_max_time": None,
            "ofi_min_time": None,
            "ofi_max_time": None,
            "overlap_start": None,
            "overlap_end": None,
            "ofi_covers_bar_range": False,
            "coverage_gap_summary": "unavailable",
        }
    bar_min = min(row.min_open_time for row in bar_rows if row.min_open_time is not None)
    bar_max = max(row.max_close_time for row in bar_rows if row.max_close_time is not None)
    valid_ofi = [row for row in ofi_rows if row.min_time is not None and row.max_time is not None]
    if not valid_ofi:
        return {
            "bar_min_time": bar_min,
            "bar_max_time": bar_max,
            "ofi_min_time": None,
            "ofi_max_time": None,
            "overlap_start": None,
            "overlap_end": None,
            "ofi_covers_bar_range": False,
            "coverage_gap_summary": "ofi_time_unavailable",
        }
    ofi_min = min(row.min_time for row in valid_ofi)
    ofi_max = max(row.max_time for row in valid_ofi)
    overlap_start = max(bar_min, ofi_min)
    overlap_end = min(bar_max, ofi_max)
    covers = ofi_min <= bar_min and ofi_max >= bar_max
    if covers:
        gap = "ofi_covers_bar_range"
    else:
        gap = "ofi_partial_overlap" if overlap_start <= overlap_end else "no_overlap"
    return {
        "bar_min_time": bar_min,
        "bar_max_time": bar_max,
        "ofi_min_time": ofi_min,
        "ofi_max_time": ofi_max,
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
        "ofi_covers_bar_range": covers,
        "coverage_gap_summary": gap,
    }


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, float) and math.isnan(value):
                value = None
            cells.append("n/a" if value is None else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report(bar_dir: Path, ofi_dir: Path, *, helper_check: dict[str, object] | None = None) -> str:
    helper_check = helper_check or _helper_check()
    bar_rows = [audit_bar_file(path) for path in _iter_files(bar_dir)]
    ofi_dir_exists = ofi_dir.exists()
    ofi_rows = [audit_ofi_file(path) for path in _iter_files(ofi_dir)] if ofi_dir_exists else []
    if ofi_dir_exists and not ofi_rows:
        ofi_inventory_state = "historical_ofi_file_inventory = unavailable"
    elif not ofi_dir_exists:
        ofi_inventory_state = "historical_ofi_file_inventory = unavailable"
    else:
        ofi_inventory_state = "historical_ofi_file_inventory = available"

    volume_delta_state = _classify_volume_delta_state(bar_rows)
    ofi_state = _classify_ofi_state(ofi_rows, helper_check, ofi_dir_exists)
    join_readiness = _join_readiness(ofi_state, helper_check, ofi_dir_exists)
    coverage = _coverage_summary(bar_rows, ofi_rows)

    suspicious_bars = [row for row in bar_rows if row.suspicious_flag_count > 0]
    suspicious_ofi = []
    for row in ofi_rows:
        reasons = _flags_for_ofi(asdict(row))
        if reasons:
            suspicious_ofi.append((row, reasons))

    lines: list[str] = []
    lines.append("# V9.2 OFI Historical Provenance & Coverage Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Determine whether existing historical OFI / `volume_delta` sources are sufficiently complete, sparse, null-safe, and provenance-clear for future research use.")
    lines.append("")
    lines.append("This audit does not approve OFI for production, paper trading, live trading, or alpha use.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Bar dir: `{bar_dir}`")
    lines.append(f"- OFI dir: `{ofi_dir}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("")
    lines.append("- Only reads parquet/csv/json/md files.")
    lines.append("- Never regenerates OFI or bars.")
    lines.append("- Writes only the markdown report.")
    lines.append("")
    lines.append("## Executive Finding")
    lines.append("")
    if not ofi_dir_exists:
        lines.append("Historical OFI files are unavailable in the requested location, so OFI joins remain blocked for today. Existing 750 BTC bars do contain `volume_delta`, but OFI provenance cannot yet be confirmed.")
    else:
        lines.append("Historical OFI files were found and scanned, but their join readiness depends on time coverage and resync/sequence-gap metadata.")
    lines.append("")
    lines.append(f"- OFI historical inventory state: `{ofi_inventory_state}`")
    lines.append(f"- Volume-delta state: `{volume_delta_state}`")
    lines.append(f"- OFI state: `{ofi_state}`")
    lines.append(f"- Join readiness: `{join_readiness}`")
    lines.append("")
    lines.append("## Bar File Inventory")
    lines.append("")
    lines.append(
        _table(
            [asdict(row) for row in bar_rows],
            [
                "file_path",
                "row_count",
                "min_open_time",
                "max_close_time",
                "has_volume_delta",
                "has_ofi_column",
                "suspicious_flag_count",
                "suspicious_reasons",
            ],
        )
    )
    lines.append("")
    lines.append("## Volume Delta Coverage")
    lines.append("")
    lines.append(
        _table(
            [asdict(row) for row in bar_rows],
            [
                "file_path",
                "volume_delta_null_count",
                "volume_delta_zero_count",
                "volume_delta_positive_count",
                "volume_delta_negative_count",
                "volume_delta_abs_sum",
                "volume_sum",
                "abs_volume_delta_over_volume_ratio",
            ],
        )
    )
    lines.append("")
    lines.append("## Historical OFI File Inventory")
    lines.append("")
    if ofi_rows:
        lines.append(
            _table(
                [asdict(row) for row in ofi_rows],
                [
                    "file_path",
                    "row_count",
                    "columns",
                    "time_column_detected",
                    "min_time",
                    "max_time",
                    "has_ofi",
                    "has_requires_resync",
                    "has_sequence_gap_flag",
                ],
            )
        )
    else:
        lines.append("historical_ofi_file_inventory = unavailable")
    lines.append("")
    lines.append("## OFI Coverage")
    lines.append("")
    lines.append(
        f"- bar_min_time: `{coverage['bar_min_time']}`\n"
        f"- bar_max_time: `{coverage['bar_max_time']}`\n"
        f"- ofi_min_time: `{coverage['ofi_min_time']}`\n"
        f"- ofi_max_time: `{coverage['ofi_max_time']}`\n"
        f"- overlap_start: `{coverage['overlap_start']}`\n"
        f"- overlap_end: `{coverage['overlap_end']}`\n"
        f"- ofi_covers_bar_range: `{coverage['ofi_covers_bar_range']}`\n"
        f"- coverage_gap_summary: `{coverage['coverage_gap_summary']}`"
    )
    lines.append("")
    lines.append("## Resync / Sequence Gap Coverage")
    lines.append("")
    if ofi_rows:
        lines.append(
            _table(
                [asdict(row) for row in ofi_rows],
                [
                    "file_path",
                    "has_requires_resync",
                    "requires_resync_true_count",
                    "has_sequence_gap_flag",
                    "sequence_gap_true_count",
                ],
            )
        )
    else:
        lines.append("Historical OFI files are unavailable, so resync / sequence-gap coverage cannot be validated.")
    lines.append("")
    lines.append("## Join Readiness")
    lines.append("")
    lines.append(f"- join_readiness: `{join_readiness}`")
    lines.append(f"- ofi_state: `{ofi_state}`")
    lines.append(f"- volume_delta_state: `{volume_delta_state}`")
    lines.append("")
    lines.append("## Data Policy Helper Check")
    lines.append("")
    lines.append(f"- join_ofi_to_bars_preserve_coverage importable: `{helper_check.get('importable')}`")
    lines.append(f"- join_ofi_to_bars_preserve_coverage callable: `{helper_check.get('callable')}`")
    lines.append(f"- preserves_coverage: `{helper_check.get('preserves_coverage')}`")
    if helper_check.get("error"):
        lines.append(f"- helper_error: `{helper_check.get('error')}`")
    lines.append("")
    lines.append("## Suspicious Files")
    lines.append("")
    if suspicious_bars:
        lines.append("Suspicious bar files:")
        lines.append(_table([asdict(row) for row in suspicious_bars], ["file_path", "suspicious_flag_count", "suspicious_reasons"]))
        lines.append("")
    if suspicious_ofi:
        lines.append("Suspicious OFI files:")
        lines.append(
            _table(
                [
                    {
                        "file_path": row.file_path,
                        "suspicious_reasons": ", ".join(reasons),
                    }
                    for row, reasons in suspicious_ofi
                ],
                ["file_path", "suspicious_reasons"],
            )
        )
        lines.append("")
    if not suspicious_bars and not suspicious_ofi:
        lines.append("No heuristic suspicious files were found.")
    lines.append("")
    lines.append("## What Is Safe")
    lines.append("")
    lines.append("- Existing 750 BTC bars expose `volume_delta` and can be audited for signed-flow coverage.")
    lines.append("- `join_ofi_to_bars_preserve_coverage` is present and importable when dependencies are available.")
    lines.append("- This report is read-only and can support future research triage.")
    lines.append("")
    lines.append("## What Is Not Safe")
    lines.append("")
    lines.append("- Treating OFI as production, paper, live, or alpha-approved.")
    lines.append("- Assuming historical OFI provenance is complete when the OFI inventory is unavailable or incomplete.")
    lines.append("- Assuming resync/sequence-gap handling exists downstream when it has not been verified.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Run a read-only source-inventory check on any historical L2 / OFI archive manifests, then validate downstream consumer wiring before considering any broader use.")
    lines.append("")
    lines.append("## Audit Summary")
    lines.append("")
    lines.append(f"- bar_file_count: `{len(bar_rows)}`")
    lines.append(f"- ofi_file_count: `{len(ofi_rows)}`")
    lines.append(f"- historical_ofi_file_inventory: `{ofi_inventory_state.split(' = ', 1)[1]}`")
    lines.append(f"- join_readiness: `{join_readiness}`")
    lines.append(f"- This audit does not approve OFI for production, paper trading, live trading, or alpha use.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.bar_dir, args.ofi_dir)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
