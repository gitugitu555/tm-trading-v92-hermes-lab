from __future__ import annotations

from pathlib import Path

import polars as pl

import scripts.diagnose_l2_ofi_bar_join_readiness as script


def _write_bar_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(
        {
            "open_time": [1_000_000_000, 2_000_000_000],
            "close_time": [1_500_000_000, 2_500_000_000],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10.0, 11.0],
        }
    )
    frame.write_parquet(path)


def _write_l2_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder", encoding="utf-8")


def test_date_extraction_from_bar_path_and_filename(tmp_path):
    bar_path = tmp_path / "bars_750btc" / "nested" / "BTCUSDT_tier2_750btc_2025-06-28.parquet"
    _write_bar_file(bar_path)

    record = script._infer_bar_metadata(bar_path)

    assert record.date_hint_from_filename == "2025-06-28"
    assert record.date_hint_from_path == "2025-06-28"
    assert record.symbol_hint == "BTCUSDT"
    assert record.bar_size_hint == "750btc"
    assert "open_time" in record.timestamp_column_candidates
    assert "close_time" in record.timestamp_column_candidates


def test_date_extraction_from_l2_path(tmp_path):
    l2_path = tmp_path / "l2" / "BTCUSDT" / "2025-07-01" / "11" / "BTCUSDT_orderbook.parquet.zst"
    _write_l2_file(l2_path)

    record = script._infer_l2_metadata(l2_path)

    assert record.file_date == "2025-07-01"
    assert record.file_hour == "11"


def test_overlap_computation(tmp_path):
    bar_dir = tmp_path / "bars"
    l2_root = tmp_path / "l2"
    _write_bar_file(bar_dir / "BTCUSDT_tier2_750btc_2025-07.parquet")
    _write_bar_file(bar_dir / "BTCUSDT_tier2_750btc_2025-06-28.parquet")
    _write_l2_file(l2_root / "BTCUSDT" / "2025-07-01" / "11" / "BTCUSDT_orderbook.parquet.zst")
    _write_l2_file(l2_root / "BTCUSDT" / "2025-06-28" / "05" / "BTCUSDT_orderbook.parquet.zst")
    _write_l2_file(l2_root / "BTCUSDT" / "2025-08-01" / "05" / "BTCUSDT_orderbook.parquet.zst")

    bar_files, _ = script.discover_bar_files(bar_dir, "BTCUSDT", 500)
    l2_files, _ = script.discover_l2_files(l2_root, "BTCUSDT", 200)
    available_l2_dates, overlap_dates, missing_bars, bar_dates = script._collect_overlap_dates(bar_files, l2_files)

    assert available_l2_dates == ["2025-06-28", "2025-07-01", "2025-08-01"]
    assert overlap_dates == ["2025-06-28", "2025-07-01"]
    assert missing_bars == ["2025-08-01"]
    assert "2025-06-28" in bar_dates or "2025-07" in bar_dates


def test_no_overlap_and_empty_dir_root_causes(tmp_path):
    bar_dir = tmp_path / "empty_bars"
    l2_root = tmp_path / "l2"
    _write_l2_file(l2_root / "BTCUSDT" / "2025-08-01" / "05" / "BTCUSDT_orderbook.parquet.zst")
    bar_files, _ = script.discover_bar_files(bar_dir, "BTCUSDT", 500)
    l2_files, _ = script.discover_l2_files(l2_root, "BTCUSDT", 200)
    _, overlap_dates, missing_bars, _ = script._collect_overlap_dates(bar_files, l2_files)

    assert bar_files == []
    assert overlap_dates == []
    assert missing_bars == ["2025-08-01"]

    report = script.build_report(
        bar_dir=bar_dir,
        l2_root=l2_root,
        max_bar_files=500,
        max_l2_files=200,
        bar_files=bar_files,
        l2_files=l2_files,
        helper_compat={"helper_available": True, "helper_selected_count": 0, "helper_selected_files": [], "helper_errors": []},
        smoke_results=[],
    )
    assert "no_bar_files_found" in report
    assert "no_date_overlap_found" in report
    assert script.PRODUCTION_APPROVAL_STATEMENT in report


def test_bar_dir_discovery_and_smoke_join_preservation(tmp_path):
    bar_dir = tmp_path / "bars_750btc"
    l2_root = tmp_path / "l2"
    _write_bar_file(bar_dir / "BTCUSDT_tier2_750btc_2025-07.parquet")
    _write_l2_file(l2_root / "BTCUSDT" / "2025-07-01" / "11" / "BTCUSDT_orderbook.parquet.zst")

    result = script.run_diagnostic(
        bar_dir=bar_dir,
        l2_root=l2_root,
        max_bar_files=500,
        max_l2_files=200,
        output_doc=tmp_path / "report.md",
    )
    report = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert result["discovered_bar_count"] == 1
    assert result["discovered_l2_count"] == 1
    assert result["selected_overlap_count"] == 1
    assert "join_helper_does_not_locate_bar_files" in report
    assert "join_readiness_smoke_attempted" in report
    assert "bar_count_preserved_in_smoke" in report
    assert script.PRODUCTION_APPROVAL_STATEMENT in report
    assert not any(path.suffix in {".csv", ".json", ".pkl", ".joblib", ".model"} for path in tmp_path.rglob("*") if path.is_file())


def test_report_distinguishes_no_overlap_case(tmp_path):
    bar_dir = tmp_path / "bars"
    l2_root = tmp_path / "l2"
    _write_bar_file(bar_dir / "BTCUSDT_tier2_750btc_2024-01.parquet")
    _write_l2_file(l2_root / "BTCUSDT" / "2025-08-01" / "05" / "BTCUSDT_orderbook.parquet.zst")

    result = script.run_diagnostic(
        bar_dir=bar_dir,
        l2_root=l2_root,
        max_bar_files=500,
        max_l2_files=200,
        output_doc=tmp_path / "report.md",
    )
    report = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert result["selected_overlap_count"] == 0
    assert "no_date_overlap_found" in report
    assert "join_readiness_smoke_attempted" not in report
    assert "join_readiness_smoke_deferred" in report
    assert "bar_count_preservation_not_applicable" in report
    assert "This diagnostic does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction." in report
