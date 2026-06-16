from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.validate_l2_ofi_discovered_policy_path_candidates as script
from features.l2_ofi_segmented_reconstruction import L2Packet, L2Segment, SegmentRunResult, packet_sort_key, segment_packets


def _row(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    first_update_id: int | None = 1,
    transaction_time: int | None = 10,
    received_time: int | None = 20,
    side: str = "bid",
    price: str = "100.0",
    quantity: str = "1.0",
):
    return {
        "symbol": "BTCUSDT",
        "event_time": event_time,
        "transaction_time": transaction_time,
        "received_time": received_time,
        "event_type": "depthUpdate",
        "first_update_id": first_update_id,
        "final_update_id": final_update_id,
        "prev_final_update_id": prev_final_update_id,
        "last_update_id": final_update_id,
        "side": side,
        "price": price,
        "quantity": quantity,
    }


def _result(*, timestamp_fallback_used: bool) -> script.CandidateResult:
    return script.CandidateResult(
        file_path="/tmp/candidate.parquet.zst",
        candidate_reason="snapshot_reset_candidate",
        file_date="2026-05-26",
        file_hour="00",
        rows_scanned=2,
        packet_count=1,
        missing_transaction_time_count=1 if timestamp_fallback_used else 0,
        missing_first_update_id_count=0,
        missing_prev_final_update_id_count=0,
        snapshot_like_packet_count=0,
        timestamp_fallback_used=timestamp_fallback_used,
        timestamp_non_monotonic_hint_count=0,
        event_time_non_monotonic_hint_count=0,
        transaction_time_non_monotonic_hint_count=0,
        received_time_non_monotonic_hint_count=0,
        source_gap_boundary_count=0,
        snapshot_reset_boundary_count=0,
        segment_count=1,
        meaningful_segment_count=1,
        one_packet_segment_count=0,
        clean_segment_count=1,
        dirty_segment_count=0,
        all_segments_clean=True,
        total_ofi_emitted_count=1,
        total_warmup_none_count=0,
        total_sequence_gap_count=0,
        min_segment_packet_count=2,
        max_segment_packet_count=2,
        side_mapping_unknown_count=0,
        policy_module_used_directly=True,
    )


def test_default_candidate_inputs_include_snapshot_reset_and_source_gap_groups():
    candidates = script.build_candidate_inputs(None)
    reasons = [candidate.reason for candidate in candidates]
    assert reasons.count("snapshot_reset_candidate") == 2
    assert reasons.count("source_gap_timestamp_candidate") == 6


def test_raw_rows_convert_into_l2packet_objects_and_use_policy_segment_packets(monkeypatch):
    frame = pd.DataFrame(
        [
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="bid", price="100.5", quantity="2.0"),
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="ask", price="101.5", quantity="3.0"),
            _row(event_time=2, final_update_id=11, prev_final_update_id=10, transaction_time=None, received_time=1, side="bid", price="102.0", quantity="1.5"),
        ]
    )
    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: frame)

    seen_packet_types: list[type] = []

    def fake_segment_packets(packets):
        packets = tuple(packets)
        assert packets
        seen_packet_types.extend(type(packet) for packet in packets)
        assert all(isinstance(packet, L2Packet) for packet in packets)
        return (
            L2Segment(
                segment_id=1,
                start_packet_index=1,
                end_packet_index=len(packets),
                start_reason="file_start",
                boundary_reason="sample_end",
                packets=packets,
            ),
        )

    monkeypatch.setattr(script, "segment_packets", fake_segment_packets)
    monkeypatch.setattr(
        script,
        "run_segment_with_ofi_engine",
        lambda segment, strict_sequence=True: SegmentRunResult(
            segment_id=segment.segment_id,
            packet_count=len(segment.packets),
            ofi_emitted_count=1,
            warmup_none_count=0,
            sequence_gap_count=0,
            clean=True,
        ),
    )
    monkeypatch.setattr(
        script,
        "summarize_segments",
        lambda segments, results: {
            "segment_count": len(tuple(segments)),
            "meaningful_segment_count": len(tuple(segments)),
            "clean_segment_count": len(tuple(results)),
            "dirty_segment_count": 0,
            "all_segments_clean": True,
            "total_ofi_emitted_count": 1,
            "total_warmup_none_count": 0,
            "total_sequence_gap_count": 0,
        },
    )

    result = script.preview_candidate_file(Path("/tmp/candidate.parquet.zst"), reason="snapshot_reset_candidate", max_events_per_file=10)

    assert seen_packet_types and all(packet_type is L2Packet for packet_type in seen_packet_types)
    assert result.timestamp_fallback_used is True
    assert result.packet_count == 2
    assert result.all_segments_clean is True


