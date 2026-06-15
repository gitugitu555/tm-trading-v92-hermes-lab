from __future__ import annotations

from pathlib import Path

import pytest

from scripts.diagnose_l2_ofi_dirty_transaction_time_file import (
    PacketSummary,
    annotate_chain,
    classify_root_cause,
    evaluate_segmentability,
    render_report,
    sort_packets,
)


def _packet(
    final_update_id: int,
    *,
    prev_final_update_id: int | None,
    first_update_id: int | None = None,
    event_time: int,
    transaction_time_min: int | None = None,
    received_time_min: int | None = None,
    event_type: str = "depthUpdate",
    side_counts: tuple[int, int] = (1, 1),
) -> PacketSummary:
    bid_count, ask_count = side_counts
    return PacketSummary(
        key=("BTCUSDT", event_time, final_update_id, prev_final_update_id, event_type),
        symbol="BTCUSDT",
        event_type=event_type,
        event_time=event_time,
        transaction_time_min=transaction_time_min,
        transaction_time_max=transaction_time_min,
        received_time_min=received_time_min,
        received_time_max=received_time_min,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        last_update_id=final_update_id,
        bid_level_count=bid_count,
        ask_level_count=ask_count,
        total_level_count=bid_count + ask_count,
        has_null_first_update_id=first_update_id is None,
        has_null_prev_final_update_id=prev_final_update_id is None,
        is_snapshot_or_reset=first_update_id is None or prev_final_update_id is None,
        raw_row_count=2,
        rows=[
            {
                "side_group": "bid",
                "price": 100.0,
                "quantity": 1.0,
            },
            {
                "side_group": "ask",
                "price": 101.0,
                "quantity": 1.0,
            },
        ],
    )


def _ordering(sequence_gap_count: int, name: str = "transaction_time_final_update_id") -> dict[str, object]:
    return {
        "ordering_name": name,
        "sequence_gap_count": sequence_gap_count,
    }


def test_source_sequence_gap_classification_when_all_orderings_mismatch():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=12, first_update_id=12, event_time=2, transaction_time_min=2),
        ]
    )
    root, _ = classify_root_cause(
        tx_ordering=_ordering(1),
        all_orderings={
            "transaction_time_final_update_id": _ordering(1),
            "event_time_final_update_id": _ordering(1),
            "final_update_id": _ordering(1),
            "received_time_final_update_id": _ordering(1),
        },
        annotated_packets=packets,
        row_order_packets=packets,
        resync_index=2,
    )
    assert root == "source_sequence_gap"


def test_event_ordering_issue_remaining_when_alternate_ordering_avoids_gap():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=11, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=20, first_update_id=21, event_time=3, transaction_time_min=3),
            _packet(40, prev_final_update_id=30, first_update_id=31, event_time=4, transaction_time_min=4),
        ]
    )
    root, _ = classify_root_cause(
        tx_ordering=_ordering(1),
        all_orderings={
            "transaction_time_final_update_id": _ordering(1),
            "event_time_final_update_id": _ordering(0, "event_time_final_update_id"),
            "final_update_id": _ordering(1),
            "received_time_final_update_id": _ordering(1),
        },
        annotated_packets=packets,
        row_order_packets=packets,
        resync_index=1,
    )
    assert root == "event_ordering_issue_remaining"


def test_duplicate_or_overlap_update_id_classification():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=9, event_time=2, transaction_time_min=2),
        ]
    )
    root, _ = classify_root_cause(
        tx_ordering=_ordering(1),
        all_orderings={
            "transaction_time_final_update_id": _ordering(1),
            "event_time_final_update_id": _ordering(1),
            "final_update_id": _ordering(1),
            "received_time_final_update_id": _ordering(1),
        },
        annotated_packets=annotate_chain(packets),
        row_order_packets=packets,
        resync_index=2,
    )
    assert root == "duplicate_or_overlap_update_id"


def test_packet_boundary_truncation_possible_near_sample_end():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=11, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=20, first_update_id=21, event_time=3, transaction_time_min=3),
            _packet(40, prev_final_update_id=30, first_update_id=31, event_time=4, transaction_time_min=4),
        ]
    )
    root, _ = classify_root_cause(
        tx_ordering=_ordering(1),
        all_orderings={
            "transaction_time_final_update_id": _ordering(1),
            "event_time_final_update_id": _ordering(1),
            "final_update_id": _ordering(1),
            "received_time_final_update_id": _ordering(1),
        },
        annotated_packets=packets,
        row_order_packets=packets,
        resync_index=4,
    )
    assert root == "packet_boundary_truncation_possible"


def test_segmentability_returns_two_clean_segments_for_one_gap(monkeypatch: pytest.MonkeyPatch):
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=20, first_update_id=20, event_time=3, transaction_time_min=3),
            _packet(40, prev_final_update_id=99, first_update_id=40, event_time=4, transaction_time_min=4),
            _packet(50, prev_final_update_id=40, first_update_id=40, event_time=5, transaction_time_min=5),
        ]
    )

    def fake_rehearsal(segment_packets, strict_sequence=True):
        return {
            "ofi_emitted_count": len(segment_packets),
            "sequence_gap_count": 0,
            "engine_completed_sample": True,
        }

    monkeypatch.setattr("scripts.diagnose_l2_ofi_dirty_transaction_time_file._ofi_rehearsal", fake_rehearsal)
    result = evaluate_segmentability(packets, 4)
    assert result["segment_before_clean"] is True
    assert result["segment_after_clean"] is True
    assert result["segmented_reconstruction_possible"] is True


def test_segmentability_fails_if_second_segment_has_gap(monkeypatch: pytest.MonkeyPatch):
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=20, first_update_id=20, event_time=3, transaction_time_min=3),
            _packet(40, prev_final_update_id=99, first_update_id=40, event_time=4, transaction_time_min=4),
            _packet(50, prev_final_update_id=40, first_update_id=40, event_time=5, transaction_time_min=5),
        ]
    )

    def fake_rehearsal(segment_packets, strict_sequence=True):
        if segment_packets and segment_packets[0].final_update_id == 40:
            return {
                "ofi_emitted_count": len(segment_packets),
                "sequence_gap_count": 1,
                "engine_completed_sample": False,
            }
        return {
            "ofi_emitted_count": len(segment_packets),
            "sequence_gap_count": 0,
            "engine_completed_sample": True,
        }

    monkeypatch.setattr("scripts.diagnose_l2_ofi_dirty_transaction_time_file._ofi_rehearsal", fake_rehearsal)
    result = evaluate_segmentability(packets, 4)
    assert result["segment_before_clean"] is True
    assert result["segment_after_clean"] is False
    assert result["segmented_reconstruction_possible"] is False


def test_report_includes_no_production_statement():
    report = render_report(
        {
            "input_file": Path("/tmp/sample.parquet.zst"),
            "expected_resync_index": 2,
            "context_events_before": 30,
            "context_events_after": 30,
            "max_events": 7000,
            "symbol": "BTCUSDT",
            "executive_finding": "x",
            "reproduction_summary": {"a": 1},
            "packet_schema_summary": {"b": 2},
            "resync_summary": {"c": 3},
            "context_window": [],
            "ordering_rows": [],
            "root_cause_label": "source_sequence_gap",
            "root_cause_reason": "r",
            "segmentability": {"s": 1},
            "what_worked": [],
            "what_failed": [],
            "what_is_safe": [],
            "what_is_not_safe": [],
            "decision_labels": [],
            "broader_reconstruction_approval": "No.",
            "alpha_approval": "No.",
            "paper_live_approval": "No.",
            "required_next_step": "next",
        }
    )
    assert "This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use." in report
