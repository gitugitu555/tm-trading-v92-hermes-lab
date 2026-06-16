#!/usr/bin/env python3
"""Bounded read-only diagnostic of dirty raw snapshot/reset L2 candidate files."""

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
    is_snapshot_or_reset,
    is_source_gap,
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)

PRODUCTION_APPROVAL_STATEMENT = "This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use."
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
        "dirty_snapshot_reset_candidate",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst",
        "dirty_snapshot_reset_candidate",
    ),
]


@dataclass(frozen=True)
class CandidateFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class SnapshotDirtyCaseResult:
    file_path: str
    file_date: str | None
    file_hour: str | None
    rows_scanned: int
    packet_count: int
    snapshot_like_packet_count: int
    snapshot_like_packet_indexes: tuple[int, ...]
    first_packet_is_snapshot_reset: bool
    segment_count: int
    snapshot_reset_boundary_count: int
    source_gap_boundary_count: int
    dirty_segment_count: int
    clean_segment_count: int
    all_segments_clean: bool
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    dirty_segment_ids: tuple[int, ...]
    dirty_segment_contains_snapshot_reset: bool
    snapshot_packet_position_in_dirty_segment: int | None
    dirty_segment_first_packet_is_snapshot_reset: bool
    next_packet_after_snapshot_prev_final_update_id: int | None
    snapshot_packet_final_update_id: int | None
    next_packet_chains_to_snapshot: bool | None
    hypothesis_a_first_packet_snapshot_supported: bool
    hypothesis_b_next_packet_chain_failure_supported: bool
    hypothesis_c_seed_insufficient_supported: bool
    root_cause_classification: str
    policy_module_used_directly: bool
    side_mapping_unknown_count: int
    snapshot_context_windows: tuple[dict[str, Any], ...]
    dirty_segment_details: tuple[dict[str, Any], ...]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-events-per-file", type=int, default=75_000)
    parser.add_argument("--context-packets-around-snapshot", type=int, default=10)
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


def _packets_from_frame(frame: pd.DataFrame) -> tuple[list[L2Packet], dict[str, int]]:
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


def _ordered_packets(packets: Iterable[L2Packet]) -> tuple[L2Packet, ...]:
    return tuple(sorted(tuple(packets), key=packet_sort_key))


def _packet_summary(packet: L2Packet, index: int) -> dict[str, Any]:
    return {
        "packet_index": index,
        "event_time": packet.event_time,
        "transaction_time": packet.transaction_time,
        "received_time": packet.received_time,
        "first_update_id": packet.first_update_id,
        "final_update_id": packet.final_update_id,
        "prev_final_update_id": packet.prev_final_update_id,
        "event_type": packet.event_type,
        "is_snapshot_or_reset": is_snapshot_or_reset(packet),
        "bid_level_count": len(packet.bids),
        "ask_level_count": len(packet.asks),
        "total_level_count": len(packet.bids) + len(packet.asks),
    }


def _source_gap_count(ordered_packets: Iterable[L2Packet]) -> int:
    count = 0
    previous: L2Packet | None = None
    for packet in ordered_packets:
        if previous is None:
            previous = packet
            continue
        if is_source_gap(previous, packet):
            count += 1
        previous = packet
    return count


def _analyze_snapshot_context(ordered_packets: tuple[L2Packet, ...], context_size: int) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    context_windows: list[dict[str, Any]] = []
    snapshot_indexes = [idx for idx, packet in enumerate(ordered_packets, start=1) if is_snapshot_or_reset(packet)]
    first_packet_is_snapshot_reset = bool(ordered_packets and is_snapshot_or_reset(ordered_packets[0]))
    first_snapshot = ordered_packets[snapshot_indexes[0] - 1] if snapshot_indexes else None
    next_packet_after_snapshot = ordered_packets[snapshot_indexes[0]] if snapshot_indexes and snapshot_indexes[0] < len(ordered_packets) else None

    for snapshot_index in snapshot_indexes:
        start = max(0, snapshot_index - 1 - context_size)
        end = min(len(ordered_packets), snapshot_index + context_size)
        context_windows.append(
            {
                "snapshot_packet_index": snapshot_index,
                "previous_packets": [
                    _packet_summary(packet, idx)
                    for idx, packet in enumerate(ordered_packets[start : snapshot_index - 1], start=start + 1)
                ],
                "snapshot_packet": _packet_summary(ordered_packets[snapshot_index - 1], snapshot_index),
                "next_packets": [
                    _packet_summary(packet, idx)
                    for idx, packet in enumerate(ordered_packets[snapshot_index:end], start=snapshot_index + 1)
                ],
            }
        )

    next_packet_prev_final_update_id = next_packet_after_snapshot.prev_final_update_id if next_packet_after_snapshot else None
    snapshot_final_update_id = first_snapshot.final_update_id if first_snapshot else None
    next_packet_chains_to_snapshot = (
        None
        if first_snapshot is None or next_packet_after_snapshot is None or is_snapshot_or_reset(next_packet_after_snapshot)
        else next_packet_after_snapshot.prev_final_update_id == first_snapshot.final_update_id
    )

    flags = {
        "snapshot_like_packet_indexes": tuple(snapshot_indexes),
        "first_packet_is_snapshot_reset": first_packet_is_snapshot_reset,
        "snapshot_packet_final_update_id": snapshot_final_update_id,
        "next_packet_after_snapshot_prev_final_update_id": next_packet_prev_final_update_id,
        "next_packet_chains_to_snapshot": next_packet_chains_to_snapshot,
    }
    return tuple(context_windows), flags


