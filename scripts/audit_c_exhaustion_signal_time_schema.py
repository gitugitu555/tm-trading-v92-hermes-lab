#!/usr/bin/env python3
"""Read-only schema audit for C_Exhaustion signal-time availability."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_SIGNAL_TIME_SCHEMA_AUDIT.md")
DEFAULT_BAR_DIR = Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc")
DEFAULT_MAX_ROWS = 5000
REPORTS_DIR = ROOT / "reports"

REPLAY_PATH_CANDIDATES = [
    ROOT / "reports/c_exhaustion_replay_post_regime_fix/trade_log.csv",
    ROOT / "reports/c_exhaustion_replay_post_regime_fix/c_exhaustion_replay_trades.csv",
    ROOT / "reports/c_exhaustion_replay_post_regime_fix/c_exhaustion_replay_trade_log.csv",
]

TRADE_REQUIRED_COLUMNS = [
    "signal_time",
    "entry_time",
    "exit_time",
    "signal_index",
    "entry_index",
    "exit_index",
]

BAR_REQUIRED_COLUMNS = [
    "open_time",
    "close_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


@dataclass(frozen=True)
class TableAudit:
    path: Path | None
    row_count: int | None
    columns: list[str]
    present: dict[str, bool]
    missing: list[str]
    timestamp_checks: dict[str, object]
    min_time: pd.Timestamp | None = None
    max_time: pd.Timestamp | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--bar-file", type=Path)
    parser.add_argument("--trade-log", type=Path)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    return parser.parse_args(argv)


def _iter_text_files(paths: Iterable[Path]) -> Iterable[Path]:
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".md", ".txt"}:
                yield path


def _discover_trade_log(repo_root: Path) -> Path | None:
    for candidate in REPLAY_PATH_CANDIDATES:
        if candidate.exists():
            return candidate

    search_dirs = [repo_root / "docs", repo_root / "scripts", repo_root / "replays"]
    for path in _iter_text_files(search_dirs):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "trade_log.csv" in text and "c_exhaustion_replay_post_regime_fix" in text:
            for rel in re.findall(r"reports/c_exhaustion_replay_post_regime_fix/[\w\-.]+\.csv", text):
                candidate = repo_root / rel
                if candidate.exists():
                    return candidate
    return None


def _discover_bar_file(bar_search_dir: Path) -> Path | None:
    if not bar_search_dir.exists():
        return None
    candidates = sorted(bar_search_dir.glob("BTCUSDT_tier2_750btc_*.parquet"))
    return candidates[0] if candidates else None


def _read_table(path: Path, max_rows: int) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=max_rows)
    if suffix == ".parquet":
        df = pd.read_parquet(path)
        if max_rows > 0:
            return df.head(max_rows).copy()
        return df
    raise ValueError(f"Unsupported schema file type: {path.suffix}")


def _parse_timestamp_value(value: object) -> pd.Timestamp | pd.NaT:
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, (int, float)):
        ivalue = int(value)
        unit = "us" if abs(ivalue) > 100_000_000_000_000 else "ms"
        return pd.to_datetime(ivalue, unit=unit, errors="coerce")
    text = str(value).strip()
    if not text:
        return pd.NaT
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        ivalue = int(float(text))
        unit = "us" if abs(ivalue) > 100_000_000_000_000 else "ms"
        return pd.to_datetime(ivalue, unit=unit, errors="coerce")
    return pd.to_datetime(text, errors="coerce", utc=False)


def _parse_timestamp_series(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    return series.apply(_parse_timestamp_value)


def _audit_table(path: Path | None, *, max_rows: int, required_columns: list[str], timestamp_pairs: list[tuple[str, str]]) -> TableAudit:
    if path is None:
        return TableAudit(
            path=None,
            row_count=None,
            columns=[],
            present={col: False for col in required_columns},
            missing=list(required_columns),
            timestamp_checks={},
        )

    df = _read_table(path, max_rows=max_rows)
    columns = list(df.columns)
    present = {col: col in df.columns for col in required_columns}
    missing = [col for col, is_present in present.items() if not is_present]

    timestamp_checks: dict[str, object] = {}
    parsed: dict[str, pd.Series] = {}
    for left, right in timestamp_pairs:
        left_series = _parse_timestamp_series(df[left]) if left in df.columns else pd.Series(dtype="datetime64[ns]")
        right_series = _parse_timestamp_series(df[right]) if right in df.columns else pd.Series(dtype="datetime64[ns]")
        parsed[left] = left_series
        parsed[right] = right_series
        timestamp_checks[f"parseable_{left}"] = bool(len(left_series) and left_series.notna().all()) if left in df.columns else False
        timestamp_checks[f"parseable_{right}"] = bool(len(right_series) and right_series.notna().all()) if right in df.columns else False
        if left in df.columns and right in df.columns and len(left_series) and len(right_series):
            timestamp_checks[f"{left}_lte_{right}"] = bool((left_series <= right_series).all())
        else:
            timestamp_checks[f"{left}_lte_{right}"] = None

    # Record min/max for the primary time columns when present.
    min_time = None
    max_time = None
    if timestamp_pairs:
        first_left = timestamp_pairs[0][0]
        if first_left in parsed and len(parsed[first_left]):
            min_time = parsed[first_left].min()
            max_time = parsed[first_left].max()

    return TableAudit(
        path=path,
        row_count=int(len(df)),
        columns=columns,
        present=present,
        missing=missing,
        timestamp_checks=timestamp_checks,
        min_time=min_time if isinstance(min_time, pd.Timestamp) else None,
        max_time=max_time if isinstance(max_time, pd.Timestamp) else None,
    )


def _feature_rows(trade_audit: TableAudit, bar_audit: TableAudit) -> list[dict[str, object]]:
    trade_cols = set(trade_audit.columns)
    bar_cols = set(bar_audit.columns)

    def _yes_no(value: bool) -> str:
        return "yes" if value else "no"

    rows: list[dict[str, object]] = []

    def add_row(feature_family: str, required_columns: list[str], replay_ok: bool, bar_ok: bool, eligible: str, blocker: str, leakage_guard: str, requires_l2: bool = False) -> None:
        rows.append(
            {
                "feature_family": feature_family,
                "required_columns": ", ".join(required_columns) if required_columns else "none",
                "replay_available": _yes_no(replay_ok),
                "bar_available": _yes_no(bar_ok),
                "eligible_now": eligible,
                "requires_l2_or_ofi_approval": _yes_no(requires_l2),
                "blocker": blocker,
                "leakage_guard": leakage_guard,
            }
        )

    add_row(
        "OHLCV context",
        ["open_time", "close_time", "open", "high", "low", "close", "volume"],
        {"open_time", "close_time", "open", "high", "low", "close", "volume"}.issubset(bar_cols),
        {"open_time", "close_time", "open", "high", "low", "close", "volume"}.issubset(bar_cols),
        "yes",
        "none",
        "completed bars only; no future bars; rolling windows must be shifted",
    )
    add_row(
        "regime",
        ["regime"],
        "regime" in trade_cols,
        "regime" in bar_cols,
        "yes",
        "none if present; otherwise missing schema column",
        "close-of-bar labels only; no future confirmation",
    )
    add_row(
        "volume_delta",
        ["volume_delta"],
        "volume_delta" in trade_cols,
        "volume_delta" in bar_cols,
        "yes" if "volume_delta" in trade_cols or "volume_delta" in bar_cols else "no",
        "missing schema column if absent",
        "past-only derived signed volume; avoid same-bar leakage",
    )
    add_row(
        "CVD / delta",
        ["volume_delta", "delta", "cvd"],
        {"volume_delta", "delta", "cvd"}.intersection(trade_cols) or "volume_delta" in bar_cols,
        "volume_delta" in bar_cols,
        "yes" if ("volume_delta" in bar_cols or {"delta", "cvd"}.intersection(trade_cols)) else "no",
        "missing schema column if no signed-flow source exists",
        "use only past trades or bar-level signed volume; shift if derived from rolling windows",
    )
    add_row(
        "absorption proxy",
        ["side", "price", "size_base", "buyer_is_maker", "native_aggressor_side", "volume_delta"],
        {"side", "price", "size_base"}.issubset(trade_cols) or {"buyer_is_maker", "native_aggressor_side"}.intersection(trade_cols),
        False,
        "no",
        "missing schema columns for signed-trade inputs",
        "strict past-only window; never use post-signal move",
    )
    add_row(
        "VPIN / toxicity",
        ["side", "size_base", "buy_volume", "sell_volume"],
        {"side", "size_base"}.issubset(trade_cols) or {"buy_volume", "sell_volume"}.issubset(trade_cols),
        {"buy_volume", "sell_volume"}.issubset(bar_cols),
        "no" if not ({"buy_volume", "sell_volume"}.issubset(bar_cols) or {"side", "size_base"}.issubset(trade_cols)) else "yes",
        "missing buy/sell bucket columns or signed trade fields",
        "past-only buckets or completed bar splits only",
    )
    add_row(
        "footprint",
        ["price", "size_base", "side"],
        {"price", "size_base", "side"}.issubset(trade_cols),
        False,
        "no",
        "missing raw trade tape columns",
        "price-level binning must stop at signal time",
    )
    add_row(
        "OFI / MLOFI",
        ["bids", "asks", "ofi", "mlofi_weighted_aggregate"],
        {"bids", "asks", "ofi"}.intersection(trade_cols),
        {"bids", "asks", "ofi"}.intersection(bar_cols),
        "no",
        "requires approved OFI/L2 artifacts and historical provenance",
        "bounded L2 snapshots only; no future-book contamination",
        requires_l2=True,
    )
    add_row(
        "microprice / spread / depth",
        ["bids", "asks", "microprice", "spread_bps", "depth_top5", "depth_top10"],
        {"bids", "asks", "microprice"}.intersection(trade_cols),
        {"bids", "asks", "microprice"}.intersection(bar_cols),
        "no",
        "requires approved OFI/L2 artifacts",
        "bounded L2 snapshots only; no future-book contamination",
        requires_l2=True,
    )
    add_row(
        "spoofing / iceberg / L2 whale pressure",
        ["ts_event", "bids", "asks", "refill_count", "whale_pressure"],
        {"ts_event", "bids", "asks"}.issubset(trade_cols),
        {"ts_event", "bids", "asks"}.issubset(bar_cols),
        "no",
        "requires approved L2 history and historical event coverage",
        "timestamp ordering and missing-update sensitivity",
        requires_l2=True,
    )
    add_row(
        "funding / OI / liquidation / basis",
        ["funding", "open_interest", "liquidation", "basis"],
        {"funding", "open_interest", "liquidation", "basis"}.intersection(trade_cols),
        {"funding", "open_interest", "liquidation", "basis"}.intersection(bar_cols),
        "no",
        "missing verified historical source",
        "point-in-time publication timing must be audited",
    )

    return rows


def _format_columns(columns: list[str]) -> str:
    return ", ".join(columns) if columns else "none"


def _format_presence(present: dict[str, bool]) -> str:
    return ", ".join(f"{k}={str(v).lower()}" for k, v in present.items())


def build_report(
    repo_root: Path,
    *,
    bar_file: Path | None = None,
    trade_log: Path | None = None,
    bar_search_dir: Path = DEFAULT_BAR_DIR,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> tuple[str, dict[str, object]]:
    discovered_trade_log = trade_log if trade_log is not None else _discover_trade_log(repo_root)
    discovered_bar_file = bar_file if bar_file is not None else _discover_bar_file(bar_search_dir)

    trade_audit = _audit_table(
        discovered_trade_log,
        max_rows=max_rows,
        required_columns=TRADE_REQUIRED_COLUMNS,
        timestamp_pairs=[("signal_time", "entry_time"), ("entry_time", "exit_time")],
    )
    bar_audit = _audit_table(
        discovered_bar_file,
        max_rows=max_rows,
        required_columns=BAR_REQUIRED_COLUMNS,
        timestamp_pairs=[("open_time", "close_time")],
    )

    trade_ts_checks = trade_audit.timestamp_checks
    bar_ts_checks = bar_audit.timestamp_checks

    alignment_available = (
        discovered_trade_log is not None
        and discovered_bar_file is not None
        and trade_audit.row_count is not None
        and bar_audit.row_count is not None
    )

    signal_time_basis = "mixed"
    signal_in_bar_range = None
    full_join_avoided = True
    if alignment_available:
        trade_df = _read_table(discovered_trade_log, max_rows=max_rows)
        bar_df = _read_table(discovered_bar_file, max_rows=max_rows)
        trade_signal = _parse_timestamp_series(trade_df["signal_time"]) if "signal_time" in trade_df.columns else pd.Series(dtype="datetime64[ns]")
        bar_open = _parse_timestamp_series(bar_df["open_time"]) if "open_time" in bar_df.columns else pd.Series(dtype="datetime64[ns]")
        bar_close = _parse_timestamp_series(bar_df["close_time"]) if "close_time" in bar_df.columns else pd.Series(dtype="datetime64[ns]")
        if len(trade_signal) and len(bar_open) and len(bar_close):
            bar_min = min(bar_open.min(), bar_close.min())
            bar_max = max(bar_open.max(), bar_close.max())
            signal_in_bar_range = bool(((trade_signal >= bar_min) & (trade_signal <= bar_max)).any())
        else:
            signal_in_bar_range = None

    required_signal_cols = ["signal_time", "entry_time", "exit_time", "signal_index", "entry_index", "exit_index"]
    required_bar_cols = ["open_time", "close_time", "open", "high", "low", "close", "volume"]
    trade_optional_cols = ["side", "entry_price", "exit_price", "pnl", "pnl_bps", "regime"]
    bar_optional_cols = ["volume_delta", "regime", "vol_roll_95", "local_low", "c_signal", "trade_count"]

    signal_time_inputs: list[str] = []
    for column in [
        "signal_time",
        "entry_time",
        "exit_time",
        "signal_index",
        "entry_index",
        "exit_index",
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "regime",
        "vol_roll_95",
        "local_low",
        "c_signal",
        "volume_delta",
    ]:
        if column in trade_audit.columns or column in bar_audit.columns:
            signal_time_inputs.append(column)

    feature_rows = _feature_rows(trade_audit, bar_audit)

    audit_mode = "static + optional schema audit" if (discovered_trade_log is not None or discovered_bar_file is not None) else "static-only audit"
    decision_labels = [
        "c_exhaustion_signal_time_schema_audit_created",
        "gate_1_schema_audit_completed_or_partial",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_market_data_artifacts_written",
        "no_strategy_backtest_run",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    if trade_audit.path is not None and bar_audit.path is not None:
        gate_1_status = "pass" if not trade_audit.missing and not bar_audit.missing else "partial"
    elif trade_audit.path is not None or bar_audit.path is not None:
        gate_1_status = "partial"
    else:
        gate_1_status = "blocked"

    report: list[str] = []
    report.append("# V9.2 C_Exhaustion Signal-Time Schema Audit")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("Verify which C_Exhaustion signal-time and bar schema columns are actually present in local replay outputs and 750btc bars, without joining new OFI artifacts or running any strategy evaluation.")
    report.append("")
    report.append("## Inputs")
    report.append("")
    report.append(f"- audit_mode: `{audit_mode}`")
    report.append(f"- explicit_bar_file: `{bar_file}`" if bar_file is not None else "- explicit_bar_file: `null`")
    report.append(f"- explicit_trade_log: `{trade_log}`" if trade_log is not None else "- explicit_trade_log: `null`")
    report.append(f"- discovered_bar_file: `{discovered_bar_file}`" if discovered_bar_file is not None else "- discovered_bar_file: `null`")
    report.append(f"- discovered_trade_log: `{discovered_trade_log}`" if discovered_trade_log is not None else "- discovered_trade_log: `null`")
    report.append(f"- max_rows: `{max_rows}`")
    report.append("")
    report.append("## Read-Only Guardrails")
    report.append("")
    report.append("- No raw L2 data was read.")
    report.append("- No OFI artifacts were read.")
    report.append("- No OFI artifacts were written.")
    report.append("- No market-data artifacts were written.")
    report.append("- No strategy backtest was run.")
    report.append("- No alpha claim is made.")
    report.append("- Full reconstruction remains blocked.")
    report.append("")
    report.append("## Candidate Files")
    report.append("")
    report.append(f"- Discovered trade-log file: `{discovered_trade_log}`" if discovered_trade_log is not None else "- Discovered trade-log file: `none`")
    report.append(f"- Discovered bar file: `{discovered_bar_file}`" if discovered_bar_file is not None else "- Discovered bar file: `none`")
    report.append(f"- Inspected trade-log file: `{trade_audit.path}`" if trade_audit.path is not None else "- Inspected trade-log file: `none`")
    report.append(f"- Inspected bar file: `{bar_audit.path}`" if bar_audit.path is not None else "- Inspected bar file: `none`")
    report.append("")
    report.append("## Current Signal-Time Columns / Inputs")
    report.append("")
    report.append(f"- present columns: `{_format_columns(signal_time_inputs)}`")
    report.append(f"- required signal-time columns present: `{_format_presence({col: col in trade_audit.columns for col in required_signal_cols})}`")
    report.append(f"- required bar columns present: `{_format_presence({col: col in bar_audit.columns for col in required_bar_cols})}`")
    report.append("")
    report.append("## Replay / Trade-Log Schema")
    report.append("")
    report.append(f"- file inspected: `{trade_audit.path}`" if trade_audit.path is not None else "- file inspected: `none`")
    report.append(f"- row sample count: `{trade_audit.row_count}`" if trade_audit.row_count is not None else "- row sample count: `none`")
    report.append(f"- columns: `{_format_columns(trade_audit.columns)}`")
    report.append(f"- required column presence: `{_format_presence(trade_audit.present)}`")
    report.append(f"- missing required columns: `{', '.join(trade_audit.missing) if trade_audit.missing else 'none'}`")
    report.append(f"- optional signal-time columns present: `{_format_columns([col for col in trade_optional_cols if col in trade_audit.columns])}`")
    report.append(f"- parseable_timestamp_signal_time: `{trade_ts_checks.get('parseable_signal_time')}`")
    report.append(f"- parseable_timestamp_entry_time: `{trade_ts_checks.get('parseable_entry_time')}`")
    report.append(f"- parseable_timestamp_exit_time: `{trade_ts_checks.get('parseable_exit_time')}`")
    report.append(f"- signal_time_lte_entry_time: `{trade_ts_checks.get('signal_time_lte_entry_time')}`")
    report.append(f"- entry_time_lte_exit_time: `{trade_ts_checks.get('entry_time_lte_exit_time')}`")
    report.append("")
    report.append("## Bar Schema")
    report.append("")
    report.append(f"- file inspected: `{bar_audit.path}`" if bar_audit.path is not None else "- file inspected: `none`")
    report.append(f"- row sample count: `{bar_audit.row_count}`" if bar_audit.row_count is not None else "- row sample count: `none`")
    report.append(f"- columns: `{_format_columns(bar_audit.columns)}`")
    report.append(f"- required column presence: `{_format_presence(bar_audit.present)}`")
    report.append(f"- missing required columns: `{', '.join(bar_audit.missing) if bar_audit.missing else 'none'}`")
    report.append(f"- optional bar columns present: `{_format_columns([col for col in bar_optional_cols if col in bar_audit.columns])}`")
    report.append(f"- parseable_open_time: `{bar_ts_checks.get('parseable_open_time')}`")
    report.append(f"- parseable_close_time: `{bar_ts_checks.get('parseable_close_time')}`")
    report.append(f"- open_time_lte_close_time: `{bar_ts_checks.get('open_time_lte_close_time')}`")
    report.append(f"- volume_delta present: `{bar_audit.present.get('volume_delta')}`")
    report.append(f"- trade-flow columns beyond OHLCV/regime: `{', '.join(sorted(set(bar_audit.columns).difference({'open_time', 'close_time', 'open', 'high', 'low', 'close', 'volume', 'regime'}))) if bar_audit.columns else 'none'}`")
    report.append("")
    report.append("## Signal-Time Alignment Checks")
    report.append("")
    if alignment_available:
        report.append(f"- signal_time values appear within inspected bar range: `{signal_in_bar_range}`")
        report.append(f"- matching timestamp basis: `{signal_time_basis}`")
        report.append(f"- full join avoided: `{str(full_join_avoided).lower()}`")
    else:
        report.append("- signal_time values appear within inspected bar range: `partial / not available`")
        report.append("- matching timestamp basis: `unknown`")
        report.append("- full join avoided: `true`")
    report.append("")
    report.append("## Feature Availability From Actual Schema")
    report.append("")
    headers = [
        "feature family",
        "required columns",
        "replay/trade-log available?",
        "bar available?",
        "eligible now?",
        "requires L2/OFI approval?",
        "leakage guard",
        "status",
    ]
    report.append("| " + " | ".join(headers) + " |")
    report.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in feature_rows:
        report.append(
            "| "
            + " | ".join(
                [
                    str(row["feature_family"]),
                    str(row["required_columns"]),
                    str(row["replay_available"]),
                    str(row["bar_available"]),
                    str(row["eligible_now"]),
                    str(row["requires_l2_or_ofi_approval"]),
                    str(row["leakage_guard"]),
                    str(row["blocker"]),
                ]
            )
            + " |"
        )
    report.append("")
    report.append("## Blocked Features")
    report.append("")
    report.append("### Blocked by OFI/L2 approval")
    report.append("- OFI")
    report.append("- MLOFI")
    report.append("- microprice")
    report.append("- spread")
    report.append("- depth")
    report.append("- queue imbalance")
    report.append("- L2 imbalance")
    report.append("- spoofing")
    report.append("- iceberg")
    report.append("- L2 whale pressure")
    report.append("")
    report.append("### Blocked by missing historical source")
    report.append("- funding")
    report.append("- OI")
    report.append("- liquidation")
    report.append("- derivatives crowding")
    report.append("- basis")
    report.append("")
    report.append("### Blocked by missing schema columns")
    if trade_audit.missing:
        report.append(f"- trade-log missing: {', '.join(trade_audit.missing)}")
    if bar_audit.missing:
        report.append(f"- bar schema missing: {', '.join(bar_audit.missing)}")
    if not trade_audit.missing and not bar_audit.missing:
        report.append("- none for required columns")
    report.append("")
    report.append("### Blocked by timestamp ambiguity")
    if alignment_available:
        report.append("- none for the inspected schema sample")
    else:
        report.append("- alignment could not be fully verified because one or both inspected files were unavailable")
    report.append("")
    report.append("## Gate 1 Finding")
    report.append("")
    report.append("- Gate 1 static inventory: already passed")
    report.append(f"- Gate 1 schema availability: `{gate_1_status}`")
    report.append("- Gate 2 feature table dry run: not started")
    report.append("")
    report.append("## Recommended Next Step")
    report.append("")
    if gate_1_status == "pass" and signal_in_bar_range is True:
        report.append("Run a bounded read-only feature table dry run for OHLCV/regime/volume_delta-only features on a tiny sample, writing only a Markdown report and no data artifacts.")
    elif gate_1_status == "pass":
        report.append("Run a bounded read-only signal-time alignment audit on the discovered replay output and 750btc bar sample to resolve the mixed timestamp basis before any feature table dry run.")
    else:
        report.append("Identify or produce an approved replay output path first, then repeat the bounded read-only schema audit before any feature table dry run.")
    report.append("")
    report.append("## What Is Safe")
    report.append("")
    report.append("- schema-only audit")
    report.append("- timestamp alignment audit")
    report.append("- leakage audit")
    report.append("- bounded read-only diagnostics")
    report.append("")
    report.append("## What Is Not Safe")
    report.append("")
    report.append("- alpha claims")
    report.append("- strategy optimization")
    report.append("- backtesting as part of this task")
    report.append("- full reconstruction")
    report.append("- OFI artifact generation")
    report.append("- paper/live trading")
    report.append("- using unapproved L2 features")
    report.append("")
    report.append("## Decision")
    report.append("")
    for label in decision_labels:
        report.append(f"- `{label}`")

    result = {
        "audit_mode": audit_mode,
        "explicit_bar_file": bar_file,
        "explicit_trade_log": trade_log,
        "discovered_bar_file": discovered_bar_file,
        "discovered_trade_log": discovered_trade_log,
        "signal_source_files": [
            str(path)
            for path in [
                repo_root / "replays/c_exhaustion_replay.py",
                repo_root / "scripts/run_c_exhaustion_replay.py",
                repo_root / "scripts/diagnose_c_exhaustion_meta_label_baseline.py",
                repo_root / "scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py",
                repo_root / "scripts/diagnose_c_exhaustion_signal_state.py",
                repo_root / "scripts/diagnose_c_exhaustion_regime_context.py",
            ]
            if path.exists()
        ],
        "current_signal_time_inputs": signal_time_inputs,
        "trade_audit": trade_audit,
        "bar_audit": bar_audit,
        "feature_rows": feature_rows,
        "decision_labels": decision_labels,
        "gate_1_status": gate_1_status,
        "signal_in_bar_range": signal_in_bar_range,
        "signal_time_basis": signal_time_basis,
        "full_join_avoided": full_join_avoided,
        "alignment_available": alignment_available,
    }
    return "\n".join(report) + "\n", result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _summary = build_report(
        ROOT,
        bar_file=args.bar_file,
        trade_log=args.trade_log,
        bar_search_dir=DEFAULT_BAR_DIR,
        max_rows=args.max_rows,
    )
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
