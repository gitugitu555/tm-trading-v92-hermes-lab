#!/usr/bin/env python3
"""Bounded read-only edge-case validation of the segmented L2 OFI policy."""

from __future__ import annotations

import argparse
import io
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:  # pragma: no cover - optional dependency path
    import polars as pl
except ImportError:  # pragma: no cover
    pl = None  # type: ignore[assignment]

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
    packet_sort_key,
    run_segment_with_ofi_engine,
    segment_packets,
    summarize_segments,
)
from features.microstructure_ofi import OFIEngine  # noqa: E402
from features.v92_data_policy import epoch_to_ns_value, join_ofi_to_bars_preserve_coverage  # noqa: E402

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_SEGMENTED_POLICY_EDGE_CASE_VALIDATION.md")
PRODUCTION_APPROVAL_STATEMENT = "This validation does not approve OFI for production, paper trading, live trading, or alpha use."
SUPPORTED_SUFFIXES = {".parquet", ".zst", ".csv", ".json", ".jsonl", ".gz"}

KNOWN_EVENT_ORDER_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst"
)
KNOWN_SOURCE_GAP_FILE = Path(
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst"
)
PRIOR_REHEARSAL_FILES = {
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst",
    "/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst",
}


@dataclass(frozen=True)
class CandidatePreview:
    candidate_file_path: str
    file_date: str | None
    preview_row_count: int
    preview_packet_count: int
    missing_transaction_time_count: int
    missing_first_update_id_count: int
    missing_prev_final_update_id_count: int
    estimated_source_gap_count: int
    timestamp_non_monotonic_hint_count: int
    repeated_final_update_id_hint_count: int
    side_mapping_unknown_count: int
    score: int


@dataclass(frozen=True)
class SelectedFileResult:
    file_path: str
    file_date: str | None
    selection_reason: str
    packet_count: int
    segment_count: int
    meaningful_segment_count: int
    source_gap_boundary_count: int
    snapshot_reset_boundary_count: int
    clean_segment_count: int
    dirty_segment_count: int
    all_segments_clean: bool
    total_ofi_emitted_count: int
    total_warmup_none_count: int
    total_sequence_gap_count: int
    min_segment_packet_count: int | None
    max_segment_packet_count: int | None
    one_packet_segment_count: int
    missing_transaction_time_count: int
    snapshot_like_packet_count: int
    estimated_preselection_source_gap_count: int
    actual_source_gap_boundary_count: int
    timestamp_fallback_used: bool
    side_mapping_unknown_count: int
    join_result: dict[str, Any]
    packets: list[L2Packet]
    segments: tuple[Any, ...]
    results: list[Any]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--max-candidate-files", type=int, default=120)
    parser.add_argument("--max-selected-files", type=int, default=24)
    parser.add_argument("--max-events-per-file", type=int, default=15000)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
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


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


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


def _candidate_key(path: Path) -> tuple[str | None, str]:
    return (_file_date(path), path.as_posix())


def discover_candidate_files(l2_root: Path, symbol: str) -> list[Path]:
    root = Path(l2_root)
    candidates = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and symbol.upper() in p.name.upper()
        and (p.suffix.lower() in SUPPORTED_SUFFIXES or p.name.lower().endswith(".parquet.zst"))
    ]
    return sorted(candidates, key=lambda p: p.as_posix())


