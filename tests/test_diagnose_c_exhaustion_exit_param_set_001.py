from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.diagnose_c_exhaustion_exit_param_set_001 as src


def _write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except Exception as exc:  # pragma: no cover - parquet engine availability varies
        pytest.skip(f"parquet engine unavailable: {exc}")
    return path


def _bars_for_activation_false() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = []
    highs = [100.20, 100.30, 100.45, 100.49, 200.00, 300.00]
    closes = [100.10, 100.20, 100.30, 100.40, 200.00, 300.00]
    for idx, (high, close) in enumerate(zip(highs, closes, strict=False)):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": high,
                "low": 99.0,
                "close": close,
                "volume": 100.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _bars_for_protective_trigger() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = []
    highs = [100.20, 100.70, 100.40, 100.30, 100.10, 100.10]
    closes = [100.10, 100.20, 100.35, 100.25, 100.05, 100.00]
    for idx, (high, close) in enumerate(zip(highs, closes, strict=False)):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": high,
                "low": 99.0,
                "close": close,
                "volume": 100.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _bars_for_no_trigger() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = []
    highs = [100.20, 100.70, 100.80, 100.90, 100.95, 100.95]
    closes = [100.10, 100.40, 100.70, 100.80, 100.85, 100.90]
    for idx, (high, close) in enumerate(zip(highs, closes, strict=False)):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": high,
                "low": 99.0,
                "close": close,
                "volume": 100.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _bars_for_unavailable_unmatched() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = []
    # One valid window, one window with no finite high/close pair, and no bars for the unmatched trade.
    payload = [
        (100.20, 100.10),
        (100.70, 100.20),
        (100.30, 100.20),
        (float("nan"), 100.20),
    ]
    for idx, (high, close) in enumerate(payload):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": high,
                "low": 99.0,
                "close": close,
                "volume": 100.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _trade_frame_activation_false() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    return pd.DataFrame(
        [
            {
                "signal_index": 0,
                "entry_index": 0,
                "exit_index": 4,
                "signal_time": start,
                "entry_time": start,
                "exit_time": start + pd.Timedelta(hours=4),
                "entry_price": 100.0,
                "exit_price": 100.0,
                "gross_return_bps": 0.0,
                "net_return_bps": -12.0,
                "year": 2025,
            }
        ]
    )


def _trade_frame_protective_trigger() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    return pd.DataFrame(
        [
            {
                "signal_index": 1,
                "entry_index": 0,
                "exit_index": 4,
                "signal_time": start,
                "entry_time": start,
                "exit_time": start + pd.Timedelta(hours=4),
                "entry_price": 100.0,
                "exit_price": 100.0,
                "gross_return_bps": 0.0,
                "net_return_bps": -12.0,
                "year": 2025,
            }
        ]
    )


def _trade_frame_no_trigger() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    return pd.DataFrame(
        [
            {
                "signal_index": 2,
                "entry_index": 0,
                "exit_index": 4,
                "signal_time": start,
                "entry_time": start,
                "exit_time": start + pd.Timedelta(hours=4),
                "entry_price": 100.0,
                "exit_price": 100.0,
                "gross_return_bps": 0.0,
                "net_return_bps": -12.0,
                "year": 2026,
            }
        ]
    )


def _multi_trade_frame() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    rows = [
        {
            "signal_index": 0,
            "entry_index": 0,
            "exit_index": 4,
            "signal_time": start,
            "entry_time": start,
            "exit_time": start + pd.Timedelta(hours=4),
            "entry_price": 100.0,
            "exit_price": 100.0,
            "gross_return_bps": 0.0,
            "net_return_bps": -12.0,
            "year": 2025,
        },
        {
            "signal_index": 1,
            "entry_index": 1,
            "exit_index": 5,
            "signal_time": start + pd.Timedelta(hours=1),
            "entry_time": start + pd.Timedelta(hours=1),
            "exit_time": start + pd.Timedelta(hours=5),
            "entry_price": 100.0,
            "exit_price": 100.90,
            "gross_return_bps": 90.0,
            "net_return_bps": 78.0,
            "year": 2025,
        },
        {
            "signal_index": 2,
            "entry_index": 2,
            "exit_index": 6,
            "signal_time": start + pd.Timedelta(hours=2),
            "entry_time": start + pd.Timedelta(hours=2),
            "exit_time": start + pd.Timedelta(hours=6),
            "entry_price": 100.0,
            "exit_price": 100.85,
            "gross_return_bps": 85.0,
            "net_return_bps": 73.0,
            "year": 2026,
        },
        {
            "signal_index": 3,
            "entry_index": 20,
            "exit_index": 24,
            "signal_time": start + pd.Timedelta(hours=20),
            "entry_time": start + pd.Timedelta(hours=20),
            "exit_time": start + pd.Timedelta(hours=24),
            "entry_price": 100.0,
            "exit_price": 98.0,
            "gross_return_bps": -200.0,
            "net_return_bps": -212.0,
            "year": 2026,
        },
    ]
    return pd.DataFrame(rows)


