from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.v92_fixed_running_mfe_giveback_protection_experiment import (
    MIN_COMPLETED_BARS,
    build_report,
    evaluate_experiment,
)


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


def test_future_bars_do_not_change_trigger():
    trades, bars = _synthetic_trade_and_bars()
    baseline = evaluate_experiment(trades, bars)
    bars_future = bars.copy()
    bars_future.loc[18:, "high"] = 9999.0
    bars_future.loc[18:, "close"] = 9998.0
    future = evaluate_experiment(trades, bars_future)

    assert bool(baseline.loc[0, "triggered"])
    assert bool(future.loc[0, "triggered"])
    assert baseline.loc[0, "trigger_completed_bars"] == future.loc[0, "trigger_completed_bars"]
    assert baseline.loc[0, "synthetic_exit_price"] == future.loc[0, "synthetic_exit_price"]


def test_minimum_delay_blocks_early_trigger():
    trades, bars = _synthetic_trade_and_bars()
    bars.loc[: MIN_COMPLETED_BARS - 2, "high"] = 200.0
    bars.loc[: MIN_COMPLETED_BARS - 2, "close"] = 199.0
    result = evaluate_experiment(trades, bars)

    assert bool(result.loc[0, "triggered"])
    assert result.loc[0, "trigger_completed_bars"] >= MIN_COMPLETED_BARS


def test_no_activation_means_no_trigger():
    trades, bars = _synthetic_trade_and_bars()
    bars.loc[1:17, "high"] = 100.2
    bars.loc[1:17, "close"] = 99.8
    result = evaluate_experiment(trades, bars)

    assert not bool(result.loc[0, "activated"])
    assert not bool(result.loc[0, "triggered"])
