from __future__ import annotations

from pathlib import Path

import pytest

from features.l2_ofi_segmented_reconstruction import (
    L2Packet,
    L2Segment,
    packet_sort_key,
    is_snapshot_or_reset,
    is_source_gap,
    segment_packets,
    run_segment_with_ofi_engine,
)


def _packet(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    first_update_id: int | None = 1,
    transaction_time: int | None = None,
    received_time: int | None = None,
    event_type: str = "depthUpdate",
    bids: tuple[tuple[float, float], ...] = ((100.0, 1.0),),
    asks: tuple[tuple[float, float], ...] = ((101.0, 1.0),),
) -> L2Packet:
    return L2Packet(
        symbol="BTCUSDT",
        event_type=event_type,
        event_time=event_time,
        transaction_time=transaction_time,
        received_time=received_time,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        bids=bids,
        asks=asks,
    )


def test_packet_sort_key_uses_transaction_time_before_final_update_id():
    packets = [
        _packet(event_time=2, transaction_time=20, final_update_id=1, prev_final_update_id=0),
        _packet(event_time=1, transaction_time=10, final_update_id=99, prev_final_update_id=98),
    ]
    ordered = sorted(packets, key=packet_sort_key)
    assert ordered[0].transaction_time == 10
    assert ordered[1].transaction_time == 20


def test_packet_sort_key_falls_back_when_transaction_time_is_none():
    packets = [
        _packet(event_time=3, transaction_time=None, final_update_id=20, prev_final_update_id=19),
        _packet(event_time=1, transaction_time=None, final_update_id=10, prev_final_update_id=9),
    ]
    ordered = sorted(packets, key=packet_sort_key)
    assert ordered[0].event_time == 1
    assert ordered[1].event_time == 3


def test_is_snapshot_or_reset_detects_null_first_update_id():
    assert is_snapshot_or_reset(_packet(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=None))


def test_is_snapshot_or_reset_detects_null_prev_final_update_id():
    assert is_snapshot_or_reset(_packet(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None))


def test_is_source_gap_detects_true_source_gap():
    previous = _packet(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=9)
    current = _packet(event_time=2, final_update_id=20, prev_final_update_id=12, first_update_id=10)
    assert is_source_gap(previous, current)


def test_is_source_gap_ignores_snapshot_reset_packets():
    previous = _packet(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=9)
    current = _packet(event_time=2, final_update_id=20, prev_final_update_id=None, first_update_id=None)
    assert is_source_gap(previous, current) is False


def test_segment_packets_detects_boundaries_and_preserves_order():
    packets = [
        _packet(event_time=3, transaction_time=30, final_update_id=30, prev_final_update_id=999, first_update_id=11),
        _packet(event_time=1, transaction_time=10, final_update_id=10, prev_final_update_id=9, first_update_id=9),
        _packet(event_time=2, transaction_time=20, final_update_id=20, prev_final_update_id=10, first_update_id=10),
        _packet(event_time=4, transaction_time=40, final_update_id=40, prev_final_update_id=None, first_update_id=None),
        _packet(event_time=5, transaction_time=50, final_update_id=50, prev_final_update_id=40, first_update_id=40),
    ]
    segments = segment_packets(packets)
    assert segments[0].start_packet_index == 1
    assert segments[0].start_reason == "file_start"
    assert segments[0].packets[0].final_update_id == 10
    assert len(segments) == 3
    assert segments[0].boundary_reason == "source_sequence_gap"
    assert segments[1].boundary_reason == "snapshot_or_reset"
    assert segments[2].boundary_reason == "sample_end"
    assert segments[1].packets[0].final_update_id == 30
    assert segments[2].packets[0].prev_final_update_id is None


def test_segment_packets_never_carries_packets_across_gap_boundary():
    packets = [
        _packet(event_time=1, transaction_time=10, final_update_id=10, prev_final_update_id=9, first_update_id=9),
        _packet(event_time=2, transaction_time=20, final_update_id=20, prev_final_update_id=10, first_update_id=10),
        _packet(event_time=3, transaction_time=30, final_update_id=30, prev_final_update_id=999, first_update_id=11),
    ]
    segments = segment_packets(packets)
    assert len(segments) == 2
    assert segments[0].packets[-1].final_update_id == 20
    assert segments[1].packets[0].final_update_id == 30


def test_run_segment_with_ofi_engine_instantiates_fresh_engine_per_segment(monkeypatch: pytest.MonkeyPatch):
    packets = segment_packets([
        _packet(event_time=1, transaction_time=10, final_update_id=10, prev_final_update_id=9, first_update_id=9),
        _packet(event_time=2, transaction_time=20, final_update_id=20, prev_final_update_id=10, first_update_id=10),
    ])

    class DummyEngine:
        instances: list["DummyEngine"] = []

        def __init__(self, max_levels: int = 50):
            self.max_levels = max_levels
            self.requires_resync = False
            self.last_update_id = None
            DummyEngine.instances.append(self)

        def reset(self):
            self.requires_resync = False
            self.last_update_id = None

        def process_event(self, **kwargs):
            self.last_update_id = kwargs.get("final_update_id")
            return None if self.last_update_id == 10 else 1.0

    monkeypatch.setattr("features.l2_ofi_segmented_reconstruction.OFIEngine", DummyEngine)
    result_1 = run_segment_with_ofi_engine(packets[0])
    result_2 = run_segment_with_ofi_engine(packets[0])
    assert len(DummyEngine.instances) == 2
    assert result_1.packet_count == len(packets[0].packets)
    assert result_2.packet_count == len(packets[0].packets)


def test_one_packet_segment_returns_no_meaningful_ofi_beyond_warmup():
    segment = L2Segment(
        segment_id=1,
        start_packet_index=1,
        end_packet_index=1,
        start_reason="file_start",
        boundary_reason="sample_end",
        packets=(
            _packet(event_time=1, transaction_time=10, final_update_id=10, prev_final_update_id=9, first_update_id=9),
        ),
    )
    result = run_segment_with_ofi_engine(segment)
    assert result.ofi_emitted_count == 0
    assert result.warmup_none_count == 1
    assert result.clean is True


def test_report_statement_present():
    doc = Path("/home/tokio/tm-trading-v92-core/docs/v92_L2_OFI_SEGMENTED_RECONSTRUCTION_POLICY.md")
    assert "This policy module does not approve OFI for production, paper trading, live trading, or alpha use." in doc.read_text(encoding="utf-8")
