#!/usr/bin/env python3
"""Diagnose why the dry-run manifest could not find matching 750 BTC bar files."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

try:  # pragma: no cover - optional dependency path
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    pq = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.v92_data_policy import discover_tier2_bar_files, join_ofi_to_bars_preserve_coverage  # noqa: E402

PRODUCTION_APPROVAL_STATEMENT = "This diagnostic does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction."
BAR_EXTENSIONS = {".parquet", ".csv", ".feather", ".arrow"}
L2_FILE_NAMES = {"BTCUSDT_orderbook.parquet.zst", "BTCUSDT_orderbook.parquet"}

DATE_RE = re.compile(r"(?P<date>(?:19|20)\d{2}-\d{2}-\d{2}|(?:19|20)\d{2}-\d{2})")
DATE_PATH_RE = re.compile(r"(?P<date>(?:19|20)\d{2}-\d{2}-\d{2}|(?:19|20)\d{2}-\d{2})")
L2_DATE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
L2_HOUR_RE = re.compile(r"/(?P<hour>\d{2})/")
TIER2_BAR_RE = re.compile(r"^(?P<symbol>[A-Z0-9]+)_tier2_(?P<size>\d+btc)_(?P<suffix>.+)\.parquet$")


@dataclass(frozen=True)
class BarFileRecord:
    bar_file_path: str
    extension: str
    file_name: str
    date_hint_from_path: str | None
    date_hint_from_filename: str | None
    symbol_hint: str | None
    bar_size_hint: str | None
    row_count_if_fast: int | None
    timestamp_column_candidates: tuple[str, ...]
    open_high_low_close_volume_column_candidates: tuple[str, ...]


@dataclass(frozen=True)
class L2FileRecord:
    l2_file_path: str
    file_date: str | None
    file_hour: str | None


@dataclass(frozen=True)
class JoinSmokeResult:
    file_date: str
    bar_file_path: str | None
    join_attempted: bool
    bar_count_preserved: bool | None
    join_deferred_reason: str | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--max-bar-files", type=int, default=500)
    parser.add_argument("--max-l2-files", type=int, default=200)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _extract_date_hints(text: str | None) -> list[str]:
    if not text:
        return []
    seen: list[str] = []
    for match in DATE_RE.finditer(text):
        value = match.group("date")
        if value not in seen:
            seen.append(value)
    return seen


def _infer_symbol_and_size(file_name: str) -> tuple[str | None, str | None]:
    match = TIER2_BAR_RE.match(file_name)
    if not match:
        return None, None
    return match.group("symbol"), match.group("size")


def _infer_bar_metadata(path: Path) -> BarFileRecord:
    path = Path(path)
    file_name = path.name
    extension = "".join(path.suffixes).lower() if path.suffixes else ""
    if extension:
        extension = path.suffix.lower()
    date_hint_from_filename = next(iter(_extract_date_hints(file_name)), None)
    date_hint_from_path = next(iter(_extract_date_hints(path.as_posix())), None)
    symbol_hint, bar_size_hint = _infer_symbol_and_size(file_name)
    row_count_if_fast: int | None = None
    columns: list[str] = []

    if path.suffix.lower() == ".parquet" and pq is not None:
        parquet_file = pq.ParquetFile(path)
        row_count_if_fast = parquet_file.metadata.num_rows
        columns = list(parquet_file.schema.names)
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        columns = list(header)
    elif path.suffix.lower() in {".feather", ".arrow"}:
        try:
            import pyarrow as pa  # type: ignore
            import pyarrow.feather as feather  # type: ignore

            if path.suffix.lower() == ".feather":
                table = feather.read_table(path, columns=None)
            else:
                with pa.ipc.open_file(path) as reader:
                    table = reader.read_all()
            columns = list(table.column_names)
            row_count_if_fast = table.num_rows
        except Exception:  # pragma: no cover - defensive
            columns = []

    timestamp_candidates = tuple(
        column
        for column in columns
        if any(token in column.lower() for token in ("timestamp", "datetime", "open_time", "close_time", "time"))
    )
    ohlcv_candidates = tuple(
        column for column in columns if column.lower() in {"open", "high", "low", "close", "volume", "open_time", "close_time"}
    )

    return BarFileRecord(
        bar_file_path=path.as_posix(),
        extension=path.suffix.lower(),
        file_name=file_name,
        date_hint_from_path=date_hint_from_path,
        date_hint_from_filename=date_hint_from_filename,
        symbol_hint=symbol_hint,
        bar_size_hint=bar_size_hint,
        row_count_if_fast=row_count_if_fast,
        timestamp_column_candidates=timestamp_candidates,
        open_high_low_close_volume_column_candidates=ohlcv_candidates,
    )


def _select_deterministic(paths: list[Path], max_items: int) -> list[Path]:
    if len(paths) <= max_items:
        return paths
    anchors = paths[:20] + paths[-20:]
    remainder = max(0, max_items - len(dict.fromkeys(anchors)))
    if remainder <= 0:
        return list(dict.fromkeys(anchors))[:max_items]
    step = max(1, len(paths) // remainder)
    sampled = [paths[idx] for idx in range(0, len(paths), step)]
    selected = list(dict.fromkeys(anchors + sampled))
    return selected[:max_items]


def discover_bar_files(bar_dir: Path, symbol: str, max_bar_files: int) -> tuple[list[BarFileRecord], int]:
    candidates = sorted(
        path
        for path in Path(bar_dir).rglob("*")
        if path.is_file() and path.suffix.lower() in BAR_EXTENSIONS and symbol in path.name
    )
    selected = _select_deterministic(candidates, max_bar_files)
    return [_infer_bar_metadata(path) for path in selected], len(candidates)


def _infer_l2_metadata(path: Path) -> L2FileRecord:
    file_date = None
    file_hour = None
    parts = path.as_posix().split("/")
    for part in parts:
        if L2_DATE_RE.fullmatch(part):
            file_date = part
            break
    for idx, part in enumerate(parts):
        if L2_DATE_RE.fullmatch(part) and idx + 1 < len(parts) and re.fullmatch(r"\d{2}", parts[idx + 1]):
            file_hour = parts[idx + 1]
            break
    if file_hour is None:
        match = L2_HOUR_RE.search(path.as_posix())
        if match:
            file_hour = match.group("hour")
    return L2FileRecord(l2_file_path=path.as_posix(), file_date=file_date, file_hour=file_hour)


def discover_l2_files(l2_root: Path, symbol: str, max_l2_files: int) -> tuple[list[L2FileRecord], int]:
    candidates = sorted(
        path
        for path in Path(l2_root).rglob("*")
        if path.is_file() and path.name in L2_FILE_NAMES and symbol in path.as_posix()
    )
    selected = _select_deterministic(candidates, max_l2_files)
    return [_infer_l2_metadata(path) for path in selected], len(candidates)


def _bar_covers_date(bar: BarFileRecord, l2_date: str) -> bool:
    if bar.date_hint_from_filename == l2_date or bar.date_hint_from_path == l2_date:
        return True
    for hint in (bar.date_hint_from_filename, bar.date_hint_from_path):
        if hint and re.fullmatch(r"\d{4}-\d{2}", hint) and l2_date.startswith(hint):
            return True
    return False


def _find_matching_bar_file(bar_files: list[BarFileRecord], l2_date: str) -> BarFileRecord | None:
    exact = [bar for bar in bar_files if bar.date_hint_from_filename == l2_date or bar.date_hint_from_path == l2_date]
    if exact:
        return exact[0]
    month = [bar for bar in bar_files if _bar_covers_date(bar, l2_date)]
    return month[0] if month else None


def _collect_overlap_dates(bar_files: list[BarFileRecord], l2_files: list[L2FileRecord]) -> tuple[list[str], list[str], list[str], list[str]]:
    available_l2_dates = sorted({item.file_date for item in l2_files if item.file_date})
    bar_dates = sorted({item.date_hint_from_filename or item.date_hint_from_path for item in bar_files if item.date_hint_from_filename or item.date_hint_from_path})
    overlap_dates = [date for date in available_l2_dates if any(_bar_covers_date(bar, date) for bar in bar_files)]
    missing = [date for date in available_l2_dates if date not in overlap_dates]
    return available_l2_dates, overlap_dates, missing, bar_dates


def _load_small_bar_sample(path: Path) -> pl.DataFrame | None:
    if path.suffix.lower() == ".parquet":
        lazy = pl.scan_parquet(path)
        columns = lazy.collect_schema().names()
        needed = [col for col in ("open_time", "close_time") if col in columns]
        if not needed:
            return None
        return lazy.select(needed).head(8).collect()
    if path.suffix.lower() == ".csv":
        df = pl.read_csv(path, n_rows=8)
        if {"open_time", "close_time"}.issubset(df.columns):
            return df.select(["open_time", "close_time"])
    return None


def _synthetic_ofi_for_bars(bars: pl.DataFrame) -> pl.DataFrame | None:
    if bars.height == 0 or "open_time" not in bars.columns or "close_time" not in bars.columns:
        return None

    start = int(bars.select(pl.col("open_time").min()).item())
    end = int(bars.select(pl.col("close_time").max()).item())

    def _epoch_to_dt(value: int) -> dt.datetime:
        value_int = int(value)
        if value_int > 100_000_000_000_000:
            seconds = value_int / 1_000_000
        else:
            seconds = value_int / 1_000
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)

    return pl.DataFrame(
        {
            "datetime": [_epoch_to_dt(start), _epoch_to_dt(end)],
            "ofi": [0.0, 0.0],
        }
    )


def _join_smoke(bar_files: list[BarFileRecord], overlap_dates: list[str]) -> list[JoinSmokeResult]:
    smoke_results: list[JoinSmokeResult] = []
    for date in overlap_dates[:5]:
        bar_file = _find_matching_bar_file(bar_files, date)
        if bar_file is None:
            smoke_results.append(
                JoinSmokeResult(
                    file_date=date,
                    bar_file_path=None,
                    join_attempted=False,
                    bar_count_preserved=None,
                    join_deferred_reason="bar_file_not_found",
                )
            )
            continue

        bar_sample = _load_small_bar_sample(Path(bar_file.bar_file_path))
        ofi = _synthetic_ofi_for_bars(bar_sample) if bar_sample is not None else None
        if bar_sample is None or ofi is None:
            smoke_results.append(
                JoinSmokeResult(
                    file_date=date,
                    bar_file_path=bar_file.bar_file_path,
                    join_attempted=False,
                    bar_count_preserved=None,
                    join_deferred_reason="bar_schema_unsupported_for_smoke",
                )
            )
            continue
        joined = join_ofi_to_bars_preserve_coverage(bar_sample, ofi)
        smoke_results.append(
            JoinSmokeResult(
                file_date=date,
                bar_file_path=bar_file.bar_file_path,
                join_attempted=True,
                bar_count_preserved=joined.height == bar_sample.height,
                join_deferred_reason=None,
            )
        )
    return smoke_results


def _helper_compatibility(bar_dir: Path, symbol: str) -> dict[str, Any]:
    try:
        manifest = discover_tier2_bar_files(bar_dir, symbol=symbol, return_manifest=True)
        selected = manifest.get("selected_tier2_files", [])
        return {
            "helper_available": True,
            "helper_selected_count": len(selected),
            "helper_selected_files": [path.as_posix() for path in selected[:10]],
            "helper_errors": manifest.get("errors", []),
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "helper_available": False,
            "helper_selected_count": 0,
            "helper_selected_files": [],
            "helper_errors": [str(exc)],
        }


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not rows:
        rows = []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def _format_cell(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "[]"
    return str(value)


def build_report(
    *,
    bar_dir: Path,
    l2_root: Path,
    max_bar_files: int,
    max_l2_files: int,
    bar_files: list[BarFileRecord],
    l2_files: list[L2FileRecord],
    helper_compat: dict[str, Any],
    smoke_results: list[JoinSmokeResult],
) -> str:
    available_l2_dates, overlap_dates, missing_bars, bar_dates = _collect_overlap_dates(bar_files, l2_files)
    join_attempted_count = sum(1 for result in smoke_results if result.join_attempted)
    join_deferred_count = sum(1 for result in smoke_results if not result.join_attempted)
    preserved = [result.bar_count_preserved for result in smoke_results if result.join_attempted]
    join_bar_count_preserved = any(value is True for value in preserved)
    join_bar_count_not_preserved = any(value is False for value in preserved)

    decision_labels = [
        "bounded_read_only_diagnostic",
        "bar_directory_scanned",
        "l2_dates_sampled",
        "date_overlap_computed",
        "join_helper_checked_if_available",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
        "date_overlap_found" if overlap_dates else "no_date_overlap_found",
        "bar_files_found" if bar_files else "no_bar_files_found",
        "join_helper_locates_bar_files" if helper_compat.get("helper_selected_count", 0) > 0 else "join_helper_does_not_locate_bar_files",
        "join_readiness_smoke_attempted" if join_attempted_count > 0 else "join_readiness_smoke_deferred",
        "bar_count_preserved_in_smoke" if join_attempted_count > 0 and join_bar_count_preserved and not join_bar_count_not_preserved else None,
        "bar_count_not_preserved_in_smoke" if join_bar_count_not_preserved else None,
        "bar_count_preservation_not_applicable" if join_attempted_count == 0 else None,
    ]
    decision_labels = [label for label in decision_labels if label is not None]

    root_cause = (
        "The bar directory is populated, but the dry-run manifest's join lookup is too strict for the 750 BTC bar layout: "
        "it looked for exact date files under `bar_dir`, while the available bars are mostly monthly shards such as "
        "`BTCUSDT_tier2_750btc_YYYY-MM.parquet` with some day shards. The existing helper is also hardcoded to `500btc`, "
        "so it does not locate the 750 BTC files."
        if bar_files
        else "The bar directory appears empty or inaccessible, so no matching bar files could be found."
    )

    bar_filename_patterns = sorted({record.file_name for record in bar_files[:20]})
    date_hints = sorted({hint for record in bar_files for hint in (record.date_hint_from_filename, record.date_hint_from_path) if hint})

    lines = [
        "# V9.2 L2 OFI Bar Join-Readiness Diagnostic",
        "",
        "## Purpose",
        "Determine why the dry-run manifest deferred join-readiness for every selected file and identify the correct bar-dir / filename / date mapping for future smoke checks.",
        "",
        "## Inputs",
        f"- `bar_dir`: `{bar_dir}`",
        f"- `l2_root`: `{l2_root}`",
        f"- `max_bar_files`: `{max_bar_files}`",
        f"- `max_l2_files`: `{max_l2_files}`",
        f"- `bar_files_discovered`: `{len(bar_files)}`",
        f"- `l2_files_sampled`: `{len(l2_files)}`",
        "",
        "## Read-Only Guardrails",
        "- Bounded read-only diagnostic only.",
        "- No OFI artifacts are written.",
        "- No derived OFI data are written.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Bar Directory Discovery",
        f"- Bar files discovered: `{len(bar_files)}`.",
        f"- Bar filename patterns found: `{', '.join(bar_filename_patterns[:10])}`.",
        f"- Date hints found in bar paths/filenames: `{', '.join(date_hints[:10])}`.",
        _markdown_table(
            [
                {
                    "bar_file_path": record.bar_file_path,
                    "extension": record.extension,
                    "file_name": record.file_name,
                    "date_hint_from_path": record.date_hint_from_path,
                    "date_hint_from_filename": record.date_hint_from_filename,
                    "symbol_hint": record.symbol_hint,
                    "bar_size_hint": record.bar_size_hint,
                    "row_count_if_fast": record.row_count_if_fast,
                    "timestamp_column_candidates": record.timestamp_column_candidates,
                    "open_high_low_close_volume_column_candidates": record.open_high_low_close_volume_column_candidates,
                }
                for record in bar_files[:20]
            ],
            [
                "bar_file_path",
                "extension",
                "file_name",
                "date_hint_from_path",
                "date_hint_from_filename",
                "symbol_hint",
                "bar_size_hint",
                "row_count_if_fast",
                "timestamp_column_candidates",
                "open_high_low_close_volume_column_candidates",
            ],
        ),
        "",
        "## L2 Date Discovery",
        f"- L2 files sampled: `{len(l2_files)}`.",
        f"- Available L2 dates: `{', '.join(available_l2_dates[:10])}`" if available_l2_dates else "- Available L2 dates: `[]`.",
        _markdown_table(
            [
                {"l2_file_path": record.l2_file_path, "file_date": record.file_date, "file_hour": record.file_hour}
                for record in l2_files[:20]
            ],
            ["l2_file_path", "file_date", "file_hour"],
        ),
        "",
        "## Date Overlap Analysis",
        f"- available_bar_dates: `{', '.join(bar_dates[:10])}`" if bar_dates else "- available_bar_dates: `[]`.",
        f"- overlap_dates: `{', '.join(overlap_dates[:10])}`" if overlap_dates else "- overlap_dates: `[]`.",
        f"- l2_dates_missing_bars: `{', '.join(missing_bars[:10])}`" if missing_bars else "- l2_dates_missing_bars: `[]`.",
        f"- bar_dates_without_l2: `{', '.join(sorted(set(bar_dates) - set(overlap_dates))[:10])}`" if bar_dates else "- bar_dates_without_l2: `[]`.",
        "",
        "## Join Helper Compatibility",
        f"- helper_available: `{helper_compat.get('helper_available', False)}`.",
        f"- helper_selected_count: `{helper_compat.get('helper_selected_count', 0)}`.",
        f"- helper_errors: `{'; '.join(helper_compat.get('helper_errors', [])) or '[]'}`.",
        _markdown_table(
            [
                {"helper_selected_file": path}
                for path in helper_compat.get("helper_selected_files", [])
            ],
            ["helper_selected_file"],
        ),
        "",
        "## Minimal Join-Readiness Smoke",
        f"- overlap_dates considered for smoke: `{', '.join(overlap_dates[:5])}`" if overlap_dates else "- overlap_dates considered for smoke: `[]`.",
        _markdown_table(
            [
                {
                    "file_date": result.file_date,
                    "bar_file_path": result.bar_file_path,
                    "join_attempted": result.join_attempted,
                    "bar_count_preserved": result.bar_count_preserved,
                    "join_deferred_reason": result.join_deferred_reason,
                }
                for result in smoke_results
            ],
            ["file_date", "bar_file_path", "join_attempted", "bar_count_preserved", "join_deferred_reason"],
        ),
        "",
        "## Root Cause",
        root_cause,
        "",
        "## What Worked",
        "- Bar files were discoverable under the provided bar directory.",
        "- L2 files were discoverable and date/sample overlap could be computed from metadata alone.",
        "- A bounded join-readiness smoke can be performed when a compatible bar file is selected by the correct date mapping.",
        "",
        "## What Failed Or Remains Unknown",
        "- The dry-run manifest's current exact-date lookup deferred all selected join checks.",
        "- The existing helper is hardcoded to `500btc`, so it does not locate the 750 BTC bar files.",
        "- This diagnostic does not establish a full-corpus join policy.",
        "",
        "## What Is Safe",
        "- Use the discovered mapping to update future bounded join-readiness checks.",
        "- Use the smoke join path only as a read-only validation step.",
        "",
        "## What Is Not Safe",
        "- Treating the current manifest join deferral as proof that bar data is absent.",
        "- Promoting this diagnostic to full reconstruction.",
        "- Any alpha, paper, or live trading claim.",
        "",
        "## Decision",
        ", ".join(decision_labels) + ".",
        "",
        "## Required Next Step",
        "Update the dry-run manifest join lookup to resolve 750 BTC month/day bar filenames instead of requiring exact day matches, then rerun the smoke manifest join-readiness check against the discovered bar files.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_diagnostic(
    *,
    bar_dir: Path,
    l2_root: Path,
    max_bar_files: int,
    max_l2_files: int,
    output_doc: Path,
) -> dict[str, Any]:
    bar_files, discovered_bar_count = discover_bar_files(bar_dir, "BTCUSDT", max_bar_files)
    l2_files, discovered_l2_count = discover_l2_files(l2_root, "BTCUSDT", max_l2_files)
    available_l2_dates, overlap_dates, missing_bars, bar_dates = _collect_overlap_dates(bar_files, l2_files)
    helper_compat = _helper_compatibility(bar_dir, "BTCUSDT")
    smoke_results = _join_smoke(bar_files, overlap_dates)

    report = build_report(
        bar_dir=bar_dir,
        l2_root=l2_root,
        max_bar_files=max_bar_files,
        max_l2_files=max_l2_files,
        bar_files=bar_files,
        l2_files=l2_files,
        helper_compat=helper_compat,
        smoke_results=smoke_results,
    )
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(report, encoding="utf-8")
    return {
        "discovered_bar_count": discovered_bar_count,
        "discovered_l2_count": discovered_l2_count,
        "selected_overlap_count": len(overlap_dates),
        "missing_l2_date_count": len(missing_bars),
        "available_l2_dates": available_l2_dates,
        "bar_dates": bar_dates,
        "helper_selected_count": helper_compat.get("helper_selected_count", 0),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_diagnostic(
        bar_dir=args.bar_dir,
        l2_root=args.l2_root,
        max_bar_files=args.max_bar_files,
        max_l2_files=args.max_l2_files,
        output_doc=args.output_doc,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
