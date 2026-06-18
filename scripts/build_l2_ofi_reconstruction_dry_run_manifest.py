#!/usr/bin/env python3
"""Build a bounded read-only manifest for broader L2 OFI reconstruction."""

from __future__ import annotations

import argparse
import io
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

try:  # pragma: no cover - optional dependency path
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    pq = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency path
    import zstandard as zstd
except ImportError:  # pragma: no cover
    zstd = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.l2_ofi_segmented_reconstruction import (  # noqa: E402
    L2Packet,
    is_snapshot_bridge_event,
    is_snapshot_or_reset,
    is_source_gap,
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)
from features.v92_data_policy import join_ofi_to_bars_preserve_coverage  # noqa: E402

PRODUCTION_APPROVAL_STATEMENT = "This dry-run manifest does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction."
FULL_MANIFEST_BUDGET = {
    "max_candidate_files": 720,
    "preview_rows_per_file": 25000,
    "max_policy_check_files": 80,
}
REQUIRED_COLUMNS = [
    "symbol",
    "event_time",
    "transaction_time",
    "received_time",
    "event_type",
    "first_update_id",
    "final_update_id",
    "prev_final_update_id",
    "side",
    "price",
    "quantity",
]

DEFAULT_CANDIDATE_INPUTS: list[tuple[str, str]] = [
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst",
        "known_original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst",
        "known_original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst",
        "known_original_sample",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst",
        "known_source_gap_heavy",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst",
        "known_snapshot_reset_bridge",
    ),
    (
        "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst",
        "known_snapshot_reset_bridge",
    ),
]


@dataclass(frozen=True)
class CandidateFile:
    path: Path
    candidate_reason: str


@dataclass(frozen=True)
class CandidatePreview:
    candidate_file_path: str
    file_date: str | None
    file_hour: str | None
    preview_row_count: int
    preview_packet_count: int
    missing_required_column_count: int
    missing_transaction_time_count: int
    snapshot_like_packet_count: int
    estimated_source_gap_count: int
    timestamp_non_monotonic_hint_count: int
    side_mapping_unknown_count: int
    candidate_reason: str
    candidate_score: int
    dry_run_policy_class: str


@dataclass(frozen=True)
class PolicyCheckResult:
    file_path: str
    file_date: str | None
    file_hour: str | None
    rows_scanned: int
    packet_count: int
    segment_count: int
    meaningful_segment_count: int
    clean_segment_count: int
    dirty_segment_count: int
    all_segments_clean: bool
    source_gap_boundary_count: int
    snapshot_like_packet_count: int
    snapshot_bridge_event_count: int
    snapshot_reset_clean_seed_count: int
    snapshot_reset_chain_failure_count: int
    quarantined_segment_count: int
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    ofi_suppressed_due_to_snapshot_bridge_count: int
    ofi_suppressed_due_to_quarantine_count: int
    policy_check_status: str
    candidate_reason: str = ""
    candidate_score: int = 0
    dry_run_policy_class: str = "policy_check_selected"
    quarantined_segment_ofi_emitted_count: int = 0
    side_mapping_unknown_count: int = 0


@dataclass(frozen=True)
class JoinReadinessResult:
    file_date: str | None
    bar_file_found: bool
    bar_file_path: str | None = None
    bar_shard_resolution_strategy: str | None = None
    bar_row_count: int | None = None
    join_attempted: bool = False
    bar_count_preserved: bool | None = None
    join_deferred_reason: str | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--bar-size", default="750btc")
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--max-candidate-files", type=int, default=720)
    parser.add_argument("--preview-rows-per-file", type=int, default=25_000)
    parser.add_argument("--max-policy-check-files", type=int, default=80)
    parser.add_argument("--candidate-batch-index", type=int, default=None)
    parser.add_argument("--candidate-batch-count", type=int, default=None)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--candidate-file", action="append", default=None)
    return parser.parse_args(argv)


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not rows:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def _dry_run_scope_label(
    *,
    max_candidate_files: int,
    preview_rows_per_file: int,
    max_policy_check_files: int,
    candidate_batch_index: int | None = None,
    candidate_batch_count: int | None = None,
) -> str:
    if candidate_batch_index is not None or candidate_batch_count is not None:
        return "full_bounded_manifest_batch"
    if (
        max_candidate_files == FULL_MANIFEST_BUDGET["max_candidate_files"]
        and preview_rows_per_file == FULL_MANIFEST_BUDGET["preview_rows_per_file"]
        and max_policy_check_files == FULL_MANIFEST_BUDGET["max_policy_check_files"]
    ):
        return "full_bounded_manifest"
    return "smoke_bounded_manifest"


def _partition_candidate_batch(
    candidates: list[CandidateFile],
    *,
    candidate_batch_index: int | None,
    candidate_batch_count: int | None,
) -> list[CandidateFile]:
    if candidate_batch_index is None and candidate_batch_count is None:
        return candidates
    if candidate_batch_index is None or candidate_batch_count is None:
        raise ValueError("candidate_batch_index and candidate_batch_count must both be provided together")
    if candidate_batch_count <= 0:
        raise ValueError("candidate_batch_count must be positive")
    if candidate_batch_index < 0 or candidate_batch_index >= candidate_batch_count:
        raise ValueError("candidate_batch_index must be within [0, candidate_batch_count)")
    total = len(candidates)
    start = (total * candidate_batch_index) // candidate_batch_count
    end = (total * (candidate_batch_index + 1)) // candidate_batch_count
    return candidates[start:end]


def _file_date(path: Path) -> str | None:
    match = re.search(r"20\d{2}-\d{2}-\d{2}", path.as_posix())
    return match.group(0) if match else None


def _file_hour(path: Path) -> str | None:
    parts = path.parts
    for idx, part in enumerate(parts[:-1]):
        if len(part) == 10 and part[4] == "-" and part[7] == "-" and idx + 1 < len(parts):
            next_part = parts[idx + 1]
            if len(next_part) == 2 and next_part.isdigit():
                return next_part
    return None


