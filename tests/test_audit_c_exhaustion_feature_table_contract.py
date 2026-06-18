from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.audit_c_exhaustion_feature_table_contract as audit


def _write_frame(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        frame.to_csv(path, index=False)
        return path
    if path.suffix == ".parquet":
        try:
            frame.to_parquet(path, index=False)
        except Exception as exc:  # pragma: no cover - engine availability varies
            pytest.skip(f"parquet engine unavailable: {exc}")
        return path
    raise AssertionError(f"unsupported suffix: {path.suffix}")


def _bar_frame(start: str, periods: int) -> pd.DataFrame:
    opens = pd.date_range(start, periods=periods, freq="1h", tz="UTC")
    closes = opens + pd.Timedelta("1h")
    return pd.DataFrame(
        {
            "bar_id": list(range(periods)),
            "open_time": opens,
            "close_time": closes,
            "open": [100.0 + idx for idx in range(periods)],
            "high": [100.5 + idx for idx in range(periods)],
            "low": [99.5 + idx for idx in range(periods)],
            "close": [100.25 + idx for idx in range(periods)],
            "volume": [10.0 + idx for idx in range(periods)],
            "volume_delta": [1.0 if idx % 2 == 0 else -1.0 for idx in range(periods)],
            "vol_roll_95": [0.1 + idx for idx in range(periods)],
            "local_low": [99.0 + idx for idx in range(periods)],
            "c_signal": [1 if idx % 2 == 0 else 0 for idx in range(periods)],
            "trade_count": [4 + idx for idx in range(periods)],
        }
    )


def _trade_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_index": 0,
                "entry_index": 1,
                "exit_index": 2,
                "signal_time": "2024-01-01T01:00:00Z",
                "entry_time": "2024-01-01T01:00:00Z",
                "exit_time": "2024-01-01T02:00:00Z",
                "entry_price": 100.5,
                "exit_price": 101.0,
                "gross_return_bps": 12.0,
                "net_return_bps": 10.0,
                "holding_bars": 1,
                "year": 2024,
            },
            {
                "signal_index": 1,
                "entry_index": 2,
                "exit_index": 3,
                "signal_time": "2024-01-01T02:00:00Z",
                "entry_time": "2024-01-01T02:00:00Z",
                "exit_time": "2024-01-01T03:00:00Z",
                "entry_price": 101.5,
                "exit_price": 102.0,
                "gross_return_bps": 14.0,
                "net_return_bps": 11.0,
                "holding_bars": 1,
                "year": 2024,
            },
            {
                "signal_index": 4,
                "entry_index": 5,
                "exit_index": 6,
                "signal_time": "2025-01-01T01:00:00Z",
                "entry_time": "2025-01-01T01:00:00Z",
                "exit_time": "2025-01-01T02:00:00Z",
                "entry_price": 104.5,
                "exit_price": 105.0,
                "gross_return_bps": 16.0,
                "net_return_bps": 13.0,
                "holding_bars": 1,
                "year": 2025,
            },
            {
                "signal_index": 5,
                "entry_index": 6,
                "exit_index": 7,
                "signal_time": "2025-01-01T02:00:00Z",
                "entry_time": "2025-01-01T02:00:00Z",
                "exit_time": "2025-01-01T03:00:00Z",
                "entry_price": 105.5,
                "exit_price": 106.0,
                "gross_return_bps": 18.0,
                "net_return_bps": 15.0,
                "holding_bars": 1,
                "year": 2025,
            },
        ]
    )


