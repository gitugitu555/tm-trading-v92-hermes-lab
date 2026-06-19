from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.diagnose_c_exhaustion_fixed_post_mfe_window as src


def _write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except Exception as exc:  # pragma: no cover - parquet engine availability varies
        pytest.skip(f"parquet engine unavailable: {exc}")
    return path


def _bars_frame() -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2025-01-01T00:00:00")
    for idx in range(60):
        open_time = start + pd.Timedelta(hours=idx)
        if idx <= 19:
            highs = [101.0, 110.0, 115.0, 120.0, 119.0, 118.0, 117.0, 116.0, 115.0, 114.0, 113.0, 112.0, 111.0, 110.0, 109.0, 108.0, 107.0, 106.0, 105.0, 104.0]
            closes = [100.0, 101.0, 102.0, 118.0, 117.0, 116.0, 115.0, 114.0, 113.0, 112.0, 111.0, 110.0, 109.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0, 98.0]
        elif idx <= 39:
            highs = [105.0, 110.0, 125.0, 130.0, 129.0, 128.0, 127.0, 126.0, 125.0, 124.0, 123.0, 122.0, 121.0, 120.0, 119.0, 118.0, 117.0, 116.0, 115.0, 114.0]
            closes = [100.0, 101.0, 102.0, 125.0, 124.0, 123.0, 122.0, 121.0, 120.0, 119.0, 118.0, 117.0, 116.0, 115.0, 114.0, 120.0, 119.0, 115.0, 114.0, 113.0]
        else:
            highs = [110.0, 120.0, 130.0, 140.0, 139.0, 138.0, 137.0, 136.0, 135.0, 134.0, 133.0, 132.0, 131.0, 130.0, 129.0, 128.0, 127.0, 126.0, 125.0, 124.0]
            closes = [100.0, 101.0, 102.0, 130.0, 129.0, 128.0, 127.0, 126.0, 125.0, 124.0, 123.0, 122.0, 121.0, 120.0, 119.0, 120.0, 118.0, 125.0, 124.0, 123.0]
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": highs[idx % 20],
                "low": 99.0,
                "close": closes[idx % 20],
                "volume": 10.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _trade_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = [
        {
            "signal_index": 0,
            "entry_index": 1,
            "exit_index": 20,
            "signal_time": start + pd.Timedelta(hours=1),
            "entry_time": start + pd.Timedelta(hours=1),
            "exit_time": start + pd.Timedelta(hours=20),
            "entry_price": 100.0,
            "exit_price": 98.0,
            "gross_return_bps": -200.0,
            "net_return_bps": -220.0,
            "year": 2025,
        },
        {
            "signal_index": 20,
            "entry_index": 21,
            "exit_index": 37,
            "signal_time": start + pd.Timedelta(hours=20 + 1),
            "entry_time": start + pd.Timedelta(hours=21),
            "exit_time": start + pd.Timedelta(hours=37),
            "entry_price": 100.0,
            "exit_price": 115.0,
            "gross_return_bps": 1500.0,
            "net_return_bps": 1480.0,
            "year": 2025,
        },
        {
            "signal_index": 40,
            "entry_index": 41,
            "exit_index": 57,
            "signal_time": start + pd.Timedelta(hours=41),
            "entry_time": start + pd.Timedelta(hours=41),
            "exit_time": start + pd.Timedelta(hours=57),
            "entry_price": 100.0,
            "exit_price": 125.0,
            "gross_return_bps": 2500.0,
            "net_return_bps": 2480.0,
            "year": 2026,
        },
        {
            "signal_index": 54,
            "entry_index": 55,
            "exit_index": 59,
            "signal_time": start + pd.Timedelta(hours=55),
            "entry_time": start + pd.Timedelta(hours=55),
            "exit_time": start + pd.Timedelta(hours=59),
            "entry_price": 100.0,
            "exit_price": 98.0,
            "gross_return_bps": -200.0,
            "net_return_bps": -220.0,
            "year": 2026,
        },
    ]
    return pd.DataFrame(rows)


