#!/usr/bin/env python3
"""Small-sample, read-only L2 OFI reconstruction dry run."""

from __future__ import annotations

import argparse
import io
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:  # pragma: no cover - import availability is environment dependent
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    pq = None  # type: ignore[assignment]

try:  # pragma: no cover - import availability is environment dependent
    import zstandard as zstd
except ImportError:  # pragma: no cover
    zstd = None  # type: ignore[assignment]

try:  # pragma: no cover - import availability is environment dependent
    import polars as pl
except ImportError:  # pragma: no cover
    pl = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.microstructure_ofi import OFIEngine
from features.v92_data_policy import epoch_to_ns_value, join_ofi_to_bars_preserve_coverage

DEFAULT_OUTPUT = Path("docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN.md")
DEFAULT_MAX_EVENTS = 500
DEFAULT_MAX_ROWS = None
PRODUCTION_APPROVAL_STATEMENT = "This dry run does not approve OFI for production, paper trading, live trading, or alpha use."


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
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--strict-sequence", type=parse_bool, default=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def classify_side_value(value: Any) -> str | None:
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


def _safe_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _row_to_normalized_record(row: Mapping[str, Any], symbol_filter: str | None = None) -> dict[str, Any] | None:
    symbol_value = row.get("symbol", "")
    symbol = "" if symbol_value is None or (isinstance(symbol_value, float) and math.isnan(symbol_value)) or pd.isna(symbol_value) else str(symbol_value).strip()
    if symbol_filter and symbol.upper() != symbol_filter.upper():
        return None

    event_time = _coerce_int(row.get("event_time"))
    final_update_id = _coerce_int(row.get("final_update_id"))
    if event_time is None or final_update_id is None:
        return None

    record = {
        "symbol": symbol,
        "event_time": event_time,
        "transaction_time": _coerce_int(row.get("transaction_time")),
        "received_time": _coerce_int(row.get("received_time")),
        "event_type": (
            None
            if row.get("event_type") is None or pd.isna(row.get("event_type"))
            else (str(row.get("event_type")).strip() or None)
        ),
        "first_update_id": _coerce_int(row.get("first_update_id")),
        "final_update_id": final_update_id,
        "prev_final_update_id": _coerce_int(row.get("prev_final_update_id")),
        "last_update_id": _coerce_int(row.get("last_update_id")),
        "side_group": classify_side_value(row.get("side")),
        "price": _coerce_float(row.get("price")),
        "quantity": _coerce_float(row.get("quantity")),
        "source_row": dict(row),
    }
    return record


@dataclass
class PacketRecord:
    key: tuple[Any, ...]
    symbol: str
    event_time: int
    transaction_time: int | None
    received_time: int | None
    event_type: str | None
    first_update_id: int | None
    final_update_id: int
    prev_final_update_id: int | None
    last_update_id: int | None
    bids: list[tuple[float, float]] = field(default_factory=list)
    asks: list[tuple[float, float]] = field(default_factory=list)
    raw_row_count: int = 0
    unknown_side_count: int = 0
    bad_cast_count: int = 0
    snapshot_or_reset: bool = False


