from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.diagnose_c_exhaustion_mfe_mae_source_alignment as src


def _write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except Exception as exc:  # pragma: no cover - parquet engine availability varies
        pytest.skip(f"parquet engine unavailable: {exc}")
    return path


def _bars_frame(include_bar_id: bool = True) -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2025-01-01T00:00:00")
    for idx in range(6):
        open_time = start + pd.Timedelta(hours=idx)
        close_time = open_time + pd.Timedelta(hours=1)
        row = {
            "open_time": open_time,
            "close_time": close_time,
            "open": 100.0 + idx,
            "high": 101.0 + idx,
            "low": 99.0 + idx,
            "close": 100.5 + idx,
            "volume": 10.0 + idx,
            "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            "regime": "baseline",
        }
        if include_bar_id:
            row["bar_id"] = idx
        rows.append(row)
    # add a second shard that covers 2026 dates for shard coverage checks
    for idx in range(3):
        open_time = pd.Timestamp("2026-05-09T00:00:00") + pd.Timedelta(hours=idx)
        close_time = open_time + pd.Timedelta(hours=1)
        row = {
            "open_time": open_time,
            "close_time": close_time,
            "open": 110.0 + idx,
            "high": 111.0 + idx,
            "low": 109.0 + idx,
            "close": 110.5 + idx,
            "volume": 20.0 + idx,
            "volume_delta": -1.0 if idx % 2 == 0 else 1.0,
            "regime": "recent",
        }
        if include_bar_id:
            row["bar_id"] = 100 + idx
        rows.append(row)
    return pd.DataFrame(rows)


def _trade_frame(overlap: bool = True) -> pd.DataFrame:
    if overlap:
        rows = [
            {
                "signal_index": 1,
                "entry_index": 2,
                "exit_index": 4,
                "signal_time": pd.Timestamp("2025-01-01T02:00:00"),
                "entry_time": pd.Timestamp("2025-01-01T02:00:00"),
                "exit_time": pd.Timestamp("2025-01-01T04:00:00"),
                "entry_price": 100.0,
                "exit_price": 103.0,
                "net_return_bps": 300.0,
                "gross_return_bps": 310.0,
                "holding_bars": 2,
                "year": 2025,
            },
            {
                "signal_index": 6,
                "entry_index": 6,
                "exit_index": 7,
                "signal_time": pd.Timestamp("2026-05-09T00:00:00"),
                "entry_time": pd.Timestamp("2026-05-09T00:00:00"),
                "exit_time": pd.Timestamp("2026-05-09T01:00:00"),
                "entry_price": 110.0,
                "exit_price": 112.0,
                "net_return_bps": 180.0,
                "gross_return_bps": 190.0,
                "holding_bars": 1,
                "year": 2026,
            },
        ]
    else:
        rows = [
            {
                "signal_index": 50,
                "entry_index": 51,
                "exit_index": 52,
                "signal_time": pd.Timestamp("2027-01-01T00:00:00"),
                "entry_time": pd.Timestamp("2027-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2027-01-01T01:00:00"),
                "entry_price": 100.0,
                "exit_price": 98.0,
                "net_return_bps": -200.0,
                "gross_return_bps": -190.0,
                "holding_bars": 1,
                "year": 2027,
            }
        ]
    return pd.DataFrame(rows)


def _build_repo(tmp_path: Path, include_bar_id: bool = True, overlap: bool = True) -> tuple[Path, Path, Path]:
    trade_log = tmp_path / "trade_log.csv"
    _trade_frame(overlap=overlap).to_csv(trade_log, index=False)
    bar_dir = tmp_path / "bars_750btc"
    bars = _bars_frame(include_bar_id=include_bar_id)
    _write_parquet(bars.iloc[:6], bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet")
    _write_parquet(bars.iloc[6:], bar_dir / "BTCUSDT_tier2_750btc_2026-05-09.parquet")
    return trade_log, bar_dir, tmp_path / "report.md"


def test_computes_trade_and_bar_timestamp_ranges(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    trade_info = summary["trade_info"]
    bar_info = summary["bar_info"]
    assert trade_info["min_signal_time"] == pd.Timestamp("2025-01-01T02:00:00")
    assert trade_info["max_exit_time"] == pd.Timestamp("2026-05-09T01:00:00")
    assert bar_info["min_open_time"] == pd.Timestamp("2025-01-01T00:00:00")
    assert bar_info["max_close_time"] == pd.Timestamp("2026-05-09T03:00:00")


def test_detects_exact_open_and_close_match_rates(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    matches = {row["label"]: row for row in summary["exact_matches"]}
    assert matches["signal_time == bar open_time"]["matched_count"] == 1
    assert matches["signal_time == bar close_time"]["matched_count"] == 1
    assert matches["entry_time == bar open_time"]["matched_count"] == 2
    assert matches["exit_time == bar open_time"]["matched_count"] == 2


def test_computes_interval_overlap_counts_without_mfe_mae(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    conventions = {row["convention"]: row for row in summary["interval_conventions"]}
    assert conventions["half_open_open_time_convention"]["matched_trade_count"] == 2
    assert conventions["closed_open_time_convention"]["matched_trade_count"] == 2
    assert conventions["close_time_convention"]["matched_trade_count"] == 2
    assert conventions["broad_overlap_convention"]["matched_trade_count"] == 2
    assert summary["decision"] == "source_alignment_diagnostic_pass"


def test_computes_nearest_timestamp_distance_without_altering_matching(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    nearest = summary["nearest"]
    assert nearest["signal_time_nearest_open"]["median"] is not None
    assert nearest["signal_time_nearest_close"]["median"] is not None
    assert nearest["entry_time_nearest_open"]["median"] is not None


def test_detects_bar_id_mapping_feasibility(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, include_bar_id=True)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    index_audit = summary["index_audit"]
    assert index_audit["bar_id_available"] is True
    assert index_audit["entry_index_count_in_bar_id"] == 1
    assert index_audit["exit_index_count_in_bar_id"] == 1
    assert index_audit["both_indices_count_in_bar_id"] == 1
    assert index_audit["indices_within_row_range"] is True


def test_handles_missing_bar_id_safely(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, include_bar_id=False)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    index_audit = summary["index_audit"]
    assert index_audit["bar_id_available"] is False
    assert index_audit["entry_index_count_in_bar_id"] is None
    assert index_audit["exit_index_count_in_bar_id"] is None


def test_produces_blocked_decision_when_no_overlap_exists(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, overlap=False)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert summary["decision"] == "source_alignment_diagnostic_blocked"
    assert summary["safe_matching_convention_decision"] == "no_safe_matching_convention_identified"


def test_report_contains_safety_statements(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert output_doc.exists()
    assert "No MFE/MAE was computed." in report
    assert "No giveback classification was performed." in report
    assert "No source-construction script was patched." in report
    assert "No paper/live trading is approved." in report
    assert "No production approval is given." in report
    assert "Alpha is not approved." in report
    assert summary["decision"] in {
        "source_alignment_diagnostic_pass",
        "source_alignment_diagnostic_partial",
        "source_alignment_diagnostic_blocked",
    }


def test_report_does_not_approve_alpha_paper_live(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    lower = report.lower()
    assert "alpha is not approved" in lower
    assert "no paper/live trading is approved" in lower
    assert "no production approval is given" in lower


def test_script_does_not_require_real_trade_log_real_bars_raw_l2_or_ofi_artifacts(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert summary["trade_rows_loaded"] == 2
    assert summary["bar_rows_loaded"] == 9
    assert "raw_l2_data_read: `false`" in report
    assert "ofi_artifacts_read: `false`" in report
