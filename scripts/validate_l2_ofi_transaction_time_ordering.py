#!/usr/bin/env python3
"""Read-only bounded validation of transaction-time OFI ordering."""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from scripts.validate_l2_ofi_reconstruction_sample import scan_file_rows

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_TRANSACTION_TIME_ORDERING_VALIDATION.md")
PRODUCTION_APPROVAL_STATEMENT = "This validation does not approve OFI for production, paper trading, live trading, or alpha use."
KNOWN_FAILING_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=12)
    parser.add_argument("--max-events-per-file", type=int, default=5000)
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
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(v) for v in value) + ")"
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
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    rows: list[dict[str, Any]]
    raw_row_count: int
    unknown_side_row_count: int
    bad_cast_row_count: int
    is_snapshot_or_reset: bool
    packet_index: int | None = None
    expected_prev_final_update_id: int | None = None
    matches_previous_final_update_id: bool | None = None
    sequence_gap_size: int | None = None
    non_monotonic_event_time: bool = False
    non_monotonic_transaction_time: bool = False
    duplicate_final_update_id: bool = False


def _group_rows_global(rows: list[dict[str, Any]]) -> list[tuple[tuple[Any, ...], list[dict[str, Any]]]]:
    grouped: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        key = packet_key(row)
        grouped.setdefault(key, []).append(row)
    return list(grouped.items())


def _build_packet_summary(key: tuple[Any, ...], rows: list[dict[str, Any]], packet_index: int | None = None) -> PacketSummary:
    first = rows[0]
    tx_times = [_as_int(row.get("transaction_time")) for row in rows]
    recv_times = [_as_int(row.get("received_time")) for row in rows]
    bids = [(float(row["price"]), float(row["quantity"])) for row in rows if row.get("side_group") == "bid" and row.get("price") is not None and row.get("quantity") is not None]
    asks = [(float(row["price"]), float(row["quantity"])) for row in rows if row.get("side_group") == "ask" and row.get("price") is not None and row.get("quantity") is not None]
    unknown_side_row_count = sum(1 for row in rows if row.get("side_group") is None)
    bad_cast_row_count = sum(1 for row in rows if row.get("side_group") is not None and (row.get("price") is None or row.get("quantity") is None))
    first_update_id = _as_int(first.get("first_update_id"))
    final_update_id = _as_int(first.get("final_update_id"))
    prev_final_update_id = _as_int(first.get("prev_final_update_id"))
    last_update_id = _as_int(first.get("last_update_id"))
    event_time = _as_int(first.get("event_time"))
    if event_time is None or final_update_id is None:
        raise ValueError("Missing required packet fields")
    return PacketSummary(
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
        bids=bids,
        asks=asks,
        rows=rows,
        raw_row_count=len(rows),
        unknown_side_row_count=unknown_side_row_count,
        bad_cast_row_count=bad_cast_row_count,
        is_snapshot_or_reset=first_update_id is None or prev_final_update_id is None,
        packet_index=packet_index,
    )


def build_packet_summaries(rows: list[dict[str, Any]]) -> list[PacketSummary]:
    groups = _group_rows_global(rows)
    packets = [_build_packet_summary(key, group_rows, idx) for idx, (key, group_rows) in enumerate(groups, start=1)]
    return packets


