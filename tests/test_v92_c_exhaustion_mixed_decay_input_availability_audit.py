from __future__ import annotations

from pathlib import Path

from scripts.v92_c_exhaustion_mixed_decay_input_availability_audit import build_report


def test_report_builds_from_real_inputs():
    report, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    assert "V9.2 Hermes C Exhaustion Mixed Decay Input Availability Audit" in report
    assert "## Field Availability Table" in report
    assert meta["decision"] in {
        "proceed_to_enriched_signal_regime_decay_diagnostic_design_only",
        "keep_anchor_alive_but_data_insufficient",
        "reject_anchor_due_to_unrecoverable_missing_inputs",
        "blocked_due_to_missing_required_inputs",
    }
    assert len(meta["safe_available"]) >= 1
    assert len(meta["reconstructable_without_leakage"]) >= 1


def test_classification_counts_are_reasonable():
    _, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    assert len(meta["safe_available"]) >= 6
    assert len(meta["safe_partial"]) >= 1
    assert len(meta["reconstructable_without_leakage"]) >= 4
    assert len(meta["blocked"]) >= 6


def test_enriched_diagnostic_design_is_allowed():
    _, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    assert meta["allowed"] is True