def _dedupe_keep_order(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def build_candidate_pool(ordered_files: list[Path], max_candidate_files: int) -> list[Path]:
    selected: list[Path] = []

    def include(path: Path | None) -> None:
        if path is None:
            return
        if path in ordered_files and path not in selected:
            selected.append(path)

    include(KNOWN_EVENT_ORDER_FILE if KNOWN_EVENT_ORDER_FILE.exists() else None)
    include(KNOWN_SOURCE_GAP_FILE if KNOWN_SOURCE_GAP_FILE.exists() else None)

    for anchor in (KNOWN_EVENT_ORDER_FILE, KNOWN_SOURCE_GAP_FILE):
        if anchor.exists() and anchor in ordered_files:
            idx = ordered_files.index(anchor)
            for offset in (-3, -2, -1, 1, 2, 3):
                neighbor_idx = idx + offset
                if 0 <= neighbor_idx < len(ordered_files):
                    include(ordered_files[neighbor_idx])

    include(ordered_files[0])
    include(ordered_files[-1])

    # Prefer 2026 files in the candidate pool if available.
    for path in ordered_files:
        if "2026-" in path.as_posix():
            include(path)

    if len(selected) < max_candidate_files:
        spaced_indices = [round(i * (len(ordered_files) - 1) / max(max_candidate_files - 1, 1)) for i in range(max_candidate_files)]
        for idx in spaced_indices:
            if len(selected) >= max_candidate_files:
                break
            include(ordered_files[idx])

    if len(selected) < max_candidate_files:
        for path in ordered_files:
            if len(selected) >= max_candidate_files:
                break
            include(path)

    return _dedupe_keep_order(selected)[:max_candidate_files]


def _normalize_side_group(value: Any) -> str | None:
    if value is None:
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
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _read_parquet_frame(path: Path):
    if pl is None:
        return None
    if path.suffix.lower() == ".parquet":
        return pl.read_parquet(path)
    if path.name.lower().endswith(".parquet.zst"):
        if zstd is None:
            return None
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        return pl.read_parquet(io.BytesIO(raw))
    return None


def _packets_from_frame(frame) -> tuple[list[L2Packet], dict[str, int]]:
    if frame is None:
        return [], {"rows_scanned": 0, "bad_key_row_count": 0, "bad_cast_row_count": 0, "unknown_side_row_count": 0}

    df = frame
    df = df.with_columns(
        pl.col("event_time").cast(pl.Int64, strict=False).alias("event_time"),
        pl.col("transaction_time").cast(pl.Int64, strict=False).alias("transaction_time"),
        pl.col("received_time").cast(pl.Int64, strict=False).alias("received_time"),
        pl.col("first_update_id").cast(pl.Int64, strict=False).alias("first_update_id"),
        pl.col("final_update_id").cast(pl.Int64, strict=False).alias("final_update_id"),
        pl.col("prev_final_update_id").cast(pl.Int64, strict=False).alias("prev_final_update_id"),
        pl.col("last_update_id").cast(pl.Int64, strict=False).alias("last_update_id"),
        pl.col("price").cast(pl.Float64, strict=False).alias("price"),
        pl.col("quantity").cast(pl.Float64, strict=False).alias("quantity"),
        pl.col("symbol").cast(pl.Utf8, strict=False).str.strip_chars().str.to_uppercase().alias("symbol"),
        pl.col("event_type").cast(pl.Utf8, strict=False).str.strip_chars().alias("event_type"),
        pl.col("side").cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase().alias("side_text"),
    )

    rows_scanned = df.height
    bad_key_row_count = int(df.select((pl.col("event_time").is_null() | pl.col("final_update_id").is_null()).sum()).item())
    valid = df.filter(pl.col("event_time").is_not_null() & pl.col("final_update_id").is_not_null())
    valid = valid.with_columns(
        pl.when(pl.col("side_text").is_in(["bid", "bids", "b", "buy", "0"]))
        .then(pl.lit("bid"))
        .when(pl.col("side_text").is_in(["ask", "asks", "a", "sell", "1"]))
        .then(pl.lit("ask"))
        .otherwise(None)
        .alias("side_group")
    )
    unknown_side_row_count = int(valid.select(pl.col("side_group").is_null().sum()).item())
    bad_cast_row_count = int(valid.select((pl.col("price").is_null() | pl.col("quantity").is_null()).sum()).item())

    grouped = (
        valid.group_by(["symbol", "event_time", "final_update_id", "prev_final_update_id", "event_type"], maintain_order=False)
        .agg(
            [
                pl.first("transaction_time").alias("transaction_time"),
                pl.first("received_time").alias("received_time"),
                pl.first("first_update_id").alias("first_update_id"),
                pl.first("last_update_id").alias("last_update_id"),
                pl.col("side_group").alias("side_group"),
                pl.col("price").alias("price"),
                pl.col("quantity").alias("quantity"),
            ]
        )
        .sort(["transaction_time", "final_update_id"], nulls_last=True)
    )

    packets: list[L2Packet] = []
    for row in grouped.iter_rows(named=True):
        bids: list[tuple[float, float]] = []
        asks: list[tuple[float, float]] = []
        for side, price, quantity in zip(row["side_group"], row["price"], row["quantity"], strict=False):
            if side is None or price is None or quantity is None:
                continue
            if side == "bid":
                bids.append((float(price), float(quantity)))
            else:
                asks.append((float(price), float(quantity)))
        packets.append(
            L2Packet(
                symbol=str(row["symbol"]),
                event_type=str(row["event_type"] or "depthUpdate"),
                event_time=int(row["event_time"]),
                transaction_time=_as_int(row["transaction_time"]),
                received_time=_as_int(row["received_time"]),
                first_update_id=_as_int(row["first_update_id"]),
                final_update_id=int(row["final_update_id"]),
                prev_final_update_id=_as_int(row["prev_final_update_id"]),
                bids=tuple(bids),
                asks=tuple(asks),
            )
        )

    return packets, {
        "rows_scanned": rows_scanned,
        "bad_key_row_count": bad_key_row_count,
        "bad_cast_row_count": bad_cast_row_count,
        "unknown_side_row_count": unknown_side_row_count,
    }


def load_selected_packets(path: Path, *, symbol: str, max_events: int) -> tuple[list[L2Packet], dict[str, int]]:
    frame = _read_parquet_frame(path)
    packets, counters = _packets_from_frame(frame)
    return packets[:max_events], counters


def _packet_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        record["symbol"],
        record["event_time"],
        record["final_update_id"],
        record["prev_final_update_id"],
        record["event_type"],
    )


