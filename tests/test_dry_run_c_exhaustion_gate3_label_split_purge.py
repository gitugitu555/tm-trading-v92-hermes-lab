from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.dry_run_c_exhaustion_gate3_label_split_purge as gate3


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
            "entry_time": "2020-06-01T00:00:00",
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
    return trade_log, bar_dir, tmp_path / "dry_run.md"


def test_script_can_operate_on_synthetic_trade_log_and_synthetic_feature_table(tmp_path: Path):
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

    report = output_doc.read_text(encoding="utf-8")
    assert rc == 0
    assert output_doc.exists()
    assert "real_trade_log_read: `true`" in report
    assert "real_bar_data_read: `true`" in report
    assert "No raw L2 data was read." in report
    assert "No OFI artifacts were read." in report
    assert "No OFI artifacts were written." in report
    assert "No feature-table artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No model was trained." in report
    assert "No predictive metrics were computed." in report
    assert "No alpha claim is made." in report
    assert "gate_3_label_split_purge_dry_run_pass" in report


def test_option_a_label_generation_works_on_synthetic_data():
    labelled = gate3.generate_primary_label(_trade_frame())

    assert labelled.loc[labelled["net_return_bps"] > 0, gate3.PRIMARY_LABEL_NAME].eq(1).all()
    assert labelled.loc[labelled["net_return_bps"] <= 0, gate3.PRIMARY_LABEL_NAME].eq(0).all()


def test_net_return_bps_is_not_included_in_model_features():
    contract = gate3.validate_feature_contract(gate3.APPROVED_MODEL_FEATURES)

    assert contract["outcome_columns_excluded_from_model_features"] is True
    assert "net_return_bps" not in gate3.APPROVED_MODEL_FEATURES


def test_label_keep_is_not_included_in_model_features():
    contract = gate3.validate_feature_contract(gate3.APPROVED_MODEL_FEATURES)

    assert contract["label_column_excluded_from_model_features"] is True


def test_chronological_split_assignment_is_correct():
    frame = gate3.assign_chronological_split(gate3.generate_primary_label(_trade_frame()))
    split_by_year = frame.groupby("year")["split"].first().to_dict()

    assert split_by_year[2020] == "train"
    assert split_by_year[2021] == "train"
    assert split_by_year[2022] == "train"
    assert split_by_year[2023] == "train"
    assert split_by_year[2024] == "validation"
    assert split_by_year[2025] == "holdout"
    assert split_by_year[2026] == "holdout"


def test_out_of_protocol_years_are_flagged():
    frame = gate3.assign_chronological_split(gate3.generate_primary_label(_trade_frame()))
    assert set(frame.loc[frame["split"] == "out_of_protocol", "year"].astype(int)) == {2027}


def test_purge_detection_flags_overlapping_train_intervals():
    frame = gate3.compute_purge_embargo_flags(gate3.assign_chronological_split(gate3.generate_primary_label(_trade_frame())))
    purged = frame[(frame["split"] == "train") & (frame["purge_candidate"])]

    assert len(purged) >= 1
    assert 2023 in set(purged["year"].astype(int))


def test_embargo_detection_flags_rows_near_split_boundaries():
    frame = gate3.compute_purge_embargo_flags(gate3.assign_chronological_split(gate3.generate_primary_label(_trade_frame())))
    embargoed = frame[frame["embargo_candidate"]]

    assert len(embargoed) >= 2
    assert {2023, 2024, 2025, 2026}.intersection(set(embargoed["year"].astype(int)))


def test_feature_contract_detects_missing_approved_features():
    columns = gate3.APPROVED_MODEL_FEATURES[:-1]
    contract = gate3.validate_feature_contract(columns)

    assert contract["approved_features_missing_count"] == 1
    assert contract["approved_features_present_count"] == 23


def test_feature_contract_detects_forbidden_model_columns():
    columns = gate3.APPROVED_MODEL_FEATURES + ["entry_price", "OFI", "microprice"]
    contract = gate3.validate_feature_contract(columns)

    assert contract["forbidden_features_present_in_model_matrix_count"] == 3
    assert "entry_price" in contract["forbidden_present"]
    assert "OFI" in contract["forbidden_present"]
    assert "microprice" in contract["forbidden_present"]


def test_audit_identity_columns_are_excluded_from_model_features():
    contract = gate3.validate_feature_contract(gate3.APPROVED_MODEL_FEATURES)

    assert contract["audit_identity_columns_excluded_from_model_features"] is True


def test_sample_size_readiness_rule_is_computed(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=20)

    assert summary["validation_min_required_count"] >= 1
    assert summary["holdout_min_required_count"] >= 1
    assert summary["validation_sample_size_rule_pass"] is True
    assert summary["holdout_sample_size_rule_pass"] is True


def test_report_contains_required_safety_statements_and_no_alpha_approval_language(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = gate3.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None, max_trades=20, max_bar_files=5, max_bars=20)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No feature-table artifacts were written.",
        "No strategy backtest was run.",
        "No model was trained.",
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
