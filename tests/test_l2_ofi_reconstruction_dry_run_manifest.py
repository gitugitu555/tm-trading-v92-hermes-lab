from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import polars as pl

import scripts.build_l2_ofi_reconstruction_dry_run_manifest as script


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


def test_deterministic_candidate_selection_includes_anchors_and_known_candidates():
    anchor_paths = [Path(path) for path, _ in script.DEFAULT_CANDIDATE_INPUTS]
    extra_paths = [Path(f"/tmp/file_{idx:04d}.parquet.zst") for idx in range(200)]
    candidates, discovered_count = script.select_candidate_files(anchor_paths + extra_paths, 80, None)
    selected_paths = {candidate.path for candidate in candidates}

    assert discovered_count == len(anchor_paths) + len(extra_paths)
    assert set(anchor_paths).issubset(selected_paths)
    assert any(candidate.candidate_reason == "known_original_sample" for candidate in candidates)
    assert any(candidate.candidate_reason == "known_source_gap_heavy" for candidate in candidates)
    assert any(candidate.candidate_reason == "known_snapshot_reset_bridge" for candidate in candidates)


def test_preview_policy_class_assignment_for_clean_source_gap_snapshot_and_deferred(monkeypatch):
    clean_frame = pd.DataFrame([
        _row(event_time=1, final_update_id=10, prev_final_update_id=9),
        _row(event_time=2, final_update_id=11, prev_final_update_id=10),
    ])
    source_gap_frame = pd.DataFrame([
        _row(event_time=1, final_update_id=10, prev_final_update_id=9),
        _row(event_time=2, final_update_id=11, prev_final_update_id=99),
    ])
    snapshot_frame = pd.DataFrame([
        _row(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None),
        _row(event_time=2, final_update_id=15, prev_final_update_id=9, first_update_id=10),
    ])
    empty_frame = pd.DataFrame()
    missing_column_frame = pd.DataFrame([
        {"symbol": "BTCUSDT", "event_time": 1, "final_update_id": 10, "prev_final_update_id": 9, "event_type": "depthUpdate", "price": "100", "quantity": "1"},
    ])

    frames = {
        "/tmp/clean.parquet.zst": clean_frame,
        "/tmp/source_gap.parquet.zst": source_gap_frame,
        "/tmp/snapshot.parquet.zst": snapshot_frame,
        "/tmp/empty.parquet.zst": empty_frame,
        "/tmp/missing.parquet.zst": missing_column_frame,
    }
    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: frames[path.as_posix()])

    clean = script.preview_candidate_file(Path("/tmp/clean.parquet.zst"), candidate_reason="evenly_spaced", max_rows=10)
    source_gap = script.preview_candidate_file(Path("/tmp/source_gap.parquet.zst"), candidate_reason="evenly_spaced", max_rows=10)
    snapshot = script.preview_candidate_file(Path("/tmp/snapshot.parquet.zst"), candidate_reason="evenly_spaced", max_rows=10)
    empty = script.preview_candidate_file(Path("/tmp/empty.parquet.zst"), candidate_reason="evenly_spaced", max_rows=10)
    missing = script.preview_candidate_file(Path("/tmp/missing.parquet.zst"), candidate_reason="evenly_spaced", max_rows=10)

    assert clean.dry_run_policy_class == "likely_clean_preview"
    assert source_gap.dry_run_policy_class == "likely_source_gap_preview"
    assert snapshot.dry_run_policy_class == "likely_snapshot_reset_preview"
    assert empty.dry_run_policy_class == "deferred_empty_preview"
    assert missing.dry_run_policy_class == "deferred_missing_columns"