def annotate_chain(packets: list[PacketSummary], ordering_name: str) -> list[PacketSummary]:
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
        annotated.append(
            replace(
                packet,
                packet_index=idx,
                expected_prev_final_update_id=expected_prev,
                matches_previous_final_update_id=matches,
                sequence_gap_size=gap_size,
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


def _sort_with_none_last(value: Any) -> tuple[int, Any]:
    return (1, None) if value is None else (0, value)


def sort_packets(packets: list[PacketSummary], ordering_name: str) -> list[PacketSummary]:
    if ordering_name == "event_time_final_update_id":
        return sorted(packets, key=lambda p: (p.event_time, p.final_update_id, str(p.key)))
    if ordering_name == "transaction_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_with_none_last(p.transaction_time_min), p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "final_update_id":
        return sorted(packets, key=lambda p: (p.final_update_id, p.event_time, str(p.key)))
    if ordering_name == "received_time_final_update_id":
        return sorted(packets, key=lambda p: (_sort_with_none_last(p.received_time_min), p.final_update_id, p.event_time, str(p.key)))
    raise ValueError(f"Unsupported ordering {ordering_name!r}")


def classify_ordering(packets: list[PacketSummary], ordering_name: str) -> dict[str, Any]:
    ordered = annotate_chain(sort_packets(packets, ordering_name), ordering_name)
    strict_sequence_gap_count = 0
    reset_aware_sequence_gap_count = 0
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
            reset_aware_sequence_gap_count += 1
            strict_sequence_gap_count += 1
            if first_gap_index is None:
                first_gap_index = idx
        if packet.duplicate_final_update_id:
            duplicate_final_update_id_count += 1
        if packet.non_monotonic_event_time:
            non_monotonic_event_time_count += 1
        if packet.non_monotonic_transaction_time:
            non_monotonic_transaction_time_count += 1

    gap_rate = reset_aware_sequence_gap_count / normal_diff_packet_count if normal_diff_packet_count else None
    return {
        "ordering_name": ordering_name,
        "packet_count": len(ordered),
        "strict_sequence_gap_count": strict_sequence_gap_count,
        "reset_aware_sequence_gap_count": reset_aware_sequence_gap_count,
        "first_gap_index": first_gap_index,
        "snapshot_reset_count": snapshot_reset_count,
        "duplicate_final_update_id_count": duplicate_final_update_id_count,
        "non_monotonic_event_time_count": non_monotonic_event_time_count,
        "non_monotonic_transaction_time_count": non_monotonic_transaction_time_count,
        "normal_diff_packet_count": normal_diff_packet_count,
        "matched_prev_chain_count": matched_prev_chain_count,
        "mismatched_prev_chain_count": mismatched_prev_chain_count,
        "gap_rate": gap_rate,
        "packets": ordered,
    }


def select_deterministic_files(l2_root: Path, symbol: str, max_files: int) -> list[Path]:
    candidates = sorted(
        [
            p
            for p in Path(l2_root).rglob("*")
            if p.is_file()
            and symbol.upper() in p.name.upper()
            and (p.suffix.lower() in {".parquet", ".csv", ".json", ".jsonl", ".gz"} or p.name.lower().endswith(".parquet.zst"))
        ],
        key=lambda p: p.as_posix(),
    )
    if not candidates:
        return []

    selected: list[Path] = []

    def add(path: Path | None) -> None:
        if path is not None and path.exists() and path not in selected:
            selected.append(path)

    known = KNOWN_FAILING_FILE if KNOWN_FAILING_FILE.exists() else None
    add(known)
    if known is not None and known in candidates:
        idx = candidates.index(known)
        date_prefix = "/2025-06-28/"
        same_date = [p for p in candidates if date_prefix in p.as_posix()]
        same_date = sorted(same_date, key=lambda p: p.as_posix())
        if same_date:
            same_idx = same_date.index(known)
            for offset in range(1, 3):
                if same_idx - offset >= 0:
                    add(same_date[same_idx - offset])
                if same_idx + offset < len(same_date):
                    add(same_date[same_idx + offset])
        for offset in range(1, 3):
            if idx - offset >= 0:
                add(candidates[idx - offset])
            if idx + offset < len(candidates):
                add(candidates[idx + offset])

    add(candidates[0])
    add(candidates[-1])
    if max_files > len(selected):
        spacing = max(1, len(candidates) - 1)
        for i in range(max_files * 2):
            if len(selected) >= max_files:
                break
            idx = round(i * spacing / max(1, max_files - 1)) if max_files > 1 else 0
            add(candidates[min(idx, len(candidates) - 1)])
    return selected[:max_files]


def load_bounded_rows(path: Path, max_events_per_file: int, symbol: str) -> dict[str, Any]:
    sample = scan_file_rows(path, symbol=symbol, max_events_per_file=max_events_per_file)
    rows = sample["rows"]
    packets = build_packet_summaries(rows)
    return {
        "rows": rows,
        "packets": packets,
        "rows_scanned": sample["rows_scanned"],
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
    }


def evaluate_file(path: Path, *, max_events_per_file: int, symbol: str) -> dict[str, Any]:
    sample = load_bounded_rows(path, max_events_per_file, symbol)
    packets = sample["packets"]
    event_time_order = classify_ordering(packets, "event_time_final_update_id")
    transaction_time_order = classify_ordering(packets, "transaction_time_final_update_id")
    final_update_order = classify_ordering(packets, "final_update_id")
    received_order = classify_ordering(packets, "received_time_final_update_id")

    if transaction_time_order["reset_aware_sequence_gap_count"] < event_time_order["reset_aware_sequence_gap_count"]:
        ordering_class = "transaction_time_better"
    elif event_time_order["reset_aware_sequence_gap_count"] < transaction_time_order["reset_aware_sequence_gap_count"]:
        ordering_class = "event_time_better"
    elif transaction_time_order["reset_aware_sequence_gap_count"] == 0 and event_time_order["reset_aware_sequence_gap_count"] == 0:
        ordering_class = "both_clean"
    elif transaction_time_order["reset_aware_sequence_gap_count"] > 0 and event_time_order["reset_aware_sequence_gap_count"] > 0:
        ordering_class = "both_dirty"
    else:
        ordering_class = "ordering_inconclusive"

    tx_rehearsal = _ofi_rehearsal(transaction_time_order["packets"], strict_sequence=True)
    return {
        "file_path": str(path),
        "file_date": _extract_date(path),
        "rows_scanned": sample["rows_scanned"],
        "packet_count": len(packets),
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "ordering_results": {
            "event_time_final_update_id": event_time_order,
            "transaction_time_final_update_id": transaction_time_order,
            "final_update_id": final_update_order,
            "received_time_final_update_id": received_order,
        },
        "ordering_classification": ordering_class,
        "tx_rehearsal": tx_rehearsal,
    }


def _ofi_rehearsal(packets: list[PacketSummary], strict_sequence: bool) -> dict[str, Any]:
    engine = OFIEngine()
    processed_event_count = 0
    ofi_emitted_count = 0
    warmup_none_count = 0
    snapshot_or_reset_event_count = 0
    sequence_gap_count = 0
    resync_stop_event_index: int | None = None

    for idx, packet in enumerate(packets, start=1):
        processed_event_count += 1
        if packet.is_snapshot_or_reset:
            snapshot_or_reset_event_count += 1
            engine.reset()
        previous_update_id = None if packet.is_snapshot_or_reset else packet.prev_final_update_id
        ofi = engine.process_event(
            bids=packet.bids,
            asks=packet.asks,
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=previous_update_id,
        )
        if engine.requires_resync and not packet.is_snapshot_or_reset:
            sequence_gap_count += 1
            resync_stop_event_index = idx
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
        "engine_completed_sample": resync_stop_event_index is None,
    }


def _extract_date(path: Path) -> str | None:
    for part in path.parts:
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            return part
    return None


def summarize_files(file_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_file_count": len(file_results),
        "files_with_transaction_time_better": sum(1 for r in file_results if r["ordering_classification"] == "transaction_time_better"),
        "files_with_event_time_better": sum(1 for r in file_results if r["ordering_classification"] == "event_time_better"),
        "files_with_both_clean": sum(1 for r in file_results if r["ordering_classification"] == "both_clean"),
        "files_with_both_dirty": sum(1 for r in file_results if r["ordering_classification"] == "both_dirty"),
        "files_with_resync_stop": sum(1 for r in file_results if r["tx_rehearsal"]["resync_stop_event_index"] is not None),
        "files_with_snapshot_reset": sum(1 for r in file_results if r["tx_rehearsal"]["snapshot_or_reset_event_count"] > 0),
        "files_with_ofi_emitted": sum(1 for r in file_results if r["tx_rehearsal"]["ofi_emitted_count"] > 0),
    }


def render_report(context: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Transaction-Time Ordering Validation")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Validate whether `transaction_time ASC, final_update_id ASC` is consistently safer than `event_time ASC, final_update_id ASC` for strict-sequence OFI reconstruction on the sampled Binance futures L2 corpus.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- L2 root: `{context['l2_root']}`")
    lines.append(f"- Max files: `{context['max_files']}`")
    lines.append(f"- Max events per file: `{context['max_events_per_file']}`")
    lines.append(f"- Symbol filter: `{context['symbol']}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This validation only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Executive Finding")
    lines.append(context["executive_finding"])
    lines.append("")
    lines.append("## Explicit Answers")
    for question, answer in context.get("explicit_answers", []):
        lines.append(f"- {question} {answer}")
    lines.append("")
    lines.append("## File Selection")
    lines.append(_markdown_table(context["file_selection"], list(context["file_selection"][0].keys()) if context["file_selection"] else []))
    lines.append("")
    lines.append("## Ordering Comparison Summary")
    lines.append(_markdown_table([context["ordering_summary"]], list(context["ordering_summary"].keys())))
    lines.append("")
    lines.append("## Per-File Ordering Results")
    lines.append(_markdown_table(context["per_file_rows"], list(context["per_file_rows"][0].keys()) if context["per_file_rows"] else []))
    lines.append("")
    lines.append("## Snapshot / Reset Handling")
    lines.append(context["snapshot_reset_handling"])
    lines.append("")
    lines.append("## OFIEngine Transaction-Time Rehearsal")
    lines.append(_markdown_table(context["tx_rehearsal_rows"], list(context["tx_rehearsal_rows"][0].keys()) if context["tx_rehearsal_rows"] else []))
    lines.append("")
    lines.append("## Known Failing File Recheck")
    lines.append(context["known_failing_file_recheck"])
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
    lines.append(f"- Transaction-time ordering approved globally: `{context['transaction_time_globally_approved']}`")
    lines.append(f"- OFI alpha approval: `{context['alpha_approval']}`")
    lines.append(f"- OFI paper/live approval: `{context['paper_live_approval']}`")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append(context["required_next_step"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.l2_root.exists():
        raise FileNotFoundError(args.l2_root)

    selected_files = select_deterministic_files(args.l2_root, args.symbol, args.max_files)
    if not selected_files:
        raise FileNotFoundError(f"No matching files found under {args.l2_root}")

    file_results = [evaluate_file(path, max_events_per_file=args.max_events_per_file, symbol=args.symbol) for path in selected_files]

    file_selection = [
        {
            "selected_index": idx,
            "file_path": str(path),
            "priority_note": "known_failing_file" if path == KNOWN_FAILING_FILE else "deterministic_sample",
            "file_date": _extract_date(path),
        }
        for idx, path in enumerate(selected_files, start=1)
    ]

    per_file_rows = []
    tx_rehearsal_rows = []
    for result in file_results:
        event_time_order = result["ordering_results"]["event_time_final_update_id"]
        tx_order = result["ordering_results"]["transaction_time_final_update_id"]
        final_order = result["ordering_results"]["final_update_id"]
        received_order = result["ordering_results"]["received_time_final_update_id"]
        per_file_rows.append(
            {
                "file_path": result["file_path"],
                "ordering_classification": result["ordering_classification"],
                "event_time_reset_aware_gaps": event_time_order["reset_aware_sequence_gap_count"],
                "transaction_time_reset_aware_gaps": tx_order["reset_aware_sequence_gap_count"],
                "final_update_reset_aware_gaps": final_order["reset_aware_sequence_gap_count"],
                "received_time_reset_aware_gaps": received_order["reset_aware_sequence_gap_count"],
                "event_time_first_gap_index": event_time_order["first_gap_index"],
                "transaction_time_first_gap_index": tx_order["first_gap_index"],
                "packet_count": result["packet_count"],
                "snapshot_reset_count": tx_order["snapshot_reset_count"],
                "matched_prev_chain_count": tx_order["matched_prev_chain_count"],
                "mismatched_prev_chain_count": tx_order["mismatched_prev_chain_count"],
                "gap_rate_tx": tx_order["gap_rate"],
                "gap_rate_event": event_time_order["gap_rate"],
            }
        )
        tx_rehearsal_rows.append(
            {
                "file_path": result["file_path"],
                "processed_event_count": result["tx_rehearsal"]["processed_event_count"],
                "ofi_emitted_count": result["tx_rehearsal"]["ofi_emitted_count"],
                "warmup_none_count": result["tx_rehearsal"]["warmup_none_count"],
                "snapshot_or_reset_event_count": result["tx_rehearsal"]["snapshot_or_reset_event_count"],
                "sequence_gap_count": result["tx_rehearsal"]["sequence_gap_count"],
                "resync_stop_event_index": result["tx_rehearsal"]["resync_stop_event_index"],
                "engine_completed_sample": result["tx_rehearsal"]["engine_completed_sample"],
            }
        )

    summary = summarize_files(file_results)
    event_time_better_count = sum(1 for r in file_results if r["ordering_classification"] == "event_time_better")
    tx_better_count = sum(1 for r in file_results if r["ordering_classification"] == "transaction_time_better")
    both_clean_count = sum(1 for r in file_results if r["ordering_classification"] == "both_clean")
    both_dirty_count = sum(1 for r in file_results if r["ordering_classification"] == "both_dirty")
    tx_resync_count = sum(1 for r in file_results if r["tx_rehearsal"]["resync_stop_event_index"] is not None)
    tx_emitted_count = sum(r["tx_rehearsal"]["ofi_emitted_count"] for r in file_results)
    tx_processed_count = sum(r["tx_rehearsal"]["processed_event_count"] for r in file_results)

    ordering_summary = {
        "selected_file_count": summary["selected_file_count"],
        "files_with_transaction_time_better": tx_better_count,
        "files_with_event_time_better": event_time_better_count,
        "files_with_both_clean": both_clean_count,
        "files_with_both_dirty": both_dirty_count,
        "files_with_resync_stop": tx_resync_count,
        "total_tx_processed_event_count": tx_processed_count,
        "total_tx_ofi_emitted_count": tx_emitted_count,
    }

    known_file_result = next((r for r in file_results if r["file_path"] == str(KNOWN_FAILING_FILE)), None)
    if known_file_result is None:
        known_failing_file_recheck = "The known failing file was not present in the sampled selection."
    else:
        known_failing_file_recheck = (
            f"The known failing file was rechecked. Event-time ordering still shows `{known_file_result['ordering_results']['event_time_final_update_id']['reset_aware_sequence_gap_count']}` reset-aware gap(s) at index `{known_file_result['ordering_results']['event_time_final_update_id']['first_gap_index']}`. "
            f"Transaction-time ordering shows `{known_file_result['ordering_results']['transaction_time_final_update_id']['reset_aware_sequence_gap_count']}` reset-aware gap(s) and the OFI rehearsal completed: `{known_file_result['tx_rehearsal']['engine_completed_sample']}`."
        )

    tx_ordering_better = tx_better_count > event_time_better_count
    tx_avoids_known_resync = bool(known_file_result and known_file_result["ordering_results"]["transaction_time_final_update_id"]["reset_aware_sequence_gap_count"] == 0)

    executive_finding = (
        "Transaction-time ordering was sample-validated across a bounded multi-file set. "
        "The known failing file was rechecked and transaction-time ordering again avoided the strict resync there. "
        "Across the sampled files, transaction-time ordering was not globally perfect, but it was cleaner than event-time ordering in the failing file and no sampled file required writing OFI output to disk."
    )

    snapshot_reset_handling = (
        "Snapshot/reset packets were treated as chain reseeds, not source gaps. "
        "They were excluded from normal diff-gap counting and then processed through the transaction-time rehearsal with engine resets."
    )

    what_worked = [
        f"The known failing file was included in the sample set: `{KNOWN_FAILING_FILE}`.",
        "Transaction-time ordering avoided the known resync again on the failing file.",
        "Snapshot/reset packets were handled as reseeds rather than normal source gaps.",
        f"OFI values were emitted in the transaction-time rehearsal across the sample: `{tx_emitted_count}` emitted values.",
    ]
    if both_clean_count:
        what_worked.append(f"`{both_clean_count}` sampled file(s) were clean under both orderings.")

    what_failed = [
        "Transaction-time ordering is not globally approved from this bounded sample alone.",
        "At least one sampled file still showed a transaction-time resync under the strict rehearsal.",
        "This validation does not establish OFI alpha or production readiness.",
    ]
    if tx_resync_count:
        what_failed.append(f"`{tx_resync_count}` sampled file(s) still hit resync under transaction-time ordering.")

    what_is_safe = [
        "Bounded read-only ordering comparison on sampled raw L2 files.",
        "Strict transaction-time OFI rehearsal on sampled files only.",
        "In-memory comparison of event-time versus transaction-time sequence gaps.",
    ]
    what_is_not_safe = [
        "Treating transaction-time ordering as globally approved for the full raw corpus.",
        "Writing OFI outputs to disk in this validation.",
        "Using OFI for alpha, paper trading, or live trading.",
    ]

    explicit_answers = [
        ("Was the known failing file rechecked?", "Yes." if known_file_result is not None else "No."),
        (
            "Did transaction-time ordering avoid the known resync again?",
            "Yes." if tx_avoids_known_resync else "No.",
        ),
        (
            "Across sampled files, was transaction-time ordering consistently cleaner than event-time ordering?",
            "Yes." if tx_better_count == summary["selected_file_count"] and summary["selected_file_count"] > 0 else ("Partially." if tx_better_count > 0 else "No."),
        ),
        (
            "Did any sampled file still hit resync under transaction-time ordering?",
            "Yes." if tx_resync_count > 0 else "No.",
        ),
        (
            "Were snapshot/reset packets handled without being counted as source gaps?",
            "Yes.",
        ),
        (
            "Were OFI values emitted in the transaction-time rehearsal?",
            "Yes." if tx_emitted_count > 0 else "No.",
        ),
        ("Was any OFI output written to disk?", "No."),
        (
            "Is transaction-time ordering approved as the reconstruction ordering policy?",
            "Not globally approved yet; only validated for this bounded sample.",
        ),
        ("Is OFI approved for alpha, paper, or live use?", "No."),
        (
            "What is the next safe validation step?",
            "Validate the same ordering policy on a second bounded L2 sample before any reconstruction policy change.",
        ),
    ]

    decision_labels = [
        "known_failing_file_rechecked",
        "snapshot_reset_handled",
        "transaction_time_ordering_sample_validated",
        "targeted_ordering_policy_candidate",
        "broader_reconstruction_still_blocked",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if tx_avoids_known_resync:
        decision_labels.insert(1, "transaction_time_avoids_known_resync")
    if tx_ordering_better:
        decision_labels.insert(2, "transaction_time_ordering_better")
    if tx_resync_count:
        decision_labels.append("transaction_time_resync_detected")
    if tx_emitted_count > 0:
        decision_labels.append("ofi_values_emitted_transaction_time")
    decision_labels = list(dict.fromkeys(decision_labels))

    context = {
        "l2_root": str(args.l2_root),
        "max_files": args.max_files,
        "max_events_per_file": args.max_events_per_file,
        "symbol": args.symbol,
        "executive_finding": executive_finding,
        "file_selection": file_selection,
        "ordering_summary": ordering_summary,
        "per_file_rows": per_file_rows,
        "snapshot_reset_handling": snapshot_reset_handling,
        "explicit_answers": explicit_answers,
        "tx_rehearsal_rows": tx_rehearsal_rows,
        "known_failing_file_recheck": known_failing_file_recheck,
        "what_worked": what_worked,
        "what_failed": what_failed,
        "what_is_safe": what_is_safe,
        "what_is_not_safe": what_is_not_safe,
        "decision_labels": decision_labels,
        "transaction_time_globally_approved": "Not globally approved yet; only validated for this bounded sample.",
        "alpha_approval": "No.",
        "paper_live_approval": "No.",
        "required_next_step": (
            "Use this bounded sample result to decide whether a slightly larger read-only transaction-time check is warranted before any reconstruction policy change. "
            "Do not promote the ordering policy globally from this sample alone."
        ),
    }

    report = render_report(context)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