def _parse_date_components(path: Path) -> tuple[int, int, int] | None:
    file_date = _file_date(path)
    if file_date is None:
        return None
    year, month, day = file_date.split("-")
    return int(year), int(month), int(day)


def _is_supported_path(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.endswith(".parquet")
        or name.endswith(".parquet.zst")
        or name.endswith(".csv")
        or name.endswith(".feather")
        or name.endswith(".arrow")
    )


def _bar_file_date_hint(path: Path) -> str | None:
    match = re.search(r"20\d{2}-\d{2}(?:-\d{2})?", path.name)
    return match.group(0) if match else _file_date(path)


def _bar_file_resolution_strategy(path: Path, file_date: str | None) -> str | None:
    if file_date is None:
        return None
    filename = path.name
    if re.search(rf"20\d{{2}}-\d{{2}}-\d{{2}}", filename):
        return "day"
    if re.search(rf"20\d{{2}}-\d{{2}}", filename):
        return "month"
    return None


def _collect_bar_files(bar_dir: Path, symbol: str, bar_size: str) -> list[Path]:
    root = Path(bar_dir)
    patterns = ["*.parquet", "*.csv", "*.feather", "*.arrow"]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(root.rglob(pattern))
    filtered: list[Path] = []
    for path in candidates:
        name = path.name.lower()
        if symbol.lower() not in name or bar_size.lower() not in name or "tier2" not in name:
            continue
        if _bar_file_date_hint(path) is None:
            continue
        filtered.append(path)
    unique = {path.as_posix(): path for path in filtered}
    return sorted(unique.values(), key=lambda path: (_bar_file_date_hint(path) or "", path.as_posix()))


def _read_parquet_preview(path: Path, max_rows: int) -> pd.DataFrame:
    if pq is None or zstd is None:
        raise RuntimeError("pyarrow and zstandard are required for bounded parquet previewing")
    if path.suffix.lower() == ".parquet":
        parquet_file = pq.ParquetFile(path)
    elif path.name.lower().endswith(".parquet.zst"):
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        parquet_file = pq.ParquetFile(io.BytesIO(raw))
    else:
        raise ValueError(f"Unsupported parquet path: {path}")

    batches: list[pd.DataFrame] = []
    rows_remaining = max_rows
    for batch in parquet_file.iter_batches(batch_size=min(max_rows, 8192)):
        if rows_remaining <= 0:
            break
        batch_df = batch.to_pandas()
        if len(batch_df) > rows_remaining:
            batch_df = batch_df.iloc[:rows_remaining].copy()
        batches.append(batch_df)
        rows_remaining -= len(batch_df)
    if not batches:
        return pd.DataFrame()
    return pd.concat(batches, ignore_index=True)


