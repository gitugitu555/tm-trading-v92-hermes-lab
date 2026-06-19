from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.diagnose_c_exhaustion_nonparametric_failure_attribution as src


def _write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except Exception as exc:  # pragma: no cover - parquet engine availability varies
        pytest.skip(f"parquet engine unavailable: {exc}")
    return path


def _bars_frame() -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2020-01-01T00:00:00")
    for idx in range(8):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": [100.5, 101.5, 102.0, 103.0, 104.0, 105.0, 106.0, 200.0][idx],
                "low": [99.5, 99.0, 99.0, 99.0, 99.0, 99.0, 99.0, 99.0][idx],
                "close": [100.2, 100.8, 101.0, 102.0, 103.0, 104.0, 105.0, 150.0][idx],
                "volume": 10.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )

    start_2025 = pd.Timestamp("2025-01-01T00:00:00")
    for idx in range(8):
        open_time = start_2025 + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": 100 + idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": [100.5, 101.0, 105.0, 104.0, 103.0, 102.0, 101.0, 100.0][idx],
                "low": [99.8, 99.7, 99.6, 99.5, 99.4, 99.3, 99.2, 99.1][idx],
                "close": [99.9, 100.0, 104.0, 103.0, 102.0, 99.0, 98.0, 97.0][idx],
                "volume": 20.0 + idx,
                "volume_delta": -1.0 if idx % 2 == 0 else 1.0,
            }
        )

    start_2026 = pd.Timestamp("2026-01-01T00:00:00")
    for idx in range(4):
        open_time = start_2026 + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": 200 + idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": [100.2, 100.6, 100.9, 101.0][idx],
                "low": [99.8, 99.7, 99.6, 99.5][idx],
                "close": [100.1, 100.3, 100.6, 100.8][idx],
                "volume": 30.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )

    return pd.DataFrame(rows)


def _trade_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_index": 0,
                "entry_index": 0,
                "exit_index": 7,
                "signal_time": pd.Timestamp("2020-01-01T00:00:00"),
                "entry_time": pd.Timestamp("2020-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2020-01-01T07:00:00"),
                "entry_price": 100.0,
                "exit_price": 105.0,
                "gross_return_bps": 500.0,
                "net_return_bps": 488.0,
                "year": 2020,
            },
            {
                "signal_index": 100,
                "entry_index": 100,
                "exit_index": 106,
                "signal_time": pd.Timestamp("2025-01-01T00:00:00"),
                "entry_time": pd.Timestamp("2025-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2025-01-01T06:00:00"),
                "entry_price": 100.0,
                "exit_price": 99.0,
                "gross_return_bps": -100.0,
                "net_return_bps": -112.0,
                "year": 2025,
            },
            {
                "signal_index": 200,
                "entry_index": 200,
                "exit_index": 204,
                "signal_time": pd.Timestamp("2026-01-01T00:00:00"),
                "entry_time": pd.Timestamp("2026-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2026-01-01T04:00:00"),
                "entry_price": 100.0,
                "exit_price": 100.8,
                "gross_return_bps": 80.0,
                "net_return_bps": 68.0,
                "year": 2026,
            },
            {
                "signal_index": 999,
                "entry_index": 999,
                "exit_index": 1000,
                "signal_time": pd.Timestamp("2030-01-01T00:00:00"),
                "entry_time": pd.Timestamp("2030-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2030-01-01T01:00:00"),
                "entry_price": 100.0,
                "exit_price": 98.0,
                "gross_return_bps": -200.0,
                "net_return_bps": -212.0,
                "year": 2030,
            },
        ]
    )


def _build_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    trade_log = tmp_path / "trade_log.csv"
    bar_dir = tmp_path / "bars_750btc"
    output_doc = tmp_path / "diagnostic.md"
    _trade_frame().to_csv(trade_log, index=False)
    _write_parquet(_bars_frame(), bar_dir / "BTCUSDT_tier2_750btc_2020-01.parquet")
    return trade_log, bar_dir, output_doc