def _segment_and_replay(packets: Iterable[L2Packet]) -> tuple[tuple[Any, ...], list[Any], list[Any]]:
    ordered_packets = _ordered_packets(packets)
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    return ordered_packets, list(segments), results


def _dirty_segment_details(segments: list[Any], results: list[Any], ordered_packets: tuple[L2Packet, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    details: list[dict[str, Any]] = []
    primary_dirty_snapshot_index: int | None = None
    primary_snapshot_final_update_id: int | None = None
    primary_next_prev_final_update_id: int | None = None
    primary_next_chains: bool | None = None
    contains_snapshot = False
    first_packet_is_snapshot = False

    for segment, result in zip(segments, results):
        if result.clean:
            continue
        contains_snapshot = any(is_snapshot_or_reset(packet) for packet in segment.packets)
        first_packet_is_snapshot = bool(segment.packets and is_snapshot_or_reset(segment.packets[0]))
        snapshot_pos = next((idx for idx, packet in enumerate(segment.packets, start=1) if is_snapshot_or_reset(packet)), None)
        snapshot_packet = segment.packets[snapshot_pos - 1] if snapshot_pos else None
        next_packet = segment.packets[snapshot_pos] if snapshot_pos and snapshot_pos < len(segment.packets) else None
        next_chains = (
            None
            if snapshot_packet is None or next_packet is None or is_snapshot_or_reset(next_packet)
            else next_packet.prev_final_update_id == snapshot_packet.final_update_id
        )
        details.append(
            {
                "segment_id": segment.segment_id,
                "start_reason": segment.start_reason,
                "boundary_reason": segment.boundary_reason,
                "packet_count": len(segment.packets),
                "contains_snapshot_reset_packet": contains_snapshot,
                "snapshot_packet_position_in_segment": snapshot_pos,
                "first_packet_is_snapshot_reset": first_packet_is_snapshot,
                "sequence_gap_count": result.sequence_gap_count,
                "warmup_none_count": result.warmup_none_count,
                "ofi_emitted_count": result.ofi_emitted_count,
                "previous_final_update_id": None if snapshot_pos is None else snapshot_packet.prev_final_update_id,
                "snapshot_packet_final_update_id": None if snapshot_pos is None else snapshot_packet.final_update_id,
                "next_packet_prev_final_update_id": None if next_packet is None else next_packet.prev_final_update_id,
                "next_packet_chains_to_snapshot": next_chains,
            }
        )
        if primary_dirty_snapshot_index is None and snapshot_pos is not None:
            primary_dirty_snapshot_index = snapshot_pos
            primary_snapshot_final_update_id = snapshot_packet.final_update_id if snapshot_packet else None
            primary_next_prev_final_update_id = None if next_packet is None else next_packet.prev_final_update_id
            primary_next_chains = next_chains

    summary = {
        "dirty_segment_contains_snapshot_reset": contains_snapshot,
        "dirty_segment_first_packet_is_snapshot_reset": first_packet_is_snapshot,
        "snapshot_packet_position_in_dirty_segment": primary_dirty_snapshot_index,
        "snapshot_packet_final_update_id": primary_snapshot_final_update_id,
        "next_packet_after_snapshot_prev_final_update_id": primary_next_prev_final_update_id,
        "next_packet_chains_to_snapshot": primary_next_chains,
    }
    return details, summary


def _classify_root_cause(*, first_packet_is_snapshot_reset: bool, dirty_segment_contains_snapshot_reset: bool, next_packet_chains_to_snapshot: bool | None, dirty_segment_count: int) -> tuple[bool, bool, bool, str]:
    hypothesis_a = first_packet_is_snapshot_reset
    hypothesis_b = bool(dirty_segment_contains_snapshot_reset and next_packet_chains_to_snapshot is False)
    hypothesis_c = bool(dirty_segment_contains_snapshot_reset and next_packet_chains_to_snapshot is True and dirty_segment_count > 0)

    if hypothesis_b:
        classification = "post_snapshot_chain_failure"
    elif hypothesis_c:
        classification = "snapshot_seed_insufficient"
    elif hypothesis_a:
        classification = "first_packet_snapshot_reset"
    else:
        classification = "unknown"
    return hypothesis_a, hypothesis_b, hypothesis_c, classification


def preview_candidate_file(path: Path, *, reason: str, max_events_per_file: int, context_packets_around_snapshot: int) -> SnapshotDirtyCaseResult:
    frame = _read_parquet_preview(path, max_events_per_file)
    packets, counters = _packets_from_frame(frame)
    ordered_packets, segments, results = _segment_and_replay(packets)
    _ = _source_gap_count(ordered_packets)
    summary = summarize_segments(segments, results)
    dirty_segments, dirty_summary = _dirty_segment_details(segments, results, ordered_packets)
    snapshot_context_windows, snapshot_summary = _analyze_snapshot_context(ordered_packets, context_packets_around_snapshot)
    source_gap_boundary_count = sum(1 for segment in segments if segment.boundary_reason == "source_sequence_gap")
    snapshot_reset_boundary_count = sum(1 for segment in segments if segment.boundary_reason == "snapshot_or_reset")
    hypothesis_a, hypothesis_b, hypothesis_c, classification = _classify_root_cause(
        first_packet_is_snapshot_reset=bool(snapshot_summary["first_packet_is_snapshot_reset"]),
        dirty_segment_contains_snapshot_reset=bool(dirty_summary["dirty_segment_contains_snapshot_reset"]),
        next_packet_chains_to_snapshot=snapshot_summary["next_packet_chains_to_snapshot"],
        dirty_segment_count=summary["dirty_segment_count"],
    )
    dirty_segment_ids = tuple(detail["segment_id"] for detail in dirty_segments)

    return SnapshotDirtyCaseResult(
        file_path=path.as_posix(),
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        rows_scanned=counters["rows_scanned"],
        packet_count=len(ordered_packets),
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if is_snapshot_or_reset(packet)),
        snapshot_like_packet_indexes=snapshot_summary["snapshot_like_packet_indexes"],
        first_packet_is_snapshot_reset=bool(snapshot_summary["first_packet_is_snapshot_reset"]),
        segment_count=summary["segment_count"],
        snapshot_reset_boundary_count=snapshot_reset_boundary_count,
        source_gap_boundary_count=source_gap_boundary_count,
        dirty_segment_count=summary["dirty_segment_count"],
        clean_segment_count=summary["clean_segment_count"],
        all_segments_clean=bool(summary["all_segments_clean"]),
        total_ofi_emitted_count=int(summary["total_ofi_emitted_count"]),
        total_warmup_none_count=int(summary["total_warmup_none_count"]),
        total_sequence_gap_count=int(summary["total_sequence_gap_count"]),
        dirty_segment_ids=dirty_segment_ids,
        dirty_segment_contains_snapshot_reset=bool(dirty_summary["dirty_segment_contains_snapshot_reset"]),
        snapshot_packet_position_in_dirty_segment=dirty_summary["snapshot_packet_position_in_dirty_segment"],
        dirty_segment_first_packet_is_snapshot_reset=bool(dirty_summary["dirty_segment_first_packet_is_snapshot_reset"]),
        next_packet_after_snapshot_prev_final_update_id=dirty_summary["next_packet_after_snapshot_prev_final_update_id"],
        snapshot_packet_final_update_id=dirty_summary["snapshot_packet_final_update_id"],
        next_packet_chains_to_snapshot=dirty_summary["next_packet_chains_to_snapshot"],
        hypothesis_a_first_packet_snapshot_supported=hypothesis_a,
        hypothesis_b_next_packet_chain_failure_supported=hypothesis_b,
        hypothesis_c_seed_insufficient_supported=hypothesis_c,
        root_cause_classification=classification,
        policy_module_used_directly=True,
        side_mapping_unknown_count=counters["unknown_side_row_count"],
        snapshot_context_windows=snapshot_context_windows,
        dirty_segment_details=tuple(dirty_segments),
    )


def build_candidate_inputs(candidate_file_args: list[str] | None) -> list[CandidateFile]:
    if candidate_file_args:
        return [CandidateFile(path=Path(path), reason="override_dirty_snapshot_candidate") for path in candidate_file_args]
    return [CandidateFile(path=Path(path), reason="dirty_snapshot_reset_candidate") for path, _ in DEFAULT_CANDIDATE_INPUTS]


def build_report(*, candidate_inputs: list[CandidateFile], results: list[SnapshotDirtyCaseResult], max_events_per_file: int, context_packets_around_snapshot: int) -> str:
    selected_candidate_count = len(candidate_inputs)
    total_rows_scanned = sum(result.rows_scanned for result in results)
    total_packet_count = sum(result.packet_count for result in results)
    total_snapshot_like_packet_count = sum(result.snapshot_like_packet_count for result in results)
    files_with_first_packet_snapshot_reset = sum(1 for result in results if result.first_packet_is_snapshot_reset)
    total_segment_count = sum(result.segment_count for result in results)
    total_snapshot_reset_boundary_count = sum(result.snapshot_reset_boundary_count for result in results)
    total_source_gap_boundary_count = sum(result.source_gap_boundary_count for result in results)
    files_all_segments_clean = sum(1 for result in results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in results if result.dirty_segment_count > 0)
    total_dirty_segment_count = sum(result.dirty_segment_count for result in results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in results)
    hypothesis_a_supported_file_count = sum(1 for result in results if result.hypothesis_a_first_packet_snapshot_supported)
    hypothesis_b_supported_file_count = sum(1 for result in results if result.hypothesis_b_next_packet_chain_failure_supported)
    hypothesis_c_supported_file_count = sum(1 for result in results if result.hypothesis_c_seed_insufficient_supported)
    if any(result.hypothesis_c_seed_insufficient_supported for result in results):
        root_cause_label = "snapshot_seed_insufficient"
    elif any(result.hypothesis_b_next_packet_chain_failure_supported for result in results):
        root_cause_label = "post_snapshot_chain_failure"
    elif any(result.hypothesis_a_first_packet_snapshot_supported for result in results):
        root_cause_label = "first_packet_snapshot_reset"
    else:
        root_cause_label = "unknown"

    decision_labels = [
        "policy_module_used_directly",
        "dirty_snapshot_candidates_used_deterministically",
        "raw_snapshot_reset_packets_observed",
        "dirty_segments_associated_with_snapshot_reset",
        "snapshot_first_packet_hypothesis_evaluated",
        "post_snapshot_chain_hypothesis_evaluated",
        "snapshot_seed_insufficient_hypothesis_evaluated",
        "root_cause_classified_bounded_only",
        "no_policy_change_made",
        "no_ofi_engine_change_made",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    lines = [
        "# V9.2 L2 OFI Snapshot/Reset Dirty Case Diagnostic",
        "",
        "## Purpose",
        "Determine why the observed raw snapshot/reset-like candidate files remained dirty under the reusable segmented OFI reconstruction policy.",
        "",
        "## Inputs",
        f"- `max_events_per_file`: `{max_events_per_file}`",
        f"- `context_packets_around_snapshot`: `{context_packets_around_snapshot}`",
        f"- `selected_candidate_count`: `{selected_candidate_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded diagnostic only.",
        "- No OFI artifacts are written.",
        "- No policy or OFIEngine behavior is changed.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Diagnostic Method",
        "- Raw rows were converted to `L2Packet` objects in memory.",
        "- Packets were ordered using the reusable policy `packet_sort_key`.",
        "- Snapshot/reset-like packets were identified with `is_snapshot_or_reset`.",
        "- Segmentation and OFIEngine replay were delegated to the reusable policy module.",
        "",
        "## Candidate Files",
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
        "## Executive Finding",
        f"{selected_candidate_count} dirty snapshot/reset candidate files were processed in bounded read-only mode.",
        f"Raw snapshot/reset-like packets were observed in `{sum(1 for result in results if result.snapshot_like_packet_count > 0)}` files.",
        f"Dirty snapshot/reset candidates remained dirty in `{files_with_dirty_segments}` files.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Per-File Dirty Case Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "file_date": result.file_date,
                    "file_hour": result.file_hour,
                    "rows_scanned": result.rows_scanned,
                    "packet_count": result.packet_count,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "snapshot_like_packet_indexes": result.snapshot_like_packet_indexes,
                    "first_packet_is_snapshot_reset": result.first_packet_is_snapshot_reset,
                    "segment_count": result.segment_count,
                    "snapshot_reset_boundary_count": result.snapshot_reset_boundary_count,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "dirty_segment_ids": result.dirty_segment_ids,
                    "dirty_segment_contains_snapshot_reset": result.dirty_segment_contains_snapshot_reset,
                    "snapshot_packet_position_in_dirty_segment": result.snapshot_packet_position_in_dirty_segment,
                    "dirty_segment_first_packet_is_snapshot_reset": result.dirty_segment_first_packet_is_snapshot_reset,
                    "next_packet_after_snapshot_prev_final_update_id": result.next_packet_after_snapshot_prev_final_update_id,
                    "snapshot_packet_final_update_id": result.snapshot_packet_final_update_id,
                    "next_packet_chains_to_snapshot": result.next_packet_chains_to_snapshot,
                    "hypothesis_a_first_packet_snapshot_supported": result.hypothesis_a_first_packet_snapshot_supported,
                    "hypothesis_b_next_packet_chain_failure_supported": result.hypothesis_b_next_packet_chain_failure_supported,
                    "hypothesis_c_seed_insufficient_supported": result.hypothesis_c_seed_insufficient_supported,
                    "root_cause_classification": result.root_cause_classification,
                }
                for result in results
            ],
            [
                "file_path",
                "file_date",
                "file_hour",
                "rows_scanned",
                "packet_count",
                "snapshot_like_packet_count",
                "snapshot_like_packet_indexes",
                "first_packet_is_snapshot_reset",
                "segment_count",
                "snapshot_reset_boundary_count",
                "source_gap_boundary_count",
                "dirty_segment_count",
                "clean_segment_count",
                "all_segments_clean",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "dirty_segment_ids",
                "dirty_segment_contains_snapshot_reset",
                "snapshot_packet_position_in_dirty_segment",
                "dirty_segment_first_packet_is_snapshot_reset",
                "next_packet_after_snapshot_prev_final_update_id",
                "snapshot_packet_final_update_id",
                "next_packet_chains_to_snapshot",
                "hypothesis_a_first_packet_snapshot_supported",
                "hypothesis_b_next_packet_chain_failure_supported",
                "hypothesis_c_seed_insufficient_supported",
                "root_cause_classification",
            ],
        ),
        "",
        "## Snapshot Context Windows",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "snapshot_packet_indexes": result.snapshot_like_packet_indexes,
                    "snapshot_context_windows": result.snapshot_context_windows,
                }
                for result in results
            ],
            ["file_path", "snapshot_packet_indexes", "snapshot_context_windows"],
        ),
        "",
        "## Dirty Segment Anatomy",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "dirty_segment_details": result.dirty_segment_details,
                }
                for result in results
            ],
            ["file_path", "dirty_segment_details"],
        ),
        "",
        "## Hypothesis A: First Packet Snapshot/Reset",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "first_packet_is_snapshot_reset": result.first_packet_is_snapshot_reset,
                    "hypothesis_a_first_packet_snapshot_supported": result.hypothesis_a_first_packet_snapshot_supported,
                }
                for result in results
            ],
            ["file_path", "first_packet_is_snapshot_reset", "hypothesis_a_first_packet_snapshot_supported"],
        ),
        "",
        "## Hypothesis B: Post-Snapshot Chain Failure",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "dirty_segment_contains_snapshot_reset": result.dirty_segment_contains_snapshot_reset,
                    "next_packet_after_snapshot_prev_final_update_id": result.next_packet_after_snapshot_prev_final_update_id,
                    "snapshot_packet_final_update_id": result.snapshot_packet_final_update_id,
                    "next_packet_chains_to_snapshot": result.next_packet_chains_to_snapshot,
                    "hypothesis_b_next_packet_chain_failure_supported": result.hypothesis_b_next_packet_chain_failure_supported,
                }
                for result in results
            ],
            [
                "file_path",
                "dirty_segment_contains_snapshot_reset",
                "next_packet_after_snapshot_prev_final_update_id",
                "snapshot_packet_final_update_id",
                "next_packet_chains_to_snapshot",
                "hypothesis_b_next_packet_chain_failure_supported",
            ],
        ),
        "",
        "## Hypothesis C: Snapshot Seed Insufficient",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "dirty_segment_contains_snapshot_reset": result.dirty_segment_contains_snapshot_reset,
                    "dirty_segment_first_packet_is_snapshot_reset": result.dirty_segment_first_packet_is_snapshot_reset,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "hypothesis_c_seed_insufficient_supported": result.hypothesis_c_seed_insufficient_supported,
                }
                for result in results
            ],
            [
                "file_path",
                "dirty_segment_contains_snapshot_reset",
                "dirty_segment_first_packet_is_snapshot_reset",
                "dirty_segment_count",
                "all_segments_clean",
                "hypothesis_c_seed_insufficient_supported",
            ],
        ),
        "",
        "## Aggregate Summary",
        _markdown_table(
            [
                {
                    "selected_candidate_count": selected_candidate_count,
                    "total_rows_scanned": total_rows_scanned,
                    "total_packet_count": total_packet_count,
                    "total_snapshot_like_packet_count": total_snapshot_like_packet_count,
                    "files_with_first_packet_snapshot_reset": files_with_first_packet_snapshot_reset,
                    "total_segment_count": total_segment_count,
                    "total_snapshot_reset_boundary_count": total_snapshot_reset_boundary_count,
                    "total_source_gap_boundary_count": total_source_gap_boundary_count,
                    "files_all_segments_clean": files_all_segments_clean,
                    "files_with_dirty_segments": files_with_dirty_segments,
                    "total_dirty_segment_count": total_dirty_segment_count,
                    "total_sequence_gap_count": total_sequence_gap_count,
                    "hypothesis_a_supported_file_count": hypothesis_a_supported_file_count,
                    "hypothesis_b_supported_file_count": hypothesis_b_supported_file_count,
                    "hypothesis_c_supported_file_count": hypothesis_c_supported_file_count,
                }
            ],
            [
                "selected_candidate_count",
                "total_rows_scanned",
                "total_packet_count",
                "total_snapshot_like_packet_count",
                "files_with_first_packet_snapshot_reset",
                "total_segment_count",
                "total_snapshot_reset_boundary_count",
                "total_source_gap_boundary_count",
                "files_all_segments_clean",
                "files_with_dirty_segments",
                "total_dirty_segment_count",
                "total_sequence_gap_count",
                "hypothesis_a_supported_file_count",
                "hypothesis_b_supported_file_count",
                "hypothesis_c_supported_file_count",
            ],
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- The dirty snapshot/reset candidate files were used deterministically.",
        "- Snapshot/reset-like packets were observed in the bounded raw sample.",
        "- The diagnostic remained in-memory and read-only.",
        "",
        "## What Failed Or Remains Unknown",
        "- The observed snapshot/reset-like packets did not produce clean segmented OFI processing in this bounded sample.",
        "- No policy or OFIEngine behavior was changed.",
        "- A different bounded sample could still produce a different hypothesis mix.",
        "",
        "## What Is Safe",
        "- Bounded read-only diagnostics on the discovered dirty snapshot/reset files.",
        "- Using the observed patterns for future bounded diagnostics.",
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
        "Use the dirty snapshot/reset candidates only for bounded follow-up diagnostics; do not change the policy or promote the workflow to full reconstruction.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_validation(*, max_events_per_file: int, context_packets_around_snapshot: int, output_doc: Path, candidate_file_args: list[str] | None) -> dict[str, Any]:
    candidate_inputs = build_candidate_inputs(candidate_file_args)
    results = [
        preview_candidate_file(
            candidate.path,
            reason=candidate.reason,
            max_events_per_file=max_events_per_file,
            context_packets_around_snapshot=context_packets_around_snapshot,
        )
        for candidate in candidate_inputs
    ]
    report = build_report(
        candidate_inputs=candidate_inputs,
        results=results,
        max_events_per_file=max_events_per_file,
        context_packets_around_snapshot=context_packets_around_snapshot,
    )
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(report, encoding="utf-8")
    return {
        "selected_candidate_count": len(candidate_inputs),
        "total_rows_scanned": sum(result.rows_scanned for result in results),
        "total_packet_count": sum(result.packet_count for result in results),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_validation(
        max_events_per_file=args.max_events_per_file,
        context_packets_around_snapshot=args.context_packets_around_snapshot,
        output_doc=args.output_doc,
        candidate_file_args=args.candidate_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
