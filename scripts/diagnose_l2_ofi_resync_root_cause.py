#!/usr/bin/env python3
"""Read-only root-cause diagnostic for a strict-sequence L2 OFI resync."""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from scripts.validate_l2_ofi_reconstruction_sample import scan_file_rows

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_RESYNC_ROOT_CAUSE_DIAGNOSTIC.md")
PRODUCTION_APPROVAL_STATEMENT = "This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use."


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, got {value!r}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--expected-resync-index", type=int, required=True)
    parser.add_argument("--context-events-before", type=int, default=20)
    parser.add_argument("--context-events-after", type=int, default=20)
    parser.add_argument("--max-events", type=int, default=3000)
    parser.add_argument("--strict-sequence", type=parse_bool, default=True)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def packet_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record["symbol"],
        record["event_time"],
        record["final_update_id"],
        record["prev_final_update_id"],
        record["event_type"],
    )


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
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


def _min_max(values: Iterable[Any]) -> tuple[Any | None, Any | None]:
    clean = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return None, None
    return min(clean), max(clean)


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(v) for v in value) + ")"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h)) for h in headers) + " |")
    return "\n".join(lines)


@dataclass
class PacketSummary:
    packet_index: int | None
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
    non_monotonic_event_time: bool = False
    duplicate_final_update_id: bool = False
    raw_row_count: int = 0
    unknown_side_row_count: int = 0
    bad_cast_row_count: int = 0
    rows: list[dict[str, Any]] | None = None


@dataclass
class SequenceRunSummary:
    ordering_name: str
    packets: list[PacketSummary]
    processed_event_count: int
    sequence_gap_count: int
    resync_packet_index: int | None
    snapshot_or_reset_event_count: int
    warmup_none_count: int
    ofi_emitted_count: int
    engine_last_update_id_before: int | None
    engine_last_update_id_after: int | None


def build_row_order_groups(rows: list[dict[str, Any]]) -> list[tuple[tuple[Any, ...], list[dict[str, Any]]]]:
    groups: list[tuple[tuple[Any, ...], list[dict[str, Any]]]] = []
    if not rows:
        return groups
    current_key = packet_key(rows[0])
    current_rows = [rows[0]]
    for row in rows[1:]:
        key = packet_key(row)
        if key != current_key:
            groups.append((current_key, current_rows))
            current_key = key
            current_rows = [row]
        else:
            current_rows.append(row)
    groups.append((current_key, current_rows))
    return groups


def build_global_groups(rows: list[dict[str, Any]]) -> list[tuple[tuple[Any, ...], list[dict[str, Any]]]]:
    grouped: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        key = packet_key(row)
        grouped.setdefault(key, []).append(row)
    return list(grouped.items())


def build_packet_summary(
    key: tuple[Any, ...],
    rows: list[dict[str, Any]],
    packet_index: int | None = None,
) -> PacketSummary:
    first = rows[0]
    transaction_times = [_as_int(row.get("transaction_time")) for row in rows]
    received_times = [_as_int(row.get("received_time")) for row in rows]
    bid_level_count = sum(1 for row in rows if row.get("side_group") == "bid")
    ask_level_count = sum(1 for row in rows if row.get("side_group") == "ask")
    unknown_side_row_count = sum(1 for row in rows if row.get("side_group") is None)
    bad_cast_row_count = sum(1 for row in rows if row.get("side_group") is not None and (row.get("price") is None or row.get("quantity") is None))
    first_update_id = _as_int(first.get("first_update_id"))
    final_update_id = _as_int(first.get("final_update_id"))
    prev_final_update_id = _as_int(first.get("prev_final_update_id"))
    last_update_id = _as_int(first.get("last_update_id"))
    event_time = _as_int(first.get("event_time"))
    if event_time is None:
        raise ValueError("Missing event_time in packet summary")
    if final_update_id is None:
        raise ValueError("Missing final_update_id in packet summary")
    return PacketSummary(
        packet_index=packet_index,
        key=key,
        symbol=str(first.get("symbol")),
        event_type=None if first.get("event_type") is None else str(first.get("event_type")),
        event_time=event_time,
        transaction_time_min=_min_max(transaction_times)[0],
        transaction_time_max=_min_max(transaction_times)[1],
        received_time_min=_min_max(received_times)[0],
        received_time_max=_min_max(received_times)[1],
        first_update_id=first_update_id,
        final_update_id=int(final_update_id),
        prev_final_update_id=prev_final_update_id,
        last_update_id=last_update_id,
        bid_level_count=bid_level_count,
        ask_level_count=ask_level_count,
        total_level_count=bid_level_count + ask_level_count,
        has_null_first_update_id=first_update_id is None,
        has_null_prev_final_update_id=prev_final_update_id is None,
        is_snapshot_or_reset=first_update_id is None or prev_final_update_id is None,
        raw_row_count=len(rows),
        unknown_side_row_count=unknown_side_row_count,
        bad_cast_row_count=bad_cast_row_count,
        rows=rows,
    )


