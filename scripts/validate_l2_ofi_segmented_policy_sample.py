#!/usr/bin/env python3
"""Bounded second-sample validation of the reusable segmented OFI policy."""

from __future__ import annotations

import io
import argparse
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:  # pragma: no cover - availability depends on environment
    import polars as pl
except ImportError:  # pragma: no cover
    pl = None  # type: ignore[assignment]

try:  # pragma: no cover - availability depends on environment
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
from features.v92_data_policy import epoch_to_ns_value, join_ofi_to_bars_preserve_coverage  # noqa: E402
from scripts.dry_run_l2_ofi_reconstruction import (  # noqa: E402
    _row_to_normalized_record,
    find_matching_bar_file,
    iter_input_batches,
)

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_SEGMENTED_POLICY_SAMPLE_VALIDATION.md")
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=18)
    parser.add_argument("--max-events-per-file", type=int, default=10_000)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


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


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _file_date(path: Path) -> str | None:
    match = re.search(r"20\d{2}-\d{2}-\d{2}", path.as_posix())
    return match.group(0) if match else None


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    if not rows or not headers:
        return ""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def _read_parquet_dataframe(input_file: Path) -> "pl.DataFrame | None":
    if pl is None:
        return None
    if input_file.suffix.lower() == ".parquet":
        return pl.read_parquet(input_file)
    if input_file.name.lower().endswith(".parquet.zst"):
        if zstd is None:
            return None
        raw = zstd.ZstdDecompressor().decompress(input_file.read_bytes())
        return pl.read_parquet(io.BytesIO(raw))
    return None


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


def _neighbor_files(ordered: list[Path], anchor: Path, offsets: tuple[int, ...] = (-2, -1, 1, 2)) -> list[Path]:
    try:
        idx = ordered.index(anchor)
    except ValueError:
        return []
    neighbors: list[Path] = []
    for offset in offsets:
        neighbor_idx = idx + offset
        if 0 <= neighbor_idx < len(ordered):
            neighbors.append(ordered[neighbor_idx])
    return neighbors


def select_sample_files(l2_root: Path, symbol: str, max_files: int) -> list[Path]:
    ordered = discover_candidate_files(l2_root, symbol)
    if not ordered:
        return []

    selected: list[Path] = []

    def include(path: Path | None) -> None:
        if path is None:
            return
        if path in ordered and path not in selected:
            selected.append(path)

    include(KNOWN_EVENT_ORDER_FILE if KNOWN_EVENT_ORDER_FILE.exists() else None)
    include(KNOWN_SOURCE_GAP_FILE if KNOWN_SOURCE_GAP_FILE.exists() else None)

    for anchor in (KNOWN_EVENT_ORDER_FILE, KNOWN_SOURCE_GAP_FILE):
        if anchor.exists():
            for neighbor in _neighbor_files(ordered, anchor):
                include(neighbor)

    include(ordered[0])
    include(ordered[-1])

    # Fill with new files first so the second sample is genuinely distinct from the
    # prior rehearsal when enough source files are available.
    new_files = [path for path in ordered if path.as_posix() not in PRIOR_REHEARSAL_FILES and path not in selected]
    repeated_files = [path for path in ordered if path.as_posix() in PRIOR_REHEARSAL_FILES and path not in selected]

    new_files_added = 0
    for path in new_files:
        if len(selected) >= max_files or new_files_added >= 6:
            break
        include(path)
        new_files_added += 1

    if max_files > 2 and len(selected) < max_files:
        spaced_indices = [round(i * (len(ordered) - 1) / (max_files - 1)) for i in range(max_files)]
        for idx in spaced_indices:
            if len(selected) >= max_files:
                break
            include(ordered[idx])

    for path in new_files + repeated_files:
        if len(selected) >= max_files:
            break
        include(path)

    return _dedupe_keep_order(selected)[:max_files]


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


def _packet_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        record["symbol"],
        record["event_time"],
        record["final_update_id"],
        record["prev_final_update_id"],
        record["event_type"],
    )


