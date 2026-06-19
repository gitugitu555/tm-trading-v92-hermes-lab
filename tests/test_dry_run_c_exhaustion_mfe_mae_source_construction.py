from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.dry_run_c_exhaustion_mfe_mae_source_construction as src


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
    for idx in range(30):
        open_time = start + pd.Timedelta(hours=idx)
        close_time = open_time + pd.Timedelta(hours=1)
        open_price = 100.0
        high = 101.0
        low = 99.0
        close = 100.0
        if 1 <= idx <= 3:
            high = 100.0 - (idx - 1)
            low = 97.0 - (idx - 1)
        elif 5 <= idx <= 7:
            high = [102.0, 105.0, 104.0][idx - 5]
            low = [99.0, 98.0, 97.0][idx - 5]
        elif 9 <= idx <= 11:
            high = [110.0, 108.0, 105.0][idx - 9]
            low = [99.0, 98.0, 97.0][idx - 9]
        elif 13 <= idx <= 15:
            high = [110.0, 109.0, 108.0][idx - 13]
            low = [99.0, 98.0, 97.0][idx - 13]
        elif 17 <= idx <= 19:
            high = [103.0, 102.0, 101.0][idx - 17]
            low = [98.0, 97.0, 96.0][idx - 17]
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": close_time,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 10.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _trade_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = []
    specs = [
        # bad_entry_loss
        (0, 1, 4, 2025, 100.0, 98.0, -200.0, -212.0),
        # giveback_loss
        (4, 5, 8, 2025, 100.0, 98.0, -200.0, -212.0),
        # weak_positive_exit
        (8, 9, 12, 2026, 100.0, 103.0, 300.0, 288.0),
        # clean_winner
        (12, 13, 16, 2026, 100.0, 107.0, 700.0, 688.0),
        # unresolved: exit beyond bar coverage
        (16, 17, 40, 2026, 100.0, 101.0, 100.0, 88.0),
    ]
    for signal_idx, entry_idx, exit_idx, year, entry_price, exit_price, gross_bps, net_bps in specs:
        rows.append(
            {
                "signal_index": signal_idx,
                "entry_index": entry_idx,
                "exit_index": exit_idx,
                "signal_time": start + pd.Timedelta(hours=signal_idx + 1),
                "entry_time": start + pd.Timedelta(hours=entry_idx),
                "exit_time": start + pd.Timedelta(hours=exit_idx),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "gross_return_bps": gross_bps,
                "net_return_bps": net_bps,
                "holding_bars": exit_idx - entry_idx,
                "year": year,
            }
        )
    return pd.DataFrame(rows)


