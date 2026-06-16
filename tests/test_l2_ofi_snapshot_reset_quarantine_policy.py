from __future__ import annotations

from pathlib import Path

from features.microstructure_ofi import OFIEngine
from features.l2_ofi_segmented_reconstruction import (
    L2Packet,
    L2Segment,
    SegmentRunResult,
    segment_packets,
    run_segment_with_ofi_engine,
    summarize_segments,
)
import scripts.validate_l2_ofi_snapshot_reset_quarantine_policy as script


def _packet(
    *,
    event_time: int,
    final_update_id: int,
    prev_final_update_id: int | None,
    first_update_id: int | None,
    transaction_time: int | None = 10,
    received_time: int | None = 20,
    bids=((100.0, 1.0),),
    asks=(),
) -> L2Packet:
    return L2Packet(
        symbol="BTCUSDT",
        event_type="depthUpdate",
        event_time=event_time,
        transaction_time=transaction_time,
        received_time=received_time,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        bids=bids,
        asks=asks,
    )


def test_valid_snapshot_bridge_event_keeps_segment_clean_and_suppresses_bridge_ofi(monkeypatch):
    packets = [
        _packet(event_time=1, final_update_id=100, prev_final_update_id=None, first_update_id=None),
        _packet(event_time=2, final_update_id=105, prev_final_update_id=90, first_update_id=95),
        _packet(event_time=3, final_update_id=110, prev_final_update_id=105, first_update_id=106),
    ]

    class DummyEngine:
        instances: list["DummyEngine"] = []

        def __init__(self, max_levels: int = 50):
            self.max_levels = max_levels
            self.requires_resync = False
            self.last_update_id = None
            self.calls: list[dict[str, object]] = []
            DummyEngine.instances.append(self)

        def reset(self):
            self.requires_resync = False
            self.last_update_id = None

        def process_event(self, **kwargs):
            self.calls.append(kwargs)
            self.last_update_id = kwargs["final_update_id"]
            if kwargs["first_update_id"] is None:
                return None
            if kwargs["previous_update_id"] is None and kwargs["final_update_id"] == 105:
                return 9.0
            return 1.0

    monkeypatch.setattr("features.l2_ofi_segmented_reconstruction.OFIEngine", DummyEngine)

    segments = segment_packets(packets)
    assert len(segments) == 1
    assert segments[0].quarantined is False

    result = run_segment_with_ofi_engine(segments[0])
    assert result.clean is True
    assert result.quarantined is False
    assert result.snapshot_reset_observed_count == 1
    assert result.snapshot_reset_clean_seed_count == 1
    assert result.snapshot_bridge_event_count == 1
    assert result.ofi_suppressed_due_to_snapshot_bridge_count == 1
    assert result.ofi_emitted_count == 1
    assert result.snapshot_reset_chain_failure_count == 0
    assert result.quarantined_segment_count == 0


def test_invalid_snapshot_bridge_event_quarantines_segment(monkeypatch):
    packets = [
        _packet(event_time=1, final_update_id=100, prev_final_update_id=None, first_update_id=None, transaction_time=1),
        _packet(event_time=2, final_update_id=90, prev_final_update_id=80, first_update_id=70, transaction_time=2),
        _packet(event_time=3, final_update_id=110, prev_final_update_id=90, first_update_id=91, transaction_time=3),
    ]

    class DummyEngine:
        instances: list["DummyEngine"] = []

        def __init__(self, max_levels: int = 50):
            self.max_levels = max_levels
            self.requires_resync = False
            self.last_update_id = None
            self.calls: list[dict[str, object]] = []
            DummyEngine.instances.append(self)

        def reset(self):
            self.requires_resync = False
            self.last_update_id = None

        def process_event(self, **kwargs):
            self.calls.append(kwargs)
            self.last_update_id = kwargs["final_update_id"]
            return None

    monkeypatch.setattr("features.l2_ofi_segmented_reconstruction.OFIEngine", DummyEngine)

    segments = segment_packets(packets)
    assert len(segments) == 1
    assert segments[0].quarantined is True
    assert segments[0].quarantine_reason == "snapshot_reset_bridge_failure"

    result = run_segment_with_ofi_engine(segments[0])
    assert result.quarantined is True
    assert result.clean is False
    assert result.ofi_emitted_count == 0
    assert result.quarantine_reason == "snapshot_reset_bridge_failure"
    assert result.snapshot_reset_chain_failure_count == 1
    assert result.quarantined_segment_count == 1
    assert result.ofi_suppressed_due_to_quarantine_count >= 1


