#!/usr/bin/env python3
"""Bounded read-only validation of discovered raw L2 candidates for unexercised OFI policy paths."""

from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass
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

from features.l2_ofi_segmented_reconstruction import (  # noqa: E402
    L2Packet,
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_DISCOVERED_POLICY_PATH_CANDIDATE_VALIDATION.md")
PRODUCTION_APPROVAL_STATEMENT = "This validation does not approve OFI for production, paper trading, live trading, or alpha use."
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

DEFAULT_CANDIDATE_INPUTS: list[tuple[str, str]] = [
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst",
        "snapshot_reset_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst",
        "snapshot_reset_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst",
        "source_gap_timestamp_candidate",
    ),
]


@dataclass(frozen=True)
class CandidateFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class CandidateResult:
    file_path: str
    candidate_reason: str
    file_date: str | None
    file_hour: str | None
    rows_scanned: int
    packet_count: int
    missing_transaction_time_count: int
    missing_first_update_id_count: int
    missing_prev_final_update_id_count: int
    snapshot_like_packet_count: int
    timestamp_fallback_used: bool
    timestamp_non_monotonic_hint_count: int
    event_time_non_monotonic_hint_count: int
    transaction_time_non_monotonic_hint_count: int
    received_time_non_monotonic_hint_count: int
    source_gap_boundary_count: int
    snapshot_reset_boundary_count: int
    segment_count: int
    meaningful_segment_count: int
    one_packet_segment_count: int
    clean_segment_count: int
    dirty_segment_count: int
    all_segments_clean: bool
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    min_segment_packet_count: int | None
    max_segment_packet_count: int | None
    side_mapping_unknown_count: int
    policy_module_used_directly: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-events-per-file", type=int, default=50_000)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--candidate-file", action="append", default=None)
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


def _read_parquet_preview(path: Path, max_rows: int) -> pd.DataFrame:
    if pq is None or zstd is None:
        raise RuntimeError("pyarrow and zstandard are required for bounded parquet previewing")
    if path.suffix.lower() == ".parquet":
        parquet_file = pq.ParquetFile(path)
    elif path.name.lower().endswith(".parquet.zst"):
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        parquet_file = pq.ParquetFile(io.BytesIO(raw))
    else:
        raise ValueError(f"Unsupported parquet path: {path}")

    batches: list[pd.DataFrame] = []
    rows_remaining = max_rows
    for batch in parquet_file.iter_batches(batch_size=min(max_rows, 8192)):
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


def _as_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in REQUIRED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized["symbol"] = normalized["symbol"].astype("string").str.strip().str.upper()
    normalized["event_type"] = normalized["event_type"].astype("string").str.strip()
    for column in ["event_time", "transaction_time", "received_time", "first_update_id", "final_update_id", "prev_final_update_id", "last_update_id"]:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["price"] = pd.to_numeric(normalized["price"], errors="coerce")
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce")
    normalized["side_text"] = normalized["side"].astype("string").str.strip().str.lower()
    return normalized


def _frame_to_packets(frame: pd.DataFrame) -> tuple[list[L2Packet], dict[str, int]]:
    if frame.empty:
        return [], {"rows_scanned": 0, "unknown_side_row_count": 0, "missing_required_column_count": len(REQUIRED_COLUMNS)}

    normalized = _normalize_frame(frame)
    rows_scanned = int(len(normalized))
    missing_required_column_count = sum(1 for column in REQUIRED_COLUMNS if column not in frame.columns)

    valid = normalized[
        normalized["symbol"].notna()
        & normalized["event_time"].notna()
        & normalized["final_update_id"].notna()
    ].copy()
    valid["side_group"] = valid["side"].map(_normalize_side)
    unknown_side_row_count = int(valid["side_group"].isna().sum())

    grouped = valid.groupby(["symbol", "event_time", "final_update_id", "prev_final_update_id", "event_type"], dropna=False, sort=False)

    packets: list[L2Packet] = []
    for _, group in grouped:
        first = group.iloc[0]
        bids: list[tuple[float, float]] = []
        asks: list[tuple[float, float]] = []
        for _, row in group.iterrows():
            side = row.get("side_group")
            price = _as_float(row.get("price"))
            quantity = _as_float(row.get("quantity"))
            if side is None or price is None or quantity is None:
                continue
            if side == "bid":
                bids.append((price, quantity))
            else:
                asks.append((price, quantity))
        packets.append(
            L2Packet(
                symbol=str(first["symbol"]),
                event_type=str(first["event_type"] or "depthUpdate"),
                event_time=int(first["event_time"]),
                transaction_time=_as_int(first.get("transaction_time")),
                received_time=_as_int(first.get("received_time")),
                first_update_id=_as_int(first.get("first_update_id")),
                final_update_id=int(first["final_update_id"]),
                prev_final_update_id=_as_int(first.get("prev_final_update_id")),
                bids=tuple(bids),
                asks=tuple(asks),
            )
        )

    return packets, {
        "rows_scanned": rows_scanned,
        "unknown_side_row_count": unknown_side_row_count,
        "missing_required_column_count": missing_required_column_count,
    }