def test_policy_check_status_assignment_for_accepted_quarantined_rejected_and_deferred(monkeypatch):
    frame = pd.DataFrame([
        _row(event_time=1, final_update_id=10, prev_final_update_id=9),
        _row(event_time=2, final_update_id=11, prev_final_update_id=10),
    ])
    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: frame)
    monkeypatch.setattr(script, "segment_packets", lambda packets: (SimpleNamespace(quarantined=False, packets=tuple(packets)),))
    monkeypatch.setattr(script, "run_segment_with_ofi_engine", lambda segment: SimpleNamespace(quarantined=False, ofi_emitted_count=1, clean=True))

    def summary_factory(**kwargs):
        return kwargs

    cases = [
        ("accepted_bounded_clean", dict(segment_count=1, meaningful_segment_count=1, clean_segment_count=1, dirty_segment_count=0, all_segments_clean=True, source_gap_boundary_count=0, snapshot_bridge_event_count=0, snapshot_reset_clean_seed_count=0, snapshot_reset_chain_failure_count=0, quarantined_segment_count=0, total_ofi_emitted_count=1, total_warmup_none_count=0, total_sequence_gap_count=0, ofi_suppressed_due_to_snapshot_bridge_count=0, ofi_suppressed_due_to_quarantine_count=0)),
        ("accepted_bounded_source_gap_clean", dict(segment_count=1, meaningful_segment_count=1, clean_segment_count=1, dirty_segment_count=0, all_segments_clean=True, source_gap_boundary_count=2, snapshot_bridge_event_count=0, snapshot_reset_clean_seed_count=0, snapshot_reset_chain_failure_count=0, quarantined_segment_count=0, total_ofi_emitted_count=1, total_warmup_none_count=0, total_sequence_gap_count=0, ofi_suppressed_due_to_snapshot_bridge_count=0, ofi_suppressed_due_to_quarantine_count=0)),
        ("accepted_bounded_snapshot_bridge_clean", dict(segment_count=1, meaningful_segment_count=1, clean_segment_count=1, dirty_segment_count=0, all_segments_clean=True, source_gap_boundary_count=0, snapshot_bridge_event_count=1, snapshot_reset_clean_seed_count=1, snapshot_reset_chain_failure_count=0, quarantined_segment_count=0, total_ofi_emitted_count=1, total_warmup_none_count=0, total_sequence_gap_count=0, ofi_suppressed_due_to_snapshot_bridge_count=1, ofi_suppressed_due_to_quarantine_count=0)),
        ("quarantined_bounded_snapshot_chain_failure", dict(segment_count=1, meaningful_segment_count=1, clean_segment_count=0, dirty_segment_count=1, all_segments_clean=False, source_gap_boundary_count=0, snapshot_bridge_event_count=0, snapshot_reset_clean_seed_count=0, snapshot_reset_chain_failure_count=1, quarantined_segment_count=1, total_ofi_emitted_count=0, total_warmup_none_count=0, total_sequence_gap_count=0, ofi_suppressed_due_to_snapshot_bridge_count=0, ofi_suppressed_due_to_quarantine_count=1)),
        ("rejected_bounded_dirty_sequence", dict(segment_count=1, meaningful_segment_count=1, clean_segment_count=0, dirty_segment_count=1, all_segments_clean=False, source_gap_boundary_count=0, snapshot_bridge_event_count=0, snapshot_reset_clean_seed_count=0, snapshot_reset_chain_failure_count=0, quarantined_segment_count=0, total_ofi_emitted_count=0, total_warmup_none_count=0, total_sequence_gap_count=1, ofi_suppressed_due_to_snapshot_bridge_count=0, ofi_suppressed_due_to_quarantine_count=0)),
    ]

    def fake_run_segment(segment):
        return SimpleNamespace(quarantined=False, ofi_emitted_count=1)

    for status, summary in cases:
        def fake_segment_packets(packets, summary=summary):
            packet_tuple = tuple(packets)
            boundary_reason = "source_sequence_gap" if summary["source_gap_boundary_count"] > 0 else "sample_end"
            return (SimpleNamespace(quarantined=False, packets=packet_tuple, boundary_reason=boundary_reason),)

        monkeypatch.setattr(script, "segment_packets", fake_segment_packets)
        monkeypatch.setattr(script, "run_segment_with_ofi_engine", fake_run_segment)
        monkeypatch.setattr(script, "summarize_segments", lambda segments, results, summary=summary: summary)
        result = script._run_policy_check(
            script.CandidatePreview(
                candidate_file_path="/tmp/candidate.parquet.zst",
                file_date="2026-01-01",
                file_hour="00",
                preview_row_count=2,
                preview_packet_count=2,
                missing_required_column_count=0,
                missing_transaction_time_count=0,
                snapshot_like_packet_count=0,
                estimated_source_gap_count=0,
                timestamp_non_monotonic_hint_count=0,
                side_mapping_unknown_count=0,
                candidate_reason="known_original_sample",
                candidate_score=100,
                dry_run_policy_class="policy_check_selected",
            ),
            Path("/tmp/candidate.parquet.zst"),
            10,
        )
        assert result.policy_check_status == status

    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: pd.DataFrame())
    empty_result = script._run_policy_check(
        script.CandidatePreview(
            candidate_file_path="/tmp/empty.parquet.zst",
            file_date="2026-01-01",
            file_hour="00",
            preview_row_count=0,
            preview_packet_count=0,
            missing_required_column_count=0,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            side_mapping_unknown_count=0,
            candidate_reason="evenly_spaced",
            candidate_score=0,
            dry_run_policy_class="deferred_empty_preview",
        ),
        Path("/tmp/empty.parquet.zst"),
        10,
    )
    assert empty_result.policy_check_status == "deferred_no_packets"

    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: pd.DataFrame([{"symbol": "BTCUSDT"}]))
    missing_result = script._run_policy_check(
        script.CandidatePreview(
            candidate_file_path="/tmp/missing.parquet.zst",
            file_date="2026-01-01",
            file_hour="00",
            preview_row_count=1,
            preview_packet_count=0,
            missing_required_column_count=1,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            side_mapping_unknown_count=0,
            candidate_reason="evenly_spaced",
            candidate_score=0,
            dry_run_policy_class="deferred_missing_columns",
        ),
        Path("/tmp/missing.parquet.zst"),
        10,
    )
    assert missing_result.policy_check_status == "deferred_missing_columns"


