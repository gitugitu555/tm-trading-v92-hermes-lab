from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.audit_c_exhaustion_signal_time_feature_availability as audit


def _make_temp_repo(root: Path) -> Path:
    (root / "replays").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "features").mkdir(parents=True, exist_ok=True)

    (root / "replays" / "c_exhaustion_replay.py").write_text(
        "def attach_c_exhaustion_signal(df):\n"
        "    return df\n"
        "def replay_c_exhaustionfade(df):\n"
        "    return df\n"
        "signal_time = 'signal_time'\n"
        "entry_time = 'entry_time'\n"
        "exit_time = 'exit_time'\n",
        encoding="utf-8",
    )
    (root / "scripts" / "run_c_exhaustion_replay.py").write_text(
        "from replays.c_exhaustion_replay import replay_c_exhaustionfade\n",
        encoding="utf-8",
    )
    (root / "scripts" / "diagnose_c_exhaustion_meta_label_baseline.py").write_text(
        "signal_time = 'signal_time'\n",
        encoding="utf-8",
    )
    (root / "scripts" / "diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py").write_text(
        "bad_context_label_36 = True\n",
        encoding="utf-8",
    )
    (root / "scripts" / "diagnose_c_exhaustion_signal_state.py").write_text(
        "signal_time = 'signal_time'\n",
        encoding="utf-8",
    )
    (root / "scripts" / "diagnose_c_exhaustion_regime_context.py").write_text(
        "regime = 'EXHAUSTED'\n",
        encoding="utf-8",
    )
    (root / "features" / "regime_classifier.py").write_text(
        "def add_regime_labels(df):\n    return df\n",
        encoding="utf-8",
    )
    return root


def test_static_only_run_creates_report_and_guardrails(tmp_path: Path):
    repo = _make_temp_repo(tmp_path / "repo")
    out = tmp_path / "audit.md"

    report, summary = audit.build_report(repo)
    out.write_text(report, encoding="utf-8")

    assert out.exists()
    assert "No raw L2 data was read." in report
    assert "No OFI artifacts were read." in report
    assert "No OFI artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "Full reconstruction remains blocked." in report
    assert "alpha claim is made" in report
    assert "gate_1_static_inventory_completed" in report
    assert "data_availability_audit_partial" in report
    assert summary["signal_source_files"]
    assert "replays/c_exhaustion_replay.py" in summary["signal_source_files"]


def test_feature_classifier_marks_ohlcv_available_and_ofi_blocked():
    ohlcv = audit.classify_feature("OHLCV / regime")
    ofi = audit.classify_feature("OFI / MLOFI")
    book = audit.classify_feature("microstructure / book state")

    assert ohlcv["current_eligibility"] == "available_now"
    assert ohlcv["requires_l2"] is False
    assert ohlcv["requires_approved_ofi_artifact"] is False

    assert ofi["requires_l2"] is True
    assert ofi["requires_approved_ofi_artifact"] is True
    assert ofi["current_eligibility"] == "blocked_by_ofi_l2_approval"

    assert book["requires_l2"] is True
    assert book["requires_approved_ofi_artifact"] is True
    assert book["current_eligibility"] == "blocked_by_ofi_l2_approval"


def test_static_inventory_includes_replay_files_when_present(tmp_path: Path):
    repo = _make_temp_repo(tmp_path / "repo")
    report, summary = audit.build_report(repo)

    assert "replays/c_exhaustion_replay.py" in summary["signal_source_files"]
    assert "scripts/run_c_exhaustion_replay.py" in summary["signal_source_files"]
    assert "C_Exhaustion Signal Source" in report


def test_report_does_not_contain_alpha_approval_language(tmp_path: Path):
    repo = _make_temp_repo(tmp_path / "repo")
    report, _summary = audit.build_report(repo)

    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()


def test_optional_schema_audit_reads_only_specified_csv(tmp_path: Path):
    repo = _make_temp_repo(tmp_path / "repo")
    bar_file = tmp_path / "bars.csv"
    trade_log = tmp_path / "trades.csv"

    pd.DataFrame(
        {
            "open_time": [1, 2],
            "close_time": [3, 4],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [10.0, 11.0],
            "volume_delta": [1.0, -1.0],
        }
    ).to_csv(bar_file, index=False)
    pd.DataFrame(
        {
            "signal_time": ["2024-01-01T00:00:00Z"],
            "entry_time": ["2024-01-01T00:05:00Z"],
            "exit_time": ["2024-01-01T01:05:00Z"],
            "net_return_bps": [10.0],
        }
    ).to_csv(trade_log, index=False)

    report, summary = audit.build_report(repo, bar_file=bar_file, trade_log=trade_log)

    assert "optional_schema_audit_completed" in report
    assert "`open_time, close_time, open, high, low, close, volume, volume_delta`" in report
    assert "`signal_time, entry_time, exit_time, net_return_bps`" in report
    assert summary["schema_audits"]
    assert report.count("Optional Schema Audit") == 1
