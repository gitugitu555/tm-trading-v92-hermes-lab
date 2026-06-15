#!/usr/bin/env python3
"""Read-only inventory audit for historical L2 / OFI source data."""

from __future__ import annotations

import argparse
import io
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pyarrow.parquet as pq
import zstandard as zstd

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_SOURCE_INVENTORY_AUDIT.md")
IGNORED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "reports", "tmp_diagnostics"}
SEARCH_SUFFIXES = {".parquet", ".zst", ".zip", ".gz", ".csv", ".json", ".jsonl", ".md", ".txt", ".toml", ".yaml", ".yml", ".checksum"}
PRODUCTION_APPROVAL_STATEMENT = "This audit does not approve OFI for production, paper trading, live trading, or alpha use."


TERM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("orderbook", re.compile(r"orderbook", re.IGNORECASE)),
    ("depthUpdate", re.compile(r"depthupdate", re.IGNORECASE)),
    ("bookTicker", re.compile(r"bookticker", re.IGNORECASE)),
    ("snapshot", re.compile(r"snapshot", re.IGNORECASE)),
    ("diff", re.compile(r"diff", re.IGNORECASE)),
    ("tbt", re.compile(r"(^|[^a-z0-9])tbt([^a-z0-9]|$)", re.IGNORECASE)),
    ("full_depth", re.compile(r"full[_-]?depth", re.IGNORECASE)),
    ("mbo", re.compile(r"(^|[^a-z0-9])mbo([^a-z0-9]|$)", re.IGNORECASE)),
    ("mbp", re.compile(r"(^|[^a-z0-9])mbp([^a-z0-9]|$)", re.IGNORECASE)),
    ("aggTrades", re.compile(r"aggtrades", re.IGNORECASE)),
    ("trades", re.compile(r"(^|[^a-z0-9])trades([^a-z0-9]|$)", re.IGNORECASE)),
    ("ofi", re.compile(r"(^|[^a-z0-9])ofi([^a-z0-9]|$)", re.IGNORECASE)),
    ("OFI", re.compile(r"(^|[^a-z0-9])OFI([^a-z0-9]|$)")),
    ("ohlcv", re.compile(r"ohlcv|kline|candles?|bars?", re.IGNORECASE)),
    ("manifest", re.compile(r"(checksum|manifest|readme|license|notes?)", re.IGNORECASE)),
]


@dataclass(frozen=True)
class RootStatus:
    path: str
    exists: bool
    candidate_count: int
    note: str


@dataclass(frozen=True)
class CandidateRecord:
    path: str
    file_size_bytes: int
    extension: str
    mtime_utc: str
    name_match_terms: str
    parent_dir: str
    symbol_guess: str
    venue_guess: str
    data_type_guess: str
    time_coverage_guess: str
    schema_hint: str
    usable_for_ofi_reconstruction_guess: str
    risk: str
    required_action: str
    readiness: str
    source_family: str


@dataclass(frozen=True)
class AuditResult:
    root_status: list[RootStatus]
    candidates: list[CandidateRecord]
    data_policy_helper_ok: bool
    data_policy_helper_note: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-roots", nargs="+", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _match_terms(path: Path) -> list[str]:
    text = str(path)
    terms = [label for label, pattern in TERM_PATTERNS if pattern.search(text)]
    return terms


