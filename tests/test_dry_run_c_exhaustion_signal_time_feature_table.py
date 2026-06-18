from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.dry_run_c_exhaustion_signal_time_feature_table as dry_run


def _write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except Exception as exc:  # pragma: no cover - engine availability varies
        pytest.skip(f"parquet engine unavailable: {exc}")
    return path


def _write_trade_log(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _bar_frame(
    start: str,
    periods: int,
    *,
    freq: str = "1min",
    include_volume_delta: bool = True,
    include_regime: bool = False,
    volume_delta_seed: float = 1.0,
) -> pd.DataFrame:
    opens = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    closes = opens + pd.Timedelta(freq)
    data: dict[str, list[object]] = {
        "bar_id": list(range(periods)),
        "open_time": opens,
        "close_time": closes,
        "open": [100.0 + idx for idx in range(periods)],
        "high": [100.5 + idx for idx in range(periods)],
        "low": [99.5 + idx for idx in range(periods)],
        "close": [100.2 + idx for idx in range(periods)],
        "volume": [10.0 + idx for idx in range(periods)],
    }
    if include_volume_delta:
        data["volume_delta"] = [volume_delta_seed + idx for idx in range(periods)]
    if include_regime:
        data["regime"] = ["EXHAUSTED" if idx % 2 == 0 else "NOISE" for idx in range(periods)]
    return pd.DataFrame(data)


def _trade_log_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_index": 14,
                "entry_index": 15,
                "exit_index": 16,
                "signal_time": "2024-01-01T00:15:00Z",
                "entry_time": "2024-01-02T00:00:00Z",
                "exit_time": "2024-01-02T00:01:00Z",
                "entry_price": 115.0,
                "exit_price": 116.0,
                "gross_return_bps": 86.9,
                "net_return_bps": 81.9,
                "holding_bars": 1,
                "year": 2024,
            },
            {
                "signal_index": 18,
                "entry_index": 19,
                "exit_index": 20,
                "signal_time": "2024-01-02T00:04:00Z",
                "entry_time": "2024-01-02T00:04:00Z",
                "exit_time": "2024-01-02T00:05:00Z",
                "entry_price": 119.0,
                "exit_price": 120.0,
                "gross_return_bps": 84.0,
                "net_return_bps": 79.0,
                "holding_bars": 1,
                "year": 2024,
            },
        ]
    )


def _build_repo(tmp_path: Path, *, include_volume_delta: bool = True, include_regime: bool = False) -> tuple[Path, Path, Path]:
    trade_log = _write_trade_log(_trade_log_frame(), tmp_path / "trade_log.csv")
    bar_dir = tmp_path / "bars_750btc"
    _write_parquet(
        _bar_frame("2024-01-01T00:00:00Z", 15, include_volume_delta=include_volume_delta, include_regime=include_regime, volume_delta_seed=1.0),
        bar_dir / "BTCUSDT_tier2_750btc_2024-01-01.parquet",
    )
    _write_parquet(
        _bar_frame("2024-01-02T00:00:00Z", 15, include_volume_delta=include_volume_delta, include_regime=include_regime, volume_delta_seed=100.0),
        bar_dir / "BTCUSDT_tier2_750btc_2024-01-02.parquet",
    )
    _write_parquet(
        _bar_frame("2024-01-03T00:00:00Z", 15, include_volume_delta=include_volume_delta, include_regime=include_regime, volume_delta_seed=999.0),
        bar_dir / "BTCUSDT_tier2_750btc_2024-01-03.parquet",
    )
    return trade_log, bar_dir, tmp_path / "audit.md"


def test_script_runs_on_synthetic_trade_log_and_bars(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)

    rc = dry_run.main(
        [
            "--trade-log",
            str(trade_log),
            "--bar-dir",
            str(bar_dir),
            "--output-doc",
            str(output_doc),
        ]
    )

    report = output_doc.read_text(encoding="utf-8")
    assert rc == 0
    assert output_doc.exists()
    assert "No raw L2 data was read." in report
    assert "No OFI artifacts were read." in report
    assert "No OFI artifacts were written." in report
    assert "No feature-table artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No model was trained." in report
    assert "No alpha claim is made." in report
    assert "Full reconstruction remains blocked." in report
    assert "gate_2_feature_table_dry_run_completed_or_partial" in report


