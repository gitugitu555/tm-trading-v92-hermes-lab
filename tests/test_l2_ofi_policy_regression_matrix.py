from __future__ import annotations

from pathlib import Path

import scripts.validate_l2_ofi_policy_regression_matrix as script


def _candidate(group_name: str, suffix: str) -> script.CandidateFile:
    return script.CandidateFile(path=Path(f"/tmp/{suffix}.parquet.zst"), group_name=group_name)


def _result(
    *,
    group_name: str,
    all_segments_clean: bool,
    source_gap_boundary_count: int = 0,
    snapshot_bridge_event_count: int = 0,
    quarantined_segment_count: int = 0,
    quarantined_segment_ofi_emitted_count: int = 0,
    total_sequence_gap_count: int = 0,
) -> script.CandidateResult:
    return script.CandidateResult(
        group_name=group_name,
        file_path=f"/tmp/{group_name}.parquet.zst",
        file_date="2026-01-01",
        file_hour="00",
        rows_scanned=100,
        packet_count=10,
        segment_count=1,
        meaningful_segment_count=1,
        clean_segment_count=1 if all_segments_clean else 0,
        dirty_segment_count=0 if all_segments_clean else 1,
        all_segments_clean=all_segments_clean,
        source_gap_boundary_count=source_gap_boundary_count,
        snapshot_like_packet_count=1 if group_name == "snapshot_reset_bridge" else 0,
        snapshot_bridge_event_count=snapshot_bridge_event_count,
        snapshot_reset_clean_seed_count=snapshot_bridge_event_count,
        snapshot_reset_chain_failure_count=0 if snapshot_bridge_event_count > 0 else quarantined_segment_count,
        quarantined_segment_count=quarantined_segment_count,
        total_ofi_emitted_count=9,
        total_warmup_none_count=1,
        total_sequence_gap_count=total_sequence_gap_count,
        ofi_suppressed_due_to_snapshot_bridge_count=snapshot_bridge_event_count,
        ofi_suppressed_due_to_quarantine_count=quarantined_segment_count,
        side_mapping_unknown_count=0,
        policy_module_used_directly=True,
        quarantined_segment_ofi_emitted_count=quarantined_segment_ofi_emitted_count,
    )


def test_default_candidate_groups_include_expected_group_names():
    candidates = script.build_candidate_inputs(None)
    assert {candidate.group_name for candidate in candidates} == {
        "original_sample",
        "source_gap_heavy",
        "snapshot_reset_bridge",
    }


def test_group_level_regression_status_passes_and_fails_by_rules():
    candidate_inputs = [
        _candidate("original_sample", "original"),
        _candidate("source_gap_heavy", "source_gap"),
        _candidate("snapshot_reset_bridge", "bridge"),
    ]
    results = [
        _result(group_name="original_sample", all_segments_clean=True),
        _result(group_name="source_gap_heavy", all_segments_clean=True, source_gap_boundary_count=2),
        _result(group_name="snapshot_reset_bridge", all_segments_clean=True, snapshot_bridge_event_count=1, quarantined_segment_count=0),
    ]

    summaries = {summary.group_name: summary for summary in script.build_group_summaries(candidate_inputs, results)}
    assert summaries["original_sample"].regression_status == "passed"
    assert summaries["source_gap_heavy"].regression_status == "passed"
    assert summaries["snapshot_reset_bridge"].regression_status == "passed"

    failing_results = [
        _result(group_name="original_sample", all_segments_clean=True),
        _result(group_name="source_gap_heavy", all_segments_clean=True, source_gap_boundary_count=0),
        _result(group_name="snapshot_reset_bridge", all_segments_clean=True, snapshot_bridge_event_count=1, quarantined_segment_count=0),
    ]
    failing_summaries = {summary.group_name: summary for summary in script.build_group_summaries(candidate_inputs, failing_results)}
    assert failing_summaries["source_gap_heavy"].regression_status == "failed"


def test_source_gap_heavy_requires_boundaries_and_snapshot_bridge_requires_clean_bridge_and_no_quarantine():
    candidate_inputs = [
        _candidate("source_gap_heavy", "source_gap"),
        _candidate("snapshot_reset_bridge", "bridge"),
    ]
    results = [
        _result(group_name="source_gap_heavy", all_segments_clean=True, source_gap_boundary_count=0),
        _result(group_name="snapshot_reset_bridge", all_segments_clean=False, snapshot_bridge_event_count=1, quarantined_segment_count=1),
    ]
    summaries = {summary.group_name: summary for summary in script.build_group_summaries(candidate_inputs, results)}

    assert summaries["source_gap_heavy"].regression_status == "failed"
    assert summaries["snapshot_reset_bridge"].regression_status == "failed"


def test_report_does_not_claim_all_passed_when_a_group_fails():
    candidate_inputs = [
        _candidate("original_sample", "original"),
        _candidate("source_gap_heavy", "source_gap"),
        _candidate("snapshot_reset_bridge", "bridge"),
    ]
    results = [
        _result(group_name="original_sample", all_segments_clean=True),
        _result(group_name="source_gap_heavy", all_segments_clean=True, source_gap_boundary_count=0),
        _result(group_name="snapshot_reset_bridge", all_segments_clean=True, snapshot_bridge_event_count=1, quarantined_segment_count=0),
    ]
    report = script.build_report(candidate_inputs=candidate_inputs, results=results, max_events_per_file=75000)

    assert "At least one bounded candidate group failed the regression matrix" in report
    assert "source_gap_heavy_regression_failed" in report
    assert "source_gap_heavy_regression_passed" not in report
    assert script.PRODUCTION_APPROVAL_STATEMENT in report


def test_report_includes_conservative_decision_labels():
    candidate_inputs = [
        _candidate("original_sample", "original"),
        _candidate("source_gap_heavy", "source_gap"),
        _candidate("snapshot_reset_bridge", "bridge"),
    ]
    results = [
        _result(group_name="original_sample", all_segments_clean=True),
        _result(group_name="source_gap_heavy", all_segments_clean=True, source_gap_boundary_count=2),
        _result(group_name="snapshot_reset_bridge", all_segments_clean=True, snapshot_bridge_event_count=1, quarantined_segment_count=0),
    ]
    report = script.build_report(candidate_inputs=candidate_inputs, results=results, max_events_per_file=75000)

    assert "candidate_groups_deterministic" in report
    assert "original_sample_regression_passed" in report
    assert "source_gap_heavy_regression_passed" in report
    assert "source_gap_boundaries_preserved" in report
    assert "snapshot_bridge_events_detected" in report
    assert "snapshot_reset_bridge_regression_passed" in report
    assert "no_invalid_snapshot_reset_chains_quarantined" in report
    assert "quarantined_segments_emit_no_ofi" in report
    assert "This regression matrix does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction." in report
