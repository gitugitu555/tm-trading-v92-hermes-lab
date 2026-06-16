from __future__ import annotations

from pathlib import Path

import polars as pl

import scripts.validate_l2_ofi_segmented_policy_edge_cases as script
from features.l2_ofi_segmented_reconstruction import L2Packet, L2Segment, SegmentRunResult


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
    final_update_id: int,
    prev_final_update_id: int | None,
    *,
    transaction_time: int | None = 10,
    first_update_id: int | None = 1,
    bids=((100.0, 1.0),),
    asks=((101.0, 1.0),),
) -> L2Packet:
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
    frame = pl.DataFrame(
        [
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="bid", price="100.5", quantity="2.0"),
            _row(event_time=1, final_update_id=10, prev_final_update_id=9, side="ask", price="101.5", quantity="3.0"),
        ]
    )
    packets, counters = script._packets_from_frame(frame)
    assert counters["rows_scanned"] == 2
    assert len(packets) == 1
    assert isinstance(packets[0], L2Packet)
    assert packets[0].bids == ((100.5, 2.0),)
    assert packets[0].asks == ((101.5, 3.0),)


def test_candidate_scoring_ranks_source_gap_heavy_samples_above_clean_samples():
    clean = script.CandidatePreview(
        candidate_file_path="clean",
        file_date="2025-06-01",
        preview_row_count=100,
        preview_packet_count=10,
        missing_transaction_time_count=0,
        missing_first_update_id_count=0,
        missing_prev_final_update_id_count=0,
        estimated_source_gap_count=0,
        timestamp_non_monotonic_hint_count=0,
        repeated_final_update_id_hint_count=0,
        side_mapping_unknown_count=0,
        score=0,
    )
    dirty = script.CandidatePreview(
        candidate_file_path="dirty",
        file_date="2025-06-02",
        preview_row_count=100,
        preview_packet_count=10,
        missing_transaction_time_count=2,
        missing_first_update_id_count=1,
        missing_prev_final_update_id_count=1,
        estimated_source_gap_count=3,
        timestamp_non_monotonic_hint_count=2,
        repeated_final_update_id_hint_count=1,
        side_mapping_unknown_count=0,
        score=3361,
    )
    ranked = script.rank_candidate_previews([clean, dirty])
    assert ranked[0].candidate_file_path == "dirty"


def test_select_final_files_prefers_edge_cases_before_bounded_2026_slice():
    ordered_files = [
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-01-01/00/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-01/00/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/00/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/01/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/02/BTCUSDT_orderbook.parquet.zst"),
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/03/BTCUSDT_orderbook.parquet.zst"),
    ]
    previews = [
        script.CandidatePreview(
            candidate_file_path=ordered_files[0].as_posix(),
            file_date="2025-01-01",
            preview_row_count=100,
            preview_packet_count=10,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            repeated_final_update_id_hint_count=0,
            side_mapping_unknown_count=0,
            score=0,
        ),
        script.CandidatePreview(
            candidate_file_path=ordered_files[1].as_posix(),
            file_date="2025-06-28",
            preview_row_count=100,
            preview_packet_count=10,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            estimated_source_gap_count=3,
            timestamp_non_monotonic_hint_count=1,
            repeated_final_update_id_hint_count=1,
            side_mapping_unknown_count=0,
            score=3150,
        ),
        script.CandidatePreview(
            candidate_file_path=ordered_files[2].as_posix(),
            file_date="2025-08-28",
            preview_row_count=100,
            preview_packet_count=10,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            estimated_source_gap_count=2,
            timestamp_non_monotonic_hint_count=1,
            repeated_final_update_id_hint_count=0,
            side_mapping_unknown_count=0,
            score=2100,
        ),
        script.CandidatePreview(
            candidate_file_path=ordered_files[3].as_posix(),
            file_date="2025-09-01",
            preview_row_count=100,
            preview_packet_count=10,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            estimated_source_gap_count=1,
            timestamp_non_monotonic_hint_count=1,
            repeated_final_update_id_hint_count=0,
            side_mapping_unknown_count=0,
            score=1100,
        ),
    ] + [
        script.CandidatePreview(
            candidate_file_path=path.as_posix(),
            file_date="2026-01-01",
            preview_row_count=100,
            preview_packet_count=10,
            missing_transaction_time_count=0,
            missing_first_update_id_count=0,
            missing_prev_final_update_id_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            repeated_final_update_id_hint_count=0,
            side_mapping_unknown_count=0,
            score=0,
        )
        for path in ordered_files[4:]
    ]
    selected = script.select_final_files(previews, ordered_files, max_selected_files=6)
    selected_paths = [path.as_posix() for path, _ in selected]
    assert ordered_files[1].as_posix() in selected_paths
    assert ordered_files[2].as_posix() in selected_paths
    assert sum(1 for path in selected_paths if "2026-" in path) <= 4


