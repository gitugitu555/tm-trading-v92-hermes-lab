from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.audit_c_exhaustion_signal_time_schema as audit


def _make_temp_repo(root: Path) -> Path:
    for rel in [
        "replays",
        "scripts",
        "features",
        "docs",
        "reports/c_exhaustion_replay_post_regime_fix",
        "bars_750btc",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)

    (root / "replays" / "c_exhaustion_replay.py").write_text(
        "def attach_c_exhaustion_signal(df):\n"
        "    return df\n"
        "def replay_c_exhaustionfade(df):\n"
        "    return df\n",
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
        "regime = 'EXHAUSTED'\n",
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
    (root / "docs" / "v92_C_EXHAUSTION_SIGNAL_TIME_FEATURE_AVAILABILITY_AUDIT.md").write_text(
        "placeholder",
        encoding="utf-8",
    )
    (root / "docs" / "v92_ORDER_FLOW_FEATURE_INTEGRATION_PLAN.md").write_text(
        "placeholder",
        encoding="utf-8",
    )
    return root


def _write_table(frame: pd.DataFrame, path: Path) -> Path:
    if path.suffix == ".csv":
        frame.to_csv(path, index=False)
        return path
    if path.suffix == ".parquet":
        try:
            frame.to_parquet(path, index=False)
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"parquet engine unavailable: {exc}")
        return path
    raise AssertionError(f"unsupported format: {path.suffix}")


def _base_bar_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open_time": ["2024-01-01T00:00:00Z", "2024-01-01T00:05:00Z"],
            "close_time": ["2024-01-01T00:05:00Z", "2024-01-01T00:10:00Z"],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [10.0, 11.0],
            "volume_delta": [1.5, -0.5],
            "regime": ["EXHAUSTED", "EXHAUSTED"],
            "vol_roll_95": [0.12, 0.13],
            "local_low": [99.0, 100.0],
            "c_signal": [1, 0],
            "trade_count": [4, 5],
        }
    )


def _base_trade_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "signal_time": ["2024-01-01T00:05:00Z", "2024-01-01T00:10:00Z"],
            "entry_time": ["2024-01-01T00:10:00Z", "2024-01-01T00:15:00Z"],
            "exit_time": ["2024-01-01T00:20:00Z", "2024-01-01T00:25:00Z"],
            "signal_index": [1, 2],
            "entry_index": [2, 3],
            "exit_index": [4, 5],
            "side": ["long", "short"],
            "entry_price": [100.5, 101.5],
            "exit_price": [101.0, 101.0],
            "pnl_bps": [12.0, -3.0],
            "regime": ["EXHAUSTED", "EXHAUSTED"],
        }
    )


def _bind_temp_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(audit, "ROOT", repo, raising=False)
    monkeypatch.setattr(
        audit,
        "REPLAY_PATH_CANDIDATES",
        [repo / "reports" / "c_exhaustion_replay_post_regime_fix" / "trade_log.csv"],
        raising=False,
    )
    monkeypatch.setattr(audit, "DEFAULT_BAR_DIR", repo / "bars_750btc", raising=False)


def _feature_row(summary: dict[str, object], name: str) -> dict[str, object]:
    rows = summary["feature_rows"]
    assert isinstance(rows, list)
    for row in rows:
        if row["feature_family"] == name:
            return row
    raise AssertionError(f"missing feature row: {name}")


def test_static_mode_succeeds_without_real_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _make_temp_repo(tmp_path / "repo")
    _bind_temp_repo(monkeypatch, repo)
    out = tmp_path / "audit.md"

    rc = audit.main(["--output-doc", str(out)])

    report = out.read_text(encoding="utf-8")

    assert rc == 0
    assert out.exists()
    assert "No raw L2 data was read." in report
    assert "No OFI artifacts were read." in report
    assert "No OFI artifacts were written." in report
    assert "No market-data artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No alpha claim is made." in report
    assert "Full reconstruction remains blocked." in report
    assert "gate_1_schema_audit_completed_or_partial" in report


