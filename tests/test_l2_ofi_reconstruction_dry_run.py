from __future__ import annotations

import pandas as pd

import scripts.dry_run_l2_ofi_reconstruction as dry_run
from scripts.dry_run_l2_ofi_reconstruction import PacketAssembler, PacketRecord


def test_price_and_quantity_string_casting():
    record = dry_run._row_to_normalized_record(
        {
            "symbol": "BTCUSDT",
            "event_time": "1751086799938",
            "transaction_time": "1751086799938",
            "received_time": "1751086799937",
            "event_type": "update",
            "first_update_id": "10",
            "final_update_id": "11",
            "prev_final_update_id": "9",
            "last_update_id": "11",
            "side": "bid",
            "price": "100.5",
            "quantity": "2.25",
        },
        symbol_filter="BTCUSDT",
    )

    assert record is not None
    assert record["price"] == 100.5
    assert record["quantity"] == 2.25
    assert record["final_update_id"] == 11
    assert record["event_time"] == 1751086799938


def test_event_grouping_combines_multiple_rows_into_one_packet():
    assembler = PacketAssembler(symbol_filter="BTCUSDT")
    row1 = {
        "symbol": "BTCUSDT",
        "event_time": 1,
        "transaction_time": 1,
        "received_time": 1,
        "event_type": "update",
        "first_update_id": 10,
        "final_update_id": 11,
        "prev_final_update_id": 9,
        "last_update_id": 11,
        "side": "bid",
        "price": "100.0",
        "quantity": "1.0",
    }
    row2 = {
        "symbol": "BTCUSDT",
        "event_time": 1,
        "transaction_time": 1,
        "received_time": 2,
        "event_type": "update",
        "first_update_id": 10,
        "final_update_id": 11,
        "prev_final_update_id": 9,
        "last_update_id": 11,
        "side": "ask",
        "price": "101.0",
        "quantity": "2.0",
    }

    assert assembler.consume_row(row1) == []
    assert assembler.consume_row(row2) == []
    packet = assembler.finish()
    assert packet is not None
    assert packet.raw_row_count == 2
    assert packet.bids == [(100.0, 1.0)]
    assert packet.asks == [(101.0, 2.0)]


def test_side_mapping_builds_bids_and_asks_correctly():
    assembler = PacketAssembler(symbol_filter="BTCUSDT")
    rows = [
        {
            "symbol": "BTCUSDT",
            "event_time": 1,
            "transaction_time": 1,
            "received_time": 1,
            "event_type": "update",
            "first_update_id": 10,
            "final_update_id": 11,
            "prev_final_update_id": 9,
            "last_update_id": 11,
            "side": "buy",
            "price": "100.0",
            "quantity": "1.0",
        },
        {
            "symbol": "BTCUSDT",
            "event_time": 1,
            "transaction_time": 1,
            "received_time": 2,
            "event_type": "update",
            "first_update_id": 10,
            "final_update_id": 11,
            "prev_final_update_id": 9,
            "last_update_id": 11,
            "side": "sell",
            "price": "101.0",
            "quantity": "2.0",
        },
        {
            "symbol": "BTCUSDT",
            "event_time": 1,
            "transaction_time": 1,
            "received_time": 3,
            "event_type": "update",
            "first_update_id": 10,
            "final_update_id": 12,
            "prev_final_update_id": 11,
            "last_update_id": 12,
            "side": "0",
            "price": "99.5",
            "quantity": "3.0",
        },
        {
            "symbol": "BTCUSDT",
            "event_time": 1,
            "transaction_time": 1,
            "received_time": 4,
            "event_type": "update",
            "first_update_id": 10,
            "final_update_id": 12,
            "prev_final_update_id": 11,
            "last_update_id": 12,
            "side": "1",
            "price": "101.5",
            "quantity": "4.0",
        },
    ]

    first_finalized = None
    for row in rows:
        finalized = assembler.consume_row(row)
        if finalized:
            first_finalized = finalized[0]
    packet = assembler.finish()
    assert first_finalized is not None
    assert first_finalized.bids == [(100.0, 1.0)]
    assert first_finalized.asks == [(101.0, 2.0)]
    assert packet is not None
    assert packet.bids == [(99.5, 3.0)]
    assert packet.asks == [(101.5, 4.0)]

    assert dry_run.classify_side_value("bid") == "bid"
    assert dry_run.classify_side_value("ask") == "ask"
    assert dry_run.classify_side_value("buy") == "bid"
    assert dry_run.classify_side_value("sell") == "ask"
    assert dry_run.classify_side_value("0") == "bid"
    assert dry_run.classify_side_value("1") == "ask"


