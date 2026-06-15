from __future__ import annotations

import pandas as pd

from scripts.diagnose_c_exhaustion_ex_ante_proxy_gate_matrix import (
    compute_stability_flags,
    rank_candidates,
    summarize_candidate_period,
)


def _make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "net_return_bps": [10.0, -5.0, 20.0, -15.0],
            "bad_context_label_36": [False, True, False, True],
            "trend_continuation_flag_36": [False, True, False, False],
            "failed_reversal_flag_36": [False, False, False, True],
            "pre_signal_return_24_bars_bps": [-100.0, -300.0, -150.0, -50.0],
            "pre_signal_return_36_bars_bps": [-120.0, -400.0, -180.0, -90.0],
            "body_to_range_ratio": [0.60, 0.80, 0.70, 0.90],
            "range_expansion_ratio_24": [1.10, 1.60, 1.30, 1.80],
            "range_expansion_ratio_36": [1.05, 1.40, 1.20, 1.70],
            "realized_vol_24_bars_bps": [40.0, 60.0, 45.0, 80.0],
            "realized_vol_36_bars_bps": [35.0, 55.0, 42.0, 75.0],
            "adr_stretch": [0.80, 0.96, 0.70, 1.10],
            "close_vs_local_low_bps": [-20.0, -75.0, -40.0, -10.0],
        }
    )


def test_summarize_candidate_period_counts_pre_filter_rows():
    frame = _make_frame()
    summary = summarize_candidate_period(frame, "body_to_range_lt_0_75", period="all_period")

    assert summary["input_trade_count"] == 4
    assert summary["kept_trade_count"] == 2
    assert summary["removed_trade_count"] == 2
    assert summary["kept_rate"] == 0.5


def test_baseline_keeps_all_rows():
    frame = _make_frame()
    summary = summarize_candidate_period(frame, "baseline_no_gate", period="all_period")

    assert summary["input_trade_count"] == 4
    assert summary["kept_trade_count"] == 4
    assert summary["removed_trade_count"] == 0
    assert summary["kept_rate"] == 1.0


def test_stability_flags_and_ranking_use_recent_period_sign():
    period_rows = [
        {"candidate": "cand_a", "period": "early_period", "net_expectancy_bps": 10.0, "kept_trade_count": 12},
        {"candidate": "cand_a", "period": "middle_period", "net_expectancy_bps": 5.0, "kept_trade_count": 11},
        {"candidate": "cand_a", "period": "recent_period", "net_expectancy_bps": -1.0, "kept_trade_count": 10},
    ]
    flags = compute_stability_flags(period_rows)

    assert flags["early_positive"] is True
    assert flags["middle_positive"] is True
    assert flags["recent_positive"] is False
    assert flags["positive_all_periods"] is False
    assert flags["min_period_trade_count"] == 10
    assert flags["sample_too_small"] is False

    rows = [
        {
            "candidate": "cand_bad_recent",
            "family": "test",
            "net_expectancy_bps": 100.0,
            "bad_context_reduction_vs_baseline": 0.5,
            "kept_trade_count": 20,
            "removed_trade_count": 1,
            "kept_rate": 0.95,
            "early_positive": True,
            "middle_positive": True,
            "recent_positive": False,
            "positive_all_periods": False,
            "min_period_trade_count": 10,
            "sample_too_small": False,
        },
        {
            "candidate": "cand_good",
            "family": "test",
            "net_expectancy_bps": 50.0,
            "bad_context_reduction_vs_baseline": 0.1,
            "kept_trade_count": 18,
            "removed_trade_count": 2,
            "kept_rate": 0.9,
            "early_positive": True,
            "middle_positive": True,
            "recent_positive": True,
            "positive_all_periods": True,
            "min_period_trade_count": 12,
            "sample_too_small": False,
        },
    ]

    ranked = rank_candidates(rows)

    assert ranked[0]["candidate"] == "cand_good"
    assert ranked[0]["positive_all_periods"] is True
    assert ranked[1]["positive_all_periods"] is False