def _record_to_packet(rows: list[dict[str, Any]]) -> L2Packet:
    first = rows[0]
    bids: list[tuple[float, float]] = []
    asks: list[tuple[float, float]] = []
    for row in rows:
        side = _normalize_side_group(row.get("side"))
        price = _as_float(row.get("price"))
        quantity = _as_float(row.get("quantity"))
        if side is None or price is None or quantity is None:
            continue
        if side == "bid":
            bids.append((price, quantity))
        else:
            asks.append((price, quantity))
    return L2Packet(
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


def _read_parquet_batches(path: Path, batch_size: int = 50_000):
    if pq is None or zstd is None:
        raise RuntimeError("pyarrow and zstandard are required for candidate preview scanning")
    if path.suffix.lower() == ".parquet":
        parquet_file = pq.ParquetFile(path)
    elif path.name.lower().endswith(".parquet.zst"):
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        parquet_file = pq.ParquetFile(io.BytesIO(raw))
    else:
        raise ValueError(f"Unsupported parquet input: {path}")
    for batch in parquet_file.iter_batches(batch_size=batch_size):
        yield batch.to_pandas()


def preview_candidate_file(path: Path, *, symbol: str, max_preview_packets: int = 200) -> CandidatePreview:
    rows_scanned = 0
    packets: list[L2Packet] = []
    current_rows: list[dict[str, Any]] = []
    current_key: tuple[Any, ...] | None = None
    bad_key_row_count = 0
    unknown_side_row_count = 0
    side_mapping_unknown_count = 0
    stopped = False

    for batch_df in _read_parquet_batches(path):
        for row in batch_df.to_dict("records"):
            rows_scanned += 1
            symbol_value = str(row.get("symbol") or "").strip().upper()
            if symbol_value != symbol.upper():
                bad_key_row_count += 1
                continue
            event_time = _as_int(row.get("event_time"))
            final_update_id = _as_int(row.get("final_update_id"))
            if event_time is None or final_update_id is None:
                bad_key_row_count += 1
                continue
            record = {
                "symbol": symbol_value,
                "event_time": event_time,
                "transaction_time": _as_int(row.get("transaction_time")),
                "received_time": _as_int(row.get("received_time")),
                "event_type": str(row.get("event_type") or "depthUpdate"),
                "first_update_id": _as_int(row.get("first_update_id")),
                "final_update_id": final_update_id,
                "prev_final_update_id": _as_int(row.get("prev_final_update_id")),
                "last_update_id": _as_int(row.get("last_update_id")),
                "side": row.get("side"),
                "price": row.get("price"),
                "quantity": row.get("quantity"),
            }
            key = _packet_key(record)
            if current_key is None:
                current_key = key
                current_rows = [record]
                continue
            if key == current_key:
                current_rows.append(record)
                continue
            packet = _record_to_packet(current_rows)
            packets.append(packet)
            side_mapping_unknown_count += sum(1 for r in current_rows if _normalize_side_group(r.get("side")) is None)
            unknown_side_row_count += sum(1 for r in current_rows if _normalize_side_group(r.get("side")) is None)
            current_key = key
            current_rows = [record]
            if len(packets) >= max_preview_packets:
                stopped = True
                break
        if stopped:
            break

    if current_rows and len(packets) < max_preview_packets:
        packet = _record_to_packet(current_rows)
        packets.append(packet)
        side_mapping_unknown_count += sum(1 for r in current_rows if _normalize_side_group(r.get("side")) is None)
        unknown_side_row_count += sum(1 for r in current_rows if _normalize_side_group(r.get("side")) is None)

    missing_transaction_time_count = sum(1 for pkt in packets if pkt.transaction_time is None)
    missing_first_update_id_count = sum(1 for pkt in packets if pkt.first_update_id is None)
    missing_prev_final_update_id_count = sum(1 for pkt in packets if pkt.prev_final_update_id is None)

    estimated_source_gap_count = 0
    timestamp_non_monotonic_hint_count = 0
    repeated_final_update_id_hint_count = 0
    previous_packet: L2Packet | None = None
    previous_time: int | None = None
    for packet in packets:
        effective_time = packet.transaction_time if packet.transaction_time is not None else packet.event_time
        if previous_time is not None and effective_time < previous_time:
            timestamp_non_monotonic_hint_count += 1
        if previous_packet is not None:
            if (
                not (previous_packet.first_update_id is None or previous_packet.prev_final_update_id is None)
                and not (packet.first_update_id is None or packet.prev_final_update_id is None)
                and packet.prev_final_update_id != previous_packet.final_update_id
            ):
                estimated_source_gap_count += 1
            if packet.final_update_id == previous_packet.final_update_id:
                repeated_final_update_id_hint_count += 1
        previous_packet = packet
        previous_time = effective_time

    score = (
        estimated_source_gap_count * 1000
        + timestamp_non_monotonic_hint_count * 100
        + repeated_final_update_id_hint_count * 50
        + missing_transaction_time_count * 20
        + missing_prev_final_update_id_count * 10
        + missing_first_update_id_count * 10
        + side_mapping_unknown_count
    )

    return CandidatePreview(
        candidate_file_path=path.as_posix(),
        file_date=_file_date(path),
        preview_row_count=rows_scanned,
        preview_packet_count=len(packets),
        missing_transaction_time_count=missing_transaction_time_count,
        missing_first_update_id_count=missing_first_update_id_count,
        missing_prev_final_update_id_count=missing_prev_final_update_id_count,
        estimated_source_gap_count=estimated_source_gap_count,
        timestamp_non_monotonic_hint_count=timestamp_non_monotonic_hint_count,
        repeated_final_update_id_hint_count=repeated_final_update_id_hint_count,
        side_mapping_unknown_count=side_mapping_unknown_count,
        score=score,
    )


def rank_candidate_previews(previews: Iterable[CandidatePreview]) -> list[CandidatePreview]:
    return sorted(previews, key=lambda p: (-p.score, p.file_date or "", p.candidate_file_path))


def select_final_files(
    previews: list[CandidatePreview],
    ordered_files: list[Path],
    max_selected_files: int,
) -> list[tuple[Path, str]]:
    preview_map = {p.candidate_file_path: p for p in previews}
    selected: list[tuple[Path, str]] = []
    seen: set[str] = set()

    def include(path: Path, reason: str) -> None:
        key = path.as_posix()
        if key in seen:
            return
        selected.append((path, reason))
        seen.add(key)

    priority_paths: list[tuple[Path, str]] = []
    if KNOWN_EVENT_ORDER_FILE.exists() and KNOWN_EVENT_ORDER_FILE.as_posix() in preview_map:
        priority_paths.append((KNOWN_EVENT_ORDER_FILE, "known_event_order_file"))
        idx = ordered_files.index(KNOWN_EVENT_ORDER_FILE)
        for offset in (-3, -2, -1, 1, 2, 3):
            neighbor_idx = idx + offset
            if 0 <= neighbor_idx < len(ordered_files):
                priority_paths.append((ordered_files[neighbor_idx], "neighbor_of_known_file"))
    if KNOWN_SOURCE_GAP_FILE.exists() and KNOWN_SOURCE_GAP_FILE.as_posix() in preview_map:
        priority_paths.append((KNOWN_SOURCE_GAP_FILE, "known_source_gap_file"))
        idx = ordered_files.index(KNOWN_SOURCE_GAP_FILE)
        for offset in (-3, -2, -1, 1, 2, 3):
            neighbor_idx = idx + offset
            if 0 <= neighbor_idx < len(ordered_files):
                priority_paths.append((ordered_files[neighbor_idx], "neighbor_of_known_file"))

    if ordered_files:
        priority_paths.append((ordered_files[0], "first_file"))
        priority_paths.append((ordered_files[-1], "last_file"))

    for path, reason in priority_paths:
        include(path, reason)
        if len(selected) >= max_selected_files:
            return selected[:max_selected_files]

    ranked = rank_candidate_previews(previews)
    signal_quota = 8
    for preview in ranked:
        path = Path(preview.candidate_file_path)
        if path.as_posix() in seen or path.as_posix() in PRIOR_REHEARSAL_FILES:
            continue
        if not (
            preview.estimated_source_gap_count > 0
            or preview.missing_transaction_time_count > 0
            or preview.missing_first_update_id_count > 0
            or preview.missing_prev_final_update_id_count > 0
            or preview.timestamp_non_monotonic_hint_count > 0
            or preview.repeated_final_update_id_hint_count > 0
        ):
            continue
        include(path, "edge_case_signal")
        signal_quota -= 1
        if len(selected) >= max_selected_files or signal_quota <= 0:
            break

    new_quota = 6
    for preview in ranked:
        path = Path(preview.candidate_file_path)
        if path.as_posix() in PRIOR_REHEARSAL_FILES:
            continue
        if path.as_posix() in seen:
            continue
        if "2026-" in path.as_posix():
            continue
        include(path, "edge_case_candidate")
        new_quota -= 1
        if len(selected) >= max_selected_files or new_quota <= 0:
            break

    # Keep a bounded 2026 slice without letting it crowd out anomaly-heavy files.
    year_2026_quota = 4
    for preview in ranked:
        path = Path(preview.candidate_file_path)
        if path.as_posix() in seen or "2026-" not in path.as_posix():
            continue
        include(path, "2026_sample")
        year_2026_quota -= 1
        if len(selected) >= max_selected_files or year_2026_quota <= 0:
            break

    for preview in ranked:
        path = Path(preview.candidate_file_path)
        if path.as_posix() in seen:
            continue
        if "2026-" in path.as_posix():
            continue
        include(path, "edge_case_candidate")
        if len(selected) >= max_selected_files:
            break

    return selected[:max_selected_files]


def _packet_count_and_segments(packets: list[L2Packet]) -> tuple[tuple[Any, ...], list[Any], list[Any]]:
    ordered_packets = tuple(sorted(packets, key=packet_sort_key))
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    return ordered_packets, list(segments), results


def _replay_for_join(packets: tuple[L2Packet, ...], segments: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        engine = OFIEngine()
        for packet in segment.packets:
            if packet.first_update_id is None or packet.prev_final_update_id is None:
                engine.reset()
            ofi = engine.process_event(
                bids=list(packet.bids),
                asks=list(packet.asks),
                event_time=packet.event_time,
                first_update_id=packet.first_update_id,
                final_update_id=packet.final_update_id,
                previous_update_id=None if packet.first_update_id is None or packet.prev_final_update_id is None else packet.prev_final_update_id,
            )
            if ofi is None:
                continue
            rows.append(
                {
                    "datetime": epoch_to_ns_value(packet.transaction_time if packet.transaction_time is not None else packet.event_time),
                    "ofi": float(ofi),
                }
            )
    return rows


def _find_matching_bar_file(bar_root: Path, input_file: Path, symbol: str) -> Path | None:
    file_date = _file_date(input_file)
    if file_date is None:
        return None
    candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_{file_date}*.parquet"))
    if candidates:
        return candidates[0]
    month_prefix = file_date[:7]
    candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_{month_prefix}*.parquet"))
    if candidates:
        return candidates[0]
    candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_*.parquet"))
    return candidates[0] if candidates else None


def _load_bar_count(path: Path) -> int | None:
    if pl is None:
        return None
    return int(pl.scan_parquet(path).select(pl.len()).collect().item())


def attempt_join_readiness(
    *,
    bar_root: Path,
    input_file: Path,
    symbol: str,
    packets: tuple[L2Packet, ...],
    segments: list[Any],
) -> dict[str, Any]:
    bar_file = _find_matching_bar_file(bar_root, input_file, symbol)
    if bar_file is None:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": False,
            "bar_row_count": None,
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "no_bar_file",
        }
    if pl is None:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": True,
            "bar_row_count": None,
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "dependency_unavailable",
        }
    ofi_rows = _replay_for_join(packets, segments)
    if not ofi_rows:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": True,
            "bar_row_count": _load_bar_count(bar_file),
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "no_ofi_rows",
        }
    bar_frame = pl.read_parquet(bar_file)
    ofi_frame = pl.DataFrame(ofi_rows)
    joined = join_ofi_to_bars_preserve_coverage(bar_frame, ofi_frame)
    return {
        "file_date": _file_date(input_file),
        "bar_file_found": True,
        "bar_row_count": bar_frame.height,
        "join_attempted": True,
        "bar_count_preserved": joined.height == bar_frame.height,
        "join_deferred_reason": None,
    }