def test_snapshot_reset_packet_detection_when_ids_are_null():
    assembler = PacketAssembler(symbol_filter="BTCUSDT")
    assembler.consume_row(
        {
            "symbol": "BTCUSDT",
            "event_time": 1,
            "transaction_time": 1,
            "received_time": 1,
            "event_type": "snapshot",
            "first_update_id": None,
            "final_update_id": 11,
            "prev_final_update_id": None,
            "last_update_id": 11,
            "side": "bid",
            "price": "100.0",
            "quantity": "1.0",
        }
    )
    packet = assembler.finish()
    assert packet is not None
    assert packet.snapshot_or_reset is True


def test_sequence_gap_resync_handling_stops_in_strict_mode():
    packets = [
        PacketRecord(
            key=("BTCUSDT", 1, 11, 9, "update"),
            symbol="BTCUSDT",
            event_time=1,
            transaction_time=1,
            received_time=1,
            event_type="update",
            first_update_id=10,
            final_update_id=11,
            prev_final_update_id=9,
            last_update_id=11,
            bids=[(100.0, 1.0)],
            asks=[(101.0, 1.0)],
        ),
        PacketRecord(
            key=("BTCUSDT", 2, 12, 99, "update"),
            symbol="BTCUSDT",
            event_time=2,
            transaction_time=2,
            received_time=2,
            event_type="update",
            first_update_id=11,
            final_update_id=12,
            prev_final_update_id=99,
            last_update_id=12,
            bids=[(100.5, 1.0)],
            asks=[(101.5, 1.0)],
        ),
    ]

    result = dry_run.process_packets(packets, strict_sequence=True)
    assert result["sequence_gap_count"] == 1
    assert result["resync_stop_event_index"] == 2
    assert len(result["ofi_values"]) == 2
    assert result["ofi_values"][0] is None
    assert result["ofi_values"][1] is None


def test_ofi_summary_stats_handle_none_warmup_values():
    summary = dry_run.summarize_ofi([None, 2.0, -1.0, 0.0])
    assert summary["ofi_count"] == 3
    assert summary["ofi_null_count"] == 1
    assert summary["ofi_positive_count"] == 1
    assert summary["ofi_negative_count"] == 1
    assert summary["ofi_zero_count"] == 1
    assert summary["ofi_min"] == -1.0
    assert summary["ofi_max"] == 2.0


def test_report_includes_no_production_statement():
    context = {
        "input_file": "/tmp/sample.parquet.zst",
        "max_events": 5,
        "strict_sequence": True,
        "symbol": "BTCUSDT",
        "known_schema_quirks": [],
        "event_grouping_method": "grouped",
        "snapshot_reset_handling": "reset",
        "sequence_resync_handling": "resync",
        "dry_run_summary": {
            "read_mode": "bounded_batch_scan_in_memory",
            "source_file_read_complete": False,
            "rows_scanned": 10,
            "packets_built": 2,
            "bad_key_row_count": 0,
            "bad_cast_row_count": 0,
            "unknown_side_row_count": 0,
            "processed_event_count": 2,
            "ofi_emitted_count": 1,
            "warmup_none_count": 1,
            "sequence_gap_count": 0,
            "duplicate_final_update_id_count": 0,
            "snapshot_or_reset_event_count": 1,
            "resync_stop_event_index": None,
        },
        "ofi_summary": dry_run.summarize_ofi([None, 1.0]),
        "join_summary": {
            "bar_file_found": False,
            "bar_row_count": None,
            "join_helper_importable": True,
            "join_helper_callable": True,
            "coverage_preserving_join_attempted": False,
            "joined_row_count_if_attempted": None,
            "bar_count_preserved_if_attempted": None,
            "join_check_deferred": True,
        },
        "what_worked": [],
        "what_failed": [],
        "what_is_safe": [],
        "what_is_not_safe": [],
        "required_next_step": "next",
        "explicit_answers": [],
    }
    report = dry_run.render_report(context)
    assert dry_run.PRODUCTION_APPROVAL_STATEMENT in report
