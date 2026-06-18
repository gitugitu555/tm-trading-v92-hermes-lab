from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.audit_c_exhaustion_signal_time_alignment as audit


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


def _trade_log_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _bar_frame(start: str, periods: int, *, freq: str = "5min", include_volume_delta: bool = True) -> pd.DataFrame:
    opens = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    closes = opens + pd.Timedelta(freq)
    data: dict[str, list[object]] = {
        "bar_id": list(range(periods)),
        "open_time": opens,
        "close_time": closes,
        "open": [100.0 + idx for idx in range(periods)],
        "high": [100.5 + idx for idx in range(periods)],
        "low": [99.5 + idx for idx in range(periods)],
        "close": [100.25 + idx for idx in range(periods)],
        "volume": [10.0 + idx for idx in range(periods)],
    }
    if include_volume_delta:
        data["volume_delta"] = [1.0 if idx % 2 == 0 else -1.0 for idx in range(periods)]
    return pd.DataFrame(data)


def _build_repo(
    tmp_path: Path,
    *,
    include_volume_delta: bool = True,
    wrong_day: bool = True,
    include_second_trade_day: bool = False,
) -> tuple[Path, Path, Path]:
    bar_dir = tmp_path / "bars_750btc"
    trade_log = tmp_path / "trade_log.csv"
    output_doc = tmp_path / "audit.md"

    trade_rows = [
        {
            "signal_index": 0,
            "entry_index": 1,
            "exit_index": 2,
            "signal_time": "2024-01-01T00:05:00Z",
            "entry_time": "2024-01-01T00:05:00Z",
            "exit_time": "2024-01-01T00:15:00Z",
            "entry_price": 101.0,
            "exit_price": 102.0,
            "gross_return_bps": 9.9,
            "net_return_bps": 4.9,
            "holding_bars": 1,
            "year": 2024,
        }
    ]
    if include_second_trade_day:
        trade_rows.append(
            {
                "signal_index": 1,
                "entry_index": 2,
                "exit_index": 3,
                "signal_time": "2024-01-02T00:05:00Z",
                "entry_time": "2024-01-02T00:05:00Z",
                "exit_time": "2024-01-02T00:15:00Z",
                "entry_price": 102.0,
                "exit_price": 103.0,
                "gross_return_bps": 9.7,
                "net_return_bps": 4.7,
                "holding_bars": 1,
                "year": 2024,
            }
        )
    _write_frame(_trade_log_frame(trade_rows), trade_log)

    _write_frame(_bar_frame("2024-01-01T00:00:00Z", 4, include_volume_delta=include_volume_delta), bar_dir / "BTCUSDT_tier2_750btc_2024-01-01.parquet")
    _write_frame(_bar_frame("2024-01-01T00:00:00Z", 4, include_volume_delta=include_volume_delta), bar_dir / "BTCUSDT_tier2_750btc_2024-01-02.parquet")
    if wrong_day:
        _write_frame(_bar_frame("2024-01-01T00:00:00Z", 4, include_volume_delta=include_volume_delta), bar_dir / "BTCUSDT_tier2_750btc_2024-01-03.parquet")

    return trade_log, bar_dir, output_doc


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
    assert "No market-data artifacts were written." in report
    assert "No strategy backtest was run." in report
    assert "No alpha claim is made." in report
    assert "Full reconstruction remains blocked." in report
    assert "gate_1_alignment_audit_completed" in report


def test_relevant_bar_shard_discovery_does_not_use_wrong_day_fallback(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path, wrong_day=True, include_second_trade_day=True)

    report, summary = audit.build_report(
        trade_log=trade_log,
        bar_dir=bar_dir,
        output_doc=None,
        max_trades=10,
        max_bar_files=10,
        max_bars=100,
    )

    selected = [path.name for path in summary["bar_files"]]
    assert "BTCUSDT_tier2_750btc_2024-01-03.parquet" not in selected
    assert "BTCUSDT_tier2_750btc_2024-01-01.parquet" in selected
    assert "BTCUSDT_tier2_750btc_2024-01-02.parquet" in selected
    assert "2024-01-03" not in report


def test_index_alignment_and_match_rates_are_computed(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path)

    report, summary = audit.build_report(
        trade_log=trade_log,
        bar_dir=bar_dir,
        output_doc=None,
        max_trades=10,
        max_bar_files=10,
        max_bars=100,
    )

    metrics = summary["alignment"]
    assert metrics["signal_index_in_range_pct"] == pytest.approx(100.0)
    assert metrics["entry_index_in_range_pct"] == pytest.approx(100.0)
    assert metrics["exit_index_in_range_pct"] == pytest.approx(100.0)
    assert metrics["signal_lte_entry_lte_exit_index_pct"] == pytest.approx(100.0)
    assert metrics["holding_bars_consistency_pct"] == pytest.approx(100.0)
    assert "signal_time_matches_signal_bar_close_pct" in report
    assert "entry_time_matches_entry_bar_open_pct" in report
    assert "exit_time_matches_exit_bar_close_pct" in report