def _build_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    trade_log = _write_frame(_trade_frame(), tmp_path / "trade_log.csv")
    bar_dir = tmp_path / "bars_750btc"
    _write_frame(_bar_frame("2024-01-01T00:00:00Z", 4), bar_dir / "BTCUSDT_tier2_750btc_2024-01-01.parquet")
    _write_frame(_bar_frame("2025-01-01T00:00:00Z", 4), bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet")
    return trade_log, bar_dir, tmp_path / "audit.md"


def _contract_row(summary: dict[str, object], name: str) -> dict[str, object]:
    rows = summary["feature_contract_rows"]
    assert isinstance(rows, list)
    for row in rows:
        if row["column"] == name:
            return row
    raise AssertionError(f"missing contract row: {name}")


def test_script_runs_on_synthetic_trade_log_and_bars(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)

    rc = audit.main(
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
    assert "No market-data artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No model was trained." in report
    assert "No predictive metrics were computed." in report
    assert "No alpha claim is made." in report
    assert "Full reconstruction remains blocked." in report
    assert "gate_2_feature_contract_audit_pass" in report


def test_feature_contract_separates_model_features_from_audit_identity_columns(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    assert summary["model_feature_column_count"] == 24
    assert summary["audit_identity_column_count"] == 7
    assert _contract_row(summary, "signal_open")["role"] == "model_feature"
    assert _contract_row(summary, "year")["role"] == "audit_identity"
    assert _contract_row(summary, "signal_return_3_bar")["timestamp_basis"] == "past_bar_close"
    assert _contract_row(summary, "signal_volume_delta")["leakage_safe"] == "true"


def test_outcome_columns_are_excluded_from_model_features(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    feature_table = summary["feature_table"]
    for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps", "holding_bars"]:
        assert column not in feature_table.columns
    assert "year" in feature_table.columns
    assert summary["gate_2_status"] == "pass"


def test_yearly_row_counts_and_null_finite_audit_are_computed(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    yearly = {row["year"]: row for row in summary["yearly_summary"]}
    assert yearly["2024"]["trade_rows"] == 2
    assert yearly["2024"]["feature_rows"] == 2
    assert yearly["2024"]["row_count_preserved"] is True
    assert yearly["2025"]["trade_rows"] == 2
    assert yearly["2025"]["feature_rows"] == 2
    assert yearly["2025"]["row_count_preserved"] is True
    assert summary["feature_null_issue_count_total"] == 0
    assert summary["feature_nonfinite_issue_count_total"] == 0
    assert summary["null_finite_by_year"]["2024"]["signal_return_3_bar"]["null_pct"] > 0.0
    assert summary["null_finite_by_year"]["2025"]["signal_return_3_bar"]["null_pct"] == pytest.approx(0.0)
    assert summary["null_finite_by_year"]["2024"]["signal_return_3_bar"]["finite_pct"] < 100.0
    assert "entry_price" not in summary["stats_by_year"]["2024"]


def test_distribution_summary_uses_model_features_only_and_omits_pnl_metrics(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    assert "## Feature Distribution Sanity Summary" in report
    assert "No predictive metrics were computed." in report
    assert "No model was trained." in report
    assert "entry_price" not in summary["stats_by_year"]["2024"]
    assert "exit_price" not in summary["stats_by_year"]["2024"]


def test_ofi_mlofi_microprice_spread_depth_remain_excluded(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    _report, summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    blocked_rows = summary["blocked_feature_rows"]
    blocked_names = {row["column"] for row in blocked_rows}
    assert summary["blocked_feature_family_count"] == 7
    for name in [
        "OFI / MLOFI",
        "microprice / spread / depth",
        "spoofing / iceberg / L2 whale pressure",
        "absorption proxy",
        "VPIN / toxicity",
        "footprint",
        "funding / OI / liquidation / basis",
        "regime",
    ]:
        assert name in blocked_names or any(name in row["notes"] or name in row["family"] for row in blocked_rows)


def test_report_includes_required_safety_statements_and_no_alpha_approval_language(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    report, _summary = audit.build_report(trade_log, bar_dir, output_doc=None, max_trades=10, max_bar_files=10, max_bars=100)

    for expected in [
        "No raw L2 data was read.",
        "No OFI artifacts were read.",
        "No OFI artifacts were written.",
        "No feature-table artifacts were written.",
        "No market-data artifacts were written.",
        "No strategy backtest was run.",
        "No model was trained.",
        "No predictive metrics were computed.",
        "No alpha claim is made.",
        "Full reconstruction remains blocked.",
    ]:
        assert expected in report
    assert "alpha approval" not in report.lower()
    assert "production use is approved" not in report.lower()


def test_script_does_not_require_seagate_data_for_tests(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)

    rc = audit.main(
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
