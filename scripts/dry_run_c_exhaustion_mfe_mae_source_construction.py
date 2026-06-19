#!/usr/bin/env python3
"""Bounded descriptive MFE/MAE source-construction dry run for C_Exhaustion."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import load_750btc_bars  # noqa: E402

DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_CONSTRUCTION_DRY_RUN.md")
TIMESTAMP_TOLERANCE_MS = 1.0

REQUIRED_TRADE_COLUMNS = [
    "signal_index",
    "entry_index",
    "exit_index",
    "signal_time",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "net_return_bps",
]

OPTIONAL_TRADE_COLUMNS = ["year", "gross_return_bps", "holding_bars"]

REQUIRED_BAR_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]
OPTIONAL_BAR_COLUMNS = ["bar_id", "volume", "volume_delta"]

CLASS_LABELS = ["bad_entry_loss", "giveback_loss", "weak_positive_exit", "clean_winner", "unresolved"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.3f}"
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    return str(value)


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def _parse_timestamp_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if isinstance(parsed, pd.Series):
        return parsed.dt.tz_convert(None)
    return pd.Series(parsed).dt.tz_convert(None)


def _parse_trade_frame(trade_log: Path) -> pd.DataFrame:
    suffix = trade_log.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(trade_log)
    elif suffix == ".parquet":
        frame = pd.read_parquet(trade_log)
    else:  # pragma: no cover - not used in approved task
        raise ValueError(f"Unsupported trade-log type: {trade_log.suffix}")

    missing = [column for column in REQUIRED_TRADE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Trade log is missing required columns: {missing}")

    for column in ["signal_time", "entry_time", "exit_time"]:
        frame[column] = _parse_timestamp_series(frame[column])
    for column in ["signal_index", "entry_index", "exit_index", "year", "holding_bars"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    for column in ["entry_price", "exit_price", "gross_return_bps", "net_return_bps"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "year" not in frame.columns or not frame["year"].notna().any():
        frame["year"] = _parse_timestamp_series(frame["signal_time"]).dt.year.astype("Int64")
    return frame


def _load_bars(bar_dir: Path) -> tuple[pd.DataFrame, list[Path]]:
    bar_files = sorted(bar_dir.glob("BTCUSDT_tier2_750btc_*.parquet"))
    if not bar_files:
        raise FileNotFoundError(f"No 750 BTC parquet shards found in {bar_dir}")
    bars = load_750btc_bars(bar_dir).to_pandas()
    for column in ["open_time", "close_time"]:
        bars[column] = _parse_timestamp_series(bars[column])
    sort_cols = [column for column in ["open_time", "close_time", "bar_id"] if column in bars.columns]
    if sort_cols:
        bars = bars.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    return bars, bar_files


def _within_tolerance(left: object, right: object, tolerance_ms: float = TIMESTAMP_TOLERANCE_MS) -> bool:
    if pd.isna(left) or pd.isna(right):
        return False
    delta_ms = abs((pd.Timestamp(left) - pd.Timestamp(right)).total_seconds() * 1000.0)
    return delta_ms <= tolerance_ms


def _final_return_basis(trades: pd.DataFrame) -> str:
    if "gross_return_bps" in trades.columns and trades["gross_return_bps"].notna().any():
        return "gross_return_bps"
    return "net_return_bps"


def _side_basis(trades: pd.DataFrame) -> str:
    if "side" not in trades.columns:
        return "long-only (assumed; side column absent)"
    side = trades["side"].dropna().astype(str).str.lower()
    if side.empty:
        return "unresolved"
    if side.isin({"long", "buy", "1", "true"}).all():
        return "explicit long-only"
    if side.isin({"short", "sell", "-1", "false"}).all():
        return "explicit short-only"
    return "unresolved"


def construct_excursion_table(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    """Build the in-memory row-level excursion table without writing artifacts."""
    bars = bars.copy().reset_index(drop=True)
    for column in REQUIRED_BAR_COLUMNS:
        if column not in bars.columns:
            raise ValueError(f"Bar data is missing required columns: {column}")
    if "year" not in trades.columns or not trades["year"].notna().any():
        trades = trades.copy()
        trades["year"] = _parse_timestamp_series(trades["signal_time"]).dt.year.astype("Int64")

    final_basis = _final_return_basis(trades)
    matched_rows: list[dict[str, object]] = []
    open_times = bars["open_time"].tolist()
    close_times = bars["close_time"].tolist()
    highs = pd.to_numeric(bars["high"], errors="coerce").to_numpy(dtype=float)
    lows = pd.to_numeric(bars["low"], errors="coerce").to_numpy(dtype=float)

    for row in trades.itertuples(index=False):
        signal_index = getattr(row, "signal_index", pd.NA)
        entry_index = getattr(row, "entry_index", pd.NA)
        exit_index = getattr(row, "exit_index", pd.NA)
        signal_time = getattr(row, "signal_time", pd.NaT)
        entry_time = getattr(row, "entry_time", pd.NaT)
        exit_time = getattr(row, "exit_time", pd.NaT)
        entry_price = getattr(row, "entry_price", np.nan)
        exit_price = getattr(row, "exit_price", np.nan)
        gross_return_bps = getattr(row, "gross_return_bps", np.nan) if "gross_return_bps" in trades.columns else np.nan
        net_return_bps = getattr(row, "net_return_bps", np.nan)
        year = getattr(row, "year", pd.NA)
        holding_bars = getattr(row, "holding_bars", pd.NA) if "holding_bars" in trades.columns else pd.NA

        result: dict[str, object] = {
            "signal_index": signal_index,
            "entry_index": entry_index,
            "exit_index": exit_index,
            "signal_time": signal_time,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "year": year,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_return_bps": gross_return_bps,
            "net_return_bps": net_return_bps,
            "holding_bars": holding_bars,
            "final_return_basis": final_basis,
            "final_return_bps": np.nan,
            "max_favorable_price": np.nan,
            "max_adverse_price": np.nan,
            "mfe_bps": np.nan,
            "mae_bps": np.nan,
            "time_to_mfe_bars": np.nan,
            "time_to_mae_bars": np.nan,
            "time_from_mfe_to_exit_bars": np.nan,
            "peak_to_exit_return_bps": np.nan,
            "intra_trade_bar_count": np.nan,
            "mfe_giveback_bps": np.nan,
            "positive_mfe_before_loss": False,
            "excursion_class": "unresolved",
            "row_status": "unresolved",
        }

        required_present = all(
            pd.notna(value)
            for value in [signal_index, entry_index, exit_index, signal_time, entry_time, exit_time, entry_price, exit_price]
        )
        if not required_present:
            matched_rows.append(result)
            continue

        try:
            s_idx = int(signal_index)
            e_idx = int(entry_index)
            x_idx = int(exit_index)
        except Exception:
            matched_rows.append(result)
            continue

        if s_idx < 0 or e_idx < 0 or x_idx < 0 or e_idx >= x_idx:
            matched_rows.append(result)
            continue
        if x_idx > len(bars) - 1 or s_idx > len(bars) - 1:
            matched_rows.append(result)
            continue
        if not (
            _within_tolerance(signal_time, close_times[s_idx])
            and _within_tolerance(entry_time, open_times[e_idx])
            and _within_tolerance(exit_time, open_times[x_idx])
        ):
            matched_rows.append(result)
            continue

        if "side" in trades.columns:
            side_value = getattr(row, "side", None)
            if pd.notna(side_value):
                side_text = str(side_value).strip().lower()
                if side_text not in {"long", "buy", "1", "true"}:
                    matched_rows.append(result)
                    continue

        path = bars.iloc[e_idx:x_idx].copy()
        if path.empty or path["high"].isna().all() or path["low"].isna().all():
            matched_rows.append(result)
            continue

        entry_price = float(entry_price)
        exit_price = float(exit_price)
        final_return_bps = float(gross_return_bps) if "gross_return_bps" in trades.columns and pd.notna(gross_return_bps) else float(net_return_bps)

        high_series = pd.to_numeric(path["high"], errors="coerce").dropna()
        low_series = pd.to_numeric(path["low"], errors="coerce").dropna()
        if high_series.empty or low_series.empty:
            matched_rows.append(result)
            continue

        high_values = high_series.to_numpy(dtype=float)
        low_values = low_series.to_numpy(dtype=float)
        mfe_pos = int(np.argmax(high_values))
        mae_pos = int(np.argmin(low_values))
        max_favorable_price = float(high_values[mfe_pos])
        max_adverse_price = float(low_values[mae_pos])
        mfe_bps = (max_favorable_price / entry_price - 1.0) * 10_000.0
        mae_bps = (max_adverse_price / entry_price - 1.0) * 10_000.0
        time_to_mfe_bars = float(mfe_pos)
        time_to_mae_bars = float(mae_pos)
        intra_trade_bar_count = int(len(path))
        time_from_mfe_to_exit_bars = float(max(intra_trade_bar_count - 1 - mfe_pos, 0))
        peak_to_exit_return_bps = (exit_price / max_favorable_price - 1.0) * 10_000.0 if max_favorable_price > 0.0 else np.nan
        mfe_giveback_bps = mfe_bps - final_return_bps
        positive_mfe_before_loss = bool(final_return_bps < 0.0 and mfe_bps > 0.0)

        if final_return_bps < 0.0 and mfe_bps <= 0.0:
            excursion_class = "bad_entry_loss"
        elif final_return_bps < 0.0 and mfe_bps > 0.0:
            excursion_class = "giveback_loss"
        elif final_return_bps > 0.0 and mfe_bps > 0.0 and mfe_giveback_bps >= 0.50 * mfe_bps:
            excursion_class = "weak_positive_exit"
        elif final_return_bps > 0.0:
            excursion_class = "clean_winner"
        else:
            excursion_class = "unresolved"

        result.update(
            {
                "final_return_bps": final_return_bps,
                "max_favorable_price": max_favorable_price,
                "max_adverse_price": max_adverse_price,
                "mfe_bps": mfe_bps,
                "mae_bps": mae_bps,
                "time_to_mfe_bars": time_to_mfe_bars,
                "time_to_mae_bars": time_to_mae_bars,
                "time_from_mfe_to_exit_bars": time_from_mfe_to_exit_bars,
                "peak_to_exit_return_bps": peak_to_exit_return_bps,
                "intra_trade_bar_count": intra_trade_bar_count,
                "mfe_giveback_bps": mfe_giveback_bps,
                "positive_mfe_before_loss": positive_mfe_before_loss,
                "excursion_class": excursion_class,
                "row_status": "matched",
            }
        )
        matched_rows.append(result)

    return pd.DataFrame(matched_rows)


def _summary_by_year(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in sorted(pd.to_numeric(frame["year"], errors="coerce").dropna().astype(int).unique().tolist()):
        group = frame[pd.to_numeric(frame["year"], errors="coerce").astype("Int64") == year].copy()
        rows.append(_summarize_group(group, int(year)))
    return rows


def _summarize_group(group: pd.DataFrame, year: int | None = None) -> dict[str, object]:
    valid = group[group["row_status"] == "matched"].copy()
    losing = valid[valid["final_return_bps"] < 0.0].copy()
    summary = {
        "year": year,
        "count": int(len(group)),
        "matched": int((group["row_status"] == "matched").sum()),
        "unresolved": int((group["row_status"] != "matched").sum()),
        "avg_mfe_bps": float(valid["mfe_bps"].mean()) if len(valid) else None,
        "median_mfe_bps": float(valid["mfe_bps"].median()) if len(valid) else None,
        "avg_mae_bps": float(valid["mae_bps"].mean()) if len(valid) else None,
        "median_mae_bps": float(valid["mae_bps"].median()) if len(valid) else None,
        "avg_mfe_giveback_bps": float(valid["mfe_giveback_bps"].mean()) if len(valid) else None,
        "median_mfe_giveback_bps": float(valid["mfe_giveback_bps"].median()) if len(valid) else None,
        "avg_time_to_mfe_bars": float(valid["time_to_mfe_bars"].mean()) if len(valid) else None,
        "median_time_to_mfe_bars": float(valid["time_to_mfe_bars"].median()) if len(valid) else None,
        "avg_time_to_mae_bars": float(valid["time_to_mae_bars"].mean()) if len(valid) else None,
        "median_time_to_mae_bars": float(valid["time_to_mae_bars"].median()) if len(valid) else None,
        "avg_time_from_mfe_to_exit_bars": float(valid["time_from_mfe_to_exit_bars"].mean()) if len(valid) else None,
        "median_time_from_mfe_to_exit_bars": float(valid["time_from_mfe_to_exit_bars"].median()) if len(valid) else None,
        "bad_entry_loss": int((valid["excursion_class"] == "bad_entry_loss").sum()),
        "giveback_loss": int((valid["excursion_class"] == "giveback_loss").sum()),
        "weak_positive_exit": int((valid["excursion_class"] == "weak_positive_exit").sum()),
        "clean_winner": int((valid["excursion_class"] == "clean_winner").sum()),
        "unresolved_label": int((valid["excursion_class"] == "unresolved").sum()),
        "losing_trade_count": int(len(losing)),
        "losing_trades_with_positive_mfe": int((losing["mfe_bps"] > 0.0).sum()) if len(losing) else 0,
        "losing_trades_without_positive_mfe": int((losing["mfe_bps"] <= 0.0).sum()) if len(losing) else 0,
        "positive_mfe_before_loss_rate": float((losing["mfe_bps"] > 0.0).mean()) if len(losing) else None,
        "giveback_loss_count": int((losing["excursion_class"] == "giveback_loss").sum()) if len(losing) else 0,
        "bad_entry_loss_count": int((losing["excursion_class"] == "bad_entry_loss").sum()) if len(losing) else 0,
    }
    return summary


def construct_diagnostics(trades: pd.DataFrame, bars: pd.DataFrame, bar_files_read: int) -> tuple[pd.DataFrame, dict[str, object]]:
    diagnostics = construct_excursion_table(trades, bars)
    if "year" not in diagnostics.columns or not diagnostics["year"].notna().any():
        diagnostics["year"] = _parse_timestamp_series(diagnostics["signal_time"]).dt.year.astype("Int64")
    else:
        diagnostics["year"] = pd.to_numeric(diagnostics["year"], errors="coerce").astype("Int64")

    total = int(len(diagnostics))
    matched = int((diagnostics["row_status"] == "matched").sum())
    unresolved = int((diagnostics["row_status"] != "matched").sum())
    final_basis = _final_return_basis(trades)
    side_basis = _side_basis(trades)

    overall_summary = _summarize_group(diagnostics, None)
    overall_summary.update(
        {
            "trade_rows_loaded": int(len(trades)),
            "bar_rows_loaded": int(len(bars)),
            "bar_files_read": int(bar_files_read),
            "rows_with_matched_bars": matched,
            "rows_without_matched_bars": total - matched,
            "unresolved_rows": unresolved,
            "year_min": int(pd.to_numeric(diagnostics["year"], errors="coerce").dropna().min()) if diagnostics["year"].notna().any() else None,
            "year_max": int(pd.to_numeric(diagnostics["year"], errors="coerce").dropna().max()) if diagnostics["year"].notna().any() else None,
            "side_basis": side_basis,
            "final_return_basis": final_basis,
            "classification_counts": diagnostics["excursion_class"].value_counts(dropna=False).reindex(CLASS_LABELS, fill_value=0).to_dict(),
            "yearly_rows": _summary_by_year(diagnostics),
            "losing_trade_classification_by_year": [
                {
                    "year": row["year"],
                    "losing_trade_count": row["losing_trade_count"],
                    "losing_trades_with_positive_mfe": row["losing_trades_with_positive_mfe"],
                    "losing_trades_without_positive_mfe": row["losing_trades_without_positive_mfe"],
                    "positive_mfe_before_loss_rate": row["positive_mfe_before_loss_rate"],
                    "giveback_loss_count": row["giveback_loss_count"],
                    "bad_entry_loss_count": row["bad_entry_loss_count"],
                }
                for row in _summary_by_year(diagnostics)
            ],
        }
    )

    recent_2025 = diagnostics[pd.to_numeric(diagnostics["year"], errors="coerce").astype("Int64") == 2025]
    recent_2026 = diagnostics[pd.to_numeric(diagnostics["year"], errors="coerce").astype("Int64") == 2026]
    overall_summary["2025_vs_2026"] = {
        "2025": _summarize_group(recent_2025, 2025),
        "2026": _summarize_group(recent_2026, 2026),
    }

    return diagnostics, overall_summary


def build_report(*, trade_log: Path, bar_dir: Path, output_doc: Path | None = None) -> tuple[str, dict[str, object]]:
    trades = _parse_trade_frame(trade_log)
    bars, bar_files = _load_bars(bar_dir)
    diagnostics, summary = construct_diagnostics(trades, bars, len(bar_files))

    year_rows = summary["yearly_rows"]
    classification_counts = summary["classification_counts"]
    losing_by_year = summary["losing_trade_classification_by_year"]
    y2025 = summary["2025_vs_2026"]["2025"]
    y2026 = summary["2025_vs_2026"]["2026"]

    kept_available = False

    lines: list[str] = []
    lines.append("# V9.2 C_Exhaustion MFE/MAE Source Construction Dry Run")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is a bounded descriptive source-construction dry run only. It computes row-level MFE/MAE and giveback diagnostics in memory from the existing trade log and bounded 750btc bars, and writes only a Markdown summary.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- trade_log path: `{trade_log}`")
    lines.append(f"- bar_dir path: `{bar_dir}`")
    lines.append("- real_trade_log_read: `true`")
    lines.append("- real_bar_data_read: `true`")
    lines.append("- raw_l2_data_read: `false`")
    lines.append("- ofi_artifacts_read: `false`")
    lines.append("- row_level_artifacts_written: `false`")
    lines.append("- feature_table_artifacts_written: `false`")
    lines.append("- model_artifacts_written: `false`")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No model was trained.")
    lines.append("- No model was refit.")
    lines.append("- No scaler was refit.")
    lines.append("- No threshold was tuned.")
    lines.append("- No exit horizon was optimized.")
    lines.append("- No target/stop tuning was performed.")
    lines.append("- No strategy backtest was run.")
    lines.append("- No strategy/replay logic was changed.")
    lines.append("- No raw L2 data was read.")
    lines.append("- No OFI artifacts were read or written.")
    lines.append("- No row-level artifacts were written.")
    lines.append("- No feature-table artifacts were written.")
    lines.append("- No model artifacts were written.")
    lines.append("- No paper/live trading is approved.")
    lines.append("- No production approval is given.")
    lines.append("- Alpha is not approved.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("")
    lines.append("## Pre-Registered Protocol Applied")
    lines.append("")
    lines.append(f"- source preregistration file path: `docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_PREREGISTRATION.md`")
    lines.append("- existing trade intervals only")
    lines.append("- bounded 750btc bars only")
    lines.append(f"- side_basis: `{summary['side_basis']}`")
    lines.append("- no alternative exits searched")
    lines.append("- classification framework: `bad_entry_loss`, `giveback_loss`, `weak_positive_exit`, `clean_winner`, `unresolved`")
    lines.append("- weak_positive_exit threshold fixed at 50% giveback of MFE")
    lines.append("- no threshold tuning")
    lines.append("")
    lines.append("## Source Construction Summary")
    lines.append("")
    lines.append(f"- trade_rows_loaded: `{summary['trade_rows_loaded']}`")
    lines.append(f"- bar_rows_loaded: `{summary['bar_rows_loaded']}`")
    lines.append(f"- bar_files_read: `{summary['bar_files_read']}`")
    lines.append(f"- rows_with_matched_bars: `{summary['rows_with_matched_bars']}`")
    lines.append(f"- rows_without_matched_bars: `{summary['rows_without_matched_bars']}`")
    lines.append(f"- unresolved_rows: `{summary['unresolved_rows']}`")
    lines.append(f"- year_min: `{summary['year_min']}`")
    lines.append(f"- year_max: `{summary['year_max']}`")
    lines.append(f"- side_basis: `{summary['side_basis']}`")
    lines.append(f"- final_return_basis: `{summary['final_return_basis']}`")
    lines.append("")
    lines.append("## Classification Counts")
    lines.append("")
    lines.append(_markdown_table([classification_counts], CLASS_LABELS))
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "year": row["year"],
                "bad_entry_loss": row["bad_entry_loss"],
                "giveback_loss": row["giveback_loss"],
                "weak_positive_exit": row["weak_positive_exit"],
                "clean_winner": row["clean_winner"],
                "unresolved": row["unresolved_label"],
            }
            for row in year_rows
        ],
        ["year", "bad_entry_loss", "giveback_loss", "weak_positive_exit", "clean_winner", "unresolved"],
    ))
    lines.append("")
    lines.append("## Losing Trade Giveback Summary")
    lines.append("")
    overall_losing = diagnostics[diagnostics["final_return_bps"] < 0.0].copy()
    losing_positive_mfe = int((overall_losing["mfe_bps"] > 0.0).sum())
    losing_without_positive_mfe = int((overall_losing["mfe_bps"] <= 0.0).sum())
    positive_rate = float((overall_losing["mfe_bps"] > 0.0).mean()) if len(overall_losing) else None
    lines.append(f"- losing_trade_count: `{int(len(overall_losing))}`")
    lines.append(f"- losing_trades_with_positive_mfe: `{losing_positive_mfe}`")
    lines.append(f"- losing_trades_without_positive_mfe: `{losing_without_positive_mfe}`")
    lines.append(f"- positive_mfe_before_loss_rate: `{_fmt(positive_rate)}`")
    lines.append(f"- giveback_loss_count: `{int((overall_losing['excursion_class'] == 'giveback_loss').sum())}`")
    lines.append(f"- bad_entry_loss_count: `{int((overall_losing['excursion_class'] == 'bad_entry_loss').sum())}`")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "year": row["year"],
                "losing_trade_count": row["losing_trade_count"],
                "losing_trades_with_positive_mfe": row["losing_trades_with_positive_mfe"],
                "losing_trades_without_positive_mfe": row["losing_trades_without_positive_mfe"],
                "positive_mfe_before_loss_rate": row["positive_mfe_before_loss_rate"],
                "giveback_loss_count": row["giveback_loss_count"],
                "bad_entry_loss_count": row["bad_entry_loss_count"],
            }
            for row in year_rows
        ],
        [
            "year",
            "losing_trade_count",
            "losing_trades_with_positive_mfe",
            "losing_trades_without_positive_mfe",
            "positive_mfe_before_loss_rate",
            "giveback_loss_count",
            "bad_entry_loss_count",
        ],
    ))
    lines.append("")
    lines.append("## Excursion Summary By Year")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "year": row["year"],
                "count": row["count"],
                "avg_mfe_bps": row["avg_mfe_bps"],
                "median_mfe_bps": row["median_mfe_bps"],
                "avg_mae_bps": row["avg_mae_bps"],
                "median_mae_bps": row["median_mae_bps"],
                "avg_mfe_giveback_bps": row["avg_mfe_giveback_bps"],
                "median_mfe_giveback_bps": row["median_mfe_giveback_bps"],
                "avg_time_to_mfe_bars": row["avg_time_to_mfe_bars"],
                "median_time_to_mfe_bars": row["median_time_to_mfe_bars"],
                "avg_time_to_mae_bars": row["avg_time_to_mae_bars"],
                "median_time_to_mae_bars": row["median_time_to_mae_bars"],
                "avg_time_from_mfe_to_exit_bars": row["avg_time_from_mfe_to_exit_bars"],
                "median_time_from_mfe_to_exit_bars": row["median_time_from_mfe_to_exit_bars"],
            }
            for row in year_rows
        ],
        [
            "year",
            "count",
            "avg_mfe_bps",
            "median_mfe_bps",
            "avg_mae_bps",
            "median_mae_bps",
            "avg_mfe_giveback_bps",
            "median_mfe_giveback_bps",
            "avg_time_to_mfe_bars",
            "median_time_to_mfe_bars",
            "avg_time_to_mae_bars",
            "median_time_to_mae_bars",
            "avg_time_from_mfe_to_exit_bars",
            "median_time_from_mfe_to_exit_bars",
        ],
    ))
    lines.append("")
    lines.append("## 2025 vs 2026 Holdout Comparison")
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "year": 2025,
                "total trades": y2025["count"],
                "losing trades": y2025["losing_trade_count"],
                "positive-MFE-before-loss count": y2025["losing_trades_with_positive_mfe"],
                "giveback_loss count": y2025["giveback_loss_count"],
                "bad_entry_loss count": y2025["bad_entry_loss_count"],
                "weak_positive_exit count": y2025["weak_positive_exit"],
                "clean_winner count": y2025["clean_winner"],
                "unresolved count": y2025["unresolved_label"],
            },
            {
                "year": 2026,
                "total trades": y2026["count"],
                "losing trades": y2026["losing_trade_count"],
                "positive-MFE-before-loss count": y2026["losing_trades_with_positive_mfe"],
                "giveback_loss count": y2026["giveback_loss_count"],
                "bad_entry_loss count": y2026["bad_entry_loss_count"],
                "weak_positive_exit count": y2026["weak_positive_exit"],
                "clean_winner count": y2026["clean_winner"],
                "unresolved count": y2026["unresolved_label"],
            },
        ],
        [
            "year",
            "total trades",
            "losing trades",
            "positive-MFE-before-loss count",
            "giveback_loss count",
            "bad_entry_loss count",
            "weak_positive_exit count",
            "clean_winner count",
            "unresolved count",
        ],
    ))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- 2025 improved versus keep-all in the earlier diagnostics but remained negative.")
    lines.append("- 2026 worsened versus keep-all in the earlier diagnostics.")
    lines.append("- This source-construction dry run is intended to determine whether those losses are more consistent with bad entries or giveback failures.")
    lines.append("")
    lines.append("## Kept vs Skipped Comparison")
    lines.append("")
    lines.append("Row-level logistic kept/skipped decisions were not available as an approved row-level source.")
    lines.append("The dry run did not retrain or rerun the logistic model to reconstruct predictions.")
    lines.append("Kept/skipped giveback comparison is deferred until row-level predictions are separately available or pre-registered.")
    lines.append("")
    lines.append("## What This Proves")
    lines.append("")
    lines.append("- Row-level MFE/MAE source construction can be performed safely from existing trade intervals and bounded bars.")
    lines.append("- Descriptive giveback labels can be assigned without changing strategy logic.")
    lines.append("- The output can distinguish bad entries from giveback failures.")
    lines.append("- The resulting diagnostics can show whether 2026 requires further investigation.")
    lines.append("")
    lines.append("## What This Does Not Prove")
    lines.append("")
    lines.append("- no alpha approval")
    lines.append("- no strategy improvement")
    lines.append("- no exit optimization")
    lines.append("- no target/stop approval")
    lines.append("- no paper/live readiness")
    lines.append("- no production readiness")
    lines.append("- no OFI/L2 approval")
    lines.append("")
    lines.append("## Stop / Go Assessment")
    lines.append("")
    lines.append("- stop/pause modeling if most 2025/2026 losses are giveback_loss")
    lines.append("- stop/pause modeling if logistic-kept 2026 losers are mostly giveback_loss, if known")
    lines.append("- stop/pause if reconstruction is unsafe or incomplete")
    lines.append("- continue only if the next hypothesis is non-leaky and separately pre-registered")
    lines.append("")
    lines.append("## Recommended Next Step")
    lines.append("")
    if int((overall_losing["excursion_class"] == "giveback_loss").sum()) >= int((overall_losing["excursion_class"] == "bad_entry_loss").sum()):
        lines.append("Recommend an exit-management diagnostic review document, not an optimization run.")
    else:
        lines.append("Recommend a conservative entry-filter diagnostic preregistration, not model-class expansion.")
    lines.append("")
    lines.append("## Explicitly Not Approved")
    lines.append("")
    lines.append("- No paper trading.")
    lines.append("- No live trading.")
    lines.append("- No production deployment.")
    lines.append("- No additional model classes.")
    lines.append("- No threshold tuning.")
    lines.append("- No feature fishing.")
    lines.append("- No OFI/L2 integration.")
    lines.append("- No full reconstruction.")
    lines.append("- No claims of alpha.")
    lines.append("- No strategy/replay changes.")
    lines.append("- No exit-horizon optimization.")
    lines.append("- No target/stop tuning.")
    lines.append("- No backtest reruns.")
    lines.append("- No row-level artifact persistence.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    total_trades = int(summary["trade_rows_loaded"])
    matched_rows = int(summary["rows_with_matched_bars"])
    unresolved_rows = int(summary["unresolved_rows"])
    if unresolved_rows == 0 and matched_rows == total_trades:
        decision = "bounded_mfe_mae_source_construction_pass"
    elif matched_rows > 0:
        decision = "bounded_mfe_mae_source_construction_partial"
    else:
        decision = "bounded_mfe_mae_source_construction_blocked"
    lines.append(f"Decision: `{decision}`")
    lines.append("")
    lines.append("## Decision Labels")
    lines.append("")
    labels = [
        "c_exhaustion_mfe_mae_source_construction_dry_run_created",
        "bounded_descriptive_only",
        "real_trade_log_read",
        "real_bounded_bar_data_read",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_row_level_artifacts_written",
        "no_feature_table_artifacts_written",
        "no_model_artifacts_written",
        "no_strategy_backtest_run",
        "no_strategy_replay_changes",
        "no_exit_optimization",
        "no_target_stop_tuning",
        "no_threshold_tuning",
        "no_new_model_trained",
        "full_reconstruction_not_approved",
        "alpha_not_approved",
        "paper_live_blocked",
        "production_not_approved",
        decision,
    ]
    for label in labels:
        lines.append(f"- `{label}`")

    report = "\n".join(lines) + "\n"
    if output_doc is not None:
        output_doc.parent.mkdir(parents=True, exist_ok=True)
        output_doc.write_text(report, encoding="utf-8")
    return report, {
        **summary,
        "decision": decision,
        "kept_skipped_available": kept_available,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _summary = build_report(trade_log=args.trade_log, bar_dir=args.bar_dir, output_doc=args.output_doc)
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
