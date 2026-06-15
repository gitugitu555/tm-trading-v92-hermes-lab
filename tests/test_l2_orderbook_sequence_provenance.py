from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.audit_l2_orderbook_sequence_provenance as audit


def test_schema_classifier_detects_complete_schema():
    cols = [
        "received_time",
        "event_time",
        "transaction_time",
        "symbol",
        "event_type",
        "first_update_id",
        "final_update_id",
        "prev_final_update_id",
        "last_update_id",
        "side",
        "price",
        "quantity",
    ]
    assert audit.classify_schema_columns(cols) == "schema_complete"


def test_schema_classifier_detects_missing_sequence_fields():
    cols = [
        "received_time",
        "event_time",
        "transaction_time",
        "symbol",
        "event_type",
        "side",
        "price",
        "quantity",
    ]
    assert audit.classify_schema_columns(cols) == "schema_missing_sequence_fields"


def test_sequence_gap_detector_catches_prev_final_mismatch():
    df = pd.DataFrame(
        {
            "event_time": [1, 2, 3],
            "first_update_id": [10, 11, 12],
            "final_update_id": [10, 11, 12],
            "prev_final_update_id": [9, 10, 99],
            "last_update_id": [10, 11, 12],
        }
    )
    gap_count, gap_rate, non_mono_event, non_mono_update = audit._sequence_gap_stats(df)
    assert gap_count == 1
    assert gap_rate == 0.5
    assert non_mono_event == 0
    assert non_mono_update == 0


def test_non_monotonic_event_time_detector_works():
    df = pd.DataFrame(
        {
            "event_time": [1, 5, 4],
            "first_update_id": [10, 11, 12],
            "final_update_id": [10, 11, 12],
            "prev_final_update_id": [9, 10, 11],
            "last_update_id": [10, 11, 12],
        }
    )
    _, _, non_mono_event, _ = audit._sequence_gap_stats(df)
    assert non_mono_event == 1


def test_cross_file_continuity_classifier_detects_plausible_continuity():
    left = audit.SampleFileStats(
        file_path="left",
        file_size_bytes=1,
        mtime_utc="2026-01-01T00:00:00Z",
        schema_columns=[],
        row_count_if_available=1,
        min_event_time_sample=1,
        max_event_time_sample=1,
        min_transaction_time_sample=1,
        max_transaction_time_sample=1,
        min_received_time_sample=1,
        max_received_time_sample=1,
        min_first_update_id_sample=10,
        max_final_update_id_sample=20,
        min_prev_final_update_id_sample=9,
        max_prev_final_update_id_sample=19,
        side_values_sample="bid",
        event_type_values_sample="depthUpdate",
        price_null_count_sample=0,
        quantity_null_count_sample=0,
        duplicate_update_id_count_sample=0,
        negative_quantity_count_sample=0,
        zero_quantity_count_sample=0,
        schema_classification="schema_complete",
        sample_sequence_gap_count=0,
        sample_sequence_gap_rate=0.0,
        sample_non_monotonic_event_time_count=0,
        sample_non_monotonic_update_id_count=0,
    )
    right = audit.SampleFileStats(
        file_path="right",
        file_size_bytes=1,
        mtime_utc="2026-01-01T01:00:00Z",
        schema_columns=[],
        row_count_if_available=1,
        min_event_time_sample=2,
        max_event_time_sample=2,
        min_transaction_time_sample=2,
        max_transaction_time_sample=2,
        min_received_time_sample=2,
        max_received_time_sample=2,
        min_first_update_id_sample=21,
        max_final_update_id_sample=30,
        min_prev_final_update_id_sample=20,
        max_prev_final_update_id_sample=29,
        side_values_sample="ask",
        event_type_values_sample="depthUpdate",
        price_null_count_sample=0,
        quantity_null_count_sample=0,
        duplicate_update_id_count_sample=0,
        negative_quantity_count_sample=0,
        zero_quantity_count_sample=0,
        schema_classification="schema_complete",
        sample_sequence_gap_count=0,
        sample_sequence_gap_rate=0.0,
        sample_non_monotonic_event_time_count=0,
        sample_non_monotonic_update_id_count=0,
    )
    assert audit._classify_cross_file_continuity(left, right) == "cross_file_continuity_plausible"


def test_report_includes_no_production_statement(tmp_path):
    root_status = [audit.RootStatus(path=str(tmp_path), exists=True, candidate_count=1, note="present")]
    candidate_rows = [
        audit.CandidateFile(
            path=str(tmp_path / "BTCUSDT_orderbook.parquet.zst"),
            file_size_bytes=1,
            extension=".parquet.zst",
            mtime_utc="2026-01-01T00:00:00Z",
            name_match_terms="orderbook",
            parent_dir=str(tmp_path),
            symbol_guess="BTCUSDT",
            venue_guess="binance_futures",
            data_type_guess="l2_diff",
            time_coverage_guess="2026-01-01",
            schema_hint="received_time, event_time, transaction_time, symbol, event_type, first_update_id, final_update_id, prev_final_update_id, last_update_id, side, price, quantity",
            usable_for_ofi_reconstruction_guess="possibly_ready_needs_schema_check",
            risk="moderate",
            required_action="Validate schema.",
            source_family=str(tmp_path),
        )
    ]
    sample_rows = [
        audit.SampleFileStats(
            file_path=str(tmp_path / "BTCUSDT_orderbook.parquet.zst"),
            file_size_bytes=1,
            mtime_utc="2026-01-01T00:00:00Z",
            schema_columns=["received_time", "event_time", "transaction_time", "symbol", "event_type", "first_update_id", "final_update_id", "prev_final_update_id", "last_update_id", "side", "price", "quantity"],
            row_count_if_available=3,
            min_event_time_sample=1,
            max_event_time_sample=3,
            min_transaction_time_sample=1,
            max_transaction_time_sample=3,
            min_received_time_sample=1,
            max_received_time_sample=3,
            min_first_update_id_sample=10,
            max_final_update_id_sample=12,
            min_prev_final_update_id_sample=9,
            max_prev_final_update_id_sample=11,
            side_values_sample="bid",
            event_type_values_sample="depthUpdate",
            price_null_count_sample=0,
            quantity_null_count_sample=0,
            duplicate_update_id_count_sample=0,
            negative_quantity_count_sample=0,
            zero_quantity_count_sample=0,
            schema_classification="schema_complete",
            sample_sequence_gap_count=0,
            sample_sequence_gap_rate=0.0,
            sample_non_monotonic_event_time_count=0,
            sample_non_monotonic_update_id_count=0,
            cross_file_continuity_status="cross_file_continuity_plausible",
        )
    ]
    report = audit.render_report(root_status, candidate_rows, sample_rows, [("left", "right", "cross_file_continuity_plausible")], {
        "first_date": "2026-01-01",
        "last_date": "2026-01-01",
        "file_count": 1,
        "date_count": 1,
        "hour_count": 1,
        "missing_day_count_if_inferable": 0,
        "missing_hour_count_if_inferable": 23,
        "duplicate_hour_count_if_inferable": 0,
    })
    assert audit.PRODUCTION_APPROVAL_STATEMENT in report