def test_script_uses_policy_segment_packets_directly(monkeypatch):
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
    ordered_packets, segments, results = script._packet_count_and_segments([_packet(10, 9), _packet(20, 10)])
    assert calls == [2]
    assert len(segments) == 1
    assert len(results) == 1
    assert len(ordered_packets) == 2


def test_source_gap_in_synthetic_rows_becomes_source_sequence_gap_boundary():
    ordered_packets, segments, results = script._packet_count_and_segments(
        [_packet(10, 9), _packet(20, 10), _packet(30, 999)]
    )
    summary = script.summarize_segments(segments, results)
    assert len(segments) == 2
    assert segments[0].boundary_reason == "source_sequence_gap"
    assert summary["total_sequence_gap_count"] >= 0
    assert ordered_packets[0].final_update_id == 10


def test_snapshot_reset_in_synthetic_rows_becomes_snapshot_or_reset_boundary():
    ordered_packets, segments, results = script._packet_count_and_segments(
        [_packet(10, 9), _packet(20, None, first_update_id=None, transaction_time=20), _packet(30, 20, transaction_time=30)]
    )
    assert len(segments) == 2
    assert any(segment.boundary_reason == "snapshot_or_reset" for segment in segments)
    assert ordered_packets[1].first_update_id is None
    assert script.packet_sort_key(_packet(40, 39, transaction_time=None, first_update_id=1)).__class__ is tuple


def test_missing_transaction_time_uses_event_time_fallback_ordering():
    ordered_packets, segments, results = script._packet_count_and_segments(
        [
            _packet(20, 10, transaction_time=None, first_update_id=10),
            _packet(10, 9, transaction_time=None, first_update_id=9),
        ]
    )
    assert ordered_packets[0].final_update_id == 10
    assert ordered_packets[1].final_update_id == 20


def test_clean_segments_produce_clean_summary():
    ordered_packets, segments, results = script._packet_count_and_segments([_packet(10, 9), _packet(20, 10)])
    summary = script.summarize_segments(segments, results)
    assert summary["all_segments_clean"] is True
    assert summary["dirty_segment_count"] == 0
    assert summary["total_ofi_emitted_count"] >= 1


def test_one_packet_segments_counted_but_not_meaningful_coverage():
    ordered_packets, segments, results = script._packet_count_and_segments([_packet(10, 9)])
    summary = script.summarize_segments(segments, results)
    assert summary["meaningful_segment_count"] == 0
    assert len(segments) == 1
    assert results[0].warmup_none_count == 1