def _guess_symbol(path: Path) -> str:
    m = re.search(r"(BTCUSDT|BTC-USDT|BTCUSD|ETHUSDT|ETHUSD|SOLUSDT|BNBUSDT|XRPUSDT)", str(path), re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return "UNKNOWN"


def _guess_venue(path: Path) -> str:
    lower = str(path).lower()
    if "binance_futures" in lower or "futures" in lower:
        return "binance_futures"
    if "binance/spot" in lower or "/spot/" in lower:
        return "binance_spot"
    if "binance" in lower:
        return "binance"
    if "okx" in lower:
        return "okx"
    if "bybit" in lower:
        return "bybit"
    return "unknown"


def _guess_time_coverage(path: Path) -> str:
    text = str(path)
    date_matches = re.findall(r"20\d{2}-\d{2}-\d{2}", text)
    month_matches = re.findall(r"20\d{2}-\d{2}", text)
    if date_matches:
        unique_dates = sorted(set(date_matches))
        if len(unique_dates) == 1:
            return unique_dates[0]
        return f"{unique_dates[0]}..{unique_dates[-1]}"
    if month_matches:
        unique_months = sorted(set(month_matches))
        if len(unique_months) == 1:
            return unique_months[0]
        return f"{unique_months[0]}..{unique_months[-1]}"
    return "unknown"


def _source_family(path: Path) -> str:
    lower = path.as_posix().lower()
    if "orderbook/binance_futures/btcusdt" in lower:
        prefix = path.as_posix().split("orderbook/binance_futures/BTCUSDT", 1)[0] + "orderbook/binance_futures/BTCUSDT"
        return prefix
    if "aggtrades/btcusdt" in lower:
        prefix = path.as_posix().split("aggTrades/BTCUSDT", 1)[0] + "aggTrades/BTCUSDT"
        if "2020-05-22_to_2026-05-21" in lower:
            prefix = path.as_posix().split("aggTrades/BTCUSDT/2020-05-22_to_2026-05-21", 1)[0] + "aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"
        return prefix
    if "bars_750btc" in lower:
        prefix = path.as_posix().split("bars_750btc", 1)[0] + "bars_750btc"
        return prefix
    return str(path.parent)


def _file_type_by_name(path: Path) -> tuple[str, str, str, str]:
    lower = path.as_posix().lower()
    ext = "".join(path.suffixes).lower() or path.suffix.lower()

    if path.suffix.lower() in {".md", ".txt", ".toml", ".yaml", ".yml", ".json"} or path.name.lower().endswith(".checksum"):
        if "checksum" in lower or path.name.lower().endswith(".checksum"):
            return "manifest", "not_ready_manifest_only", "documentation", "Document-only."
        return "manifest", "not_ready_manifest_only", "documentation", "Document-only."

    if "ofi" in lower:
        return "ofi_output", "possibly_ready_needs_schema_check", "research_only", "Validate provenance and resync coverage before using derived OFI."

    if "aggtrades" in lower:
        return "agg_trades", "not_ready_trades_only", "high", "Not an L2 source; cannot reconstruct OFI from trades alone."

    if "bookticker" in lower:
        return "book_ticker", "possibly_ready_needs_schema_check", "moderate", "Top-of-book only; insufficient for full OFI."

    if "full_depth" in lower or re.search(r"(^|[^a-z0-9])tbt([^a-z0-9]|$)", lower) or re.search(r"(^|[^a-z0-9])mbo([^a-z0-9]|$)", lower) or re.search(r"(^|[^a-z0-9])mbp([^a-z0-9]|$)", lower):
        return "l2_tbt", "ofi_reconstruction_ready", "moderate", "Likely full-depth or tick-by-tick order book source."

    if "depthupdate" in lower or "orderbook" in lower or "snapshot" in lower or "diff" in lower:
        return "l2_diff", "possibly_ready_needs_schema_check", "moderate", "Likely L2 diff/order-book source; confirm schema."

    if "trades" in lower:
        return "trade_ticks", "not_ready_trades_only", "high", "Trade ticks are not sufficient to reconstruct OFI."

    if re.search(r"(ohlcv|kline|candles?|bars?)", lower):
        return "ohlcv", "not_ready_ohlcv_only", "high", "OHLCV bars are not L2 OFI sources."

    return "unknown", "not_ready_unknown", "high", "Unclear source type."


def classify_candidate_path(path: Path) -> tuple[str, str, str, str]:
    """Public helper for tests: classify a path by filename/path only."""
    return _file_type_by_name(path)


def _schema_supports_ofi(schema_columns: list[str]) -> bool:
    lower_cols = {col.lower() for col in schema_columns}
    has_update_ids = {"first_update_id", "final_update_id", "last_update_id"}.intersection(lower_cols)
    has_levels = {"bid", "ask", "bids", "asks"}.intersection(lower_cols)
    has_trade_fields = {"price", "quantity", "qty", "side"}.intersection(lower_cols)
    has_time = {"timestamp", "time", "event_time", "datetime", "transaction_time"}.intersection(lower_cols)
    return bool(has_time and has_trade_fields and (has_update_ids or has_levels))


def _read_schema_hint(path: Path) -> tuple[str, bool]:
    try:
        if path.name.lower().endswith(".parquet.zst") or ".zst" in path.suffixes:
            with path.open("rb") as fh:
                data = zstd.ZstdDecompressor().decompress(fh.read())
            schema = pq.read_schema(io.BytesIO(data))
        elif path.suffix.lower() == ".parquet":
            schema = pq.read_schema(path)
        else:
            return "schema_not_applicable", False
        columns = list(schema.names)
        return ", ".join(columns), _schema_supports_ofi(columns)
    except Exception as exc:  # pragma: no cover - defensive reporting
        return f"schema_unavailable: {type(exc).__name__}", False


@lru_cache(maxsize=128)
def _sample_schema_hint(path_str: str) -> tuple[str, bool]:
    return _read_schema_hint(Path(path_str))


def _schema_group_key(path: Path, data_type_guess: str) -> str | None:
    if data_type_guess in {"l2_diff", "l2_tbt", "book_ticker", "ofi_output"}:
        return f"{data_type_guess}:{path.name.lower()}"
    return None


def _scan_root(root: Path) -> tuple[RootStatus, list[CandidateRecord]]:
    if not root.exists():
        return RootStatus(path=str(root), exists=False, candidate_count=0, note="missing root"), []

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_PARTS]
        current = Path(dirpath)
        if root == Path("/mnt/seagate") and not any(part in {"tm-trading-v555", "tm-trading-v92-phase1f"} for part in current.parts):
            if current == root:
                dirnames[:] = [d for d in dirnames if d in {"tm-trading-v555", "tm-trading-v92-phase1f"}]
            continue
        for name in filenames:
            path = current / name
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in SEARCH_SUFFIXES and not path.name.lower().endswith(".parquet.zst"):
                continue
            if not _is_candidate_path(path):
                continue
            files.append(path)

    schema_cache: dict[str, tuple[str, bool]] = {}
    records = [_build_candidate_record(path, root, schema_cache) for path in sorted(files)]
    note = "present"
    if records:
        families = Counter(row.data_type_guess for row in records)
        note = ", ".join(f"{k}:{v}" for k, v in families.most_common(3))
    return RootStatus(path=str(root), exists=True, candidate_count=len(records), note=note), records


