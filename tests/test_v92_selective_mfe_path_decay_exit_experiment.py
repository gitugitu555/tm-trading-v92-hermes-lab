from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import _load_bars, _parse_trade_frame
from scripts.v92_selective_mfe_path_decay_exit_experiment import build_report, evaluate_selective_decay_experiment


def _synthetic_trade_and_bars() -> tuple[pd.DataFrame, pd.DataFrame]:
    base_times = pd.date_range("2024-01-01", periods=20, freq="5min")
    bars = pd.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": np.full(20, 100.0),
            "high": np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 111, 110, 108, 106, 104, 103, 102, 101], dtype=float),
            "low": np.full(20, 99.0),
            "close": np.array([100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 104, 103.5, 102, 101, 100, 99.5, 99, 98.5, 98], dtype=float),
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


def test_future_bars_do_not_change_eligibility():
    trades, bars = _synthetic_trade_and_bars()
    base = evaluate_selective_decay_experiment(trades, bars)
    future = bars.copy()
    future.loc[18:, "high"] = 9999.0
    future.loc[18:, "close"] = 9998.0
    result = evaluate_selective_decay_experiment(trades, future)

    assert bool(base.loc[0, "selective_eligible"]) == bool(result.loc[0, "selective_eligible"])
    assert base.loc[0, "current_return_at_trigger_bps"] == result.loc[0, "current_return_at_trigger_bps"]
    assert base.loc[0, "giveback_depth_at_trigger_bps"] == result.loc[0, "giveback_depth_at_trigger_bps"]


def test_original_exit_labels_do_not_change_eligibility():
    trades, bars = _synthetic_trade_and_bars()
    base = evaluate_selective_decay_experiment(trades, bars)
    mutated = trades.copy()
    mutated["exit_price"] = 9999.0
    mutated["gross_return_bps"] = 99999.0
    mutated["net_return_bps"] = 99988.0
    result = evaluate_selective_decay_experiment(mutated, bars)

    assert bool(base.loc[0, "selective_eligible"]) == bool(result.loc[0, "selective_eligible"])
    assert base.loc[0, "trigger_offset_bars"] == result.loc[0, "trigger_offset_bars"]
    assert base.loc[0, "current_return_at_trigger_bps"] == result.loc[0, "current_return_at_trigger_bps"]


def test_report_builds_from_real_inputs():
    trades = _parse_trade_frame(Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"))
    bars, _ = _load_bars(Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"))
    report, meta = build_report(Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"), Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"))

    assert "selective_mfe_path_decay_exit_experiment" in report
    assert meta["decision"] in {
        "reject_selective_mfe_path_decay_exit_rule",
        "keep_selective_exit_hypothesis_alive_but_do_not_patch",
        "proceed_to_core_patch_design_review_only",
    }
    assert len(trades) == 310
    assert bars.shape[0] > 0
