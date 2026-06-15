from __future__ import annotations

from pathlib import Path

import scripts.validate_l2_ofi_reconstruction_sample as sample
from scripts.dry_run_l2_ofi_reconstruction import PacketRecord


def _row(symbol: str, event_time: int, final_update_id: int, prev_final_update_id: int | None, side: str, price: str, quantity: str):
    return {
        "symbol": symbol,
        "event_time": event_time,
        "transaction_time": event_time,
        "received_time": event_time,
        "event_type": "update",
        "first_update_id": final_update_id - 1,
        "final_update_id": final_update_id,
        "prev_final_update_id": prev_final_update_id,
        "last_update_id": final_update_id,
        "side": side,
        "price": price,
        "quantity": quantity,
    }


def test_deterministic_file_selection_first_last_evenly_spaced(tmp_path):
    files = []
    for day in ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06", "2025-01-07", "2025-01-08"]:
        path = tmp_path / day / "00" / "BTCUSDT_orderbook.parquet.zst"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
        files.append(path)

    selected = sample.select_deterministic_files(sorted(files, key=lambda p: p.as_posix()), 6)
    assert selected[0] == files[0]
    assert selected[-1] == files[-1]
    assert len(selected) == 6


def test_row_order_grouping_differs_from_global_grouping_when_key_non_contiguous():
    rows = [
        sample._row_to_normalized_record(_row("BTCUSDT", 1, 10, 9, "bid", "100.0", "1.0"), symbol_filter="BTCUSDT"),
        sample._row_to_normalized_record(_row("BTCUSDT", 2, 11, 10, "ask", "101.0", "2.0"), symbol_filter="BTCUSDT"),
        sample._row_to_normalized_record(_row("BTCUSDT", 1, 10, 9, "ask", "101.5", "3.0"), symbol_filter="BTCUSDT"),
    ]
    rows = [r for r in rows if r is not None]
    row_order = sample.group_row_order_packets(rows)
    global_packets = sample.group_global_packets(rows)

    assert len(row_order) == 3
    assert len(global_packets) == 2
    assert sample.compare_grouping(rows)["packet_grouping_order_risk"] is True


def test_global_packet_grouping_combines_non_contiguous_rows_correctly():
    rows = [
        sample._row_to_normalized_record(_row("BTCUSDT", 1, 10, 9, "bid", "100.0", "1.0"), symbol_filter="BTCUSDT"),
        sample._row_to_normalized_record(_row("BTCUSDT", 2, 11, 10, "ask", "101.0", "2.0"), symbol_filter="BTCUSDT"),
        sample._row_to_normalized_record(_row("BTCUSDT", 1, 10, 9, "ask", "101.5", "3.0"), symbol_filter="BTCUSDT"),
    ]
    rows = [r for r in rows if r is not None]
    packets = sample.group_global_packets(rows)
    assert len(packets) == 2
    assert packets[0].bids == [(100.0, 1.0)]
    assert packets[0].asks == [(101.5, 3.0)]


def test_last_packet_boundary_risk_detection_when_next_row_has_same_key():
    last_key = ("BTCUSDT", 1, 10, 9, "update")
    next_key = ("BTCUSDT", 1, 10, 9, "update")
    assert sample.packet_boundary_risk(last_key, next_key) is True
    assert sample.packet_boundary_risk(last_key, ("BTCUSDT", 2, 11, 10, "update")) is False


def test_dropped_last_packet_for_boundary_safety(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "\n".join(
            [
                "symbol,event_time,transaction_time,received_time,event_type,first_update_id,final_update_id,prev_final_update_id,last_update_id,side,price,quantity",
                "BTCUSDT,1,1,1,update,9,10,8,10,bid,100.0,1.0",
                "BTCUSDT,1,1,1,update,9,10,8,10,ask,101.0,2.0",
                "BTCUSDT,2,2,2,update,10,11,10,11,bid,100.5,1.5",
            ]
        )
    )

    result = sample.scan_file_rows(csv_path, symbol="BTCUSDT", max_events_per_file=10)
    assert result["dropped_last_packet_for_boundary_safety"] == 1
    assert result["packet_boundary_unknown"] is True


