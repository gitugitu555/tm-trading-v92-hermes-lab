from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.diagnose_l2_ofi_snapshot_reset_dirty_cases as script
from features.l2_ofi_segmented_reconstruction import L2Packet, L2Segment, SegmentRunResult, is_snapshot_or_reset, segment_packets


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


def _packet(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    first_update_id: int | None,
    transaction_time: int | None = 10,
    bids=((100.0, 1.0),),
    asks=(),
) -> L2Packet:
    return L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=event_time,
        transaction_time=transaction_time,
        received_time=20,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        bids=bids,
        asks=asks,
    )


def _result(**overrides) -> script.SnapshotDirtyCaseResult:
    base = dict(
        file_path="/tmp/candidate.parquet.zst",
        file_date="2026-05-26",
        file_hour="00",
        rows_scanned=2,
        packet_count=2,
        snapshot_like_packet_count=1,
        snapshot_like_packet_indexes=(1,),
        first_packet_is_snapshot_reset=True,
        segment_count=1,
        snapshot_reset_boundary_count=0,
        source_gap_boundary_count=0,
        dirty_segment_count=1,
        clean_segment_count=0,
        all_segments_clean=False,
        total_ofi_emitted_count=0,
        total_warmup_none_count=1,
        total_sequence_gap_count=1,
        dirty_segment_ids=(1,),
        dirty_segment_contains_snapshot_reset=True,
        snapshot_packet_position_in_dirty_segment=1,
        dirty_segment_first_packet_is_snapshot_reset=True,
        next_packet_after_snapshot_prev_final_update_id=999,
        snapshot_packet_final_update_id=1000,
        next_packet_chains_to_snapshot=False,
        hypothesis_a_first_packet_snapshot_supported=True,
        hypothesis_b_next_packet_chain_failure_supported=True,
        hypothesis_c_seed_insufficient_supported=False,
        root_cause_classification="post_snapshot_chain_failure",
        policy_module_used_directly=True,
        side_mapping_unknown_count=0,
        snapshot_context_windows=(),
        dirty_segment_details=(),
    )
    base.update(overrides)
    return script.SnapshotDirtyCaseResult(**base)


def test_snapshot_reset_packet_detection_from_synthetic_rows():
    frame = pd.DataFrame(
        [
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=None),
            _row(event_time=2, final_update_id=11, prev_final_update_id=10, first_update_id=1),
        ]
    )
    packets, counters = script._packets_from_frame(frame)
    assert counters["rows_scanned"] == 2
    assert len(packets) == 2
    assert any(is_snapshot_or_reset(packet) for packet in packets)


def test_first_packet_snapshot_reset_hypothesis_classification():
    classification = script._classify_root_cause(
        first_packet_is_snapshot_reset=True,
        dirty_segment_contains_snapshot_reset=False,
        next_packet_chains_to_snapshot=None,
        dirty_segment_count=1,
    )
    assert classification[3] == "first_packet_snapshot_reset"


def test_post_snapshot_chain_failure_hypothesis_classification():
    classification = script._classify_root_cause(
        first_packet_is_snapshot_reset=False,
        dirty_segment_contains_snapshot_reset=True,
        next_packet_chains_to_snapshot=False,
        dirty_segment_count=1,
    )
    assert classification[3] == "post_snapshot_chain_failure"


def test_snapshot_seed_insufficient_hypothesis_classification():
    classification = script._classify_root_cause(
        first_packet_is_snapshot_reset=False,
        dirty_segment_contains_snapshot_reset=True,
        next_packet_chains_to_snapshot=True,
        dirty_segment_count=1,
    )
    assert classification[3] == "snapshot_seed_insufficient"


def test_diagnostic_uses_policy_segment_packets_directly(monkeypatch):
    frame = pd.DataFrame(
        [
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=None),
            _row(event_time=2, final_update_id=11, prev_final_update_id=10, first_update_id=1),
        ]
    )
    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: frame)

    calls: list[int] = []

    def fake_segment_packets(packets):
        packets = tuple(packets)
        calls.append(len(packets))
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
            ofi_emitted_count=0,
            warmup_none_count=1,
            sequence_gap_count=1,
            clean=False,
        ),
    )
    monkeypatch.setattr(
        script,
        "summarize_segments",
        lambda segments, results: {
            "segment_count": len(tuple(segments)),
            "meaningful_segment_count": len(tuple(segments)),
            "clean_segment_count": 0,
            "dirty_segment_count": 1,
            "all_segments_clean": False,
            "total_ofi_emitted_count": 0,
            "total_warmup_none_count": 1,
            "total_sequence_gap_count": 1,
        },
    )

    result = script.preview_candidate_file(
        Path("/tmp/candidate.parquet.zst"),
        reason="dirty_snapshot_reset_candidate",
        max_events_per_file=10,
        context_packets_around_snapshot=1,
    )

    assert calls == [2]
    assert result.policy_module_used_directly is True
    assert result.root_cause_classification == "snapshot_seed_insufficient"
    assert result.dirty_segment_contains_snapshot_reset is True


def test_report_includes_no_production_statement_and_no_behavior_change_claim():
    result = _result()
    report = script.build_report(
        candidate_inputs=script.build_candidate_inputs(None),
        results=[result],
        max_events_per_file=10,
        context_packets_around_snapshot=3,
    )
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
    assert "No policy or OFIEngine behavior was changed." in report
    assert "full_reconstruction_not_approved" in report
    assert "segmented_reconstruction_still_bounded_only" in report


def test_build_candidate_inputs_is_deterministic():
    candidates = script.build_candidate_inputs(None)
    assert len(candidates) == 2
    assert all(candidate.reason == "dirty_snapshot_reset_candidate" for candidate in candidates)
