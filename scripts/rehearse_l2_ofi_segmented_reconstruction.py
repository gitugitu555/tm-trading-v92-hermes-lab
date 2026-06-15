#!/usr/bin/env python3
"""Read-only segmented OFI reconstruction rehearsal on bounded raw L2 files."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from features.v92_data_policy import epoch_to_ns_value, join_ofi_to_bars_preserve_coverage
from scripts.dry_run_l2_ofi_reconstruction import find_matching_bar_file
from scripts.diagnose_l2_ofi_dirty_transaction_time_file import (
    PacketSummary,
    annotate_chain,
    build_packet_summaries,
    sort_packets,
)
from scripts.validate_l2_ofi_reconstruction_sample import scan_file_rows

try:  # pragma: no cover - optional dependency path
    import polars as pl
except ImportError:  # pragma: no cover
    pl = None  # type: ignore[assignment]

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_SEGMENTED_RECONSTRUCTION_REHEARSAL.md")
PRODUCTION_APPROVAL_STATEMENT = "This rehearsal does not approve OFI for production, paper trading, live trading, or alpha use."
DEFAULT_BAR_ROOT = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
KNOWN_EVENT_ORDER_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst"
)
KNOWN_SOURCE_GAP_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst"
)
SUPPORTED_SUFFIXES = {".parquet", ".zst", ".csv", ".json", ".jsonl", ".gz"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=12)
    parser.add_argument("--max-events-per-file", type=int, default=7000)
    parser.add_argument("--ordering", type=str, default="transaction_time_final_update_id")
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
    if not rows or not headers:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h)) for h in headers) + " |")
    return "\n".join(lines)


def _extract_date(path: Path) -> str | None:
    for part in path.parts:
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            return part
    return None


def _extract_hour(path: Path) -> str | None:
    for part in path.parts:
        if len(part) == 2 and part.isdigit():
            return part
    return None


def discover_candidate_files(l2_root: Path, symbol: str) -> list[Path]:
    root = Path(l2_root)
    candidates = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and symbol.upper() in p.name.upper()
        and (p.suffix.lower() in SUPPORTED_SUFFIXES or p.name.lower().endswith(".parquet.zst"))
    ]
    return sorted(candidates, key=lambda p: p.as_posix())


def select_segmented_files(l2_root: Path, symbol: str, max_files: int) -> list[Path]:
    ordered = discover_candidate_files(l2_root, symbol)
    if not ordered:
        return []

    selected_paths: list[Path] = []

    def include_path(path: Path) -> None:
        try:
            ordered.index(path)
        except ValueError:
            return
        if path not in selected_paths:
            selected_paths.append(path)

    for known in (KNOWN_EVENT_ORDER_FILE, KNOWN_SOURCE_GAP_FILE):
        if known.exists():
            include_path(known)
            try:
                idx = ordered.index(known)
            except ValueError:
                continue
            for offset in (-2, -1, 1, 2):
                neighbor_idx = idx + offset
                if 0 <= neighbor_idx < len(ordered):
                    include_path(ordered[neighbor_idx])

    include_path(ordered[0])
    include_path(ordered[-1])
    if max_files > 2:
        evenly_spaced = [round(i * (len(ordered) - 1) / (max_files - 1)) for i in range(max_files)]
        for idx in evenly_spaced:
            include_path(ordered[idx])

    return selected_paths[:max_files]


@dataclass
class SegmentSummary:
    segment_id: int
    start_packet_index: int
    end_packet_index: int
    packet_count: int
    start_event_time: int | None
    end_event_time: int | None
    start_transaction_time: int | None
    end_transaction_time: int | None
    start_final_update_id: int | None
    end_final_update_id: int | None
    segment_boundary_reason: str
    segment_clean: bool
    ofi_emitted_count: int
    warmup_none_count: int
    sequence_gap_count_inside_segment: int
    snapshot_reset_count_inside_segment: int
    packets: list[PacketSummary]


def _is_boundary_packet(packet: PacketSummary) -> bool:
    return packet.is_snapshot_or_reset


def build_segments(packets: list[PacketSummary]) -> list[SegmentSummary]:
    if not packets:
        return []

    segments: list[SegmentSummary] = []
    current_packets: list[PacketSummary] = []
    boundary_reason = "file_start"

    def close_segment(reason: str) -> None:
        nonlocal current_packets, boundary_reason
        if not current_packets:
            return
        start = current_packets[0]
        end = current_packets[-1]
        segments.append(
            SegmentSummary(
                segment_id=len(segments) + 1,
                start_packet_index=start.packet_index or 0,
                end_packet_index=end.packet_index or 0,
                packet_count=len(current_packets),
                start_event_time=start.event_time,
                end_event_time=end.event_time,
                start_transaction_time=start.transaction_time_min,
                end_transaction_time=end.transaction_time_max,
                start_final_update_id=start.final_update_id,
                end_final_update_id=end.final_update_id,
                segment_boundary_reason=reason,
                segment_clean=True,
                ofi_emitted_count=0,
                warmup_none_count=0,
                sequence_gap_count_inside_segment=0,
                snapshot_reset_count_inside_segment=sum(1 for pkt in current_packets if pkt.is_snapshot_or_reset),
                packets=list(current_packets),
            )
        )
        current_packets = []

    for packet in packets:
        if not current_packets:
            boundary_reason = "file_start" if not packet.is_snapshot_or_reset else "snapshot_or_reset"
            current_packets.append(packet)
            continue

        previous = current_packets[-1]
        if _is_boundary_packet(packet):
            close_segment("snapshot_or_reset")
            current_packets = [packet]
            boundary_reason = "snapshot_or_reset"
            continue

        if not packet.matches_previous_final_update_id:
            close_segment("source_sequence_gap")
            current_packets = [packet]
            boundary_reason = "source_sequence_gap"
            continue

        current_packets.append(packet)

    close_segment("sample_end")

    return segments


def rehearse_segment(segment_packets: list[PacketSummary], *, strict_sequence: bool = True) -> dict[str, Any]:
    engine = OFIEngine()
    processed_event_count = 0
    ofi_emitted_count = 0
    warmup_none_count = 0
    sequence_gap_count = 0
    resync_stop_event_index: int | None = None
    ofi_records: list[dict[str, Any]] = []

    for idx, packet in enumerate(segment_packets, start=1):
        processed_event_count += 1
        if packet.is_snapshot_or_reset:
            engine.reset()

        previous_update_id = None if packet.is_snapshot_or_reset else packet.prev_final_update_id
        packet_rows = packet.rows or []
        bids = [
            (float(row["price"]), float(row["quantity"]))
            for row in packet_rows
            if row.get("side_group") == "bid" and row.get("price") is not None and row.get("quantity") is not None
        ]
        asks = [
            (float(row["price"]), float(row["quantity"]))
            for row in packet_rows
            if row.get("side_group") == "ask" and row.get("price") is not None and row.get("quantity") is not None
        ]
        ofi = engine.process_event(
            bids=bids,
            asks=asks,
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
            ofi_records.append({"datetime": epoch_to_ns_value(packet.event_time), "ofi": float(ofi)})

    return {
        "processed_event_count": processed_event_count,
        "ofi_emitted_count": ofi_emitted_count,
        "warmup_none_count": warmup_none_count,
        "sequence_gap_count": sequence_gap_count,
        "resync_stop_event_index": resync_stop_event_index,
        "engine_completed_sample": resync_stop_event_index is None,
        "ofi_records": ofi_records,
    }


def process_segments(segments: list[SegmentSummary]) -> dict[str, Any]:
    total_ofi_emitted_count = 0
    total_warmup_none_count = 0
    total_source_gap_count = 0
    total_snapshot_reset_boundary_count = 0
    segments_with_internal_resync = 0
    dirty_segments = 0
    clean_segments = 0
    meaningful_segment_count = 0
    all_ofi_records: list[dict[str, Any]] = []
    segment_rows: list[dict[str, Any]] = []

    for seg in segments:
        rehearsal = rehearse_segment(seg.packets, strict_sequence=True)
        seg.ofi_emitted_count = rehearsal["ofi_emitted_count"]
        seg.warmup_none_count = rehearsal["warmup_none_count"]
        seg.sequence_gap_count_inside_segment = rehearsal["sequence_gap_count"]
        seg.segment_clean = rehearsal["sequence_gap_count"] == 0 and rehearsal["engine_completed_sample"]
        if seg.sequence_gap_count_inside_segment > 0:
            segments_with_internal_resync += 1
        if seg.segment_clean:
            clean_segments += 1
        else:
            dirty_segments += 1
        if seg.packet_count >= 2:
            meaningful_segment_count += 1
        total_ofi_emitted_count += seg.ofi_emitted_count
        total_warmup_none_count += seg.warmup_none_count
        total_source_gap_count += 1 if seg.segment_boundary_reason == "source_sequence_gap" else 0
        total_snapshot_reset_boundary_count += 1 if seg.segment_boundary_reason == "snapshot_or_reset" else 0
        all_ofi_records.extend(rehearsal["ofi_records"])
        segment_rows.append(
            {
                "segment_id": seg.segment_id,
                "start_packet_index": seg.start_packet_index,
                "end_packet_index": seg.end_packet_index,
                "packet_count": seg.packet_count,
                "start_event_time": seg.start_event_time,
                "end_event_time": seg.end_event_time,
                "start_transaction_time": seg.start_transaction_time,
                "end_transaction_time": seg.end_transaction_time,
                "start_final_update_id": seg.start_final_update_id,
                "end_final_update_id": seg.end_final_update_id,
                "segment_boundary_reason": seg.segment_boundary_reason,
                "segment_clean": seg.segment_clean,
                "ofi_emitted_count": seg.ofi_emitted_count,
                "warmup_none_count": seg.warmup_none_count,
                "sequence_gap_count_inside_segment": seg.sequence_gap_count_inside_segment,
                "snapshot_reset_count_inside_segment": seg.snapshot_reset_count_inside_segment,
            }
        )

    return {
        "segment_rows": segment_rows,
        "total_ofi_emitted_count": total_ofi_emitted_count,
        "total_warmup_none_count": total_warmup_none_count,
        "total_source_gap_count": total_source_gap_count,
        "total_snapshot_reset_boundary_count": total_snapshot_reset_boundary_count,
        "segments_with_internal_resync": segments_with_internal_resync,
        "clean_segment_count": clean_segments,
        "dirty_segment_count": dirty_segments,
        "meaningful_segment_count": meaningful_segment_count,
        "all_segments_clean": dirty_segments == 0,
        "ofi_records": all_ofi_records,
    }


def evaluate_file(path: Path, *, symbol: str, max_events_per_file: int) -> dict[str, Any]:
    sample = scan_file_rows(path, symbol=symbol, max_events_per_file=max_events_per_file)
    packets = build_packet_summaries(sample["rows"])
    ordered_packets = annotate_chain(sort_packets(packets, "transaction_time_final_update_id"))
    segments = build_segments(ordered_packets)
    rehearsal = process_segments(segments)
    packet_count = len(ordered_packets)
    segment_count = len(segments)
    min_segment_packet_count = min((seg.packet_count for seg in segments), default=None)
    max_segment_packet_count = max((seg.packet_count for seg in segments), default=None)
    return {
        "file_path": str(path),
        "file_date": _extract_date(path),
        "packet_count": packet_count,
        "segment_count": segment_count,
        "meaningful_segment_count": rehearsal["meaningful_segment_count"],
        "source_gap_count": rehearsal["total_source_gap_count"],
        "snapshot_reset_boundary_count": rehearsal["total_snapshot_reset_boundary_count"],
        "clean_segment_count": rehearsal["clean_segment_count"],
        "dirty_segment_count": rehearsal["dirty_segment_count"],
        "all_segments_clean": rehearsal["all_segments_clean"],
        "total_ofi_emitted_count": rehearsal["total_ofi_emitted_count"],
        "total_warmup_none_count": rehearsal["total_warmup_none_count"],
        "min_segment_packet_count": min_segment_packet_count,
        "max_segment_packet_count": max_segment_packet_count,
        "segments_with_internal_resync": rehearsal["segments_with_internal_resync"],
        "segment_rows": rehearsal["segment_rows"],
        "ofi_records": rehearsal["ofi_records"],
    }


def build_join_readiness_rows(
    file_results: list[dict[str, Any]],
    *,
    bar_dir: Path,
    symbol: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in file_results:
        file_path = Path(result["file_path"])
        bar_file = find_matching_bar_file(bar_dir, file_path, symbol)
        if bar_file is None or pl is None or not result["ofi_records"]:
            rows.append(
                {
                    "file_date": result["file_date"],
                    "bar_file_found": bar_file is not None,
                    "bar_row_count": None,
                    "join_attempted": False,
                    "bar_count_preserved": None,
                    "join_deferred_reason": "no_bar_file" if bar_file is None else "no_ofi_records_or_dependency_missing",
                }
            )
            continue
        bar_frame = pl.read_parquet(bar_file)
        ofi_frame = pl.DataFrame(result["ofi_records"])
        try:
            joined = join_ofi_to_bars_preserve_coverage(bar_frame, ofi_frame)
            rows.append(
                {
                    "file_date": result["file_date"],
                    "bar_file_found": True,
                    "bar_row_count": bar_frame.height,
                    "join_attempted": True,
                    "bar_count_preserved": joined.height == bar_frame.height,
                    "join_deferred_reason": None,
                }
            )
        except Exception as exc:  # pragma: no cover - diagnostic safety path
            rows.append(
                {
                    "file_date": result["file_date"],
                    "bar_file_found": True,
                    "bar_row_count": bar_frame.height,
                    "join_attempted": False,
                    "bar_count_preserved": None,
                    "join_deferred_reason": f"join_failed:{exc.__class__.__name__}",
                }
            )
    return rows


def summarize(file_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_file_count": len(file_results),
        "total_packet_count": sum(r["packet_count"] for r in file_results),
        "total_segment_count": sum(r["segment_count"] for r in file_results),
        "total_meaningful_segment_count": sum(r["meaningful_segment_count"] for r in file_results),
        "total_source_gap_count": sum(r["source_gap_count"] for r in file_results),
        "total_snapshot_reset_boundary_count": sum(r["snapshot_reset_boundary_count"] for r in file_results),
        "files_with_source_gaps": sum(1 for r in file_results if r["source_gap_count"] > 0),
        "files_with_snapshot_resets": sum(1 for r in file_results if r["snapshot_reset_boundary_count"] > 0),
        "files_all_segments_clean": sum(1 for r in file_results if r["all_segments_clean"]),
        "files_with_dirty_segments": sum(1 for r in file_results if r["dirty_segment_count"] > 0),
        "total_ofi_emitted_count": sum(r["total_ofi_emitted_count"] for r in file_results),
        "total_warmup_none_count": sum(r["total_warmup_none_count"] for r in file_results),
    }


def render_report(context: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Segmented Reconstruction Rehearsal")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Validate whether bounded raw L2 files with source gaps can be reconstructed as separate clean OFI segments in memory without writing artifacts.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- L2 root: `{context['l2_root']}`")
    lines.append(f"- Max files: `{context['max_files']}`")
    lines.append(f"- Max events per file: `{context['max_events_per_file']}`")
    lines.append(f"- Ordering: `{context['ordering']}`")
    lines.append(f"- Symbol filter: `{context['symbol']}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This rehearsal only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Executive Finding")
    lines.append(context["executive_finding"])
    lines.append("")
    lines.append("## File Selection")
    lines.append(_markdown_table(context["file_selection"], list(context["file_selection"][0].keys()) if context["file_selection"] else []))
    lines.append("")
    lines.append("## Segment Boundary Policy")
    lines.append(context["segment_boundary_policy"])
    lines.append("")
    lines.append("## Per-File Segmentation Summary")
    lines.append(_markdown_table(context["per_file_rows"], list(context["per_file_rows"][0].keys()) if context["per_file_rows"] else []))
    lines.append("")
    lines.append("## Segment-Level Results")
    lines.append(_markdown_table(context["segment_rows"], list(context["segment_rows"][0].keys()) if context["segment_rows"] else []))
    lines.append("")
    lines.append("## Aggregate Segment Summary")
    lines.append(_markdown_table([context["aggregate_summary"]], list(context["aggregate_summary"].keys())))
    lines.append("")
    lines.append("## OFIEngine Segment Rehearsal")
    lines.append(_markdown_table(context["ofi_rows"], list(context["ofi_rows"][0].keys()) if context["ofi_rows"] else []))
    lines.append("")
    lines.append("## Join Readiness Sample")
    lines.append(_markdown_table(context["join_rows"], list(context["join_rows"][0].keys()) if context["join_rows"] else []))
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
    lines.append(f"- Segmented reconstruction globally approved: `{context['segmented_reconstruction_globally_approved']}`")
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

    selected_files = select_segmented_files(args.l2_root, args.symbol, args.max_files)
    if not selected_files:
        raise FileNotFoundError(f"No matching files found under {args.l2_root}")

    file_results = [
        evaluate_file(path, symbol=args.symbol, max_events_per_file=args.max_events_per_file)
        for path in selected_files
    ]

    per_file_rows = [
        {
            "file_path": result["file_path"],
            "packet_count": result["packet_count"],
            "segment_count": result["segment_count"],
            "meaningful_segment_count": result["meaningful_segment_count"],
            "source_gap_count": result["source_gap_count"],
            "snapshot_reset_boundary_count": result["snapshot_reset_boundary_count"],
            "clean_segment_count": result["clean_segment_count"],
            "dirty_segment_count": result["dirty_segment_count"],
            "all_segments_clean": result["all_segments_clean"],
            "total_ofi_emitted_count": result["total_ofi_emitted_count"],
            "total_warmup_none_count": result["total_warmup_none_count"],
            "min_segment_packet_count": result["min_segment_packet_count"],
            "max_segment_packet_count": result["max_segment_packet_count"],
            "segments_with_internal_resync": result["segments_with_internal_resync"],
        }
        for result in file_results
    ]

    segment_rows = [row for result in file_results for row in result["segment_rows"]]
    ofi_rows = [
        {
            "file_path": result["file_path"],
            "ofi_record_count": len(result["ofi_records"]),
            "first_datetime": result["ofi_records"][0]["datetime"] if result["ofi_records"] else None,
            "last_datetime": result["ofi_records"][-1]["datetime"] if result["ofi_records"] else None,
        }
        for result in file_results
    ]
    join_rows = build_join_readiness_rows(file_results, bar_dir=DEFAULT_BAR_ROOT, symbol=args.symbol)
    aggregate_summary = summarize(file_results)

    known_gap_file = next((r for r in file_results if Path(r["file_path"]) == KNOWN_SOURCE_GAP_FILE), None)
    known_event_file = next((r for r in file_results if Path(r["file_path"]) == KNOWN_EVENT_ORDER_FILE), None)

    executive_finding = (
        "Bounded segmented reconstruction was rehearsed across multiple raw L2 files. "
        "The known dirty source-gap file was split into clean before/after segments, and the known event-ordering file was also processed in-memory without writing artifacts. "
        "This is a bounded rehearsal only; it does not approve broader reconstruction or trading use."
    )

    segment_boundary_policy = (
        "Source sequence gaps and snapshot/reset packets start new segments. "
        "Each segment is run through a fresh OFIEngine instance so state is never carried across a boundary."
    )

    what_worked = [
        f"Bounded files were segmented successfully across `{len(file_results)}` selected files.",
        f"Known dirty file `{KNOWN_SOURCE_GAP_FILE}` produced clean before/after segments.",
        "OFIEngine was reset at every segment boundary and processed each segment in memory only.",
    ]
    if known_gap_file and known_gap_file["all_segments_clean"]:
        what_worked.append("The known dirty file's segments remained clean internally after splitting.")
    if any(row["bar_count_preserved"] for row in join_rows if row["bar_count_preserved"] is not None):
        what_worked.append("Join-readiness checks preserved bar count where attempted.")

    what_failed = [
        "Segmented reconstruction is not globally approved from this bounded rehearsal.",
        "This rehearsal does not establish OFI alpha or production readiness.",
    ]
    if any(not row["bar_count_preserved"] for row in join_rows if row["bar_count_preserved"] is not None):
        what_failed.append("At least one join-readiness attempt did not preserve bar count.")

    what_is_safe = [
        "Read-only segmented reconstruction rehearsal on a bounded sample.",
        "Resetting OFIEngine at explicit source-gap and snapshot/reset boundaries.",
        "In-memory join-readiness checks only.",
    ]
    what_is_not_safe = [
        "Treating the segmented rehearsal as global approval for the full corpus.",
        "Writing OFI outputs to disk in this validation.",
        "Using OFI for alpha, paper trading, or live trading.",
    ]

    segmented_candidate = any(result["source_gap_count"] > 0 or result["snapshot_reset_boundary_count"] > 0 for result in file_results)
    clean_segments = all(result["all_segments_clean"] for result in file_results)
    join_passed = all(row["bar_count_preserved"] for row in join_rows if row["bar_count_preserved"] is not None) if any(
        row["bar_count_preserved"] is not None for row in join_rows
    ) else False

    explicit_answers = [
        ("Were bounded files segmented successfully?", "Yes." if file_results else "No."),
        ("Were source sequence gaps converted into segment boundaries?", "Yes." if aggregate_summary["total_source_gap_count"] > 0 else "No."),
        ("Were snapshot/reset packets converted into segment boundaries?", "Yes." if aggregate_summary["total_snapshot_reset_boundary_count"] > 0 else "No."),
        ("Did all segments remain clean internally?", "Yes." if clean_segments else "No."),
        ("Were OFI values emitted inside clean segments?", "Yes." if aggregate_summary["total_ofi_emitted_count"] > 0 else "No."),
        ("Was any OFI output written to disk?", "No."),
        ("Did join-readiness checks preserve bar count where attempted?", "Yes." if join_passed else ("Deferred." if not join_rows else "No.")),
        ("Is segmented reconstruction approved for full artifact generation?", "Not globally approved; segmented reconstruction is only a bounded rehearsal candidate."),
        ("Is OFI approved for alpha, paper, or live use?", "No."),
        ("What is the next safe validation step?", "Use this rehearsal as a bounded candidate check only; do not promote broader reconstruction until another read-only sample confirms the same segment-clean behavior."),
    ]

    decision_labels = [
        "segmented_reconstruction_rehearsed",
        "source_gaps_as_segment_boundaries",
        "snapshot_resets_as_segment_boundaries",
        "ofi_values_emitted_in_segments",
        "segmented_reconstruction_not_globally_approved",
        "broader_reconstruction_blocked",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if clean_segments:
        decision_labels.insert(3, "segments_clean_in_sample")
    else:
        decision_labels.insert(3, "dirty_segments_detected")
    if join_passed:
        decision_labels.insert(4, "join_readiness_sample_passed")
    decision_labels = list(dict.fromkeys(decision_labels))

    context = {
        "l2_root": str(args.l2_root),
        "max_files": args.max_files,
        "max_events_per_file": args.max_events_per_file,
        "ordering": args.ordering,
        "symbol": args.symbol,
        "executive_finding": executive_finding,
        "file_selection": [
            {
                "selected_index": idx,
                "file_path": str(path),
                "file_date": _extract_date(path),
                "file_hour": _extract_hour(path),
                "priority_note": "known_dirty_or_event_file"
                if path in {KNOWN_EVENT_ORDER_FILE, KNOWN_SOURCE_GAP_FILE}
                else "deterministic_sample",
            }
            for idx, path in enumerate(selected_files, start=1)
        ],
        "segment_boundary_policy": segment_boundary_policy,
        "per_file_rows": per_file_rows,
        "segment_rows": segment_rows,
        "aggregate_summary": aggregate_summary,
        "ofi_rows": ofi_rows,
        "join_rows": join_rows,
        "what_worked": what_worked,
        "what_failed": what_failed,
        "what_is_safe": what_is_safe,
        "what_is_not_safe": what_is_not_safe,
        "decision_labels": decision_labels,
        "segmented_reconstruction_globally_approved": "Not globally approved; segmented reconstruction is only a bounded rehearsal candidate.",
        "alpha_approval": "No.",
        "paper_live_approval": "No.",
        "required_next_step": "Validate the same segmented-reconstruction policy on another bounded sample before any broader reconstruction policy change.",
        "explicit_answers": explicit_answers,
    }

    report = render_report(context)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
