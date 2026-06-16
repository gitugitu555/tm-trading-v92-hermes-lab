#!/usr/bin/env python3
"""Bounded read-only discovery of raw L2 files that may exercise unobserved OFI policy paths."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:  # pragma: no cover - optional dependency path
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    pq = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency path
    import zstandard as zstd
except ImportError:  # pragma: no cover
    zstd = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_UNEXERCISED_POLICY_PATH_DISCOVERY.md")
PRODUCTION_APPROVAL_STATEMENT = "This discovery does not approve OFI for production, paper trading, live trading, or alpha use."
SUPPORTED_SUFFIXES = {".parquet", ".zst", ".csv", ".json", ".jsonl", ".gz"}
REQUIRED_COLUMNS = [
    "symbol",
    "event_time",
    "transaction_time",
    "received_time",
    "event_type",
    "first_update_id",
    "final_update_id",
    "prev_final_update_id",
    "side",
    "price",
    "quantity",
]

KNOWN_EVENT_ORDER_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst"
)
KNOWN_SOURCE_GAP_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst"
)


@dataclass(frozen=True)
class CandidatePreview:
    candidate_file_path: str
    file_date: str | None
    file_hour: str | None
    preview_row_count: int
    preview_packet_count: int
    missing_transaction_time_count: int
    missing_first_update_id_count: int
    missing_prev_final_update_id_count: int
    snapshot_like_row_count: int
    snapshot_like_packet_count: int
    timestamp_non_monotonic_hint_count: int
    event_time_non_monotonic_hint_count: int
    transaction_time_non_monotonic_hint_count: int
    received_time_non_monotonic_hint_count: int
    repeated_final_update_id_hint_count: int
    estimated_source_gap_count: int
    side_mapping_unknown_count: int
    missing_required_column_count: int
    candidate_score: int
    candidate_reasons: tuple[str, ...]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--max-candidate-files", type=int, default=360)
    parser.add_argument("--preview-rows-per-file", type=int, default=25_000)
    parser.add_argument("--max-selected-findings", type=int, default=40)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not rows:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def _file_date(path: Path) -> str | None:
    match = re.search(r"20\d{2}-\d{2}-\d{2}", path.as_posix())
    return match.group(0) if match else None


def _file_hour(path: Path) -> str | None:
    parts = path.parts
    for idx, part in enumerate(parts[:-1]):
        if len(part) == 10 and part[4] == "-" and part[7] == "-" and idx + 1 < len(parts):
            next_part = parts[idx + 1]
            if len(next_part) == 2 and next_part.isdigit():
                return next_part
    return None


def _path_is_2026(path: Path) -> bool:
    return "2026-" in path.as_posix()


def _path_is_month_or_day_boundary(path: Path) -> bool:
    file_date = _file_date(path)
    file_hour = _file_hour(path)
    if file_date is None or file_hour is None:
        return False
    return file_date.endswith("-01") or file_hour in {"00", "23"}


def discover_candidate_files(l2_root: Path, symbol: str) -> list[Path]:
    root = Path(l2_root)
    candidates = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and symbol.upper() in path.name.upper()
        and (path.suffix.lower() in SUPPORTED_SUFFIXES or path.name.lower().endswith(".parquet.zst"))
    ]
    return sorted(candidates, key=lambda p: p.as_posix())


def _dedupe_keep_order(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def _evenly_spaced_subset(paths: list[Path], limit: int) -> list[Path]:
    if not paths or limit <= 0:
        return []
    if len(paths) <= limit:
        return list(paths)
    if limit == 1:
        return [paths[len(paths) // 2]]
    indices = [round(i * (len(paths) - 1) / (limit - 1)) for i in range(limit)]
    return [paths[idx] for idx in indices]


def build_candidate_pool(ordered_files: list[Path], max_candidate_files: int) -> list[Path]:
    if not ordered_files:
        return []

    selected: list[Path] = []

    def include(path: Path | None) -> None:
        if path is None:
            return
        if path in ordered_files and path not in selected:
            selected.append(path)

    for anchor in (KNOWN_EVENT_ORDER_FILE, KNOWN_SOURCE_GAP_FILE):
        include(anchor if anchor.exists() else None)
        if anchor.exists() and anchor in ordered_files:
            idx = ordered_files.index(anchor)
            for offset in (-3, -2, -1, 1, 2, 3):
                neighbor_idx = idx + offset
                if 0 <= neighbor_idx < len(ordered_files):
                    include(ordered_files[neighbor_idx])

    include(ordered_files[0])
    include(ordered_files[-1])

    month_open_files = [path for path in ordered_files if _path_is_month_or_day_boundary(path)]
    for path in _evenly_spaced_subset(month_open_files, min(60, max_candidate_files)):
        include(path)

    year_2026_files = [path for path in ordered_files if _path_is_2026(path)]
    for path in _evenly_spaced_subset(year_2026_files, min(60, max_candidate_files)):
        include(path)

    if len(selected) < max_candidate_files:
        for path in _evenly_spaced_subset(ordered_files, max_candidate_files):
            include(path)
            if len(selected) >= max_candidate_files:
                break

    if len(selected) < max_candidate_files:
        for path in ordered_files:
            include(path)
            if len(selected) >= max_candidate_files:
                break

    return _dedupe_keep_order(selected)[:max_candidate_files]


def _read_parquet_preview(path: Path, preview_rows_per_file: int) -> pd.DataFrame:
    if pq is None or zstd is None:
        raise RuntimeError("pyarrow and zstandard are required for parquet discovery")
    if path.suffix.lower() == ".parquet":
        parquet_file = pq.ParquetFile(path)
    elif path.name.lower().endswith(".parquet.zst"):
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        parquet_file = pq.ParquetFile(io.BytesIO(raw))
    else:
        raise ValueError(f"Unsupported parquet path: {path}")

    batches: list[pd.DataFrame] = []
    rows_remaining = preview_rows_per_file
    for batch in parquet_file.iter_batches(batch_size=min(8192, preview_rows_per_file)):
        if rows_remaining <= 0:
            break
        batch_df = batch.to_pandas()
        if len(batch_df) > rows_remaining:
            batch_df = batch_df.iloc[:rows_remaining].copy()
        batches.append(batch_df)
        rows_remaining -= len(batch_df)
    if not batches:
        return pd.DataFrame()
    return pd.concat(batches, ignore_index=True)


def _read_csv_preview(path: Path, preview_rows_per_file: int) -> pd.DataFrame:
    compression = "gzip" if path.suffix.lower() == ".gz" else None
    return pd.read_csv(path, nrows=preview_rows_per_file, compression=compression)


def _read_json_preview(path: Path, preview_rows_per_file: int) -> pd.DataFrame:
    if path.name.lower().endswith(".jsonl"):
        return pd.read_json(path, lines=True, nrows=preview_rows_per_file)
    return pd.read_json(path).head(preview_rows_per_file)


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in REQUIRED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized["symbol"] = normalized["symbol"].astype("string").str.strip().str.upper()
    normalized["event_type"] = normalized["event_type"].astype("string").str.strip()
    for column in ["event_time", "transaction_time", "received_time", "first_update_id", "final_update_id", "prev_final_update_id"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["price"] = pd.to_numeric(normalized["price"], errors="coerce")
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce")
    normalized["side_text"] = normalized["side"].astype("string").str.strip().str.lower()
    return normalized


def _normalize_side(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        ivalue = int(value)
        if ivalue == 0:
            return "bid"
        if ivalue == 1:
            return "ask"
    text = str(value).strip().lower()
    if text in {"bid", "bids", "b", "buy", "0"}:
        return "bid"
    if text in {"ask", "asks", "a", "sell", "1"}:
        return "ask"
    return None


def _packet_sort_key(packet: dict[str, Any]) -> tuple[Any, ...]:
    transaction_time = packet.get("transaction_time")
    event_time = packet.get("event_time")
    effective_time = transaction_time if pd.notna(transaction_time) and transaction_time is not None else event_time
    return (effective_time, packet.get("final_update_id"), packet.get("event_time"))


def preview_candidate_frame(frame: pd.DataFrame, *, candidate_file_path: str, preview_rows_per_file: int) -> CandidatePreview:
    normalized = _normalize_frame(frame)
    if preview_rows_per_file >= 0:
        normalized = normalized.iloc[:preview_rows_per_file].copy()

    preview_row_count = int(len(normalized))
    missing_required_column_count = sum(1 for column in REQUIRED_COLUMNS if column not in frame.columns)
    missing_transaction_time_count = int(normalized["transaction_time"].isna().sum())
    missing_first_update_id_count = int(normalized["first_update_id"].isna().sum())
    missing_prev_final_update_id_count = int(normalized["prev_final_update_id"].isna().sum())
    snapshot_like_row_count = int((normalized["first_update_id"].isna() | normalized["prev_final_update_id"].isna()).sum())
    side_mapping_unknown_count = int(sum(_normalize_side(value) is None for value in normalized["side"]))

    packet_rows: list[dict[str, Any]] = []
    if preview_row_count > 0 and missing_required_column_count < len(REQUIRED_COLUMNS):
        group_columns = ["symbol", "event_time", "final_update_id", "prev_final_update_id", "event_type"]
        grouped = normalized.groupby(group_columns, dropna=False, sort=False)
        for _, group in grouped:
            first = group.iloc[0]
            packet_rows.append(
                {
                    "symbol": first.get("symbol"),
                    "event_time": first.get("event_time"),
                    "transaction_time": first.get("transaction_time"),
                    "received_time": first.get("received_time"),
                    "first_update_id": first.get("first_update_id"),
                    "final_update_id": first.get("final_update_id"),
                    "prev_final_update_id": first.get("prev_final_update_id"),
                    "snapshot_like": bool(pd.isna(first.get("first_update_id")) or pd.isna(first.get("prev_final_update_id"))),
                    "side_unknown_count": int(sum(_normalize_side(value) is None for value in group["side"])),
                }
            )

    preview_packet_count = len(packet_rows)
    missing_transaction_packet_count = int(sum(pd.isna(packet.get("transaction_time")) for packet in packet_rows))
    snapshot_like_packet_count = int(sum(packet["snapshot_like"] for packet in packet_rows))

    event_time_non_monotonic_hint_count = 0
    transaction_time_non_monotonic_hint_count = 0
    received_time_non_monotonic_hint_count = 0
    timestamp_non_monotonic_hint_count = 0
    repeated_final_update_id_hint_count = 0

    previous_event_time = None
    previous_transaction_time = None
    previous_received_time = None
    previous_effective_time = None
    previous_packet: dict[str, Any] | None = None
    for packet in packet_rows:
        event_time = packet.get("event_time")
        transaction_time = packet.get("transaction_time")
        received_time = packet.get("received_time")
        effective_time = transaction_time if pd.notna(transaction_time) and transaction_time is not None else event_time
        if previous_event_time is not None and pd.notna(event_time) and event_time < previous_event_time:
            event_time_non_monotonic_hint_count += 1
        if previous_transaction_time is not None and pd.notna(transaction_time) and transaction_time is not None and transaction_time < previous_transaction_time:
            transaction_time_non_monotonic_hint_count += 1
        if previous_received_time is not None and pd.notna(received_time) and received_time < previous_received_time:
            received_time_non_monotonic_hint_count += 1
        if previous_effective_time is not None and pd.notna(effective_time) and effective_time < previous_effective_time:
            timestamp_non_monotonic_hint_count += 1
        if previous_packet is not None and packet.get("final_update_id") == previous_packet.get("final_update_id"):
            repeated_final_update_id_hint_count += 1
        previous_event_time = event_time if pd.notna(event_time) else previous_event_time
        previous_transaction_time = transaction_time if pd.notna(transaction_time) else previous_transaction_time
        previous_received_time = received_time if pd.notna(received_time) else previous_received_time
        previous_effective_time = effective_time if pd.notna(effective_time) else previous_effective_time
        previous_packet = packet

    estimated_source_gap_count = 0
    previous_packet = None
    for packet in sorted(packet_rows, key=_packet_sort_key):
        current_is_snapshot_like = bool(packet["snapshot_like"])
        if previous_packet is not None:
            previous_is_snapshot_like = bool(previous_packet["snapshot_like"])
            if (
                not previous_is_snapshot_like
                and not current_is_snapshot_like
                and pd.notna(packet.get("prev_final_update_id"))
                and pd.notna(previous_packet.get("final_update_id"))
                and packet.get("prev_final_update_id") != previous_packet.get("final_update_id")
            ):
                estimated_source_gap_count += 1
        previous_packet = packet

    candidate_reasons: list[str] = []
    if snapshot_like_packet_count > 0:
        candidate_reasons.append("snapshot_reset_like")
    if missing_transaction_packet_count > 0:
        candidate_reasons.append("missing_transaction_time")
    if missing_first_update_id_count > 0:
        candidate_reasons.append("missing_first_update_id")
    if missing_prev_final_update_id_count > 0:
        candidate_reasons.append("missing_prev_final_update_id")
    if estimated_source_gap_count > 0:
        candidate_reasons.append("estimated_source_gap")
    if timestamp_non_monotonic_hint_count > 0:
        candidate_reasons.append("timestamp_non_monotonicity")
    if event_time_non_monotonic_hint_count > 0:
        candidate_reasons.append("event_time_non_monotonicity")
    if transaction_time_non_monotonic_hint_count > 0:
        candidate_reasons.append("transaction_time_non_monotonicity")
    if received_time_non_monotonic_hint_count > 0:
        candidate_reasons.append("received_time_non_monotonicity")
    if repeated_final_update_id_hint_count > 0:
        candidate_reasons.append("repeated_final_update_id")
    if side_mapping_unknown_count > 0:
        candidate_reasons.append("unknown_side_mapping")
    if missing_required_column_count > 0:
        candidate_reasons.append("missing_required_column")

    candidate_score = (
        snapshot_like_packet_count * 5000
        + snapshot_like_row_count * 50
        + missing_transaction_packet_count * 2500
        + missing_first_update_id_count * 1500
        + missing_prev_final_update_id_count * 1500
        + estimated_source_gap_count * 1000
        + timestamp_non_monotonic_hint_count * 300
        + event_time_non_monotonic_hint_count * 150
        + transaction_time_non_monotonic_hint_count * 150
        + received_time_non_monotonic_hint_count * 100
        + repeated_final_update_id_hint_count * 100
        + side_mapping_unknown_count * 50
        + missing_required_column_count * 500
    )

    return CandidatePreview(
        candidate_file_path=candidate_file_path,
        file_date=_file_date(Path(candidate_file_path)),
        file_hour=_file_hour(Path(candidate_file_path)),
        preview_row_count=preview_row_count,
        preview_packet_count=preview_packet_count,
        missing_transaction_time_count=missing_transaction_packet_count,
        missing_first_update_id_count=missing_first_update_id_count,
        missing_prev_final_update_id_count=missing_prev_final_update_id_count,
        snapshot_like_row_count=snapshot_like_row_count,
        snapshot_like_packet_count=snapshot_like_packet_count,
        timestamp_non_monotonic_hint_count=timestamp_non_monotonic_hint_count,
        event_time_non_monotonic_hint_count=event_time_non_monotonic_hint_count,
        transaction_time_non_monotonic_hint_count=transaction_time_non_monotonic_hint_count,
        received_time_non_monotonic_hint_count=received_time_non_monotonic_hint_count,
        repeated_final_update_id_hint_count=repeated_final_update_id_hint_count,
        estimated_source_gap_count=estimated_source_gap_count,
        side_mapping_unknown_count=side_mapping_unknown_count,
        missing_required_column_count=missing_required_column_count,
        candidate_score=candidate_score,
        candidate_reasons=tuple(candidate_reasons),
    )


def preview_candidate_file(path: Path, *, symbol: str, preview_rows_per_file: int) -> CandidatePreview:
    if path.suffix.lower() == ".parquet" or path.name.lower().endswith(".parquet.zst"):
        frame = _read_parquet_preview(path, preview_rows_per_file)
    elif path.suffix.lower() == ".csv" or path.name.lower().endswith(".csv.gz"):
        frame = _read_csv_preview(path, preview_rows_per_file)
    elif path.suffix.lower() in {".json", ".jsonl"}:
        frame = _read_json_preview(path, preview_rows_per_file)
    else:
        frame = pd.DataFrame()
    if frame.empty:
        return CandidatePreview(
            candidate_file_path=path.as_posix(),
            file_date=_file_date(path),
            file_hour=_file_hour(path),
            preview_row_count=0,
            preview_packet_count=0,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            snapshot_like_row_count=0,
            snapshot_like_packet_count=0,
            timestamp_non_monotonic_hint_count=0,
            event_time_non_monotonic_hint_count=0,
            transaction_time_non_monotonic_hint_count=0,
            received_time_non_monotonic_hint_count=0,
            repeated_final_update_id_hint_count=0,
            estimated_source_gap_count=0,
            side_mapping_unknown_count=0,
            missing_required_column_count=len(REQUIRED_COLUMNS),
            candidate_score=0,
            candidate_reasons=("empty_preview",),
        )
    return preview_candidate_frame(frame, candidate_file_path=path.as_posix(), preview_rows_per_file=preview_rows_per_file)


def rank_candidate_previews(previews: Iterable[CandidatePreview]) -> list[CandidatePreview]:
    return sorted(previews, key=lambda p: (-p.candidate_score, p.file_date or "", p.file_hour or "", p.candidate_file_path))


def select_final_findings(previews: list[CandidatePreview], max_selected_findings: int) -> list[CandidatePreview]:
    return rank_candidate_previews(previews)[:max_selected_findings]


def _preview_rows_to_table_rows(previews: Iterable[CandidatePreview]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preview in previews:
        rows.append(
            {
                "candidate_file_path": preview.candidate_file_path,
                "file_date": preview.file_date,
                "file_hour": preview.file_hour,
                "preview_row_count": preview.preview_row_count,
                "preview_packet_count": preview.preview_packet_count,
                "missing_transaction_time_count": preview.missing_transaction_time_count,
                "missing_first_update_id_count": preview.missing_first_update_id_count,
                "missing_prev_final_update_id_count": preview.missing_prev_final_update_id_count,
                "snapshot_like_row_count": preview.snapshot_like_row_count,
                "snapshot_like_packet_count": preview.snapshot_like_packet_count,
                "timestamp_non_monotonic_hint_count": preview.timestamp_non_monotonic_hint_count,
                "event_time_non_monotonic_hint_count": preview.event_time_non_monotonic_hint_count,
                "transaction_time_non_monotonic_hint_count": preview.transaction_time_non_monotonic_hint_count,
                "received_time_non_monotonic_hint_count": preview.received_time_non_monotonic_hint_count,
                "repeated_final_update_id_hint_count": preview.repeated_final_update_id_hint_count,
                "estimated_source_gap_count": preview.estimated_source_gap_count,
                "side_mapping_unknown_count": preview.side_mapping_unknown_count,
                "missing_required_column_count": preview.missing_required_column_count,
                "candidate_score": preview.candidate_score,
                "candidate_reasons": ", ".join(preview.candidate_reasons) if preview.candidate_reasons else "",
            }
        )
    return rows


def build_report(
    *,
    l2_root: Path,
    candidate_file_count: int,
    selected_findings: list[CandidatePreview],
    candidate_previews: list[CandidatePreview],
    max_candidate_files: int,
    max_selected_findings: int,
) -> str:
    total_candidates = len(candidate_previews)
    snapshot_candidates = [preview for preview in candidate_previews if preview.snapshot_like_packet_count > 0]
    fallback_candidates = [preview for preview in candidate_previews if preview.missing_transaction_time_count > 0]
    source_gap_candidates = [preview for preview in candidate_previews if preview.estimated_source_gap_count > 0]
    timestamp_candidates = [preview for preview in candidate_previews if preview.timestamp_non_monotonic_hint_count > 0]
    side_mapping_candidates = [preview for preview in candidate_previews if preview.side_mapping_unknown_count > 0]
    missing_column_candidates = [preview for preview in candidate_previews if preview.missing_required_column_count > 0]

    decision_labels = [
        "bounded_read_only_discovery",
        "candidate_selection_deterministic",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if snapshot_candidates:
        decision_labels.append("raw_snapshot_reset_candidates_found")
    if fallback_candidates:
        decision_labels.append("raw_timestamp_fallback_candidates_found")
    if source_gap_candidates:
        decision_labels.append("raw_source_gap_candidates_found")
    if timestamp_candidates:
        decision_labels.append("timestamp_ordering_hints_found")
    if side_mapping_candidates:
        decision_labels.append("unknown_side_mapping_hints_found")

    lines = [
        "# V9.2 L2 OFI Unexercised Policy Path Discovery",
        "",
        "## Purpose",
        "Find bounded raw L2 files that may exercise policy paths not yet observed in the bounded segmented reconstruction rehearsals, focusing on snapshot/reset-like packets, missing transaction_time fallback cases, source-gap hints, ordering anomalies, and side-mapping anomalies.",
        "",
        "## Inputs",
        f"- `l2_root`: `{l2_root}`",
        f"- `symbol`: `BTCUSDT`",
        f"- `max_candidate_files`: `{max_candidate_files}`",
        f"- `candidate_file_count`: `{candidate_file_count}`",
        f"- `max_selected_findings`: `{max_selected_findings}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded discovery only.",
        "- No OFI artifacts are written.",
        "- No alpha, paper, or live approval is granted.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Discovery Method",
        "Deterministic candidate selection used anchored files, neighboring files around the known anomaly files, first and last files, month-open and hour-boundary files, evenly spaced corpus files, and 2026 files where present. Each candidate was previewed only on bounded rows and scored from packet-level hints.",
        "",
        "## Candidate Selection",
        f"- Candidate files discovered: `{candidate_file_count}`",
        f"- Candidate files previewed: `{total_candidates}`",
        f"- Selected findings reported: `{len(selected_findings)}`",
        "",
        "## Executive Finding",
        f"Bounded discovery previewed `{total_candidates}` candidate raw L2 files and ranked `{len(selected_findings)}` findings.",
        f"Raw snapshot/reset-like candidates found: `{len(snapshot_candidates)}`.",
        f"Raw missing transaction_time fallback candidates found: `{len(fallback_candidates)}`.",
        f"Raw source-gap candidates found: `{len(source_gap_candidates)}`.",
        f"Timestamp ordering hints found: `{len(timestamp_candidates)}`.",
        f"Unknown side-mapping hints found: `{len(side_mapping_candidates)}`.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Top Candidate Findings",
        _markdown_table(
            _preview_rows_to_table_rows(selected_findings),
            [
                "candidate_file_path",
                "file_date",
                "file_hour",
                "candidate_score",
                "candidate_reasons",
                "preview_row_count",
                "preview_packet_count",
                "snapshot_like_packet_count",
                "missing_transaction_time_count",
                "estimated_source_gap_count",
                "timestamp_non_monotonic_hint_count",
                "side_mapping_unknown_count",
                "missing_required_column_count",
            ],
        ),
        "",
        "## Snapshot/Reset Candidate Findings",
        (
            "No raw snapshot/reset-like candidates were found in this bounded discovery window."
            if not snapshot_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(snapshot_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "snapshot_like_row_count",
                    "snapshot_like_packet_count",
                ],
            )
        ),
        "",
        "## Transaction-Time Fallback Candidate Findings",
        (
            "No raw missing transaction_time fallback candidates were found in this bounded discovery window."
            if not fallback_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(fallback_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "missing_transaction_time_count",
                ],
            )
        ),
        "",
        "## Source-Gap Candidate Findings",
        (
            "No raw source-gap candidates were found in this bounded discovery window."
            if not source_gap_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(source_gap_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "estimated_source_gap_count",
                    "snapshot_like_packet_count",
                ],
            )
        ),
        "",
        "## Timestamp Ordering Candidate Findings",
        (
            "No timestamp non-monotonicity hints were found in this bounded discovery window."
            if not timestamp_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(timestamp_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "timestamp_non_monotonic_hint_count",
                    "event_time_non_monotonic_hint_count",
                    "transaction_time_non_monotonic_hint_count",
                    "received_time_non_monotonic_hint_count",
                ],
            )
        ),
        "",
        "## Side Mapping Candidate Findings",
        (
            "No unknown side mappings were found in this bounded discovery window."
            if not side_mapping_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(side_mapping_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "side_mapping_unknown_count",
                ],
            )
        ),
        "",
        "## Missing Column Findings",
        (
            "No missing required columns were found in this bounded discovery window."
            if not missing_column_candidates
            else _markdown_table(
                _preview_rows_to_table_rows(missing_column_candidates[:10]),
                [
                    "candidate_file_path",
                    "file_date",
                    "file_hour",
                    "candidate_score",
                    "candidate_reasons",
                    "missing_required_column_count",
                ],
            )
        ),
        "",
        "## What Worked",
        "- Discovery was bounded and read-only.",
        "- Candidate selection was deterministic.",
        "- Snapshot/reset-like, fallback, source-gap, timestamp, side-mapping, and missing-column hints were scored without writing derived artifacts.",
        "",
        "## What Failed Or Remains Unknown",
        "- This is a discovery pass only.",
        "- A bounded preview can miss rare paths outside the sampled window.",
        "- No OFI reconstruction or trading approval was attempted.",
        "",
        "## What Is Safe",
        "- Bounded read-only discovery of candidate raw L2 files.",
        "- Using the previews to choose future bounded tests or diagnostics.",
        "",
        "## What Is Not Safe",
        "- Full reconstruction.",
        "- Any paper or live trading use.",
        "- Alpha claims.",
        "",
        "## Decision",
        ", ".join(decision_labels) + ".",
        "",
        "## Required Next Step",
        "Use any discovered candidate files only for bounded read-only diagnostics or synthetic reproductions of the unexercised policy paths.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_discovery(
    *,
    l2_root: Path,
    max_candidate_files: int,
    preview_rows_per_file: int,
    max_selected_findings: int,
    symbol: str,
    output_doc: Path,
) -> dict[str, Any]:
    discovered = discover_candidate_files(l2_root, symbol)
    candidate_pool = build_candidate_pool(discovered, max_candidate_files)
    previews = [preview_candidate_file(path, symbol=symbol, preview_rows_per_file=preview_rows_per_file) for path in candidate_pool]
    selected_findings = select_final_findings(previews, max_selected_findings)
    report = build_report(
        l2_root=l2_root,
        candidate_file_count=len(discovered),
        selected_findings=selected_findings,
        candidate_previews=previews,
        max_candidate_files=max_candidate_files,
        max_selected_findings=max_selected_findings,
    )
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(report, encoding="utf-8")
    return {
        "candidate_file_count": len(discovered),
        "preview_file_count": len(candidate_pool),
        "selected_finding_count": len(selected_findings),
        "snapshot_candidates": sum(1 for preview in previews if preview.snapshot_like_packet_count > 0),
        "fallback_candidates": sum(1 for preview in previews if preview.missing_transaction_time_count > 0),
        "source_gap_candidates": sum(1 for preview in previews if preview.estimated_source_gap_count > 0),
        "timestamp_candidates": sum(1 for preview in previews if preview.timestamp_non_monotonic_hint_count > 0),
        "side_mapping_candidates": sum(1 for preview in previews if preview.side_mapping_unknown_count > 0),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_discovery(
        l2_root=args.l2_root,
        max_candidate_files=args.max_candidate_files,
        preview_rows_per_file=args.preview_rows_per_file,
        max_selected_findings=args.max_selected_findings,
        symbol=args.symbol,
        output_doc=args.output_doc,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