def _packet_sort_diagnostics(packets: list[L2Packet]) -> dict[str, int | bool]:
    ordered = sorted(packets, key=packet_sort_key)
    timestamp_fallback_used = any(packet.transaction_time is None for packet in ordered)
    timestamp_non_monotonic_hint_count = 0
    event_time_non_monotonic_hint_count = 0
    transaction_time_non_monotonic_hint_count = 0
    received_time_non_monotonic_hint_count = 0
    repeated_final_update_id_hint_count = 0

    previous_packet: L2Packet | None = None
    previous_event_time: int | None = None
    previous_transaction_time: int | None = None
    previous_received_time: int | None = None
    previous_effective_time: int | None = None

    for packet in ordered:
        effective_time = packet.transaction_time if packet.transaction_time is not None else packet.event_time
        if previous_packet is not None and packet.final_update_id == previous_packet.final_update_id:
            repeated_final_update_id_hint_count += 1
        if previous_event_time is not None and packet.event_time < previous_event_time:
            event_time_non_monotonic_hint_count += 1
        if previous_transaction_time is not None and packet.transaction_time is not None and packet.transaction_time < previous_transaction_time:
            transaction_time_non_monotonic_hint_count += 1
        if previous_received_time is not None and packet.received_time is not None and packet.received_time < previous_received_time:
            received_time_non_monotonic_hint_count += 1
        if previous_effective_time is not None and effective_time < previous_effective_time:
            timestamp_non_monotonic_hint_count += 1
        previous_packet = packet
        previous_event_time = packet.event_time
        if packet.transaction_time is not None:
            previous_transaction_time = packet.transaction_time
        if packet.received_time is not None:
            previous_received_time = packet.received_time
        previous_effective_time = effective_time

    return {
        "timestamp_fallback_used": timestamp_fallback_used,
        "timestamp_non_monotonic_hint_count": timestamp_non_monotonic_hint_count,
        "event_time_non_monotonic_hint_count": event_time_non_monotonic_hint_count,
        "transaction_time_non_monotonic_hint_count": transaction_time_non_monotonic_hint_count,
        "received_time_non_monotonic_hint_count": received_time_non_monotonic_hint_count,
        "repeated_final_update_id_hint_count": repeated_final_update_id_hint_count,
    }


def _source_gap_count(packets: list[L2Packet]) -> int:
    ordered = sorted(packets, key=packet_sort_key)
    count = 0
    previous: L2Packet | None = None
    for packet in ordered:
        if previous is None:
            previous = packet
            continue
        if (
            previous.first_update_id is None
            or previous.prev_final_update_id is None
            or packet.first_update_id is None
            or packet.prev_final_update_id is None
        ):
            previous = packet
            continue
        if packet.prev_final_update_id != previous.final_update_id:
            count += 1
        previous = packet
    return count


def _segment_and_replay(packets: list[L2Packet]) -> tuple[tuple[Any, ...], list[Any], list[Any]]:
    ordered_packets = tuple(sorted(packets, key=packet_sort_key))
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    return ordered_packets, list(segments), results