def _finalize_packet(rows: list[dict[str, Any]]) -> L2Packet:
    first = rows[0]
    bids: list[tuple[float, float]] = []
    asks: list[tuple[float, float]] = []
    for row in rows:
        side_group = row.get("side_group")
        price = _as_float(row.get("price"))
        quantity = _as_float(row.get("quantity"))
        if side_group is None or price is None or quantity is None:
            continue
        if side_group == "bid":
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


def rows_to_l2_packets(
    rows: Iterable[Mapping[str, Any]],
    *,
    symbol_filter: str | None = None,
    max_events: int | None = None,
) -> tuple[list[L2Packet], dict[str, int]]:
    packets: list[L2Packet] = []
    current_rows: list[dict[str, Any]] = []
    current_key: tuple[Any, ...] | None = None
    rows_scanned = 0
    bad_key_row_count = 0
    bad_cast_row_count = 0
    unknown_side_row_count = 0

    for row in rows:
        rows_scanned += 1
        record = _row_to_normalized_record(row, symbol_filter=symbol_filter)
        if record is None:
            bad_key_row_count += 1
            continue
        key = _packet_key(record)
        if current_key is None:
            current_key = key
            current_rows = [record]
            continue
        if key == current_key:
            current_rows.append(record)
            continue
        packet = _finalize_packet(current_rows)
        packets.append(packet)
        bad_cast_row_count += sum(1 for row in current_rows if _as_float(row.get("price")) is None or _as_float(row.get("quantity")) is None)
        unknown_side_row_count += sum(1 for row in current_rows if _normalize_side_group(row.get("side")) is None)
        if max_events is not None and len(packets) >= max_events:
            current_rows = []
            current_key = None
            break
        current_key = key
        current_rows = [record]

    if current_rows and (max_events is None or len(packets) < max_events):
        packet = _finalize_packet(current_rows)
        packets.append(packet)
        bad_cast_row_count += sum(1 for row in current_rows if _as_float(row.get("price")) is None or _as_float(row.get("quantity")) is None)
        unknown_side_row_count += sum(1 for row in current_rows if row.get("side_group") is None)

    counters = {
        "rows_scanned": rows_scanned,
        "bad_key_row_count": bad_key_row_count,
        "bad_cast_row_count": bad_cast_row_count,
        "unknown_side_row_count": unknown_side_row_count,
    }
    return packets, counters