def test_policy_check_handles_missing_source_gap_summary_key(monkeypatch):
    frame = pd.DataFrame([
        _row(event_time=1, final_update_id=10, prev_final_update_id=9),
        _row(event_time=2, final_update_id=11, prev_final_update_id=10),
    ])
    monkeypatch.setattr(script, "_read_parquet_preview", lambda path, max_rows: frame)
    monkeypatch.setattr(
        script,
        "segment_packets",
        lambda packets: (SimpleNamespace(quarantined=False, packets=tuple(packets), boundary_reason="sample_end"),),
    )
    monkeypatch.setattr(script, "run_segment_with_ofi_engine", lambda segment: SimpleNamespace(quarantined=False, ofi_emitted_count=1, clean=True))
    monkeypatch.setattr(
        script,
        "summarize_segments",
        lambda segments, results: {
            "segment_count": 1,
            "meaningful_segment_count": 1,
            "clean_segment_count": 1,
            "dirty_segment_count": 0,
            "all_segments_clean": True,
            "snapshot_bridge_event_count": 0,
            "snapshot_reset_clean_seed_count": 0,
            "snapshot_reset_chain_failure_count": 0,
            "quarantined_segment_count": 0,
            "total_ofi_emitted_count": 1,
            "total_warmup_none_count": 0,
            "total_sequence_gap_count": 0,
            "ofi_suppressed_due_to_snapshot_bridge_count": 0,
            "ofi_suppressed_due_to_quarantine_count": 0,
        },
    )

    result = script._run_policy_check(
        script.CandidatePreview(
            candidate_file_path="/tmp/candidate.parquet.zst",
            file_date="2026-01-01",
            file_hour="00",
            preview_row_count=2,
            preview_packet_count=2,
            missing_required_column_count=0,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            side_mapping_unknown_count=0,
            candidate_reason="known_original_sample",
            candidate_score=100,
            dry_run_policy_class="policy_check_selected",
        ),
        Path("/tmp/candidate.parquet.zst"),
        10,
    )

    assert result.source_gap_boundary_count == 0
    assert result.policy_check_status == "accepted_bounded_clean"