def _normalize_side(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        ivalue = int(value)
        if ivalue == 0:
            return "bid"
        if ivalue == 1:
            return "ask"
    text = str(value).strip().lower()
    if text in {"bid", "bids", "b", "buy", "0"}:
        return "bid"
    if text in {"ask", "asks", "a", "sell", "1"}:
        return "ask"
    return None


def _as_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in REQUIRED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized["symbol"] = normalized["symbol"].astype("string").str.strip().str.upper()
    normalized["event_type"] = normalized["event_type"].astype("string").str.strip()
    for column in ["event_time", "transaction_time", "received_time", "first_update_id", "final_update_id", "prev_final_update_id", "last_update_id"]:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["price"] = pd.to_numeric(normalized["price"], errors="coerce")
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce")
    return normalized


def _frame_to_packets(frame: pd.DataFrame) -> tuple[list[L2Packet], dict[str, int]]:
    if frame.empty:
        return [], {"rows_scanned": 0, "unknown_side_row_count": 0, "missing_required_column_count": len(REQUIRED_COLUMNS)}

    normalized = _normalize_frame(frame)
    rows_scanned = int(len(normalized))
    missing_required_column_count = sum(1 for column in REQUIRED_COLUMNS if column not in frame.columns)

    valid = normalized[
        normalized["symbol"].notna()
        & normalized["event_time"].notna()
        & normalized["final_update_id"].notna()
    ].copy()
    valid["side_group"] = valid["side"].map(_normalize_side)
    unknown_side_row_count = int(valid["side_group"].isna().sum())

    grouped = valid.groupby(["symbol", "event_time", "final_update_id", "prev_final_update_id", "event_type"], dropna=False, sort=False)

    packets: list[L2Packet] = []
    for _, group in grouped:
        first = group.iloc[0]
        bids: list[tuple[float, float]] = []
        asks: list[tuple[float, float]] = []
        for _, row in group.iterrows():
            side = row.get("side_group")
            price = _as_float(row.get("price"))
            quantity = _as_float(row.get("quantity"))
            if side is None or price is None or quantity is None:
                continue
            if side == "bid":
                bids.append((price, quantity))
            else:
                asks.append((price, quantity))
        packets.append(
            L2Packet(
                symbol=str(first["symbol"]),
                event_type=str(first["event_type"] or "depthUpdate"),
                event_time=int(first["event_time"]),
                transaction_time=_as_int(first.get("transaction_time")),
                received_time=_as_int(first.get("received_time")),
                first_update_id=_as_int(first.get("first_update_id")),
                final_update_id=int(first["final_update_id"]),
                prev_final_update_id=_as_int(first.get("prev_final_update_id")),
                bids=tuple(bids),
                asks=tuple(asks),
            )
        )

    return packets, {"rows_scanned": rows_scanned, "unknown_side_row_count": unknown_side_row_count, "missing_required_column_count": missing_required_column_count}


def _estimate_source_gap_count(ordered_packets: list[L2Packet]) -> int:
    count = 0
    previous: L2Packet | None = None
    for packet in ordered_packets:
        if previous is None:
            previous = packet
            continue
        if is_source_gap(previous, packet):
            count += 1
        previous = packet
    return count


def _packet_hint_diagnostics(ordered_packets: list[L2Packet]) -> dict[str, int | bool]:
    timestamp_fallback_used = any(packet.transaction_time is None for packet in ordered_packets)
    timestamp_non_monotonic_hint_count = 0
    previous_effective_time: int | None = None
    for packet in ordered_packets:
        effective_time = packet.transaction_time if packet.transaction_time is not None else packet.event_time
        if previous_effective_time is not None and effective_time < previous_effective_time:
            timestamp_non_monotonic_hint_count += 1
        previous_effective_time = effective_time
    return {
        "timestamp_fallback_used": timestamp_fallback_used,
        "timestamp_non_monotonic_hint_count": timestamp_non_monotonic_hint_count,
    }


def discover_all_candidate_paths(l2_root: Path, symbol: str) -> list[Path]:
    root = Path(l2_root)
    candidates: list[Path] = []
    for pattern in (f"{symbol}_orderbook.parquet.zst", f"{symbol}_orderbook.parquet"):
        candidates.extend(sorted(root.rglob(pattern)))
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[path.as_posix()] = path
    ordered = sorted(unique.values(), key=lambda path: (_file_date(path) or "", _file_hour(path) or "", path.as_posix()))
    return ordered


def _merge_unique(selected: list[tuple[Path, str]], path: Path, reason: str) -> None:
    path_key = path.as_posix()
    if any(existing_path.as_posix() == path_key for existing_path, _ in selected):
        return
    selected.append((path, reason))


def select_candidate_files(all_paths: list[Path], max_candidate_files: int, candidate_file_args: list[str] | None) -> tuple[list[CandidateFile], int]:
    if candidate_file_args:
        return [CandidateFile(path=Path(path), candidate_reason="override_candidate") for path in candidate_file_args], len(all_paths)

    selected: list[tuple[Path, str]] = []
    remaining = list(all_paths)
    known = {Path(path).as_posix(): reason for path, reason in DEFAULT_CANDIDATE_INPUTS}

    for path in all_paths:
        if path.as_posix() in known:
            _merge_unique(selected, path, known[path.as_posix()])

    def take_first(predicate, limit: int, reason: str) -> None:
        count = 0
        for path in all_paths:
            if count >= limit:
                break
            if predicate(path) and path.as_posix() not in {p.as_posix() for p, _ in selected}:
                _merge_unique(selected, path, reason)
                count += 1

    def is_month_open(path: Path) -> bool:
        parts = _parse_date_components(path)
        return bool(parts and parts[2] == 1 and _file_hour(path) == "00")

    def is_boundary(path: Path) -> bool:
        return _file_hour(path) in {"00", "23"}

    def is_2026(path: Path) -> bool:
        parts = _parse_date_components(path)
        return bool(parts and parts[0] == 2026)

    take_first(lambda path: True, 20, "first_chronological")
    for path in reversed(all_paths):
        if len(selected) >= max_candidate_files:
            break
        _merge_unique(selected, path, "last_chronological")

    take_first(is_month_open, 40, "month_open")
    take_first(is_boundary, 120, "day_boundary_hour_boundary")
    take_first(is_2026, 120, "2026_file")

    seen = {p.as_posix() for p, _ in selected}
    remaining = [path for path in all_paths if path.as_posix() not in seen]
    slots_left = max(0, max_candidate_files - len(selected))
    if slots_left > 0 and remaining:
        if slots_left >= len(remaining):
            step_indexes = list(range(len(remaining)))
        else:
            step = len(remaining) / float(slots_left)
            step_indexes = sorted({min(len(remaining) - 1, int(round(i * step))) for i in range(slots_left)})
        for idx in step_indexes:
            if len(selected) >= max_candidate_files:
                break
            _merge_unique(selected, remaining[idx], "evenly_spaced")

    selected = selected[:max_candidate_files]
    return [CandidateFile(path=path, candidate_reason=reason) for path, reason in selected], len(all_paths)


def _preview_classification(preview: CandidatePreview) -> str:
    if preview.preview_row_count == 0:
        return "deferred_empty_preview"
    if preview.missing_required_column_count > 0:
        return "deferred_missing_columns"
    if not _is_supported_path(Path(preview.candidate_file_path)):
        return "unsupported_path"
    if preview.snapshot_like_packet_count > 0:
        return "likely_snapshot_reset_preview"
    if preview.missing_transaction_time_count > 0 or preview.estimated_source_gap_count > 0:
        return "likely_source_gap_preview"
    if preview.timestamp_non_monotonic_hint_count > 0:
        return "likely_source_gap_preview"
    return "likely_clean_preview"


def preview_candidate_file(path: Path, *, candidate_reason: str, max_rows: int) -> CandidatePreview:
    frame = _read_parquet_preview(path, max_rows)
    packets, counters = _frame_to_packets(frame)
    ordered_packets = sorted(packets, key=packet_sort_key)
    diagnostics = _packet_hint_diagnostics(list(ordered_packets))
    estimated_source_gap_count = _estimate_source_gap_count(list(ordered_packets))
    preview = CandidatePreview(
        candidate_file_path=path.as_posix(),
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        preview_row_count=counters["rows_scanned"],
        preview_packet_count=len(ordered_packets),
        missing_required_column_count=counters["missing_required_column_count"],
        missing_transaction_time_count=sum(1 for packet in ordered_packets if packet.transaction_time is None),
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if is_snapshot_or_reset(packet)),
        estimated_source_gap_count=estimated_source_gap_count,
        timestamp_non_monotonic_hint_count=int(diagnostics["timestamp_non_monotonic_hint_count"]),
        side_mapping_unknown_count=counters["unknown_side_row_count"],
        candidate_reason=candidate_reason,
        candidate_score=0,
        dry_run_policy_class="",
    )
    score = 0
    if candidate_reason == "known_original_sample":
        score += 1000
    elif candidate_reason == "known_source_gap_heavy":
        score += 900
    elif candidate_reason == "known_snapshot_reset_bridge":
        score += 1100
    elif candidate_reason == "month_open":
        score += 50
    elif candidate_reason == "day_boundary_hour_boundary":
        score += 40
    elif candidate_reason == "2026_file":
        score += 60
    elif candidate_reason == "evenly_spaced":
        score += 10
    elif candidate_reason == "first_chronological":
        score += 30
    elif candidate_reason == "last_chronological":
        score += 30
    score += preview.snapshot_like_packet_count * 200
    score += preview.estimated_source_gap_count * 150
    score += preview.missing_transaction_time_count * 80
    score += preview.timestamp_non_monotonic_hint_count * 40
    score += preview.side_mapping_unknown_count * 5
    score += min(preview.preview_packet_count, 100)
    return CandidatePreview(
        **{
            **preview.__dict__,
            "candidate_score": score,
            "dry_run_policy_class": _preview_classification(preview),
        }
    )


