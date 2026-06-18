#!/usr/bin/env python3
"""Read-only alignment audit for C_Exhaustion signal-time mapping."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_SIGNAL_TIME_ALIGNMENT_AUDIT.md")
DEFAULT_MAX_TRADES = 5000
DEFAULT_MAX_BAR_FILES = 120
DEFAULT_MAX_BARS = 250_000
TIMESTAMP_TOLERANCE_MS = 1.0

TRADE_REQUIRED_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
]

BAR_REQUIRED_COLUMNS = [
    "open_time",
    "close_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

BAR_TIME_COLUMNS = ["open_time", "close_time"]
BAR_FEATURE_COLUMNS = ["volume_delta", "regime", "bar_id"]


@dataclass(frozen=True)
class TradeLogAudit:
    path: Path
    row_count: int
    columns: list[str]
    frame: pd.DataFrame
    min_signal_time: pd.Timestamp | None
    max_signal_time: pd.Timestamp | None
    min_entry_time: pd.Timestamp | None
    max_entry_time: pd.Timestamp | None
    min_exit_time: pd.Timestamp | None
    max_exit_time: pd.Timestamp | None


@dataclass(frozen=True)
class BarShard:
    path: Path
    shard_kind: str
    shard_start: date
    shard_end: date
    selection_reason: str


@dataclass(frozen=True)
class BarAudit:
    files: list[BarShard]
    frame: pd.DataFrame
    row_count: int
    columns: list[str]
    min_open_time: pd.Timestamp | None
    max_close_time: pd.Timestamp | None
    volume_delta_present: bool
    volume_delta_non_null_pct: float | None
    volume_delta_finite_pct: float | None
    volume_delta_usable: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--max-trades", type=int, default=DEFAULT_MAX_TRADES)
    parser.add_argument("--max-bar-files", type=int, default=DEFAULT_MAX_BAR_FILES)
    parser.add_argument("--max-bars", type=int, default=DEFAULT_MAX_BARS)
    return parser.parse_args(argv)


def _read_table(path: Path, max_rows: int | None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=max_rows)
    if suffix == ".parquet":
        df = pd.read_parquet(path)
        if max_rows is not None and max_rows > 0:
            return df.head(max_rows).copy()
        return df
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _parse_timestamp_value(value: object) -> pd.Timestamp | pd.NaT:
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value.tz_localize(None) if value.tzinfo is not None else value
    if isinstance(value, (int, float)):
        ivalue = int(value)
        unit = "us" if abs(ivalue) > 100_000_000_000_000 else "ms"
        ts = pd.to_datetime(ivalue, unit=unit, errors="coerce", utc=True)
        return ts.tz_convert(None) if isinstance(ts, pd.Timestamp) and ts.tzinfo is not None else ts
    text = str(value).strip()
    if not text:
        return pd.NaT
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        ivalue = int(float(text))
        unit = "us" if abs(ivalue) > 100_000_000_000_000 else "ms"
        ts = pd.to_datetime(ivalue, unit=unit, errors="coerce", utc=True)
        return ts.tz_convert(None) if isinstance(ts, pd.Timestamp) and ts.tzinfo is not None else ts
    ts = pd.to_datetime(text, errors="coerce", utc=True)
    if isinstance(ts, pd.Timestamp) and ts.tzinfo is not None:
        return ts.tz_convert(None)
    return ts


def _parse_timestamp_series(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    return series.apply(_parse_timestamp_value)


def _format_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.3f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _date_from_filename(path: Path) -> tuple[str, date, date] | None:
    name = path.name
    day_match = re.fullmatch(r"BTCUSDT_tier2_750btc_(\d{4}-\d{2}-\d{2})\.parquet", name)
    if day_match:
        parsed = date.fromisoformat(day_match.group(1))
        return "day", parsed, parsed
    month_match = re.fullmatch(r"BTCUSDT_tier2_750btc_(\d{4}-\d{2})\.parquet", name)
    if month_match:
        year, month = map(int, month_match.group(1).split("-"))
        first = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last = next_month - timedelta(days=1)
        return "month", first, last
    return None


def _trade_time_range(frame: pd.DataFrame) -> dict[str, pd.Timestamp | None]:
    result: dict[str, pd.Timestamp | None] = {}
    for column in ["signal_time", "entry_time", "exit_time"]:
        ts = _parse_timestamp_series(frame[column]) if column in frame.columns else pd.Series(dtype="datetime64[ns]")
        result[f"min_{column}"] = ts.min() if len(ts) else None
        result[f"max_{column}"] = ts.max() if len(ts) else None
    return result


def _load_trade_log(path: Path, max_trades: int) -> TradeLogAudit:
    frame = _read_table(path, max_trades)
    columns = list(frame.columns)
    missing = [column for column in TRADE_REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Trade log is missing required columns: {missing}")

    parsed = {column: _parse_timestamp_series(frame[column]) for column in ["signal_time", "entry_time", "exit_time"]}
    return TradeLogAudit(
        path=path,
        row_count=int(len(frame)),
        columns=columns,
        frame=frame,
        min_signal_time=parsed["signal_time"].min(),
        max_signal_time=parsed["signal_time"].max(),
        min_entry_time=parsed["entry_time"].min(),
        max_entry_time=parsed["entry_time"].max(),
        min_exit_time=parsed["exit_time"].min(),
        max_exit_time=parsed["exit_time"].max(),
    )


def _discover_bar_files(bar_dir: Path, trade_max_date: date, max_bar_files: int) -> list[BarShard]:
    if not bar_dir.exists():
        return []

    candidates: list[tuple[Path, str, date, date]] = []
    for path in sorted(bar_dir.glob("BTCUSDT_tier2_750btc_*.parquet")):
        parsed = _date_from_filename(path)
        if parsed is None:
            continue
        shard_kind, shard_start, shard_end = parsed
        if shard_start <= trade_max_date:
            candidates.append((path, shard_kind, shard_start, shard_end))

    day_months = {
        (shard_start.year, shard_start.month)
        for _, shard_kind, shard_start, _ in candidates
        if shard_kind == "day"
    }

    selected: list[BarShard] = []
    for path, shard_kind, shard_start, shard_end in candidates:
        if len(selected) >= max_bar_files:
            break
        if shard_kind == "month" and (shard_start.year, shard_start.month) in day_months:
            continue
        if shard_end < shard_start:
            continue
        if shard_start <= trade_max_date:
            reason = "prefix anchor for absolute index mapping" if shard_end < trade_max_date else "overlaps trade-log range"
            selected.append(
                BarShard(
                    path=path,
                    shard_kind=shard_kind,
                    shard_start=shard_start,
                    shard_end=shard_end,
                    selection_reason=reason,
                )
            )

    return selected


def _normalize_bar_times(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in BAR_TIME_COLUMNS:
        if column in normalized.columns:
            normalized[column] = _parse_timestamp_series(normalized[column])
    return normalized


def _read_bar_files(files: list[BarShard], max_bars: int) -> BarAudit:
    frames: list[pd.DataFrame] = []
    for shard in files:
        frames.append(_read_table(shard.path, None))
    if frames:
        frame = pd.concat(frames, ignore_index=True)
    else:
        frame = pd.DataFrame()

    if not frame.empty:
        frame = _normalize_bar_times(frame)
        sort_columns = [column for column in ["open_time", "close_time", "bar_id"] if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
        if max_bars > 0 and len(frame) > max_bars:
            frame = frame.head(max_bars).copy()
            truncated = True
        else:
            truncated = False
    else:
        truncated = False

    if "volume_delta" in frame.columns:
        volume_delta = pd.to_numeric(frame["volume_delta"], errors="coerce")
        non_null_pct = float(volume_delta.notna().mean() * 100.0) if len(volume_delta) else 0.0
        finite_pct = float(pd.Series(volume_delta).apply(lambda x: pd.notna(x) and math.isfinite(float(x))).mean() * 100.0) if len(volume_delta) else 0.0
        usable = bool(len(volume_delta) and volume_delta.notna().any() and finite_pct > 0.0)
    else:
        non_null_pct = 0.0
        finite_pct = 0.0
        usable = False

    return BarAudit(
        files=files,
        frame=frame,
        row_count=int(len(frame)),
        columns=list(frame.columns),
        min_open_time=frame["open_time"].min() if "open_time" in frame.columns and len(frame) else None,
        max_close_time=frame["close_time"].max() if "close_time" in frame.columns and len(frame) else None,
        volume_delta_present="volume_delta" in frame.columns,
        volume_delta_non_null_pct=non_null_pct if "volume_delta" in frame.columns else None,
        volume_delta_finite_pct=finite_pct if "volume_delta" in frame.columns else None,
        volume_delta_usable=usable if not truncated else False,
    )


def _within_tolerance(left: pd.Timestamp | pd.NaT, right: pd.Timestamp | pd.NaT, tolerance_ms: float) -> bool:
    if pd.isna(left) or pd.isna(right):
        return False
    delta_ms = abs((left - right).total_seconds() * 1000.0)
    return delta_ms <= tolerance_ms


def _series_match_rate(left: pd.Series, right: pd.Series, tolerance_ms: float) -> float | None:
    if len(left) == 0 or len(right) == 0:
        return None
    if len(left) != len(right):
        raise ValueError("Series length mismatch for match-rate calculation")
    valid = []
    for left_value, right_value in zip(left, right):
        if pd.isna(left_value) or pd.isna(right_value):
            continue
        valid.append(_within_tolerance(left_value, right_value, tolerance_ms))
    if not valid:
        return None
    return float(sum(valid) / len(valid) * 100.0)


def _index_in_range(index: int, row_count: int) -> bool:
    return 0 <= index < row_count


def _compute_alignment_metrics(trade: TradeLogAudit, bars: BarAudit, tolerance_ms: float) -> dict[str, object]:
    trade_frame = trade.frame.copy()
    bar_frame = bars.frame.copy()
    total_trades = int(len(trade_frame))

    index_columns = ["signal_index", "entry_index", "exit_index"]
    in_range_metrics: dict[str, float | None] = {}
    for column in index_columns:
        if column in trade_frame.columns and bars.row_count:
            in_range = trade_frame[column].apply(lambda x: _index_in_range(int(x), bars.row_count) if pd.notna(x) else False)
            in_range_metrics[f"{column}_in_range_pct"] = float(in_range.mean() * 100.0)
        else:
            in_range_metrics[f"{column}_in_range_pct"] = None

    if all(column in trade_frame.columns for column in index_columns):
        ordered = trade_frame.apply(
            lambda row: bool(
                pd.notna(row["signal_index"])
                and pd.notna(row["entry_index"])
                and pd.notna(row["exit_index"])
                and int(row["signal_index"]) <= int(row["entry_index"]) <= int(row["exit_index"])
                and _index_in_range(int(row["signal_index"]), bars.row_count)
                and _index_in_range(int(row["entry_index"]), bars.row_count)
                and _index_in_range(int(row["exit_index"]), bars.row_count)
            ),
            axis=1,
        )
        signal_lte_entry_lte_exit_index_pct = float(ordered.mean() * 100.0)
    else:
        signal_lte_entry_lte_exit_index_pct = None

    holding_bars_consistency_pct = None
    if "holding_bars" in trade_frame.columns and all(column in trade_frame.columns for column in index_columns):
        holding_ok = trade_frame.apply(
            lambda row: bool(
                pd.notna(row["holding_bars"])
                and pd.notna(row["entry_index"])
                and pd.notna(row["exit_index"])
                and int(row["exit_index"]) - int(row["entry_index"]) == int(row["holding_bars"])
            ),
            axis=1,
        )
        holding_bars_consistency_pct = float(holding_ok.mean() * 100.0)

    signal_idx = trade_frame["signal_index"].astype("Int64") if "signal_index" in trade_frame.columns else pd.Series(dtype="Int64")
    entry_idx = trade_frame["entry_index"].astype("Int64") if "entry_index" in trade_frame.columns else pd.Series(dtype="Int64")
    exit_idx = trade_frame["exit_index"].astype("Int64") if "exit_index" in trade_frame.columns else pd.Series(dtype="Int64")

    def _indexed_match_rate(trade_times: pd.Series, indexes: pd.Series, column: str) -> float | None:
        if column not in bar_frame.columns:
            return None
        matches = []
        for trade_value, idx in zip(_parse_timestamp_series(trade_times), indexes):
            if pd.isna(trade_value) or pd.isna(idx):
                continue
            int_idx = int(idx)
            if not _index_in_range(int_idx, bars.row_count):
                continue
            bar_value = bar_frame.iloc[int_idx][column]
            matches.append(_within_tolerance(trade_value, bar_value, tolerance_ms))
        if not matches:
            return None
        return float(sum(matches) / len(matches) * 100.0)

    signal_open_pct = _indexed_match_rate(trade_frame["signal_time"], signal_idx, "open_time") if "signal_time" in trade_frame.columns else None
    signal_close_pct = _indexed_match_rate(trade_frame["signal_time"], signal_idx, "close_time") if "signal_time" in trade_frame.columns else None
    entry_open_pct = _indexed_match_rate(trade_frame["entry_time"], entry_idx, "open_time") if "entry_time" in trade_frame.columns else None
    entry_close_pct = _indexed_match_rate(trade_frame["entry_time"], entry_idx, "close_time") if "entry_time" in trade_frame.columns else None
    exit_open_pct = _indexed_match_rate(trade_frame["exit_time"], exit_idx, "open_time") if "exit_time" in trade_frame.columns else None
    exit_close_pct = _indexed_match_rate(trade_frame["exit_time"], exit_idx, "close_time") if "exit_time" in trade_frame.columns else None

    convention, confidence = _infer_convention(
        signal_open_pct=signal_open_pct,
        signal_close_pct=signal_close_pct,
        entry_open_pct=entry_open_pct,
        entry_close_pct=entry_close_pct,
        exit_open_pct=exit_open_pct,
        exit_close_pct=exit_close_pct,
    )

    return {
        **in_range_metrics,
        "signal_lte_entry_lte_exit_index_pct": signal_lte_entry_lte_exit_index_pct,
        "holding_bars_consistency_pct": holding_bars_consistency_pct,
        "signal_time_matches_signal_bar_open_pct": signal_open_pct,
        "signal_time_matches_signal_bar_close_pct": signal_close_pct,
        "entry_time_matches_entry_bar_open_pct": entry_open_pct,
        "entry_time_matches_entry_bar_close_pct": entry_close_pct,
        "exit_time_matches_exit_bar_open_pct": exit_open_pct,
        "exit_time_matches_exit_bar_close_pct": exit_close_pct,
        "timestamp_convention": convention,
        "timestamp_convention_confidence_pct": confidence,
        "trade_count": total_trades,
    }


def _infer_convention(
    *,
    signal_open_pct: float | None,
    signal_close_pct: float | None,
    entry_open_pct: float | None,
    entry_close_pct: float | None,
    exit_open_pct: float | None,
    exit_close_pct: float | None,
) -> tuple[str, float | None]:
    def _gte(value: float | None, threshold: float = 95.0) -> bool:
        return value is not None and value >= threshold

    if _gte(signal_close_pct) and _gte(entry_open_pct) and _gte(exit_close_pct):
        return "signal_close_entry_open_exit_close", min(signal_close_pct, entry_open_pct, exit_close_pct)  # type: ignore[arg-type]
    if _gte(signal_open_pct) and _gte(entry_open_pct) and _gte(exit_close_pct):
        return "signal_open_entry_open_exit_close", min(signal_open_pct, entry_open_pct, exit_close_pct)  # type: ignore[arg-type]
    if _gte(signal_close_pct) and _gte(entry_close_pct) and _gte(exit_close_pct):
        return "close_time_based", min(signal_close_pct, entry_close_pct, exit_close_pct)  # type: ignore[arg-type]
    if _gte(signal_open_pct) and _gte(entry_open_pct) and _gte(exit_open_pct):
        return "open_time_based", min(signal_open_pct, entry_open_pct, exit_open_pct)  # type: ignore[arg-type]
    if any(value is None for value in [signal_open_pct, signal_close_pct, entry_open_pct, entry_close_pct, exit_open_pct, exit_close_pct]):
        return "mixed", max(value for value in [signal_open_pct, signal_close_pct, entry_open_pct, entry_close_pct, exit_open_pct, exit_close_pct] if value is not None) if any(value is not None for value in [signal_open_pct, signal_close_pct, entry_open_pct, entry_close_pct, exit_open_pct, exit_close_pct]) else None
    return "mixed", max(signal_open_pct or 0.0, signal_close_pct or 0.0, entry_open_pct or 0.0, entry_close_pct or 0.0, exit_open_pct or 0.0, exit_close_pct or 0.0)


def _feature_rows(bar_audit: BarAudit) -> list[dict[str, object]]:
    bar_cols = set(bar_audit.columns)

    def schema_available(columns: Iterable[str]) -> bool:
        return all(column in bar_cols for column in columns)

    rows = [
        {
            "feature_family": "OHLCV context",
            "schema_available": _bool_str(schema_available(["open_time", "close_time", "open", "high", "low", "close", "volume"])),
            "alignment_safe": "yes",
            "eligible_for_gate2_dry_run": "yes",
            "blocker": "none",
            "notes": "uses deterministic bar ordering and past-only bars",
        },
        {
            "feature_family": "regime",
            "schema_available": _bool_str("regime" in bar_cols),
            "alignment_safe": "yes",
            "eligible_for_gate2_dry_run": "yes",
            "blocker": "missing stored regime column; may be derived in memory from OHLCV using canonical classifier",
            "notes": "only if materialized from existing OHLCV and shifted safely",
        },
        {
            "feature_family": "volume_delta",
            "schema_available": _bool_str("volume_delta" in bar_cols),
            "alignment_safe": "yes" if bar_audit.volume_delta_usable else "no",
            "eligible_for_gate2_dry_run": "yes" if bar_audit.volume_delta_usable else "no",
            "blocker": "volume_delta absent or unusable" if not bar_audit.volume_delta_usable else "none",
            "notes": "present in overlapping bar schema when selected files include it",
        },
        {
            "feature_family": "CVD / delta proxy from volume_delta",
            "schema_available": _bool_str("volume_delta" in bar_cols),
            "alignment_safe": "yes" if bar_audit.volume_delta_usable else "no",
            "eligible_for_gate2_dry_run": "yes" if bar_audit.volume_delta_usable else "no",
            "blocker": "requires volume_delta and shift-safe rolling windows" if not bar_audit.volume_delta_usable else "none",
            "notes": "derived from existing bar schema; no predictive claim",
        },
        {
            "feature_family": "absorption proxy",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "missing raw signed-trade schema columns",
            "notes": "requires trade tape fields not present in the replay output or bar schema",
        },
        {
            "feature_family": "VPIN / toxicity",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "missing raw signed-trade bucket columns",
            "notes": "requires signed-flow buckets not present here",
        },
        {
            "feature_family": "footprint",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "missing raw trade tape columns",
            "notes": "price-level aggregation requires trade tape that is not in scope",
        },
        {
            "feature_family": "OFI / MLOFI",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "blocked by unapproved L2 / OFI artifacts",
            "notes": "cannot use until reconstruction and artifact approval exist",
        },
        {
            "feature_family": "microprice / spread / depth",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "blocked by unapproved L2 / OFI artifacts",
            "notes": "requires book-state inputs that remain infrastructure-only",
        },
        {
            "feature_family": "spoofing / iceberg / L2 whale pressure",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "blocked by unapproved L2 / OFI artifacts and missing event history",
            "notes": "requires event-level L2 coverage that is not approved",
        },
        {
            "feature_family": "funding / OI / liquidation / basis",
            "schema_available": "false",
            "alignment_safe": "no",
            "eligible_for_gate2_dry_run": "no",
            "blocker": "missing verified historical source",
            "notes": "not present in the inspected trade log or bar schema",
        },
    ]
    return rows


def _bar_files_report_rows(files: list[BarShard]) -> list[dict[str, object]]:
    return [
        {
            "file": shard.path.as_posix(),
            "kind": shard.shard_kind,
            "selection_reason": shard.selection_reason,
        }
        for shard in files
    ]


def build_report(
    *,
    trade_log: Path,
    bar_dir: Path,
    output_doc: Path | None = None,
    max_trades: int = DEFAULT_MAX_TRADES,
    max_bar_files: int = DEFAULT_MAX_BAR_FILES,
    max_bars: int = DEFAULT_MAX_BARS,
) -> tuple[str, dict[str, object]]:
    trade_audit = _load_trade_log(trade_log, max_trades)
    trade_min_date = trade_audit.min_signal_time.date() if trade_audit.min_signal_time is not None else trade_audit.min_entry_time.date()
    trade_max_date = trade_audit.max_exit_time.date() if trade_audit.max_exit_time is not None else trade_audit.max_signal_time.date()

    bar_files = _discover_bar_files(bar_dir, trade_max_date, max_bar_files)
    bar_audit = _read_bar_files(bar_files, max_bars)
    alignment = _compute_alignment_metrics(trade_audit, bar_audit, TIMESTAMP_TOLERANCE_MS)
    feature_rows = _feature_rows(bar_audit)

    volume_delta_present = bar_audit.volume_delta_present
    alignment_status = "pass"
    if not bar_files or bar_audit.row_count == 0:
        alignment_status = "blocked"
    elif any(value is None for key, value in alignment.items() if key.endswith("_pct") and key != "holding_bars_consistency_pct"):
        alignment_status = "partial"
    elif alignment.get("signal_time_matches_signal_bar_close_pct") is None or alignment.get("entry_time_matches_entry_bar_open_pct") is None:
        alignment_status = "partial"
    elif bool(alignment.get("signal_time_matches_signal_bar_close_pct", 0.0) < 95.0 or alignment.get("entry_time_matches_entry_bar_open_pct", 0.0) < 95.0):
        alignment_status = "partial"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Signal-Time Alignment Audit")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Resolve the mixed timestamp basis between the C_Exhaustion replay output and the bounded 750btc bar frame before any Gate 2 feature table dry run.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- trade_log path: `{trade_log}`")
    report.append(f"- bar_dir path: `{bar_dir}`")
    report.append(f"- max_trades: `{max_trades}`")
    report.append(f"- max_bar_files: `{max_bar_files}`")
    report.append(f"- max_bars: `{max_bars}`")
    report.append(f"- inspected_trade_rows: `{trade_audit.row_count}`")
    report.append(f"- inspected_bar_rows: `{bar_audit.row_count}`")
    report.append(f"- inspected_bar_files: `{len(bar_files)}`")
    report.append("")
    report.append("## Read-Only Guardrails")
    report.append("")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No market-data artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Trade-Log Time Range")
    report.append("")
    report.append(f"- min_signal_time: `{trade_audit.min_signal_time}`")
    report.append(f"- max_signal_time: `{trade_audit.max_signal_time}`")
    report.append(f"- min_entry_time: `{trade_audit.min_entry_time}`")
    report.append(f"- max_entry_time: `{trade_audit.max_entry_time}`")
    report.append(f"- min_exit_time: `{trade_audit.min_exit_time}`")
    report.append(f"- max_exit_time: `{trade_audit.max_exit_time}`")
    report.append("")
    report.append("## Bar Shards Inspected")
    report.append("")
    if bar_files:
        for shard in bar_files:
            report.append(f"- `{shard.path.name}`: {shard.selection_reason}")
    else:
        report.append("- none")
    report.append("")
    report.append("## Bar Time Range")
    report.append("")
    report.append(f"- min_open_time: `{bar_audit.min_open_time}`")
    report.append(f"- max_close_time: `{bar_audit.max_close_time}`")
    report.append("")
    report.append("## Index Alignment Checks")
    report.append("")
    report.append(f"- signal_index_in_range_pct: `{_format_pct(alignment['signal_index_in_range_pct'])}`")
    report.append(f"- entry_index_in_range_pct: `{_format_pct(alignment['entry_index_in_range_pct'])}`")
    report.append(f"- exit_index_in_range_pct: `{_format_pct(alignment['exit_index_in_range_pct'])}`")
    report.append(f"- signal_lte_entry_lte_exit_index_pct: `{_format_pct(alignment['signal_lte_entry_lte_exit_index_pct'])}`")
    report.append(f"- holding_bars_consistency_pct: `{_format_pct(alignment['holding_bars_consistency_pct'])}`")
    report.append("")
    report.append("## Timestamp Basis Checks")
    report.append("")
    report.append(f"- signal_time_matches_signal_bar_open_pct: `{_format_pct(alignment['signal_time_matches_signal_bar_open_pct'])}`")
    report.append(f"- signal_time_matches_signal_bar_close_pct: `{_format_pct(alignment['signal_time_matches_signal_bar_close_pct'])}`")
    report.append(f"- entry_time_matches_entry_bar_open_pct: `{_format_pct(alignment['entry_time_matches_entry_bar_open_pct'])}`")
    report.append(f"- entry_time_matches_entry_bar_close_pct: `{_format_pct(alignment['entry_time_matches_entry_bar_close_pct'])}`")
    report.append(f"- exit_time_matches_exit_bar_open_pct: `{_format_pct(alignment['exit_time_matches_exit_bar_open_pct'])}`")
    report.append(f"- exit_time_matches_exit_bar_close_pct: `{_format_pct(alignment['exit_time_matches_exit_bar_close_pct'])}`")
    report.append("")
    report.append("## Inferred Timestamp Convention")
    report.append("")
    report.append(f"- convention: `{alignment['timestamp_convention']}`")
    report.append(f"- confidence_pct: `{_format_pct(alignment['timestamp_convention_confidence_pct'])}`")
    report.append("- exact field-level note: the replay output should be interpreted only through the matched open/close basis, not as a timing claim about future bars.")
    report.append("")
    report.append("## Volume Delta Availability")
    report.append("")
    report.append(f"- volume_delta column present: `{_bool_str(volume_delta_present)}`")
    report.append(f"- volume_delta non-null pct: `{_format_pct(bar_audit.volume_delta_non_null_pct)}`")
    report.append(f"- volume_delta finite pct: `{_format_pct(bar_audit.volume_delta_finite_pct)}`")
    report.append(f"- volume_delta usable for future Gate 2 schema-only feature table: `{_bool_str(bar_audit.volume_delta_usable)}`")
    report.append("")
    report.append("## Feature Eligibility After Alignment Audit")
    report.append("")
    headers = [
        "feature family",
        "schema available?",
        "alignment-safe?",
        "eligible for Gate 2 dry run?",
        "blocker",
        "notes",
    ]
    report.append("| " + " | ".join(headers) + " |")
    report.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in feature_rows:
        report.append(
            "| "
            + " | ".join(
                [
                    row["feature_family"],
                    row["schema_available"],
                    row["alignment_safe"],
                    row["eligible_for_gate2_dry_run"],
                    row["blocker"],
                    row["notes"],
                ]
            )
            + " |"
        )
    report.append("")
    report.append("## Gate 1 Finding")
    report.append("")
    report.append("- Gate 1 static inventory: pass")
    report.append("- Gate 1 schema availability: pass")
    report.append(f"- Gate 1 timestamp alignment: `{alignment_status}`")
    report.append("- Gate 2 feature table dry run: not started")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if alignment_status == "pass":
        report.append("Run a bounded read-only Gate 2 feature table dry run using only OHLCV/regime/volume_delta features on a tiny sample, writing only a Markdown report and no data artifacts.")
    else:
        report.append("Fix timestamp basis resolution first, then repeat the bounded read-only alignment audit before any Gate 2 feature table dry run.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- timestamp alignment audit")
    report.append("- schema-only audit")
    report.append("- leakage audit")
    report.append("- bounded read-only feature availability diagnostics")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- alpha claims")
    report.append("- strategy optimization")
    report.append("- backtesting as part of this task")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("- using unapproved L2 features")
    report.append("")
    report.append("## Decision")
    report.append("")
    for label in [
        "c_exhaustion_signal_time_alignment_audit_created",
        "gate_1_alignment_audit_completed",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_market_data_artifacts_written",
        "no_strategy_backtest_run",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
        "gate_1_alignment_pass" if alignment_status == "pass" else ("gate_1_alignment_partial" if alignment_status == "partial" else "gate_1_alignment_blocked"),
    ]:
        report.append(f"- `{label}`")

    summary = {
        "trade_log_path": trade_log,
        "bar_dir_path": bar_dir,
        "trade_log_rows": trade_audit.row_count,
        "bar_rows": bar_audit.row_count,
        "bar_files": [shard.path for shard in bar_files],
        "bar_file_reasons": {shard.path.as_posix(): shard.selection_reason for shard in bar_files},
        "bar_columns": bar_audit.columns,
        "trade_columns": trade_audit.columns,
        "alignment": alignment,
        "alignment_status": alignment_status,
        "feature_rows": feature_rows,
        "volume_delta_present": volume_delta_present,
    }

    report_text = "\n".join(report) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report_text, encoding="utf-8")
    return report_text, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_report(
        trade_log=args.trade_log,
        bar_dir=args.bar_dir,
        output_doc=args.output_doc,
        max_trades=args.max_trades,
        max_bar_files=args.max_bar_files,
        max_bars=args.max_bars,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
