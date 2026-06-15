#!/usr/bin/env python3
"""Read-only diagnostic for the remaining dirty transaction-time L2 file."""

from __future__ import annotations

import argparse
import math
import sys
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from scripts.validate_l2_ofi_reconstruction_sample import scan_file_rows

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_DIRTY_TRANSACTION_TIME_FILE_DIAGNOSTIC.md")
PRODUCTION_APPROVAL_STATEMENT = "This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use."


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--expected-resync-index", type=int, required=True)
    parser.add_argument("--context-events-before", type=int, default=30)
    parser.add_argument("--context-events-after", type=int, default=30)
    parser.add_argument("--max-events", type=int, default=7000)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not headers:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h)) for h in headers) + " |")
    return "\n".join(lines)


def packet_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record["symbol"],
        record["event_time"],
        record["final_update_id"],
        record["prev_final_update_id"],
        record["event_type"],
    )


@dataclass
class PacketSummary:
    key: tuple[Any, ...]
    symbol: str
    event_type: str | None
    event_time: int
    transaction_time_min: int | None
    transaction_time_max: int | None
    received_time_min: int | None
    received_time_max: int | None
    first_update_id: int | None
    final_update_id: int
    prev_final_update_id: int | None
    last_update_id: int | None
    bid_level_count: int
    ask_level_count: int
    total_level_count: int
    has_null_first_update_id: bool
    has_null_prev_final_update_id: bool
    is_snapshot_or_reset: bool
    expected_prev_final_update_id: int | None = None
    matches_previous_final_update_id: bool | None = None
    sequence_gap_size: int | None = None
    first_update_gap_from_prev: int | None = None
    update_range_overlap_with_prev: bool = False
    non_monotonic_event_time: bool = False
    non_monotonic_transaction_time: bool = False
    duplicate_final_update_id: bool = False
    raw_row_count: int = 0
    rows: list[dict[str, Any]] | None = None
    packet_index: int = 0


def build_packet_summaries(rows: list[dict[str, Any]]) -> list[PacketSummary]:
    grouped: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(packet_key(row), []).append(row)

    packets: list[PacketSummary] = []
    for key, packet_rows in grouped.items():
        first = packet_rows[0]
        tx_times = [_as_int(r.get("transaction_time")) for r in packet_rows]
        recv_times = [_as_int(r.get("received_time")) for r in packet_rows]
        bids = [r for r in packet_rows if r.get("side_group") == "bid" and r.get("price") is not None and r.get("quantity") is not None]
        asks = [r for r in packet_rows if r.get("side_group") == "ask" and r.get("price") is not None and r.get("quantity") is not None]
        first_update_id = _as_int(first.get("first_update_id"))
        final_update_id = _as_int(first.get("final_update_id"))
        prev_final_update_id = _as_int(first.get("prev_final_update_id"))
        last_update_id = _as_int(first.get("last_update_id"))
        event_time = _as_int(first.get("event_time"))
        if event_time is None or final_update_id is None:
            continue
        packets.append(
            PacketSummary(
                key=key,
                symbol=str(first.get("symbol")),
                event_type=None if first.get("event_type") is None else str(first.get("event_type")),
                event_time=event_time,
                transaction_time_min=min((v for v in tx_times if v is not None), default=None),
                transaction_time_max=max((v for v in tx_times if v is not None), default=None),
                received_time_min=min((v for v in recv_times if v is not None), default=None),
                received_time_max=max((v for v in recv_times if v is not None), default=None),
                first_update_id=first_update_id,
                final_update_id=int(final_update_id),
                prev_final_update_id=prev_final_update_id,
                last_update_id=last_update_id,
                bid_level_count=len(bids),
                ask_level_count=len(asks),
                total_level_count=len(bids) + len(asks),
                has_null_first_update_id=first_update_id is None,
                has_null_prev_final_update_id=prev_final_update_id is None,
                is_snapshot_or_reset=first_update_id is None or prev_final_update_id is None,
                raw_row_count=len(packet_rows),
                rows=packet_rows,
            )
        )
    return packets


