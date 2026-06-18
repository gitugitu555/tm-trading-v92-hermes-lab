from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.check_c_exhaustion_gate3_protocol as gate3


def test_approved_feature_contract_has_exactly_24_model_features():
    assert len(gate3.APPROVED_MODEL_FEATURES) == 24


def test_audit_identity_columns_are_not_model_features():
    assert all(column not in gate3.APPROVED_MODEL_FEATURES for column in gate3.AUDIT_IDENTITY_COLUMNS)


def test_forbidden_columns_are_detected_if_present_in_model_columns():
    df = gate3._synthetic_fixture()
    model_frame = gate3._build_model_frame(df, include_forbidden=True)
    result = gate3.validate_feature_contract(model_frame.columns)

    assert result["forbidden_features_detected_count"] > 0
    assert "entry_price" in result["forbidden_detected"]
    assert "OFI" in result["forbidden_detected"]


def test_option_a_label_generation_works_and_does_not_add_net_return_bps_to_model_features():
    df = gate3._synthetic_fixture()
    labelled = gate3.generate_primary_label(df)

    assert gate3.PRIMARY_LABEL_NAME in labelled.columns
    assert labelled.loc[labelled["net_return_bps"] > 0, gate3.PRIMARY_LABEL_NAME].eq(1).all()
    assert labelled.loc[labelled["net_return_bps"] <= 0, gate3.PRIMARY_LABEL_NAME].eq(0).all()
    assert "net_return_bps" not in gate3.APPROVED_MODEL_FEATURES


def test_chronological_split_assignment_maps_years_correctly():
    df = gate3.assign_chronological_split(gate3.generate_primary_label(gate3._synthetic_fixture()))
    split_by_year = df.groupby("year")["split"].first().to_dict()

    assert split_by_year[2020] == "train"
    assert split_by_year[2021] == "train"
    assert split_by_year[2022] == "train"
    assert split_by_year[2023] == "train"
    assert split_by_year[2024] == "validation"
    assert split_by_year[2025] == "holdout"
    assert split_by_year[2026] == "holdout"
    assert split_by_year[2027] == "out_of_protocol"


def test_out_of_protocol_years_are_flagged():
    df = gate3.assign_chronological_split(gate3.generate_primary_label(gate3._synthetic_fixture()))
    out_of_protocol = df[df["split"] == "out_of_protocol"]

    assert not out_of_protocol.empty
    assert set(out_of_protocol["year"].astype(int)) == {2027}


def test_purge_detection_flags_overlapping_train_intervals():
    df = gate3.assign_chronological_split(gate3.generate_primary_label(gate3._synthetic_fixture()))
    purged = gate3.compute_purge_flags(df, gate3.DEFAULT_EMBARGO)
    train_purges = purged[(purged["split"] == "train") & (purged["purge_candidate"])]

    assert len(train_purges) >= 1
    assert any(row.year == 2023 for row in train_purges.itertuples(index=False))


def test_embargo_detection_flags_boundary_near_rows():
    df = gate3.assign_chronological_split(gate3.generate_primary_label(gate3._synthetic_fixture()))
    purged = gate3.compute_purge_flags(df, gate3.DEFAULT_EMBARGO)
    embargoed = purged[purged["embargo_candidate"]]

    assert len(embargoed) >= 2
    assert any(row.year == 2023 for row in embargoed.itertuples(index=False))
    assert any(row.year == 2024 for row in embargoed.itertuples(index=False))


def test_report_contains_required_safety_statements(tmp_path: Path):
    output = tmp_path / "protocol.md"
    report, summary = gate3.build_report(output_doc=output)

    assert output.exists()
    assert "No real trade log was read." in report
    assert "No real bar data was read." in report
    assert "No raw L2 data was read." in report
    assert "No OFI artifacts were read." in report
    assert "No OFI artifacts were written." in report
    assert "No feature-table artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No model was trained." in report
    assert "No predictive metrics were computed." in report
    assert "No alpha claim is made." in report
    assert "Full reconstruction remains blocked." in report
    assert summary["protocol_pass"] is True
    assert summary["synthetic_fixture_only"] is True


def test_report_does_not_contain_alpha_approval_language(tmp_path: Path):
    report, _summary = gate3.build_report(output_doc=tmp_path / "protocol.md")

    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()


def test_script_does_not_read_real_trade_logs_real_bars_raw_l2_or_ofi_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def _fail(*_args, **_kwargs):
        raise AssertionError("unexpected real-data read")

    monkeypatch.setattr(pd, "read_csv", _fail)
    monkeypatch.setattr(pd, "read_parquet", _fail)

    output = tmp_path / "protocol.md"
    rc = gate3.main(["--output-doc", str(output)])

    assert rc == 0
    assert output.exists()


def test_script_writes_only_the_markdown_report(tmp_path: Path):
    output = tmp_path / "protocol.md"
    rc = gate3.main(["--output-doc", str(output)])

    assert rc == 0
    assert output.exists()
    assert output.suffix == ".md"
    assert sorted(p.suffix for p in tmp_path.iterdir()) == [".md"]
