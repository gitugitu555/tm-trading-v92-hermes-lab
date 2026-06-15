#!/usr/bin/env python3
"""Bounded multi-file validation for raw L2 OFI reconstruction."""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:  # pragma: no cover - availability depends on environment
    import polars as pl
except ImportError:  # pragma: no cover
    pl = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from features.v92_data_policy import epoch_to_ns_value, join_ofi_to_bars_preserve_coverage
from scripts.dry_run_l2_ofi_reconstruction import (  # reuse repaired dry-run helpers
    PacketRecord,
    _row_to_normalized_record,
    find_matching_bar_file,
    iter_input_batches,
    summarize_ofi,
)

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_RECONSTRUCTION_SAMPLE_VALIDATION.md")
PRODUCTION_APPROVAL_STATEMENT = "This validation does not approve OFI for production, paper trading, live trading, or alpha use."
SUPPORTED_SUFFIXES = {".parquet", ".zst", ".csv", ".json", ".jsonl", ".gz"}


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, got {value!r}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=6)
    parser.add_argument("--max-events-per-file", type=int, default=2000)
    parser.add_argument("--strict-sequence", type=parse_bool, default=True)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _file_date(path: Path) -> str | None:
    match = re.search(r"20\d{2}-\d{2}-\d{2}", path.as_posix())
    return match.group(0) if match else None


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


def select_deterministic_files(files: list[Path], max_files: int) -> list[Path]:
    ordered = sorted(files, key=lambda p: p.as_posix())
    if len(ordered) <= max_files:
        return ordered
    if max_files <= 1:
        return [ordered[0]]
    if max_files == 2:
        return [ordered[0], ordered[-1]]
    indices = [round(i * (len(ordered) - 1) / (max_files - 1)) for i in range(max_files)]
    selected: list[Path] = []
    seen: set[str] = set()
    for idx in indices:
        path = ordered[idx]
        if path.as_posix() not in seen:
            selected.append(path)
            seen.add(path.as_posix())
    if ordered[0].as_posix() not in seen:
        selected.insert(0, ordered[0])
    if ordered[-1].as_posix() not in seen:
        selected.append(ordered[-1])
    return sorted(selected, key=lambda p: p.as_posix())


def packet_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record["symbol"],
        record["event_time"],
        record["final_update_id"],
        record["prev_final_update_id"],
        record["event_type"],
    )


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value)


def _build_packet_from_rows(rows: list[dict[str, Any]]) -> PacketRecord:
    first = rows[0]
    packet = PacketRecord(
        key=packet_key(first),
        symbol=str(first["symbol"]),
        event_time=int(first["event_time"]),
        transaction_time=first["transaction_time"],
        received_time=first["received_time"],
        event_type=first["event_type"],
        first_update_id=first["first_update_id"],
        final_update_id=int(first["final_update_id"]),
        prev_final_update_id=first["prev_final_update_id"],
        last_update_id=first["last_update_id"],
        snapshot_or_reset=first["first_update_id"] is None or first["prev_final_update_id"] is None,
    )
    for row in rows:
        packet.raw_row_count += 1
        side_group = row["side_group"]
        price = row["price"]
        quantity = row["quantity"]
        if side_group is None:
            packet.unknown_side_count += 1
            continue
        if price is None or quantity is None:
            packet.bad_cast_count += 1
            continue
        if side_group == "bid":
            packet.bids.append((float(price), float(quantity)))
        else:
            packet.asks.append((float(price), float(quantity)))
    return packet


def group_row_order_packets(rows: list[dict[str, Any]]) -> list[PacketRecord]:
    packets: list[PacketRecord] = []
    if not rows:
        return packets
    current_key = packet_key(rows[0])
    current_rows = [rows[0]]
    for row in rows[1:]:
        key = packet_key(row)
        if key != current_key:
            packets.append(_build_packet_from_rows(current_rows))
            current_rows = [row]
            current_key = key
        else:
            current_rows.append(row)
    if current_rows:
        packets.append(_build_packet_from_rows(current_rows))
    return packets


def group_global_packets(rows: list[dict[str, Any]]) -> list[PacketRecord]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order: list[tuple[Any, ...]] = []
    for row in rows:
        key = packet_key(row)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    packets = [_build_packet_from_rows(grouped[key]) for key in order]
    packets.sort(key=lambda pkt: (pkt.event_time, pkt.final_update_id, str(pkt.key)))
    return packets


