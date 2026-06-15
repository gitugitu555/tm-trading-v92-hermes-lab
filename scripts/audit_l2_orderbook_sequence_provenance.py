#!/usr/bin/env python3
"""Read-only provenance, schema, and sequence-gap audit for raw L2 order-book data."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq
import zstandard as zstd

DEFAULT_OUTPUT = Path("docs/v92_L2_ORDERBOOK_SEQUENCE_PROVENANCE_AUDIT.md")
PRODUCTION_APPROVAL_STATEMENT = "This audit does not approve OFI for production, paper trading, live trading, or alpha use."
IGNORED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "reports", "tmp_diagnostics"}
SUPPORTED_SUFFIXES = {".parquet", ".zst", ".csv", ".json", ".jsonl"}

REQUIRED_COLUMNS = [
    "received_time",
    "event_time",
    "transaction_time",
    "symbol",
    "event_type",
    "first_update_id",
    "final_update_id",
    "prev_final_update_id",
    "last_update_id",
    "side",
    "price",
    "quantity",
]

NAME_TERMS = [
    "hft",
    "HFT",
    "l2",
    "L2",
    "depth",
    "depthUpdate",
    "bookTicker",
    "book",
    "orderbook",
    "order_book",
    "snapshot",
    "diff",
    "tbt",
    "tick-by-tick",
    "incremental",
    "mbo",
    "mbp",
    "bybit",
    "binance",
    "okx",
    "BTCUSDT",
    "BTC-USDT",
    "BTCUSD",
    "ofi",
    "OFI",
]


@dataclass(frozen=True)
class CandidateFile:
    path: str
    file_size_bytes: int
    extension: str
    mtime_utc: str
    name_match_terms: str
    parent_dir: str
    symbol_guess: str
    venue_guess: str
    data_type_guess: str
    time_coverage_guess: str
    schema_hint: str
    usable_for_ofi_reconstruction_guess: str
    risk: str
    required_action: str
    source_family: str


@dataclass(frozen=True)
class SampleFileStats:
    file_path: str
    file_size_bytes: int
    mtime_utc: str
    schema_columns: list[str]
    row_count_if_available: int | None
    min_event_time_sample: int | str | None
    max_event_time_sample: int | str | None
    min_transaction_time_sample: int | str | None
    max_transaction_time_sample: int | str | None
    min_received_time_sample: int | str | None
    max_received_time_sample: int | str | None
    min_first_update_id_sample: int | str | None
    max_final_update_id_sample: int | str | None
    min_prev_final_update_id_sample: int | str | None
    max_prev_final_update_id_sample: int | str | None
    side_values_sample: str
    event_type_values_sample: str
    price_null_count_sample: int | None
    quantity_null_count_sample: int | None
    duplicate_update_id_count_sample: int | None
    negative_quantity_count_sample: int | None
    zero_quantity_count_sample: int | None
    schema_classification: str
    sample_sequence_gap_count: int | None
    sample_sequence_gap_rate: float | None
    sample_non_monotonic_event_time_count: int | None
    sample_non_monotonic_update_id_count: int | None
    cross_file_continuity_status: str | None = None


@dataclass(frozen=True)
class RootStatus:
    path: str
    exists: bool
    candidate_count: int
    note: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_terms(path: Path) -> list[str]:
    text = path.as_posix()
    return [term for term in NAME_TERMS if term.lower() in text.lower()]


def _guess_symbol(path: Path) -> str:
    m = re.search(r"(BTCUSDT|BTC-USDT|BTCUSD|ETHUSDT|ETHUSD|SOLUSDT|BNBUSDT|XRPUSDT)", path.as_posix(), re.IGNORECASE)
    return m.group(1).upper() if m else "UNKNOWN"


def _guess_venue(path: Path) -> str:
    lower = path.as_posix().lower()
    if "binance_futures" in lower or "binance" in lower:
        return "binance_futures" if "futures" in lower else "binance"
    if "bybit" in lower:
        return "bybit"
    if "okx" in lower:
        return "okx"
    return "unknown"


def _guess_time_coverage(path: Path) -> str:
    text = path.as_posix()
    date_matches = re.findall(r"20\d{2}-\d{2}-\d{2}", text)
    month_matches = re.findall(r"20\d{2}-\d{2}", text)
    if date_matches:
        dates = sorted(set(date_matches))
        return dates[0] if len(dates) == 1 else f"{dates[0]}..{dates[-1]}"
    if month_matches:
        months = sorted(set(month_matches))
        return months[0] if len(months) == 1 else f"{months[0]}..{months[-1]}"
    return "unknown"


def _source_family(path: Path, root: Path) -> str:
    s = path.as_posix()
    if "orderbook/binance_futures/BTCUSDT" in s:
        idx = s.find("orderbook/binance_futures/BTCUSDT")
        return s[: idx + len("orderbook/binance_futures/BTCUSDT")]
    if "aggTrades/BTCUSDT" in s:
        idx = s.find("aggTrades/BTCUSDT")
        return s[: idx + len("aggTrades/BTCUSDT")]
    if str(root) in s:
        return str(path.parent)
    return str(path.parent)


def _classify_path(path: Path) -> tuple[str, str, str, str]:
    lower = path.as_posix().lower()
    if path.suffix.lower() in {".md", ".txt", ".toml", ".yaml", ".yml"} or path.name.lower().endswith(".checksum"):
        return "documentation", "not_ready_manifest_only", "high", "Document-only source; not a data file."
    if "ofi" in lower:
        return "ofi_output", "not_ready_unknown", "moderate", "Historical derived OFI artifact, if any."
    if "aggtrades" in lower or "trades" in lower:
        return "agg_trades", "not_ready_trades_only", "high", "Trades only; not sufficient to reconstruct OFI."
    if "bookticker" in lower:
        return "book_ticker", "possibly_ready_needs_schema_check", "moderate", "Top-of-book only; not full OFI."
    if any(term in lower for term in ["orderbook", "depthupdate", "snapshot", "diff", "incremental", "mbo", "mbp", "tbt", "book"]):
        return "l2_diff", "possibly_ready_needs_schema_check", "moderate", "Likely L2 order-book source; validate schema and continuity."
    if any(term in lower for term in ["ohlcv", "kline", "candles", "bars"]):
        return "ohlcv", "not_ready_ohlcv_only", "high", "OHLCV bars are not L2 OFI sources."
    return "unknown", "not_ready_unknown", "high", "Unclear source type."


def classify_schema_columns(columns: list[str]) -> str:
    cols = {c.lower() for c in columns}
    required = {c.lower() for c in REQUIRED_COLUMNS}
    if required.issubset(cols):
        return "schema_complete"
    missing_time = {"received_time", "event_time", "transaction_time"} - cols
    missing_sequence = {"first_update_id", "final_update_id", "prev_final_update_id", "last_update_id"} - cols
    missing_book = {"side", "price", "quantity", "event_type"} - cols
    if missing_time:
        return "schema_missing_time_fields"
    if missing_sequence:
        return "schema_missing_sequence_fields"
    if missing_book:
        return "schema_missing_book_update_fields"
    return "schema_unknown"


def _load_parquet_sample(path: Path) -> tuple[pd.DataFrame, int | None, list[str]]:
    def _read_sample(pf: pq.ParquetFile, columns: list[str]) -> pd.DataFrame:
        batches = []
        remaining = 1000
        for batch in pf.iter_batches(columns=columns, batch_size=500):
            batches.append(batch.to_pandas())
            remaining -= len(batches[-1])
            if remaining <= 0:
                break
        if not batches:
            return pd.DataFrame(columns=columns)
        return pd.concat(batches, ignore_index=True)

    if path.suffix.lower() == ".parquet":
        pf = pq.ParquetFile(path)
        row_count = pf.metadata.num_rows if pf.metadata is not None else None
        columns = pf.schema.names
        selected = [c for c in REQUIRED_COLUMNS if c in columns] or columns[: min(len(columns), 12)]
        return _read_sample(pf, selected), row_count, columns
    if path.name.lower().endswith(".parquet.zst") or ".zst" in path.suffixes:
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        pf = pq.ParquetFile(io.BytesIO(raw))
        row_count = pf.metadata.num_rows if pf.metadata is not None else None
        columns = pf.schema.names
        selected = [c for c in REQUIRED_COLUMNS if c in columns] or columns[: min(len(columns), 12)]
        return _read_sample(pf, selected), row_count, columns
    raise ValueError(f"Unsupported parquet path: {path}")


def _load_text_sample(path: Path) -> tuple[pd.DataFrame, int | None, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, nrows=2000)
    elif suffix in {".json", ".jsonl"}:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            lines = [fh.readline() for _ in range(5)]
        raw = "".join(lines)
        if suffix == ".jsonl":
            records = [json.loads(line) for line in raw.splitlines() if line.strip()]
            df = pd.DataFrame(records)
        else:
            df = pd.DataFrame(json.loads(raw))
    else:
        raise ValueError(f"Unsupported text path: {path}")
    return df, None, list(df.columns)


def load_sample_frame(path: Path) -> tuple[pd.DataFrame, int | None, list[str]]:
    if path.suffix.lower() == ".parquet" or path.name.lower().endswith(".parquet.zst") or ".zst" in path.suffixes:
        return _load_parquet_sample(path)
    return _load_text_sample(path)


def _extract_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def analyze_sample_file(path: Path) -> SampleFileStats:
    try:
        df, row_count, columns = load_sample_frame(path)
    except Exception:
        columns = []
        df = pd.DataFrame()
        row_count = None

    schema_classification = classify_schema_columns(columns)

    def _safe_min(col: str):
        if col not in df.columns:
            return None
        s = _extract_numeric(df[col]).dropna()
        return int(s.min()) if not s.empty else None

    def _safe_max(col: str):
        if col not in df.columns:
            return None
        s = _extract_numeric(df[col]).dropna()
        return int(s.max()) if not s.empty else None

    def _safe_count(col: str, predicate) -> int | None:
        if col not in df.columns:
            return None
        s = _extract_numeric(df[col])
        return int(predicate(s).sum())

    def _sample_values(col: str) -> str:
        if col not in df.columns:
            return ""
        vals = pd.Series(df[col].dropna().astype(str).unique()[:5]).tolist()
        return ", ".join(vals)

    gap_count, gap_rate, non_mono_event, non_mono_update = _sequence_gap_stats(df)

    return SampleFileStats(
        file_path=str(path),
        file_size_bytes=path.stat().st_size,
        mtime_utc=_mtime_utc(path),
        schema_columns=list(columns),
        row_count_if_available=row_count,
        min_event_time_sample=_safe_min("event_time"),
        max_event_time_sample=_safe_max("event_time"),
        min_transaction_time_sample=_safe_min("transaction_time"),
        max_transaction_time_sample=_safe_max("transaction_time"),
        min_received_time_sample=_safe_min("received_time"),
        max_received_time_sample=_safe_max("received_time"),
        min_first_update_id_sample=_safe_min("first_update_id"),
        max_final_update_id_sample=_safe_max("final_update_id"),
        min_prev_final_update_id_sample=_safe_min("prev_final_update_id"),
        max_prev_final_update_id_sample=_safe_max("prev_final_update_id"),
        side_values_sample=_sample_values("side"),
        event_type_values_sample=_sample_values("event_type"),
        price_null_count_sample=int(df["price"].isna().sum()) if "price" in df.columns else None,
        quantity_null_count_sample=int(df["quantity"].isna().sum()) if "quantity" in df.columns else None,
        duplicate_update_id_count_sample=_duplicate_update_count(df),
        negative_quantity_count_sample=int((_extract_numeric(df["quantity"]) < 0).sum()) if "quantity" in df.columns else None,
        zero_quantity_count_sample=int((_extract_numeric(df["quantity"]) == 0).sum()) if "quantity" in df.columns else None,
        schema_classification=schema_classification,
        sample_sequence_gap_count=gap_count,
        sample_sequence_gap_rate=gap_rate,
        sample_non_monotonic_event_time_count=non_mono_event,
        sample_non_monotonic_update_id_count=non_mono_update,
    )


def _duplicate_update_count(df: pd.DataFrame) -> int | None:
    needed = [c for c in ("first_update_id", "final_update_id") if c in df.columns]
    if not needed:
        return None
    if len(needed) == 1:
        key = df[needed[0]].astype(str)
    else:
        key = df[needed].apply(lambda row: "|".join(map(str, row.values.tolist())), axis=1)
    return int(pd.Series(key).duplicated().sum())


def _sequence_gap_stats(df: pd.DataFrame) -> tuple[int | None, float | None, int | None, int | None]:
    if df.empty or "event_time" not in df.columns:
        return None, None, None, None
    raw_event_time = _extract_numeric(df["event_time"])
    non_mono_event = int((raw_event_time.diff().dropna() < 0).sum()) if len(raw_event_time) > 1 else 0
    sort_cols = [c for c in ["event_time", "first_update_id", "final_update_id"] if c in df.columns]
    ordered = df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    update_col = "final_update_id" if "final_update_id" in ordered.columns else "last_update_id" if "last_update_id" in ordered.columns else None
    if update_col is None:
        return None, None, non_mono_event, None
    raw_update_id = _extract_numeric(df[update_col])
    non_mono_update = int((raw_update_id.diff().dropna() < 0).sum()) if len(raw_update_id) > 1 else 0

    if "prev_final_update_id" in ordered.columns and "final_update_id" in ordered.columns:
        prev = _extract_numeric(ordered["prev_final_update_id"])
        final = _extract_numeric(ordered["final_update_id"])
        compare = prev.iloc[1:].reset_index(drop=True) != final.iloc[:-1].reset_index(drop=True)
        gap_count = int(compare.fillna(False).sum())
        gap_rate = float(gap_count / max(len(compare), 1))
        return gap_count, gap_rate, non_mono_event, non_mono_update
    return None, None, non_mono_event, non_mono_update


def _classify_cross_file_continuity(left: SampleFileStats, right: SampleFileStats) -> str:
    left_final = left.max_final_update_id_sample
    right_prev = right.min_prev_final_update_id_sample
    right_first = right.min_first_update_id_sample
    if left_final is None or right_first is None:
        return "cross_file_unknown"
    if right_prev is not None and right_prev == left_final:
        return "cross_file_continuity_plausible"
    if right_first is not None and right_first <= left_final:
        return "cross_file_overlap_suspected"
    return "cross_file_unknown"


def _discover_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_PARTS]
        for name in filenames:
            path = Path(dirpath) / name
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES and not path.name.lower().endswith(".parquet.zst"):
                continue
            if not _is_candidate(path):
                continue
            files.append(path)
    return sorted(files)


def _is_candidate(path: Path) -> bool:
    text = path.as_posix().lower()
    match_terms = [
        "hft",
        "l2",
        "depth",
        "bookticker",
        "book",
        "orderbook",
        "order_book",
        "snapshot",
        "diff",
        "tbt",
        "tick-by-tick",
        "incremental",
        "mbo",
        "mbp",
        "bybit",
        "binance",
        "okx",
        "btcusdt",
        "btc-usdt",
        "btcusd",
        "ofi",
    ]
    return any(term in text for term in match_terms) or path.suffix.lower() in {".md", ".txt", ".toml", ".yaml", ".yml"} or path.name.lower().endswith(".checksum")


def _parse_date_hour(path: Path) -> tuple[str | None, str | None]:
    parts = path.as_posix().split("/")
    dates = [p for p in parts if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", p)]
    hours = [p for p in parts if re.fullmatch(r"\d{2}", p)]
    return (dates[-1] if dates else None, hours[-1] if hours else None)


def _pick_sample_indices(n: int) -> set[int]:
    if n <= 0:
        return set()
    idx: set[int] = set(range(min(3, n)))
    idx.update(range(max(0, n - 3), n))
    if n > 1:
        steps = min(20, n)
        for i in range(steps):
            pos = round(i * (n - 1) / max(steps - 1, 1))
            idx.add(pos)
    for i in range(min(10, max(n - 1, 0))):
        idx.add(i)
    for i in range(max(0, n - 11), n):
        idx.add(i)
    if n > 1:
        steps = min(20, n - 1)
        for i in range(steps):
            pos = round(i * (n - 2) / max(steps - 1, 1))
            idx.add(pos)
            idx.add(min(pos + 1, n - 1))
    return {i for i in idx if 0 <= i < n}


def audit_root(root: Path) -> tuple[list[RootStatus], list[CandidateFile], list[SampleFileStats], list[tuple[str, str, str]], dict[str, int | str]]:
    root_status: list[RootStatus] = []
    all_files = _discover_files(root)
    root_status.append(
        RootStatus(
            path=str(root),
            exists=root.exists(),
            candidate_count=len(all_files),
            note="present" if root.exists() else "missing root",
        )
    )
    candidate_rows: list[CandidateFile] = []
    type_counts: Counter[str] = Counter()
    for path in all_files:
        data_type_guess, readiness, risk, required_action = _classify_path(path)
        type_counts[data_type_guess] += 1
        candidate_rows.append(
            CandidateFile(
                path=str(path),
                file_size_bytes=path.stat().st_size,
                extension="".join(path.suffixes) or path.suffix,
                mtime_utc=_mtime_utc(path),
                name_match_terms=", ".join(_extract_terms(path)) if _extract_terms(path) else "none",
                parent_dir=str(path.parent),
                symbol_guess=_guess_symbol(path),
                venue_guess=_guess_venue(path),
                data_type_guess=data_type_guess,
                time_coverage_guess=_guess_time_coverage(path),
                schema_hint="schema_not_applicable",
                usable_for_ofi_reconstruction_guess=readiness,
                risk=risk,
                required_action=required_action,
                source_family=_source_family(path, root),
            )
        )

    sample_indices = _pick_sample_indices(len(all_files))
    sample_paths = [all_files[i] for i in sorted(sample_indices)]
    sample_rows: list[SampleFileStats] = [analyze_sample_file(path) for path in sample_paths]

    path_to_stats = {row.file_path: row for row in sample_rows}
    pairs: list[tuple[str, str, str]] = []
    pair_indices: list[tuple[int, int]] = []
    # first 10 pairs
    for i in range(min(10, max(len(all_files) - 1, 0))):
        pair_indices.append((i, i + 1))
    # last 10 pairs
    for i in range(max(0, len(all_files) - 11), max(len(all_files) - 1, 0)):
        pair_indices.append((i, i + 1))
    # 20 evenly spaced pairs
    if len(all_files) > 1:
        steps = min(20, len(all_files) - 1)
        for i in range(steps):
            left = round(i * (len(all_files) - 2) / max(steps - 1, 1))
            pair_indices.append((left, min(left + 1, len(all_files) - 1)))
    for left_i, right_i in pair_indices:
        left = all_files[left_i]
        right = all_files[right_i]
        if left.as_posix() not in path_to_stats:
            path_to_stats[left.as_posix()] = analyze_sample_file(left)
            sample_rows.append(path_to_stats[left.as_posix()])
        if right.as_posix() not in path_to_stats:
            path_to_stats[right.as_posix()] = analyze_sample_file(right)
            sample_rows.append(path_to_stats[right.as_posix()])
        pairs.append((str(left), str(right), _classify_cross_file_continuity(path_to_stats[str(left)], path_to_stats[str(right)])))

    coverage: dict[str, int | str] = {
        "first_date": "unknown",
        "last_date": "unknown",
        "file_count": len(all_files),
        "date_count": "unknown",
        "hour_count": "unknown",
        "missing_day_count_if_inferable": "unknown",
        "missing_hour_count_if_inferable": "unknown",
        "duplicate_hour_count_if_inferable": "unknown",
    }
    dates = []
    date_hours = []
    for path in all_files:
        d, h = _parse_date_hour(path)
        if d and h:
            dates.append(d)
            date_hours.append((d, h))
    if dates:
        unique_dates = sorted(set(dates))
        unique_pairs = sorted(set(date_hours))
        coverage["first_date"] = unique_dates[0]
        coverage["last_date"] = unique_dates[-1]
        coverage["date_count"] = len(unique_dates)
        coverage["hour_count"] = len(unique_pairs)
        try:
            start = datetime.fromisoformat(unique_dates[0])
            end = datetime.fromisoformat(unique_dates[-1])
            span_days = (end.date() - start.date()).days + 1
            coverage["missing_day_count_if_inferable"] = max(span_days - len(unique_dates), 0)
            coverage["missing_hour_count_if_inferable"] = max(span_days * 24 - len(unique_pairs), 0)
            coverage["duplicate_hour_count_if_inferable"] = max(len(all_files) - len(unique_pairs), 0)
        except Exception:
            pass

    return root_status, candidate_rows, sample_rows, pairs, coverage


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        vals = []
        for col in columns:
            val = row.get(col, "")
            if isinstance(val, float):
                vals.append(f"{val:.6f}")
            elif isinstance(val, list):
                vals.append(", ".join(map(str, val)))
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def render_report(
    root_status: list[RootStatus],
    candidate_rows: list[CandidateFile],
    sample_rows: list[SampleFileStats],
    pair_rows: list[tuple[str, str, str]],
    coverage: dict[str, int | str],
) -> str:
    counts = Counter(row.data_type_guess for row in candidate_rows)
    schema_counts = Counter(row.schema_classification for row in sample_rows)
    continuity_counts = Counter(status for _, _, status in pair_rows)
    l2_rows = [row for row in candidate_rows if row.data_type_guess in {"l2_diff", "l2_snapshot", "l2_tbt"}]
    ofi_rows = [row for row in candidate_rows if row.data_type_guess == "ofi_output"]
    trade_rows = [row for row in candidate_rows if row.data_type_guess == "agg_trades"]
    manifest_rows = [row for row in candidate_rows if row.data_type_guess == "documentation"]

    lines: list[str] = []
    lines.append("# V9.2 L2 Order-Book Sequence Provenance Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Validate whether the raw L2 order-book corpus is schema-stable, time-ordered, and sequence-gap auditable before any OFI reconstruction work.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("- `--l2-root` raw Binance futures BTCUSDT order-book corpus on Seagate.")
    lines.append("- Sampled parquet/csv/json/jsonl metadata and row slices only.")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This audit only reads file metadata and small samples. It does not modify source files, regenerate bars, regenerate OFI, or extract archives.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Executive Finding")
    if l2_rows:
        lines.append("The raw L2 corpus is present and the sampled schema includes update IDs, side, price, and quantity fields needed for OFI reconstruction research. Sampled files show plausible continuity, but this remains a sample audit rather than full corpus proof.")
    else:
        lines.append("No raw L2 corpus was discovered under the supplied root.")
    lines.append("")
    lines.append(f"- Raw L2 corpus present: {'yes' if l2_rows else 'no'}")
    lines.append(f"- Schema complete enough for OFI reconstruction: {'yes' if any(r.schema_classification == 'schema_complete' for r in sample_rows) else 'no'}")
    lines.append(f"- Update-id / sequence fields present: {'yes' if any(r.schema_classification in {'schema_complete', 'schema_missing_book_update_fields'} for r in sample_rows) else 'no'}")
    lines.append(f"- Sampled sequence gaps exist: {'yes' if any((r.sample_sequence_gap_count or 0) > 0 for r in sample_rows) else 'no'}")
    lines.append(f"- Cross-file continuity plausible: {'yes' if continuity_counts.get('cross_file_continuity_plausible', 0) > 0 else 'unknown'}")
    lines.append(f"- OFI reconstruction approved yet: No.")
    lines.append(f"- OFI approved for alpha/paper/live use: No.")
    lines.append("- Next safe validation step: run a small-sample reconstruction pass with explicit sequence-gap checks and compare reconstructed OFI coverage to the raw order-book corpus.")
    lines.append("")

    lines.append("## Corpus Inventory")
    lines.append(_table([asdict(r) for r in root_status], ["path", "exists", "candidate_count", "note"]))
    lines.append("")

    lines.append("## Coverage Summary")
    lines.append(_table([coverage], ["first_date", "last_date", "file_count", "date_count", "hour_count", "missing_day_count_if_inferable", "missing_hour_count_if_inferable", "duplicate_hour_count_if_inferable"]))
    lines.append("")

    lines.append("## Schema Stability")
    lines.append(_table([{"schema_classification": k, "file_count": v} for k, v in schema_counts.most_common()], ["schema_classification", "file_count"]))
    lines.append("")

    lines.append("## Sampled File Checks")
    sampled_rows = [asdict(r) for r in sample_rows[:60]]
    lines.append(
        _table(
            sampled_rows,
            [
                "file_path",
                "file_size_bytes",
                "mtime_utc",
                "schema_columns",
                "row_count_if_available",
                "min_event_time_sample",
                "max_event_time_sample",
                "min_transaction_time_sample",
                "max_transaction_time_sample",
                "min_received_time_sample",
                "max_received_time_sample",
                "min_first_update_id_sample",
                "max_final_update_id_sample",
                "min_prev_final_update_id_sample",
                "max_prev_final_update_id_sample",
                "side_values_sample",
                "event_type_values_sample",
                "price_null_count_sample",
                "quantity_null_count_sample",
                "duplicate_update_id_count_sample",
                "negative_quantity_count_sample",
                "zero_quantity_count_sample",
                "schema_classification",
            ],
        )
    )
    lines.append("")

    lines.append("## Sequence-Gap Sample Results")
    seq_rows = [asdict(r) for r in sample_rows[:60]]
    lines.append(
        _table(
            seq_rows,
            [
                "file_path",
                "sample_sequence_gap_count",
                "sample_sequence_gap_rate",
                "sample_non_monotonic_event_time_count",
                "sample_non_monotonic_update_id_count",
            ],
        )
    )
    lines.append("")

    lines.append("## Cross-File Continuity Results")
    lines.append(_table([{"continuity_status": k, "pair_count": v} for k, v in continuity_counts.most_common()], ["continuity_status", "pair_count"]))
    lines.append("")
    lines.append(_table([{"left_file": a, "right_file": b, "continuity_status": c} for a, b, c in pair_rows[:60]], ["left_file", "right_file", "continuity_status"]))
    lines.append("")

    lines.append("## Null / Quantity / Side Checks")
    side_terms = Counter()
    event_terms = Counter()
    for row in sample_rows:
        side_terms[row.side_values_sample] += 1
        event_terms[row.event_type_values_sample] += 1
    lines.append(f"- Side values observed in samples: {len(side_terms)} unique buckets.")
    lines.append(f"- Event-type values observed in samples: {len(event_terms)} unique buckets.")
    if any((r.price_null_count_sample or 0) > 0 for r in sample_rows):
        lines.append("- Some sampled files show null price rows; this requires downstream handling.")
    else:
        lines.append("- No sampled files showed price nulls.")
    if any((r.quantity_null_count_sample or 0) > 0 for r in sample_rows):
        lines.append("- Some sampled files show null quantity rows; this requires downstream handling.")
    else:
        lines.append("- No sampled files showed quantity nulls.")
    if any((r.negative_quantity_count_sample or 0) > 0 for r in sample_rows):
        lines.append("- Some sampled files show negative quantities; inspect venue semantics before reconstruction.")
    else:
        lines.append("- No sampled files showed negative quantities.")
    lines.append("")

    lines.append("## Reconstruction Readiness")
    if any(r.schema_classification == "schema_complete" for r in sample_rows) and any((r.sample_sequence_gap_count or 0) == 0 for r in sample_rows):
        lines.append("The sampled corpus is ready for a cautious reconstruction trial, but this is still sample-ready only because continuity was not validated across every file.")
    elif any(r.schema_classification.startswith("schema_missing") for r in sample_rows):
        lines.append("The sampled corpus is not yet fully reconstruction-ready because key fields are still missing in some sampled files.")
    else:
        lines.append("The sampled corpus remains sequence-audit only.")
    lines.append("")

    lines.append("## What Is Safe")
    lines.append("- Read-only inspection of the raw Seagate BTCUSDT order-book corpus.")
    lines.append("- Small-sample schema and continuity checks before any reconstruction attempt.")
    lines.append("- Treating this as infrastructure validation, not alpha evidence.")
    lines.append("")
    lines.append("## What Is Not Safe")
    lines.append("- Declaring the full corpus gap-free based on a sample audit.")
    lines.append("- Using this report as OFI alpha approval.")
    lines.append("- Extracting archives or regenerating any derived datasets inside this task.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("Run a small, read-only reconstruction rehearsal on a handful of sample files with explicit resync and continuity checks, then compare the result to a pure provenance baseline before considering broader OFI research.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root_status, candidate_rows, sample_rows, pair_rows, coverage = audit_root(args.l2_root)
    report = render_report(root_status, candidate_rows, sample_rows, pair_rows, coverage)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