def test_source_gap_behavior_remains_unchanged():
    packets = [
        _packet(event_time=1, final_update_id=10, prev_final_update_id=9, first_update_id=9),
        _packet(event_time=2, final_update_id=20, prev_final_update_id=10, first_update_id=10),
        _packet(event_time=3, final_update_id=30, prev_final_update_id=999, first_update_id=11),
    ]
    segments = segment_packets(packets)
    assert len(segments) == 2
    assert segments[0].boundary_reason == "source_sequence_gap"
    assert segments[0].quarantined is False


def test_summarize_segments_includes_new_quarantine_counters():
    segments = (
        L2Segment(
            segment_id=1,
            start_packet_index=1,
            end_packet_index=2,
            start_reason="file_start",
            boundary_reason="sample_end",
            packets=(
                _packet(event_time=1, final_update_id=10, prev_final_update_id=None, first_update_id=None),
                _packet(event_time=2, final_update_id=20, prev_final_update_id=10, first_update_id=11),
            ),
            quarantined=False,
            quarantine_reason=None,
        ),
        L2Segment(
            segment_id=2,
            start_packet_index=3,
            end_packet_index=3,
            start_reason="file_start",
            boundary_reason="sample_end",
            packets=(
                _packet(event_time=3, final_update_id=30, prev_final_update_id=20, first_update_id=21),
            ),
            quarantined=True,
            quarantine_reason="snapshot_reset_bridge_failure",
        ),
    )
    results = (
        SegmentRunResult(
            segment_id=1,
            packet_count=2,
            ofi_emitted_count=1,
            warmup_none_count=1,
            sequence_gap_count=0,
            clean=True,
            quarantined=False,
            quarantine_reason=None,
            snapshot_reset_observed_count=1,
            snapshot_reset_clean_seed_count=1,
            snapshot_reset_chain_failure_count=0,
            snapshot_bridge_event_count=1,
            quarantined_segment_count=0,
            ofi_suppressed_due_to_quarantine_count=0,
            ofi_suppressed_due_to_snapshot_bridge_count=1,
        ),
        SegmentRunResult(
            segment_id=2,
            packet_count=1,
            ofi_emitted_count=0,
            warmup_none_count=0,
            sequence_gap_count=0,
            clean=False,
            quarantined=True,
            quarantine_reason="snapshot_reset_bridge_failure",
            snapshot_reset_observed_count=1,
            snapshot_reset_clean_seed_count=0,
            snapshot_reset_chain_failure_count=1,
            snapshot_bridge_event_count=0,
            quarantined_segment_count=1,
            ofi_suppressed_due_to_quarantine_count=1,
            ofi_suppressed_due_to_snapshot_bridge_count=0,
        ),
    )
    summary = summarize_segments(segments, results)
    assert summary["segment_count"] == 2
    assert summary["clean_segment_count"] == 1
    assert summary["dirty_segment_count"] == 1
    assert summary["snapshot_reset_observed_count"] == 2
    assert summary["snapshot_reset_clean_seed_count"] == 1
    assert summary["snapshot_reset_chain_failure_count"] == 1
    assert summary["snapshot_bridge_event_count"] == 1
    assert summary["quarantined_segment_count"] == 1
    assert summary["ofi_suppressed_due_to_quarantine_count"] == 1
    assert summary["ofi_suppressed_due_to_snapshot_bridge_count"] == 1


def test_report_statement_present():
    doc = Path("/home/tokio/tm-trading-v92-core/docs/v92_L2_OFI_SNAPSHOT_RESET_QUARANTINE_POLICY_VALIDATION.md")
    script.run_validation(max_events_per_file=10, output_doc=doc, candidate_file_args=[])
    assert script.PRODUCTION_APPROVAL_STATEMENT in doc.read_text(encoding="utf-8")
    assert "No policy or OFIEngine behavior is changed." in doc.read_text(encoding="utf-8")