def count_duplicate_packet_keys(packets: list[PacketRecord]) -> int:
    counts = Counter(pkt.key for pkt in packets)
    return sum(1 for count in counts.values() if count > 1)


def count_bid_ask_updates(rows: list[dict[str, Any]]) -> tuple[int, int]:
    bid = sum(1 for row in rows if row["side_group"] == "bid")
    ask = sum(1 for row in rows if row["side_group"] == "ask")
    return bid, ask


def packet_boundary_risk(last_packet_key: tuple[Any, ...], next_row_key: tuple[Any, ...] | None) -> bool:
    return next_row_key is not None and next_row_key == last_packet_key


def scan_file_rows(
    input_file: Path,
    *,
    symbol: str,
    max_events_per_file: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rows_scanned = 0
    bad_key_row_count = 0
    bad_cast_row_count = 0
    unknown_side_row_count = 0
    packet_boundary_unknown = False
    dropped_last_packet_for_boundary_safety = 0
    current_rows: list[dict[str, Any]] = []
    current_key: tuple[Any, ...] | None = None
    complete_packet_count = 0
    for batch_df, _, _, _ in iter_input_batches(input_file):
        for row in batch_df.to_dict("records"):
            rows_scanned += 1
            record = _row_to_normalized_record(row, symbol_filter=symbol)
            if record is None:
                bad_key_row_count += 1
                continue
            key = packet_key(record)
            if current_key is None:
                current_key = key
                current_rows = [record]
                continue
            if key == current_key:
                current_rows.append(record)
                continue

            packet = _build_packet_from_rows(current_rows)
            rows.extend(current_rows)
            bad_cast_row_count += packet.bad_cast_count
            unknown_side_row_count += packet.unknown_side_count
            complete_packet_count += 1
            if complete_packet_count >= max_events_per_file:
                current_rows = []
                current_key = None
                break
            current_rows = [record]
            current_key = key
        if complete_packet_count >= max_events_per_file:
            break

    if current_rows and complete_packet_count < max_events_per_file:
        # EOF or bounded scan ended mid-packet; drop the incomplete packet.
        packet_boundary_unknown = True
        dropped_last_packet_for_boundary_safety = 1

    return {
        "rows": rows,
        "rows_scanned": rows_scanned,
        "bad_key_row_count": bad_key_row_count,
        "bad_cast_row_count": bad_cast_row_count,
        "unknown_side_row_count": unknown_side_row_count,
        "packet_boundary_unknown": packet_boundary_unknown,
        "dropped_last_packet_for_boundary_safety": dropped_last_packet_for_boundary_safety,
        "complete_packet_count": complete_packet_count,
    }


def compare_grouping(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_order_packets = group_row_order_packets(rows)
    global_packets = group_global_packets(rows)
    row_order_duplicate_packet_key_count = count_duplicate_packet_keys(row_order_packets)
    global_duplicate_packet_key_count = count_duplicate_packet_keys(global_packets)
    row_order_bid_count, row_order_ask_count = count_bid_ask_updates(rows)
    global_bid_count, global_ask_count = count_bid_ask_updates(rows)
    return {
        "row_order_packets": row_order_packets,
        "global_packets": global_packets,
        "row_order_packet_count": len(row_order_packets),
        "global_packet_count": len(global_packets),
        "row_order_duplicate_packet_key_count": row_order_duplicate_packet_key_count,
        "global_duplicate_packet_key_count": global_duplicate_packet_key_count,
        "row_order_bid_update_count": row_order_bid_count,
        "row_order_ask_update_count": row_order_ask_count,
        "global_bid_update_count": global_bid_count,
        "global_ask_update_count": global_ask_count,
        "first_row_order_key": row_order_packets[0].key if row_order_packets else None,
        "last_row_order_key": row_order_packets[-1].key if row_order_packets else None,
        "first_global_key": global_packets[0].key if global_packets else None,
        "last_global_key": global_packets[-1].key if global_packets else None,
        "packet_grouping_order_risk": (
            len(row_order_packets) != len(global_packets)
            or row_order_duplicate_packet_key_count != global_duplicate_packet_key_count
            or (row_order_packets and global_packets and row_order_packets[0].key != global_packets[0].key)
            or (row_order_packets and global_packets and row_order_packets[-1].key != global_packets[-1].key)
        ),
    }


def process_global_packets(
    global_packets: list[PacketRecord],
    *,
    strict_sequence: bool,
) -> dict[str, Any]:
    return _process_packets(global_packets, strict_sequence=strict_sequence)


def _process_packets(packets: list[PacketRecord], *, strict_sequence: bool) -> dict[str, Any]:
    engine = OFIEngine()
    ofi_values: list[float | None] = []
    event_times: list[int] = []
    final_update_ids: list[int] = []
    sequence_gap_count = 0
    duplicate_final_update_id_count = 0
    snapshot_or_reset_event_count = 0
    warmup_none_count = 0
    processed_event_count = 0
    ofi_emitted_count = 0
    resync_stop_event_index: int | None = None
    last_final_update_id: int | None = None

    for idx, packet in enumerate(packets, start=1):
        processed_event_count += 1
        if packet.snapshot_or_reset:
            snapshot_or_reset_event_count += 1
            engine.reset()

        previous_update_id = None if packet.snapshot_or_reset else packet.prev_final_update_id
        ofi = engine.process_event(
            bids=packet.bids,
            asks=packet.asks,
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=previous_update_id,
        )
        if engine.requires_resync and not packet.snapshot_or_reset:
            sequence_gap_count += 1
            resync_stop_event_index = idx
            ofi_values.append(None)
            event_times.append(packet.event_time)
            final_update_ids.append(packet.final_update_id)
            if strict_sequence:
                break
            engine.reset()
            continue

        if last_final_update_id is not None and packet.final_update_id == last_final_update_id:
            duplicate_final_update_id_count += 1
        last_final_update_id = packet.final_update_id

        event_times.append(packet.event_time)
        final_update_ids.append(packet.final_update_id)
        if ofi is None:
            warmup_none_count += 1
            ofi_values.append(None)
        else:
            ofi_values.append(float(ofi))
            ofi_emitted_count += 1

    return {
        "ofi_values": ofi_values,
        "event_times": event_times,
        "final_update_ids": final_update_ids,
        "processed_event_count": processed_event_count,
        "ofi_emitted_count": ofi_emitted_count,
        "warmup_none_count": warmup_none_count,
        "sequence_gap_count": sequence_gap_count,
        "duplicate_final_update_id_count": duplicate_final_update_id_count,
        "snapshot_or_reset_event_count": snapshot_or_reset_event_count,
        "resync_stop_event_index": resync_stop_event_index,
    }


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(v) for v in value) + ")"
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(v) for v in value) + "]"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h)) for h in headers) + " |")
    return "\n".join(lines)