def _is_candidate_path(path: Path) -> bool:
    text = path.as_posix().lower()
    if any(term in text for term in ("orderbook", "aggtrades", "bookticker", "depthupdate", "ofi", "snapshot", "diff", "tbt", "mbo", "mbp", "ohlcv", "kline", "candles", "bar", "trade")):
        return True
    if path.suffix.lower() in {".md", ".txt", ".toml", ".yaml", ".yml", ".json"} or path.name.lower().endswith(".checksum"):
        return True
    return False


def _build_candidate_record(path: Path, root: Path, schema_cache: dict[str, tuple[str, bool]]) -> CandidateRecord:
    data_type_guess, readiness, risk, required_action = _file_type_by_name(path)
    symbol = _guess_symbol(path)
    venue = _guess_venue(path)
    terms = _match_terms(path)
    time_coverage = _guess_time_coverage(path)
    schema_hint = "schema_not_applicable"
    usable = readiness

    schema_key = _schema_group_key(path, data_type_guess)
    if schema_key is not None and (path.name.lower().endswith(".parquet.zst") or path.suffix.lower() == ".parquet"):
        if schema_key not in schema_cache:
            schema_cache[schema_key] = _sample_schema_hint(str(path))
        schema_hint, schema_supports_ofi = schema_cache[schema_key]
        if schema_supports_ofi and data_type_guess in {"l2_diff", "l2_tbt"}:
            usable = "ofi_reconstruction_ready"
        elif data_type_guess == "book_ticker":
            usable = "possibly_ready_needs_schema_check"
    elif data_type_guess in {"agg_trades", "trade_ticks", "ohlcv", "manifest"}:
        schema_hint = "schema_not_applicable"

    if data_type_guess == "l2_diff" and usable != "ofi_reconstruction_ready":
        required_action = "Confirm schema and sequence continuity before reconstruction."
    elif data_type_guess == "l2_tbt":
        required_action = "Validate raw depth schema and sequence coverage before reconstruction."
    elif data_type_guess == "ofi_output":
        required_action = "Validate provenance and resync fields before any use."

    if usable == "ofi_reconstruction_ready":
        risk = "moderate"
    elif usable.startswith("not_ready"):
        risk = "high"
    else:
        risk = "moderate"

    stat = path.stat()
    return CandidateRecord(
        path=str(path),
        file_size_bytes=stat.st_size,
        extension="".join(path.suffixes) or path.suffix,
        mtime_utc=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        name_match_terms=", ".join(terms) if terms else "none",
        parent_dir=str(path.parent),
        symbol_guess=symbol,
        venue_guess=venue,
        data_type_guess=data_type_guess,
        time_coverage_guess=time_coverage,
        schema_hint=schema_hint,
        usable_for_ofi_reconstruction_guess=usable,
        risk=risk,
        required_action=required_action,
        readiness=usable,
        source_family=_source_family(path),
    )