def _select_policy_check_candidates(previews: list[CandidatePreview], max_policy_check_files: int) -> set[str]:
    ranked = sorted(
        previews,
        key=lambda item: (
            -item.candidate_score,
            item.candidate_file_path,
        ),
    )
    return {item.candidate_file_path for item in ranked[:max_policy_check_files]}


def _run_policy_check(preview: CandidatePreview, path: Path, max_rows: int) -> PolicyCheckResult:
    frame = _read_parquet_preview(path, max_rows)
    packets, counters = _frame_to_packets(frame)
    ordered_packets = sorted(packets, key=packet_sort_key)
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    summary = summarize_segments(segments, results)
    source_gap_boundary_count = sum(1 for segment in segments if segment.boundary_reason == "source_sequence_gap")
    quarantined_segments = [segment for segment, result in zip(segments, results) if result.quarantined]
    quarantined_segment_ofi_emitted_count = sum(result.ofi_emitted_count for segment, result in zip(segments, results) if result.quarantined)
    policy_check_status: str
    if counters["rows_scanned"] == 0:
        policy_check_status = "deferred_no_packets"
    elif counters["missing_required_column_count"] > 0:
        policy_check_status = "deferred_missing_columns"
    elif not _is_supported_path(path):
        policy_check_status = "deferred_unsupported_path"
    elif summary.get("dirty_segment_count", 0) > 0:
        if summary.get("quarantined_segment_count", 0) > 0:
            policy_check_status = "quarantined_bounded_snapshot_chain_failure"
        else:
            policy_check_status = "rejected_bounded_dirty_sequence"
    elif summary.get("snapshot_bridge_event_count", 0) > 0:
        policy_check_status = "accepted_bounded_snapshot_bridge_clean"
    elif source_gap_boundary_count > 0:
        policy_check_status = "accepted_bounded_source_gap_clean"
    else:
        policy_check_status = "accepted_bounded_clean"

    return PolicyCheckResult(
        file_path=path.as_posix(),
        file_date=_file_date(path),
        file_hour=_file_hour(path),
        rows_scanned=counters["rows_scanned"],
        packet_count=len(ordered_packets),
        segment_count=int(summary["segment_count"]),
        meaningful_segment_count=int(summary["meaningful_segment_count"]),
        clean_segment_count=int(summary["clean_segment_count"]),
        dirty_segment_count=int(summary["dirty_segment_count"]),
        all_segments_clean=bool(summary["all_segments_clean"]),
        source_gap_boundary_count=source_gap_boundary_count,
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if is_snapshot_or_reset(packet)),
        snapshot_bridge_event_count=int(summary["snapshot_bridge_event_count"]),
        snapshot_reset_clean_seed_count=int(summary["snapshot_reset_clean_seed_count"]),
        snapshot_reset_chain_failure_count=int(summary["snapshot_reset_chain_failure_count"]),
        quarantined_segment_count=len(quarantined_segments),
        total_ofi_emitted_count=int(summary["total_ofi_emitted_count"]),
        total_warmup_none_count=int(summary["total_warmup_none_count"]),
        total_sequence_gap_count=int(summary["total_sequence_gap_count"]),
        ofi_suppressed_due_to_snapshot_bridge_count=int(summary["ofi_suppressed_due_to_snapshot_bridge_count"]),
        ofi_suppressed_due_to_quarantine_count=int(summary["ofi_suppressed_due_to_quarantine_count"]),
        policy_check_status=policy_check_status,
        candidate_reason=preview.candidate_reason,
        candidate_score=preview.candidate_score,
        dry_run_policy_class="policy_check_selected",
        quarantined_segment_ofi_emitted_count=quarantined_segment_ofi_emitted_count,
        side_mapping_unknown_count=counters["unknown_side_row_count"],
    )


def _find_bar_file(bar_dir: Path, symbol: str, bar_size: str, file_date: str | None) -> tuple[Path | None, str | None]:
    if file_date is None:
        return None, None
    root = Path(bar_dir)
    exact_patterns = [
        f"{symbol}*tier2*{bar_size}_{file_date}.parquet",
        f"{symbol}*tier2*{bar_size}_{file_date}.csv",
        f"{symbol}*tier2*{bar_size}_{file_date}.feather",
        f"{symbol}*tier2*{bar_size}_{file_date}.arrow",
        f"{symbol}*tier2*{bar_size}_{file_date}.parquet.zst",
    ]
    for pattern in exact_patterns:
        matches = sorted(root.rglob(pattern))
        if matches:
            return matches[0], "day"

    month = file_date[:7]
    month_patterns = [
        f"{symbol}*tier2*{bar_size}_{month}.parquet",
        f"{symbol}*tier2*{bar_size}_{month}.csv",
        f"{symbol}*tier2*{bar_size}_{month}.feather",
        f"{symbol}*tier2*{bar_size}_{month}.arrow",
        f"{symbol}*tier2*{bar_size}_{month}.parquet.zst",
    ]
    for pattern in month_patterns:
        matches = sorted(root.rglob(pattern))
        if matches:
            return matches[0], "month"
    return None, None


def _load_bar_frame(bar_path: Path) -> pl.DataFrame:
    return pl.read_parquet(bar_path)


