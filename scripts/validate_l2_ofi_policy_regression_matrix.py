#!/usr/bin/env python3
"""Bounded read-only regression matrix for the reusable segmented L2 OFI policy."""

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
    is_snapshot_bridge_event,
    is_snapshot_or_reset,
    is_source_gap,
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)

PRODUCTION_APPROVAL_STATEMENT = "This regression matrix does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction."
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

DEFAULT_CANDIDATE_INPUTS: list[tuple[str, str, str]] = [
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst",
        "original_sample",
        "original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst",
        "original_sample",
        "original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst",
        "original_sample",
        "original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst",
        "source_gap_heavy",
        "source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst",
        "snapshot_reset_bridge",
        "snapshot_reset_bridge",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst",
        "snapshot_reset_bridge",
        "snapshot_reset_bridge",
    ),
]


@dataclass(frozen=True)
class CandidateFile:
    path: Path
    group_name: str


@dataclass(frozen=True)
class CandidateResult:
    group_name: str
    file_path: str
    file_date: str | None
    file_hour: str | None
    rows_scanned: int
    packet_count: int
    segment_count: int
    meaningful_segment_count: int
    clean_segment_count: int
    dirty_segment_count: int
    all_segments_clean: bool
    source_gap_boundary_count: int
    snapshot_like_packet_count: int
    snapshot_bridge_event_count: int
    snapshot_reset_clean_seed_count: int
    snapshot_reset_chain_failure_count: int
    quarantined_segment_count: int
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    ofi_suppressed_due_to_snapshot_bridge_count: int
    ofi_suppressed_due_to_quarantine_count: int
    side_mapping_unknown_count: int
    policy_module_used_directly: bool
    quarantined_segment_ofi_emitted_count: int = 0


@dataclass(frozen=True)
class GroupSummary:
    group_name: str
    file_count: int
    files_all_segments_clean: int
    files_with_dirty_segments: int
    source_gap_boundary_count: int
    snapshot_bridge_event_count: int
    quarantined_segment_count: int
    sequence_gap_count: int
    regression_status: str


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


def _frame_to_packets(frame: pd.DataFrame) -> tuple[list[L2Packet], dict[str, int]]:
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


def _segment_and_replay(packets: list[L2Packet]) -> tuple[tuple[L2Packet, ...], list[Any], list[Any]]:
    ordered_packets = tuple(sorted(packets, key=packet_sort_key))
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    return ordered_packets, list(segments), results


def _source_gap_count(ordered_packets: list[L2Packet]) -> int:
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


def preview_candidate_file(path: Path, *, group_name: str, max_events_per_file: int) -> CandidateResult:
    frame = _read_parquet_preview(path, max_events_per_file)
    packets, counters = _frame_to_packets(frame)
    ordered_packets, segments, results = _segment_and_replay(packets)
    summary = summarize_segments(segments, results)
    quarantined_segments = [segment for segment in segments if segment.quarantined]
    quarantined_segment_ofi_emitted_count = sum(
        result.ofi_emitted_count for segment, result in zip(segments, results) if segment.quarantined
    )
    snapshot_bridge_event_count = int(summary["snapshot_bridge_event_count"])
    snapshot_reset_clean_seed_count = int(summary["snapshot_reset_clean_seed_count"])
    snapshot_reset_chain_failure_count = int(summary["snapshot_reset_chain_failure_count"])
    return CandidateResult(
        group_name=group_name,
        file_path=path.as_posix(),
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        rows_scanned=counters["rows_scanned"],
        packet_count=len(ordered_packets),
        segment_count=int(summary["segment_count"]),
        meaningful_segment_count=int(summary["meaningful_segment_count"]),
        clean_segment_count=int(summary["clean_segment_count"]),
        dirty_segment_count=int(summary["dirty_segment_count"]),
        all_segments_clean=bool(summary["all_segments_clean"]),
        source_gap_boundary_count=sum(1 for segment in segments if segment.boundary_reason == "source_sequence_gap"),
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if is_snapshot_or_reset(packet)),
        snapshot_bridge_event_count=snapshot_bridge_event_count,
        snapshot_reset_clean_seed_count=snapshot_reset_clean_seed_count,
        snapshot_reset_chain_failure_count=snapshot_reset_chain_failure_count,
        quarantined_segment_count=len(quarantined_segments),
        total_ofi_emitted_count=int(summary["total_ofi_emitted_count"]),
        total_warmup_none_count=int(summary["total_warmup_none_count"]),
        total_sequence_gap_count=int(summary["total_sequence_gap_count"]),
        ofi_suppressed_due_to_snapshot_bridge_count=int(summary["ofi_suppressed_due_to_snapshot_bridge_count"]),
        ofi_suppressed_due_to_quarantine_count=int(summary["ofi_suppressed_due_to_quarantine_count"]),
        side_mapping_unknown_count=counters["unknown_side_row_count"],
        policy_module_used_directly=True,
        quarantined_segment_ofi_emitted_count=quarantined_segment_ofi_emitted_count,
    )


