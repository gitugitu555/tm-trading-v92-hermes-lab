from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl

import scripts.v92_c_exhaustion_vwap_distance_context_stability_diagnostic as diag


def _sample_bars() -> pl.DataFrame:
    base_times = pd.date_range("2024-01-01", periods=60, freq="5min")
    opens = 100.0 + pd.Series(range(60), dtype="float64") * 0.5
    highs = opens + 1.5
    lows = opens - 1.0
    closes = opens + 0.25
    volume = 1000.0 + pd.Series(range(60), dtype="float64") * 10.0
    volume_delta = pd.Series(range(-30, 30), dtype="float64")
    vwap = opens + 0.1
    return pl.DataFrame(
        {
            "open_time": base_times,
            "close_time": base_times + pd.Timedelta(minutes=5),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "bar_range": highs - lows,
            "body_size": closes - opens,
            "adr_stretch": pd.Series(range(60), dtype="float64") / 100.0,
            "rv_1d": 10.0 + pd.Series(range(60), dtype="float64") * 0.1,
            "rv_15th_pct": 8.0 + pd.Series(range(60), dtype="float64") * 0.05,
            "vwap": vwap,
            "volume": volume,
            "volume_delta": volume_delta,
            "regime": ["EXHAUSTED"] * 60,
        }
    )


def _sample_trades() -> pd.DataFrame:
    bars = _sample_bars().to_pandas()
    return pd.DataFrame(
        {
            "signal_index": [25, 30],
            "entry_index": [26, 31],
            "exit_index": [35, 40],
            "signal_time": [bars.loc[25, "close_time"], bars.loc[30, "close_time"]],
            "entry_time": [bars.loc[26, "open_time"], bars.loc[31, "open_time"]],
            "exit_time": [bars.loc[35, "open_time"], bars.loc[40, "open_time"]],
            "entry_price": [float(bars.loc[26, "open"]), float(bars.loc[31, "open"])],
            "exit_price": [float(bars.loc[35, "open"]), float(bars.loc[40, "open"])],
            "gross_return_bps": [120.0, -80.0],
            "net_return_bps": [115.0, -85.0],
            "year": [2024, 2025],
            "excursion_class": ["clean_winner", "giveback_loss"],
        }
    )


def test_bucket_distance_from_vwap_is_preregistered() -> None:
    assert diag._bucket_distance_from_vwap(-150.0) == "below -100 bps"
    assert diag._bucket_distance_from_vwap(-50.0) == "-100 to -25 bps"
    assert diag._bucket_distance_from_vwap(0.0) == "-25 to +25 bps"
    assert diag._bucket_distance_from_vwap(75.0) == "+25 to +100 bps"
    assert diag._bucket_distance_from_vwap(150.0) == "above +100 bps"


def test_synthetic_causality_checks_all_pass() -> None:
    results = diag._synthetic_causality_tests()
    assert results
    assert all(result.passed for result in results)


def test_build_report_smoke(monkeypatch) -> None:
    bars = _sample_bars()
    trades = _sample_trades()

    monkeypatch.setattr(diag, "_parse_trade_frame", lambda _: trades.copy())
    monkeypatch.setattr(diag, "load_750btc_bars", lambda _: bars)
    monkeypatch.setattr(diag, "normalize_v92_bar_timestamps", lambda df: df)
    monkeypatch.setattr(diag, "add_v92_regime_labels", lambda df: df)

    report, metadata = diag.build_report(Path("trade_log.csv"), Path("bars"))
    assert "VWAP Distance Context Stability Diagnostic" in report
    assert "## Stop / Go Conclusion" in report
    assert metadata["total_trades"] == 2
    assert metadata["target_recent_count"] >= 0
    assert metadata["decision"] in {
        "proceed_to_vwap_context_filter_preregistration_design_only",
        "keep_anchor_alive_but_collect_more_inputs",
        "reject_vwap_context_followup",
        "blocked_due_to_missing_required_inputs",
    }
