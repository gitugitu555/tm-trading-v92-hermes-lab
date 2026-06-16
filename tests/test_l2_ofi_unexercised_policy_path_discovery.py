from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.discover_l2_ofi_unexercised_policy_paths as script


def _row(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    transaction_time: int | None = 10,
    received_time: int | None = 20,
    first_update_id: int | None = 1,
    side: str = "bid",
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
        "side": side,
        "price": "100.0",
        "quantity": "1.0",
    }


def test_candidate_scoring_prioritizes_snapshot_reset_candidates():
    clean = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9)]),
        candidate_file_path="/tmp/clean.parquet.zst",
        preview_rows_per_file=10,
    )
    snapshot = script.preview_candidate_frame(
        pd.DataFrame(
            [
                _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None),
                _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None, side="ask"),
            ]
        ),
        candidate_file_path="/tmp/snapshot.parquet.zst",
        preview_rows_per_file=10,
    )
    ranked = script.rank_candidate_previews([clean, snapshot])
    assert ranked[0].candidate_file_path == "/tmp/snapshot.parquet.zst"
    assert ranked[0].snapshot_like_packet_count > 0


def test_candidate_scoring_prioritizes_missing_transaction_time_candidates():
    clean = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9)]),
        candidate_file_path="/tmp/clean.parquet.zst",
        preview_rows_per_file=10,
    )
    fallback = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9, transaction_time=None)]),
        candidate_file_path="/tmp/fallback.parquet.zst",
        preview_rows_per_file=10,
    )
    ranked = script.rank_candidate_previews([clean, fallback])
    assert ranked[0].candidate_file_path == "/tmp/fallback.parquet.zst"
    assert ranked[0].missing_transaction_time_count > 0


def test_source_gap_estimate_excludes_snapshot_reset_like_packets():
    preview = script.preview_candidate_frame(
        pd.DataFrame(
            [
                _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None),
                _row(event_time=2, final_update_id=20, prev_final_update_id=10, first_update_id=2),
            ]
        ),
        candidate_file_path="/tmp/mixed.parquet.zst",
        preview_rows_per_file=10,
    )
    assert preview.snapshot_like_packet_count == 1
    assert preview.estimated_source_gap_count == 0


def test_unknown_side_mappings_are_counted_defensively():
    preview = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9, side="???")]),
        candidate_file_path="/tmp/unknown-side.parquet.zst",
        preview_rows_per_file=10,
    )
    assert preview.side_mapping_unknown_count == 1
    assert preview.candidate_score > 0


def test_missing_columns_do_not_crash_discovery():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSDT",
                "event_time": 1,
                "final_update_id": 10,
                "side": "bid",
                "price": "100.0",
                "quantity": "1.0",
            }
        ]
    )
    preview = script.preview_candidate_frame(frame, candidate_file_path="/tmp/missing-cols.parquet.zst", preview_rows_per_file=10)
    assert preview.missing_required_column_count > 0
    assert preview.preview_row_count == 1


def test_report_includes_no_production_no_alpha_statement():
    preview = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9)]),
        candidate_file_path="/tmp/clean.parquet.zst",
        preview_rows_per_file=10,
    )
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        candidate_file_count=1,
        selected_findings=[preview],
        candidate_previews=[preview],
        max_candidate_files=360,
        max_selected_findings=40,
    )
    assert script.PRODUCTION_APPROVAL_STATEMENT in report


def test_report_clearly_states_no_raw_candidates_when_counts_are_zero():
    preview = script.preview_candidate_frame(
        pd.DataFrame([_row(event_time=1, final_update_id=10, prev_final_update_id=9)]),
        candidate_file_path="/tmp/clean.parquet.zst",
        preview_rows_per_file=10,
    )
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        candidate_file_count=1,
        selected_findings=[],
        candidate_previews=[preview],
        max_candidate_files=360,
        max_selected_findings=40,
    )
    assert "No raw snapshot/reset-like candidates were found in this bounded discovery window." in report
    assert "No raw missing transaction_time fallback candidates were found in this bounded discovery window." in report
    assert "No raw source-gap candidates were found in this bounded discovery window." in report


def test_report_uses_conservative_decision_labels():
    snapshot_preview = script.preview_candidate_frame(
        pd.DataFrame(
            [
                _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None),
                _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None, side="ask"),
            ]
        ),
        candidate_file_path="/tmp/snapshot.parquet.zst",
        preview_rows_per_file=10,
    )
    report = script.build_report(
        l2_root=Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT"),
        candidate_file_count=1,
        selected_findings=[snapshot_preview],
        candidate_previews=[snapshot_preview],
        max_candidate_files=360,
        max_selected_findings=40,
    )
    assert "bounded_read_only_discovery" in report
    assert "candidate_selection_deterministic" in report
    assert "no_ofi_artifacts_written" in report
    assert "full_reconstruction_not_approved" in report
    assert "segmented_reconstruction_still_bounded_only" in report
    assert "alpha_blocked" in report
    assert "paper_live_blocked" in report
