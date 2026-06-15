from __future__ import annotations

import numpy as np
import polars as pl

from features.regime_classifier import add_regime_labels
from replays.c_exhaustion_replay import (
    add_v92_regime_labels,
    attach_c_exhaustion_signal,
    replay_c_exhaustionfade,
)


def _make_bars(n: int, seed: int = 42) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    n = max(n, 800)

    close = 30_000.0 + np.cumsum(rng.normal(0, 100, n))
    close = np.clip(close, 1_000, None)
    high = close + rng.uniform(50, 200, n)
    low = close - rng.uniform(50, 200, n)
    low = np.clip(low, 1.0, None)
    open_ = close + rng.normal(0, 50, n)

    open_time = np.arange(n, dtype=np.int64) * 60_000 + 1_600_000_000_000
    close_time = open_time + 59_000

    return pl.DataFrame(
        {
            "open_time": open_time,
            "close_time": close_time,
            "open": open_.astype(np.float64),
            "high": high.astype(np.float64),
            "low": low.astype(np.float64),
            "close": close.astype(np.float64),
            "volume": rng.uniform(100, 500, n).astype(np.float64),
            "volume_delta": rng.normal(0, 50, n).astype(np.float64),
        }
    )


def test_replay_wrapper_matches_central_classifier():
    bars = _make_bars(800)

    central = add_regime_labels(bars)
    via_replay = add_v92_regime_labels(bars)

    assert "regime" in central.columns
    assert "regime" in via_replay.columns
    assert central["regime"].to_list() == via_replay["regime"].to_list()


def test_replay_has_no_local_classifier_fallback():
    import replays.c_exhaustion_replay as replay_module

    assert not hasattr(replay_module, "_add_regime_labels")


def test_attach_signal_attaches_regime_when_missing():
    bars = _make_bars(800)
    assert "regime" not in bars.columns

    result = attach_c_exhaustion_signal(
        bars,
        signal_lookback_bars=5,
        volume_lookback_bars=10,
    )

    assert "regime" in result.columns
    assert "c_signal" in result.columns


def test_replay_runs_on_raw_bars_without_precomputed_regime():
    bars = _make_bars(800)
    assert "regime" not in bars.columns

    result = replay_c_exhaustionfade(
        bars,
        horizon_bars=36,
        round_trip_cost_bps=12.0,
        signal_lookback_bars=5,
        volume_lookback_bars=10,
        bar_size=750,
    )

    assert result.summary["trade_count"] >= 0
    assert "trade_count" in result.summary
    assert "net_expectancy_bps" in result.summary


def test_classifier_outputs_only_valid_regimes():
    bars = _make_bars(800)
    result = add_regime_labels(bars)

    valid = {"TREND_BUILDUP", "ABSORPTION", "EXHAUSTED", "NOISE"}
    observed = set(result["regime"].to_list())

    assert observed <= valid


def test_classifier_drops_private_internal_columns():
    bars = _make_bars(800)
    result = add_regime_labels(bars)

    leaked = [col for col in result.columns if col.startswith("_")]
    assert not leaked, f"Internal private columns leaked: {leaked}"