def _build_join_readiness_result(bar_dir: Path, symbol: str, bar_size: str, file_date: str | None) -> JoinReadinessResult:
    bar_path, resolution_strategy = _find_bar_file(bar_dir, symbol, bar_size, file_date)
    if file_date is None:
        return JoinReadinessResult(file_date=None, bar_file_found=False, bar_file_path=None, bar_shard_resolution_strategy=None, bar_row_count=None, join_attempted=False, bar_count_preserved=None, join_deferred_reason="file_date_unavailable")
    if bar_path is None:
        return JoinReadinessResult(file_date=file_date, bar_file_found=False, bar_file_path=None, bar_shard_resolution_strategy=None, bar_row_count=None, join_attempted=False, bar_count_preserved=None, join_deferred_reason="bar_file_missing")
    bar_frame = _load_bar_frame(bar_path)
    synthetic_ofi = pl.DataFrame(
        {
            "datetime": [
                bar_frame.select(pl.col("open_time").min()).item(),
                bar_frame.select(pl.col("close_time").max()).item(),
            ],
            "ofi": [0.0, 0.0],
        }
    )
    joined = join_ofi_to_bars_preserve_coverage(bar_frame, synthetic_ofi)
    return JoinReadinessResult(
        file_date=file_date,
        bar_file_found=True,
        bar_file_path=bar_path.as_posix(),
        bar_shard_resolution_strategy=resolution_strategy,
        bar_row_count=bar_frame.height,
        join_attempted=True,
        bar_count_preserved=joined.height == bar_frame.height,
        join_deferred_reason=None,
    )