def test_half_open_matching_excludes_exit_bar(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    trades = pd.read_csv(trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = _bars_frame()
    evaluated = src._evaluate_trades(trades, bars)
    row = evaluated.loc[evaluated["year"] == 2020].iloc[0]

    assert row["match_status"] == "matched"
    assert row["mfe_bps"] == pytest.approx(600.0)
    assert row["checkpoint_return_1_bps"] == pytest.approx(20.0)
    assert row["checkpoint_return_3_bps"] == pytest.approx(100.0)
    assert row["checkpoint_return_6_bps"] == pytest.approx(400.0)
    assert row["mfe_bps"] < 10_000.0


def test_checkpoint_returns_use_only_available_completed_bars(tmp_path: Path):
    trade_log, bar_dir, _ = _build_repo(tmp_path)
    trades = pd.read_csv(trade_log, parse_dates=["signal_time", "entry_time", "exit_time"])
    bars = _bars_frame()
    evaluated = src._evaluate_trades(trades, bars)
    row = evaluated.loc[evaluated["year"] == 2025].iloc[0]

    assert row["checkpoint_return_1_bps"] == pytest.approx(-10.0)
    assert row["checkpoint_return_3_bps"] == pytest.approx(400.0)
    assert row["checkpoint_return_6_bps"] == pytest.approx(-100.0)
    assert row["early_favorable_excursion_6_bps"] == pytest.approx(500.0)
    assert row["early_adverse_excursion_6_bps"] == pytest.approx(-70.0)


def test_unmatched_and_unavailable_rows_are_counted(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert summary["rows_with_matched_bars"] == 3
    assert summary["unmatched_rows"] == 1
    assert summary["unavailable_path_rows"] == 1
    assert "unmatched_rows" in report
    assert "unavailable_path_rows" in report


def test_split_keys_and_context_missing_counts_are_reported(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    _report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert set(summary["splits"].keys()) == {"full sample", "2020-2023", "2024-2026", "2025", "2026"}
    assert summary["years"][2020]["trade_count"] == 1
    assert summary["years"][2025]["trade_count"] == 1
    assert summary["years"][2026]["trade_count"] == 1
    assert any(row["column"] == "regime" and row["status"] == "missing" for row in summary["context_rows"])
    assert any(row["column"] == "signal_state" and row["status"] == "missing" for row in summary["context_rows"])


def test_report_marks_hindsight_only_and_not_a_trading_rule(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    lower = report.lower()
    assert "hindsight-only" in lower
    assert "not a trading rule" in lower
    assert "attribution bins are descriptive only" in lower
    assert "alpha remains blocked" in lower


def test_script_writes_aggregate_markdown_only_and_no_gemini_files(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    rc = src.main(
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
    files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}
    assert files == {
        Path("trade_log.csv"),
        Path("diagnostic.md"),
        Path("bars_750btc/BTCUSDT_tier2_750btc_2020-01.parquet"),
    }
    assert not any(path.name == "manifest-check.yml" for path in tmp_path.rglob("*"))
    assert not any(path.name == "verify_run_manifest.py" for path in tmp_path.rglob("*"))


def test_validation_sections_include_net_expectancy_and_decision_label(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert "net_expectancy_bps_12bps" in report
    assert summary["decision"] in set(src.DECISION_LABELS)
    assert "decision:" in report


def test_remote_layout_remains_unchanged_by_script(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    repo_root = Path(__file__).resolve().parents[1]
    before = __import__("subprocess").run(["git", "-C", str(repo_root), "remote", "-v"], check=True, capture_output=True, text=True).stdout
    _report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)
    after = __import__("subprocess").run(["git", "-C", str(repo_root), "remote", "-v"], check=True, capture_output=True, text=True).stdout

    assert before == after
    assert "upstream" in before
    assert "origin" in before