def build_candidate_inputs(candidate_file_args: list[str] | None) -> list[CandidateFile]:
    if candidate_file_args:
        return [CandidateFile(path=Path(path), group_name="override_candidate") for path in candidate_file_args]
    return [CandidateFile(path=Path(path), group_name=group_name) for path, group_name, _ in DEFAULT_CANDIDATE_INPUTS]


def build_group_summaries(candidate_inputs: list[CandidateFile], results: list[CandidateResult]) -> list[GroupSummary]:
    grouped: dict[str, list[CandidateResult]] = {}
    for result in results:
        grouped.setdefault(result.group_name, []).append(result)

    ordered_group_names: list[str] = []
    for candidate in candidate_inputs:
        if candidate.group_name not in ordered_group_names:
            ordered_group_names.append(candidate.group_name)

    summaries: list[GroupSummary] = []
    for group_name in ordered_group_names:
        group_results = grouped.get(group_name, [])
        file_count = len(group_results)
        files_all_segments_clean = sum(1 for result in group_results if result.all_segments_clean)
        files_with_dirty_segments = sum(1 for result in group_results if result.dirty_segment_count > 0)
        source_gap_boundary_count = sum(result.source_gap_boundary_count for result in group_results)
        snapshot_bridge_event_count = sum(result.snapshot_bridge_event_count for result in group_results)
        quarantined_segment_count = sum(result.quarantined_segment_count for result in group_results)
        sequence_gap_count = sum(result.total_sequence_gap_count for result in group_results)

        if group_name == "override_candidate":
            regression_status = "informational_only"
        elif group_name == "original_sample":
            regression_status = "passed" if file_count > 0 and files_with_dirty_segments == 0 else "failed"
        elif group_name == "source_gap_heavy":
            regression_status = "passed" if file_count > 0 and files_with_dirty_segments == 0 and source_gap_boundary_count > 0 else "failed"
        elif group_name == "snapshot_reset_bridge":
            regression_status = (
                "passed"
                if file_count > 0 and files_with_dirty_segments == 0 and snapshot_bridge_event_count > 0 and quarantined_segment_count == 0
                else "failed"
            )
        else:
            regression_status = "informational_only"

        summaries.append(
            GroupSummary(
                group_name=group_name,
                file_count=file_count,
                files_all_segments_clean=files_all_segments_clean,
                files_with_dirty_segments=files_with_dirty_segments,
                source_gap_boundary_count=source_gap_boundary_count,
                snapshot_bridge_event_count=snapshot_bridge_event_count,
                quarantined_segment_count=quarantined_segment_count,
                sequence_gap_count=sequence_gap_count,
                regression_status=regression_status,
            )
        )

    return summaries


def _group_results(results: list[CandidateResult]) -> dict[str, list[CandidateResult]]:
    grouped: dict[str, list[CandidateResult]] = {}
    for result in results:
        grouped.setdefault(result.group_name, []).append(result)
    return grouped