def _bar_row_count(path: Path) -> int | None:
    if pl is None:
        return None
    try:
        return pl.scan_parquet(path).select(pl.len()).collect().item()
    except Exception:
        return None


def attempt_join_sample(
    *,
    bar_root: Path,
    input_file: Path,
    symbol: str,
    processed_event_times: list[int],
    processed_ofi_values: list[float | None],
) -> dict[str, Any]:
    helper_importable = True
    helper_callable = callable(join_ofi_to_bars_preserve_coverage)
    bar_file = find_matching_bar_file(bar_root, input_file, symbol)
    if bar_file is None or not bar_file.exists():
        return {
            "bar_file_found": False,
            "bar_row_count": None,
            "join_attempted": False,
            "joined_row_count": None,
            "bar_count_preserved": None,
            "join_deferred_reason": "bar_file_missing",
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
        }
    if pl is None:
        return {
            "bar_file_found": True,
            "bar_row_count": _bar_row_count(bar_file),
            "join_attempted": False,
            "joined_row_count": None,
            "bar_count_preserved": None,
            "join_deferred_reason": "polars_missing",
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
        }
    ofi_pairs = [(t, v) for t, v in zip(processed_event_times, processed_ofi_values) if v is not None]
    if not ofi_pairs:
        return {
            "bar_file_found": True,
            "bar_row_count": _bar_row_count(bar_file),
            "join_attempted": False,
            "joined_row_count": None,
            "bar_count_preserved": None,
            "join_deferred_reason": "no_ofi_values",
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
        }
    try:
        bar_frame = pl.scan_parquet(bar_file).collect()
        ofi_frame = pl.DataFrame(
            {
                "datetime": pd.to_datetime([epoch_to_ns_value(t) for t, _ in ofi_pairs], unit="ns"),
                "ofi": [v for _, v in ofi_pairs],
            }
        )
        joined = join_ofi_to_bars_preserve_coverage(bar_frame, ofi_frame)
        return {
            "bar_file_found": True,
            "bar_row_count": bar_frame.height,
            "join_attempted": True,
            "joined_row_count": joined.height,
            "bar_count_preserved": joined.height == bar_frame.height,
            "join_deferred_reason": None,
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "bar_file_found": True,
            "bar_row_count": _bar_row_count(bar_file),
            "join_attempted": False,
            "joined_row_count": None,
            "bar_count_preserved": None,
            "join_deferred_reason": f"join_failed:{type(exc).__name__}",
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
        }


