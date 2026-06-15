from __future__ import annotations

from pathlib import Path

import scripts.validate_l2_ofi_transaction_time_ordering as txord


def _packet(
    *,
    event_time: int,
    tx_time: int | None,
    final_update_id: int,
    prev_final_update_id: int | None,
    snapshot: bool = False,
):
    rows = [
        {
            "symbol": "BTCUSDT",
            "event_time": event_time,
            "transaction_time": tx_time,
            "received_time": event_time + 100,
            "event_type": "snapshot" if snapshot else "update",
            "first_update_id": None if snapshot else final_update_id - 1,
            "final_update_id": final_update_id,
            "prev_final_update_id": None if snapshot else prev_final_update_id,
            "last_update_id": final_update_id,
            "side_group": "bid",
            "price": 100.0,
            "quantity": 1.0,
        },
        {
            "symbol": "BTCUSDT",
            "event_time": event_time,
            "transaction_time": tx_time,
            "received_time": event_time + 101,
            "event_type": "snapshot" if snapshot else "update",
            "first_update_id": None if snapshot else final_update_id - 1,
            "final_update_id": final_update_id,
            "prev_final_update_id": None if snapshot else prev_final_update_id,
            "last_update_id": final_update_id,
            "side_group": "ask",
            "price": 101.0,
            "quantity": 2.0,
        },
    ]
    return txord._build_packet_summary(( "BTCUSDT", event_time, final_update_id, None if snapshot else prev_final_update_id, "snapshot" if snapshot else "update"), rows)


def test_deterministic_file_selection_always_includes_known_failing_file(tmp_path, monkeypatch):
    known = tmp_path / "2025-06-28" / "05" / "BTCUSDT_orderbook.parquet.zst"
    known.parent.mkdir(parents=True, exist_ok=True)
    known.write_text("x")
    monkeypatch.setattr(txord, "KNOWN_FAILING_FILE", known)

    extra = []
    for idx in range(4):
        path = tmp_path / f"2025-06-2{idx}" / "00" / "BTCUSDT_orderbook.parquet.zst"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
        extra.append(path)

    selected = txord.select_deterministic_files(tmp_path, "BTCUSDT", max_files=3)
    assert known in selected


def test_transaction_time_ordering_removes_gap_that_event_time_creates():
    packets = [
        _packet(event_time=1, tx_time=2, final_update_id=10, prev_final_update_id=20, snapshot=False),
        _packet(event_time=2, tx_time=1, final_update_id=20, prev_final_update_id=None, snapshot=True),
        _packet(event_time=3, tx_time=3, final_update_id=21, prev_final_update_id=10, snapshot=False),
    ]
    event_result = txord.classify_ordering(packets, "event_time_final_update_id")
    tx_result = txord.classify_ordering(packets, "transaction_time_final_update_id")
    assert event_result["reset_aware_sequence_gap_count"] == 1
    assert tx_result["reset_aware_sequence_gap_count"] == 0
    assert tx_result["first_gap_index"] is None


def test_snapshot_reset_packets_reset_chain_and_are_not_counted_as_source_gaps():
    packets = [
        _packet(event_time=1, tx_time=1, final_update_id=10, prev_final_update_id=8, snapshot=False),
        _packet(event_time=2, tx_time=2, final_update_id=20, prev_final_update_id=None, snapshot=True),
        _packet(event_time=3, tx_time=3, final_update_id=21, prev_final_update_id=20, snapshot=False),
    ]
    result = txord.classify_ordering(packets, "transaction_time_final_update_id")
    assert result["snapshot_reset_count"] == 1
    assert result["reset_aware_sequence_gap_count"] == 0


def test_both_clean_classification():
    packets = [
        _packet(event_time=1, tx_time=1, final_update_id=10, prev_final_update_id=8, snapshot=False),
        _packet(event_time=2, tx_time=2, final_update_id=11, prev_final_update_id=10, snapshot=False),
    ]
    event_result = txord.classify_ordering(packets, "event_time_final_update_id")
    tx_result = txord.classify_ordering(packets, "transaction_time_final_update_id")
    assert event_result["reset_aware_sequence_gap_count"] == 0
    assert tx_result["reset_aware_sequence_gap_count"] == 0


def test_both_dirty_classification():
    packets = [
        _packet(event_time=1, tx_time=1, final_update_id=10, prev_final_update_id=8, snapshot=False),
        _packet(event_time=2, tx_time=2, final_update_id=12, prev_final_update_id=99, snapshot=False),
    ]
    event_result = txord.classify_ordering(packets, "event_time_final_update_id")
    tx_result = txord.classify_ordering(packets, "transaction_time_final_update_id")
    assert event_result["reset_aware_sequence_gap_count"] > 0
    assert tx_result["reset_aware_sequence_gap_count"] > 0


def test_transaction_time_better_classification():
    packets = [
        _packet(event_time=1, tx_time=2, final_update_id=10, prev_final_update_id=20, snapshot=False),
        _packet(event_time=2, tx_time=1, final_update_id=20, prev_final_update_id=None, snapshot=True),
        _packet(event_time=3, tx_time=3, final_update_id=21, prev_final_update_id=10, snapshot=False),
    ]
    event_result = txord.classify_ordering(packets, "event_time_final_update_id")
    tx_result = txord.classify_ordering(packets, "transaction_time_final_update_id")
    assert tx_result["reset_aware_sequence_gap_count"] < event_result["reset_aware_sequence_gap_count"]


def test_report_includes_no_production_no_alpha_statement():
    report = txord.render_report(
        {
            "l2_root": "/tmp",
            "max_files": 1,
            "max_events_per_file": 1,
            "symbol": "BTCUSDT",
            "executive_finding": "finding",
            "file_selection": [{"selected_index": 1, "file_path": "/tmp/a.parquet.zst", "priority_note": "known_failing_file", "file_date": "2025-06-28"}],
            "ordering_summary": {"selected_file_count": 1},
            "per_file_rows": [{"file_path": "/tmp/a.parquet.zst", "ordering_classification": "transaction_time_better"}],
            "snapshot_reset_handling": "snapshot reset",
            "tx_rehearsal_rows": [{"file_path": "/tmp/a.parquet.zst", "processed_event_count": 1, "ofi_emitted_count": 1, "warmup_none_count": 0, "snapshot_or_reset_event_count": 0, "sequence_gap_count": 0, "resync_stop_event_index": None, "engine_completed_sample": True}],
            "known_failing_file_recheck": "recheck",
            "what_worked": ["a"],
            "what_failed": ["b"],
            "what_is_safe": ["c"],
            "what_is_not_safe": ["d"],
            "decision_labels": ["known_failing_file_rechecked"],
            "transaction_time_globally_approved": "Not globally approved yet; only validated for this bounded sample.",
            "alpha_approval": "No.",
            "paper_live_approval": "No.",
            "required_next_step": "next",
        }
    )
    assert txord.PRODUCTION_APPROVAL_STATEMENT in report