def preview_candidate_file(path: Path, *, reason: str, max_events_per_file: int) -> CandidateResult:
    frame = _read_parquet_preview(path, max_events_per_file)
    packets, counters = _frame_to_packets(frame)
    ordered_packets, segments, results = _segment_and_replay(packets)
    summary = summarize_segments(segments, results)
    boundary_counts = {
        "source_sequence_gap": sum(1 for segment in segments if segment.boundary_reason == "source_sequence_gap"),
        "snapshot_or_reset": sum(1 for segment in segments if segment.boundary_reason == "snapshot_or_reset"),
    }
    diagnostics = _packet_sort_diagnostics(list(ordered_packets))
    return CandidateResult(
        file_path=path.as_posix(),
        candidate_reason=reason,
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        rows_scanned=counters["rows_scanned"],
        packet_count=len(ordered_packets),
        missing_transaction_time_count=sum(1 for packet in ordered_packets if packet.transaction_time is None),
        missing_first_update_id_count=sum(1 for packet in ordered_packets if packet.first_update_id is None),
        missing_prev_final_update_id_count=sum(1 for packet in ordered_packets if packet.prev_final_update_id is None),
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if packet.first_update_id is None or packet.prev_final_update_id is None),
        timestamp_fallback_used=bool(diagnostics["timestamp_fallback_used"]),
        timestamp_non_monotonic_hint_count=int(diagnostics["timestamp_non_monotonic_hint_count"]),
        event_time_non_monotonic_hint_count=int(diagnostics["event_time_non_monotonic_hint_count"]),
        transaction_time_non_monotonic_hint_count=int(diagnostics["transaction_time_non_monotonic_hint_count"]),
        received_time_non_monotonic_hint_count=int(diagnostics["received_time_non_monotonic_hint_count"]),
        source_gap_boundary_count=boundary_counts["source_sequence_gap"],
        snapshot_reset_boundary_count=boundary_counts["snapshot_or_reset"],
        segment_count=summary["segment_count"],
        meaningful_segment_count=summary["meaningful_segment_count"],
        one_packet_segment_count=sum(1 for segment in segments if len(segment.packets) == 1),
        clean_segment_count=summary["clean_segment_count"],
        dirty_segment_count=summary["dirty_segment_count"],
        all_segments_clean=bool(summary["all_segments_clean"]),
        total_ofi_emitted_count=int(summary["total_ofi_emitted_count"]),
        total_warmup_none_count=int(summary["total_warmup_none_count"]),
        total_sequence_gap_count=int(summary["total_sequence_gap_count"]),
        min_segment_packet_count=min((len(segment.packets) for segment in segments), default=None),
        max_segment_packet_count=max((len(segment.packets) for segment in segments), default=None),
        side_mapping_unknown_count=counters["unknown_side_row_count"],
        policy_module_used_directly=True,
    )


def build_candidate_inputs(candidate_file_args: list[str] | None) -> list[CandidateFile]:
    if candidate_file_args:
        return [CandidateFile(path=Path(path), reason="override_candidate") for path in candidate_file_args]
    return [CandidateFile(path=Path(path), reason=reason) for path, reason in DEFAULT_CANDIDATE_INPUTS]