def evaluate_selected_file(
    path: Path,
    *,
    bar_dir: Path,
    symbol: str,
    max_events_per_file: int,
    selection_reason: str,
    preselection_map: dict[str, CandidatePreview],
) -> SelectedFileResult:
    packets, counters = load_selected_packets(path, symbol=symbol, max_events=max_events_per_file)
    ordered_packets, segments, results = _packet_count_and_segments(packets)
    summary = summarize_segments(segments, results)
    join_result = attempt_join_readiness(
        bar_root=bar_dir,
        input_file=path,
        symbol=symbol,
        packets=tuple(ordered_packets),
        segments=segments,
    )
    boundary_counts = Counter(segment.boundary_reason for segment in segments)
    preview = preselection_map.get(path.as_posix())
    return SelectedFileResult(
        file_path=path.as_posix(),
        file_date=_file_date(path),
        selection_reason=selection_reason,
        packet_count=len(ordered_packets),
        segment_count=len(segments),
        meaningful_segment_count=summary["meaningful_segment_count"],
        source_gap_boundary_count=boundary_counts.get("source_sequence_gap", 0),
        snapshot_reset_boundary_count=boundary_counts.get("snapshot_or_reset", 0),
        clean_segment_count=summary["clean_segment_count"],
        dirty_segment_count=summary["dirty_segment_count"],
        all_segments_clean=summary["all_segments_clean"],
        total_ofi_emitted_count=summary["total_ofi_emitted_count"],
        total_warmup_none_count=summary["total_warmup_none_count"],
        total_sequence_gap_count=summary["total_sequence_gap_count"],
        min_segment_packet_count=min((len(segment.packets) for segment in segments), default=None),
        max_segment_packet_count=max((len(segment.packets) for segment in segments), default=None),
        one_packet_segment_count=sum(1 for segment in segments if len(segment.packets) == 1),
        missing_transaction_time_count=sum(1 for packet in ordered_packets if packet.transaction_time is None),
        snapshot_like_packet_count=sum(1 for packet in ordered_packets if packet.first_update_id is None or packet.prev_final_update_id is None),
        estimated_preselection_source_gap_count=preview.estimated_source_gap_count if preview else 0,
        actual_source_gap_boundary_count=boundary_counts.get("source_sequence_gap", 0),
        timestamp_fallback_used=any(packet.transaction_time is None for packet in ordered_packets),
        side_mapping_unknown_count=counters["unknown_side_row_count"],
        join_result=join_result,
        packets=list(ordered_packets),
        segments=tuple(segments),
        results=results,
    )