def _relative_display(path: str) -> str:
    return path.replace(str(Path.cwd()) + os.sep, "")


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        vals = []
        for col in columns:
            val = row.get(col, "")
            if isinstance(val, float):
                vals.append(f"{val:.6f}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def _group_records(records: list[CandidateRecord]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], list[CandidateRecord]] = defaultdict(list)
    for row in records:
        key = (row.data_type_guess, row.venue_guess, row.symbol_guess, row.source_family)
        groups[key].append(row)

    summary_rows = []
    for (data_type, venue, symbol, parent_dir), group in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3])):
        sizes = [r.file_size_bytes for r in group]
        sample = group[0]
        summary_rows.append(
            {
                "data_type_guess": data_type,
                "venue_guess": venue,
                "symbol_guess": symbol,
                "file_count": len(group),
                "example_path": sample.path,
                "time_coverage_guess": sample.time_coverage_guess,
                "schema_hint": sample.schema_hint,
                "usable_for_ofi_reconstruction_guess": sample.usable_for_ofi_reconstruction_guess,
                "file_size_mib": (sum(sizes) / len(sizes)) / (1024 * 1024),
                "risk": sample.risk,
                "required_action": sample.required_action,
            }
        )
    return summary_rows


def _check_data_policy_helper() -> tuple[bool, str]:
    try:
        import polars as pl
        from features.v92_data_policy import join_ofi_to_bars_preserve_coverage
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"import failed: {type(exc).__name__}"

    try:
        bars = pl.DataFrame(
            {
                "open_time": [1_600_000_000_000],
                "close_time": [1_600_000_000_500],
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "volume": [1.0],
            }
        )
        ofi = pl.DataFrame({"datetime": [datetime(2020, 1, 1, tzinfo=timezone.utc)], "ofi": [0.0]})
        out = join_ofi_to_bars_preserve_coverage(bars, ofi)
        ok = out.height == bars.height and "bar_ofi" in out.columns and "has_ofi_coverage" in out.columns
        return ok, "importable and callable" if ok else "callable check failed"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"call failed: {type(exc).__name__}"


def audit_inventory(search_roots: list[Path]) -> AuditResult:
    root_status: list[RootStatus] = []
    candidates: list[CandidateRecord] = []
    for root in search_roots:
        status, rows = _scan_root(root)
        root_status.append(status)
        candidates.extend(rows)
    unique_candidates: list[CandidateRecord] = []
    seen_paths: set[str] = set()
    for row in candidates:
        if row.path in seen_paths:
            continue
        seen_paths.add(row.path)
        unique_candidates.append(row)
    helper_ok, helper_note = _check_data_policy_helper()
    return AuditResult(root_status=root_status, candidates=unique_candidates, data_policy_helper_ok=helper_ok, data_policy_helper_note=helper_note)