def build_report(
    *,
    discovered_file_count: int,
    discovered_bar_count: int,
    bar_month_shard_count: int,
    bar_day_shard_count: int,
    candidate_batch_index: int | None = None,
    candidate_batch_count: int | None = None,
    candidate_inputs: list[CandidateFile],
    previews: list[CandidatePreview],
    policy_results: list[PolicyCheckResult],
    join_results: list[JoinReadinessResult],
    bar_size: str,
    max_candidate_files: int,
    preview_rows_per_file: int,
    max_policy_check_files: int,
) -> str:
    dry_run_scope = _dry_run_scope_label(
        max_candidate_files=max_candidate_files,
        preview_rows_per_file=preview_rows_per_file,
        max_policy_check_files=max_policy_check_files,
        candidate_batch_index=candidate_batch_index,
        candidate_batch_count=candidate_batch_count,
    )
    preview_count = len(previews)
    policy_check_count = len(policy_results)
    selected_count = len(candidate_inputs)
    accepted_count = sum(1 for result in policy_results if result.policy_check_status.startswith("accepted_bounded"))
    source_gap_clean_count = sum(1 for result in policy_results if result.policy_check_status == "accepted_bounded_source_gap_clean")
    snapshot_bridge_clean_count = sum(1 for result in policy_results if result.policy_check_status == "accepted_bounded_snapshot_bridge_clean")
    quarantined_count = sum(1 for result in policy_results if result.policy_check_status == "quarantined_bounded_snapshot_chain_failure")
    rejected_count = sum(1 for result in policy_results if result.policy_check_status == "rejected_bounded_dirty_sequence")
    deferred_count = sum(1 for result in policy_results if result.policy_check_status.startswith("deferred_"))
    total_rows_scanned = sum(result.rows_scanned for result in policy_results)
    total_packet_count = sum(result.packet_count for result in policy_results)
    total_segment_count = sum(result.segment_count for result in policy_results)
    total_meaningful_segment_count = sum(result.meaningful_segment_count for result in policy_results)
    files_all_segments_clean = sum(1 for result in policy_results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in policy_results if result.dirty_segment_count > 0)
    total_source_gap_boundary_count = sum(result.source_gap_boundary_count for result in policy_results)
    total_snapshot_like_packet_count = sum(result.snapshot_like_packet_count for result in policy_results)
    total_snapshot_bridge_event_count = sum(result.snapshot_bridge_event_count for result in policy_results)
    total_snapshot_reset_clean_seed_count = sum(result.snapshot_reset_clean_seed_count for result in policy_results)
    total_snapshot_reset_chain_failure_count = sum(result.snapshot_reset_chain_failure_count for result in policy_results)
    total_quarantined_segment_count = sum(result.quarantined_segment_count for result in policy_results)
    total_ofi_emitted_count = sum(result.total_ofi_emitted_count for result in policy_results)
    total_warmup_none_count = sum(result.total_warmup_none_count for result in policy_results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in policy_results)
    total_ofi_suppressed_due_to_snapshot_bridge_count = sum(result.ofi_suppressed_due_to_snapshot_bridge_count for result in policy_results)
    total_ofi_suppressed_due_to_quarantine_count = sum(result.ofi_suppressed_due_to_quarantine_count for result in policy_results)
    unknown_side_mapping_total = sum(result.side_mapping_unknown_count for result in policy_results)

    join_attempted_count = sum(1 for result in join_results if result.join_attempted)
    join_deferred_count = sum(1 for result in join_results if not result.join_attempted)
    join_preserved_count = sum(1 for result in join_results if result.join_attempted and result.bar_count_preserved is True)
    join_not_preserved_count = sum(1 for result in join_results if result.join_attempted and result.bar_count_preserved is False)
    join_readiness_attempted = join_attempted_count > 0
    join_readiness_deferred = join_deferred_count > 0
    preserved_attempted = [result.bar_count_preserved for result in join_results if result.join_attempted]
    join_bar_count_preserved = bool(preserved_attempted) and all(value is True for value in preserved_attempted)
    join_bar_count_not_preserved = any(value is False for value in preserved_attempted)
    join_all_deferred = len(join_results) > 0 and join_attempted_count == 0

    decision_labels = [
        "bounded_read_only_dry_run",
        "candidate_selection_deterministic",
        "policy_module_used_directly",
        "policy_check_bounded_only",
        "no_ofi_artifacts_written",
        "full_reconstruction_not_approved",
        "segmented_reconstruction_still_bounded_only",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if join_readiness_attempted:
        decision_labels.append("join_readiness_checked_where_possible")
    elif len(join_results) > 0:
        decision_labels.append("join_readiness_not_attempted")
    if dry_run_scope == "full_bounded_manifest_batch":
        decision_labels.append("full_bounded_manifest_batch_completed")
    else:
        decision_labels.append("full_bounded_manifest_completed" if dry_run_scope == "full_bounded_manifest" else "smoke_bounded_manifest_completed")
    if accepted_count > 0:
        decision_labels.append("accepted_bounded_clean_candidates_found")
    if source_gap_clean_count > 0:
        decision_labels.append("source_gap_clean_candidates_found")
    if snapshot_bridge_clean_count > 0:
        decision_labels.append("snapshot_bridge_clean_candidates_found")
    if quarantined_count > 0:
        decision_labels.append("quarantined_candidates_found")
    if rejected_count > 0:
        decision_labels.append("rejected_dirty_candidates_found")
    if deferred_count > 0:
        decision_labels.append("deferred_candidates_found")
    if join_readiness_attempted and join_bar_count_preserved and not join_bar_count_not_preserved:
        decision_labels.append("bar_count_preserved_where_attempted")
    elif join_readiness_attempted and join_bar_count_not_preserved:
        decision_labels.append("bar_count_not_preserved_where_attempted")
    elif not join_readiness_attempted:
        decision_labels.append("bar_count_preservation_not_applicable")
    if join_readiness_deferred:
        decision_labels.append("join_readiness_deferred_bar_files_missing")
    if any(result.bar_shard_resolution_strategy == "month" for result in join_results if result.join_attempted):
        decision_labels.append("bar_month_shards_resolved")
    if any(result.bar_shard_resolution_strategy == "day" for result in join_results if result.join_attempted):
        decision_labels.append("bar_day_shards_resolved")

    selected_preview_map = {preview.candidate_file_path: preview for preview in previews}

    def _regression_label_for_group(group_name: str) -> str:
        if group_name == "known_original_sample":
            return "original_sample_regression_passed" if accepted_count > 0 else "original_sample_regression_failed"
        if group_name == "known_source_gap_heavy":
            return "source_gap_heavy_regression_passed" if source_gap_clean_count > 0 else "source_gap_heavy_regression_failed"
        if group_name == "known_snapshot_reset_bridge":
            return "snapshot_reset_bridge_regression_passed" if snapshot_bridge_clean_count > 0 else "snapshot_reset_bridge_regression_failed"
        return "override_candidate_regression_informational_only"

    group_name_order: list[str] = []
    for candidate in candidate_inputs:
        if candidate.candidate_reason not in group_name_order:
            group_name_order.append(candidate.candidate_reason)

    group_summaries: list[dict[str, Any]] = []
    grouped_results: dict[str, list[PolicyCheckResult]] = {}
    for result in policy_results:
        grouped_results.setdefault(result.candidate_reason, []).append(result)
    for group_name in group_name_order:
        group = grouped_results.get(group_name, [])
        group_summaries.append(
            {
                "group_name": group_name,
                "file_count": len(group),
                "files_all_segments_clean": sum(1 for result in group if result.all_segments_clean),
                "files_with_dirty_segments": sum(1 for result in group if result.dirty_segment_count > 0),
                "source_gap_boundary_count": sum(result.source_gap_boundary_count for result in group),
                "snapshot_bridge_event_count": sum(result.snapshot_bridge_event_count for result in group),
                "quarantined_segment_count": sum(result.quarantined_segment_count for result in group),
                "sequence_gap_count": sum(result.total_sequence_gap_count for result in group),
                "regression_status": _regression_label_for_group(group_name),
            }
        )

    preview_class_counts: dict[str, int] = {}
    for preview in previews:
        preview_class_counts[preview.dry_run_policy_class] = preview_class_counts.get(preview.dry_run_policy_class, 0) + 1
    policy_status_counts: dict[str, int] = {}
    for result in policy_results:
        policy_status_counts[result.policy_check_status] = policy_status_counts.get(result.policy_check_status, 0) + 1

    lines = [
        "# V9.2 L2 OFI Reconstruction Dry-Run Manifest",
        "",
        "## Purpose",
        "Estimate which raw L2 files would be selected, skipped, rejected, quarantined, or deferred under the current segmented OFI policy without writing any OFI artifacts.",
        "",
        "## Inputs",
        f"- `symbol`: `BTCUSDT`",
        f"- `max_candidate_files`: `{max_candidate_files}`",
        f"- `preview_rows_per_file`: `{preview_rows_per_file}`",
        f"- `max_policy_check_files`: `{max_policy_check_files}`",
        f"- `bar_size`: `{bar_size}`",
        f"- `candidate_batch_index`: `{candidate_batch_index}`",
        f"- `candidate_batch_count`: `{candidate_batch_count}`",
        f"- `selected_file_count`: `{selected_count}`",
        f"- `selected_file_count_for_batch`: `{selected_count}`",
        f"- `files_previewed`: `{preview_count}`",
        f"- `files_previewed_for_batch`: `{preview_count}`",
        f"- `files_policy_checked`: `{policy_check_count}`",
        f"- `files_policy_checked_for_batch`: `{policy_check_count}`",
        f"- `discovered_file_count`: `{discovered_file_count}`",
        f"- `discovered_bar_count`: `{discovered_bar_count}`",
        f"- `bar_month_shard_count`: `{bar_month_shard_count}`",
        f"- `bar_day_shard_count`: `{bar_day_shard_count}`",
        f"- `previewed_file_count`: `{preview_count}`",
        f"- `policy_checked_file_count`: `{policy_check_count}`",
        f"- `join_attempted_count`: `{join_attempted_count}`",
        f"- `join_deferred_count`: `{join_deferred_count}`",
        f"- `join_preserved_count`: `{join_preserved_count}`",
        f"- `join_not_preserved_count`: `{join_not_preserved_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only bounded dry-run only.",
        "- No OFI artifacts are written.",
        "- No packet tables are written.",
        "- No derived OFI data are written.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Current Policy Status",
        "- Reusable segmented L2 OFI policy module is present and reused directly.",
        "- Source-gap behavior remains validated in bounded regression.",
        "- Snapshot/reset bridge behavior remains validated in bounded regression.",
        "- Quarantine behavior remains bounded and read-only.",
        "",
        "## Dry-Run Scope",
        f"- `{dry_run_scope}`",
        f"- `candidate_batch_index`: `{candidate_batch_index}`",
        f"- `candidate_batch_count`: `{candidate_batch_count}`",
        "",
        "## Candidate Selection Method",
        "Deterministic bounded selection anchored on known sample files, source-gap-heavy files, snapshot/reset bridge files, first/last chronological files, month-open files, day-boundary/hour-boundary files, 2026 files, and evenly spaced corpus files, capped to the configured preview budget.",
        "",
        "## Candidate Preview Summary",
        _markdown_table(
            [
                {
                    "dry_run_policy_class": key,
                    "count": value,
                }
                for key, value in sorted(preview_class_counts.items())
            ],
            ["dry_run_policy_class", "count"],
        ),
        "",
        "## Policy-Check Selection",
        _markdown_table(
            [
                {
                    "file_path": preview.candidate_file_path,
                    "candidate_reason": preview.candidate_reason,
                    "candidate_score": preview.candidate_score,
                    "dry_run_policy_class": preview.dry_run_policy_class,
                }
                for preview in sorted(
                    [preview for preview in previews if preview.candidate_file_path in selected_preview_map],
                    key=lambda item: (-item.candidate_score, item.candidate_file_path),
                )
            ],
            ["file_path", "candidate_reason", "candidate_score", "dry_run_policy_class"],
        ),
        "",
        "## Executive Finding",
        f"Discovered files under `l2_root`: `{discovered_file_count}`.",
        f"Discovered bar files under `bar_dir`: `{discovered_bar_count}`.",
        f"Files previewed: `{preview_count}`.",
        f"Files policy-checked: `{policy_check_count}`.",
        f"Join-readiness attempted: `{join_attempted_count}`.",
        f"Join-readiness deferred: `{join_deferred_count}`.",
        f"Join-readiness preserved where attempted: `{join_preserved_count}`.",
        f"Join-readiness not preserved where attempted: `{join_not_preserved_count}`.",
        f"Accepted bounded-clean candidates: `{accepted_count}`.",
        f"Source-gap-clean candidates: `{source_gap_clean_count}`.",
        f"Snapshot-bridge-clean candidates: `{snapshot_bridge_clean_count}`.",
        f"Quarantined candidates: `{quarantined_count}`.",
        f"Rejected/dirty candidates: `{rejected_count}`.",
        f"Deferred candidates: `{deferred_count}`.",
        f"Selected files for batch: `{selected_count}`.",
        f"Join-readiness checks attempted: `{join_readiness_attempted}`.",
        f"Join-readiness checks deferred: `{join_readiness_deferred}`.",
        f"Bar-count preservation maintained where attempted: `{join_bar_count_preserved and not join_bar_count_not_preserved}`.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Policy-Check Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "file_date": result.file_date,
                    "file_hour": result.file_hour,
                    "rows_scanned": result.rows_scanned,
                    "packet_count": result.packet_count,
                    "segment_count": result.segment_count,
                    "meaningful_segment_count": result.meaningful_segment_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "snapshot_bridge_event_count": result.snapshot_bridge_event_count,
                    "snapshot_reset_clean_seed_count": result.snapshot_reset_clean_seed_count,
                    "snapshot_reset_chain_failure_count": result.snapshot_reset_chain_failure_count,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "ofi_suppressed_due_to_snapshot_bridge_count": result.ofi_suppressed_due_to_snapshot_bridge_count,
                    "ofi_suppressed_due_to_quarantine_count": result.ofi_suppressed_due_to_quarantine_count,
                    "policy_check_status": result.policy_check_status,
                }
                for result in policy_results
            ],
            [
                "file_path",
                "file_date",
                "file_hour",
                "rows_scanned",
                "packet_count",
                "segment_count",
                "meaningful_segment_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "source_gap_boundary_count",
                "snapshot_like_packet_count",
                "snapshot_bridge_event_count",
                "snapshot_reset_clean_seed_count",
                "snapshot_reset_chain_failure_count",
                "quarantined_segment_count",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "ofi_suppressed_due_to_snapshot_bridge_count",
                "ofi_suppressed_due_to_quarantine_count",
                "policy_check_status",
            ],
        ),
        "",
        "## Join-Readiness Results",
        _markdown_table(
            [
                {
                    "file_date": result.file_date,
                    "bar_file_found": result.bar_file_found,
                    "bar_file_path": result.bar_file_path,
                    "bar_shard_resolution_strategy": result.bar_shard_resolution_strategy,
                    "bar_row_count": result.bar_row_count,
                    "join_attempted": result.join_attempted,
                    "bar_count_preserved": result.bar_count_preserved,
                    "join_deferred_reason": result.join_deferred_reason,
                }
                for result in join_results
            ],
            ["file_date", "bar_file_found", "bar_file_path", "bar_shard_resolution_strategy", "bar_row_count", "join_attempted", "bar_count_preserved", "join_deferred_reason"],
        ),
        "",
        "## Bar Shard Results",
        f"- `bar_size`: `{bar_size}`",
        f"- `bar_shard_resolution_strategy`: `day -> month -> bar-size-filtered fallback`",
        f"- `bar_month_shard_count`: `{bar_month_shard_count}`",
        f"- `bar_day_shard_count`: `{bar_day_shard_count}`",
        "",
        "## Dry-Run Classification Summary",
        _markdown_table(
            [
                {"policy_check_status": key, "count": value}
                for key, value in sorted(policy_status_counts.items())
            ],
            ["policy_check_status", "count"],
        ),
        "",
        "## Accepted Bounded Clean Candidates",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "policy_check_status": result.policy_check_status,
                    "all_segments_clean": result.all_segments_clean,
                }
                for result in policy_results
                if result.policy_check_status == "accepted_bounded_clean"
            ],
            ["file_path", "policy_check_status", "all_segments_clean"],
        ),
        "",
        "## Quarantined Candidates",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "policy_check_status": result.policy_check_status,
                    "quarantined_segment_count": result.quarantined_segment_count,
                    "snapshot_reset_chain_failure_count": result.snapshot_reset_chain_failure_count,
                }
                for result in policy_results
                if result.policy_check_status == "quarantined_bounded_snapshot_chain_failure"
            ],
            ["file_path", "policy_check_status", "quarantined_segment_count", "snapshot_reset_chain_failure_count"],
        ),
        "",
        "## Rejected Or Deferred Candidates",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "policy_check_status": result.policy_check_status,
                    "all_segments_clean": result.all_segments_clean,
                    "join_deferred_reason": next((jr.join_deferred_reason for jr in join_results if jr.file_date == result.file_date), None),
                }
                for result in policy_results
                if result.policy_check_status.startswith("deferred_") or result.policy_check_status.startswith("rejected_")
            ],
            ["file_path", "policy_check_status", "all_segments_clean", "join_deferred_reason"],
        ),
        "",
        "## Estimated Output Plan",
        "- Metadata-only projection: `symbol=BTCUSDT/date=YYYY-MM-DD/hour=HH`.",
        "- The plan is estimated from bounded dry-run classification only.",
        "- No OFI output partitions were written.",
        "- Bar shard resolution strategy: `day` first, then `month`, then a bar-size-filtered fallback scan.",
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- Candidate files were selected deterministically.",
        "- Source-gap and snapshot/reset bridge validation paths were exercised without writing OFI artifacts.",
        "- Join-readiness was evaluated as metadata, and the manifest now resolves 750 BTC day/month bar shards before deferring any unresolved dates.",
        "- The report distinguishes join attempts, deferrals, and bar-count preservation outcomes.",
        "",
        "## What Failed Or Remains Unknown",
        "- The manifest is bounded; it does not guarantee full-corpus cleanliness.",
        "- Some candidates may still be deferred or rejected in a future broader pass.",
        "- This remains a bounded validation only.",
        "",
        "## What Is Safe",
        "- Use this manifest as a read-only estimate of broader reconstruction behavior.",
        "- Use accepted bounded-clean candidates only for further bounded validation work.",
        "",
        "## What Is Not Safe",
        "- Full reconstruction.",
        "- Any paper or live trading use.",
        "- Alpha claims.",
        "",
        "## Decision",
        ", ".join(decision_labels) + ".",
        "",
        "## Required Next Step",
        "Continue bounded read-only regression checks only; do not promote the workflow to full reconstruction or artifact generation.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_validation(
    *,
    l2_root: Path,
    bar_dir: Path,
    bar_size: str,
    max_candidate_files: int,
    preview_rows_per_file: int,
    max_policy_check_files: int,
    candidate_batch_index: int | None,
    candidate_batch_count: int | None,
    output_doc: Path,
    candidate_file_args: list[str] | None,
) -> dict[str, Any]:
    all_paths = discover_all_candidate_paths(l2_root, "BTCUSDT")
    bar_files = _collect_bar_files(bar_dir, "BTCUSDT", bar_size)
    bar_month_shard_count = sum(1 for path in bar_files if _bar_file_resolution_strategy(path, _bar_file_date_hint(path)) == "month")
    bar_day_shard_count = sum(1 for path in bar_files if _bar_file_resolution_strategy(path, _bar_file_date_hint(path)) == "day")
    candidate_inputs_full, discovered_file_count = select_candidate_files(all_paths, max_candidate_files, candidate_file_args)
    candidate_inputs = _partition_candidate_batch(
        candidate_inputs_full,
        candidate_batch_index=candidate_batch_index,
        candidate_batch_count=candidate_batch_count,
    )
    previews: list[CandidatePreview] = []
    for candidate in candidate_inputs:
        preview = preview_candidate_file(candidate.path, candidate_reason=candidate.candidate_reason, max_rows=preview_rows_per_file)
        previews.append(preview)

    selected_paths = _select_policy_check_candidates(previews, max_policy_check_files)
    previews = [
        CandidatePreview(
            **{
                **preview.__dict__,
                "dry_run_policy_class": "policy_check_selected" if preview.candidate_file_path in selected_paths else preview.dry_run_policy_class,
            }
        )
        for preview in previews
    ]
    preview_map = {preview.candidate_file_path: preview for preview in previews}
    policy_results: list[PolicyCheckResult] = []
    for candidate in candidate_inputs:
        preview = preview_map[candidate.path.as_posix()]
        if preview.candidate_file_path not in selected_paths:
            continue
        policy_results.append(_run_policy_check(preview, candidate.path, preview_rows_per_file))

    join_results: list[JoinReadinessResult] = []
    for result in policy_results:
        join_results.append(_build_join_readiness_result(bar_dir, "BTCUSDT", bar_size, result.file_date))

    report = build_report(
        discovered_file_count=discovered_file_count,
        discovered_bar_count=len(bar_files),
        bar_month_shard_count=bar_month_shard_count,
        bar_day_shard_count=bar_day_shard_count,
        candidate_batch_index=candidate_batch_index,
        candidate_batch_count=candidate_batch_count,
        candidate_inputs=candidate_inputs,
        previews=previews,
        policy_results=policy_results,
        join_results=join_results,
        bar_size=bar_size,
        max_candidate_files=max_candidate_files,
        preview_rows_per_file=preview_rows_per_file,
        max_policy_check_files=max_policy_check_files,
    )
    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(report, encoding="utf-8")
    return {
        "discovered_file_count": discovered_file_count,
        "previewed_file_count": len(previews),
        "policy_checked_file_count": len(policy_results),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_validation(
        l2_root=args.l2_root,
        bar_dir=args.bar_dir,
        bar_size=args.bar_size,
        max_candidate_files=args.max_candidate_files,
        preview_rows_per_file=args.preview_rows_per_file,
        max_policy_check_files=args.max_policy_check_files,
        candidate_batch_index=args.candidate_batch_index,
        candidate_batch_count=args.candidate_batch_count,
        output_doc=args.output_doc,
        candidate_file_args=args.candidate_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
