from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl

import scripts.v92_c_exhaustion_richer_context_enriched_decay_diagnostic as diag


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
            "signal_index": [25],
            "entry_index": [26],
            "exit_index": [35],
            "signal_time": [bars.loc[25, "close_time"]],
            "entry_time": [bars.loc[26, "open_time"]],
            "exit_time": [bars.loc[35, "open_time"]],
            "entry_price": [float(bars.loc[26, "open"])],
            "exit_price": [float(bars.loc[35, "open"])],
            "gross_return_bps": [120.0],
            "net_return_bps": [115.0],
            "year": [2024],
            "excursion_class": ["clean_winner"],
        }
    )


def _sample_context() -> pd.DataFrame:
    entry_times = pd.to_datetime(
        [
            "2024-01-01 01:00:00",
            "2024-01-01 09:00:00",
            "2024-01-01 14:30:00",
            "2024-01-01 18:00:00",
            "2025-01-01 02:00:00",
            "2025-01-01 10:00:00",
            "2025-01-01 15:00:00",
            "2025-01-01 20:00:00",
        ]
    )
    return pd.DataFrame(
        {
            "signal_index": list(range(8)),
            "entry_time": entry_times,
            "signal_time": entry_times - pd.Timedelta(minutes=5),
            "year": [2024, 2024, 2024, 2024, 2025, 2025, 2025, 2025],
            "gross_return_bps": [140.0, 80.0, -60.0, -120.0, 30.0, -40.0, -90.0, 20.0],
            "net_return_bps": [135.0, 75.0, -65.0, -125.0, 25.0, -45.0, -95.0, 15.0],
            "original_return_bps": [140.0, 80.0, -60.0, -120.0, 30.0, -40.0, -90.0, 20.0],
            "bar_size": [750] * 8,
            "horizon": [36] * 8,
            "side": ["long-only (assumed; side column absent)"] * 8,
            "trade_density": [10.0, 20.0, 30.0, 12.0, 15.0, 25.0, 35.0, 40.0],
            "trade_density_bucket": ["low", "low", "medium", "low", "medium", "medium", "high", "high"],
            "distance_from_recent_high_low": [0.1, 0.5, 0.9, 0.4, 0.2, 0.7, 0.8, 0.95],
            "distance_from_recent_high_low_bucket": ["near recent low", "middle range", "near recent high", "middle range", "near recent low", "middle range", "near recent high", "near recent high"],
            "local_trend_range_state": ["range", "range_expansion", "failed_reversal", "trend_continuation", "range", "mixed", "range", "range_expansion"],
            "distance_from_vwap": [-120.0, -80.0, -10.0, 40.0, -90.0, -20.0, 60.0, 150.0],
            "distance_from_vwap_bucket": ["below -100 bps", "-100 to -25 bps", "-25 to +25 bps", "+25 to +100 bps", "-100 to -25 bps", "-25 to +25 bps", "+25 to +100 bps", "above +100 bps"],
            "prior_bar_return_path": [-50.0, -5.0, 10.0, 45.0, 30.0, -35.0, 0.0, 20.0],
            "prior_bar_return_path_bucket": ["negative", "flat", "flat", "positive", "positive", "negative", "flat", "flat"],
            "cvd_delta": [-5.0, 0.0, 7.0, -3.0, 2.0, -8.0, 4.0, 1.0],
            "cvd_delta_bucket": ["negative", "neutral", "positive", "negative", "positive", "negative", "positive", "positive"],
            "session_time_of_day_labels": ["asia", "europe", "overlap", "us", "asia", "europe", "overlap", "us"],
            "weekday_weekend_effect": ["weekday", "weekday", "weekday", "weekday", "weekday", "weekday", "weekday", "weekday"],
            "volatility_label": ["<25", "25-50", "50-100", ">100", "<25", "25-50", "50-100", ">100"],
            "range_trend_label": ["range", "range_expansion", "failed_reversal", "trend_continuation", "range", "mixed", "range", "range_expansion"],
            "regime_label": ["EXHAUSTED"] * 8,
            "signal_state": ["c_signal"] * 8,
            "exit_class": ["clean_winner", "clean_winner", "giveback_loss", "giveback_loss", "weak_positive_exit", "weak_positive_exit", "clean_winner", "giveback_loss"],
            "mfe_bps": [300.0, 250.0, 220.0, 210.0, 180.0, 170.0, 260.0, 230.0],
            "mae_bps": [-40.0, -35.0, -60.0, -80.0, -30.0, -55.0, -45.0, -70.0],
        }
    )


def test_bucket_helpers_cover_preregistered_bins() -> None:
    assert diag._bucket_distance_from_vwap(-101.0) == "below -100 bps"
    assert diag._bucket_distance_from_vwap(-50.0) == "-100 to -25 bps"
    assert diag._bucket_distance_from_vwap(0.0) == "-25 to +25 bps"
    assert diag._bucket_distance_from_vwap(80.0) == "+25 to +100 bps"
    assert diag._bucket_distance_from_vwap(101.0) == "above +100 bps"

    assert diag._bucket_recent_range_position(0.10) == "near recent low"
    assert diag._bucket_recent_range_position(0.50) == "middle range"
    assert diag._bucket_recent_range_position(0.90) == "near recent high"

    assert diag._bucket_trade_density(10.0, 12.0, 20.0) == "low"
    assert diag._bucket_trade_density(18.0, 12.0, 20.0) == "medium"
    assert diag._bucket_trade_density(30.0, 12.0, 20.0) == "high"

    assert diag._bucket_weekday_weekend(pd.Timestamp("2024-01-01 02:00:00")) == "weekday"
    assert diag._bucket_weekday_weekend(pd.Timestamp("2024-01-06 02:00:00")) == "weekend"

    assert diag._bucket_cvd(-1.0) == "negative"
    assert diag._bucket_cvd(0.0) == "neutral"
    assert diag._bucket_cvd(1.0) == "positive"


def test_synthetic_causality_checks_all_pass() -> None:
    results = diag._synthetic_causality_tests()
    assert results
    assert all(result.passed for result in results)


def test_build_report_smoke(monkeypatch) -> None:
    bars = _sample_bars()
    trades = _sample_trades()
    context = _sample_context()

    monkeypatch.setattr(diag, "_parse_trade_frame", lambda _: trades.copy())
    monkeypatch.setattr(diag, "load_750btc_bars", lambda _: bars)
    monkeypatch.setattr(diag, "normalize_v92_bar_timestamps", lambda df: df)
    monkeypatch.setattr(diag, "add_v92_regime_labels", lambda df: df)
    monkeypatch.setattr(diag, "_build_context", lambda _trades, _bars: context.copy())

    report, metadata = diag.build_report(Path("trade_log.csv"), Path("bars"))
    assert "V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic" in report
    assert "## Stop / Go Conclusion" in report
    assert metadata["total_trades"] == len(context)
    assert metadata["decision"] in {
        "proceed_to_preregistered_richer_context_filter_design_only",
        "keep_anchor_alive_but_collect_more_inputs",
        "reject_c_exhaustion_anchor_as_unexplained_recent_decay",
        "blocked_due_to_missing_required_inputs",
    }