def test_feature_table_row_count_preserves_trade_log_row_count(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    assert summary["trade_rows_loaded"] == 2
    assert summary["feature_rows_constructed"] == 2
    assert summary["row_count_preserved"] is True
    assert "row_count_preserved: `true`" in report


def test_signal_index_maps_to_signal_bar_features(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)
    feature_table = summary["feature_table"]

    first = feature_table.iloc[0]
    assert first["signal_open"] == pytest.approx(114.0)
    assert first["signal_close"] == pytest.approx(114.2)
    assert first["signal_volume"] == pytest.approx(24.0)


def test_signal_time_equals_signal_bar_close_convention_is_enforced(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    assert "signal_time = signal bar close_time" in report
    assert summary["alignment"]["signal_time_matches_signal_bar_close_pct"] == pytest.approx(100.0)
    assert summary["alignment"]["entry_time_matches_entry_bar_open_pct"] == pytest.approx(100.0)
    assert summary["alignment"]["exit_time_matches_exit_bar_open_pct"] == pytest.approx(100.0)


def test_entry_exit_outcome_columns_are_not_model_features(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps", "holding_bars", "year"]:
        assert column not in feature_table.columns
    for column in ["entry_index", "exit_index", "entry_time", "exit_time"]:
        assert column in feature_table.columns
    assert summary["leakage_audit"]["outcome_columns_excluded_from_features"] is True


def test_exit_bar_data_is_not_used_in_model_features(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    assert "exit_price" not in feature_table.columns
    assert summary["leakage_audit"]["no_exit_bar_data_used"] is True


def test_volume_delta_features_are_created_when_present(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path, include_volume_delta=True)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    assert "signal_volume_delta" in feature_table.columns
    assert "cvd_proxy_at_signal" in feature_table.columns
    assert summary["volume_delta_present"] is True
    assert feature_table.iloc[0]["signal_volume_delta"] == pytest.approx(15.0)
    assert feature_table.iloc[0]["cvd_proxy_at_signal"] == pytest.approx(sum(1.0 + idx for idx in range(15)))


def test_volume_delta_features_are_skipped_when_absent(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path, include_volume_delta=False)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    assert summary["volume_delta_present"] is False
    assert "signal_volume_delta" not in feature_table.columns
    assert "cvd_proxy_at_signal" not in feature_table.columns


def test_cvd_proxy_is_cumulative_only_through_signal_index(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path, include_volume_delta=True)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    first = feature_table.iloc[0]
    expected_cvd = sum(1.0 + idx for idx in range(15))
    assert first["cvd_proxy_at_signal"] == pytest.approx(expected_cvd)
    assert first["cvd_proxy_slope_3_past"] == pytest.approx((expected_cvd - sum(1.0 + idx for idx in range(12))) / 3.0)
    assert first["cvd_proxy_slope_5_past"] == pytest.approx((expected_cvd - sum(1.0 + idx for idx in range(10))) / 5.0)


def test_rolling_features_use_past_and_signal_bars_only(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path, include_volume_delta=True)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    feature_table = summary["feature_table"]
    first = feature_table.iloc[0]
    expected_vol_mean = sum(10.0 + idx for idx in range(15)) / 15.0
    assert first["rolling_vol_20_past"] == pytest.approx(expected_vol_mean)
    assert first["signal_return_1_bar"] == pytest.approx(114.2 / 113.2 - 1.0)


def test_ofi_and_l2_features_are_excluded(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _, summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)
    feature_table = summary["feature_table"]

    blocked_columns = [
        "ofi",
        "mlofi",
        "microprice",
        "spread",
        "depth",
        "queue_imbalance",
        "l2_imbalance",
        "spoofing",
        "iceberg",
        "whale_pressure",
    ]
    for blocked in blocked_columns:
        assert blocked not in feature_table.columns
    assert "OFI / MLOFI" in "\n".join(summary["feature_families_excluded"])


def test_report_includes_required_safety_statements_and_no_alpha_approval_language(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No feature-table artifacts were written.",
        "No market-data artifacts were written.",
        "No strategy backtest was run.",
        "No model was trained.",
        "No alpha claim is made.",
        "Full reconstruction remains blocked.",
    ]:
        assert expected in report
    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()


def test_script_does_not_require_seagate_data_for_tests(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = dry_run.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, preview_rows=2)

    assert "/mnt/seagate" not in report
    assert "raw/cryptohftdata" not in report