def test_report_includes_no_production_no_alpha_no_full_reconstruction_statement():
    candidate_inputs = [_candidate for _candidate in [script.CandidateFile(path=Path("/tmp/a.parquet.zst"), candidate_reason="known_original_sample")]]
    previews = [
        script.CandidatePreview(
            candidate_file_path="/tmp/a.parquet.zst",
            file_date="2026-01-01",
            file_hour="00",
            preview_row_count=1,
            preview_packet_count=1,
            missing_required_column_count=0,
            missing_transaction_time_count=0,
            snapshot_like_packet_count=0,
            estimated_source_gap_count=0,
            timestamp_non_monotonic_hint_count=0,
            side_mapping_unknown_count=0,
            candidate_reason="known_original_sample",
            candidate_score=100,
            dry_run_policy_class="policy_check_selected",
        )
    ]
    policy_results = [
        script.PolicyCheckResult(
            file_path="/tmp/a.parquet.zst",
            file_date="2026-01-01",
            file_hour="00",
            rows_scanned=1,
            packet_count=1,
            segment_count=1,
            meaningful_segment_count=1,
            clean_segment_count=1,
            dirty_segment_count=0,
            all_segments_clean=True,
            source_gap_boundary_count=0,
            snapshot_like_packet_count=0,
            snapshot_bridge_event_count=0,
            snapshot_reset_clean_seed_count=0,
            snapshot_reset_chain_failure_count=0,
            quarantined_segment_count=0,
            total_ofi_emitted_count=1,
            total_warmup_none_count=0,
            total_sequence_gap_count=0,
            ofi_suppressed_due_to_snapshot_bridge_count=0,
            ofi_suppressed_due_to_quarantine_count=0,
            policy_check_status="accepted_bounded_clean",
            candidate_reason="known_original_sample",
            candidate_score=100,
            dry_run_policy_class="policy_check_selected",
            quarantined_segment_ofi_emitted_count=0,
            side_mapping_unknown_count=0,
        )
    ]
    join_results = [
        script.JoinReadinessResult(
            file_date="2026-01-01",
            bar_file_found=True,
            bar_row_count=10,
            join_attempted=True,
            bar_count_preserved=True,
            join_deferred_reason=None,
        )
    ]

    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=1,
        bar_month_shard_count=1,
        bar_day_shard_count=0,
        candidate_inputs=candidate_inputs,
        previews=previews,
        policy_results=policy_results,
        join_results=join_results,
        bar_size="750btc",
        max_candidate_files=720,
        preview_rows_per_file=25_000,
        max_policy_check_files=80,
    )
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
    assert "No OFI output partitions were written." in report
    assert "candidate_selection_deterministic" in report
    assert "bar_count_preserved_where_attempted" in report
    assert "## Dry-Run Scope" in report
    assert "full_bounded_manifest" in report
    assert "selected_file_count" in report
    assert "files_previewed" in report
    assert "files_policy_checked" in report


def test_report_marks_smoke_scope_and_does_not_claim_full_manifest_for_smaller_budget():
    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=0,
        bar_month_shard_count=0,
        bar_day_shard_count=0,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "## Dry-Run Scope" in report
    assert "smoke_bounded_manifest" in report
    assert "smoke_bounded_manifest_completed" in report
    assert "full_bounded_manifest_completed" not in report
    assert "max_candidate_files`: `80`" in report
    assert "preview_rows_per_file`: `5000`" in report
    assert "max_policy_check_files`: `20`" in report
    assert "This dry-run manifest does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction." in report


def test_report_marks_join_readiness_deferred_when_all_checks_are_deferred():
    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=0,
        bar_month_shard_count=0,
        bar_day_shard_count=0,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[
            script.JoinReadinessResult(
                file_date="2026-01-01",
                bar_file_found=False,
                bar_row_count=None,
                join_attempted=False,
                bar_count_preserved=None,
                join_deferred_reason="bar_file_missing",
            )
        ],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "join_readiness_deferred_bar_files_missing" in report
    assert "bar_count_preservation_not_applicable" in report
    assert "bar_count_preserved_where_attempted" not in report
    assert "bar_count_not_preserved_where_attempted" not in report
    assert "join_readiness_deferred_bar_files_missing" in report
    assert "bar_count_preservation_not_applicable" in report


def test_report_marks_bar_count_preserved_where_attempted_only_when_all_attempted_joins_preserve():
    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=1,
        bar_month_shard_count=1,
        bar_day_shard_count=0,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[
            script.JoinReadinessResult(
                file_date="2026-01-01",
                bar_file_found=True,
                bar_row_count=10,
                join_attempted=True,
                bar_count_preserved=True,
                join_deferred_reason=None,
            )
        ],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "join_readiness_checked_where_possible" in report
    assert "bar_count_preserved_where_attempted" in report
    assert "bar_count_not_preserved_where_attempted" not in report
    assert "bar_count_preservation_not_applicable" not in report


def test_report_marks_bar_count_not_preserved_where_attempted_when_any_join_fails():
    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=1,
        bar_month_shard_count=1,
        bar_day_shard_count=0,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[
            script.JoinReadinessResult(
                file_date="2026-01-01",
                bar_file_found=True,
                bar_row_count=10,
                join_attempted=True,
                bar_count_preserved=False,
                join_deferred_reason=None,
            )
        ],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "join_readiness_checked_where_possible" in report
    assert "bar_count_not_preserved_where_attempted" in report
    assert "bar_count_preserved_where_attempted" not in report
    assert "bar_count_preservation_not_applicable" not in report


