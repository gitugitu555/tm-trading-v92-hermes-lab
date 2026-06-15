from __future__ import annotations

from pathlib import Path

import scripts.diagnose_l2_ofi_resync_root_cause as diag


def _row(
    *,
    symbol: str,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    side: str,
    price: str,
    quantity: str,
    transaction_time: int | None = None,
    received_time: int | None = None,
    event_type: str = "update",
    first_update_id: int | None = None,
    last_update_id: int | None = None,
):
    return {
        "symbol": symbol,
        "event_time": event_time,
        "transaction_time": transaction_time if transaction_time is not None else event_time,
        "received_time": received_time if received_time is not None else event_time,
        "event_type": event_type,
        "first_update_id": first_update_id if first_update_id is not None else final_update_id - 1,
        "final_update_id": final_update_id,
        "prev_final_update_id": prev_final_update_id,
        "last_update_id": last_update_id if last_update_id is not None else final_update_id,
        "side_group": side,
        "price": price,
        "quantity": quantity,
    }


def _packet_rows(key_final: int, prev_final: int | None, event_time: int, *, event_type: str = "update", snapshot: bool = False):
    if snapshot:
        first_update_id = None
        prev_update_id = None
        event_type = "snapshot"
    else:
        first_update_id = key_final - 1
        prev_update_id = prev_final
    return [
        _row(
            symbol="BTCUSDT",
            event_time=event_time,
            final_update_id=key_final,
            prev_final_update_id=prev_update_id,
            side="bid",
            price="100.0",
            quantity="1.0",
            event_type=event_type,
            first_update_id=first_update_id,
        ),
        _row(
            symbol="BTCUSDT",
            event_time=event_time,
            final_update_id=key_final,
            prev_final_update_id=prev_update_id,
            side="ask",
            price="101.0",
            quantity="2.0",
            event_type=event_type,
            first_update_id=first_update_id,
        ),
    ]


def test_sequence_table_marks_matching_prev_final_update_id_correctly():
    rows = _packet_rows(10, 8, 1) + _packet_rows(11, 10, 2)
    table = diag.build_packet_table(rows)
    packets = table["annotated_global_packets"]

    assert len(packets) == 2
    assert packets[1].matches_previous_final_update_id is True
    assert packets[1].sequence_gap_size == 0
    assert packets[1].expected_prev_final_update_id == 10