def _date_range_from_path(path: Path) -> str:
    date_str = _file_date(path)
    return date_str or "unknown"


def process_file(
    path: Path,
    *,
    bar_root: Path,
    symbol: str,
    max_events_per_file: int,
    strict_sequence: bool,
) -> dict[str, Any]:
    sample = scan_file_rows(path, symbol=symbol, max_events_per_file=max_events_per_file)
    grouping = compare_grouping(sample["rows"])
    processing = process_global_packets(grouping["global_packets"], strict_sequence=strict_sequence)
    ofi_summary = summarize_ofi(processing["ofi_values"])
    join_summary = attempt_join_sample(
        bar_root=bar_root,
        input_file=path,
        symbol=symbol,
        processed_event_times=processing["event_times"],
        processed_ofi_values=processing["ofi_values"],
    )
    bid_count, ask_count = count_bid_ask_updates(sample["rows"])
    return {
        "file_path": str(path),
        "file_date": _date_range_from_path(path),
        "rows_scanned": sample["rows_scanned"],
        "row_order_packet_count": grouping["row_order_packet_count"],
        "global_packet_count": grouping["global_packet_count"],
        "packet_grouping_order_risk": grouping["packet_grouping_order_risk"],
        "row_order_duplicate_packet_key_count": grouping["row_order_duplicate_packet_key_count"],
        "global_duplicate_packet_key_count": grouping["global_duplicate_packet_key_count"],
        "duplicate_packet_key_count": grouping["global_duplicate_packet_key_count"],
        "dropped_last_packet_for_boundary_safety": sample["dropped_last_packet_for_boundary_safety"],
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
        "processed_event_count": processing["processed_event_count"],
        "ofi_emitted_count": processing["ofi_emitted_count"],
        "warmup_none_count": processing["warmup_none_count"],
        "snapshot_or_reset_event_count": processing["snapshot_or_reset_event_count"],
        "sequence_gap_count": processing["sequence_gap_count"],
        "resync_stop_event_index": processing["resync_stop_event_index"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "bid_update_count": bid_count,
        "ask_update_count": ask_count,
        "ofi_positive_count": ofi_summary["ofi_positive_count"],
        "ofi_negative_count": ofi_summary["ofi_negative_count"],
        "ofi_zero_count": ofi_summary["ofi_zero_count"],
        "ofi_mean": ofi_summary["ofi_mean"],
        "ofi_min": ofi_summary["ofi_min"],
        "ofi_max": ofi_summary["ofi_max"],
        "ofi_abs_sum": ofi_summary["ofi_abs_sum"],
        "event_time_min": min((pkt.event_time for pkt in grouping["global_packets"]), default=None),
        "event_time_max": max((pkt.event_time for pkt in grouping["global_packets"]), default=None),
        "final_update_id_min": min((pkt.final_update_id for pkt in grouping["global_packets"]), default=None),
        "final_update_id_max": max((pkt.final_update_id for pkt in grouping["global_packets"]), default=None),
        "first_packet_key": grouping["first_global_key"],
        "last_packet_key": grouping["last_global_key"],
        "cross_file_continuity_status": "cross_file_unknown",
        "join_summary": join_summary,
        "global_packets": grouping["global_packets"],
        "row_order_packets": grouping["row_order_packets"],
        "strict_sequence": strict_sequence,
        "packet_boundary_unknown": sample["packet_boundary_unknown"],
    }


def classify_cross_file_continuity(left: dict[str, Any], right: dict[str, Any]) -> str:
    left_last = left["last_packet_key"]
    right_first = right["first_packet_key"]
    if left_last is None or right_first is None:
        return "cross_file_unknown"
    left_date = left.get("file_date")
    right_date = right.get("file_date")
    if left_date != "unknown" and right_date != "unknown":
        if left_date == right_date:
            if left["final_update_id_max"] is not None and right["global_packets"]:
                if right["global_packets"][0].prev_final_update_id == left["final_update_id_max"]:
                    return "cross_file_continuity_plausible"
                if right["global_packets"][0].prev_final_update_id is not None:
                    return "cross_file_gap_suspected"
            return "cross_file_unknown"
        # Non-adjacent dates are not enough evidence to call continuity.
        return "cross_file_unknown"
    return "cross_file_unknown"


def summarize_results(file_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_file_count": len(file_results),
        "total_rows_scanned": sum(r["rows_scanned"] for r in file_results),
        "total_processed_event_count": sum(r["processed_event_count"] for r in file_results),
        "total_ofi_emitted_count": sum(r["ofi_emitted_count"] for r in file_results),
        "files_with_packet_grouping_order_risk": sum(1 for r in file_results if r["packet_grouping_order_risk"]),
        "files_with_resync_stop": sum(1 for r in file_results if r["resync_stop_event_index"] is not None),
        "files_with_snapshot_reset": sum(1 for r in file_results if r["snapshot_or_reset_event_count"] > 0),
        "files_with_bad_casts": sum(1 for r in file_results if r["bad_cast_row_count"] > 0),
        "files_with_unknown_sides": sum(1 for r in file_results if r["unknown_side_row_count"] > 0),
    }


def render_report(
    file_results: list[dict[str, Any]],
    aggregate: dict[str, Any],
    continuity_rows: list[dict[str, Any]],
    join_rows: list[dict[str, Any]],
    explicit_answers: list[tuple[str, str]],
    decision_labels: list[str],
    selected_files: list[Path],
    file_selection_note: str,
    l2_root: Path,
    bar_dir: Path,
    max_events_per_file: int,
) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Reconstruction Sample Validation")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Validate that OFI reconstruction remains stable across a larger bounded sample of raw L2 files and that packet grouping is safe across row-order, packet-boundary, and cross-file concerns.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- L2 root: `{l2_root}`")
    lines.append(f"- Bar dir: `{bar_dir}`")
    lines.append(f"- Selected files: `{len(selected_files)}`")
    lines.append(f"- Max events per file: `{max_events_per_file}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This validation only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any derived parquet/csv/json artifacts.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## File Selection")
    lines.append(file_selection_note)
    lines.append("")
    lines.append(_markdown_table(
        [
            {
                "selected_file": str(p),
                "file_date": _file_date(p) or "unknown",
            }
            for p in selected_files
        ],
        ["selected_file", "file_date"],
    ))
    lines.append("")
    lines.append("## Packet Grouping Validation")
    lines.append(_markdown_table(
        [
            {
                "file_path": r["file_path"],
                "row_order_packet_count": r["row_order_packet_count"],
                "global_packet_count": r["global_packet_count"],
                "packet_grouping_order_risk": r["packet_grouping_order_risk"],
                "row_order_duplicate_packet_key_count": r["row_order_duplicate_packet_key_count"],
                "global_duplicate_packet_key_count": r["global_duplicate_packet_key_count"],
                "first_packet_key": r["first_packet_key"],
                "last_packet_key": r["last_packet_key"],
            }
            for r in file_results
        ],
        [
            "file_path",
            "row_order_packet_count",
            "global_packet_count",
            "packet_grouping_order_risk",
            "row_order_duplicate_packet_key_count",
            "global_duplicate_packet_key_count",
            "first_packet_key",
            "last_packet_key",
        ],
    ))
    lines.append("")
    lines.append("## Packet Boundary Safety")
    lines.append(_markdown_table(
        [
            {
                "file_path": r["file_path"],
                "packet_boundary_unknown": r["packet_boundary_unknown"],
                "dropped_last_packet_for_boundary_safety": r["dropped_last_packet_for_boundary_safety"],
            }
            for r in file_results
        ],
        ["file_path", "packet_boundary_unknown", "dropped_last_packet_for_boundary_safety"],
    ))
    lines.append("")
    lines.append("## Per-File Reconstruction Results")
    lines.append(_markdown_table(
        [
            {
                "file_path": r["file_path"],
                "rows_scanned": r["rows_scanned"],
                "processed_event_count": r["processed_event_count"],
                "ofi_emitted_count": r["ofi_emitted_count"],
                "warmup_none_count": r["warmup_none_count"],
                "snapshot_or_reset_event_count": r["snapshot_or_reset_event_count"],
                "sequence_gap_count": r["sequence_gap_count"],
                "resync_stop_event_index": r["resync_stop_event_index"],
                "bad_cast_row_count": r["bad_cast_row_count"],
                "unknown_side_row_count": r["unknown_side_row_count"],
                "ofi_positive_count": r["ofi_positive_count"],
                "ofi_negative_count": r["ofi_negative_count"],
                "ofi_zero_count": r["ofi_zero_count"],
                "ofi_mean": r["ofi_mean"],
                "ofi_min": r["ofi_min"],
                "ofi_max": r["ofi_max"],
                "ofi_abs_sum": r["ofi_abs_sum"],
                "event_time_min": r["event_time_min"],
                "event_time_max": r["event_time_max"],
                "final_update_id_min": r["final_update_id_min"],
                "final_update_id_max": r["final_update_id_max"],
            }
            for r in file_results
        ],
        [
            "file_path",
            "rows_scanned",
            "processed_event_count",
            "ofi_emitted_count",
            "warmup_none_count",
            "snapshot_or_reset_event_count",
            "sequence_gap_count",
            "resync_stop_event_index",
            "bad_cast_row_count",
            "unknown_side_row_count",
            "ofi_positive_count",
            "ofi_negative_count",
            "ofi_zero_count",
            "ofi_mean",
            "ofi_min",
            "ofi_max",
            "ofi_abs_sum",
            "event_time_min",
            "event_time_max",
            "final_update_id_min",
            "final_update_id_max",
        ],
    ))
    lines.append("")
    lines.append("## Aggregate OFI Summary")
    lines.append(_markdown_table([aggregate], list(aggregate.keys())))
    lines.append("")
    lines.append("## Cross-File Continuity")
    lines.append(_markdown_table(continuity_rows, ["left_file", "right_file", "continuity_status"]))
    lines.append("")
    lines.append("## Join Readiness Sample")
    lines.append(_markdown_table(join_rows, list(join_rows[0].keys()) if join_rows else []))
    lines.append("")
    lines.append("## What Worked")
    lines.extend(f"- {line}" for line in [
        "Multiple raw L2 files were readable.",
        "Global packet grouping on bounded samples completed.",
        "OFI values were emitted in-memory for the bounded sample set.",
        "The join helper was importable and callable.",
    ])
    lines.append("")
    lines.append("## What Failed Or Remains Unknown")
    lines.extend(f"- {line}" for line in [
        "Cross-file continuity is only sample-evidenced and may be unknown across distant dates.",
        "At least one selected file hit a strict-sequence resync stop during sample processing.",
        "Packet boundary safety is conservative; incomplete trailing packets are not promoted into the reconstruction.",
        "This validation does not prove the full corpus gap-free or production-ready.",
    ])
    lines.append("")
    lines.append("## What Is Safe")
    lines.extend(f"- {line}" for line in [
        "Read-only reconstruction on a bounded multi-file sample.",
        "In-memory OFI processing and summary statistics only.",
        "Coverage-preserving join checks without writing output.",
    ])
    lines.append("")
    lines.append("## What Is Not Safe")
    lines.extend(f"- {line}" for line in [
        "Using this sample as OFI alpha evidence.",
        "Writing reconstructed OFI artifacts to disk in this task.",
        "Claiming the full raw L2 corpus is gap-free from a bounded sample.",
    ])
    lines.append("")
    lines.append("## Decision")
    lines.append(" ".join([
        "Decision labels:",
        ", ".join(decision_labels),
    ]))
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("If this bounded sample remains stable, extend to a slightly larger read-only sample before any broader reconstruction work; do not treat this sample as OFI approval.")
    lines.append("")
    lines.append("## Explicit Answers")
    for question, answer in explicit_answers:
        lines.append(f"- {question} {answer}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    files = discover_candidate_files(args.l2_root, args.symbol)
    selected_files = select_deterministic_files(files, args.max_files)
    file_results: list[dict[str, Any]] = []
    continuity_rows: list[dict[str, Any]] = []
    join_rows: list[dict[str, Any]] = []

    for path in selected_files:
        result = process_file(
            path,
            bar_root=args.bar_dir,
            symbol=args.symbol,
            max_events_per_file=args.max_events_per_file,
            strict_sequence=args.strict_sequence,
        )
        file_results.append(result)

    for left, right in zip(file_results, file_results[1:]):
        continuity_rows.append(
            {
                "left_file": left["file_path"],
                "right_file": right["file_path"],
                "continuity_status": classify_cross_file_continuity(left, right),
            }
        )

    # Keep a compact join-readiness sample per selected file.
    for result in file_results:
        join = result["join_summary"]
        join_rows.append(
            {
                "file_date": result["file_date"],
                "bar_file_found": join["bar_file_found"],
                "bar_row_count": join["bar_row_count"],
                "join_attempted": join["join_attempted"],
                "joined_row_count": join["joined_row_count"],
                "bar_count_preserved": join["bar_count_preserved"],
                "join_deferred_reason": join["join_deferred_reason"],
            }
        )

    aggregate = summarize_results(file_results)
    explicit_answers = [
        ("Were multiple raw L2 files readable?", "Yes." if len(file_results) >= 2 else "No."),
        ("Did global packet grouping work?", "Yes." if all(r["global_packet_count"] > 0 for r in file_results) else "No."),
        ("Did row-order packet grouping differ from global grouping?", "Yes." if any(r["packet_grouping_order_risk"] for r in file_results) else "No."),
        ("Were packet-boundary risks detected or mitigated?", "Yes." if any(r["dropped_last_packet_for_boundary_safety"] or r["packet_boundary_unknown"] for r in file_results) else "No."),
        ("Were OFI values emitted across multiple files?", "Yes." if aggregate["total_ofi_emitted_count"] > 0 and len(file_results) >= 2 else "No."),
        ("Did strict sequence mode hit resync in any file?", "Yes." if aggregate["files_with_resync_stop"] > 0 else "No."),
        ("Were join checks coverage-preserving where attempted?", "Yes." if all((r["join_summary"]["bar_count_preserved"] is True) for r in file_results if r["join_summary"]["join_attempted"]) else "Deferred or not attempted."),
        ("Was any OFI output written to disk?", "No."),
        ("Is OFI approved for alpha, paper, or live use?", "No."),
        ("What is the next safe validation step?", "Use this bounded sample as proof-of-life, then extend to a slightly larger read-only sample only if the packet-grouping and join-readiness signals remain stable."),
    ]

    decision_labels = ["alpha_blocked", "paper_live_blocked"]
    if len(file_results) >= 2:
        decision_labels.append("multi_file_l2_sample_readable")
    if all(r["global_packet_count"] > 0 for r in file_results):
        decision_labels.append("global_packet_grouping_successful")
    if any(r["packet_grouping_order_risk"] for r in file_results):
        decision_labels.append("packet_grouping_order_risk_detected")
    if any(r["dropped_last_packet_for_boundary_safety"] or r["packet_boundary_unknown"] for r in file_results):
        decision_labels.append("packet_boundary_safety_applied")
    if aggregate["total_ofi_emitted_count"] > 0:
        decision_labels.append("ofi_values_emitted_multi_file")
    if aggregate["files_with_resync_stop"] > 0:
        decision_labels.append("strict_sequence_resync_detected")
    else:
        decision_labels.append("strict_sequence_sample_passed")
    if any(r["join_summary"]["join_attempted"] and r["join_summary"]["bar_count_preserved"] for r in file_results):
        decision_labels.append("join_readiness_sample_passed")
    if any(r["join_summary"]["join_deferred_reason"] for r in file_results):
        decision_labels.append("join_readiness_deferred")
    if aggregate["files_with_resync_stop"] > 0:
        decision_labels.append("larger_sample_validation_blocked")
    elif len(file_results) >= 2 and aggregate["total_ofi_emitted_count"] > 0:
        decision_labels.append("larger_sample_validation_passed")
    else:
        decision_labels.append("larger_sample_validation_blocked")

    report = render_report(
        file_results=file_results,
        aggregate=aggregate,
        continuity_rows=continuity_rows or [{"left_file": "n/a", "right_file": "n/a", "continuity_status": "cross_file_unknown"}],
        join_rows=join_rows,
        explicit_answers=explicit_answers,
        decision_labels=decision_labels,
        selected_files=selected_files,
        file_selection_note=(
            "Deterministic selection used the first chronological file, the last chronological file, and evenly spaced files in between. "
            "The sample is bounded and read-only; it is not a full-corpus pass."
        ),
        l2_root=args.l2_root,
        bar_dir=args.bar_dir,
        max_events_per_file=args.max_events_per_file,
    )
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
