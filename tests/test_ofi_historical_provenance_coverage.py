from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.audit_ofi_historical_provenance_coverage as audit


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_missing_ofi_dir_produces_unavailable_inventory(tmp_path: Path):
    bar_dir = tmp_path / "bars"
    ofi_dir = tmp_path / "missing_ofi"
    _write_csv(
        bar_dir / "BTCUSDT_tier2_750btc_2024-01.csv",
        pd.DataFrame(
            {
                "open_time": [1, 2],
                "close_time": [2, 3],
                "open": [100.0, 101.0],
                "high": [101.0, 102.0],
                "low": [99.0, 100.0],
                "close": [100.5, 101.5],
                "volume": [500.0, 500.0],
                "volume_delta": [10.0, -10.0],
            }
        ),
    )

    report = audit.build_report(bar_dir, ofi_dir)

    assert "historical_ofi_file_inventory = unavailable" in report
    assert "blocked_no_historical_ofi_files" in report


def test_bar_volume_delta_available_and_one_sided_flagged(tmp_path: Path):
    bar_path = tmp_path / "BTCUSDT_tier2_750btc_2024-01.csv"
    frame = pd.DataFrame(
        {
            "open_time": [1, 2, 3],
            "close_time": [2, 3, 4],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [500.0, 500.0, 500.0],
            "volume_delta": [5.0, 3.0, 2.0],
        }
    )
    _write_csv(bar_path, frame)

    row = audit.audit_bar_file(bar_path)

    assert row.has_volume_delta is True
    assert row.volume_delta_positive_count == 3
    assert row.volume_delta_negative_count == 0
    assert "positive_only_volume_delta" in row.suspicious_reasons


def test_missing_requires_resync_in_ofi_file_is_flagged(tmp_path: Path):
    ofi_path = tmp_path / "ofi" / "BTCUSDT_ofi_2024-01.csv"
    frame = pd.DataFrame(
        {
            "datetime": ["2024-01-01T00:00:00", "2024-01-01T00:00:01"],
            "ofi": [1.0, -1.0],
        }
    )
    _write_csv(ofi_path, frame)

    row = audit.audit_ofi_file(ofi_path)
    reasons = audit._flags_for_ofi(row.__dict__)

    assert row.has_ofi is True
    assert row.has_requires_resync is False
    assert "requires_resync_missing" in reasons
    assert "sequence_gap_tracking_missing" in reasons


def test_report_includes_no_approval_statement(tmp_path: Path):
    bar_dir = tmp_path / "bars"
    ofi_dir = tmp_path / "ofi"
    _write_csv(
        bar_dir / "BTCUSDT_tier2_750btc_2024-01.csv",
        pd.DataFrame(
            {
                "open_time": [1],
                "close_time": [2],
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [500.0],
                "volume_delta": [10.0],
            }
        ),
    )

    report = audit.build_report(bar_dir, ofi_dir)

    assert "This audit does not approve OFI for production, paper trading, live trading, or alpha use." in report
