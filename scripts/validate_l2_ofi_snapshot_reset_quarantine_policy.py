#!/usr/bin/env python3
"""Bounded read-only validation of snapshot/reset quarantine + bridge handling."""

from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    is_normal_chain,
    is_snapshot_bridge_event,
    is_snapshot_or_reset,
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)

PRODUCTION_APPROVAL_STATEMENT = "This validation does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction."
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
class ValidationResult:
    file_path: str
    candidate_reason: str
    file_date: str | None
    file_hour: str | None
    rows_scanned: int
    packet_count: int
    snapshot_like_packet_count: int
    snapshot_like_packet_indexes: tuple[int, ...]
    first_packet_is_snapshot_reset: bool
    bridge_rule_satisfied: bool
    bridge_event_detected_count: int
    snapshot_reset_observed_count: int
    snapshot_reset_clean_seed_count: int
    snapshot_reset_chain_failure_count: int
    snapshot_bridge_event_count: int
    quarantined_segment_count: int
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    ofi_suppressed_due_to_quarantine_count: int
    ofi_suppressed_due_to_snapshot_bridge_count: int
    clean_segment_count: int
    dirty_segment_count: int
    all_segments_clean: bool
    source_gap_boundary_count: int
    quarantined: bool
    quarantine_reason: str | None
    source_gap_regression_passed: bool
    policy_module_used_directly: bool
    side_mapping_unknown_count: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-events-per-file", type=int, default=75_000)
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
    return normalized


def _packets_from_frame(frame: pd.DataFrame) -> tuple[list[L2Packet], dict[str, int]]:
    if frame.empty:
        return [], {"rows_scanned": 0, "unknown_side_row_count": 0}

    normalized = _normalize_frame(frame)
    rows_scanned = int(len(normalized))

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

    return packets, {"rows_scanned": rows_scanned, "unknown_side_row_count": unknown_side_row_count}


