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
    trade_count = 100.0 + pd.Series(range(60), dtype="float64")
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
            "trade_count": trade_count,
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


def test_period_assignment_tracks_entry_time_year_boundary() -> None:
    bars = _sample_bars()
    trades = _sample_trades()

    current = diag._build_context(trades, bars)
    assert int(current.loc[0, "year"]) == 2024
    assert current.loc[0, "period"] == "historical"

    shifted = trades.copy()
    for col in ["signal_time", "entry_time", "exit_time"]:
        shifted[col] = pd.to_datetime(shifted[col]) + pd.Timedelta(days=366)
    shifted["year"] = 2025
    future = diag._build_context(shifted, bars)
    assert int(future.loc[0, "year"]) == 2025
    assert future.loc[0, "period"] == "recent"


def test_field_coverage_requires_non_null_values() -> None:
    bars = _sample_bars()
    trades = _sample_trades()
    frame = diag._build_context(trades, bars)
    rows, available_fields, missing_fields, used_fields, blocked_fields = diag._field_availability_rows(frame)
    by_field = {row["field"]: row for row in rows}

    for field in ["trade_density", "distance_from_recent_high_low", "weekday_weekend_effect"]:
        row = by_field[field]
        assert row["non_null_count"] > 0
        assert row["status"] in {"available", "available_partial"}

    for row in rows:
        if row["status"] in {"available", "available_partial"}:
            assert row["non_null_count"] > 0

    assert "trade_density" in available_fields
    assert "distance_from_recent_high_low" in available_fields
    assert "weekday_weekend_effect" in available_fields
    assert "trade_density" in used_fields
    assert "distance_from_recent_high_low" in used_fields
    assert "weekday_weekend_effect" in used_fields
    assert "raw L2" in blocked_fields
    assert "OFI" in blocked_fields
    assert "row-level export" in blocked_fields
    assert "trade_density" not in missing_fields
    assert "distance_from_recent_high_low" not in missing_fields
    assert "weekday_weekend_effect" not in missing_fields


def test_bucket_coverage_is_not_all_na_when_source_exists() -> None:
    bars = _sample_bars()
    trades = _sample_trades()
    frame = diag._build_context(trades, bars)

    trade_density_rows = diag._bucket_rows(frame, "trade_density_bucket")
    distance_rows = diag._bucket_rows(frame, "distance_from_recent_high_low_bucket")
    weekday_rows = diag._bucket_rows(frame, "weekday_weekend_effect")

    assert any(row["historical_count"] > 0 or row["recent_count"] > 0 for row in trade_density_rows if row["bucket"] != "n/a")
    assert any(row["historical_count"] > 0 or row["recent_count"] > 0 for row in distance_rows if row["bucket"] != "n/a")
    assert any(row["historical_count"] > 0 or row["recent_count"] > 0 for row in weekday_rows if row["bucket"] in {"weekday", "weekend"})


def test_weekday_weekend_effect_is_derived_from_entry_context() -> None:
    bars = _sample_bars()
    trades = _sample_trades()
    frame = diag._build_context(trades, bars)

    assert frame["weekday_weekend_effect"].notna().all()
    assert set(frame["weekday_weekend_effect"].unique()) <= {"weekday", "weekend"}


def test_build_report_smoke(monkeypatch) -> None:
    bars = _sample_bars()
    trades = _sample_trades()

    monkeypatch.setattr(diag, "_parse_trade_frame", lambda _: trades.copy())
    monkeypatch.setattr(diag, "load_750btc_bars", lambda _: bars)
    monkeypatch.setattr(diag, "normalize_v92_bar_timestamps", lambda df: df)
    monkeypatch.setattr(diag, "add_v92_regime_labels", lambda df: df)

    report, metadata = diag.build_report(Path("trade_log.csv"), Path("bars"))
    assert "V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic" in report
    assert "## Stop / Go Conclusion" in report
    assert "no raw L2 is read" in report
    assert "OFI is not generated" in report
    assert "no row-level artifacts are exported" in report
    assert metadata["total_trades"] == 1
    assert metadata["decision"] in {
        "proceed_to_preregistered_richer_context_filter_design_only",
        "keep_anchor_alive_but_collect_more_inputs",
        "reject_c_exhaustion_anchor_as_unexplained_recent_decay",
        "blocked_due_to_missing_required_inputs",
    }