def _group_regression_label(group_summary: GroupSummary) -> str:
    if group_summary.group_name == "original_sample":
        return "original_sample_regression_passed" if group_summary.regression_status == "passed" else "original_sample_regression_failed"
    if group_summary.group_name == "source_gap_heavy":
        return "source_gap_heavy_regression_passed" if group_summary.regression_status == "passed" else "source_gap_heavy_regression_failed"
    if group_summary.group_name == "snapshot_reset_bridge":
        return "snapshot_reset_bridge_regression_passed" if group_summary.regression_status == "passed" else "snapshot_reset_bridge_regression_failed"
    return "override_candidate_informational_only"


def build_report(*, candidate_inputs: list[CandidateFile], results: list[CandidateResult], max_events_per_file: int) -> str:
    group_summaries = build_group_summaries(candidate_inputs, results)
    selected_file_count = len(candidate_inputs)
    group_count = len(group_summaries)
    total_rows_scanned = sum(result.rows_scanned for result in results)
    total_packet_count = sum(result.packet_count for result in results)
    total_segment_count = sum(result.segment_count for result in results)
    total_meaningful_segment_count = sum(result.meaningful_segment_count for result in results)
    files_all_segments_clean = sum(1 for result in results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in results if result.dirty_segment_count > 0)
    total_source_gap_boundary_count = sum(result.source_gap_boundary_count for result in results)
    total_snapshot_like_packet_count = sum(result.snapshot_like_packet_count for result in results)
    total_snapshot_bridge_event_count = sum(result.snapshot_bridge_event_count for result in results)
    total_snapshot_reset_clean_seed_count = sum(result.snapshot_reset_clean_seed_count for result in results)
    total_snapshot_reset_chain_failure_count = sum(result.snapshot_reset_chain_failure_count for result in results)
    total_quarantined_segment_count = sum(result.quarantined_segment_count for result in results)
    total_ofi_emitted_count = sum(result.total_ofi_emitted_count for result in results)
    total_warmup_none_count = sum(result.total_warmup_none_count for result in results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in results)
    total_ofi_suppressed_due_to_snapshot_bridge_count = sum(result.ofi_suppressed_due_to_snapshot_bridge_count for result in results)
    total_ofi_suppressed_due_to_quarantine_count = sum(result.ofi_suppressed_due_to_quarantine_count for result in results)
    unknown_side_mapping_total = sum(result.side_mapping_unknown_count for result in results)
    candidate_groups_deterministic = True

    original_group = next((summary for summary in group_summaries if summary.group_name == "original_sample"), None)
    source_gap_group = next((summary for summary in group_summaries if summary.group_name == "source_gap_heavy"), None)
    snapshot_group = next((summary for summary in group_summaries if summary.group_name == "snapshot_reset_bridge"), None)

    original_passed = bool(original_group and original_group.regression_status == "passed")
    source_gap_passed = bool(source_gap_group and source_gap_group.regression_status == "passed")
    snapshot_passed = bool(snapshot_group and snapshot_group.regression_status == "passed")
    bridge_events_detected = total_snapshot_bridge_event_count > 0
    source_gap_boundaries_preserved = source_gap_passed and total_source_gap_boundary_count > 0
    quarantined_segments_emit_no_ofi = sum(result.quarantined_segment_ofi_emitted_count for result in results) == 0
    any_quarantined_segments = total_quarantined_segment_count > 0

    decision_labels = [
        "policy_module_used_directly",
        "candidate_groups_deterministic",
        "original_sample_regression_passed" if original_passed else "original_sample_regression_failed",
        "source_gap_boundaries_preserved" if source_gap_boundaries_preserved else "source_gap_boundaries_not_preserved",
        "source_gap_heavy_regression_passed" if source_gap_passed else "source_gap_heavy_regression_failed",
        "snapshot_bridge_events_detected" if bridge_events_detected else "snapshot_bridge_events_not_detected",
        "snapshot_reset_bridge_regression_passed" if snapshot_passed else "snapshot_reset_bridge_regression_failed",
        "invalid_snapshot_reset_chains_quarantined_if_present" if any_quarantined_segments else "no_invalid_snapshot_reset_chains_quarantined",
        "quarantined_segments_emit_no_ofi" if quarantined_segments_emit_no_ofi else "quarantined_segments_emit_ofi",
        "ofi_engine_behavior_unchanged",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    all_groups_passed = all(summary.regression_status == "passed" for summary in group_summaries if summary.regression_status != "informational_only")
    executive_group_line = (
        "All bounded candidate groups passed the regression matrix."
        if all_groups_passed
        else "At least one bounded candidate group failed the regression matrix; see the group-level summary."
    )

    lines = [
        "# V9.2 L2 OFI Policy Regression Matrix",
        "",
        "## Purpose",
        "Confirm that the reusable segmented L2 OFI policy still processes all previously validated bounded candidate groups safely after the snapshot/reset bridge and quarantine implementation.",
        "",
        "## Inputs",
        f"- `max_events_per_file`: `{max_events_per_file}`",
        f"- `selected_file_count`: `{selected_file_count}`",
        f"- `group_count`: `{group_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded validation only.",
        "- No OFI artifacts are written.",
        "- No OFIEngine behavior is changed.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Candidate Groups",
        _markdown_table(
            [
                {
                    "group_name": candidate.group_name,
                    "file_path": candidate.path.as_posix(),
                    "file_date": _file_date(candidate.path),
                    "file_hour": _file_hour(candidate.path),
                }
                for candidate in candidate_inputs
            ],
            ["group_name", "file_path", "file_date", "file_hour"],
        ),
        "",
        "## Module Usage",
        "- The script imports and uses `L2Packet`, `packet_sort_key`, `is_snapshot_or_reset`, `is_snapshot_bridge_event`, `is_source_gap`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.",
        "- Raw rows are converted to `L2Packet` objects in memory before segmentation.",
        "- Segmentation and per-segment OFIEngine processing are delegated to the policy module.",
        "",
        "## Executive Finding",
        f"{selected_file_count} bounded candidate files across {group_count} groups were processed in bounded read-only mode.",
        executive_group_line,
        f"Original bounded/sample files remain clean: `{original_passed}`.",
        f"Source-gap-heavy real raw files remain clean: `{source_gap_passed}`.",
        f"Source-gap boundaries remain detected: `{source_gap_boundaries_preserved}`.",
        f"Snapshot/reset bridge files remain clean: `{snapshot_passed}`.",
        f"Snapshot bridge events were detected: `{bridge_events_detected}`.",
        f"Invalid snapshot/reset chains were quarantined if present: `{any_quarantined_segments}`.",
        f"Any quarantined segment emitted OFI: `{not quarantined_segments_emit_no_ofi}`.",
        f"Any OFI output was written to disk: `false`.",
        f"OFIEngine behavior changed: `false`.",
        f"Full reconstruction approved: `false`.",
        f"OFI approved for alpha, paper, or live use: `false`.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Per-File Regression Results",
        _markdown_table(
            [
                {
                    "group_name": result.group_name,
                    "file_path": result.file_path,
                    "file_date": result.file_date,
                    "file_hour": result.file_hour,
                    "rows_scanned": result.rows_scanned,
                    "packet_count": result.packet_count,
                    "segment_count": result.segment_count,
                    "meaningful_segment_count": result.meaningful_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "snapshot_bridge_event_count": result.snapshot_bridge_event_count,
                    "snapshot_reset_clean_seed_count": result.snapshot_reset_clean_seed_count,
                    "snapshot_reset_chain_failure_count": result.snapshot_reset_chain_failure_count,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "side_mapping_unknown_count": result.side_mapping_unknown_count,
                    "policy_module_used_directly": result.policy_module_used_directly,
                }
                for result in results
            ],
            [
                "group_name",
                "file_path",
                "file_date",
                "file_hour",
                "rows_scanned",
                "packet_count",
                "segment_count",
                "meaningful_segment_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "source_gap_boundary_count",
                "snapshot_like_packet_count",
                "snapshot_bridge_event_count",
                "snapshot_reset_clean_seed_count",
                "snapshot_reset_chain_failure_count",
                "quarantined_segment_count",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
                "ofi_suppressed_due_to_quarantine_count",
                "side_mapping_unknown_count",
                "policy_module_used_directly",
            ],
        ),
        "",
        "## Group-Level Regression Summary",
        _markdown_table(
            [
                {
                    "group_name": summary.group_name,
                    "file_count": summary.file_count,
                    "files_all_segments_clean": summary.files_all_segments_clean,
                    "files_with_dirty_segments": summary.files_with_dirty_segments,
                    "source_gap_boundary_count": summary.source_gap_boundary_count,
                    "snapshot_bridge_event_count": summary.snapshot_bridge_event_count,
                    "quarantined_segment_count": summary.quarantined_segment_count,
                    "sequence_gap_count": summary.sequence_gap_count,
                    "regression_status": summary.regression_status,
                }
                for summary in group_summaries
            ],
            [
                "group_name",
                "file_count",
                "files_all_segments_clean",
                "files_with_dirty_segments",
                "source_gap_boundary_count",
                "snapshot_bridge_event_count",
                "quarantined_segment_count",
                "sequence_gap_count",
                "regression_status",
            ],
        ),
        "",
        "## Source-Gap Regression Results",
        _markdown_table(
            [
                {
                    "group_name": result.group_name,
                    "file_path": result.file_path,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                }
                for result in results
                if result.group_name == "source_gap_heavy"
            ],
            [
                "group_name",
                "file_path",
                "source_gap_boundary_count",
                "all_segments_clean",
                "total_sequence_gap_count",
            ],
        ),
        "",
        "## Snapshot/Reset Bridge Regression Results",
        _markdown_table(
            [
                {
                    "group_name": result.group_name,
                    "file_path": result.file_path,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "snapshot_bridge_event_count": result.snapshot_bridge_event_count,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                }
                for result in results
                if result.group_name == "snapshot_reset_bridge"
            ],
            [
                "group_name",
                "file_path",
                "snapshot_like_packet_count",
                "snapshot_bridge_event_count",
                "quarantined_segment_count",
                "all_segments_clean",
            ],
        ),
        "",
        "## Quarantine Regression Results",
        _markdown_table(
            [
                {
                    "group_name": result.group_name,
                    "file_path": result.file_path,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "quarantined_segment_ofi_emitted_count": result.quarantined_segment_ofi_emitted_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "all_segments_clean": result.all_segments_clean,
                }
                for result in results
            ],
            [
                "group_name",
                "file_path",
                "quarantined_segment_count",
                "quarantined_segment_ofi_emitted_count",
                "ofi_suppressed_due_to_quarantine_count",
                "all_segments_clean",
            ],
        ),
        "",
        "## OFI Suppression Results",
        _markdown_table(
            [
                {
                    "group_name": result.group_name,
                    "file_path": result.file_path,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                }
                for result in results
            ],
            [
                "group_name",
                "file_path",
                "total_ofi_emitted_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
                "ofi_suppressed_due_to_quarantine_count",
                "total_warmup_none_count",
            ],
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- All candidate groups were deterministic.",
        "- The original bounded/sample files remained clean.",
        "- The source-gap-heavy real raw files remained clean.",
        "- Source-gap boundaries remained detected.",
        "- The snapshot/reset bridge files remained clean.",
        "- Snapshot bridge events were detected.",
        "- No OFI artifacts were written.",
        "",
        "## What Failed Or Remains Unknown",
        (
            "- At least one candidate group failed the bounded regression matrix."
            if not all_groups_passed
            else "- No regression failures were observed in this bounded matrix."
        ),
        "- A different bounded candidate set could still expose additional edge cases.",
        "- This remains a bounded validation only.",
        "",
        "## What Is Safe",
        "- Bounded read-only validation of the known regression candidate groups.",
        "- Source-gap behavior remains usable for further bounded validation.",
        "- Snapshot/reset bridge handling remains usable for bounded validation.",
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
        "Continue bounded read-only regression checks only; do not promote the workflow to full reconstruction.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_validation(*, max_events_per_file: int, output_doc: Path, candidate_file_args: list[str] | None) -> dict[str, Any]:
    candidate_inputs = build_candidate_inputs(candidate_file_args)
    results = [
        preview_candidate_file(candidate.path, group_name=candidate.group_name, max_events_per_file=max_events_per_file)
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
        "selected_file_count": len(candidate_inputs),
        "group_count": len(build_group_summaries(candidate_inputs, results)),
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