def test_snapshot_reset_and_source_gap_boundaries_are_classified_by_policy_module():
    snapshot_previous = L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=100,
        transaction_time=10,
        received_time=20,
        first_update_id=1,
        final_update_id=10,
        prev_final_update_id=9,
        bids=((100.0, 1.0),),
        asks=(),
    )
    snapshot_packet = L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=200,
        transaction_time=20,
        received_time=30,
        first_update_id=None,
        final_update_id=11,
        prev_final_update_id=None,
        bids=((101.0, 1.0),),
        asks=(),
    )
    source_gap_packet = L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=300,
        transaction_time=30,
        received_time=40,
        first_update_id=12,
        final_update_id=12,
        prev_final_update_id=99,
        bids=((102.0, 1.0),),
        asks=(),
    )
    ordered_snapshot_segments = segment_packets([snapshot_previous, snapshot_packet])
    ordered_gap_segments = segment_packets([snapshot_previous, source_gap_packet])

    assert len(ordered_snapshot_segments) == 2
    assert ordered_snapshot_segments[0].boundary_reason == "snapshot_or_reset"
    assert len(ordered_gap_segments) == 2
    assert ordered_gap_segments[0].boundary_reason == "source_sequence_gap"


def test_packet_sort_key_uses_transaction_time_before_received_time():
    packets = [
        L2Packet(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=300,
            transaction_time=None,
            received_time=1,
            first_update_id=1,
            final_update_id=30,
            prev_final_update_id=29,
            bids=(),
            asks=(),
        ),
        L2Packet(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=100,
            transaction_time=50,
            received_time=999,
            first_update_id=1,
            final_update_id=10,
            prev_final_update_id=9,
            bids=(),
            asks=(),
        ),
        L2Packet(
            symbol="BTCUSDT",
            event_type="depthUpdate",
            event_time=200,
            transaction_time=60,
            received_time=0,
            first_update_id=1,
            final_update_id=20,
            prev_final_update_id=19,
            bids=(),
            asks=(),
        ),
    ]
    ordered = sorted(packets, key=packet_sort_key)
    assert [packet.final_update_id for packet in ordered] == [10, 20, 30]


def test_transaction_time_fallback_is_reported_and_report_labels_stay_conservative():
    with_fallback = script.CandidateResult(
        file_path="/tmp/fallback.parquet.zst",
        candidate_reason="source_gap_timestamp_candidate",
        file_date="2025-07-01",
        file_hour="11",
        rows_scanned=2,
        packet_count=1,
        missing_transaction_time_count=1,
        missing_first_update_id_count=0,
        missing_prev_final_update_id_count=0,
        snapshot_like_packet_count=0,
        timestamp_fallback_used=True,
        timestamp_non_monotonic_hint_count=0,
        event_time_non_monotonic_hint_count=0,
        transaction_time_non_monotonic_hint_count=0,
        received_time_non_monotonic_hint_count=0,
        source_gap_boundary_count=1,
        snapshot_reset_boundary_count=0,
        segment_count=1,
        meaningful_segment_count=1,
        one_packet_segment_count=0,
        clean_segment_count=1,
        dirty_segment_count=0,
        all_segments_clean=True,
        total_ofi_emitted_count=1,
        total_warmup_none_count=0,
        total_sequence_gap_count=0,
        min_segment_packet_count=2,
        max_segment_packet_count=2,
        side_mapping_unknown_count=0,
        policy_module_used_directly=True,
    )
    without_fallback = _result(timestamp_fallback_used=False)

    observed_report = script.build_report(candidate_inputs=script.build_candidate_inputs(None), results=[with_fallback], max_events_per_file=10)
    not_observed_report = script.build_report(candidate_inputs=script.build_candidate_inputs(None), results=[without_fallback], max_events_per_file=10)

    assert "raw_missing_transaction_time_fallback_observed" in observed_report
    assert "raw_missing_transaction_time_fallback_not_observed" in not_observed_report
    assert "No raw missing transaction_time fallback candidates were found in this bounded validation window." in not_observed_report
    assert "Snapshot/reset-like raw candidates were observed, but they remained dirty in this bounded sample." in observed_report
    assert script.PRODUCTION_APPROVAL_STATEMENT in observed_report
    assert "segmented_reconstruction_still_bounded_only" in observed_report
