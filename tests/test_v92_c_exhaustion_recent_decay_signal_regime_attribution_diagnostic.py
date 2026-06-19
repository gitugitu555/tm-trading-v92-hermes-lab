from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from scripts.v92_c_exhaustion_recent_decay_signal_regime_attribution_diagnostic import (
    build_report,
    evaluate_diagnostic,
    _synthetic_causality_tests,
)


def _synthetic_trade_and_bars() -> tuple[pd.DataFrame, pl.DataFrame]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pl.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 111, 110, 108, 106, 104, 103, 102, 101], dtype=float),
            "low": np.full(20, 99.0),
            "close": np.array([100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 104, 103.5, 102, 101, 100, 99.5, 99, 98.5, 98], dtype=float),
            "volume": np.full(20, 1_000.0),
            "regime": ["EXHAUSTED"] * 20,
            "bar_range": np.full(20, 1.0),
            "body_size": np.full(20, 0.5),
            "rv_1d": np.full(20, 0.01),
            "rv_15th_pct": np.full(20, 0.02),
            "adr_stretch": np.linspace(0.1, 0.9, 20),
        }
    )
    trades = pd.DataFrame(
        {
            "signal_index": [0],
            "entry_index": [1],
            "exit_index": [18],
            "signal_time": [base_times[1]],
            "entry_time": [base_times[1]],
            "exit_time": [base_times[18]],
            "entry_price": [100.0],
            "exit_price": [100.0],
            "gross_return_bps": [0.0],
            "net_return_bps": [-1.0],
            "holding_bars": [17],
            "year": [2024],
        }
    )
    return trades, bars


def test_future_bars_do_not_change_period_or_signal_context():
    trades, bars = _synthetic_trade_and_bars()
    base = evaluate_diagnostic(trades, bars)

    future_pdf = bars.to_pandas()
    future_pdf.loc[future_pdf.index >= 18, "high"] = 9999.0
    future_pdf.loc[future_pdf.index >= 18, "close"] = 9998.0
    future = pl.from_pandas(future_pdf)
    result = evaluate_diagnostic(trades, future)

    assert base.loc[0, "period"] == result.loc[0, "period"] == "historical"
    assert base.loc[0, "realized_vol_24_bars_bps_bucket"] == result.loc[0, "realized_vol_24_bars_bps_bucket"]
    assert base.loc[0, "range_expansion_ratio_24_bucket"] == result.loc[0, "range_expansion_ratio_24_bucket"]
    assert base.loc[0, "body_to_range_ratio_bucket"] == result.loc[0, "body_to_range_ratio_bucket"]


def test_return_mutation_does_not_change_context_fields():
    trades, bars = _synthetic_trade_and_bars()
    base = evaluate_diagnostic(trades, bars)

    mutated = trades.copy()
    mutated["gross_return_bps"] = 9999.0
    mutated["net_return_bps"] = 9998.0
    result = evaluate_diagnostic(mutated, bars)

    assert base.loc[0, "period"] == result.loc[0, "period"]
    assert base.loc[0, "realized_vol_24_bars_bps_bucket"] == result.loc[0, "realized_vol_24_bars_bps_bucket"]
    assert base.loc[0, "cost_drag_bps"] == 1.0
    assert result.loc[0, "cost_drag_bps"] == 1.0


def test_report_builds_from_real_inputs():
    report, meta = build_report(
        Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"),
        Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
    )

    assert "V9.2 Hermes C Exhaustion Recent Decay Signal Regime Attribution Diagnostic" in report
    assert "## Period Comparison" in report
    assert meta["decision"] in {
        "reject_c_exhaustion_anchor_as_recently_unrepairable",
        "proceed_to_regime_filtered_preregistration_design_only",
        "proceed_to_signal_state_filter_preregistration_design_only",
        "proceed_to_cost_robustness_preregistration_design_only",
        "keep_research_anchor_alive_but_collect_more_inputs",
        "blocked_due_to_missing_required_inputs",
    }


def test_synthetic_causality_checks_pass():
    results = _synthetic_causality_tests()
    assert results
    assert all(item.passed for item in results)