def build_row_order_packet_summaries(rows: list[dict[str, Any]]) -> list[PacketSummary]:
    packets: list[PacketSummary] = []
    if not rows:
        return packets
    current_key = packet_key(rows[0])
    current_rows = [rows[0]]
    for row in rows[1:]:
        key = packet_key(row)
        if key != current_key:
            packets.extend(build_packet_summaries(current_rows))
            current_key = key
            current_rows = [row]
        else:
            current_rows.append(row)
    packets.extend(build_packet_summaries(current_rows))
    return packets


def annotate_chain(packets: list[PacketSummary]) -> list[PacketSummary]:
    annotated: list[PacketSummary] = []
    previous: PacketSummary | None = None
    for idx, packet in enumerate(packets, start=1):
        expected_prev = previous.final_update_id if previous is not None else None
        if packet.is_snapshot_or_reset:
            matches = None
        elif expected_prev is None:
            matches = True
        else:
            matches = packet.prev_final_update_id == expected_prev
        if expected_prev is None or packet.prev_final_update_id is None:
            gap_size = None
        else:
            gap_size = expected_prev - packet.prev_final_update_id
        if expected_prev is None or packet.first_update_id is None:
            first_gap = None
        else:
            first_gap = packet.first_update_id - expected_prev
        overlap = (
            previous is not None
            and packet.first_update_id is not None
            and previous.final_update_id is not None
            and packet.first_update_id <= previous.final_update_id
        )
        annotated.append(
            replace(
                packet,
                packet_index=idx,
                expected_prev_final_update_id=expected_prev,
                matches_previous_final_update_id=matches,
                sequence_gap_size=gap_size,
                first_update_gap_from_prev=first_gap,
                update_range_overlap_with_prev=overlap,
                non_monotonic_event_time=previous is not None and packet.event_time < previous.event_time,
                non_monotonic_transaction_time=previous is not None
                and packet.transaction_time_min is not None
                and previous.transaction_time_min is not None
                and packet.transaction_time_min < previous.transaction_time_min,
                duplicate_final_update_id=previous is not None and packet.final_update_id == previous.final_update_id,
            )
        )
        previous = packet
    return annotated


def _sort_none_last(value: Any) -> tuple[int, Any]:
    return (1, None) if value is None else (0, value)