def test_signal_close_entry_open_exit_close_convention_is_detected(tmp_path: Path):
    trade_log = tmp_path / "trade_log.csv"
    bar_dir = tmp_path / "bars_750btc"
    output_doc = tmp_path / "audit.md"
    _write_frame(
        _trade_log_frame(
            [
                {
                    "signal_index": 0,
                    "entry_index": 1,
                    "exit_index": 2,
                    "signal_time": "2024-01-01T00:05:00Z",
                    "entry_time": "2024-01-01T00:05:00Z",
                    "exit_time": "2024-01-01T00:15:00Z",
                    "holding_bars": 1,
                },
                {
                    "signal_index": 1,
                    "entry_index": 2,
                    "exit_index": 3,
                    "signal_time": "2024-01-01T00:10:00Z",
                    "entry_time": "2024-01-01T00:10:00Z",
                    "exit_time": "2024-01-01T00:20:00Z",
                    "holding_bars": 1,
                },
            ]
        ),
        trade_log,
    )
    _write_frame(_bar_frame("2024-01-01T00:00:00Z", 5), bar_dir / "BTCUSDT_tier2_750btc_2024-01-01.parquet")

    report, summary = audit.build_report(
        trade_log=trade_log,
        bar_dir=bar_dir,
        output_doc=output_doc,
        max_trades=10,
        max_bar_files=10,
        max_bars=100,
    )

    assert summary["alignment"]["timestamp_convention"] == "signal_close_entry_open_exit_close"
    assert "signal_close_entry_open_exit_close" in report


def test_mixed_convention_is_reported_when_match_rates_conflict(tmp_path: Path):
    trade_log = tmp_path / "trade_log.csv"
    bar_dir = tmp_path / "bars_750btc"
    _write_frame(
        _trade_log_frame(
            [
                {
                    "signal_index": 0,
                    "entry_index": 1,
                    "exit_index": 2,
                    "signal_time": "2024-01-01T00:05:00Z",
                    "entry_time": "2024-01-01T00:05:00Z",
                    "exit_time": "2024-01-01T00:15:00Z",
                },
                {
                    "signal_index": 1,
                    "entry_index": 2,
                    "exit_index": 3,
                    "signal_time": "2024-01-01T00:10:00Z",
                    "entry_time": "2024-01-01T00:10:00Z",
                    "exit_time": "2024-01-01T00:20:00Z",
                },
                {
                    "signal_index": 2,
                    "entry_index": 3,
                    "exit_index": 4,
                    "signal_time": "2024-01-01T00:15:00Z",
                    "entry_time": "2024-01-01T00:15:00Z",
                    "exit_time": "2024-01-01T00:20:00Z",
                },
            ]
        ),
        trade_log,
    )
    _write_frame(_bar_frame("2024-01-01T00:00:00Z", 6), bar_dir / "BTCUSDT_tier2_750btc_2024-01-01.parquet")

    report, summary = audit.build_report(
        trade_log=trade_log,
        bar_dir=bar_dir,
        output_doc=None,
        max_trades=10,
        max_bar_files=10,
        max_bars=100,
    )

    assert summary["alignment"]["timestamp_convention"] == "mixed"
    assert "mixed" in report


def test_volume_delta_presence_is_reported_true_when_column_exists(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path, include_volume_delta=True)
    report, summary = audit.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None)

    assert summary["volume_delta_present"] is True
    assert "- volume_delta column present: `true`" in report
    assert "- volume_delta usable for future Gate 2 schema-only feature table: `true`" in report


def test_volume_delta_presence_is_reported_false_when_column_is_absent(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path, include_volume_delta=False)
    report, summary = audit.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None)

    assert summary["volume_delta_present"] is False
    assert "- volume_delta column present: `false`" in report
    assert "- volume_delta usable for future Gate 2 schema-only feature table: `false`" in report


def test_report_includes_safety_statements_and_no_alpha_approval_language(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path)
    report, _summary = audit.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None)

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


def test_script_does_not_require_seagate_data_or_raw_l2_paths(tmp_path: Path):
    trade_log, bar_dir, _output_doc = _build_repo(tmp_path)
    report, summary = audit.build_report(trade_log=trade_log, bar_dir=bar_dir, output_doc=None)

    assert "/mnt/seagate" not in report
    assert all(str(path).startswith(str(tmp_path)) for path in summary["bar_files"])
