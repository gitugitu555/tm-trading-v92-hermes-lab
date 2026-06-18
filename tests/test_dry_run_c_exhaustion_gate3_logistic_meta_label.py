from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.dry_run_c_exhaustion_gate3_logistic_meta_label as gate3


def _write_frame(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        frame.to_csv(path, index=False)
        return path
    if path.suffix == ".parquet":
        try:
            frame.to_parquet(path, index=False)
        except Exception as exc:  # pragma: no cover - parquet engine availability varies
            pytest.skip(f"parquet engine unavailable: {exc}")
        return path
    raise AssertionError(f"unsupported suffix: {path.suffix}")


def _trade_frame() -> pd.DataFrame:
    rows = [
        {
            "signal_index": 10,
            "entry_index": 11,
            "exit_index": 12,
            "signal_time": "2020-06-01T00:00:00",
            "entry_time": "2020-05-31T23:00:00",
            "exit_time": "2021-05-31T23:00:00",
            "net_return_bps": 10.0,
            "year": 2020,
        },
        {
            "signal_index": 11,
            "entry_index": 12,
            "exit_index": 13,
            "signal_time": "2021-06-01T00:00:00",
            "entry_time": "2021-05-31T23:00:00",
            "exit_time": "2022-05-31T23:00:00",
            "net_return_bps": -5.0,
            "year": 2021,
        },
        {
            "signal_index": 12,
            "entry_index": 13,
            "exit_index": 14,
            "signal_time": "2022-06-01T00:00:00",
            "entry_time": "2022-05-31T23:00:00",
            "exit_time": "2023-12-31T17:00:00",
            "net_return_bps": 2.0,
            "year": 2022,
        },
        {
            "signal_index": 13,
            "entry_index": 14,
            "exit_index": 15,
            "signal_time": "2023-12-31T18:00:00",
            "entry_time": "2023-12-31T17:00:00",
            "exit_time": "2024-12-31T17:00:00",
            "net_return_bps": -3.0,
            "year": 2023,
        },
        {
            "signal_index": 14,
            "entry_index": 15,
            "exit_index": 15,
            "signal_time": "2024-06-01T00:00:00",
            "entry_time": "2024-05-31T23:00:00",
            "exit_time": "2024-12-31T17:00:00",
            "net_return_bps": 5.0,
            "year": 2024,
        },
        {
            "signal_index": 15,
            "entry_index": 16,
            "exit_index": 17,
            "signal_time": "2024-12-31T18:00:00",
            "entry_time": "2024-12-31T17:00:00",
            "exit_time": "2026-05-31T23:00:00",
            "net_return_bps": 1.0,
            "year": 2024,
        },
        {
            "signal_index": 16,
            "entry_index": 17,
            "exit_index": 17,
            "signal_time": "2025-06-01T00:00:00",
            "entry_time": "2025-05-31T23:00:00",
            "exit_time": "2026-05-31T23:00:00",
            "net_return_bps": -1.0,
            "year": 2025,
        },
        {
            "signal_index": 17,
            "entry_index": 18,
            "exit_index": 18,
            "signal_time": "2026-06-01T00:00:00",
            "entry_time": "2026-05-31T23:00:00",
            "exit_time": "2027-05-31T23:00:00",
            "net_return_bps": 4.0,
            "year": 2026,
        },
        {
            "signal_index": 18,
            "entry_index": 19,
            "exit_index": 19,
            "signal_time": "2027-06-01T00:00:00",
            "entry_time": "2027-05-31T23:00:00",
            "exit_time": "2027-12-30T23:00:00",
            "net_return_bps": 0.0,
            "year": 2027,
        },
        {
            "signal_index": 19,
            "entry_index": 19,
            "exit_index": 19,
            "signal_time": "2027-12-31T00:00:00",
            "entry_time": "2027-12-30T23:00:00",
            "exit_time": "2027-12-30T23:00:00",
            "net_return_bps": -2.0,
            "year": 2027,
        },
    ]
    return pd.DataFrame(rows)


def _bar_frame() -> pd.DataFrame:
    times = [
        ("2020-05-21T00:00:00", "2020-05-21T01:00:00"),
        ("2020-05-21T01:00:00", "2020-05-21T02:00:00"),
        ("2020-05-21T02:00:00", "2020-05-21T03:00:00"),
        ("2020-05-21T03:00:00", "2020-05-21T04:00:00"),
        ("2020-05-21T04:00:00", "2020-05-21T05:00:00"),
        ("2020-05-21T05:00:00", "2020-05-21T06:00:00"),
        ("2020-05-21T06:00:00", "2020-05-21T07:00:00"),
        ("2020-05-21T07:00:00", "2020-05-21T08:00:00"),
        ("2020-05-21T08:00:00", "2020-05-21T09:00:00"),
        ("2020-05-21T09:00:00", "2020-05-21T10:00:00"),
        ("2020-05-31T23:00:00", "2020-06-01T00:00:00"),
        ("2021-05-31T23:00:00", "2021-06-01T00:00:00"),
        ("2022-05-31T23:00:00", "2022-06-01T00:00:00"),
        ("2023-12-31T17:00:00", "2023-12-31T18:00:00"),
        ("2024-05-31T23:00:00", "2024-06-01T00:00:00"),
        ("2024-12-31T17:00:00", "2024-12-31T18:00:00"),
        ("2025-05-31T23:00:00", "2025-06-01T00:00:00"),
        ("2026-05-31T23:00:00", "2026-06-01T00:00:00"),
        ("2027-05-31T23:00:00", "2027-06-01T00:00:00"),
        ("2027-12-30T23:00:00", "2027-12-31T00:00:00"),
    ]
    return pd.DataFrame(
        {
            "bar_id": list(range(len(times))),
            "open_time": [start for start, _ in times],
            "close_time": [end for _, end in times],
            "open": [100.0 + idx for idx in range(len(times))],
            "high": [100.5 + idx for idx in range(len(times))],
            "low": [99.5 + idx for idx in range(len(times))],
            "close": [100.25 + idx for idx in range(len(times))],
            "volume": [10.0 + idx for idx in range(len(times))],
            "volume_delta": [1.0 if idx % 2 == 0 else -1.0 for idx in range(len(times))],
            "total_notional": [1000.0 + idx for idx in range(len(times))],
            "trade_count": [4 + idx for idx in range(len(times))],
            "vwap": [100.1 + idx for idx in range(len(times))],
        }
    )


def _build_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    trade_log = _write_frame(_trade_frame(), tmp_path / "trade_log.csv")
    bar_dir = tmp_path / "bars_750btc"
    _write_frame(_bar_frame(), bar_dir / "BTCUSDT_tier2_750btc_2027-12-30.parquet")
    return trade_log, bar_dir, tmp_path / "logistic.md"


def test_logistic_dry_run_uses_only_approved_24_features(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["x_column_count"] == 24
    assert summary["x_columns_match_contract"] is True
    assert summary["forbidden_features_present_in_x_count"] == 0


def test_forbidden_identity_outcome_and_label_columns_are_excluded_from_x(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["identity_columns_present_in_x_count"] == 0
    assert summary["outcome_columns_present_in_x_count"] == 0
    assert summary["label_column_present_in_x"] is False


def test_scaler_is_fit_only_on_train_rows(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["scaler_fitted_on_train_only"] is True
    assert summary["validation_seen_during_scaler_fit"] is False
    assert summary["holdout_seen_during_scaler_fit"] is False


def test_logistic_model_is_fit_only_on_train_rows(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["model_fitted_on_train_only"] is True


def test_threshold_050_is_primary_and_holdout_is_not_used_for_selection(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert gate3.THRESHOLD == 0.50
    assert summary["validation_used_for_threshold_selection"] is False
    assert summary["holdout_used_for_threshold_selection"] is False
    assert "default_threshold_only" in report


def test_metrics_are_computed_by_split_and_confusion_matrix_is_reported(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert set(summary["split_summaries"].keys()) == {"train", "validation", "holdout"}
    for split_name in ["train", "validation", "holdout"]:
        metrics = summary["split_summaries"][split_name]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "tp" in metrics and "tn" in metrics and "fp" in metrics and "fn" in metrics
    assert "| tn | fp | fn | tp |" in report


def test_keep_all_baseline_is_reported_by_split(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    baseline = summary["keep_all_baseline"]
    assert set(baseline.keys()) == {"train", "validation", "holdout"}
    assert baseline["train"]["keep_all_mean_net_return_bps"] is not None
    assert baseline["validation"]["keep_all_mean_net_return_bps"] is not None
    assert baseline["holdout"]["keep_all_mean_net_return_bps"] is not None


def test_yearly_kept_diagnostics_are_reported(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert len(summary["yearly_rows"]) == 8
    assert "| year | split | total rows | predicted_keep_count | predicted_skip_count | kept_positive_count | kept_negative_count | kept_mean_net_return_bps | keep_all_mean_net_return_bps |" in report


def test_no_model_artifacts_or_feature_table_artifacts_are_written(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    rc = gate3.main(
        [
            "--trade-log",
            str(trade_log),
            "--bar-dir",
            str(bar_dir),
            "--output-doc",
            str(output_doc),
        ]
    )

    assert rc == 0
    assert output_doc.exists()
    file_suffixes = sorted({path.suffix for path in tmp_path.rglob("*") if path.is_file()})
    assert file_suffixes == [".csv", ".md", ".parquet"]
    assert output_doc.suffix == ".md"


def test_report_includes_safety_statements_and_does_not_approve_alpha_or_paper_live(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No feature-table artifacts were written.",
        "No model artifacts were written.",
        "No strategy logic was changed.",
        "No replay logic was changed.",
        "No strategy backtest was run.",
        "No paper/live trading was run.",
        "No production approval is given.",
        "No alpha approval is given.",
        "Full reconstruction remains blocked.",
    ]:
        assert expected in report
    assert "alpha is approved" not in report.lower()
    assert "paper/live trading is approved" not in report.lower()
    assert "production is approved" not in report.lower()


def test_tests_do_not_require_real_trade_logs_real_bars_raw_l2_or_ofi_artifacts(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    rc = gate3.main(
        [
            "--trade-log",
            str(trade_log),
            "--bar-dir",
            str(bar_dir),
            "--output-doc",
            str(output_doc),
        ]
    )

    assert rc == 0
    assert output_doc.exists()