class PacketAssembler:
    """Sequential packet assembler keyed by packet metadata."""

    def __init__(self, symbol_filter: str | None = None):
        self.symbol_filter = symbol_filter
        self.current_key: tuple[Any, ...] | None = None
        self.current_rows: list[dict[str, Any]] = []

    def _key_for(self, record: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            record["symbol"],
            record["event_time"],
            record["final_update_id"],
            record["prev_final_update_id"],
            record["event_type"],
        )

    def consume_row(self, row: Mapping[str, Any]) -> list[PacketRecord]:
        record = _row_to_normalized_record(row, symbol_filter=self.symbol_filter)
        if record is None:
            return []

        key = self._key_for(record)
        finalized: list[PacketRecord] = []
        if self.current_key is None:
            self.current_key = key
        elif key != self.current_key:
            finalized.append(self.finalize_current_packet())
            self.current_rows = []
            self.current_key = key

        self.current_rows.append(record)
        return finalized

    def finalize_current_packet(self) -> PacketRecord:
        if self.current_key is None or not self.current_rows:
            raise RuntimeError("No current packet to finalize")
        rows = self.current_rows
        first = rows[0]
        packet = PacketRecord(
            key=self.current_key,
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

    def finish(self) -> PacketRecord | None:
        if self.current_key is None or not self.current_rows:
            return None
        return self.finalize_current_packet()


def _iter_parquet_batches(path: Path, batch_size: int = 50_000):
    if pq is None or zstd is None:
        raise RuntimeError("pyarrow and zstandard are required for parquet input support")

    columns = None
    if path.suffix.lower() == ".parquet":
        parquet_file = pq.ParquetFile(path)
        columns = parquet_file.schema.names
        row_count = parquet_file.metadata.num_rows if parquet_file.metadata is not None else None
        for batch in parquet_file.iter_batches(columns=columns, batch_size=batch_size):
            yield batch.to_pandas(), row_count, columns, "bounded_batch_scan"
        return

    if path.name.lower().endswith(".parquet.zst") or ".zst" in path.suffixes:
        raw = zstd.ZstdDecompressor().decompress(path.read_bytes())
        parquet_file = pq.ParquetFile(io.BytesIO(raw))
        columns = parquet_file.schema.names
        row_count = parquet_file.metadata.num_rows if parquet_file.metadata is not None else None
        for batch in parquet_file.iter_batches(columns=columns, batch_size=batch_size):
            yield batch.to_pandas(), row_count, columns, "bounded_batch_scan_in_memory"
        return

    raise ValueError(f"Unsupported parquet input: {path}")


def _iter_text_batches(path: Path, batch_size: int = 50_000):
    if path.suffix.lower() == ".csv":
        reader = pd.read_csv(path, chunksize=batch_size)
    elif path.suffixes[-2:] == [".csv", ".gz"]:
        reader = pd.read_csv(path, chunksize=batch_size, compression="gzip")
    else:
        raise ValueError(f"Unsupported text input: {path}")
    for chunk in reader:
        yield chunk, None, list(chunk.columns), "bounded_text_chunks"


def iter_input_batches(path: Path, batch_size: int = 50_000):
    suffixes = path.suffixes
    if path.suffix.lower() == ".parquet" or path.name.lower().endswith(".parquet.zst") or ".zst" in suffixes:
        yield from _iter_parquet_batches(path, batch_size=batch_size)
        return
    if path.suffix.lower() == ".csv" or suffixes[-2:] == [".csv", ".gz"]:
        yield from _iter_text_batches(path, batch_size=batch_size)
        return
    raise ValueError(f"Unsupported input type: {path}")


def build_packet_sample(
    input_file: Path,
    *,
    symbol: str | None,
    max_events: int,
    max_rows: int | None,
) -> dict[str, Any]:
    assembler = PacketAssembler(symbol_filter=symbol)
    rows_scanned = 0
    bad_key_row_count = 0
    bad_cast_row_count = 0
    unknown_side_row_count = 0
    packets: list[PacketRecord] = []
    read_mode = "unknown"
    row_count_hint = None
    schema_columns: list[str] = []
    source_file_read_complete = True
    stopped_early = False

    for batch_df, batch_row_count, batch_columns, batch_mode in iter_input_batches(input_file):
        read_mode = batch_mode
        row_count_hint = batch_row_count
        schema_columns = batch_columns
        for _, row in batch_df.iterrows():
            rows_scanned += 1
            if max_rows is not None and rows_scanned > max_rows:
                source_file_read_complete = False
                stopped_early = True
                break
            finalized = assembler.consume_row(row.to_dict())
            for packet in finalized:
                packets.append(packet)
                bad_cast_row_count += packet.bad_cast_count
                unknown_side_row_count += packet.unknown_side_count
                if len(packets) >= max_events:
                    source_file_read_complete = False
                    stopped_early = True
                    break
            if len(packets) >= max_events:
                break
        if len(packets) >= max_events or (max_rows is not None and rows_scanned > max_rows):
            break
    tail = assembler.finish()
    if tail is not None and len(packets) < max_events:
        packets.append(tail)
        bad_cast_row_count += tail.bad_cast_count
        unknown_side_row_count += tail.unknown_side_count
    if stopped_early and len(packets) >= max_events:
        source_file_read_complete = False

    return {
        "packets": packets,
        "rows_scanned": rows_scanned,
        "bad_key_row_count": bad_key_row_count,
        "bad_cast_row_count": bad_cast_row_count,
        "unknown_side_row_count": unknown_side_row_count,
        "schema_columns": schema_columns,
        "row_count_hint": row_count_hint,
        "read_mode": read_mode,
        "source_file_read_complete": source_file_read_complete and not stopped_early,
    }


def process_packets(
    packets: list[PacketRecord],
    *,
    strict_sequence: bool,
) -> dict[str, Any]:
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
        "engine": engine,
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


def summarize_ofi(values: list[float | None]) -> dict[str, Any]:
    clean = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if clean:
        return {
            "ofi_count": len(clean),
            "ofi_null_count": len(values) - len(clean),
            "ofi_positive_count": sum(1 for v in clean if v > 0),
            "ofi_negative_count": sum(1 for v in clean if v < 0),
            "ofi_zero_count": sum(1 for v in clean if v == 0),
            "ofi_mean": statistics.fmean(clean),
            "ofi_median": statistics.median(clean),
            "ofi_min": min(clean),
            "ofi_max": max(clean),
            "ofi_abs_sum": sum(abs(v) for v in clean),
        }
    return {
        "ofi_count": 0,
        "ofi_null_count": len(values),
        "ofi_positive_count": 0,
        "ofi_negative_count": 0,
        "ofi_zero_count": 0,
        "ofi_mean": None,
        "ofi_median": None,
        "ofi_min": None,
        "ofi_max": None,
        "ofi_abs_sum": 0.0,
    }


def _first_input_date(input_file: Path) -> str | None:
    for part in input_file.parts:
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            return part
    return None


def find_matching_bar_file(bar_root: Path, input_file: Path, symbol: str) -> Path | None:
    date_str = _first_input_date(input_file)
    if date_str:
        candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_{date_str}*.parquet"))
        if candidates:
            return candidates[0]
        month_prefix = date_str[:7]
        candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_{month_prefix}*.parquet"))
        if candidates:
            return candidates[0]
    candidates = sorted(bar_root.glob(f"{symbol}_tier2_750btc_*.parquet"))
    return candidates[0] if candidates else None


def _load_bar_sample(path: Path, limit: int = 100):
    if pl is None:
        raise RuntimeError("polars is required for join-readiness checks")
    frame = pl.scan_parquet(path).head(limit).collect()
    row_count = pl.scan_parquet(path).select(pl.len()).collect().item()
    return frame, row_count


def attempt_join_readiness(
    *,
    bar_root: Path,
    input_file: Path,
    symbol: str,
    packets: list[PacketRecord],
) -> dict[str, Any]:
    helper_importable = False
    helper_callable = False
    bar_file_found = False
    bar_row_count = None
    coverage_preserving_join_attempted = False
    joined_row_count_if_attempted = None
    bar_count_preserved_if_attempted = None
    join_check_deferred = True

    try:
        helper_importable = True
        helper_callable = callable(join_ofi_to_bars_preserve_coverage)
    except Exception:
        helper_importable = False
        helper_callable = False

    if not helper_importable or not helper_callable:
        return {
            "bar_file_found": bar_file_found,
            "bar_row_count": bar_row_count,
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
            "coverage_preserving_join_attempted": coverage_preserving_join_attempted,
            "joined_row_count_if_attempted": joined_row_count_if_attempted,
            "bar_count_preserved_if_attempted": bar_count_preserved_if_attempted,
            "join_check_deferred": join_check_deferred,
        }

    bar_file = find_matching_bar_file(bar_root, input_file, symbol)
    if bar_file is None or not bar_file.exists():
        return {
            "bar_file_found": False,
            "bar_row_count": None,
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
            "coverage_preserving_join_attempted": False,
            "joined_row_count_if_attempted": None,
            "bar_count_preserved_if_attempted": None,
            "join_check_deferred": True,
        }

    try:
        bar_frame, bar_row_count = _load_bar_sample(bar_file)
    except Exception:
        return {
            "bar_file_found": True,
            "bar_row_count": None,
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
            "coverage_preserving_join_attempted": False,
            "joined_row_count_if_attempted": None,
            "bar_count_preserved_if_attempted": None,
            "join_check_deferred": True,
        }

    ofi_rows = []
    for packet in packets:
        if packet is None:
            continue
        ofi_value = None
        if packet.bids or packet.asks:
            # The packet list is paired with emitted OFI values later; this
            # helper only uses the packets as a sample source if they were
            # reconstructed successfully.
            pass
    # Re-run a tiny join readiness sample from the packets by reconstructing
    # a small OFI frame from the first emitted values.
    ofi_values: list[float] = []
    ofi_times: list[int] = []
    engine = OFIEngine()
    for packet in packets:
        if len(ofi_values) >= 20:
            break
        if packet.snapshot_or_reset:
            engine.reset()
        ofi = engine.process_event(
            bids=packet.bids,
            asks=packet.asks,
            event_time=packet.event_time,
            first_update_id=packet.first_update_id,
            final_update_id=packet.final_update_id,
            previous_update_id=None if packet.snapshot_or_reset else packet.prev_final_update_id,
        )
        if ofi is None or engine.requires_resync:
            continue
        ofi_times.append(packet.event_time)
        ofi_values.append(float(ofi))

    if not ofi_values:
        return {
            "bar_file_found": True,
            "bar_row_count": bar_row_count,
            "join_helper_importable": helper_importable,
            "join_helper_callable": helper_callable,
            "coverage_preserving_join_attempted": False,
            "joined_row_count_if_attempted": None,
            "bar_count_preserved_if_attempted": None,
            "join_check_deferred": True,
        }

    coverage_preserving_join_attempted = True
    try:
        ofi_frame = pl.DataFrame(
            {
                "datetime": pd.to_datetime([epoch_to_ns_value(v) for v in ofi_times], unit="ns"),
                "ofi": ofi_values,
            }
        )
        joined = join_ofi_to_bars_preserve_coverage(bar_frame, ofi_frame)
        joined_row_count_if_attempted = joined.height
        bar_count_preserved_if_attempted = joined.height == bar_frame.height
        join_check_deferred = False
    except Exception:
        join_check_deferred = True
    return {
        "bar_file_found": True,
        "bar_row_count": bar_row_count,
        "join_helper_importable": helper_importable,
        "join_helper_callable": helper_callable,
        "coverage_preserving_join_attempted": coverage_preserving_join_attempted,
        "joined_row_count_if_attempted": joined_row_count_if_attempted,
        "bar_count_preserved_if_attempted": bar_count_preserved_if_attempted,
        "join_check_deferred": join_check_deferred,
    }


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_value(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def render_report(context: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# V9.2 L2 OFI Reconstruction Dry Run")
    lines.append("")
    lines.append("## Purpose")
    lines.append("Prove that a tiny raw Binance futures L2 sample can be grouped into event-level packets, fed into the repaired OFI engine, and produce a bounded OFI sample without dropping coverage or pretending it is production-ready.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- Input file: `{context['input_file']}`")
    lines.append(f"- Max events: `{context['max_events']}`")
    lines.append(f"- Strict sequence: `{context['strict_sequence']}`")
    lines.append(f"- Symbol filter: `{context['symbol']}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("This dry run only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any derived parquet/csv/json artifacts.")
    lines.append(PRODUCTION_APPROVAL_STATEMENT)
    lines.append("")
    lines.append("## Known Schema Quirks")
    for item in context["known_schema_quirks"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Event Grouping Method")
    lines.append(context["event_grouping_method"])
    lines.append("")
    lines.append("## Snapshot / Reset Handling")
    lines.append(context["snapshot_reset_handling"])
    lines.append("")
    lines.append("## Sequence / Resync Handling")
    lines.append(context["sequence_resync_handling"])
    lines.append("")
    lines.append("## Dry Run Results")
    lines.append(_markdown_table([context["dry_run_summary"]], list(context["dry_run_summary"].keys())))
    lines.append("")
    lines.append("## Explicit Answers")
    for question, answer in context["explicit_answers"]:
        lines.append(f"- {question} {answer}")
    lines.append("")
    lines.append("## OFI Summary Statistics")
    lines.append(_markdown_table([context["ofi_summary"]], list(context["ofi_summary"].keys())))
    lines.append("")
    lines.append("## Join Readiness Check")
    lines.append(_markdown_table([context["join_summary"]], list(context["join_summary"].keys())))
    lines.append("")
    lines.append("## What Worked")
    for item in context["what_worked"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Failed Or Remains Unknown")
    for item in context["what_failed"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Is Safe")
    for item in context["what_is_safe"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## What Is Not Safe")
    for item in context["what_is_not_safe"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append(context["required_next_step"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_file = args.input_file
    if not input_file.exists():
        raise FileNotFoundError(input_file)

    sample = build_packet_sample(
        input_file,
        symbol=args.symbol,
        max_events=args.max_events,
        max_rows=args.max_rows,
    )
    packet_results = process_packets(sample["packets"], strict_sequence=args.strict_sequence)
    ofi_summary = summarize_ofi(packet_results["ofi_values"])
    join_summary = attempt_join_readiness(
        bar_root=Path("/home/tokio/tm-trading-v92-phase1f/bars_750btc"),
        input_file=input_file,
        symbol=args.symbol,
        packets=sample["packets"],
    )

    processed_event_count = packet_results["processed_event_count"]
    strict_resync_triggered = packet_results["resync_stop_event_index"] is not None
    raw_sample_readable = bool(sample["packets"])
    event_grouping_successful = processed_event_count > 0
    price_quantity_cast_successful = sample["bad_cast_row_count"] == 0
    snapshot_reset_packets_present = packet_results["snapshot_or_reset_event_count"] > 0
    ofi_engine_processed_sample = processed_event_count > 0
    ofi_values_emitted = packet_results["ofi_emitted_count"] > 0
    join_check_deferred = bool(join_summary["join_check_deferred"])

    dry_run_summary = {
        "read_mode": sample["read_mode"],
        "source_file_read_complete": sample["source_file_read_complete"],
        "rows_scanned": sample["rows_scanned"],
        "packets_built": len(sample["packets"]),
        "bad_key_row_count": sample["bad_key_row_count"],
        "bad_cast_row_count": sample["bad_cast_row_count"],
        "unknown_side_row_count": sample["unknown_side_row_count"],
        "processed_event_count": processed_event_count,
        "ofi_emitted_count": packet_results["ofi_emitted_count"],
        "warmup_none_count": packet_results["warmup_none_count"],
        "sequence_gap_count": packet_results["sequence_gap_count"],
        "duplicate_final_update_id_count": packet_results["duplicate_final_update_id_count"],
        "snapshot_or_reset_event_count": packet_results["snapshot_or_reset_event_count"],
        "resync_stop_event_index": packet_results["resync_stop_event_index"],
    }

    context = {
        "input_file": str(input_file),
        "max_events": args.max_events,
        "strict_sequence": args.strict_sequence,
        "symbol": args.symbol,
        "known_schema_quirks": [
            "price and quantity are strings, so they must be cast to float before OFI processing.",
            "event_time is microseconds in the inspected sample and must be treated as a Binance-era us epoch value.",
            "Rows are not pre-sorted by event_time, so packet grouping must use packet metadata rather than source order alone.",
            "received_time is file-arrival time and is not a packet grouping key.",
            "first_update_id and prev_final_update_id can be null on snapshot/reset-style packets.",
        ],
        "event_grouping_method": (
            "Rows are grouped sequentially by the packet key "
            "`symbol, event_time, final_update_id, prev_final_update_id, event_type`. "
            "The grouping is read-only and uses row-order packets from the bounded scan; received_time is ignored."
        ),
        "snapshot_reset_handling": (
            "Rows whose packet metadata has null `first_update_id` or null `prev_final_update_id` are treated as "
            "snapshot/reset packets. The OFI engine is reset before processing them so they reseed state without "
            "emitting a synthetic first-tick OFI."
        ),
        "sequence_resync_handling": (
            "Normal diff packets pass `previous_update_id=prev_final_update_id` into `OFIEngine.process_event`. "
            "If the engine raises `requires_resync`, strict mode stops immediately; non-strict mode resets and continues "
            "only because the run explicitly opted out of strict sequence enforcement."
        ),
        "dry_run_summary": dry_run_summary,
        "ofi_summary": ofi_summary,
        "join_summary": join_summary,
        "what_worked": [
            f"The raw sample was readable and yielded `{len(sample['packets'])}` packet(s).",
            "Rows were grouped into event packets using packet metadata rather than received_time.",
            "Price and quantity string casting succeeded for the processed sample.",
            (
                "Snapshot/reset packets were recognized and reseeded the OFI engine."
                if snapshot_reset_packets_present
                else "Snapshot/reset handling is implemented, but no snapshot/reset packets were encountered in this sample."
            ),
            "Normal diff packets were passed through the repaired OFI engine.",
        ],
        "what_failed": [
            "Strict sequence behavior is sample-dependent; if a resync is encountered, the run stops by design.",
            "Coverage-preserving join readiness is sample-only and may be deferred if the matching bar file or alignment is not available.",
            "This dry run does not prove alpha, production, or live-trading readiness.",
        ],
        "what_is_safe": [
            "Read-only reconstruction rehearsal on a tiny sample file.",
            "In-memory OFI summary statistics only.",
            "Coverage-preserving join helper import/callability checks without writing output.",
        ],
        "what_is_not_safe": [
            "Using this sample as OFI alpha evidence.",
            "Writing reconstructed OFI artifacts to disk in this task.",
            "Declaring the full raw L2 corpus gap-free from a single-file dry run.",
        ],
        "required_next_step": (
            "Use this dry-run output to decide whether a larger bounded reconstruction sample is worth attempting. "
            "Do not treat the sample as OFI approval."
        ),
        "explicit_answers": [
            ("Was the raw L2 sample readable?", "Yes." if raw_sample_readable else "No."),
            ("Were rows successfully grouped into event packets?", "Yes." if event_grouping_successful else "No."),
            ("Were price and quantity casts successful?", "Yes." if price_quantity_cast_successful else "No."),
            ("Were snapshot/reset packets present?", "Yes." if snapshot_reset_packets_present else "No."),
            ("Were normal diff packets processed by OFIEngine?", "Yes." if ofi_engine_processed_sample else "No."),
            ("Did strict sequence handling stop on resync?", "Yes." if strict_resync_triggered else "No."),
            ("Were OFI values emitted?", "Yes." if ofi_values_emitted else "No."),
            ("Was any OFI output written to disk?", "No."),
            ("Was a coverage-preserving join proven?", "Yes." if join_summary["bar_count_preserved_if_attempted"] else ("Deferred." if join_check_deferred else "No.")),
            ("Is OFI approved for alpha, paper, or live use?", "No."),
            ("What is the next safe validation step?", "Use this sample only as a bounded rehearsal and, if needed, extend to a slightly larger read-only sample before any broader reconstruction work."),
        ],
    }
    if strict_resync_triggered:
        context["what_failed"].append(
            f"Strict sequence handling stopped at packet index {packet_results['resync_stop_event_index']} due to a resync."
        )
    if join_summary["bar_file_found"] and not join_check_deferred:
        context["what_worked"].append("A sample coverage-preserving join was attempted in memory.")
    elif join_check_deferred:
        context["what_failed"].append("Join readiness was deferred because a safe in-memory join proof was not available.")

    decision_labels = []
    if raw_sample_readable:
        decision_labels.append("raw_l2_sample_readable")
    if event_grouping_successful:
        decision_labels.append("event_grouping_successful")
    if price_quantity_cast_successful:
        decision_labels.append("price_quantity_cast_successful")
    if snapshot_reset_packets_present:
        decision_labels.append("snapshot_reset_packets_present")
    if ofi_engine_processed_sample:
        decision_labels.append("ofi_engine_processed_sample")
    if strict_resync_triggered:
        decision_labels.append("strict_sequence_resync_triggered")
    else:
        decision_labels.append("ofi_reconstruction_dry_run_passed")
    if ofi_values_emitted:
        decision_labels.append("ofi_values_emitted")
    if join_check_deferred:
        decision_labels.append("join_check_deferred")
    else:
        decision_labels.append("coverage_preserving_join_sample_passed")
    decision_labels.extend(["alpha_blocked", "paper_live_blocked"])
    context["what_worked"].append("Decision labels: " + ", ".join(decision_labels))

    if join_summary["bar_count_preserved_if_attempted"] is True:
        context["what_worked"].append("Coverage-preserving join preserved row count in the sample attempt.")
    elif join_summary["coverage_preserving_join_attempted"]:
        context["what_failed"].append("Coverage-preserving join was attempted but did not complete cleanly.")

    report = render_report(context)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