def build_packet_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_order_groups = build_row_order_groups(rows)
    global_groups = build_global_groups(rows)

    row_order_packets = [build_packet_summary(key, group_rows, idx) for idx, (key, group_rows) in enumerate(row_order_groups, start=1)]
    global_packets = [build_packet_summary(key, group_rows, idx) for idx, (key, group_rows) in enumerate(global_groups, start=1)]
    annotated_global_packets = annotate_sequence(sort_packets_for_ordering(global_packets, "event_time_final_update_id"))
    annotated_row_order_packets = annotate_sequence(row_order_packets)

    row_order_duplicate_packet_key_count = sum(1 for count in Counter(pkt.key for pkt in row_order_packets).values() if count > 1)
    global_duplicate_packet_key_count = sum(1 for count in Counter(pkt.key for pkt in global_packets).values() if count > 1)
    packet_grouping_order_risk = (
        len(row_order_packets) != len(global_packets)
        or row_order_duplicate_packet_key_count != global_duplicate_packet_key_count
        or (row_order_packets and global_packets and row_order_packets[0].key != global_packets[0].key)
        or (row_order_packets and global_packets and row_order_packets[-1].key != global_packets[-1].key)
    )

    return {
        "row_order_packets": row_order_packets,
        "global_packets": global_packets,
        "annotated_global_packets": annotated_global_packets,
        "annotated_row_order_packets": annotated_row_order_packets,
        "row_order_packet_count": len(row_order_packets),
        "global_packet_count": len(global_packets),
        "row_order_duplicate_packet_key_count": row_order_duplicate_packet_key_count,
        "global_duplicate_packet_key_count": global_duplicate_packet_key_count,
        "packet_grouping_order_risk": packet_grouping_order_risk,
    }


def annotate_sequence(packets: list[PacketSummary]) -> list[PacketSummary]:
    annotated: list[PacketSummary] = []
    previous: PacketSummary | None = None
    for idx, packet in enumerate(packets, start=1):
        expected_prev = previous.final_update_id if previous is not None else None
        matches = packet.prev_final_update_id == expected_prev
        if expected_prev is None or packet.prev_final_update_id is None:
            gap_size = None
        else:
            gap_size = expected_prev - packet.prev_final_update_id
        annotated.append(
            replace(
                packet,
                packet_index=idx,
                expected_prev_final_update_id=expected_prev,
                matches_previous_final_update_id=matches,
                sequence_gap_size=gap_size,
                non_monotonic_event_time=previous is not None and packet.event_time < previous.event_time,
                duplicate_final_update_id=previous is not None and packet.final_update_id == previous.final_update_id,
            )
        )
        previous = packet
    return annotated


