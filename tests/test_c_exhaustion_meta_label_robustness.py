from __future__ import annotations

import math

import scripts.diagnose_c_exhaustion_meta_label_robustness as robust


def _baseline_rows() -> list[dict[str, object]]:
    return [
        {
            "test_year": 2023,
            "baseline_no_gate_test_net_expectancy_bps": -12.0,
        },
        {
            "test_year": 2024,
            "baseline_no_gate_test_net_expectancy_bps": -18.0,
        },
        {
            "test_year": 2025,
            "baseline_no_gate_test_net_expectancy_bps": -151.297784,
        },
        {
            "test_year": 2026,
            "baseline_no_gate_test_net_expectancy_bps": -18.261942,
        },
    ]


def _fold_row(model_family: str, test_year: int, delta: float, expectancy: float, kept: int, test_count: int = 20) -> dict[str, object]:
    return {
        "split": f"walk_forward_{test_year - 2022}",
        "validate_year": test_year - 1,
        "test_year": test_year,
        "model_family": model_family,
        "validate_net_expectancy_bps_if_trading_kept_signals": expectancy + 1.0,
        "test_net_expectancy_bps_if_trading_kept_signals": expectancy,
        "delta_vs_baseline_bps": delta,
        "test_kept_trade_count": kept,
        "test_removed_trade_count": max(test_count - kept, 0),
        "test_count": test_count,
        "validation_sample_too_small": False,
        "selected_threshold": 0.5,
        "model_status": "model_execution_completed",
        "train_count": 100,
        "validate_count": 20,
        "baseline_no_gate_test_net_expectancy_bps": -20.0,
        "kept_test_returns_bps": [expectancy] * max(kept, 1),
    }


def test_candidate_selection_rejects_2026_only_sample_too_small_wins():
    rows = [
        _fold_row("decision_tree_depth_3", 2023, 1.0, 5.0, 12),
        _fold_row("decision_tree_depth_3", 2024, 1.0, 6.0, 12),
        _fold_row("decision_tree_depth_3", 2025, 1.0, 7.0, 2),
        _fold_row("decision_tree_depth_3", 2026, 1.0, 8.0, 7),
    ]
    summary = robust.summarize_candidate_selection("decision_tree_depth_3", rows, _baseline_rows())

    assert summary["passes_candidate_selection_protocol"] is False
    assert summary["sample_too_small"] is True
    assert summary["recent_total_kept_trades"] == 9
    assert summary["recent_2026_delta_bps"] == 1.0


def test_candidate_selection_requires_both_2025_and_2026_improvement():
    rows = [
        _fold_row("logistic_regression_l2", 2023, 0.5, 4.0, 12),
        _fold_row("logistic_regression_l2", 2024, 0.5, 5.0, 12),
        _fold_row("logistic_regression_l2", 2025, -0.5, -2.0, 12),
        _fold_row("logistic_regression_l2", 2026, 0.5, 3.0, 12),
    ]
    summary = robust.summarize_candidate_selection("logistic_regression_l2", rows, _baseline_rows())

    assert summary["passes_candidate_selection_protocol"] is False
    assert summary["recent_2025_delta_bps"] < 0
    assert summary["recent_2026_delta_bps"] > 0


def test_psr_returns_unreliable_for_short_trade_series():
    stats = robust._trade_sharpe_and_psr([1.0, 2.0, -1.0, 0.5, 0.25, -0.75, 1.5, 0.4, -0.2])

    assert stats["trade_count"] == 9
    assert stats["psr_unreliable"] is True
    assert stats["psr_vs_zero"] is None


def test_pbo_marks_below_median_test_rank_correctly():
    fold_rows = [
        {
            "split": "walk_forward_1",
            "model_family": "logistic_regression_l2",
            "validate_net_expectancy_bps_if_trading_kept_signals": 10.0,
            "test_net_expectancy_bps_if_trading_kept_signals": -5.0,
        },
        {
            "split": "walk_forward_1",
            "model_family": "decision_tree_depth_2",
            "validate_net_expectancy_bps_if_trading_kept_signals": 8.0,
            "test_net_expectancy_bps_if_trading_kept_signals": 1.0,
        },
        {
            "split": "walk_forward_1",
            "model_family": "decision_tree_depth_3",
            "validate_net_expectancy_bps_if_trading_kept_signals": 6.0,
            "test_net_expectancy_bps_if_trading_kept_signals": 2.0,
        },
        {
            "split": "walk_forward_2",
            "model_family": "logistic_regression_l2",
            "validate_net_expectancy_bps_if_trading_kept_signals": 7.0,
            "test_net_expectancy_bps_if_trading_kept_signals": -1.0,
        },
        {
            "split": "walk_forward_2",
            "model_family": "decision_tree_depth_2",
            "validate_net_expectancy_bps_if_trading_kept_signals": 9.0,
            "test_net_expectancy_bps_if_trading_kept_signals": 4.0,
        },
        {
            "split": "walk_forward_2",
            "model_family": "decision_tree_depth_3",
            "validate_net_expectancy_bps_if_trading_kept_signals": 5.0,
            "test_net_expectancy_bps_if_trading_kept_signals": 3.0,
        },
    ]

    summary = robust.compute_pbo_scaffold(fold_rows)

    assert summary["pbo_fold_count"] == 2
    assert summary["pbo_bad_fold_count"] == 1
    assert math.isclose(summary["pbo_rate"], 0.5)
    assert summary["fold_summaries"][0]["below_median_on_test"] is True


def test_decision_never_emits_production_approval():
    decision = robust.build_decision([], [], {"pbo_low_power": True})

    assert decision["production_status"] == "production_invalid"
    assert decision["paper_live_status"] == "paper_live_blocked"
    assert all("production_valid" not in line for line in decision["decision_lines"])