def _build_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    trade_log = tmp_path / "trade_log.csv"
    trade_log.parent.mkdir(parents=True, exist_ok=True)
    _trade_frame().to_csv(trade_log, index=False)
    bar_dir = tmp_path / "bars_750btc"
    _write_parquet(_bars_frame(), bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet")
    return trade_log, bar_dir, tmp_path / "report.md"


def test_identifies_first_mfe_bar_for_long_side_trade():
    diagnostics = src._diagnostic_frame(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["signal_index"] == 0].iloc[0]
    assert row["row_status"] == "matched"
    assert row["time_to_mfe_bars"] == pytest.approx(2.0)
    assert bool(row["mfe_plus_12_available"]) is True


def test_computes_mfe_plus_12_when_window_is_available():
    diagnostics = src._diagnostic_frame(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["signal_index"] == 0].iloc[0]
    assert bool(row["mfe_plus_12_available"]) is True
    assert row["mfe_plus_12_return_bps"] == pytest.approx(600.0)


def test_marks_insufficient_post_mfe_window():
    diagnostics = src._diagnostic_frame(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["signal_index"] == 54].iloc[0]
    assert bool(row["mfe_plus_12_available"]) is False
    assert row["mfe_plus_12_status"] == "insufficient_post_mfe_window"


def test_computes_mfe_plus_12_giveback_bps():
    diagnostics = src._diagnostic_frame(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["signal_index"] == 0].iloc[0]
    assert row["mfe_plus_12_giveback_bps"] == pytest.approx(1400.0)


def test_computes_retained_mfe_ratio_and_flags():
    diagnostics = src._diagnostic_frame(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["signal_index"] == 0].iloc[0]
    assert row["mfe_plus_12_retained_mfe_ratio"] == pytest.approx(0.3)
    assert bool(row["still_positive_at_mfe_plus_12"]) is True
    assert bool(row["lost_more_than_50pct_mfe_by_mfe_plus_12"]) is True


def test_does_not_test_alternative_review_windows(tmp_path: Path):
    assert src.POST_MFE_WINDOW_BARS == 12
    trade_log, bar_dir, output_doc = _build_repo(tmp_path / "alt_windows")
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)
    assert "no alternative review windows were tested" in report.lower()
    assert "fixed_post_mfe_review_window" in report
    assert summary["decision"] in {
        "fixed_post_mfe_review_window_diagnostic_pass",
        "fixed_post_mfe_review_window_diagnostic_partial",
        "fixed_post_mfe_review_window_diagnostic_blocked",
    }


def test_does_not_write_row_level_artifacts(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert output_doc.exists()
    assert "No row-level artifacts were written." in report
    assert "No paper/live trading is approved." in report
    assert "No production approval is given." in report
    assert "Alpha is not approved." in report
    assert summary["decision"] in {
        "fixed_post_mfe_review_window_diagnostic_pass",
        "fixed_post_mfe_review_window_diagnostic_partial",
        "fixed_post_mfe_review_window_diagnostic_blocked",
    }
    allowed = {trade_log, bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet", output_doc}
    assert {p for p in tmp_path.rglob("*") if p.is_file()} <= allowed


def test_report_contains_required_safety_statements(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert "No exit optimization was performed." in report
    assert "No alternative review windows were tested." in report
    assert "No paper/live trading is approved." in report
    assert "No production approval is given." in report
    assert "Alpha is not approved." in report


def test_report_does_not_approve_alpha_paper_live(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    lower = report.lower()
    assert "no paper/live trading is approved." in lower
    assert "no production approval is given." in lower
    assert "alpha is not approved." in lower


def test_main_writes_only_markdown_report(tmp_path: Path):
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
    assert output_doc.suffix == ".md"
    allowed = {trade_log, bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet", output_doc}
    assert {p for p in tmp_path.rglob("*") if p.is_file()} <= allowed