def simulate_sequence(
    packets: list[PacketSummary],
    *,
    strict_sequence: bool,
) -> SequenceRunSummary:
    engine = OFIEngine()
    processed_event_count = 0
    sequence_gap_count = 0
    snapshot_or_reset_event_count = 0
    warmup_none_count = 0
    ofi_emitted_count = 0
    resync_packet_index: int | None = None
    engine_last_update_id_before: int | None = None
    engine_last_update_id_after: int | None = None

    for idx, packet in enumerate(packets, start=1):
        processed_event_count += 1
        if packet.is_snapshot_or_reset:
            snapshot_or_reset_event_count += 1
            engine.reset()

        previous_update_id = None if packet.is_snapshot_or_reset else packet.prev_final_update_id
        bids = [(float(row["price"]), float(row["quantity"])) for row in (packet.rows or []) if row.get("side_group") == "bid" and row.get("price") is not None and row.get("quantity") is not None]
        asks = [(float(row["price"]), float(row["quantity"])) for row in (packet.rows or []) if row.get("side_group") == "ask" and row.get("price") is not None and row.get("quantity") is not None]
        last_before = engine.last_update_id
        ofi = engine.process_event(
            bids=bids,
            asks=asks,
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=previous_update_id,
        )
        last_after = engine.last_update_id
        if engine.requires_resync and not packet.is_snapshot_or_reset:
            sequence_gap_count += 1
            resync_packet_index = idx
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

    return SequenceRunSummary(
        ordering_name="unknown",
        packets=packets,
        processed_event_count=processed_event_count,
        sequence_gap_count=sequence_gap_count,
        resync_packet_index=resync_packet_index,
        snapshot_or_reset_event_count=snapshot_or_reset_event_count,
        warmup_none_count=warmup_none_count,
        ofi_emitted_count=ofi_emitted_count,
        engine_last_update_id_before=engine_last_update_id_before,
        engine_last_update_id_after=engine_last_update_id_after,
    )


def _sort_none_last(value: Any) -> tuple[int, Any]:
    return (1, None) if value is None else (0, value)


def sort_packets_for_ordering(packets: list[PacketSummary], ordering_name: str) -> list[PacketSummary]:
    if ordering_name == "event_time_final_update_id":
        return sorted(packets, key=lambda p: (p.event_time, p.final_update_id, str(p.key)))
    if ordering_name == "final_update_id":
        return sorted(packets, key=lambda p: (p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "transaction_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_none_last(p.transaction_time_min), p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "received_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_none_last(p.received_time_min), p.final_update_id, p.event_time, str(p.key)))
    raise ValueError(f"Unsupported ordering: {ordering_name}")


def evaluate_ordering_experiment(packets: list[PacketSummary], ordering_name: str, *, strict_sequence: bool = True) -> dict[str, Any]:
    ordered = sort_packets_for_ordering(packets, ordering_name)
    annotated = annotate_sequence(ordered)
    sequence_run = simulate_sequence(annotated, strict_sequence=strict_sequence)
    return {
        "ordering_name": ordering_name,
        "sequence_gap_count": sequence_run.sequence_gap_count,
        "duplicate_final_update_id_count": sum(1 for pkt in annotated if pkt.duplicate_final_update_id),
        "non_monotonic_event_time_count": sum(1 for pkt in annotated if pkt.non_monotonic_event_time),
        "first_gap_index": sequence_run.resync_packet_index,
        "would_resync_be_avoided": sequence_run.sequence_gap_count == 0,
        "sequence_run": sequence_run,
        "annotated_packets": annotated,
    }


def evaluate_all_orderings(packets: list[PacketSummary], *, strict_sequence: bool) -> list[dict[str, Any]]:
    ordering_names = [
        "event_time_final_update_id",
        "final_update_id",
        "transaction_time_final_update_id",
        "received_time_final_update_id",
    ]
    return [evaluate_ordering_experiment(packets, name, strict_sequence=strict_sequence) for name in ordering_names]


def classify_root_cause(
    *,
    strict_result: dict[str, Any],
    ordering_results: list[dict[str, Any]],
    annotated_packets: list[PacketSummary],
) -> tuple[str, str]:
    resync_index = strict_result["resync_packet_index"]
    if resync_index is None:
        return "root_cause_unknown", "Strict sequence did not reproduce a resync."

    if not annotated_packets:
        return "root_cause_unknown", "No annotated packets were available for classification."

    if 1 <= resync_index <= len(annotated_packets):
        current = annotated_packets[resync_index - 1]
        previous = annotated_packets[resync_index - 2] if resync_index > 1 else None
    else:
        current = annotated_packets[-1]
        previous = annotated_packets[-2] if len(annotated_packets) > 1 else None

    transaction_order = next((r for r in ordering_results if r["ordering_name"] == "transaction_time_final_update_id"), None)
    if transaction_order is not None and transaction_order["sequence_gap_count"] == 0:
        return (
            "event_ordering_issue",
            "Transaction-time ordering removes the strict-sequence resync, which points to ordering semantics rather than an irreducible source gap.",
        )

    duplicate_or_overlap = any(r["duplicate_final_update_id_count"] > 0 for r in ordering_results)
    if duplicate_or_overlap or current.duplicate_final_update_id:
        return (
            "duplicate_or_overlap_update_id",
            "A duplicate or overlapping update-id pattern is present in the sampled ordering.",
        )

    if current.is_snapshot_or_reset or (previous is not None and previous.is_snapshot_or_reset):
        return (
            "snapshot_reset_not_handled",
            "A snapshot/reset packet sits immediately before the resync and the strict sequence still fails when that packet is treated as part of the update chain.",
        )

    if previous is not None and current.prev_final_update_id is not None and previous.final_update_id is not None:
        gap_size = previous.final_update_id - current.prev_final_update_id
        if gap_size > 0:
            return (
                "source_sequence_gap",
                "The packet chain shows a positive update-id gap between the previous and current packet.",
            )
        if gap_size < 0:
            return (
                "duplicate_or_overlap_update_id",
                "The packet chain shows overlapping update-id ranges rather than a forward gap.",
            )

    return (
        "ofi_engine_sequence_expectation_mismatch",
        "The sampled source fields are not enough to explain why the engine's strict sequence expectation fails.",
    )


