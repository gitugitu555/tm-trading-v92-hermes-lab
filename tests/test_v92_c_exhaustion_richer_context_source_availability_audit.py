from __future__ import annotations

from pathlib import Path

from scripts.v92_c_exhaustion_richer_context_source_availability_audit import build_report


def test_report_builds_from_real_inputs():
    report, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    assert "V9.2 Hermes C Exhaustion Richer Context Source Availability Audit" in report
    assert "## Classification Table" in report
    assert meta["decision"] == "proceed_to_richer_context_enriched_decay_diagnostic_design_only"
    assert len(meta["safe_available"]) >= 4
    assert len(meta["safe_partial"]) >= 1
    assert len(meta["reconstructable_without_leakage"]) >= 4
    assert len(meta["blocked"]) >= 8


def test_richer_context_counts_are_reasonable():
    _, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    counts = meta["counts"]
    assert counts["safe_available"] >= 4
    assert counts["safe_partial"] >= 1
    assert counts["reconstructable_without_leakage"] >= 4
    assert counts["blocked"] >= 8
    assert meta["allowed"] is True
