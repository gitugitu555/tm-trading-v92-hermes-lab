from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.audit_c_exhaustion_gate3_design_matrix as gate3


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
            "signal_index": 0,
            "entry_index": 1,
            "exit_index": 2,
            "signal_time": "2020-06-01T00:00:00",
            "entry_time": "2020-05-31T23:00:00",
            "exit_time": "2021-05-31T23:00:00",
            "net_return_bps": 10.0,
            "year": 2020,
        },
        {
            "signal_index": 1,
            "entry_index": 2,
            "exit_index": 3,
            "signal_time": "2021-06-01T00:00:00",
            "entry_time": "2021-05-31T23:00:00",
            "exit_time": "2022-05-31T23:00:00",
            "net_return_bps": -5.0,
            "year": 2021,
        },
        {
            "signal_index": 2,
            "entry_index": 3,
            "exit_index": 4,
            "signal_time": "2022-06-01T00:00:00",
            "entry_time": "2022-05-31T23:00:00",
            "exit_time": "2023-12-31T17:00:00",
            "net_return_bps": 2.0,
            "year": 2022,
        },
        {
            "signal_index": 3,
            "entry_index": 4,
            "exit_index": 5,
            "signal_time": "2023-12-31T18:00:00",
            "entry_time": "2023-12-31T17:00:00",
            "exit_time": "2024-12-31T17:00:00",
            "net_return_bps": -3.0,
            "year": 2023,
        },
        {
            "signal_index": 4,
            "entry_index": 5,
            "exit_index": 5,
            "signal_time": "2024-06-01T00:00:00",
            "entry_time": "2024-05-31T23:00:00",
            "exit_time": "2024-12-31T17:00:00",
            "net_return_bps": 5.0,
            "year": 2024,
        },
        {
            "signal_index": 5,
            "entry_index": 6,
            "exit_index": 7,
            "signal_time": "2024-12-31T18:00:00",
            "entry_time": "2024-12-31T17:00:00",
            "exit_time": "2026-05-31T23:00:00",
            "net_return_bps": 1.0,
            "year": 2024,
        },
        {
            "signal_index": 6,
            "entry_index": 7,
            "exit_index": 7,
            "signal_time": "2025-06-01T00:00:00",
            "entry_time": "2025-05-31T23:00:00",
            "exit_time": "2026-05-31T23:00:00",
            "net_return_bps": -1.0,
            "year": 2025,
        },
        {
            "signal_index": 7,
            "entry_index": 8,
            "exit_index": 8,
            "signal_time": "2026-06-01T00:00:00",
            "entry_time": "2026-05-31T23:00:00",
            "exit_time": "2027-05-31T23:00:00",
            "net_return_bps": 4.0,
            "year": 2026,
        },
        {
            "signal_index": 8,
            "entry_index": 9,
            "exit_index": 9,
            "signal_time": "2027-06-01T00:00:00",
            "entry_time": "2027-05-31T23:00:00",
            "exit_time": "2027-12-30T23:00:00",
            "net_return_bps": 0.0,
            "year": 2027,
        },
        {
            "signal_index": 9,
            "entry_index": 9,
            "exit_index": 9,
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
    return trade_log, bar_dir, tmp_path / "design_matrix.md"


def test_script_runs_on_synthetic_trade_log_and_synthetic_bars(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc, max_trades=20, max_bar_files=5, max_bars=250000)

    assert output_doc.exists()
    assert "No scaler was fitted." in report
    assert "No model was trained." in report
    assert summary["x_row_count"] == 10
    assert summary["y_row_count"] == 10


def test_x_uses_exactly_the_approved_24_model_features(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["x_column_count"] == 24
    assert summary["x_columns_match_contract"] is True
    assert summary["approved_features_present_count"] == 24
    assert summary["approved_features_missing_count"] == 0


def test_y_is_label_keep_only_and_binary(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["y_binary"] is True
    assert summary["y_positive_count"] == 5
    assert summary["y_negative_count"] == 5


def test_x_y_row_alignment_is_preserved(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["x_y_row_alignment"] is True
    assert summary["x_row_count"] == summary["y_row_count"]


def test_forbidden_features_are_excluded_from_x(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["forbidden_features_present_in_x_count"] == 0


def test_audit_identity_columns_are_excluded_from_x(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["identity_columns_present_in_x_count"] == 0


def test_outcome_columns_are_excluded_from_x(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["outcome_columns_present_in_x_count"] == 0


def test_label_keep_is_excluded_from_x(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["label_column_present_in_x"] is False


def test_split_masks_are_mutually_exclusive_and_complete(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["split_mask_exclusive"] is True
    assert summary["split_mask_complete"] is True
    assert summary["train_rows_before_purge"] == 4
    assert summary["validation_rows"] == 2
    assert summary["holdout_rows"] == 2
    assert summary["out_of_protocol_rows"] == 2


def test_purge_and_embargo_masks_are_represented(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["purge_candidate_count"] >= 1
    assert summary["embargo_candidate_count"] >= 1
    assert summary["train_rows_after_purge"] <= summary["train_rows_before_purge"]


def test_train_only_scaler_plan_reports_scaler_fitted_false(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["scaler_required_later"] is True
    assert summary["scaler_fit_scope"] == "train_after_purge_and_embargo_only"
    assert summary["scaler_transform_scope"] == "validation_and_holdout_after_train_fit_only"
    assert summary["scaler_fitted"] is False


def test_validation_and_holdout_are_not_included_in_scaler_fit_scope(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert summary["validation_seen_during_fit"] is False
    assert summary["holdout_seen_during_fit"] is False


def test_no_predictive_metrics_are_computed(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    assert "No predictive metrics were computed." in report
    assert "precision" not in report.lower()
    assert "recall" not in report.lower()


def test_report_contains_required_safety_statements_and_no_alpha_approval_language(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=250000)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No feature-table artifacts were written.",
        "No model artifacts were written.",
        "No strategy backtest was run.",
        "No model was trained.",
        "No scaler was fitted.",
        "No predictive metrics were computed.",
        "No alpha claim is made.",
        "Full reconstruction remains blocked.",
    ]:
        assert expected in report
    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()


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


def test_script_writes_only_the_markdown_report(tmp_path: Path):
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
    assert output_doc.suffix == ".md"
    assert sorted(path.suffix for path in tmp_path.iterdir() if path.is_file()) == [".csv", ".md"]