def _build_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    trade_log = tmp_path / "trade_log.csv"
    _trade_frame().to_csv(trade_log, index=False)
    bar_dir = tmp_path / "bars_750btc"
    _write_parquet(_bars_frame(), bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet")
    return trade_log, bar_dir, tmp_path / "report.md"


def _half_open_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    bars = pd.DataFrame(
        [
            {
                "bar_id": 0,
                "open_time": pd.Timestamp("2025-01-01T00:00:00"),
                "close_time": pd.Timestamp("2025-01-01T01:00:00"),
                "open": 100.0,
                "high": 120.0,
                "low": 99.0,
                "close": 110.0,
                "volume": 10.0,
            },
            {
                "bar_id": 1,
                "open_time": pd.Timestamp("2025-01-01T01:00:00"),
                "close_time": pd.Timestamp("2025-01-01T02:00:00"),
                "open": 200.0,
                "high": 999.0,
                "low": 50.0,
                "close": 150.0,
                "volume": 11.0,
            },
            {
                "bar_id": 2,
                "open_time": pd.Timestamp("2025-01-01T02:00:00"),
                "close_time": pd.Timestamp("2025-01-01T03:00:00"),
                "open": 300.0,
                "high": 310.0,
                "low": 290.0,
                "close": 305.0,
                "volume": 12.0,
            },
        ]
    )
    trades = pd.DataFrame(
        [
            {
                "signal_index": 0,
                "entry_index": 0,
                "exit_index": 1,
                "signal_time": pd.Timestamp("2025-01-01T01:00:00"),
                "entry_time": pd.Timestamp("2025-01-01T00:00:00"),
                "exit_time": pd.Timestamp("2025-01-01T01:00:00"),
                "entry_price": 100.0,
                "exit_price": 101.0,
                "gross_return_bps": 100.0,
                "net_return_bps": 95.0,
                "year": 2025,
            }
        ]
    )
    return trades, bars


def test_computes_long_side_mfe_mae_and_all_classifications(tmp_path: Path):
    trades = _trade_frame()
    bars = _bars_frame()
    diagnostics = src.construct_excursion_table(trades, bars)

    assert set(diagnostics["excursion_class"]) == {
        "bad_entry_loss",
        "giveback_loss",
        "weak_positive_exit",
        "clean_winner",
        "unresolved",
    }
    first = diagnostics.loc[diagnostics["excursion_class"] == "bad_entry_loss"].iloc[0]
    assert first["mfe_bps"] <= 0.0
    assert first["mae_bps"] < 0.0


def test_classifies_bad_entry_loss(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    assert int((diagnostics["excursion_class"] == "bad_entry_loss").sum()) == 1


def test_classifies_giveback_loss(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    assert int((diagnostics["excursion_class"] == "giveback_loss").sum()) == 1


def test_classifies_weak_positive_exit_with_fixed_threshold(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    row = diagnostics.loc[diagnostics["excursion_class"] == "weak_positive_exit"].iloc[0]
    assert row["final_return_bps"] > 0.0
    assert row["mfe_giveback_bps"] >= 0.50 * row["mfe_bps"]


def test_classifies_clean_winner(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    assert int((diagnostics["excursion_class"] == "clean_winner").sum()) == 1


def test_marks_unresolved_when_no_matching_bars_exist(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    assert int((diagnostics["excursion_class"] == "unresolved").sum()) == 1


def test_does_not_change_entry_or_exit_times(tmp_path: Path):
    trades = _trade_frame()
    bars = _bars_frame()
    diagnostics = src.construct_excursion_table(trades, bars)
    matched = diagnostics[diagnostics["row_status"] == "matched"].copy()
    assert matched["entry_time"].equals(trades.loc[:3, "entry_time"].reset_index(drop=True))
    assert matched["exit_time"].equals(trades.loc[:3, "exit_time"].reset_index(drop=True))


def test_does_not_search_alternative_exits(tmp_path: Path):
    diagnostics = src.construct_excursion_table(_trade_frame(), _bars_frame())
    matched = diagnostics[diagnostics["row_status"] == "matched"].copy()
    assert matched["entry_index"].tolist() == [1, 5, 9, 13]
    assert matched["exit_index"].tolist() == [4, 8, 12, 16]


def test_half_open_interval_includes_entry_bar_and_excludes_exit_bar(tmp_path: Path):
    trades, bars = _half_open_fixture()
    diagnostics = src.construct_excursion_table(trades, bars)
    row = diagnostics.iloc[0]
    assert row["row_status"] == "matched"
    assert row["intra_trade_bar_count"] == 1
    assert row["max_favorable_price"] == 120.0
    assert row["max_adverse_price"] == 99.0
    assert row["mfe_bps"] == pytest.approx((120.0 / 100.0 - 1.0) * 10_000.0)
    assert row["exit_time"] == pd.Timestamp("2025-01-01T01:00:00")


def test_does_not_write_row_level_artifacts_and_report_has_safety_statements(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path)
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)

    assert output_doc.exists()
    allowed = {trade_log, bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet", output_doc}
    written_files = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert written_files <= allowed
    assert "No row-level artifacts were written." in report
    assert "No paper/live trading is approved." in report
    assert "No production approval is given." in report
    assert "Alpha is not approved." in report
    assert "source_alignment_patch_applied" in report
    assert "half_open_open_time_convention" in report
    assert summary["decision"] in {
        "bounded_mfe_mae_source_construction_pass",
        "bounded_mfe_mae_source_construction_partial",
        "bounded_mfe_mae_source_construction_blocked",
    }


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