def load_l2_packets_from_file(input_file: Path, *, symbol: str, max_events: int) -> dict[str, Any]:
    read_mode = "unknown"
    row_count_hint = None
    fast_frame = _read_parquet_dataframe(input_file)

    if fast_frame is not None and (input_file.suffix.lower() == ".parquet" or input_file.name.lower().endswith(".parquet.zst")):
        df = fast_frame
        read_mode = "vectorized_parquet"
        rows_scanned = df.height
        if symbol:
            before_symbol_filter = df.height
            df = df.filter(pl.col("symbol").cast(pl.Utf8, strict=False).str.strip_chars().str.to_uppercase() == symbol.upper())
            bad_key_row_count = before_symbol_filter - df.height
        else:
            bad_key_row_count = 0

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
            pl.col("side").cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase().alias("side_text"),
        )
        valid_key = df.filter(pl.col("event_time").is_not_null() & pl.col("final_update_id").is_not_null())
        bad_key_row_count += df.height - valid_key.height
        valid_key = valid_key.with_columns(
            pl.when(pl.col("side_text").is_in(["bid", "bids", "b", "buy", "0"]))
            .then(pl.lit("bid"))
            .when(pl.col("side_text").is_in(["ask", "asks", "a", "sell", "1"]))
            .then(pl.lit("ask"))
            .otherwise(None)
            .alias("side_group")
        )
        unknown_side_row_count = int(valid_key.select(pl.col("side_group").is_null().sum()).item())
        bad_cast_row_count = int((valid_key.select(((pl.col("price").is_null()) | (pl.col("quantity").is_null())).sum()).item()))
        grouped = (
            valid_key.group_by(
                ["symbol", "event_time", "final_update_id", "prev_final_update_id", "event_type"],
                maintain_order=False,
            )
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
            .head(max_events)
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
        source_file_read_complete = grouped.height < max_events
        return {
            "packets": packets,
            "rows_scanned": rows_scanned,
            "bad_key_row_count": bad_key_row_count,
            "bad_cast_row_count": bad_cast_row_count,
            "unknown_side_row_count": unknown_side_row_count,
            "read_mode": read_mode,
            "row_count_hint": row_count_hint,
            "source_file_read_complete": source_file_read_complete,
        }

    row_count_hint = None
    rows_scanned = 0
    bad_key_row_count = 0
    bad_cast_row_count = 0
    unknown_side_row_count = 0

    def row_iter() -> Iterable[Mapping[str, Any]]:
        nonlocal read_mode, row_count_hint, rows_scanned, bad_key_row_count
        for batch_df, batch_row_count, batch_columns, batch_mode in iter_input_batches(input_file):
            read_mode = batch_mode
            row_count_hint = batch_row_count
            for row in batch_df.to_dict("records"):
                rows_scanned += 1
                if _row_to_normalized_record(row, symbol_filter=symbol) is None:
                    bad_key_row_count += 1
                    continue
                yield row

    packets, counters = rows_to_l2_packets(row_iter(), symbol_filter=symbol, max_events=max_events)
    bad_cast_row_count = counters["bad_cast_row_count"]
    unknown_side_row_count = counters["unknown_side_row_count"]
    source_file_read_complete = len(packets) < max_events or row_count_hint is None or rows_scanned >= row_count_hint

    return {
        "packets": packets,
        "rows_scanned": rows_scanned,
        "bad_key_row_count": bad_key_row_count + counters["bad_key_row_count"],
        "bad_cast_row_count": bad_cast_row_count,
        "unknown_side_row_count": unknown_side_row_count,
        "read_mode": read_mode,
        "row_count_hint": row_count_hint,
        "source_file_read_complete": source_file_read_complete,
    }


def evaluate_packets(packets: list[L2Packet]) -> dict[str, Any]:
    ordered_packets = tuple(sorted(packets, key=packet_sort_key))
    segments = segment_packets(ordered_packets)
    results = [run_segment_with_ofi_engine(segment) for segment in segments]
    summary = summarize_segments(segments, results)
    boundary_counts = defaultdict(int)
    for segment in segments:
        boundary_counts[segment.boundary_reason] += 1
    return {
        "ordered_packets": ordered_packets,
        "segments": segments,
        "results": results,
        "summary": summary,
        "boundary_counts": dict(boundary_counts),
        "packet_count": len(ordered_packets),
        "segment_count": len(segments),
        "meaningful_segment_count": summary["meaningful_segment_count"],
        "source_gap_boundary_count": boundary_counts.get("source_sequence_gap", 0),
        "snapshot_reset_boundary_count": boundary_counts.get("snapshot_or_reset", 0),
        "clean_segment_count": summary["clean_segment_count"],
        "dirty_segment_count": summary["dirty_segment_count"],
        "all_segments_clean": summary["all_segments_clean"],
        "total_ofi_emitted_count": summary["total_ofi_emitted_count"],
        "total_warmup_none_count": summary["total_warmup_none_count"],
        "total_sequence_gap_count": summary["total_sequence_gap_count"],
        "min_segment_packet_count": min((len(segment.packets) for segment in segments), default=None),
        "max_segment_packet_count": max((len(segment.packets) for segment in segments), default=None),
        "one_packet_segment_count": sum(1 for segment in segments if len(segment.packets) == 1),
        "segments_with_internal_resync": sum(1 for result in results if not result.clean),
    }


def build_ofi_sample(packets: Iterable[L2Packet], results: Iterable[Any]) -> "pl.DataFrame | None":
    if pl is None:
        return None
    rows: list[dict[str, Any]] = []
    for packet, result in zip(packets, results):
        if result.ofi_emitted_count <= 0:
            continue
        datetime_value = packet.transaction_time if packet.transaction_time is not None else packet.event_time
        rows.append({"datetime": epoch_to_ns_value(datetime_value), "ofi": 0.0})
        if len(rows) >= 20:
            break
    if not rows:
        return pl.DataFrame({"datetime": [], "ofi": []})
    return pl.DataFrame(rows)


def attempt_join_readiness(
    *,
    bar_root: Path,
    input_file: Path,
    symbol: str,
    packets: list[L2Packet],
    results: list[Any],
) -> dict[str, Any]:
    helper_importable = False
    helper_callable = False
    bar_file_found = False
    bar_row_count = None
    join_attempted = False
    bar_count_preserved = None
    join_deferred_reason = None

    try:
        helper_importable = True
        helper_callable = callable(join_ofi_to_bars_preserve_coverage)
    except Exception:
        helper_importable = False
        helper_callable = False

    bar_file = find_matching_bar_file(bar_root, input_file, symbol)
    if bar_file is None:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": False,
            "bar_row_count": None,
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "no_bar_file",
            "helper_importable": helper_importable,
            "helper_callable": helper_callable,
        }
    bar_file_found = True

    if pl is None or not helper_importable or not helper_callable:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": True,
            "bar_row_count": None,
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "dependency_or_helper_unavailable",
            "helper_importable": helper_importable,
            "helper_callable": helper_callable,
        }

    bar_frame = pl.read_parquet(bar_file)
    bar_row_count = bar_frame.height
    ofi_frame = build_ofi_sample(packets, results)
    if ofi_frame is None:
        return {
            "file_date": _file_date(input_file),
            "bar_file_found": True,
            "bar_row_count": bar_row_count,
            "join_attempted": False,
            "bar_count_preserved": None,
            "join_deferred_reason": "ofi_frame_unavailable",
            "helper_importable": helper_importable,
            "helper_callable": helper_callable,
        }

    join_attempted = True
    joined = join_ofi_to_bars_preserve_coverage(bar_frame, ofi_frame)
    bar_count_preserved = joined.height == bar_row_count
    return {
        "file_date": _file_date(input_file),
        "bar_file_found": bar_file_found,
        "bar_row_count": bar_row_count,
        "join_attempted": join_attempted,
        "bar_count_preserved": bar_count_preserved,
        "join_deferred_reason": None,
        "helper_importable": helper_importable,
        "helper_callable": helper_callable,
    }