def test_aggregate_stats_count_files_with_resync_and_gaps_correctly():
    aggregate = sample.summarize_results(
        [
            {"rows_scanned": 10, "processed_event_count": 2, "ofi_emitted_count": 1, "packet_grouping_order_risk": False, "resync_stop_event_index": None, "snapshot_or_reset_event_count": 0, "bad_cast_row_count": 0, "unknown_side_row_count": 0},
            {"rows_scanned": 20, "processed_event_count": 3, "ofi_emitted_count": 2, "packet_grouping_order_risk": True, "resync_stop_event_index": 4, "snapshot_or_reset_event_count": 1, "bad_cast_row_count": 1, "unknown_side_row_count": 0},
        ]
    )
    assert aggregate["selected_file_count"] == 2
    assert aggregate["files_with_resync_stop"] == 1
    assert aggregate["files_with_packet_grouping_order_risk"] == 1
    assert aggregate["files_with_snapshot_reset"] == 1
    assert aggregate["files_with_bad_casts"] == 1


def test_report_includes_no_production_statement():
    report = sample.render_report(
        file_results=[
            {
                "file_path": "/tmp/a.parquet.zst",
                "file_date": "2025-01-01",
                "rows_scanned": 1,
                "row_order_packet_count": 1,
                "global_packet_count": 1,
                "packet_grouping_order_risk": False,
                "row_order_duplicate_packet_key_count": 0,
                "global_duplicate_packet_key_count": 0,
                "duplicate_packet_key_count": 0,
                "dropped_last_packet_for_boundary_safety": 0,
                "packet_boundary_unknown": False,
                "processed_event_count": 1,
                "ofi_emitted_count": 1,
                "warmup_none_count": 0,
                "snapshot_or_reset_event_count": 0,
                "sequence_gap_count": 0,
                "resync_stop_event_index": None,
                "bad_cast_row_count": 0,
                "unknown_side_row_count": 0,
                "bid_update_count": 1,
                "ask_update_count": 1,
                "ofi_positive_count": 1,
                "ofi_negative_count": 0,
                "ofi_zero_count": 0,
                "ofi_mean": 1.0,
                "ofi_min": 1.0,
                "ofi_max": 1.0,
                "ofi_abs_sum": 1.0,
                "event_time_min": 1,
                "event_time_max": 1,
                "final_update_id_min": 10,
                "final_update_id_max": 10,
                "first_packet_key": ("BTCUSDT", 1, 10, 9, "update"),
                "last_packet_key": ("BTCUSDT", 1, 10, 9, "update"),
                "cross_file_continuity_status": "cross_file_unknown",
                "join_summary": {
                    "bar_file_found": False,
                    "bar_row_count": None,
                    "join_attempted": False,
                    "joined_row_count": None,
                    "bar_count_preserved": None,
                    "join_deferred_reason": "bar_file_missing",
                    "join_helper_importable": True,
                    "join_helper_callable": True,
                },
                "global_packets": [PacketRecord(
                    key=("BTCUSDT", 1, 10, 9, "update"),
                    symbol="BTCUSDT",
                    event_time=1,
                    transaction_time=1,
                    received_time=1,
                    event_type="update",
                    first_update_id=9,
                    final_update_id=10,
                    prev_final_update_id=8,
                    last_update_id=10,
                    bids=[(100.0, 1.0)],
                    asks=[(101.0, 1.0)],
                )],
                "row_order_packets": [PacketRecord(
                    key=("BTCUSDT", 1, 10, 9, "update"),
                    symbol="BTCUSDT",
                    event_time=1,
                    transaction_time=1,
                    received_time=1,
                    event_type="update",
                    first_update_id=9,
                    final_update_id=10,
                    prev_final_update_id=8,
                    last_update_id=10,
                    bids=[(100.0, 1.0)],
                    asks=[(101.0, 1.0)],
                )],
                "strict_sequence": True,
            }
        ],
        aggregate={"selected_file_count": 1, "total_rows_scanned": 1, "total_processed_event_count": 1, "total_ofi_emitted_count": 1, "files_with_packet_grouping_order_risk": 0, "files_with_resync_stop": 0, "files_with_snapshot_reset": 0, "files_with_bad_casts": 0, "files_with_unknown_sides": 0},
        continuity_rows=[{"left_file": "a", "right_file": "b", "continuity_status": "cross_file_unknown"}],
        join_rows=[{"file_date": "2025-01-01", "bar_file_found": False, "bar_row_count": None, "join_attempted": False, "joined_row_count": None, "bar_count_preserved": None, "join_deferred_reason": "bar_file_missing"}],
        explicit_answers=[("Is OFI approved for alpha, paper, or live use?", "No.")],
        decision_labels=["alpha_blocked", "paper_live_blocked"],
        selected_files=[Path("/tmp/a.parquet.zst")],
        file_selection_note="note",
        l2_root=Path("/tmp/l2"),
        bar_dir=Path("/tmp/bars"),
        max_events_per_file=2000,
    )
    assert sample.PRODUCTION_APPROVAL_STATEMENT in report