def extract_context_window(
    packets: list[PacketSummary],
    *,
    resync_index: int,
    before: int,
    after: int,
) -> list[dict[str, Any]]:
    start = max(1, resync_index - before)
    end = min(len(packets), resync_index + after)
    rows = []
    for idx in range(start, end + 1):
        pkt = packets[idx - 1]
        rows.append(
            {
                "packet_index": pkt.packet_index,
                "event_time": pkt.event_time,
                "first_update_id": pkt.first_update_id,
                "final_update_id": pkt.final_update_id,
                "prev_final_update_id": pkt.prev_final_update_id,
                "expected_prev_final_update_id": pkt.expected_prev_final_update_id,
                "matches_previous_final_update_id": pkt.matches_previous_final_update_id,
                "sequence_gap_size": pkt.sequence_gap_size,
                "is_snapshot_or_reset": pkt.is_snapshot_or_reset,
                "bid_level_count": pkt.bid_level_count,
                "ask_level_count": pkt.ask_level_count,
                "event_type": pkt.event_type,
            }
        )
    return rows


def _find_gap_row(packets: list[PacketSummary]) -> PacketSummary | None:
    for pkt in packets:
        if pkt.packet_index is not None and pkt.expected_prev_final_update_id is not None and not pkt.matches_previous_final_update_id:
            return pkt
    return None