def _bars_for_multi_trade() -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01T00:00:00")
    highs = [100.20, 100.70, 100.90, 100.95, 100.40, 100.30, float("nan"), 100.10]
    closes = [100.10, 100.20, 100.35, 100.25, 100.80, 100.82, 100.00, 100.00]
    rows = []
    for idx, (high, close) in enumerate(zip(highs, closes, strict=False)):
        open_time = start + pd.Timedelta(hours=idx)
        rows.append(
            {
                "bar_id": idx,
                "open_time": open_time,
                "close_time": open_time + pd.Timedelta(hours=1),
                "open": 100.0,
                "high": high,
                "low": 99.0,
                "close": close,
                "volume": 100.0 + idx,
                "volume_delta": 1.0 if idx % 2 == 0 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def _build_repo(tmp_path: Path, trade_frame: pd.DataFrame, bars_frame: pd.DataFrame) -> tuple[Path, Path, Path]:
    trade_log = tmp_path / "trade_log.csv"
    bar_dir = tmp_path / "bars_750btc"
    output_doc = tmp_path / "report.md"
    trade_frame.to_csv(trade_log, index=False)
    _write_parquet(bars_frame, bar_dir / "BTCUSDT_tier2_750btc_2025-01-01.parquet")
    return trade_log, bar_dir, output_doc


def test_activation_requires_peak_at_least_50_bps():
    evaluated = src._evaluate_trades(_trade_frame_activation_false(), _bars_for_activation_false())
    row = evaluated.iloc[0]
    assert bool(row["activation_triggered"]) is False
    assert bool(row["protective_exit_triggered"]) is False
    assert row["diagnostic_return_bps"] == pytest.approx(0.0)


def test_protective_exit_cannot_occur_before_activation():
    bars = _bars_for_activation_false().copy()
    bars.loc[bars["bar_id"] == 0, "close"] = 99.50  # close below retention threshold, but peak is still below activation
    evaluated = src._evaluate_trades(_trade_frame_activation_false(), bars)
    row = evaluated.iloc[0]
    assert bool(row["activation_triggered"]) is False
    assert bool(row["protective_exit_triggered"]) is False


def test_protective_exit_triggers_when_close_is_below_half_peak_after_activation():
    evaluated = src._evaluate_trades(_trade_frame_protective_trigger(), _bars_for_protective_trigger())
    row = evaluated.iloc[0]
    assert bool(row["activation_triggered"]) is True
    assert bool(row["protective_exit_triggered"]) is True
    assert row["diagnostic_return_bps"] == pytest.approx(20.0)


def test_protective_exit_does_not_trigger_when_close_is_above_half_peak():
    evaluated = src._evaluate_trades(_trade_frame_no_trigger(), _bars_for_no_trigger())
    row = evaluated.iloc[0]
    assert bool(row["activation_triggered"]) is True
    assert bool(row["protective_exit_triggered"]) is False
    assert row["diagnostic_return_bps"] == pytest.approx(0.0)


def test_live_peak_uses_completed_bar_highs_only():
    evaluated = src._evaluate_trades(_trade_frame_protective_trigger(), _bars_for_protective_trigger())
    row = evaluated.iloc[0]
    assert row["live_peak_return_bps"] == pytest.approx(70.0)


def test_decision_return_uses_completed_bar_close_only():
    evaluated = src._evaluate_trades(_trade_frame_protective_trigger(), _bars_for_protective_trigger())
    row = evaluated.iloc[0]
    assert row["diagnostic_return_bps"] == pytest.approx(20.0)


def test_no_final_mfe_is_required():
    trade = _trade_frame_activation_false().drop(columns=["gross_return_bps"]).copy()
    evaluated = src._evaluate_trades(trade, _bars_for_activation_false())
    assert "mfe_bps" not in evaluated.columns
    assert evaluated.iloc[0]["diagnostic_return_bps"] == pytest.approx(0.0)


def test_no_future_bars_are_read_before_decision_bar():
    bars = _bars_for_activation_false().copy()
    bars.loc[bars["bar_id"] >= 4, "high"] = 5000.0
    bars.loc[bars["bar_id"] >= 4, "close"] = 5000.0
    evaluated = src._evaluate_trades(_trade_frame_activation_false(), bars)
    row = evaluated.iloc[0]
    # The large future bars lie at or after the exit timestamp and should be excluded.
    assert bool(row["activation_triggered"]) is False
    assert bool(row["protective_exit_triggered"]) is False


def test_half_open_interval_matching_is_preserved():
    bars = _bars_for_activation_false()
    path = src._interval_path(bars, pd.Timestamp("2025-01-01T00:00:00"), pd.Timestamp("2025-01-01T04:00:00"))
    assert path["open_time"].tolist() == [
        pd.Timestamp("2025-01-01T00:00:00"),
        pd.Timestamp("2025-01-01T01:00:00"),
        pd.Timestamp("2025-01-01T02:00:00"),
        pd.Timestamp("2025-01-01T03:00:00"),
    ]
    assert pd.Timestamp("2025-01-01T04:00:00") not in path["open_time"].tolist()


def test_unavailable_and_unmatched_trades_are_counted_not_dropped():
    trade = pd.DataFrame(
        [
            {
                "signal_index": 0,
                "entry_index": 3,
                "exit_index": 4,
                "signal_time": pd.Timestamp("2025-01-01T03:00:00"),
                "entry_time": pd.Timestamp("2025-01-01T03:00:00"),
                "exit_time": pd.Timestamp("2025-01-01T04:00:00"),
                "entry_price": 100.0,
                "exit_price": 100.0,
                "gross_return_bps": 0.0,
                "net_return_bps": -12.0,
                "year": 2025,
            },
            {
                "signal_index": 1,
                "entry_index": 8,
                "exit_index": 9,
                "signal_time": pd.Timestamp("2025-01-01T08:00:00"),
                "entry_time": pd.Timestamp("2025-01-01T08:00:00"),
                "exit_time": pd.Timestamp("2025-01-01T09:00:00"),
                "entry_price": 100.0,
                "exit_price": 100.0,
                "gross_return_bps": 0.0,
                "net_return_bps": -12.0,
                "year": 2026,
            },
        ]
    )
    evaluated = src._evaluate_trades(trade, _bars_for_unavailable_unmatched())
    assert int((evaluated["source_status"] == "unavailable").sum()) == 1
    assert int((evaluated["source_status"] == "unmatched").sum()) == 1


def test_aggregate_metrics_include_required_split_keys():
    evaluated = src._evaluate_trades(_multi_trade_frame(), _bars_for_multi_trade())
    summary = {
        "full_sample": src._split_metrics(evaluated, "full sample"),
        "split_2020_2023": src._split_metrics(evaluated, "2020-2023"),
        "split_2024_2026": src._split_metrics(evaluated, "2024-2026"),
        "split_2025": src._split_metrics(evaluated, "2025"),
        "split_2026": src._split_metrics(evaluated, "2026"),
    }
    assert summary["full_sample"]["split"] == "full sample"
    assert summary["split_2020_2023"]["split"] == "2020-2023"
    assert summary["split_2024_2026"]["split"] == "2024-2026"
    assert summary["split_2025"]["split"] == "2025"
    assert summary["split_2026"]["split"] == "2026"


def test_cost_ladder_includes_required_bps():
    evaluated = src._evaluate_trades(_multi_trade_frame(), _bars_for_multi_trade())
    summary = src._split_metrics(evaluated, "full sample")
    ladder = summary["diagnostic_net_expectancy_bps"]
    assert set(ladder.keys()) == {"1bps", "2bps", "3bps", "5bps", "8bps", "12bps"}


def test_script_writes_only_output_markdown_doc_and_no_row_level_artifacts(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, _multi_trade_frame(), _bars_for_multi_trade())
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
    files = {p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()}
    assert files == {
        Path("trade_log.csv"),
        Path("bars_750btc/BTCUSDT_tier2_750btc_2025-01-01.parquet"),
        Path("report.md"),
    }


def test_report_contains_safety_statements(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, _multi_trade_frame(), _bars_for_multi_trade())
    report, summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)
    assert "No strategy/replay logic changed." in report
    assert "No backtest engine changed." in report
    assert "Same-bar close diagnostic basis only." in report
    assert "Not paper/live executable." in report
    assert "Alpha remains blocked." in report
    assert summary["decision"] in {
        "fixed_param_set_001_diagnostic_passed_for_review",
        "fixed_param_set_001_diagnostic_failed",
        "fixed_param_set_001_diagnostic_inconclusive",
    }


def test_report_does_not_approve_alpha_paper_live(tmp_path: Path):
    trade_log, bar_dir, output_doc = _build_repo(tmp_path, _multi_trade_frame(), _bars_for_multi_trade())
    report, _summary = src.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=output_doc)
    lower = report.lower()
    assert "alpha remains blocked." in lower
    assert "not paper/live executable." in lower
    assert "paper/live is still blocked." in lower