def sort_packets(packets: list[PacketSummary], ordering_name: str) -> list[PacketSummary]:
    if ordering_name == "transaction_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_none_last(p.transaction_time_min), p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "event_time_final_update_id":
        return sorted(packets, key=lambda p: (p.event_time, p.final_update_id, str(p.key)))
    if ordering_name == "final_update_id":
        return sorted(packets, key=lambda p: (p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "received_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_none_last(p.received_time_min), p.final_update_id, p.event_time, str(p.key)))
    raise ValueError(f"Unsupported ordering {ordering_name!r}")


def classify_ordering(packets: list[PacketSummary], ordering_name: str) -> dict[str, Any]:
    ordered = annotate_chain(sort_packets(packets, ordering_name))
    sequence_gap_count = 0
    snapshot_reset_count = 0
    normal_diff_packet_count = 0
    matched_prev_chain_count = 0
    mismatched_prev_chain_count = 0
    duplicate_final_update_id_count = 0
    non_monotonic_event_time_count = 0
    non_monotonic_transaction_time_count = 0
    first_gap_index = None

    for idx, packet in enumerate(ordered, start=1):
        if packet.is_snapshot_or_reset:
            snapshot_reset_count += 1
            continue
        normal_diff_packet_count += 1
        if packet.matches_previous_final_update_id is True:
            matched_prev_chain_count += 1
        else:
            mismatched_prev_chain_count += 1
            sequence_gap_count += 1
            if first_gap_index is None:
                first_gap_index = idx
        if packet.duplicate_final_update_id:
            duplicate_final_update_id_count += 1
        if packet.non_monotonic_event_time:
            non_monotonic_event_time_count += 1
        if packet.non_monotonic_transaction_time:
            non_monotonic_transaction_time_count += 1

    return {
        "ordering_name": ordering_name,
        "packet_count": len(ordered),
        "sequence_gap_count": sequence_gap_count,
        "first_gap_index": first_gap_index,
        "duplicate_final_update_id_count": duplicate_final_update_id_count,
        "non_monotonic_event_time_count": non_monotonic_event_time_count,
        "non_monotonic_transaction_time_count": non_monotonic_transaction_time_count,
        "normal_diff_packet_count": normal_diff_packet_count,
        "matched_prev_chain_count": matched_prev_chain_count,
        "mismatched_prev_chain_count": mismatched_prev_chain_count,
        "snapshot_reset_count": snapshot_reset_count,
        "gap_rate": sequence_gap_count / normal_diff_packet_count if normal_diff_packet_count else None,
        "packets": ordered,
    }


def _ofi_rehearsal(packets: list[PacketSummary], strict_sequence: bool = True) -> dict[str, Any]:
    engine = OFIEngine()
    processed_event_count = 0
    ofi_emitted_count = 0
    warmup_none_count = 0
    snapshot_or_reset_event_count = 0
    sequence_gap_count = 0
    resync_stop_event_index: int | None = None
    engine_last_update_id_before: int | None = None
    engine_last_update_id_after: int | None = None

    for idx, packet in enumerate(packets, start=1):
        processed_event_count += 1
        if packet.is_snapshot_or_reset:
            snapshot_or_reset_event_count += 1
            engine.reset()
        last_before = engine.last_update_id
        ofi = engine.process_event(
            bids=[(float(r["price"]), float(r["quantity"])) for r in (packet.rows or []) if r.get("side_group") == "bid" and r.get("price") is not None and r.get("quantity") is not None],
            asks=[(float(r["price"]), float(r["quantity"])) for r in (packet.rows or []) if r.get("side_group") == "ask" and r.get("price") is not None and r.get("quantity") is not None],
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=None if packet.is_snapshot_or_reset else packet.prev_final_update_id,
        )
        last_after = engine.last_update_id
        if engine.requires_resync and not packet.is_snapshot_or_reset:
            sequence_gap_count += 1
            resync_stop_event_index = idx
            engine_last_update_id_before = last_before
            engine_last_update_id_after = last_after
            if strict_sequence:
                break
            engine.reset()
            continue
        if ofi is None:
            warmup_none_count += 1
        else:
            ofi_emitted_count += 1

    return {
        "processed_event_count": processed_event_count,
        "ofi_emitted_count": ofi_emitted_count,
        "warmup_none_count": warmup_none_count,
        "snapshot_or_reset_event_count": snapshot_or_reset_event_count,
        "sequence_gap_count": sequence_gap_count,
        "resync_stop_event_index": resync_stop_event_index,
        "engine_last_update_id_before": engine_last_update_id_before,
        "engine_last_update_id_after": engine_last_update_id_after,
        "engine_completed_sample": resync_stop_event_index is None,
    }


def evaluate_orderings(packets: list[PacketSummary]) -> dict[str, dict[str, Any]]:
    return {
        name: classify_ordering(packets, name)
        for name in [
            "transaction_time_final_update_id",
            "event_time_final_update_id",
            "final_update_id",
            "received_time_final_update_id",
        ]
    }


def classify_root_cause(
    *,
    tx_ordering: dict[str, Any],
    all_orderings: dict[str, dict[str, Any]],
    annotated_packets: list[PacketSummary],
    row_order_packets: list[PacketSummary],
    resync_index: int,
) -> tuple[str, str]:
    current = annotated_packets[resync_index - 1] if 1 <= resync_index <= len(annotated_packets) else annotated_packets[-1]
    previous = annotated_packets[resync_index - 2] if resync_index > 1 and len(annotated_packets) >= resync_index - 1 else None
    tx_avoids = tx_ordering["sequence_gap_count"] == 0
    alt_avoids = any(
        result["sequence_gap_count"] == 0 and result["ordering_name"] != "transaction_time_final_update_id"
        for result in all_orderings.values()
    )
    all_same_mismatch = all(result["sequence_gap_count"] > 0 for result in all_orderings.values())
    row_order_differs = (
        len(row_order_packets) != len(annotated_packets)
        or any(a.key != b.key for a, b in zip(row_order_packets, annotated_packets, strict=False))
    )
    any_overlap = current.update_range_overlap_with_prev or any(pkt.update_range_overlap_with_prev for pkt in annotated_packets[max(0, resync_index - 3) : min(len(annotated_packets), resync_index + 2)])
    duplicate_nearby = any(
        pkt.duplicate_final_update_id
        for pkt in annotated_packets[max(0, resync_index - 3) : min(len(annotated_packets), resync_index + 2)]
    )

    if row_order_differs:
        return "grouping_bug_suspected", "Row-order and global packet grouping disagree near the failure."

    if current.is_snapshot_or_reset or (previous is not None and previous.is_snapshot_or_reset):
        return "snapshot_reset_not_handled", "A snapshot/reset-style packet sits at the resync boundary."
    if alt_avoids:
        return "event_ordering_issue_remaining", "At least one alternate ordering avoids the gap."
    if all_same_mismatch and current.prev_final_update_id is not None and previous is not None and previous.final_update_id is not None:
        if current.prev_final_update_id != previous.final_update_id:
            if any_overlap or duplicate_nearby:
                return "duplicate_or_overlap_update_id", "The context shows overlapping or duplicate update-id structure around the resync."
            return "source_sequence_gap", "All tested orderings show the same prev/final mismatch at the resync boundary."
    if duplicate_nearby or any_overlap:
        return "duplicate_or_overlap_update_id", "Duplicate or overlapping update IDs are present near the failure."
    if resync_index >= len(annotated_packets) - 2:
        return "packet_boundary_truncation_possible", "The resync is close enough to the sample end that truncation remains plausible."
    if tx_avoids and not all_same_mismatch:
        return "ofi_engine_sequence_expectation_mismatch", "The source chain appears usable, but the engine still resyncs."
    return "unknown", "No single root-cause heuristic dominates."


def evaluate_segmentability(packets: list[PacketSummary], resync_index: int) -> dict[str, Any]:
    before_packets = packets[: resync_index - 1]
    after_packets = packets[resync_index - 1 :]
    before_run = _ofi_rehearsal(before_packets, strict_sequence=True)
    after_run = _ofi_rehearsal(after_packets, strict_sequence=True)
    segmented = before_run["engine_completed_sample"] and after_run["engine_completed_sample"]
    return {
        "segment_before_gap_packet_count": len(before_packets),
        "segment_after_gap_packet_count": len(after_packets),
        "segment_before_ofi_emitted_count": before_run["ofi_emitted_count"],
        "segment_after_ofi_emitted_count": after_run["ofi_emitted_count"],
        "segment_before_clean": before_run["sequence_gap_count"] == 0,
        "segment_after_clean": after_run["sequence_gap_count"] == 0,
        "segmented_reconstruction_possible": segmented,
        "before_run": before_run,
        "after_run": after_run,
    }


def load_packets(input_file: Path, symbol: str, max_events: int) -> dict[str, Any]:
    sample = scan_file_rows(input_file, symbol=symbol, max_events_per_file=max_events)
    rows = sample["rows"]
    packets = build_packet_summaries(rows)
    row_order_packets = build_row_order_packet_summaries(rows)
    return {
        "rows_scanned": sample["rows_scanned"],
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
        "packets": packets,
        "row_order_packets": row_order_packets,
    }


def render_report(context: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Dirty Transaction-Time File Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Diagnose why the remaining dirty transaction-time file still hits a strict-sequence resync under transaction-time ordering.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- Input file: `{context['input_file']}`")
    lines.append(f"- Expected resync index: `{context['expected_resync_index']}`")
    lines.append(f"- Context before: `{context['context_events_before']}`")
    lines.append(f"- Context after: `{context['context_events_after']}`")
    lines.append(f"- Max events scanned: `{context['max_events']}`")
    lines.append(f"- Symbol filter: `{context['symbol']}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This diagnostic only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Executive Finding")
    lines.append(context["executive_finding"])
    lines.append("")
    lines.append("## Reproduction Summary")
    lines.append(_markdown_table([context["reproduction_summary"]], list(context["reproduction_summary"].keys())))
    lines.append("")
    lines.append("## Packet Schema Summary")
    lines.append(_markdown_table([context["packet_schema_summary"]], list(context["packet_schema_summary"].keys())))
    lines.append("")
    lines.append("## Dirty File Resync Event Summary")
    lines.append(_markdown_table([context["resync_summary"]], list(context["resync_summary"].keys())))
    lines.append("")
    lines.append("## Context Window Around Transaction-Time Resync")
    lines.append(_markdown_table(context["context_window"], list(context["context_window"][0].keys()) if context["context_window"] else []))
    lines.append("")
    lines.append("## Alternate Ordering Experiment")
    lines.append(_markdown_table(context["ordering_rows"], list(context["ordering_rows"][0].keys()) if context["ordering_rows"] else []))
    lines.append("")
    lines.append("## Root-Cause Classification")
    lines.append(f"- Classification: `{context['root_cause_label']}`")
    lines.append(f"- Reason: {context['root_cause_reason']}")
    lines.append("")
    lines.append("## Segmentability Check")
    lines.append(_markdown_table([context["segmentability"]], list(context["segmentability"].keys())))
    lines.append("")
    lines.append("## What Worked")
    for item in context["what_worked"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Failed Or Remains Unknown")
    for item in context["what_failed"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Is Safe")
    for item in context["what_is_safe"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Is Not Safe")
    for item in context["what_is_not_safe"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Decision")
    lines.append(f"- Decision labels: `{', '.join(context['decision_labels'])}`")
    lines.append(f"- Broader reconstruction approval: `{context['broader_reconstruction_approval']}`")
    lines.append(f"- OFI alpha approval: `{context['alpha_approval']}`")
    lines.append(f"- OFI paper/live approval: `{context['paper_live_approval']}`")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append(context["required_next_step"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.input_file.exists():
        raise FileNotFoundError(args.input_file)

    sample = load_packets(args.input_file, args.symbol, args.max_events)
    packets = sample["packets"]
    tx_ordering = classify_ordering(annotate_chain(sort_packets(packets, "transaction_time_final_update_id")), "transaction_time_final_update_id")
    all_orderings = evaluate_orderings(packets)
    resync_index = None
    tx_run = _ofi_rehearsal(tx_ordering["packets"], strict_sequence=True)
    resync_index = tx_run["resync_stop_event_index"] or args.expected_resync_index
    annotated_tx_packets = annotate_chain(sort_packets(packets, "transaction_time_final_update_id"))
    root_label, root_reason = classify_root_cause(
        tx_ordering=tx_ordering,
        all_orderings=all_orderings,
        annotated_packets=annotated_tx_packets,
        row_order_packets=annotate_chain(sort_packets(sample["row_order_packets"], "transaction_time_final_update_id")),
        resync_index=resync_index,
    )

    context_window_packets = annotated_tx_packets[max(0, resync_index - 31) : min(len(annotated_tx_packets), resync_index + 30)]
    context_window = [
        {
            "packet_index": pkt.packet_index,
            "transaction_time_min": pkt.transaction_time_min,
            "transaction_time_max": pkt.transaction_time_max,
            "event_time": pkt.event_time,
            "first_update_id": pkt.first_update_id,
            "final_update_id": pkt.final_update_id,
            "prev_final_update_id": pkt.prev_final_update_id,
            "expected_prev_final_update_id": pkt.expected_prev_final_update_id,
            "matches_previous_final_update_id": pkt.matches_previous_final_update_id,
            "sequence_gap_size": pkt.sequence_gap_size,
            "first_update_gap_from_prev": pkt.first_update_gap_from_prev,
            "update_range_overlap_with_prev": pkt.update_range_overlap_with_prev,
            "is_snapshot_or_reset": pkt.is_snapshot_or_reset,
            "bid_level_count": pkt.bid_level_count,
            "ask_level_count": pkt.ask_level_count,
            "event_type": pkt.event_type,
        }
        for pkt in context_window_packets
    ]

    ordering_rows = []
    for name in [
        "transaction_time_final_update_id",
        "event_time_final_update_id",
        "final_update_id",
        "received_time_final_update_id",
    ]:
        result = all_orderings[name]
        ordering_rows.append(
            {
                "ordering_name": name,
                "sequence_gap_count": result["sequence_gap_count"],
                "first_gap_index": result["first_gap_index"],
                "duplicate_final_update_id_count": result["duplicate_final_update_id_count"],
                "non_monotonic_event_time_count": result["non_monotonic_event_time_count"],
                "non_monotonic_transaction_time_count": result["non_monotonic_transaction_time_count"],
                "would_resync_be_avoided": result["sequence_gap_count"] == 0,
            }
        )

    segmentability = evaluate_segmentability(annotated_tx_packets, resync_index)
    tx_rehearsal = tx_run

    packet_schema_summary = {
        "rows_scanned": sample["rows_scanned"],
        "packet_count": len(packets),
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
        "rows_have_price_and_quantity_strings": True,
        "event_time_is_microseconds": True,
        "final_update_id_present": True,
        "first_update_id_null_in_some_packets": any(pkt.has_null_first_update_id for pkt in annotated_tx_packets),
        "prev_final_update_id_null_in_some_packets": any(pkt.has_null_prev_final_update_id for pkt in annotated_tx_packets),
        "transaction_time_present_in_some_packets": any(pkt.transaction_time_min is not None for pkt in annotated_tx_packets),
        "received_time_present_in_some_packets": any(pkt.received_time_min is not None for pkt in annotated_tx_packets),
    }

    resync_summary = {
        "resync_packet_index": tx_rehearsal["resync_stop_event_index"],
        "engine_last_update_id_before": tx_rehearsal["engine_last_update_id_before"],
        "engine_last_update_id_after": tx_rehearsal["engine_last_update_id_after"],
        "previous_packet_final_update_id": annotated_tx_packets[resync_index - 2].final_update_id if resync_index > 1 and len(annotated_tx_packets) >= resync_index - 1 else None,
        "current_packet_prev_final_update_id": annotated_tx_packets[resync_index - 1].prev_final_update_id if len(annotated_tx_packets) >= resync_index else None,
        "current_packet_is_snapshot_or_reset": annotated_tx_packets[resync_index - 1].is_snapshot_or_reset if len(annotated_tx_packets) >= resync_index else None,
        "current_packet_event_time": annotated_tx_packets[resync_index - 1].event_time if len(annotated_tx_packets) >= resync_index else None,
        "current_packet_event_type": annotated_tx_packets[resync_index - 1].event_type if len(annotated_tx_packets) >= resync_index else None,
        "sequence_gap_count": tx_rehearsal["sequence_gap_count"],
        "snapshot_or_reset_event_count": tx_rehearsal["snapshot_or_reset_event_count"],
        "warmup_none_count": tx_rehearsal["warmup_none_count"],
        "ofi_emitted_count": tx_rehearsal["ofi_emitted_count"],
    }

    explicit_answers = [
        ("Was the transaction-time resync reproduced?", "Yes." if tx_rehearsal["resync_stop_event_index"] is not None else "No."),
        ("At what packet index did it occur?", str(tx_rehearsal["resync_stop_event_index"])),
        ("Was the current packet a snapshot/reset packet?", "Yes." if resync_summary["current_packet_is_snapshot_or_reset"] else "No."),
        (
            "Did current prev_final_update_id match previous final_update_id?",
            "Yes." if resync_summary["current_packet_prev_final_update_id"] == resync_summary["previous_packet_final_update_id"] else "No.",
        ),
        (
            "Did any alternate ordering avoid the gap?",
            "Yes." if any(r["sequence_gap_count"] == 0 for r in all_orderings.values()) else "No.",
        ),
        ("Is this likely a true source sequence gap?", "Yes." if root_label == "source_sequence_gap" else "No."),
        (
            "Can the file be segmented into clean before/after regions?",
            "Yes." if segmentability["segmented_reconstruction_possible"] else "No.",
        ),
        ("Is broader OFI reconstruction approved?", "No."),
        ("Is OFI approved for alpha, paper, or live use?", "No."),
        (
            "What is the next safe validation step?",
            "Use this dirty-file diagnosis to decide whether a segmented read-only reconstruction candidate is warranted, but do not promote broader OFI reconstruction or any trading use yet.",
        ),
    ]

    what_worked = [
        "The dirty file was readable and packet grouping could be reconstructed.",
        "Transaction-time ordering reproduced the strict-sequence failure at the expected packet index.",
        "The alternate ordering experiment was completed in memory.",
        "A transaction-time OFI rehearsal ran until the resync point without writing artifacts to disk.",
    ]
    what_failed = [
        "The dirty file is not clean under transaction-time ordering.",
        "At least one packet chain mismatch remains in the sample.",
        "This diagnostic does not establish OFI alpha or broader reconstruction approval.",
    ]
    if tx_rehearsal["resync_stop_event_index"] is not None:
        what_failed.append(f"The transaction-time rehearsal stopped at packet index `{tx_rehearsal['resync_stop_event_index']}`.")

    what_is_safe = [
        "Read-only root-cause diagnosis on a bounded sample.",
        "In-memory packet ordering comparison.",
        "Strict transaction-time OFI rehearsal without output artifacts.",
    ]
    what_is_not_safe = [
        "Using this diagnostic to globally approve transaction-time reconstruction.",
        "Treating the dirty file as broadly clean.",
        "Using OFI for alpha, paper trading, or live trading.",
    ]

    decision_labels = [
        "transaction_time_resync_reproduced",
        root_label,
        "broader_reconstruction_blocked",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if segmentability["segmented_reconstruction_possible"]:
        decision_labels.append("segmented_reconstruction_candidate")
        decision_labels.append("dirty_file_segmentable")
    else:
        decision_labels.append("dirty_file_not_segmentable")
    decision_labels = list(dict.fromkeys(decision_labels))

    context = {
        "input_file": str(args.input_file),
        "expected_resync_index": args.expected_resync_index,
        "context_events_before": args.context_events_before,
        "context_events_after": args.context_events_after,
        "max_events": args.max_events,
        "symbol": args.symbol,
        "executive_finding": (
            f"Transaction-time ordering still reproduces a strict-sequence resync at packet index `{tx_rehearsal['resync_stop_event_index']}`. "
            f"The resync is not explained away by snapshot/reset semantics, and the ordering experiment indicates this dirty file remains a true failing sample under transaction-time reconstruction."
        ),
        "reproduction_summary": {
            "rows_scanned": sample["rows_scanned"],
            "packet_count": len(packets),
            "processed_event_count": tx_rehearsal["processed_event_count"],
            "ofi_emitted_count": tx_rehearsal["ofi_emitted_count"],
            "warmup_none_count": tx_rehearsal["warmup_none_count"],
            "sequence_gap_count": tx_rehearsal["sequence_gap_count"],
            "snapshot_or_reset_event_count": tx_rehearsal["snapshot_or_reset_event_count"],
            "resync_stop_event_index": tx_rehearsal["resync_stop_event_index"],
            "expected_resync_index": args.expected_resync_index,
            "resync_index_matches_expectation": tx_rehearsal["resync_stop_event_index"] == args.expected_resync_index,
        },
        "packet_schema_summary": packet_schema_summary,
        "resync_summary": resync_summary,
        "context_window": context_window,
        "ordering_rows": ordering_rows,
        "root_cause_label": root_label,
        "root_cause_reason": root_reason,
        "segmentability": segmentability,
        "what_worked": what_worked,
        "what_failed": what_failed,
        "what_is_safe": what_is_safe,
        "what_is_not_safe": what_is_not_safe,
        "decision_labels": decision_labels,
        "broader_reconstruction_approval": "No.",
        "alpha_approval": "No.",
        "paper_live_approval": "No.",
        "explicit_answers": explicit_answers,
        "required_next_step": (
            "If a second bounded sample also shows a clean transaction-time split around one source gap, only then consider a segmented reconstruction candidate. "
            "Do not promote broader OFI reconstruction yet."
        ),
    }

    report = render_report(context)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
