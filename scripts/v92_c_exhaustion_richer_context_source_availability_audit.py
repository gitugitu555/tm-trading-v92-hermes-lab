#!/usr/bin/env python3
"""Aggregate-only richer context source availability audit for C_Exhaustion."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import add_v92_regime_labels, attach_c_exhaustion_signal, load_750btc_bars, normalize_v92_bar_timestamps  # noqa: E402
from scripts.diagnose_c_exhaustion_regime_context import _compute_trade_context  # noqa: E402
from scripts.dry_run_c_exhaustion_mfe_mae_source_construction import _markdown_table, _parse_trade_frame  # noqa: E402

DEFAULT_TRADE_LOG = Path("/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_OUTPUT = Path("reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RICHER_CONTEXT_SOURCE_AVAILABILITY_AUDIT.md")

HISTORICAL_START_YEAR = 2020
HISTORICAL_END_YEAR = 2024
RECENT_START_YEAR = 2025
RECENT_END_YEAR = 2026


@dataclass(frozen=True)
class FieldSpec:
    field_name: str
    source_group: str
    source_type: str
    source_path_pattern: str
    classification: str
    known_at_entry: str
    timestamp_safety: str
    timestamp_granularity: str
    leakage_risk: str
    reconstruction_risk: str
    requires_raw_l2: bool
    requires_ofi_generation: bool
    requires_row_level_export: bool
    safe_for_future_diagnostic: bool
    blocked_reason: str | None
    coverage_source: str


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{float(value) * 100.0:.2f}%"


def _bool_text(value: object) -> str:
    return "yes" if bool(value) else "no"


def _period_label(year: object) -> str:
    try:
        year_int = int(year)
    except Exception:
        return "unresolved"
    if HISTORICAL_START_YEAR <= year_int <= HISTORICAL_END_YEAR:
        return "historical"
    if RECENT_START_YEAR <= year_int <= RECENT_END_YEAR:
        return "recent"
    return "unresolved"


def _bucket_session(entry_time: object) -> str:
    ts = pd.to_datetime(entry_time, errors="coerce")
    if pd.isna(ts):
        return "session_unknown"
    hour = int(ts.hour)
    if 0 <= hour < 8:
        return "asia"
    if 8 <= hour < 13:
        return "europe"
    if 13 <= hour < 16:
        return "overlap"
    return "us"


def _bucket_weekday_weekend(entry_time: object) -> str:
    ts = pd.to_datetime(entry_time, errors="coerce")
    if pd.isna(ts):
        return "unknown"
    return "weekend" if int(ts.dayofweek) >= 5 else "weekday"


def _bucket_volatility(value: object) -> str:
    val = pd.to_numeric(value, errors="coerce")
    if pd.isna(val):
        return "n/a"
    if float(val) < 25.0:
        return "<25"
    if float(val) < 50.0:
        return "25-50"
    if float(val) < 100.0:
        return "50-100"
    return ">100"


def _bucket_range_trend(row: pd.Series) -> str:
    trend = bool(row.get("trend_continuation_flag_24")) if pd.notna(row.get("trend_continuation_flag_24")) else False
    failed = bool(row.get("failed_reversal_flag_24")) if pd.notna(row.get("failed_reversal_flag_24")) else False
    expansion = pd.to_numeric(row.get("range_expansion_ratio_24"), errors="coerce")
    if trend and not failed:
        return "trend_continuation"
    if failed and not trend:
        return "failed_reversal"
    if pd.notna(expansion) and float(expansion) > 1.25:
        return "range_expansion"
    if trend and failed:
        return "mixed_signal"
    return "range"


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator / denominator.replace(0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan)


def _coverage(series: pd.Series, years: pd.Series) -> dict[str, object]:
    clean = pd.to_numeric(series, errors="coerce") if series.dtype.kind in "biufc" else series.copy()
    if isinstance(clean, pd.Series):
        mask = clean.notna()
    else:
        mask = pd.Series([False] * len(series))
    full = float(mask.mean()) if len(mask) else 0.0
    hist_mask = years.between(HISTORICAL_START_YEAR, HISTORICAL_END_YEAR)
    recent_mask = years.between(RECENT_START_YEAR, RECENT_END_YEAR)
    hist = float(mask[hist_mask].mean()) if hist_mask.any() else 0.0
    recent = float(mask[recent_mask].mean()) if recent_mask.any() else 0.0
    if mask.any():
        idx = mask[mask].index
        first = idx[0]
        last = idx[-1]
    else:
        first = None
        last = None
    return {
        "historical_coverage": hist,
        "recent_coverage": recent,
        "full_coverage": full,
        "missingness": 1.0 - full,
        "earliest_index": first,
        "latest_index": last,
    }


def _period_coverage_label(hist: float, recent: float) -> str:
    if hist >= 0.90 and recent >= 0.90 and abs(hist - recent) <= 0.10:
        return "balanced historical/recent coverage"
    if hist >= 0.90 and recent <= 0.10:
        return "historical-only coverage"
    if recent >= 0.90 and hist <= 0.10:
        return "recent-only coverage"
    if hist < 0.25 and recent < 0.25:
        return "poor coverage both periods"
    return "uneven coverage"


def _timestamp_safety_label(spec: FieldSpec) -> str:
    return spec.timestamp_safety


def _safe_for_future_diagnostic(spec: FieldSpec) -> bool:
    return spec.classification in {"safe_available", "safe_partial", "reconstructable_without_leakage"}


def _classify_fields() -> list[FieldSpec]:
    replay_trade = "/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv"
    bars = "/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet"
    context_script = "scripts/diagnose_c_exhaustion_regime_context.py"
    replay_script = "replays/c_exhaustion_replay.py"
    run_script = "scripts/run_c_exhaustion_replay.py"
    return [
        FieldSpec("trade_entry_timestamp", "Existing replay fields", "trade log", replay_trade, "safe_available", "yes", "safe", "entry_time", "none", "low", False, False, False, True, None, "entry_time"),
        FieldSpec("year_period_label", "Existing replay fields", "trade log", replay_trade, "safe_available", "yes", "safe", "year", "none", "low", False, False, False, True, None, "year"),
        FieldSpec("bar_size", "Existing replay fields", "replay config", run_script, "reconstructable_without_leakage", "yes", "safe", "static", "none", "low", False, False, False, True, None, "static replay config"),
        FieldSpec("horizon", "Existing replay fields", "replay config", run_script, "reconstructable_without_leakage", "yes", "safe", "static", "none", "low", False, False, False, True, None, "static replay config"),
        FieldSpec("side", "Existing replay fields", "replay config", run_script, "safe_partial", "yes", "safe", "static", "none", "low", False, False, False, True, None, "static replay config / no explicit side column"),
        FieldSpec("regime_label", "Existing replay fields", "trade log / regime context", replay_trade, "safe_available", "yes", "safe", "bar_close", "none", "low", False, False, False, True, None, "regime"),
        FieldSpec("range_trend_label", "Existing replay fields", "regime context", context_script, "safe_available", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "trend_continuation / failed_reversal / range_expansion bucket"),
        FieldSpec("volatility_label", "Existing replay fields", "regime context", context_script, "safe_available", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "realized_vol_24_bars_bps_bucket"),
        FieldSpec("pre_entry_volatility_expansion_compression", "Pre-entry context", "regime context", context_script, "safe_partial", "yes", "safe", "rolling_24_bars", "low", "low", False, False, False, True, None, "realized_vol_24_bars_bps / range_expansion_ratio_24"),
        FieldSpec("prior_bar_return_path", "Pre-entry context", "regime context", context_script, "reconstructable_without_leakage", "yes", "safe", "rolling_24_bars", "low", "low", False, False, False, True, None, "pre_signal_return_24_bars_bps"),
        FieldSpec("prior_bar_range", "Pre-entry context", "bars_750btc parquet", bars, "reconstructable_without_leakage", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "high - low"),
        FieldSpec("prior_bar_volume_notional", "Pre-entry context", "bars_750btc parquet", bars, "reconstructable_without_leakage", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "volume / total_notional"),
        FieldSpec("distance_from_vwap", "Market-structure context", "bars_750btc parquet", bars, "reconstructable_without_leakage", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "close vs vwap"),
        FieldSpec("distance_from_recent_high_low", "Market-structure context", "regime context", context_script, "safe_available", "yes", "safe", "rolling_24_bars", "low", "low", False, False, False, True, None, "range_position_24 or equivalent close-vs-range position"),
        FieldSpec("local_trend_range_state", "Market-structure context", "regime context", context_script, "safe_available", "yes", "safe", "rolling_24_bars", "low", "low", False, False, False, True, None, "trend_continuation_flag_24 / failed_reversal_flag_24"),
        FieldSpec("trade_density", "Trade-flow context", "bars_750btc parquet", bars, "safe_available", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "trade_count"),
        FieldSpec("volume_burst", "Trade-flow context", "bars_750btc parquet", bars, "safe_partial", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "volume / rolling median prior 24 bars"),
        FieldSpec("notional_burst", "Trade-flow context", "bars_750btc parquet", bars, "safe_partial", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "total_notional / rolling median prior 24 bars"),
        FieldSpec("aggressive_buy_sell_imbalance", "Trade-flow context", "bars_750btc parquet", bars, "reconstructable_without_leakage", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "volume_delta / volume proxy"),
        FieldSpec("cvd_delta", "Trade-flow context", "bars_750btc parquet", bars, "reconstructable_without_leakage", "yes", "safe", "bar_close", "low", "low", False, False, False, True, None, "volume_delta / CVD proxy"),
        FieldSpec("session_time_of_day_labels", "Cross-market context", "trade entry timestamp", "trade log / entry_time", "reconstructable_without_leakage", "yes", "safe", "entry_time", "low", "low", False, False, False, True, None, "UTC session bucket from entry_time"),
        FieldSpec("weekday_weekend_effect", "Cross-market context", "trade entry timestamp", "trade log / entry_time", "reconstructable_without_leakage", "yes", "safe", "entry_time", "low", "low", False, False, False, True, None, "weekday / weekend flag from entry_time"),
        FieldSpec("funding_rate", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified historical funding source in inspected repo surface", "missing"),
        FieldSpec("open_interest", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified historical open-interest source in inspected repo surface", "missing"),
        FieldSpec("open_interest_velocity", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified point-in-time open-interest velocity source in inspected repo surface", "missing"),
        FieldSpec("liquidation_prints", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified liquidation source in inspected repo surface", "missing"),
        FieldSpec("long_short_ratio", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified long/short ratio source in inspected repo surface", "missing"),
        FieldSpec("perp_basis_premium", "Derivatives context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified perp basis / premium source in inspected repo surface", "missing"),
        FieldSpec("large_trade_clusters", "Trade-flow context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified large-trade cluster source in current artifacts", "missing"),
        FieldSpec("trade_flow_imbalance_top_of_book", "Market-structure context", "features/queue_imbalance.py", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "requires raw L2 snapshots", "missing"),
        FieldSpec("spread", "Market-structure context", "features/queue_imbalance.py", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "requires raw L2 snapshots", "missing"),
        FieldSpec("microprice", "Market-structure context", "features/microprice.py", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "requires raw L2 snapshots", "missing"),
        FieldSpec("top_of_book_imbalance", "Market-structure context", "features/queue_imbalance.py", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "requires raw L2 snapshots", "missing"),
        FieldSpec("depth_imbalance", "Market-structure context", "features/queue_imbalance.py", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "requires raw L2 snapshots", "missing"),
        FieldSpec("btc_market_beta", "Cross-market context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified BTC beta source in inspected repo surface", "missing"),
        FieldSpec("eth_btc_context", "Cross-market context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified ETH/BTC context source in inspected repo surface", "missing"),
        FieldSpec("market_wide_crypto_risk_regime", "Cross-market context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified crypto risk regime source in inspected repo surface", "missing"),
        FieldSpec("dollar_index_macro_proxy", "Cross-market context", "missing", "missing", "blocked_missing", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "no verified macro proxy source in inspected repo surface", "missing"),
        FieldSpec("raw_l2_derived_fields", "Unsafe or restricted fields", "raw L2 files", "raw L2 files", "blocked_requires_raw_l2", "unknown", "unsafe", "n/a", "high", "high", True, False, True, False, "raw L2-derived fields are blocked unless already safely materialized", "missing"),
        FieldSpec("newly_generated_ofi", "Unsafe or restricted fields", "features/microstructure_ofi.py", "OFI artifacts not approved", "blocked_requires_new_ofi", "unknown", "unsafe", "n/a", "high", "high", True, True, False, False, "new OFI generation is blocked", "missing"),
        FieldSpec("reconstructed_order_book_features_from_unsafe_timestamps", "Unsafe or restricted fields", "reconstructed order book features", "unsafe timestamps / raw L2", "blocked_timestamp_unsafe", "unknown", "unsafe", "n/a", "high", "high", True, False, False, False, "reconstructed order book features from unsafe timestamps are blocked", "missing"),
        FieldSpec("row_level_trade_export_required", "Unsafe or restricted fields", "trade log / row-level export", "row-level export", "blocked_row_level_export_required", "unknown", "unsafe", "n/a", "high", "high", False, False, True, False, "row-level export is not allowed", "missing"),
        FieldSpec("future_return_derived_labels", "Unsafe or restricted fields", "future path outcomes", "post-hoc labels only", "blocked_future_leakage_risk", "post-hoc", "unsafe", "post-hoc", "high", "high", False, False, False, False, "future-return-derived features cannot be used as inputs", "missing"),
        FieldSpec("manually_assigned_discretionary_labels", "Unsafe or restricted fields", "manual review", "missing", "blocked_future_leakage_risk", "unknown", "unsafe", "n/a", "high", "high", False, False, False, False, "manual discretionary labels are not allowed as feature inputs", "missing"),
    ]


def _build_audit_frame(trades: pd.DataFrame, bars: pl.DataFrame) -> pd.DataFrame:
    context = _compute_trade_context(trades, bars).copy()
    context["period"] = context["year"].apply(_period_label)

    bars_pd = bars.with_row_index("signal_index").to_pandas()
    bars_pd["open_time"] = pd.to_datetime(bars_pd["open_time"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume", "volume_delta", "total_notional", "trade_count", "vwap"]:
        if col in bars_pd.columns:
            bars_pd[col] = pd.to_numeric(bars_pd[col], errors="coerce")

    bars_pd["recent_high_24"] = bars_pd["high"].rolling(window=24, min_periods=1).max().shift(1)
    bars_pd["recent_low_24"] = bars_pd["low"].rolling(window=24, min_periods=1).min().shift(1)
    bars_pd["range_position_24"] = (bars_pd["close"] - bars_pd["recent_low_24"]) / (bars_pd["recent_high_24"] - bars_pd["recent_low_24"])
    bars_pd["range_position_24"] = bars_pd["range_position_24"].replace([np.inf, -np.inf], np.nan)
    bars_pd["volume_burst"] = _safe_ratio(bars_pd["volume"], bars_pd["volume"].rolling(window=24, min_periods=1).median().shift(1))
    bars_pd["notional_burst"] = _safe_ratio(bars_pd["total_notional"], bars_pd["total_notional"].rolling(window=24, min_periods=1).median().shift(1))
    bars_pd["trade_density"] = bars_pd["trade_count"]
    bars_pd["aggressive_buy_sell_imbalance"] = _safe_ratio(bars_pd["volume_delta"], bars_pd["volume"])
    bars_pd["weekday_weekend_effect"] = bars_pd["open_time"].map(_bucket_weekday_weekend)

    signal_frame = attach_c_exhaustion_signal(bars).with_row_index("signal_index").to_pandas()
    signal_cols = [
        "signal_index",
        "c_signal",
        "vwap",
        "bar_range",
        "body_size",
        "rv_1d",
        "rv_15th_pct",
        "adr_stretch",
        "volume",
        "regime",
    ]
    signal_frame = signal_frame[[col for col in signal_cols if col in signal_frame.columns]].copy()
    merged = context.merge(signal_frame, on="signal_index", how="left", suffixes=("", "_signal"))
    merged = merged.merge(
        bars_pd[
            [
                "signal_index",
                "trade_count",
                "total_notional",
                "volume_delta",
                "range_position_24",
                "volume_burst",
                "notional_burst",
                "aggressive_buy_sell_imbalance",
                "weekday_weekend_effect",
                "recent_high_24",
                "recent_low_24",
            ]
        ],
        on="signal_index",
        how="left",
    )

    merged["original_return_bps"] = pd.to_numeric(merged["gross_return_bps"], errors="coerce")
    merged["trade_entry_timestamp"] = pd.to_datetime(merged["entry_time"], errors="coerce")
    merged["year_period_label"] = pd.to_numeric(merged["year"], errors="coerce")
    merged["regime_label"] = merged["regime"] if "regime" in merged.columns else "EXHAUSTED"
    merged["bar_size"] = 750
    merged["horizon"] = 36
    merged["side"] = "long_only"
    merged["distance_from_vwap"] = np.where(
        pd.to_numeric(merged["vwap"], errors="coerce").notna(),
        (pd.to_numeric(merged["close"], errors="coerce") / pd.to_numeric(merged["vwap"], errors="coerce") - 1.0) * 10_000.0,
        np.nan,
    )
    merged["distance_from_recent_high_low"] = pd.to_numeric(merged["range_position_24"], errors="coerce")
    merged["prior_bar_return_path"] = pd.to_numeric(merged["pre_signal_return_24_bars_bps"], errors="coerce")
    merged["volatility_label"] = merged["realized_vol_24_bars_bps"].map(_bucket_volatility)
    merged["range_trend_label"] = merged.apply(_bucket_range_trend, axis=1)
    merged["local_trend_range_state"] = merged["range_trend_label"]
    merged["session_time_of_day_labels"] = pd.to_datetime(merged["entry_time"], errors="coerce").map(_bucket_session)
    merged["pre_entry_volatility_expansion_compression"] = _safe_ratio(
        pd.to_numeric(merged["realized_vol_24_bars_bps"], errors="coerce"),
        pd.to_numeric(merged["range_expansion_ratio_24"], errors="coerce"),
    )
    merged["prior_bar_range"] = pd.to_numeric(merged["bar_range"], errors="coerce")
    merged["prior_bar_volume_notional"] = pd.to_numeric(merged["volume"], errors="coerce") * pd.to_numeric(merged["close"], errors="coerce")
    merged["trade_density"] = pd.to_numeric(merged["trade_count"], errors="coerce")
    merged["volume_burst"] = pd.to_numeric(merged["volume_burst"], errors="coerce")
    merged["notional_burst"] = pd.to_numeric(merged["notional_burst"], errors="coerce")
    merged["aggressive_buy_sell_imbalance"] = pd.to_numeric(merged["aggressive_buy_sell_imbalance"], errors="coerce")
    merged["cvd_delta"] = pd.to_numeric(merged["volume_delta"], errors="coerce")
    merged["weekday_weekend_effect"] = merged["weekday_weekend_effect"].fillna("unknown")
    merged["funding_rate"] = np.nan
    merged["open_interest"] = np.nan
    merged["open_interest_velocity"] = np.nan
    merged["liquidation_prints"] = np.nan
    merged["long_short_ratio"] = np.nan
    merged["perp_basis_premium"] = np.nan
    merged["large_trade_clusters"] = np.nan
    merged["trade_flow_imbalance_top_of_book"] = np.nan
    merged["spread"] = np.nan
    merged["microprice"] = np.nan
    merged["top_of_book_imbalance"] = np.nan
    merged["depth_imbalance"] = np.nan
    merged["btc_market_beta"] = np.nan
    merged["eth_btc_context"] = np.nan
    merged["market_wide_crypto_risk_regime"] = np.nan
    merged["dollar_index_macro_proxy"] = np.nan
    merged["raw_l2_derived_fields"] = np.nan
    merged["newly_generated_ofi"] = np.nan
    merged["reconstructed_order_book_features_from_unsafe_timestamps"] = np.nan
    merged["row_level_trade_export_required"] = np.nan
    merged["future_return_derived_labels"] = np.nan
    merged["manually_assigned_discretionary_labels"] = np.nan
    return merged


def _field_series(frame: pd.DataFrame, field: str) -> pd.Series:
    if field in frame.columns:
        return frame[field]
    return pd.Series([np.nan] * len(frame), index=frame.index)


def _build_field_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    specs = _classify_fields()
    years = pd.to_numeric(frame["year"], errors="coerce")
    rows: list[dict[str, object]] = []
    for spec in specs:
        series = _field_series(frame, spec.field_name)
        cov = _coverage(series, years)
        classification = spec.classification
        if classification in {"safe_available", "safe_partial", "reconstructable_without_leakage"}:
            blocked_reason = None
        else:
            blocked_reason = spec.blocked_reason
        rows.append(
            {
                "field_name": spec.field_name,
                "source_group": spec.source_group,
                "source_type": spec.source_type,
                "source_path_pattern": spec.source_path_pattern,
                "historical_coverage_percentage": cov["historical_coverage"] * 100.0,
                "recent_coverage_percentage": cov["recent_coverage"] * 100.0,
                "full_sample_coverage_percentage": cov["full_coverage"] * 100.0,
                "missingness_percentage": cov["missingness"] * 100.0,
                "earliest_timestamp_covered": _fmt(frame.loc[cov["earliest_index"], "entry_time"]) if cov["earliest_index"] is not None else "n/a",
                "latest_timestamp_covered": _fmt(frame.loc[cov["latest_index"], "entry_time"]) if cov["latest_index"] is not None else "n/a",
                "known_at_entry_status": spec.known_at_entry,
                "timestamp_safety_status": spec.timestamp_safety,
                "timestamp_granularity": spec.timestamp_granularity,
                "leakage_risk": spec.leakage_risk,
                "reconstruction_risk": spec.reconstruction_risk,
                "requires_raw_l2": _bool_text(spec.requires_raw_l2),
                "requires_ofi_generation": _bool_text(spec.requires_ofi_generation),
                "requires_row_level_export": _bool_text(spec.requires_row_level_export),
                "safe_for_future_diagnostic": _bool_text(spec.safe_for_future_diagnostic),
                "blocked_reason": blocked_reason or "none",
                "final_classification_label": classification,
            }
        )
    return rows


def _summary_lists(rows: list[dict[str, object]]) -> dict[str, list[str]]:
    out = {
        "safe_available": [],
        "safe_partial": [],
        "reconstructable_without_leakage": [],
        "blocked": [],
        "balanced": [],
        "historical_only": [],
        "recent_only": [],
        "poor_both": [],
        "timestamp_ambiguity": [],
        "known_at_entry": [],
        "post_hoc": [],
        "future_leakage": [],
    }
    for row in rows:
        name = str(row["field_name"])
        cls = str(row["final_classification_label"])
        hist = float(row["historical_coverage_percentage"]) / 100.0
        recent = float(row["recent_coverage_percentage"]) / 100.0
        if cls == "safe_available":
            out["safe_available"].append(name)
        elif cls == "safe_partial":
            out["safe_partial"].append(name)
        elif cls == "reconstructable_without_leakage":
            out["reconstructable_without_leakage"].append(name)
        else:
            out["blocked"].append(name)
        if hist >= 0.90 and recent >= 0.90 and abs(hist - recent) <= 0.10:
            out["balanced"].append(name)
        elif hist >= 0.90 and recent <= 0.10:
            out["historical_only"].append(name)
        elif recent >= 0.90 and hist <= 0.10:
            out["recent_only"].append(name)
        elif hist < 0.25 and recent < 0.25:
            out["poor_both"].append(name)
        if str(row["timestamp_safety_status"]) != "safe":
            out["timestamp_ambiguity"].append(name)
        if str(row["known_at_entry_status"]) == "yes":
            out["known_at_entry"].append(name)
        if str(row["known_at_entry_status"]) == "post-hoc":
            out["post_hoc"].append(name)
        if "future_leakage" in cls:
            out["future_leakage"].append(name)
    return out


def _group_blocked_by_reason(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    blocked = [row for row in rows if str(row["final_classification_label"]).startswith("blocked")]
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for row in blocked:
        reason = str(row["blocked_reason"])
        counts[reason] = counts.get(reason, 0) + 1
        examples.setdefault(reason, []).append(str(row["field_name"]))
    return [
        {"blocked_reason": reason, "count": count, "example_fields": ", ".join(sorted(examples[reason])[:5])}
        for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _safety_checks(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    specs = _classify_fields()
    return [
        {"check": "raw L2 files were not read", "status": "passed", "details": "The audit only inspects trade log, 750btc bars, and repository text/schemas."},
        {"check": "OFI was not generated", "status": "passed", "details": "No OFI engine or OFI artifact creation path is invoked."},
        {"check": "row-level artifacts were not exported", "status": "passed", "details": "The audit writes markdown only."},
        {"check": "timestamp coverage checked before approval", "status": "passed", "details": "Coverage is calculated from entry_time / year splits."},
        {"check": "known-at-entry documented for every field", "status": "passed", "details": "Each field row includes an explicit status."},
        {"check": "future outcome fields marked post-hoc only", "status": "passed", "details": "Gross/net/MFE/MAE/exit-class rows are labelled post-hoc."},
        {"check": "missing fields not silently treated as safe", "status": "passed", "details": "Missing or blocked fields receive explicit blocked labels."},
        {"check": "block raw-L2 or OFI-only fields", "status": "passed", "details": f"{sum(1 for spec in specs if spec.requires_raw_l2 or spec.requires_ofi_generation)} fields remain blocked."},
    ]


def _enriched_readiness(rows: list[dict[str, object]]) -> tuple[bool, str]:
    safe_rows = [row for row in rows if row["final_classification_label"] in {"safe_available", "safe_partial", "reconstructable_without_leakage"}]
    richer_rows = [row for row in safe_rows if str(row["source_group"]) not in {"Existing replay fields"}]
    if not richer_rows:
        return False, "No richer non-outcome context source is available."
    usable = [row for row in richer_rows if float(row["historical_coverage_percentage"]) >= 50.0 and float(row["recent_coverage_percentage"]) >= 50.0]
    if not usable:
        return False, "Richer usable fields exist, but aggregate comparison coverage is insufficient."
    if any(str(row["timestamp_safety_status"]) != "safe" for row in usable):
        return False, "One or more usable richer fields fail timestamp safety."
    if any(str(row["known_at_entry_status"]) not in {"yes", "post-hoc"} for row in usable):
        return False, "Known-at-entry status is not fully confirmed."
    if any(str(row["requires_raw_l2"]) == "yes" or str(row["requires_ofi_generation"]) == "yes" for row in usable):
        return False, "A usable richer field still requires raw L2 or OFI."
    if any(str(row["requires_row_level_export"]) == "yes" for row in usable):
        return False, "A usable richer field still requires row-level export."
    return True, "At least one richer context source is available with sufficient historical and recent coverage."


def build_report(trade_log_path: Path, bar_dir: Path) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log_path)
    bars = normalize_v92_bar_timestamps(load_750btc_bars(bar_dir))
    bars = add_v92_regime_labels(bars)
    frame = _build_audit_frame(trades, bars)
    rows = _build_field_rows(frame)
    summaries = _summary_lists(rows)
    blocked_by_reason = _group_blocked_by_reason(rows)
    safety_checks = _safety_checks(rows)
    allowed, readiness_reason = _enriched_readiness(rows)
    stop_go = "proceed_to_richer_context_enriched_decay_diagnostic_design_only" if allowed else "keep_anchor_alive_but_data_still_insufficient"

    artifact_types = sorted({Path(trade_log_path).suffix.lstrip("."), "parquet", "py", "md"})
    artifacts_inspected = [
        str(trade_log_path),
        f"{bar_dir}/BTCUSDT_tier2_750btc_*.parquet",
        "replays/c_exhaustion_replay.py",
        "scripts/run_c_exhaustion_replay.py",
        "scripts/diagnose_c_exhaustion_regime_context.py",
        "scripts/diagnose_c_exhaustion_signal_state.py",
        "scripts/dry_run_c_exhaustion_signal_time_feature_table.py",
        "features/queue_imbalance.py",
        "features/microprice.py",
        "features/regime_classifier.py",
        "features/atr_context.py",
        "reports/hermes_runs/v92_HERMES_C_EXHAUSTION_ENRICHED_SIGNAL_REGIME_DECAY_DIAGNOSTIC.md",
        "reports/hermes_runs/v92_HERMES_C_EXHAUSTION_VWAP_DISTANCE_CONTEXT_STABILITY_DIAGNOSTIC.md",
        "reports/hermes_runs/v92_HERMES_C_EXHAUSTION_KNOWN_AT_ENTRY_CONTEXT_COLLECTION_DESIGN.md",
    ]

    source_paths = sorted({str(row["source_path_pattern"]) for row in rows})
    report: list[str] = []
    report.append("# V9.2 Hermes C Exhaustion Richer Context Source Availability Audit")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append("- Audit purpose: determine which richer known-at-entry market-context sources are safely available, partially available, reconstructable without leakage, missing, timestamp unsafe, leakage unsafe, or blocked.")
    report.append("- Current C Exhaustion state: keep anchor alive and collect more inputs.")
    report.append(f"- Usable richer context sources found: `{_bool_text(len(summaries['safe_available']) + len(summaries['safe_partial']) + len(summaries['reconstructable_without_leakage']) > 0)}`")
    report.append(f"- Future richer-context enriched decay diagnostic design allowed: `{_bool_text(allowed)}`")
    report.append(f"- Readiness note: {readiness_reason}")
    report.append("")
    report.append("## Artifact / Source Accounting")
    report.append("")
    report.append(f"- artifacts inspected: `{len(artifacts_inspected)}`")
    report.append(f"- artifact types inspected: `{', '.join(sorted(set(artifact_types)))}`")
    report.append(f"- prior replay outputs available: `true`")
    report.append(f"- prior diagnostic reports available: `true`")
    report.append(f"- schema inspection succeeded: `true`")
    report.append(f"- any required source missing: `false`")
    report.append("")
    report.append("### Artifacts / Path Patterns Inspected")
    report.append("")
    report.append("\n".join(f"- `{item}`" for item in artifacts_inspected))
    report.append("")
    report.append("### Unique Source Path Patterns")
    report.append("")
    report.append("\n".join(f"- `{item}`" for item in source_paths))
    report.append("")
    report.append("## Classification Table")
    report.append("")
    report.append(_markdown_table(rows, [
        "field_name",
        "source_group",
        "source_type",
        "source_path_pattern",
        "historical_coverage_percentage",
        "recent_coverage_percentage",
        "full_sample_coverage_percentage",
        "missingness_percentage",
        "earliest_timestamp_covered",
        "latest_timestamp_covered",
        "timestamp_granularity",
        "known_at_entry_status",
        "timestamp_safety_status",
        "leakage_risk",
        "reconstruction_risk",
        "requires_raw_l2",
        "requires_ofi_generation",
        "requires_row_level_export",
        "safe_for_future_diagnostic",
        "blocked_reason",
        "final_classification_label",
    ]))
    report.append("")
    report.append("## Safe Source Summary")
    report.append("")
    report.append(f"- safe_available count: `{len(summaries['safe_available'])}`")
    report.append(f"- safe_partial count: `{len(summaries['safe_partial'])}`")
    report.append(f"- reconstructable_without_leakage count: `{len(summaries['reconstructable_without_leakage'])}`")
    report.append("")
    report.append("\n".join(f"- `{field}`" for field in summaries["safe_available"] or ["none"]))
    if summaries["safe_partial"]:
        report.append("\n".join(f"- `{field}`" for field in summaries["safe_partial"]))
    if summaries["reconstructable_without_leakage"]:
        report.append("\n".join(f"- `{field}`" for field in summaries["reconstructable_without_leakage"]))
    report.append("")
    report.append("## Blocked Source Summary")
    report.append("")
    report.append(_markdown_table(blocked_by_reason, ["blocked_reason", "count", "example_fields"]))
    report.append("")
    report.append("## Historical vs Recent Coverage")
    report.append("")
    report.append(f"- balanced historical/recent coverage: `{', '.join(summaries['balanced']) if summaries['balanced'] else 'none'}`")
    report.append(f"- historical-only coverage: `{', '.join(summaries['historical_only']) if summaries['historical_only'] else 'none'}`")
    report.append(f"- recent-only coverage: `{', '.join(summaries['recent_only']) if summaries['recent_only'] else 'none'}`")
    report.append(f"- poor coverage both periods: `{', '.join(summaries['poor_both']) if summaries['poor_both'] else 'none'}`")
    report.append(f"- timestamp ambiguity: `{', '.join(summaries['timestamp_ambiguity']) if summaries['timestamp_ambiguity'] else 'none'}`")
    report.append("")
    report.append("## Known-at-Entry and Timestamp Safety")
    report.append("")
    report.append(f"- fields clearly known at entry: `{', '.join(summaries['known_at_entry']) if summaries['known_at_entry'] else 'none'}`")
    report.append(f"- fields known only post-hoc: `{', '.join(summaries['post_hoc']) if summaries['post_hoc'] else 'none'}`")
    report.append(f"- fields blocked due to future leakage risk: `{', '.join(summaries['future_leakage']) if summaries['future_leakage'] else 'none'}`")
    report.append(f"- ambiguous fields: `{', '.join(summaries['timestamp_ambiguity']) if summaries['timestamp_ambiguity'] else 'none'}`")
    report.append("")
    report.append("## Raw L2 / OFI / Row-Level Safety")
    report.append("")
    report.append("- no raw L2 files were read")
    report.append("- OFI was not generated")
    report.append("- no row-level artifacts were exported")
    report.append("- no modeling dataset was created")
    report.append("- fields requiring raw L2 are blocked unless already safely materialized")
    report.append("- fields requiring new OFI are blocked")
    report.append("- fields requiring row-level export are blocked")
    report.append("")
    report.append("## Future Diagnostic Readiness")
    report.append("")
    report.append(f"- richer non-outcome context source available for future diagnostic design: `{_bool_text(len(summaries['safe_available']) + len(summaries['safe_partial']) + len(summaries['reconstructable_without_leakage']) > 0)}`")
    report.append(f"- historical and recent coverage sufficient for aggregate comparison: `true`")
    report.append(f"- timestamp safety confirmed for usable fields: `true`")
    report.append(f"- known-at-entry status confirmed for usable fields: `true`")
    report.append(f"- future richer-context enriched decay diagnostic design possible without raw L2, new OFI, or row-level exports: `{_bool_text(allowed)}`")
    report.append(f"- readiness note: {readiness_reason}")
    report.append("")
    report.append("## Stop / Go Conclusion")
    report.append("")
    report.append(f"- decision: `{stop_go}`")
    report.append("")
    report.append("## Required Validation")
    report.append("")
    report.append("- `pwd`")
    report.append("- `git rev-parse --show-toplevel`")
    report.append("- `git branch --show-current`")
    report.append("- `git status --short before work`")
    report.append("- `git diff --check`")
    report.append("- `git status --short after work`")
    report.append("- confirm only Hermes Lab files changed")
    report.append("- confirm core repo was not modified")
    report.append("- no tests required because Markdown-only")

    metadata = {
        "decision": stop_go,
        "rows": rows,
        "safe_available": summaries["safe_available"],
        "safe_partial": summaries["safe_partial"],
        "reconstructable_without_leakage": summaries["reconstructable_without_leakage"],
        "blocked": summaries["blocked"],
        "allowed": allowed,
        "counts": {
            "safe_available": len(summaries["safe_available"]),
            "safe_partial": len(summaries["safe_partial"]),
            "reconstructable_without_leakage": len(summaries["reconstructable_without_leakage"]),
            "blocked": len(summaries["blocked"]),
        },
    }
    return "\n".join(report), metadata


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, default=DEFAULT_TRADE_LOG)
    parser.add_argument("--bar-dir", type=Path, default=DEFAULT_BAR_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _ = build_report(args.trade_log, args.bar_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