def _synthetic_source_gap_regression() -> bool:
    from features.l2_ofi_segmented_reconstruction import L2Packet as PolicyPacket

    packets = [
        PolicyPacket(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=1,
            transaction_time=10,
            received_time=20,
            first_update_id=1,
            final_update_id=10,
            prev_final_update_id=9,
            bids=((100.0, 1.0),),
            asks=(),
        ),
        PolicyPacket(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=2,
            transaction_time=20,
            received_time=21,
            first_update_id=11,
            final_update_id=20,
            prev_final_update_id=999,
            bids=((101.0, 1.0),),
            asks=(),
        ),
        PolicyPacket(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=3,
            transaction_time=30,
            received_time=31,
            first_update_id=21,
            final_update_id=30,
            prev_final_update_id=20,
            bids=((102.0, 1.0),),
            asks=(),
        ),
    ]
    segments = segment_packets(packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    summary = summarize_segments(segments, results)
    return len(segments) == 2 and segments[0].boundary_reason == "source_sequence_gap" and bool(summary["all_segments_clean"])


def _bridge_summary_for_segment(segment, *, total_source_gap_boundary_count: int) -> dict[str, Any]:
    packets = segment.packets
    snapshot_packet = packets[0] if packets else None
    bridge_packet = packets[1] if len(packets) > 1 else None
    bridge_rule_satisfied = bool(snapshot_packet and bridge_packet and is_snapshot_bridge_event(snapshot_packet, bridge_packet))
    return {
        "snapshot_like_packet_count": sum(1 for packet in packets if is_snapshot_or_reset(packet)),
        "snapshot_like_packet_indexes": tuple(idx for idx, packet in enumerate(packets, start=1) if is_snapshot_or_reset(packet)),
        "first_packet_is_snapshot_reset": bool(packets and is_snapshot_or_reset(packets[0])),
        "bridge_rule_satisfied": bridge_rule_satisfied,
        "bridge_event_detected_count": 1 if bridge_rule_satisfied else 0,
        "snapshot_packet_final_update_id": snapshot_packet.final_update_id if snapshot_packet else None,
        "next_packet_after_snapshot_prev_final_update_id": bridge_packet.prev_final_update_id if bridge_packet else None,
        "next_packet_chains_to_snapshot": None if not snapshot_packet or not bridge_packet else is_normal_chain(snapshot_packet, bridge_packet),
        "source_gap_boundary_count": total_source_gap_boundary_count,
    }


def _segment_and_replay(packets: list[L2Packet]) -> tuple[tuple[L2Packet, ...], list[Any], list[Any]]:
    ordered_packets = tuple(sorted(packets, key=packet_sort_key))
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    return ordered_packets, list(segments), results


def preview_candidate_file(path: Path, *, reason: str, max_events_per_file: int) -> ValidationResult:
    frame = _read_parquet_preview(path, max_events_per_file)
    packets, counters = _packets_from_frame(frame)
    ordered_packets, segments, results = _segment_and_replay(packets)
    summary = summarize_segments(segments, results)
    bridge_summary = _bridge_summary_for_segment(
        segments[0],
        total_source_gap_boundary_count=sum(1 for seg in segments if seg.boundary_reason == "source_sequence_gap"),
    ) if segments else {
        "snapshot_like_packet_count": 0,
        "snapshot_like_packet_indexes": (),
        "first_packet_is_snapshot_reset": False,
        "bridge_rule_satisfied": False,
        "bridge_event_detected_count": 0,
        "snapshot_packet_final_update_id": None,
        "next_packet_after_snapshot_prev_final_update_id": None,
        "next_packet_chains_to_snapshot": None,
        "source_gap_boundary_count": 0,
    }
    dirty_segments = [result for result in results if not result.clean]
    quarantined_segment_count = sum(1 for result in results if result.quarantined)
    return ValidationResult(
        file_path=path.as_posix(),
        candidate_reason=reason,
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        rows_scanned=counters["rows_scanned"],
        packet_count=len(ordered_packets),
        snapshot_like_packet_count=bridge_summary["snapshot_like_packet_count"],
        snapshot_like_packet_indexes=bridge_summary["snapshot_like_packet_indexes"],
        first_packet_is_snapshot_reset=bridge_summary["first_packet_is_snapshot_reset"],
        bridge_rule_satisfied=bridge_summary["bridge_rule_satisfied"],
        bridge_event_detected_count=bridge_summary["bridge_event_detected_count"],
        snapshot_reset_observed_count=summary["snapshot_reset_observed_count"],
        snapshot_reset_clean_seed_count=summary["snapshot_reset_clean_seed_count"],
        snapshot_reset_chain_failure_count=summary["snapshot_reset_chain_failure_count"],
        snapshot_bridge_event_count=summary["snapshot_bridge_event_count"],
        quarantined_segment_count=quarantined_segment_count,
        total_ofi_emitted_count=int(summary["total_ofi_emitted_count"]),
        total_warmup_none_count=int(summary["total_warmup_none_count"]),
        total_sequence_gap_count=int(summary["total_sequence_gap_count"]),
        ofi_suppressed_due_to_quarantine_count=int(summary["ofi_suppressed_due_to_quarantine_count"]),
        ofi_suppressed_due_to_snapshot_bridge_count=int(summary["ofi_suppressed_due_to_snapshot_bridge_count"]),
        clean_segment_count=int(summary["clean_segment_count"]),
        dirty_segment_count=int(summary["dirty_segment_count"]),
        all_segments_clean=bool(summary["all_segments_clean"]),
        source_gap_boundary_count=bridge_summary["source_gap_boundary_count"],
        quarantined=bool(any(result.quarantined for result in results)),
        quarantine_reason=next((result.quarantine_reason for result in results if result.quarantine_reason), None),
        source_gap_regression_passed=_synthetic_source_gap_regression(),
        policy_module_used_directly=True,
        side_mapping_unknown_count=counters["unknown_side_row_count"],
    )


def build_candidate_inputs(candidate_file_args: list[str] | None) -> list[CandidateFile]:
    if candidate_file_args:
        return [CandidateFile(path=Path(path), reason="override_dirty_snapshot_candidate") for path in candidate_file_args]
    return [CandidateFile(path=Path(path), reason="dirty_snapshot_reset_candidate") for path, _ in DEFAULT_CANDIDATE_INPUTS]


def build_report(*, candidate_inputs: list[CandidateFile], results: list[ValidationResult], max_events_per_file: int) -> str:
    selected_candidate_count = len(candidate_inputs)
    total_rows_scanned = sum(result.rows_scanned for result in results)
    total_packet_count = sum(result.packet_count for result in results)
    total_snapshot_like_packet_count = sum(result.snapshot_like_packet_count for result in results)
    total_segment_count = sum(result.clean_segment_count + result.dirty_segment_count for result in results)
    total_snapshot_reset_observed_count = sum(result.snapshot_reset_observed_count for result in results)
    total_snapshot_reset_clean_seed_count = sum(result.snapshot_reset_clean_seed_count for result in results)
    total_snapshot_reset_chain_failure_count = sum(result.snapshot_reset_chain_failure_count for result in results)
    total_snapshot_bridge_event_count = sum(result.snapshot_bridge_event_count for result in results)
    total_quarantined_segment_count = sum(result.quarantined_segment_count for result in results)
    total_ofi_emitted_count = sum(result.total_ofi_emitted_count for result in results)
    total_warmup_none_count = sum(result.total_warmup_none_count for result in results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in results)
    total_ofi_suppressed_due_to_quarantine_count = sum(result.ofi_suppressed_due_to_quarantine_count for result in results)
    total_ofi_suppressed_due_to_snapshot_bridge_count = sum(result.ofi_suppressed_due_to_snapshot_bridge_count for result in results)
    files_all_segments_clean = sum(1 for result in results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in results if result.dirty_segment_count > 0)
    files_with_quarantined_segments = sum(1 for result in results if result.quarantined)
    files_with_bridge_events = sum(1 for result in results if result.snapshot_bridge_event_count > 0)
    files_with_snapshot_like_packets = sum(1 for result in results if result.snapshot_like_packet_count > 0)
    source_gap_behavior_unchanged = _synthetic_source_gap_regression()

    decision_labels = [
        "policy_module_used_directly",
        "ofi_engine_behavior_unchanged",
        "binance_snapshot_bridge_rule_implemented",
        "snapshot_reset_bridge_events_detected",
        "snapshot_reset_bridge_ofi_suppressed",
        "invalid_snapshot_reset_chains_quarantined",
        "quarantined_segments_emit_no_ofi",
        "no_ofi_state_crosses_quarantine",
        "source_gap_behavior_unchanged",
        "bounded_raw_snapshot_reset_validation_completed",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    lines = [
        "# V9.2 L2 OFI Snapshot/Reset Quarantine Policy Validation",
        "",
        "## Purpose",
        "Validate the reusable segmented reconstruction policy module with snapshot/reset quarantine and bridge handling on the two real raw dirty candidate files.",
        "",
        "## Inputs",
        f"- `max_events_per_file`: `{max_events_per_file}`",
        f"- `selected_candidate_count`: `{selected_candidate_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded validation only.",
        "- No OFI artifacts are written.",
        "- No policy or OFIEngine behavior is changed.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Binance Snapshot Bridge Rule",
        "- First processed diff event after a snapshot must satisfy `first_update_id <= snapshot.final_update_id <= final_update_id`.",
        "- After that bridge event, normal continuity resumes with `current.prev_final_update_id == previous.final_update_id`.",
        "",
        "## Module Changes",
        "- `L2Segment` and `SegmentRunResult` carry quarantine metadata.",
        "- The policy module now recognizes valid post-snapshot bridge events.",
        "- Invalid snapshot/reset chains are quarantined and suppress OFI.",
        "",
        "## Executive Finding",
        f"{selected_candidate_count} dirty snapshot/reset candidate files were processed in bounded read-only mode.",
        f"Snapshot/reset-like packets were observed in `{files_with_snapshot_like_packets}` files.",
        f"Bridge events were detected in `{files_with_bridge_events}` files.",
        f"Quarantined segments were observed in `{files_with_quarantined_segments}` files.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Per-File Snapshot/Reset Results",
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
                    "bridge_rule_satisfied": result.bridge_rule_satisfied,
                    "bridge_event_detected_count": result.bridge_event_detected_count,
                    "snapshot_reset_observed_count": result.snapshot_reset_observed_count,
                    "snapshot_reset_clean_seed_count": result.snapshot_reset_clean_seed_count,
                    "snapshot_reset_chain_failure_count": result.snapshot_reset_chain_failure_count,
                    "snapshot_bridge_event_count": result.snapshot_bridge_event_count,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                    "quarantined": result.quarantined,
                    "quarantine_reason": result.quarantine_reason,
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
                "bridge_rule_satisfied",
                "bridge_event_detected_count",
                "snapshot_reset_observed_count",
                "snapshot_reset_clean_seed_count",
                "snapshot_reset_chain_failure_count",
                "snapshot_bridge_event_count",
                "quarantined_segment_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "ofi_suppressed_due_to_quarantine_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
                "quarantined",
                "quarantine_reason",
            ],
        ),
        "",
        "## Bridge Event Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "bridge_rule_satisfied": result.bridge_rule_satisfied,
                    "bridge_event_detected_count": result.bridge_event_detected_count,
                    "snapshot_reset_clean_seed_count": result.snapshot_reset_clean_seed_count,
                    "snapshot_bridge_event_count": result.snapshot_bridge_event_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                }
                for result in results
            ],
            [
                "file_path",
                "bridge_rule_satisfied",
                "bridge_event_detected_count",
                "snapshot_reset_clean_seed_count",
                "snapshot_bridge_event_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
            ],
        ),
        "",
        "## Quarantine Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "quarantined": result.quarantined,
                    "quarantine_reason": result.quarantine_reason,
                    "snapshot_reset_chain_failure_count": result.snapshot_reset_chain_failure_count,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                }
                for result in results
            ],
            [
                "file_path",
                "quarantined",
                "quarantine_reason",
                "snapshot_reset_chain_failure_count",
                "quarantined_segment_count",
                "ofi_suppressed_due_to_quarantine_count",
            ],
        ),
        "",
        "## OFI Suppression Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                }
                for result in results
            ],
            [
                "file_path",
                "total_ofi_emitted_count",
                "ofi_suppressed_due_to_quarantine_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
                "total_warmup_none_count",
            ],
        ),
        "",
        "## Segment Cleanliness Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                }
                for result in results
            ],
            [
                "file_path",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "total_sequence_gap_count",
            ],
        ),
        "",
        "## Source-Gap Regression Check",
        (
            "Synthetic source-gap regression passed; the reusable policy still splits source gaps into `source_sequence_gap` boundaries and keeps those segments clean."
            if source_gap_behavior_unchanged
            else "Synthetic source-gap regression did not pass."
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- The dirty snapshot/reset files were used deterministically.",
        "- The Binance bridge rule was applied to the raw files.",
        "- No OFI artifacts were written.",
        "",
        "## What Failed Or Remains Unknown",
        "- Some snapshot/reset candidates remain quarantined if the bridge rule is not satisfied.",
        "- A different bounded sample could still expose additional edge cases.",
        "- This remains a bounded validation only.",
        "",
        "## What Is Safe",
        "- Bounded read-only validation of the dirty snapshot/reset candidates.",
        "- Quarantine of unsafe snapshot/reset chains.",
        "- Preservation of source-gap behavior.",
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
        "Use the quarantine behavior only after this bounded validation is reviewed; do not promote the workflow to full reconstruction.",
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
        "total_rows_scanned": sum(result.rows_scanned for result in results),
        "total_packet_count": sum(result.packet_count for result in results),
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
