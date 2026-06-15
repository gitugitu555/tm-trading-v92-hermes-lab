"""Reusable segmented L2 OFI reconstruction policy.

This module captures the bounded rehearsal behavior proven on sampled raw L2
files. It provides deterministic packet ordering, segment boundary detection,
and in-memory OFIEngine segment processing without writing OFI artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from features.microstructure_ofi import OFIEngine


@dataclass(frozen=True)
class L2Packet:
    symbol: str
    event_type: str
    event_time: int
    transaction_time: int | None
    received_time: int | None
    first_update_id: int | None
    final_update_id: int
    prev_final_update_id: int | None
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class L2Segment:
    segment_id: int
    start_packet_index: int
    end_packet_index: int
    start_reason: str
    boundary_reason: str
    packets: tuple[L2Packet, ...]


@dataclass(frozen=True)
class SegmentRunResult:
    segment_id: int
    packet_count: int
    ofi_emitted_count: int
    warmup_none_count: int
    sequence_gap_count: int
    clean: bool


def packet_sort_key(packet: L2Packet) -> tuple:
    """Sort by transaction_time ASC, final_update_id ASC.

    If transaction_time is missing, fall back conservatively to event_time.
    """

    if packet.transaction_time is None:
        return (1, packet.event_time, packet.final_update_id, packet.symbol, packet.event_type)
    return (0, packet.transaction_time, packet.final_update_id, packet.symbol, packet.event_type)


def is_snapshot_or_reset(packet: L2Packet) -> bool:
    """Return True when the packet carries snapshot/reset semantics."""

    return packet.first_update_id is None or packet.prev_final_update_id is None


def is_source_gap(previous: L2Packet, current: L2Packet) -> bool:
    """Return True for a normal diff packet that breaks the prev/final chain."""

    if is_snapshot_or_reset(previous) or is_snapshot_or_reset(current):
        return False
    return current.prev_final_update_id != previous.final_update_id


def segment_packets(packets: Iterable[L2Packet]) -> tuple[L2Segment, ...]:
    """Sort packets and split them into deterministic reconstruction segments.

    Boundary reasons are recorded on the segment that is closed by the boundary.
    The terminal segment uses ``sample_end``. The file start is implicit and
    begins the first segment.
    """

    ordered = tuple(sorted(tuple(packets), key=packet_sort_key))
    if not ordered:
        return ()

    segments: list[L2Segment] = []
    current_packets: list[L2Packet] = [ordered[0]]
    start_packet_index = 1
    start_reason = "file_start"

    def close_segment(boundary_reason: str, end_index: int) -> None:
        if not current_packets:
            return
        segments.append(
            L2Segment(
                segment_id=len(segments) + 1,
                start_packet_index=start_packet_index,
                end_packet_index=end_index,
                start_reason=start_reason,
                boundary_reason=boundary_reason,
                packets=tuple(current_packets),
            )
        )

    for idx, packet in enumerate(ordered[1:], start=2):
        previous = current_packets[-1]
        if is_snapshot_or_reset(packet):
            close_segment("snapshot_or_reset", idx - 1)
            current_packets = [packet]
            start_packet_index = idx
            start_reason = "snapshot_or_reset"
            continue
        if is_source_gap(previous, packet):
            close_segment("source_sequence_gap", idx - 1)
            current_packets = [packet]
            start_packet_index = idx
            start_reason = "source_sequence_gap"
            continue
        current_packets.append(packet)

    close_segment("sample_end", len(ordered))
    return tuple(segments)


def run_segment_with_ofi_engine(segment: L2Segment, *, strict_sequence: bool = True) -> SegmentRunResult:
    """Run one segment through a fresh OFIEngine instance in memory only."""

    engine = OFIEngine()
    ofi_emitted_count = 0
    warmup_none_count = 0
    sequence_gap_count = 0

    for packet in segment.packets:
        if is_snapshot_or_reset(packet):
            engine.reset()

        ofi = engine.process_event(
            bids=list(packet.bids),
            asks=list(packet.asks),
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=None if is_snapshot_or_reset(packet) else packet.prev_final_update_id,
        )
        if engine.requires_resync and not is_snapshot_or_reset(packet):
            sequence_gap_count += 1
            if strict_sequence:
                break
            engine.reset()
            continue
        if ofi is None:
            warmup_none_count += 1
        else:
            ofi_emitted_count += 1

    return SegmentRunResult(
        segment_id=segment.segment_id,
        packet_count=len(segment.packets),
        ofi_emitted_count=ofi_emitted_count,
        warmup_none_count=warmup_none_count,
        sequence_gap_count=sequence_gap_count,
        clean=sequence_gap_count == 0,
    )


def summarize_segments(segments: Iterable[L2Segment], results: Iterable[SegmentRunResult]) -> dict[str, int | bool]:
    """Summarize segmented reconstruction rehearsal results."""

    segments = tuple(segments)
    results = tuple(results)
    return {
        "segment_count": len(segments),
        "meaningful_segment_count": sum(1 for segment in segments if len(segment.packets) >= 2),
        "clean_segment_count": sum(1 for result in results if result.clean),
        "dirty_segment_count": sum(1 for result in results if not result.clean),
        "all_segments_clean": all(result.clean for result in results) if results else True,
        "total_ofi_emitted_count": sum(result.ofi_emitted_count for result in results),
        "total_warmup_none_count": sum(result.warmup_none_count for result in results),
        "total_sequence_gap_count": sum(result.sequence_gap_count for result in results),
    }