def test_source_sequence_gap_classification_when_prev_skips_previous_final():
    previous = diag.PacketSummary(
        packet_index=1,
        key=("BTCUSDT", 1, 10, 8, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=1,
        transaction_time_min=1,
        transaction_time_max=1,
        received_time_min=1,
        received_time_max=1,
        first_update_id=9,
        final_update_id=10,
        prev_final_update_id=8,
        last_update_id=10,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        matches_previous_final_update_id=True,
        rows=_packet_rows(10, 8, 1),
    )
    current = diag.PacketSummary(
        packet_index=2,
        key=("BTCUSDT", 2, 12, 7, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=2,
        transaction_time_min=2,
        transaction_time_max=2,
        received_time_min=2,
        received_time_max=2,
        first_update_id=11,
        final_update_id=12,
        prev_final_update_id=7,
        last_update_id=12,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        rows=_packet_rows(12, 7, 2),
    )
    strict_result = {"resync_packet_index": 2}
    ordering_results = [
        {"ordering_name": "event_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "transaction_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "received_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
    ]

    label, _ = diag.classify_root_cause(strict_result=strict_result, ordering_results=ordering_results, annotated_packets=[previous, current])
    assert label == "source_sequence_gap"


def test_snapshot_reset_not_handled_classification_when_null_prev_fields_appear():
    previous = diag.PacketSummary(
        packet_index=1,
        key=("BTCUSDT", 1, 10, 8, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=1,
        transaction_time_min=1,
        transaction_time_max=1,
        received_time_min=1,
        received_time_max=1,
        first_update_id=9,
        final_update_id=10,
        prev_final_update_id=8,
        last_update_id=10,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        rows=_packet_rows(10, 8, 1),
    )
    current = diag.PacketSummary(
        packet_index=2,
        key=("BTCUSDT", 2, 11, None, "snapshot"),
        symbol="BTCUSDT",
        event_type="snapshot",
        event_time=2,
        transaction_time_min=None,
        transaction_time_max=None,
        received_time_min=2,
        received_time_max=2,
        first_update_id=None,
        final_update_id=11,
        prev_final_update_id=None,
        last_update_id=11,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=True,
        has_null_prev_final_update_id=True,
        is_snapshot_or_reset=True,
        rows=_packet_rows(11, None, 2, snapshot=True),
    )
    strict_result = {"resync_packet_index": 2}
    ordering_results = [
        {"ordering_name": "event_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "transaction_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "received_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
    ]

    label, _ = diag.classify_root_cause(strict_result=strict_result, ordering_results=ordering_results, annotated_packets=[previous, current])
    assert label == "snapshot_reset_not_handled"


def test_event_ordering_issue_classification_when_transaction_order_removes_gap():
    previous = diag.PacketSummary(
        packet_index=1,
        key=("BTCUSDT", 1, 10, 8, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=1,
        transaction_time_min=1,
        transaction_time_max=1,
        received_time_min=1,
        received_time_max=1,
        first_update_id=9,
        final_update_id=10,
        prev_final_update_id=8,
        last_update_id=10,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        rows=_packet_rows(10, 8, 1),
    )
    current = diag.PacketSummary(
        packet_index=2,
        key=("BTCUSDT", 2, 12, 7, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=2,
        transaction_time_min=2,
        transaction_time_max=2,
        received_time_min=2,
        received_time_max=2,
        first_update_id=11,
        final_update_id=12,
        prev_final_update_id=7,
        last_update_id=12,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        rows=_packet_rows(12, 7, 2),
    )
    strict_result = {"resync_packet_index": 2}
    ordering_results = [
        {"ordering_name": "event_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "transaction_time_final_update_id", "sequence_gap_count": 0, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 1, "first_gap_index": None, "would_resync_be_avoided": True},
        {"ordering_name": "received_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
    ]

    label, _ = diag.classify_root_cause(strict_result=strict_result, ordering_results=ordering_results, annotated_packets=[previous, current])
    assert label == "event_ordering_issue"


def test_duplicate_or_overlap_update_id_classification():
    packet = diag.PacketSummary(
        packet_index=2,
        key=("BTCUSDT", 2, 10, 8, "update"),
        symbol="BTCUSDT",
        event_type="update",
        event_time=2,
        transaction_time_min=2,
        transaction_time_max=2,
        received_time_min=2,
        received_time_max=2,
        first_update_id=9,
        final_update_id=10,
        prev_final_update_id=8,
        last_update_id=10,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=False,
        has_null_prev_final_update_id=False,
        is_snapshot_or_reset=False,
        duplicate_final_update_id=True,
        rows=_packet_rows(10, 8, 2),
    )
    strict_result = {"resync_packet_index": 2}
    ordering_results = [
        {"ordering_name": "event_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 1, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 1, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "transaction_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 1, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
        {"ordering_name": "received_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 1, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
    ]

    label, _ = diag.classify_root_cause(strict_result=strict_result, ordering_results=ordering_results, annotated_packets=[packet])
    assert label == "duplicate_or_overlap_update_id"


def test_alternate_ordering_experiment_reports_first_gap_index():
    rows = _packet_rows(10, 8, 1) + _packet_rows(12, 7, 2) + _packet_rows(13, 12, 3)
    table = diag.build_packet_table(rows)
    result = diag.evaluate_ordering_experiment(table["global_packets"], "event_time_final_update_id", strict_sequence=True)
    assert result["first_gap_index"] == 2
    assert result["sequence_gap_count"] == 1


def test_report_includes_no_production_statement():
    report = diag.render_report(
        {
            "input_file": "/tmp/sample.parquet.zst",
            "expected_resync_index": 2,
            "context_events_before": 20,
            "context_events_after": 20,
            "max_events": 3000,
            "strict_sequence": True,
            "symbol": "BTCUSDT",
            "executive_finding": "finding",
            "reproduction_summary": {
                "source_file_read_complete": True,
                "read_mode": "bounded_batch_scan",
                "rows_scanned": 2,
                "packets_built": 2,
                "processed_event_count": 2,
                "ofi_emitted_count": 1,
                "warmup_none_count": 1,
                "sequence_gap_count": 1,
                "snapshot_or_reset_event_count": 1,
                "resync_packet_index": 2,
                "expected_resync_index": 2,
                "resync_index_matches_expectation": True,
            },
            "packet_schema_summary": {"rows_scanned": 2},
            "resync_event_summary": {"resync_packet_index": 2},
            "context_window": [
                {
                    "packet_index": 1,
                    "event_time": 1,
                    "first_update_id": 9,
                    "final_update_id": 10,
                    "prev_final_update_id": 8,
                    "expected_prev_final_update_id": None,
                    "matches_previous_final_update_id": True,
                    "sequence_gap_size": 0,
                    "is_snapshot_or_reset": False,
                    "bid_level_count": 1,
                    "ask_level_count": 1,
                    "event_type": "update",
                }
            ],
            "source_sequence_gap_analysis": "analysis",
            "ordering_results": [
                {"ordering_name": "event_time_final_update_id", "sequence_gap_count": 1, "duplicate_final_update_id_count": 0, "non_monotonic_event_time_count": 0, "first_gap_index": 2, "would_resync_be_avoided": False},
            ],
            "root_cause_label": "event_ordering_issue",
            "root_cause_reason": "reason",
            "what_worked": ["a"],
            "what_failed": ["b"],
            "what_is_safe": ["c"],
            "what_is_not_safe": ["d"],
            "decision_labels": ["resync_reproduced", "event_ordering_issue"],
            "broader_reconstruction_approval": "No.",
            "alpha_approval": "No.",
            "paper_live_approval": "No.",
            "required_next_step": "next",
        }
    )
    assert diag.PRODUCTION_APPROVAL_STATEMENT in report