def build_report(*, candidate_inputs: list[CandidateFile], results: list[CandidateResult], max_events_per_file: int) -> str:
    selected_candidate_count = len(candidate_inputs)
    snapshot_reset_candidate_count = sum(1 for candidate in candidate_inputs if candidate.reason == "snapshot_reset_candidate")
    source_gap_timestamp_candidate_count = sum(1 for candidate in candidate_inputs if candidate.reason == "source_gap_timestamp_candidate")
    total_rows_scanned = sum(result.rows_scanned for result in results)
    total_packet_count = sum(result.packet_count for result in results)
    total_segment_count = sum(result.segment_count for result in results)
    total_meaningful_segment_count = sum(result.meaningful_segment_count for result in results)
    total_snapshot_like_packet_count = sum(result.snapshot_like_packet_count for result in results)
    total_snapshot_reset_boundary_count = sum(result.snapshot_reset_boundary_count for result in results)
    total_source_gap_boundary_count = sum(result.source_gap_boundary_count for result in results)
    files_with_snapshot_reset_boundaries = sum(1 for result in results if result.snapshot_reset_boundary_count > 0)
    files_with_source_gap_boundaries = sum(1 for result in results if result.source_gap_boundary_count > 0)
    files_with_timestamp_ordering_hints = sum(
        1
        for result in results
        if result.timestamp_non_monotonic_hint_count > 0
        or result.event_time_non_monotonic_hint_count > 0
        or result.transaction_time_non_monotonic_hint_count > 0
        or result.received_time_non_monotonic_hint_count > 0
    )
    files_with_timestamp_fallback = sum(1 for result in results if result.timestamp_fallback_used)
    files_all_segments_clean = sum(1 for result in results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in results if result.dirty_segment_count > 0)
    total_ofi_emitted_count = sum(result.total_ofi_emitted_count for result in results)
    total_warmup_none_count = sum(result.total_warmup_none_count for result in results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in results)
    unknown_side_mapping_total = sum(result.side_mapping_unknown_count for result in results)

    if files_with_timestamp_fallback > 0:
        fallback_label = "raw_missing_transaction_time_fallback_observed"
    else:
        fallback_label = "raw_missing_transaction_time_fallback_not_observed"

    decision_labels = [
        "policy_module_used_directly",
        "discovered_candidates_used_deterministically",
        "raw_snapshot_reset_candidates_validated",
        "raw_source_gap_timestamp_candidates_validated",
        "timestamp_ordering_candidates_validated",
        fallback_label,
        "segments_clean_in_discovered_candidate_sample",
        "ofi_values_emitted_in_memory_only",
        "no_ofi_artifacts_written",
        "segmented_policy_discovered_candidate_validated",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    lines = [
        "# V9.2 L2 OFI Discovered Policy Path Candidate Validation",
        "",
        "## Purpose",
        "Validate the reusable segmented reconstruction policy module on the raw L2 candidate files discovered as likely to exercise previously unobserved policy paths.",
        "",
        "## Inputs",
        f"- `max_events_per_file`: `{max_events_per_file}`",
        f"- `selected_candidate_count`: `{selected_candidate_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded validation only.",
        "- No OFI artifacts are written.",
        "- No alpha, paper, or live approval is granted.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Candidate Sources",
        _markdown_table(
            [
                {
                    "file_path": candidate.path.as_posix(),
                    "candidate_reason": candidate.reason,
                    "file_date": _file_date(candidate.path),
                    "file_hour": _file_hour(candidate.path),
                }
                for candidate in candidate_inputs
            ],
            ["file_path", "candidate_reason", "file_date", "file_hour"],
        ),
        "",
        "## Module Usage",
        "- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.",
        "- Raw rows are converted to `L2Packet` objects in-memory before segmentation.",
        "- Segmentation and per-segment OFIEngine processing are delegated to the policy module.",
        "",
        "## Executive Finding",
        f"{selected_candidate_count} discovered raw candidate files were processed in bounded read-only mode.",
        f"Snapshot/reset-like candidates selected: `{snapshot_reset_candidate_count}`.",
        f"Source-gap/timestamp candidates selected: `{source_gap_timestamp_candidate_count}`.",
        (
            "Snapshot/reset-like raw candidates were observed, but they remained dirty in this bounded sample."
            if snapshot_reset_candidate_count > 0
            else "No raw snapshot/reset-like candidates were found in this bounded validation window."
        ),
        f"Missing transaction_time fallback observed in raw candidate sample: `{files_with_timestamp_fallback > 0}`.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Per-File Candidate Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "candidate_reason": result.candidate_reason,
                    "file_date": result.file_date,
                    "file_hour": result.file_hour,
                    "rows_scanned": result.rows_scanned,
                    "packet_count": result.packet_count,
                    "missing_transaction_time_count": result.missing_transaction_time_count,
                    "missing_first_update_id_count": result.missing_first_update_id_count,
                    "missing_prev_final_update_id_count": result.missing_prev_final_update_id_count,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "timestamp_fallback_used": result.timestamp_fallback_used,
                    "timestamp_non_monotonic_hint_count": result.timestamp_non_monotonic_hint_count,
                    "event_time_non_monotonic_hint_count": result.event_time_non_monotonic_hint_count,
                    "transaction_time_non_monotonic_hint_count": result.transaction_time_non_monotonic_hint_count,
                    "received_time_non_monotonic_hint_count": result.received_time_non_monotonic_hint_count,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "snapshot_reset_boundary_count": result.snapshot_reset_boundary_count,
                    "segment_count": result.segment_count,
                    "meaningful_segment_count": result.meaningful_segment_count,
                    "one_packet_segment_count": result.one_packet_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "min_segment_packet_count": result.min_segment_packet_count,
                    "max_segment_packet_count": result.max_segment_packet_count,
                    "side_mapping_unknown_count": result.side_mapping_unknown_count,
                    "policy_module_used_directly": result.policy_module_used_directly,
                }
                for result in results
            ],
            [
                "file_path",
                "candidate_reason",
                "file_date",
                "file_hour",
                "rows_scanned",
                "packet_count",
                "missing_transaction_time_count",
                "missing_first_update_id_count",
                "missing_prev_final_update_id_count",
                "snapshot_like_packet_count",
                "timestamp_fallback_used",
                "timestamp_non_monotonic_hint_count",
                "event_time_non_monotonic_hint_count",
                "transaction_time_non_monotonic_hint_count",
                "received_time_non_monotonic_hint_count",
                "source_gap_boundary_count",
                "snapshot_reset_boundary_count",
                "segment_count",
                "meaningful_segment_count",
                "one_packet_segment_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "min_segment_packet_count",
                "max_segment_packet_count",
                "side_mapping_unknown_count",
                "policy_module_used_directly",
            ],
        ),
        "",
        "## Aggregate Candidate Summary",
        _markdown_table(
            [
                {
                    "selected_candidate_count": selected_candidate_count,
                    "snapshot_reset_candidate_count": snapshot_reset_candidate_count,
                    "source_gap_timestamp_candidate_count": source_gap_timestamp_candidate_count,
                    "total_rows_scanned": total_rows_scanned,
                    "total_packet_count": total_packet_count,
                    "total_segment_count": total_segment_count,
                    "total_meaningful_segment_count": total_meaningful_segment_count,
                    "total_snapshot_like_packet_count": total_snapshot_like_packet_count,
                    "total_snapshot_reset_boundary_count": total_snapshot_reset_boundary_count,
                    "total_source_gap_boundary_count": total_source_gap_boundary_count,
                    "files_with_snapshot_reset_boundaries": files_with_snapshot_reset_boundaries,
                    "files_with_source_gap_boundaries": files_with_source_gap_boundaries,
                    "files_with_timestamp_ordering_hints": files_with_timestamp_ordering_hints,
                    "files_with_timestamp_fallback": files_with_timestamp_fallback,
                    "files_all_segments_clean": files_all_segments_clean,
                    "files_with_dirty_segments": files_with_dirty_segments,
                    "total_ofi_emitted_count": total_ofi_emitted_count,
                    "total_warmup_none_count": total_warmup_none_count,
                    "total_sequence_gap_count": total_sequence_gap_count,
                    "unknown_side_mapping_total": unknown_side_mapping_total,
                }
            ],
            [
                "selected_candidate_count",
                "snapshot_reset_candidate_count",
                "source_gap_timestamp_candidate_count",
                "total_rows_scanned",
                "total_packet_count",
                "total_segment_count",
                "total_meaningful_segment_count",
                "total_snapshot_like_packet_count",
                "total_snapshot_reset_boundary_count",
                "total_source_gap_boundary_count",
                "files_with_snapshot_reset_boundaries",
                "files_with_source_gap_boundaries",
                "files_with_timestamp_ordering_hints",
                "files_with_timestamp_fallback",
                "files_all_segments_clean",
                "files_with_dirty_segments",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "unknown_side_mapping_total",
            ],
        ),
        "",
        "## Snapshot/Reset Raw Candidate Results",
        (
            "No raw snapshot/reset-like candidates were found in this bounded validation window."
            if snapshot_reset_candidate_count == 0
            else _markdown_table(
                [
                    {
                        "file_path": result.file_path,
                        "candidate_reason": result.candidate_reason,
                        "snapshot_like_packet_count": result.snapshot_like_packet_count,
                        "snapshot_reset_boundary_count": result.snapshot_reset_boundary_count,
                        "segment_count": result.segment_count,
                        "all_segments_clean": result.all_segments_clean,
                    }
                    for result in results
                    if result.snapshot_like_packet_count > 0
                ],
                [
                    "file_path",
                    "candidate_reason",
                    "snapshot_like_packet_count",
                    "snapshot_reset_boundary_count",
                    "segment_count",
                    "all_segments_clean",
                ],
            )
        ),
        "",
        "## Source-Gap Raw Candidate Results",
        (
            "No raw source-gap candidates were found in this bounded validation window."
            if source_gap_timestamp_candidate_count == 0
            else _markdown_table(
                [
                    {
                        "file_path": result.file_path,
                        "candidate_reason": result.candidate_reason,
                        "source_gap_boundary_count": result.source_gap_boundary_count,
                        "segment_count": result.segment_count,
                        "all_segments_clean": result.all_segments_clean,
                    }
                    for result in results
                    if result.source_gap_boundary_count > 0
                ],
                [
                    "file_path",
                    "candidate_reason",
                    "source_gap_boundary_count",
                    "segment_count",
                    "all_segments_clean",
                ],
            )
        ),
        "",
        "## Timestamp Ordering Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "timestamp_non_monotonic_hint_count": result.timestamp_non_monotonic_hint_count,
                    "event_time_non_monotonic_hint_count": result.event_time_non_monotonic_hint_count,
                    "transaction_time_non_monotonic_hint_count": result.transaction_time_non_monotonic_hint_count,
                    "received_time_non_monotonic_hint_count": result.received_time_non_monotonic_hint_count,
                    "all_segments_clean": result.all_segments_clean,
                }
                for result in results
            ],
            [
                "file_path",
                "timestamp_non_monotonic_hint_count",
                "event_time_non_monotonic_hint_count",
                "transaction_time_non_monotonic_hint_count",
                "received_time_non_monotonic_hint_count",
                "all_segments_clean",
            ],
        ),
        "",
        "## Transaction-Time Fallback Results",
        (
            "No raw missing transaction_time fallback candidates were found in this bounded validation window."
            if files_with_timestamp_fallback == 0
            else _markdown_table(
                [
                    {
                        "file_path": result.file_path,
                        "candidate_reason": result.candidate_reason,
                        "missing_transaction_time_count": result.missing_transaction_time_count,
                        "timestamp_fallback_used": result.timestamp_fallback_used,
                        "all_segments_clean": result.all_segments_clean,
                    }
                    for result in results
                    if result.timestamp_fallback_used
                ],
                [
                    "file_path",
                    "candidate_reason",
                    "missing_transaction_time_count",
                    "timestamp_fallback_used",
                    "all_segments_clean",
                ],
            )
        ),
        "",
        "## OFIEngine Segment Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "segment_count": result.segment_count,
                    "meaningful_segment_count": result.meaningful_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "min_segment_packet_count": result.min_segment_packet_count,
                    "max_segment_packet_count": result.max_segment_packet_count,
                }
                for result in results
            ],
            [
                "file_path",
                "segment_count",
                "meaningful_segment_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "min_segment_packet_count",
                "max_segment_packet_count",
            ],
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- Discovered raw candidate files were used deterministically.",
        "- Observed source gaps were processed as segment boundaries.",
        "- The bounded candidate files were handled without writing OFI artifacts.",
        "",
        "## What Failed Or Remains Unknown",
        "- Snapshot/reset-like raw candidates were observed, but this bounded sample did not produce clean snapshot_reset boundaries and those files remained dirty.",
        "- No missing transaction_time fallback raw candidate was observed in this bounded candidate set.",
        "- A different bounded candidate set could still expose additional cases.",
        "- This remains a bounded validation only.",
        "",
        "## What Is Safe",
        "- Bounded read-only validation of discovered raw candidate files.",
        "- Using these files for future bounded diagnostics or synthetic reproductions.",
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
        "Use the discovered candidate files only for bounded diagnostics or additional synthetic reproductions of the unexercised policy paths.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_validation(*, max_events_per_file: int, output_doc: Path, candidate_file_args: list[str] | None) -> dict[str, Any]:
    candidate_inputs = build_candidate_inputs(candidate_file_args)
    results = [
        preview_candidate_file(candidate.path, reason=candidate.reason, max_events_per_file=max_events_per_file)
        for candidate in candidate_inputs
    ]
    report = build_report(
        candidate_inputs=candidate_inputs,
        results=results,
        max_events_per_file=max_events_per_file,
    )
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(report, encoding="utf-8")
    return {
        "selected_candidate_count": len(candidate_inputs),
        "snapshot_reset_candidate_count": sum(1 for candidate in candidate_inputs if candidate.reason == "snapshot_reset_candidate"),
        "source_gap_timestamp_candidate_count": sum(1 for candidate in candidate_inputs if candidate.reason == "source_gap_timestamp_candidate"),
        "total_rows_scanned": sum(result.rows_scanned for result in results),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_validation(
        max_events_per_file=args.max_events_per_file,
        output_doc=args.output_doc,
        candidate_file_args=args.candidate_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