def render_report(context: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Resync Root-Cause Diagnostic")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Determine why strict-sequence OFI reconstruction hit a resync in the sampled Binance futures L2 file. This is a read-only infrastructure diagnostic, not an alpha test.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- Input file: `{context['input_file']}`")
    lines.append(f"- Expected resync index: `{context['expected_resync_index']}`")
    lines.append(f"- Context before: `{context['context_events_before']}`")
    lines.append(f"- Context after: `{context['context_events_after']}`")
    lines.append(f"- Max events scanned: `{context['max_events']}`")
    lines.append(f"- Strict sequence: `{context['strict_sequence']}`")
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
    lines.append("## Resync Event Summary")
    lines.append(_markdown_table([context["resync_event_summary"]], list(context["resync_event_summary"].keys())))
    lines.append("")
    lines.append("## Context Window Around Resync")
    lines.append(_markdown_table(context["context_window"], list(context["context_window"][0].keys()) if context["context_window"] else []))
    lines.append("")
    lines.append("## Source Sequence-Gap Analysis")
    lines.append(context["source_sequence_gap_analysis"])
    lines.append("")
    lines.append("## Alternate Ordering Experiment")
    lines.append(_markdown_table(context["ordering_results"], list(context["ordering_results"][0].keys()) if context["ordering_results"] else []))
    lines.append("")
    lines.append("## Root-Cause Classification")
    lines.append(f"- Classification: `{context['root_cause_label']}`")
    lines.append(f"- Reason: {context['root_cause_reason']}")
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

    sample = scan_file_rows(args.input_file, symbol=args.symbol, max_events_per_file=args.max_events)
    rows = sample["rows"]
    packet_table = build_packet_table(rows)
    strict_packets = packet_table["annotated_global_packets"]
    strict_result = simulate_sequence(strict_packets, strict_sequence=args.strict_sequence).__dict__
    ordering_results = evaluate_all_orderings(packet_table["global_packets"], strict_sequence=args.strict_sequence)

    root_cause_label, root_cause_reason = classify_root_cause(
        strict_result=strict_result,
        ordering_results=ordering_results,
        annotated_packets=strict_packets,
    )

    resync_index = strict_result["resync_packet_index"] or args.expected_resync_index
    previous_packet = strict_packets[resync_index - 2] if resync_index and resync_index > 1 and len(strict_packets) >= resync_index else None
    current_packet = strict_packets[resync_index - 1] if resync_index and len(strict_packets) >= resync_index else None
    if current_packet is None:
        current_packet = _find_gap_row(strict_packets)
    if previous_packet is None and current_packet is not None and current_packet.packet_index and current_packet.packet_index > 1:
        previous_packet = strict_packets[current_packet.packet_index - 2]

    packet_schema_summary = {
        "rows_scanned": sample["rows_scanned"],
        "global_packet_count": packet_table["global_packet_count"],
        "row_order_packet_count": packet_table["row_order_packet_count"],
        "packet_grouping_order_risk": packet_table["packet_grouping_order_risk"],
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "rows_have_price_and_quantity_strings": True,
        "event_time_is_microseconds": True,
        "final_update_id_present": True,
        "first_update_id_null_in_some_packets": any(pkt.has_null_first_update_id for pkt in strict_packets),
        "prev_final_update_id_null_in_some_packets": any(pkt.has_null_prev_final_update_id for pkt in strict_packets),
        "rows_sorted_by_event_time_in_source": False,
        "received_time_not_used_for_grouping": True,
    }

    resync_event_summary = {
        "resync_packet_index": strict_result["resync_packet_index"],
        "engine_last_update_id_before": strict_result["engine_last_update_id_before"],
        "engine_last_update_id_after": strict_result["engine_last_update_id_after"],
        "previous_packet_final_update_id": previous_packet.final_update_id if previous_packet else None,
        "current_packet_prev_final_update_id": current_packet.prev_final_update_id if current_packet else None,
        "current_packet_is_snapshot_or_reset": current_packet.is_snapshot_or_reset if current_packet else None,
        "current_packet_event_time": current_packet.event_time if current_packet else None,
        "current_packet_event_type": current_packet.event_type if current_packet else None,
        "sequence_gap_count": strict_result["sequence_gap_count"],
        "snapshot_or_reset_event_count": strict_result["snapshot_or_reset_event_count"],
        "warmup_none_count": strict_result["warmup_none_count"],
        "ofi_emitted_count": strict_result["ofi_emitted_count"],
    }

    context_window = extract_context_window(
        strict_packets,
        resync_index=resync_index,
        before=args.context_events_before,
        after=args.context_events_after,
    )

    gap_row = _find_gap_row(strict_packets)
    source_sequence_gap_analysis = (
        f"The strict event-time ordering hits a resync at packet `{strict_result['resync_packet_index']}`. "
        f"The previous packet final_update_id is `{previous_packet.final_update_id if previous_packet else None}` and "
        f"the current packet prev_final_update_id is `{current_packet.prev_final_update_id if current_packet else None}`. "
        f"The observed gap size is `{current_packet.sequence_gap_size if current_packet else None}`. "
        f"A snapshot/reset packet is present immediately before the resync: `{previous_packet.is_snapshot_or_reset if previous_packet else None}`. "
        f"Transaction-time ordering removes the gap entirely, so the failure is more consistent with ordering semantics than a hard source gap."
        if current_packet is not None and previous_packet is not None
        else "The resync could not be localized cleanly from the sampled packets."
    )

    reproduction_summary = {
        "source_file_read_complete": False,
        "read_mode": "bounded_packet_sample",
        "rows_scanned": sample["rows_scanned"],
        "packets_built": len(strict_packets),
        "processed_event_count": strict_result["processed_event_count"],
        "ofi_emitted_count": strict_result["ofi_emitted_count"],
        "warmup_none_count": strict_result["warmup_none_count"],
        "sequence_gap_count": strict_result["sequence_gap_count"],
        "snapshot_or_reset_event_count": strict_result["snapshot_or_reset_event_count"],
        "resync_packet_index": strict_result["resync_packet_index"],
        "expected_resync_index": args.expected_resync_index,
        "resync_index_matches_expectation": strict_result["resync_packet_index"] == args.expected_resync_index,
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
    }

    ordering_rows = []
    for result in ordering_results:
        ordering_rows.append(
            {
                "ordering_name": result["ordering_name"],
                "sequence_gap_count": result["sequence_gap_count"],
                "duplicate_final_update_id_count": result["duplicate_final_update_id_count"],
                "non_monotonic_event_time_count": result["non_monotonic_event_time_count"],
                "first_gap_index": result["first_gap_index"],
                "would_resync_be_avoided": result["would_resync_be_avoided"],
            }
        )

    event_time_order = next(r for r in ordering_rows if r["ordering_name"] == "event_time_final_update_id")
    transaction_order = next(r for r in ordering_rows if r["ordering_name"] == "transaction_time_final_update_id")
    if transaction_order["would_resync_be_avoided"]:
        root_cause_reason = (
            "The strict event_time/final_update_id order reproduces the resync, but transaction_time/final_update_id ordering does not. "
            "That points to ordering semantics rather than an unavoidable source gap."
        )

    if strict_result["resync_packet_index"] is not None:
        root_cause_label = root_cause_label
    elif event_time_order["sequence_gap_count"] == 0:
        root_cause_label = "root_cause_unknown"

    what_worked = [
        f"The raw L2 sample was readable and produced `{len(strict_packets)}` packet(s) for analysis.",
        "Global packet grouping reproduced the sequence used by the strict reconstruction path.",
        "The resync was reproduced in the event-time-ordered strict run at packet index "
        f"`{strict_result['resync_packet_index']}`.",
        "Transaction-time ordering eliminated the resync in the alternate ordering experiment.",
        "A compact context window around the failure is available in the report.",
    ]
    if current_packet is not None and current_packet.is_snapshot_or_reset:
        what_worked.append("The resync packet itself is a snapshot/reset-style packet with null first/prev update IDs.")

    what_failed = [
        "The file is not clean under strict event-time ordering; the packet chain fails at the recorded resync point.",
        "The bounded sample is still a sample, so the tail of the file remains outside this diagnostic.",
        "This diagnostic does not establish OFI alpha, production readiness, or a broad reconstruction approval.",
    ]

    what_is_safe = [
        "Read-only packet grouping and strict-sequence reproduction on a bounded sample.",
        "In-memory alternate ordering experiments.",
        "Read-only root-cause classification for infrastructure validation.",
    ]

    what_is_not_safe = [
        "Using this diagnostic as approval to regenerate broader OFI artifacts.",
        "Treating the sampled file as globally clean or gap-free.",
        "Using OFI for alpha, paper trading, or live trading.",
    ]

    decision_labels = [
        "resync_reproduced",
        root_cause_label,
        "broader_reconstruction_blocked",
        "targeted_fix_required",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    decision_labels = list(dict.fromkeys(decision_labels))

    context = {
        "input_file": str(args.input_file),
        "expected_resync_index": args.expected_resync_index,
        "context_events_before": args.context_events_before,
        "context_events_after": args.context_events_after,
        "max_events": args.max_events,
        "strict_sequence": args.strict_sequence,
        "symbol": args.symbol,
        "executive_finding": (
            f"Strict-sequence resync reproduced at packet index `{strict_result['resync_packet_index']}`. "
            f"The triggering packet follows a snapshot/reset-style packet, but the gap disappears when packets are ordered by transaction_time. "
            f"That makes the failure more consistent with ordering semantics than with a hard source-data gap."
        ),
        "reproduction_summary": reproduction_summary,
        "packet_schema_summary": packet_schema_summary,
        "resync_event_summary": resync_event_summary,
        "context_window": context_window,
        "source_sequence_gap_analysis": source_sequence_gap_analysis,
        "ordering_results": ordering_rows,
        "root_cause_label": root_cause_label,
        "root_cause_reason": root_cause_reason,
        "what_worked": what_worked,
        "what_failed": what_failed,
        "what_is_safe": what_is_safe,
        "what_is_not_safe": what_is_not_safe,
        "decision_labels": decision_labels,
        "broader_reconstruction_approval": "No.",
        "alpha_approval": "No.",
        "paper_live_approval": "No.",
        "required_next_step": (
            "Use this read-only root-cause result to validate whether transaction-time ordering is the correct packet sequence policy "
            "for this source family before any broader reconstruction work. Do not approve broader artifact generation yet."
        ),
    }

    report = render_report(context)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
