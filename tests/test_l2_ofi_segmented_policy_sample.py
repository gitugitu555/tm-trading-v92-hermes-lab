from __future__ import annotations

from pathlib import Path

import scripts.validate_l2_ofi_segmented_policy_sample as script
from features.l2_ofi_segmented_reconstruction import L2Packet, L2Segment, SegmentRunResult


def _row(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    first_update_id: int | None = 1,
    transaction_time: int | None = 10,
    received_time: int | None = 20,
    event_type: str = "depthUpdate",
    side: str = "bid",
    price: str = "100.0",
    quantity: str = "1.5",
):
    return {
        "symbol": "BTCUSDT",
        "event_time": event_time,
        "transaction_time": transaction_time,
        "received_time": received_time,
        "event_type": event_type,
        "first_update_id": first_update_id,
        "final_update_id": final_update_id,
        "prev_final_update_id": prev_final_update_id,
        "last_update_id": final_update_id,
        "side": side,
        "price": price,
        "quantity": quantity,
    }


def _packet(final_update_id: int, prev_final_update_id: int | None, *, transaction_time: int | None = 10, first_update_id: int | None = 1, bids=((100.0, 1.0),), asks=((101.0, 1.0),)) -> L2Packet:
    return L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=1000 + final_update_id,
        transaction_time=transaction_time,
        received_time=20,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        bids=bids,
        asks=asks,
    )


def test_raw_rows_convert_into_l2packet_objects():
    packets, counters = script.rows_to_l2_packets(
        [
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="bid", price="100.5", quantity="2.0"),
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="ask", price="101.5", quantity="3.0"),
        ],
        symbol_filter="BTCUSDT",
    )
    assert counters["rows_scanned"] == 2
    assert len(packets) == 1
    assert isinstance(packets[0], L2Packet)
    assert packets[0].bids == ((100.5, 2.0),)
    assert packets[0].asks == ((101.5, 3.0),)


def test_script_uses_policy_segment_packets_directly(monkeypatch):
    calls: dict[str, int] = {}

    def fake_segment_packets(packets):
        packets = tuple(packets)
        calls["packet_count"] = len(packets)
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

    def fake_run_segment_with_ofi_engine(segment, *, strict_sequence: bool = True):
        return SegmentRunResult(
            segment_id=segment.segment_id,
            packet_count=len(segment.packets),
            ofi_emitted_count=1,
            warmup_none_count=0,
            sequence_gap_count=0,
            clean=True,
        )

    monkeypatch.setattr(script, "segment_packets", fake_segment_packets)
    monkeypatch.setattr(script, "run_segment_with_ofi_engine", fake_run_segment_with_ofi_engine)

    result = script.evaluate_packets([_packet(10, 9), _packet(20, 10)])
    assert calls["packet_count"] == 2
    assert result["packet_count"] == 2
    assert result["total_ofi_emitted_count"] == 1


def test_source_gap_becomes_source_sequence_gap_boundary():
    result = script.evaluate_packets(
        [
            _packet(10, 9),
            _packet(20, 10),
            _packet(30, 999),
        ]
    )
    assert result["segment_count"] == 2
    assert result["source_gap_boundary_count"] == 1
    assert result["snapshot_reset_boundary_count"] == 0


def test_snapshot_reset_becomes_snapshot_or_reset_boundary():
    result = script.evaluate_packets(
        [
            _packet(10, 9),
            _packet(20, None, first_update_id=None, transaction_time=20),
            _packet(30, 20, transaction_time=30),
        ]
    )
    assert result["segment_count"] == 2
    assert result["snapshot_reset_boundary_count"] == 1
    assert result["source_gap_boundary_count"] == 0


def test_clean_segments_produce_clean_summary():
    result = script.evaluate_packets([_packet(10, 9), _packet(20, 10)])
    assert result["all_segments_clean"] is True
    assert result["dirty_segment_count"] == 0
    assert result["total_ofi_emitted_count"] >= 1


def test_one_packet_segment_is_not_meaningful_coverage():
    result = script.evaluate_packets([_packet(10, 9)])
    assert result["segment_count"] == 1
    assert result["meaningful_segment_count"] == 0
    assert result["one_packet_segment_count"] == 1
    assert result["total_ofi_emitted_count"] == 0
    assert result["total_warmup_none_count"] == 1


def test_report_includes_no_production_no_alpha_statement(tmp_path: Path):
    selected = [Path("/tmp/example/BTCUSDT_orderbook.parquet.zst")]
    file_results = [
        {
            "file_path": selected[0].as_posix(),
            "file_date": "2025-06-28",
            "is_repeated_from_previous_rehearsal": True,
            "rows_scanned": 2,
            "packet_count": 1,
            "segment_count": 1,
            "meaningful_segment_count": 0,
            "source_gap_boundary_count": 0,
            "snapshot_reset_boundary_count": 0,
            "clean_segment_count": 1,
            "dirty_segment_count": 0,
            "all_segments_clean": True,
            "total_ofi_emitted_count": 0,
            "total_warmup_none_count": 1,
            "total_sequence_gap_count": 0,
            "min_segment_packet_count": 1,
            "max_segment_packet_count": 1,
            "one_packet_segment_count": 1,
            "join_result": {
                "file_date": "2025-06-28",
                "bar_file_found": False,
                "bar_row_count": None,
                "join_attempted": False,
                "bar_count_preserved": None,
                "join_deferred_reason": "no_bar_file",
            },
        }
    ]
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        selected_files=selected,
        file_results=file_results,
        join_rows=[
            {
                "file_date": "2025-06-28",
                "bar_file_found": False,
                "bar_row_count": None,
                "join_attempted": False,
                "bar_count_preserved": None,
                "join_deferred_reason": "no_bar_file",
            }
        ],
        max_files=18,
        prior_rehearsal=script.PRIOR_REHEARSAL_FILES,
    )
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