def test_report_includes_no_production_no_alpha_statement(tmp_path: Path):
    selected_files = [(Path("/tmp/example/BTCUSDT_orderbook.parquet.zst"), "edge_case_candidate")]
    selected_results = [
        script.SelectedFileResult(
            file_path=selected_files[0][0].as_posix(),
            file_date="2025-06-28",
            selection_reason="edge_case_candidate",
            packet_count=1,
            segment_count=1,
            meaningful_segment_count=0,
            source_gap_boundary_count=1,
            snapshot_reset_boundary_count=0,
            clean_segment_count=1,
            dirty_segment_count=0,
            all_segments_clean=True,
            total_ofi_emitted_count=0,
            total_warmup_none_count=1,
            total_sequence_gap_count=0,
            min_segment_packet_count=1,
            max_segment_packet_count=1,
            one_packet_segment_count=1,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_preselection_source_gap_count=0,
            actual_source_gap_boundary_count=1,
            timestamp_fallback_used=False,
            side_mapping_unknown_count=0,
            join_result={
                "file_date": "2025-06-28",
                "bar_file_found": False,
                "bar_row_count": None,
                "join_attempted": False,
                "bar_count_preserved": None,
                "join_deferred_reason": "no_bar_file",
            },
            packets=[_packet(10, 9)],
            segments=(L2Segment(1, 1, 1, "file_start", "sample_end", (_packet(10, 9),)),),
            results=[SegmentRunResult(1, 1, 0, 1, 0, True)],
        )
    ]
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        candidate_file_count=1,
        candidate_previews=[
            script.CandidatePreview(
                candidate_file_path=selected_files[0][0].as_posix(),
                file_date="2025-06-28",
                preview_row_count=2,
                preview_packet_count=1,
                missing_transaction_time_count=0,
                missing_first_update_id_count=0,
                missing_prev_final_update_id_count=0,
                estimated_source_gap_count=0,
                timestamp_non_monotonic_hint_count=0,
                repeated_final_update_id_hint_count=0,
                side_mapping_unknown_count=0,
                score=0,
            )
        ],
        selected_files=selected_files,
        file_results=selected_results,
        join_rows=[selected_results[0].join_result],
        max_candidate_files=120,
        max_selected_files=24,
    )
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
    assert "Snapshot/reset-like packets were not observed" in report
    assert "bounded raw edge-case sample did not contain selected packets requiring fallback" in report


def test_report_labels_and_raw_sample_scope_are_precise(tmp_path: Path):
    selected_files = [(Path("/tmp/example/BTCUSDT_orderbook.parquet.zst"), "edge_case_candidate")]
    selected_results = [
        script.SelectedFileResult(
            file_path=selected_files[0][0].as_posix(),
            file_date="2025-06-28",
            selection_reason="edge_case_candidate",
            packet_count=1,
            segment_count=1,
            meaningful_segment_count=0,
            source_gap_boundary_count=1,
            snapshot_reset_boundary_count=0,
            clean_segment_count=1,
            dirty_segment_count=0,
            all_segments_clean=True,
            total_ofi_emitted_count=0,
            total_warmup_none_count=1,
            total_sequence_gap_count=0,
            min_segment_packet_count=1,
            max_segment_packet_count=1,
            one_packet_segment_count=1,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_preselection_source_gap_count=0,
            actual_source_gap_boundary_count=1,
            timestamp_fallback_used=False,
            side_mapping_unknown_count=0,
            join_result={
                "file_date": "2025-06-28",
                "bar_file_found": False,
                "bar_row_count": None,
                "join_attempted": False,
                "bar_count_preserved": None,
                "join_deferred_reason": "no_bar_file",
            },
            packets=[_packet(10, 9)],
            segments=(L2Segment(1, 1, 1, "file_start", "sample_end", (_packet(10, 9),)),),
            results=[SegmentRunResult(1, 1, 0, 1, 0, True)],
        )
    ]
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        candidate_file_count=1,
        candidate_previews=[
            script.CandidatePreview(
                candidate_file_path=selected_files[0][0].as_posix(),
                file_date="2025-06-28",
                preview_row_count=2,
                preview_packet_count=1,
                missing_transaction_time_count=0,
                missing_first_update_id_count=0,
                missing_prev_final_update_id_count=0,
                estimated_source_gap_count=0,
                timestamp_non_monotonic_hint_count=0,
                repeated_final_update_id_hint_count=0,
                side_mapping_unknown_count=0,
                score=0,
            )
        ],
        selected_files=selected_files,
        file_results=selected_results,
        join_rows=[selected_results[0].join_result],
        max_candidate_files=120,
        max_selected_files=24,
    )
    assert "raw_sample_source_gap_validated = yes" in report
    assert "raw_sample_snapshot_reset_observed = no" in report
    assert "raw_sample_timestamp_fallback_observed = no" in report
    assert "snapshot_reset_policy_unit_covered = yes" in report
    assert "timestamp_fallback_policy_unit_covered = yes" in report
    assert "raw_sample_snapshot_resets_not_observed" in report
    assert "raw_sample_timestamp_fallback_not_observed" in report
    assert "segmented_policy_edge_case_validated_bounded_only" in report
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