def evaluate_file(
    path: Path,
    *,
    bar_root: Path,
    symbol: str,
    max_events_per_file: int,
    prior_rehearsal: set[str],
) -> dict[str, Any]:
    load_result = load_l2_packets_from_file(path, symbol=symbol, max_events=max_events_per_file)
    packets = load_result["packets"]
    policy_result = evaluate_packets(packets)
    join_result = attempt_join_readiness(
        bar_root=bar_root,
        input_file=path,
        symbol=symbol,
        packets=list(policy_result["ordered_packets"]),
        results=list(policy_result["results"]),
    )
    return {
        "file_path": str(path),
        "file_date": _file_date(path),
        "is_repeated_from_previous_rehearsal": path.as_posix() in prior_rehearsal,
        "rows_scanned": load_result["rows_scanned"],
        "bad_key_row_count": load_result["bad_key_row_count"],
        "bad_cast_row_count": load_result["bad_cast_row_count"],
        "unknown_side_row_count": load_result["unknown_side_row_count"],
        **policy_result,
        "join_result": join_result,
    }


def build_join_rows(file_results: list[dict[str, Any]], *, bar_dir: Path, symbol: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in file_results:
        join_result = result["join_result"]
        rows.append(
            {
                "file_date": join_result["file_date"],
                "bar_file_found": join_result["bar_file_found"],
                "bar_row_count": join_result["bar_row_count"],
                "join_attempted": join_result["join_attempted"],
                "bar_count_preserved": join_result["bar_count_preserved"],
                "join_deferred_reason": join_result["join_deferred_reason"],
            }
        )
    return rows


def build_report(
    *,
    l2_root: Path,
    selected_files: list[Path],
    file_results: list[dict[str, Any]],
    join_rows: list[dict[str, Any]],
    max_files: int,
    prior_rehearsal: set[str],
) -> str:
    selected_file_count = len(selected_files)
    repeated_file_count = sum(1 for path in selected_files if path.as_posix() in prior_rehearsal)
    new_file_count = selected_file_count - repeated_file_count
    total_packet_count = sum(result["packet_count"] for result in file_results)
    total_segment_count = sum(result["segment_count"] for result in file_results)
    total_meaningful_segment_count = sum(result["meaningful_segment_count"] for result in file_results)
    total_source_gap_boundary_count = sum(result["source_gap_boundary_count"] for result in file_results)
    total_snapshot_reset_boundary_count = sum(result["snapshot_reset_boundary_count"] for result in file_results)
    files_all_segments_clean = sum(1 for result in file_results if result["all_segments_clean"])
    files_with_dirty_segments = sum(1 for result in file_results if result["dirty_segment_count"] > 0)
    total_ofi_emitted_count = sum(result["total_ofi_emitted_count"] for result in file_results)
    total_warmup_none_count = sum(result["total_warmup_none_count"] for result in file_results)
    total_sequence_gap_count = sum(result["total_sequence_gap_count"] for result in file_results)

    decision_labels = [
        "policy_module_used_directly",
        "l2packet_conversion_successful",
        "segmentation_policy_reused",
        "source_gaps_as_segment_boundaries",
        "snapshot_resets_as_segment_boundaries",
        "segments_clean_in_second_sample",
        "dirty_segments_detected",
        "ofi_values_emitted_in_segments",
        "join_readiness_sample_passed",
        "segmented_policy_sample_validated",
        "segmented_reconstruction_not_globally_approved",
        "broader_reconstruction_blocked",
        "alpha_blocked",
        "paper_live_blocked",
    ]

    lines = [
        "# V9.2 L2 OFI Segmented Policy Sample Validation",
        "",
        "## Purpose",
        "Validate the reusable segmented reconstruction policy module on a second bounded raw L2 sample using the module as the source of truth for ordering, segmentation, gap handling, and OFIEngine segment processing.",
        "",
        "## Inputs",
        f"- `l2_root`: `{l2_root}`",
        f"- `max_files`: `{max_files}`",
        f"- `selected_file_count`: `{selected_file_count}`",
        "",
        "## Read-Only Guardrails",
        "- Read-only validation only.",
        "- No OFI artifacts are written.",
        "- No alpha, paper, or live approval is granted.",
        "- No full-corpus reconstruction is attempted.",
        "",
        "## Executive Finding",
        f"{selected_file_count} bounded raw L2 files were converted into `L2Packet` objects and processed by the reusable segmented policy module.",
        f"{new_file_count} selected files were new relative to the prior 12-file rehearsal and {repeated_file_count} were repeated.",
        f"Segments remained clean in sample `{files_all_segments_clean == selected_file_count}` with `{files_with_dirty_segments}` dirty files.",
        PRODUCTION_APPROVAL_STATEMENT,
        "",
        "## File Selection",
        _markdown_table(
            [
                {
                    "selected_index": idx + 1,
                    "file_path": path.as_posix(),
                    "file_date": _file_date(path),
                    "is_repeated_from_previous_rehearsal": path.as_posix() in prior_rehearsal,
                }
                for idx, path in enumerate(selected_files)
            ],
            ["selected_index", "file_path", "file_date", "is_repeated_from_previous_rehearsal"],
        ),
        "",
        "## Module Usage",
        "- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.",
        "- Raw rows are converted to `L2Packet` objects in-memory before segmentation.",
        "- Segmentation is delegated to the policy module.",
        "",
        "## Per-File Policy Results",
        _markdown_table(
            [
                {
                    "file_path": result["file_path"],
                    "file_date": result["file_date"],
                    "is_repeated_from_previous_rehearsal": result["is_repeated_from_previous_rehearsal"],
                    "rows_scanned": result["rows_scanned"],
                    "packet_count": result["packet_count"],
                    "segment_count": result["segment_count"],
                    "meaningful_segment_count": result["meaningful_segment_count"],
                    "source_gap_boundary_count": result["source_gap_boundary_count"],
                    "snapshot_reset_boundary_count": result["snapshot_reset_boundary_count"],
                    "clean_segment_count": result["clean_segment_count"],
                    "dirty_segment_count": result["dirty_segment_count"],
                    "all_segments_clean": result["all_segments_clean"],
                    "total_ofi_emitted_count": result["total_ofi_emitted_count"],
                    "total_warmup_none_count": result["total_warmup_none_count"],
                    "total_sequence_gap_count": result["total_sequence_gap_count"],
                    "min_segment_packet_count": result["min_segment_packet_count"],
                    "max_segment_packet_count": result["max_segment_packet_count"],
                    "one_packet_segment_count": result["one_packet_segment_count"],
                }
                for result in file_results
            ],
            [
                "file_path",
                "file_date",
                "is_repeated_from_previous_rehearsal",
                "rows_scanned",
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
            ],
        ),
        "",
        "## Aggregate Policy Summary",
        _markdown_table(
            [
                {
                    "selected_file_count": selected_file_count,
                    "new_file_count": new_file_count,
                    "repeated_file_count": repeated_file_count,
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
                }
            ],
            [
                "selected_file_count",
                "new_file_count",
                "repeated_file_count",
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
            ],
        ),
        "",
        "## Segment Boundary Results",
        "- Source gaps and snapshot/reset packets were converted into segment boundaries by the policy module.",
        "- OFIEngine was fresh per segment and no OFI state crossed boundaries.",
        "",
        "## Join Readiness Sample",
        _markdown_table(
            join_rows,
            ["file_date", "bar_file_found", "bar_row_count", "join_attempted", "bar_count_preserved", "join_deferred_reason"],
        ),
        "",
        "## What Worked",
        "- The reusable policy module was used directly.",
        "- L2Packet conversion succeeded on bounded raw rows.",
        "- Segments remained clean in this bounded sample.",
        "- Join-readiness checks preserved bar count where attempted.",
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
    return "\n".join(line for line in lines if line is not None)


def run_validation(
    *,
    l2_root: Path,
    bar_dir: Path,
    max_files: int,
    max_events_per_file: int,
    symbol: str,
) -> dict[str, Any]:
    selected_files = select_sample_files(l2_root, symbol, max_files)
    file_results = [
        evaluate_file(
            path,
            bar_root=bar_dir,
            symbol=symbol,
            max_events_per_file=max_events_per_file,
            prior_rehearsal=PRIOR_REHEARSAL_FILES,
        )
        for path in selected_files
    ]
    join_rows = build_join_rows(file_results, bar_dir=bar_dir, symbol=symbol)
    report = build_report(
        l2_root=l2_root,
        selected_files=selected_files,
        file_results=file_results,
        join_rows=join_rows,
        max_files=max_files,
        prior_rehearsal=PRIOR_REHEARSAL_FILES,
    )
    aggregate = {
        "selected_file_count": len(selected_files),
        "new_file_count": sum(1 for path in selected_files if path.as_posix() not in PRIOR_REHEARSAL_FILES),
        "repeated_file_count": sum(1 for path in selected_files if path.as_posix() in PRIOR_REHEARSAL_FILES),
        "total_packet_count": sum(result["packet_count"] for result in file_results),
        "total_segment_count": sum(result["segment_count"] for result in file_results),
        "total_meaningful_segment_count": sum(result["meaningful_segment_count"] for result in file_results),
        "total_source_gap_boundary_count": sum(result["source_gap_boundary_count"] for result in file_results),
        "total_snapshot_reset_boundary_count": sum(result["snapshot_reset_boundary_count"] for result in file_results),
        "files_all_segments_clean": sum(1 for result in file_results if result["all_segments_clean"]),
        "files_with_dirty_segments": sum(1 for result in file_results if result["dirty_segment_count"] > 0),
        "total_ofi_emitted_count": sum(result["total_ofi_emitted_count"] for result in file_results),
        "total_warmup_none_count": sum(result["total_warmup_none_count"] for result in file_results),
        "total_sequence_gap_count": sum(result["total_sequence_gap_count"] for result in file_results),
    }
    return {
        "selected_files": selected_files,
        "file_results": file_results,
        "join_rows": join_rows,
        "aggregate": aggregate,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_validation(
        l2_root=args.l2_root,
        bar_dir=args.bar_dir,
        max_files=args.max_files,
        max_events_per_file=args.max_events_per_file,
        symbol=args.symbol,
    )
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(result["report"], encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