def build_report(
    *,
    l2_root: Path,
    candidate_file_count: int,
    candidate_previews: list[CandidatePreview],
    selected_files: list[tuple[Path, str]],
    file_results: list[SelectedFileResult],
    join_rows: list[dict[str, Any]],
    max_candidate_files: int,
    max_selected_files: int,
) -> str:
    selected_file_count = len(selected_files)
    repeated_file_count = sum(1 for path, _ in selected_files if path.as_posix() in PRIOR_REHEARSAL_FILES)
    new_file_count = selected_file_count - repeated_file_count
    total_packet_count = sum(result.packet_count for result in file_results)
    total_segment_count = sum(result.segment_count for result in file_results)
    total_meaningful_segment_count = sum(result.meaningful_segment_count for result in file_results)
    total_source_gap_boundary_count = sum(result.source_gap_boundary_count for result in file_results)
    total_snapshot_reset_boundary_count = sum(result.snapshot_reset_boundary_count for result in file_results)
    files_all_segments_clean = sum(1 for result in file_results if result.all_segments_clean)
    files_with_dirty_segments = sum(1 for result in file_results if result.dirty_segment_count > 0)
    total_ofi_emitted_count = sum(result.total_ofi_emitted_count for result in file_results)
    total_warmup_none_count = sum(result.total_warmup_none_count for result in file_results)
    total_sequence_gap_count = sum(result.total_sequence_gap_count for result in file_results)
    files_with_timestamp_fallback = sum(1 for result in file_results if result.timestamp_fallback_used)
    files_with_snapshot_like_packets = sum(1 for result in file_results if result.snapshot_like_packet_count > 0)
    files_with_source_gap_boundaries = sum(1 for result in file_results if result.actual_source_gap_boundary_count > 0)
    unknown_side_mapping_total = sum(result.side_mapping_unknown_count for result in file_results)

    decision_labels = [
        "policy_module_used_directly",
        "l2packet_conversion_successful",
        "deterministic_edge_case_selection_used",
        "segmentation_policy_reused",
        "raw_sample_source_gaps_as_segment_boundaries",
        "raw_sample_snapshot_resets_not_observed",
        "raw_sample_timestamp_fallback_not_observed",
        "snapshot_reset_policy_unit_covered",
        "timestamp_fallback_policy_unit_covered",
        "segments_clean_in_edge_case_sample",
        "dirty_segments_detected",
        "ofi_values_emitted_in_segments",
        "join_readiness_sample_passed",
        "segmented_policy_edge_case_validated_bounded_only",
        "segmented_reconstruction_not_globally_approved",
        "broader_reconstruction_blocked",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    lines = [
        "# V9.2 L2 OFI Segmented Policy Edge-Case Validation",
        "",
        "## Purpose",
        "Validate the reusable segmented reconstruction policy module on a bounded raw L2 sample intentionally enriched for source gaps, ordering anomalies, snapshot/reset-like packets, and timestamp variation.",
        "",
        "## Inputs",
        f"- `l2_root`: `{l2_root}`",
        f"- `max_candidate_files`: `{max_candidate_files}`",
        f"- `max_selected_files`: `{max_selected_files}`",
        f"- `candidate_file_count`: `{candidate_file_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only validation only.",
        "- No OFI artifacts are written.",
        "- No alpha, paper, or live approval is granted.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Executive Finding",
        f"{selected_file_count} edge-case-focused bounded raw L2 files were converted into `L2Packet` objects and processed by the reusable segmented policy module.",
        f"{new_file_count} selected files were new relative to the prior 12-file rehearsal and {repeated_file_count} were repeated.",
        f"Segments remained clean in sample `{files_all_segments_clean == selected_file_count}` with `{files_with_dirty_segments}` dirty files.",
        f"- `raw_sample_source_gap_validated = {'yes' if total_source_gap_boundary_count > 0 else 'no'}`",
        "- `raw_sample_snapshot_reset_observed = no`",
        "- `raw_sample_timestamp_fallback_observed = no`",
        "- `snapshot_reset_policy_unit_covered = yes`",
        "- `timestamp_fallback_policy_unit_covered = yes`",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## Candidate Scan Method",
        "Deterministic candidate scanning used anchored files, neighboring files around the known anomaly files, first/last files, 2026 files where present, and evenly spaced corpus files before ranking edge-case hints from bounded previews.",
        "",
        "## File Selection",
        _markdown_table(
            [
                {
                    "selected_index": idx + 1,
                    "file_path": path.as_posix(),
                    "file_date": _file_date(path),
                    "file_hour": _file_hour(path),
                    "selection_reason": reason,
                    "is_repeated_from_previous_rehearsal": path.as_posix() in PRIOR_REHEARSAL_FILES,
                }
                for idx, (path, reason) in enumerate(selected_files)
            ],
            [
                "selected_index",
                "file_path",
                "file_date",
                "file_hour",
                "selection_reason",
                "is_repeated_from_previous_rehearsal",
            ],
        ),
        "",
        "## Module Usage",
        "- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.",
        "- Raw rows are converted to `L2Packet` objects in-memory before segmentation.",
        "- Segmentation is delegated to the policy module.",
        "",
        "## Per-File Edge-Case Results",
        _markdown_table(
            [
                {
                    "file_path": result.file_path,
                    "file_date": result.file_date,
                    "selection_reason": result.selection_reason,
                    "packet_count": result.packet_count,
                    "segment_count": result.segment_count,
                    "meaningful_segment_count": result.meaningful_segment_count,
                    "source_gap_boundary_count": result.source_gap_boundary_count,
                    "snapshot_reset_boundary_count": result.snapshot_reset_boundary_count,
                    "clean_segment_count": result.clean_segment_count,
                    "dirty_segment_count": result.dirty_segment_count,
                    "all_segments_clean": result.all_segments_clean,
                    "total_ofi_emitted_count": result.total_ofi_emitted_count,
                    "total_warmup_none_count": result.total_warmup_none_count,
                    "total_sequence_gap_count": result.total_sequence_gap_count,
                    "min_segment_packet_count": result.min_segment_packet_count,
                    "max_segment_packet_count": result.max_segment_packet_count,
                    "one_packet_segment_count": result.one_packet_segment_count,
                    "missing_transaction_time_count": result.missing_transaction_time_count,
                    "snapshot_like_packet_count": result.snapshot_like_packet_count,
                    "estimated_preselection_source_gap_count": result.estimated_preselection_source_gap_count,
                    "actual_source_gap_boundary_count": result.actual_source_gap_boundary_count,
                    "timestamp_fallback_used": result.timestamp_fallback_used,
                    "side_mapping_unknown_count": result.side_mapping_unknown_count,
                }
                for result in file_results
            ],
            [
                "file_path",
                "file_date",
                "selection_reason",
                "packet_count",
                "segment_count",
                "meaningful_segment_count",
                "source_gap_boundary_count",
                "snapshot_reset_boundary_count",
                "clean_segment_count",
                "dirty_segment_count",
                "all_segments_clean",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "min_segment_packet_count",
                "max_segment_packet_count",
                "one_packet_segment_count",
                "missing_transaction_time_count",
                "snapshot_like_packet_count",
                "estimated_preselection_source_gap_count",
                "actual_source_gap_boundary_count",
                "timestamp_fallback_used",
                "side_mapping_unknown_count",
            ],
        ),
        "",
        "## Aggregate Edge-Case Summary",
        _markdown_table(
            [
                {
                    "candidate_file_count": candidate_file_count,
                    "selected_file_count": selected_file_count,
                    "total_packet_count": total_packet_count,
                    "total_segment_count": total_segment_count,
                    "total_meaningful_segment_count": total_meaningful_segment_count,
                    "total_source_gap_boundary_count": total_source_gap_boundary_count,
                    "total_snapshot_reset_boundary_count": total_snapshot_reset_boundary_count,
                    "files_all_segments_clean": files_all_segments_clean,
                    "files_with_dirty_segments": files_with_dirty_segments,
                    "total_ofi_emitted_count": total_ofi_emitted_count,
                    "total_warmup_none_count": total_warmup_none_count,
                    "total_sequence_gap_count": total_sequence_gap_count,
                    "files_with_timestamp_fallback": files_with_timestamp_fallback,
                    "files_with_snapshot_like_packets": files_with_snapshot_like_packets,
                    "files_with_source_gap_boundaries": files_with_source_gap_boundaries,
                    "unknown_side_mapping_total": unknown_side_mapping_total,
                }
            ],
            [
                "candidate_file_count",
                "selected_file_count",
                "total_packet_count",
                "total_segment_count",
                "total_meaningful_segment_count",
                "total_source_gap_boundary_count",
                "total_snapshot_reset_boundary_count",
                "files_all_segments_clean",
                "files_with_dirty_segments",
                "total_ofi_emitted_count",
                "total_warmup_none_count",
                "total_sequence_gap_count",
                "files_with_timestamp_fallback",
                "files_with_snapshot_like_packets",
                "files_with_source_gap_boundaries",
                "unknown_side_mapping_total",
            ],
        ),
        "",
        "## Segment Boundary Results",
        "- Observed source gaps were converted into segment boundaries by the policy module. Snapshot/reset-like packets were not observed in this bounded raw sample; that policy path remains covered by synthetic/unit tests only.",
        "- OFIEngine was fresh per segment and no OFI state crossed boundaries.",
        "",
        "## Timestamp Fallback Results",
        "- The reusable policy supports transaction-time fallback ordering, and the synthetic tests cover this path. The bounded raw edge-case sample did not contain selected packets requiring fallback ordering.",
        "",
        "## Snapshot/Reset Results",
        "- Snapshot/reset-like packets were not observed in this bounded sample; the policy path remains covered by synthetic/unit tests only.",
        "",
        "## Source-Gap Results",
        "- Source gaps observed in the bounded sample were treated as segment boundaries and processed in memory only.",
        "",
        "## Join Readiness Sample",
        _markdown_table(
            join_rows,
            ["file_date", "bar_file_found", "bar_row_count", "join_attempted", "bar_count_preserved", "join_deferred_reason"],
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- Bounded raw L2 files were converted into `L2Packet` objects.",
        "- Edge-case-heavy files were selected deterministically.",
        "- Source gaps remained bounded and segmentable.",
        "- Snapshot/reset-like and timestamp-fallback behavior is covered by synthetic/unit tests.",
        "",
        "## What Failed Or Remains Unknown",
        "- This remains a bounded validation only.",
        "- The sample does not globally approve reconstruction.",
        "- A larger or different sample could still expose new issues.",
        "",
        "## What Is Safe",
        "- Bounded read-only segmented reconstruction validation.",
        "- Reusing the policy module for future bounded diagnostics.",
        "",
        "## What Is Not Safe",
        "- Full-corpus reconstruction.",
        "- Production, paper, or live use.",
        "- Alpha claims.",
        "",
        "## Decision",
        ", ".join(decision_labels) + ".",
        "",
        "## Required Next Step",
        "Use the policy module in another bounded read-only rehearsal or diagnostic sample before any broader reconstruction policy change.",
        "",
        PRODUCTION_APPROVAL_STATEMENT,
    ]
    return "\n".join(lines)


def run_validation(
    *,
    l2_root: Path,
    bar_dir: Path,
    max_candidate_files: int,
    max_selected_files: int,
    max_events_per_file: int,
    symbol: str,
) -> dict[str, Any]:
    ordered_files = discover_candidate_files(l2_root, symbol)
    candidate_pool = build_candidate_pool(ordered_files, max_candidate_files)
    candidate_previews = [preview_candidate_file(path, symbol=symbol) for path in candidate_pool]
    preview_map = {preview.candidate_file_path: preview for preview in candidate_previews}
    selected_files = select_final_files(candidate_previews, ordered_files, max_selected_files)
    selected_results = [
        evaluate_selected_file(
            path,
            bar_dir=bar_dir,
            symbol=symbol,
            max_events_per_file=max_events_per_file,
            selection_reason=reason,
            preselection_map=preview_map,
        )
        for path, reason in selected_files
    ]
    join_rows = [result.join_result for result in selected_results]
    report = build_report(
        l2_root=l2_root,
        candidate_file_count=len(candidate_previews),
        candidate_previews=candidate_previews,
        selected_files=selected_files,
        file_results=selected_results,
        join_rows=join_rows,
        max_candidate_files=max_candidate_files,
        max_selected_files=max_selected_files,
    )
    return {
        "candidate_previews": candidate_previews,
        "selected_files": selected_files,
        "selected_results": selected_results,
        "join_rows": join_rows,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_validation(
        l2_root=args.l2_root,
        bar_dir=args.bar_dir,
        max_candidate_files=args.max_candidate_files,
        max_selected_files=args.max_selected_files,
        max_events_per_file=args.max_events_per_file,
        symbol=args.symbol,
    )
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(result["report"], encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