def render_report(result: AuditResult) -> str:
    candidates = result.candidates
    counts_by_type = Counter(row.data_type_guess for row in candidates)
    readiness_counts = Counter(row.usable_for_ofi_reconstruction_guess for row in candidates)
    ofi_outputs = [row for row in candidates if row.data_type_guess == "ofi_output"]
    l2_rows = [row for row in candidates if row.data_type_guess in {"l2_diff", "l2_snapshot", "l2_tbt"}]
    trade_rows = [row for row in candidates if row.data_type_guess in {"agg_trades", "trade_ticks"}]
    manifest_rows = [row for row in candidates if row.data_type_guess == "manifest"]
    ohlcv_rows = [row for row in candidates if row.data_type_guess == "ohlcv"]
    sample_rows = _group_records(candidates)

    lines: list[str] = []
    lines.append("# V9.2 L2 / OFI Source Inventory Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Inventory read-only historical L2 and OFI-related source files on the Seagate drive and classify whether they are usable for OFI reconstruction research.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("- Search roots supplied on the CLI.")
    lines.append("- Historical Seagate HFT order-book, trade, and documentation files discovered by filename/path scan.")
    lines.append("- Existing 750 BTC bar outputs under the phase1f workspace are treated as context only.")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This audit only reads file metadata, schemas for sampled parquet files, and short text headers where applicable.")
    lines.append("It does not extract archives, regenerate OFI, regenerate bars, or modify any source data.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Executive Finding")
    if candidates:
        lines.append(
            "Historical OFI output files were not found, but a substantial Binance futures order-book corpus exists on Seagate under `cryptohftdata/orderbook/binance_futures/BTCUSDT`, and the sampled parquet schema contains timestamp and update-id fields suitable for OFI reconstruction research."
        )
    else:
        lines.append("No relevant L2/OFI source candidates were discovered under the supplied roots.")
    lines.append("")
    lines.append(f"- Historical OFI output files found: {'yes' if ofi_outputs else 'no'}.")
    lines.append(f"- L2 snapshot/diff/TBT/full-depth files found: {'yes' if l2_rows else 'no'}.")
    lines.append(f"- Only trades/aggTrades/bars found: {'no' if l2_rows else 'yes'}; this inventory includes raw L2 order-book sources.")
    lines.append(f"- Enough source data to reconstruct OFI: {'yes' if any(row.usable_for_ofi_reconstruction_guess == 'ofi_reconstruction_ready' for row in candidates) else 'no'}.")
    lines.append(f"- OFI approved for alpha/paper/live use: No.")
    lines.append("- Next safe validation step: read-only provenance and sequence/coverage verification on the raw L2 order-book corpus, then validate any OFI join helper against those files.")
    lines.append("")

    lines.append("## Search Root Status")
    root_rows = [asdict(r) for r in result.root_status]
    if root_rows:
        lines.append(_table(root_rows, ["path", "exists", "candidate_count", "note"]))
    else:
        lines.append("No search roots were processed.")
    lines.append("")

    lines.append("## Candidate Inventory Summary")
    summary_rows = [
        {"data_type_guess": k, "file_count": v} for k, v in counts_by_type.most_common()
    ]
    if summary_rows:
        lines.append(_table(summary_rows, ["data_type_guess", "file_count"]))
    else:
        lines.append("No candidate files were discovered.")
    lines.append("")
    lines.append("Readiness summary:")
    if readiness_counts:
        lines.append(_table([{"readiness": k, "file_count": v} for k, v in readiness_counts.most_common()], ["readiness", "file_count"]))
    else:
        lines.append("No readiness classifications available.")
    lines.append("")

    lines.append("## Candidate File Inventory")
    if sample_rows:
        lines.append(
            _table(
                sample_rows,
                [
                    "data_type_guess",
                    "venue_guess",
                    "symbol_guess",
                    "file_count",
                    "example_path",
                    "time_coverage_guess",
                    "schema_hint",
                    "usable_for_ofi_reconstruction_guess",
                    "risk",
                    "required_action",
                ],
            )
        )
    else:
        lines.append("No candidate files were found.")
    lines.append("")

    lines.append("## Likely L2 Sources")
    if l2_rows:
        lines.append(
            _table(
                _group_records(l2_rows),
                ["data_type_guess", "venue_guess", "symbol_guess", "file_count", "example_path", "time_coverage_guess", "schema_hint", "usable_for_ofi_reconstruction_guess", "required_action"],
            )
        )
    else:
        lines.append("No likely L2 source files were found.")
    lines.append("")

    lines.append("## Likely HFT Full-Depth Sources")
    tbt_rows = [row for row in candidates if row.data_type_guess == "l2_tbt"]
    if tbt_rows:
        lines.append(
            _table(
                _group_records(tbt_rows),
                ["data_type_guess", "venue_guess", "symbol_guess", "file_count", "example_path", "time_coverage_guess", "schema_hint", "usable_for_ofi_reconstruction_guess", "required_action"],
            )
        )
    else:
        lines.append("No distinct full-depth/TBT source files were discovered beyond the order-book diff corpus.")
    lines.append("")

    lines.append("## Likely OFI Outputs")
    if ofi_outputs:
        lines.append(_table(_group_records(ofi_outputs), ["data_type_guess", "venue_guess", "symbol_guess", "file_count", "example_path", "time_coverage_guess", "schema_hint", "usable_for_ofi_reconstruction_guess", "required_action"]))
    else:
        lines.append("No historical OFI output files were discovered under the supplied roots.")
    lines.append("")

    lines.append("## Trade-Only / Not-L2 Sources")
    if trade_rows:
        lines.append(_table(_group_records(trade_rows), ["data_type_guess", "venue_guess", "symbol_guess", "file_count", "example_path", "time_coverage_guess", "schema_hint", "usable_for_ofi_reconstruction_guess", "required_action"]))
    else:
        lines.append("No trade-only sources were discovered.")
    lines.append("")

    lines.append("## Manifest / Documentation Sources")
    if manifest_rows:
        lines.append(_table(_group_records(manifest_rows), ["data_type_guess", "venue_guess", "symbol_guess", "file_count", "example_path", "time_coverage_guess", "schema_hint", "usable_for_ofi_reconstruction_guess", "required_action"]))
    else:
        lines.append("No manifest/documentation sources were discovered in the audited roots.")
    lines.append("")

    lines.append("## Missing Roots")
    missing = [r.path for r in result.root_status if not r.exists]
    if missing:
        lines.append(_table([{"missing_root": m} for m in missing], ["missing_root"]))
    else:
        lines.append("No search roots were missing.")
    lines.append("")

    lines.append("## OFI Reconstruction Readiness")
    if any(row.usable_for_ofi_reconstruction_guess == "ofi_reconstruction_ready" for row in candidates):
        lines.append("The historical Seagate order-book corpus is reconstruction-ready at the source level because the sampled parquet schema contains timestamps, update IDs, and order-book update fields.")
        lines.append("Historical OFI output inventory is still unavailable, so no derived OFI artifact is being claimed as production-ready.")
    elif any(row.usable_for_ofi_reconstruction_guess == "possibly_ready_needs_schema_check" for row in candidates):
        lines.append("The audit found potentially useful L2 sources, but the available evidence is not yet enough to claim OFI reconstruction readiness without schema and sequence validation.")
    else:
        lines.append("No reconstruction-ready L2 sources were discovered.")
    lines.append("")

    lines.append("## What Is Safe")
    lines.append("- Read-only inventory of Seagate HFT source files.")
    lines.append("- `features.v92_data_policy.join_ofi_to_bars_preserve_coverage` is importable and callable.")
    lines.append("- The Binance futures order-book corpus is a concrete raw L2 source family for future provenance checks.")
    lines.append("")

    lines.append("## What Is Not Safe")
    lines.append("- Treating this inventory as proof that OFI is production-ready.")
    lines.append("- Treating the absence of historical OFI output files as evidence that raw L2 reconstruction is impossible.")
    lines.append("- Treating aggTrades or OHLCV bars as sufficient OFI sources.")
    lines.append("")

    lines.append("## Required Next Step")
    lines.append("Run a read-only provenance and sequence-gap audit on the raw order-book corpus, then validate a coverage-preserving OFI join path against a small sample before considering any broader research use.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit_inventory(args.search_roots)
    report = render_report(result)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