@pytest.mark.parametrize("storage_format", [".csv", ".parquet"])
def test_explicit_schema_audit_inspects_bar_and_trade_log_files(
    tmp_path: Path, storage_format: str
):
    repo = _make_temp_repo(tmp_path / "repo")
    bar_file = _write_table(_base_bar_frame(), tmp_path / f"bars{storage_format}")
    trade_log = _write_table(_base_trade_frame(), tmp_path / f"trades{storage_format}")

    report, summary = audit.build_report(repo, bar_file=bar_file, trade_log=trade_log, max_rows=10)

    assert "## Current Signal-Time Columns / Inputs" in report
    assert "signal_time" in report
    assert "entry_time" in report
    assert "exit_time" in report
    assert "open_time" in report
    assert "close_time" in report
    assert "volume_delta" in report
    assert "signal_time_lte_entry_time: `True`" in report
    assert "entry_time_lte_exit_time: `True`" in report
    assert "open_time_lte_close_time: `True`" in report
    assert "signal_time values appear within inspected bar range: `True`" in report
    assert "matching timestamp basis: `mixed`" in report
    assert "full join avoided: `true`" in report
    assert "Optional Schema Audit" not in report
    assert "alpha approval" not in report.lower()
    assert summary["gate_1_status"] == "pass"


def test_static_inventory_includes_replay_files_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _make_temp_repo(tmp_path / "repo")
    bar_file = _write_table(_base_bar_frame(), repo / "bars_750btc" / "BTCUSDT_tier2_750btc_2024-01.parquet")
    trade_log = _write_table(
        _base_trade_frame(),
        repo / "reports" / "c_exhaustion_replay_post_regime_fix" / "trade_log.csv",
    )
    _bind_temp_repo(monkeypatch, repo)

    report, summary = audit.build_report(repo, bar_file=bar_file, trade_log=trade_log, max_rows=10)

    assert any(path.endswith("replays/c_exhaustion_replay.py") for path in summary["signal_source_files"])
    assert any(path.endswith("scripts/run_c_exhaustion_replay.py") for path in summary["signal_source_files"])
    assert any(path.endswith("scripts/diagnose_c_exhaustion_signal_state.py") for path in summary["signal_source_files"])
    assert "## Candidate Files" in report


def test_feature_classifier_marks_ohlcv_available_and_ofi_blocked(tmp_path: Path):
    repo = _make_temp_repo(tmp_path / "repo")
    bar_file = _write_table(_base_bar_frame(), tmp_path / "bars.csv")
    trade_log = _write_table(_base_trade_frame(), tmp_path / "trades.csv")

    report, summary = audit.build_report(repo, bar_file=bar_file, trade_log=trade_log, max_rows=10)

    ohlcv = _feature_row(summary, "OHLCV context")
    regime = _feature_row(summary, "regime")
    ofi = _feature_row(summary, "OFI / MLOFI")
    book = _feature_row(summary, "microprice / spread / depth")

    assert ohlcv["eligible_now"] == "yes"
    assert ohlcv["requires_l2_or_ofi_approval"] == "no"
    assert regime["eligible_now"] == "yes"
    assert regime["requires_l2_or_ofi_approval"] == "no"
    assert ofi["eligible_now"] == "no"
    assert ofi["requires_l2_or_ofi_approval"] == "yes"
    assert book["eligible_now"] == "no"
    assert book["requires_l2_or_ofi_approval"] == "yes"
    assert "volume_delta" in report


def test_report_contains_required_safety_statements_and_no_alpha_approval_language(
    tmp_path: Path,
):
    repo = _make_temp_repo(tmp_path / "repo")
    report, _summary = audit.build_report(repo)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No market-data artifacts were written.",
        "No strategy backtest was run.",
        "No alpha claim is made.",
        "Full reconstruction remains blocked.",
    ]:
        assert expected in report
    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()