def test_join_readiness_result_handles_attempted_and_deferred_without_writing(monkeypatch):
    bars = pl.DataFrame(
        {
            "open_time": [0, 1_000_000_000],
            "close_time": [1_000_000_000, 2_000_000_000],
        }
    )
    monkeypatch.setattr(script, "_find_bar_file", lambda bar_dir, symbol, bar_size, file_date: (Path("/tmp/bar.parquet"), "month") if file_date == "2026-01-01" else (None, None))
    monkeypatch.setattr(script, "_load_bar_frame", lambda path: bars)
    result = script._build_join_readiness_result(Path("/tmp"), "BTCUSDT", "750btc", "2026-01-01")
    deferred = script._build_join_readiness_result(Path("/tmp"), "BTCUSDT", "750btc", None)

    assert result.join_attempted is True
    assert result.bar_count_preserved is True
    assert deferred.join_attempted is False
    assert deferred.join_deferred_reason == "file_date_unavailable"


def test_exact_day_and_month_shard_resolution_and_no_accidental_500btc_selection(tmp_path):
    bar_dir = tmp_path / "bars"
    bar_dir.mkdir()
    day_file = bar_dir / "BTCUSDT_tier2_750btc_2025-06-28.parquet"
    month_file = bar_dir / "BTCUSDT_tier2_750btc_2025-06.parquet"
    wrong_file = bar_dir / "BTCUSDT_tier2_500btc_2025-06-28.parquet"
    pl.DataFrame({"open_time": [0], "close_time": [1]}).write_parquet(day_file)
    pl.DataFrame({"open_time": [0], "close_time": [1]}).write_parquet(month_file)
    pl.DataFrame({"open_time": [0], "close_time": [1]}).write_parquet(wrong_file)

    resolved_day, strategy_day = script._find_bar_file(bar_dir, "BTCUSDT", "750btc", "2025-06-28")
    resolved_month, strategy_month = script._find_bar_file(bar_dir, "BTCUSDT", "750btc", "2025-06-29")
    resolved_missing, strategy_missing = script._find_bar_file(bar_dir, "BTCUSDT", "750btc", "2025-07-01")
    resolved_wrong_size, _ = script._find_bar_file(bar_dir, "BTCUSDT", "500btc", "2025-06-28")

    assert resolved_day == day_file
    assert strategy_day == "day"
    assert resolved_month == month_file
    assert strategy_month == "month"
    assert resolved_missing is None
    assert strategy_missing is None
    assert resolved_wrong_size == wrong_file


def test_build_report_marks_deferred_when_no_joins_attempted_and_preservation_not_applicable():
    report = script.build_report(
        discovered_file_count=1,
        discovered_bar_count=0,
        bar_month_shard_count=0,
        bar_day_shard_count=0,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "bar_count_preservation_not_applicable" in report
    assert "bar_count_preserved_where_attempted" not in report
    assert "bar_count_not_preserved_where_attempted" not in report
    assert "join_readiness_deferred_bar_files_missing" not in report


def test_build_report_marks_month_and_day_shard_resolution_and_join_attempts(tmp_path):
    day_file = tmp_path / "BTCUSDT_tier2_750btc_2025-06-28.parquet"
    month_file = tmp_path / "BTCUSDT_tier2_750btc_2025-06.parquet"
    pl.DataFrame({"open_time": [0], "close_time": [1]}).write_parquet(day_file)
    pl.DataFrame({"open_time": [0], "close_time": [1]}).write_parquet(month_file)
    day_result = script._build_join_readiness_result(tmp_path, "BTCUSDT", "750btc", "2025-06-28")
    month_result = script._build_join_readiness_result(tmp_path, "BTCUSDT", "750btc", "2025-06-29")
    report = script.build_report(
        discovered_file_count=2,
        discovered_bar_count=2,
        bar_month_shard_count=1,
        bar_day_shard_count=1,
        candidate_inputs=[],
        previews=[],
        policy_results=[],
        join_results=[day_result, month_result],
        bar_size="750btc",
        max_candidate_files=80,
        preview_rows_per_file=5_000,
        max_policy_check_files=20,
    )
    assert "bar_month_shards_resolved" in report
    assert "bar_day_shards_resolved" in report
    assert "join_readiness_checked_where_possible" in report
    assert "bar_count_preserved_where_attempted" in report
    assert "bar_count_preservation_not_applicable" not in report
