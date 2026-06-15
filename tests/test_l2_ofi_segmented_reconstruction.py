from __future__ import annotations

from pathlib import Path

import pytest

import scripts.rehearse_l2_ofi_segmented_reconstruction as mod
from scripts.diagnose_l2_ofi_dirty_transaction_time_file import PacketSummary, annotate_chain


def _packet(
    final_update_id: int,
    *,
    prev_final_update_id: int | None,
    first_update_id: int | None = 1,
    event_time: int,
    transaction_time_min: int | None = None,
    event_type: str = "depthUpdate",
) -> PacketSummary:
    return PacketSummary(
        key=("BTCUSDT", event_time, final_update_id, prev_final_update_id, event_type),
        symbol="BTCUSDT",
        event_type=event_type,
        event_time=event_time,
        transaction_time_min=transaction_time_min,
        transaction_time_max=transaction_time_min,
        received_time_min=transaction_time_min,
        received_time_max=transaction_time_min,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        prev_final_update_id=prev_final_update_id,
        last_update_id=final_update_id,
        bid_level_count=1,
        ask_level_count=1,
        total_level_count=2,
        has_null_first_update_id=first_update_id is None,
        has_null_prev_final_update_id=prev_final_update_id is None,
        is_snapshot_or_reset=first_update_id is None or prev_final_update_id is None,
        raw_row_count=2,
        rows=[
            {"side_group": "bid", "price": 100.0, "quantity": 1.0},
            {"side_group": "ask", "price": 101.0, "quantity": 1.0},
        ],
    )


def test_source_gap_creates_new_segment_boundary():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=999, first_update_id=11, event_time=3, transaction_time_min=3),
        ]
    )
    segments = mod.build_segments(packets)
    assert len(segments) == 2
    assert segments[0].segment_boundary_reason == "source_sequence_gap"
    assert segments[0].packet_count == 2


def test_snapshot_reset_creates_new_segment_boundary():
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=None, first_update_id=None, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=20, first_update_id=20, event_time=3, transaction_time_min=3),
        ]
    )
    segments = mod.build_segments(packets)
    assert len(segments) == 2
    assert segments[0].segment_boundary_reason == "snapshot_or_reset"
    assert segments[0].packet_count == 1


def test_ofi_engine_reinstantiated_per_segment(monkeypatch: pytest.MonkeyPatch):
    packets = annotate_chain(
        [
            _packet(10, prev_final_update_id=9, first_update_id=9, event_time=1, transaction_time_min=1),
            _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2, transaction_time_min=2),
            _packet(30, prev_final_update_id=999, first_update_id=11, event_time=3, transaction_time_min=3),
        ]
    )
    segments = mod.build_segments(packets)

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

    monkeypatch.setattr(mod, "OFIEngine", DummyEngine)
    summary = mod.process_segments(segments)
    assert len(DummyEngine.instances) == len(segments)
    assert summary["total_ofi_emitted_count"] >= 1


def test_clean_segments_stay_clean_internally(monkeypatch: pytest.MonkeyPatch):
    segments = [
        mod.SegmentSummary(
            segment_id=1,
            start_packet_index=1,
            end_packet_index=2,
            packet_count=2,
            start_event_time=1,
            end_event_time=2,
            start_transaction_time=1,
            end_transaction_time=2,
            start_final_update_id=10,
            end_final_update_id=20,
            segment_boundary_reason="file_start",
            segment_clean=True,
            ofi_emitted_count=0,
            warmup_none_count=0,
            sequence_gap_count_inside_segment=0,
            snapshot_reset_count_inside_segment=0,
            packets=[_packet(10, prev_final_update_id=9, first_update_id=9, event_time=1), _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2)],
        )
    ]

    def fake_rehearsal(segment_packets, strict_sequence=True):
        return {
            "processed_event_count": len(segment_packets),
            "ofi_emitted_count": len(segment_packets) - 1,
            "warmup_none_count": 1,
            "sequence_gap_count": 0,
            "resync_stop_event_index": None,
            "engine_completed_sample": True,
            "ofi_records": [{"datetime": 1, "ofi": 1.0}],
        }

    monkeypatch.setattr(mod, "rehearse_segment", fake_rehearsal)
    summary = mod.process_segments(segments)
    assert summary["all_segments_clean"] is True
    assert summary["dirty_segment_count"] == 0
    assert summary["clean_segment_count"] == 1


def test_dirty_segment_detected_when_internal_gap_remains(monkeypatch: pytest.MonkeyPatch):
    segments = [
        mod.SegmentSummary(
            segment_id=1,
            start_packet_index=1,
            end_packet_index=2,
            packet_count=2,
            start_event_time=1,
            end_event_time=2,
            start_transaction_time=1,
            end_transaction_time=2,
            start_final_update_id=10,
            end_final_update_id=20,
            segment_boundary_reason="file_start",
            segment_clean=True,
            ofi_emitted_count=0,
            warmup_none_count=0,
            sequence_gap_count_inside_segment=0,
            snapshot_reset_count_inside_segment=0,
            packets=[_packet(10, prev_final_update_id=9, first_update_id=9, event_time=1), _packet(20, prev_final_update_id=10, first_update_id=10, event_time=2)],
        ),
        mod.SegmentSummary(
            segment_id=2,
            start_packet_index=3,
            end_packet_index=4,
            packet_count=2,
            start_event_time=3,
            end_event_time=4,
            start_transaction_time=3,
            end_transaction_time=4,
            start_final_update_id=30,
            end_final_update_id=40,
            segment_boundary_reason="source_sequence_gap",
            segment_clean=False,
            ofi_emitted_count=0,
            warmup_none_count=0,
            sequence_gap_count_inside_segment=1,
            snapshot_reset_count_inside_segment=0,
            packets=[_packet(30, prev_final_update_id=999, first_update_id=11, event_time=3), _packet(40, prev_final_update_id=30, first_update_id=12, event_time=4)],
        ),
    ]

    def fake_rehearsal(segment_packets, strict_sequence=True):
        if segment_packets[0].final_update_id == 30:
            return {
                "processed_event_count": len(segment_packets),
                "ofi_emitted_count": 0,
                "warmup_none_count": 0,
                "sequence_gap_count": 1,
                "resync_stop_event_index": 2,
                "engine_completed_sample": False,
                "ofi_records": [],
            }
        return {
            "processed_event_count": len(segment_packets),
            "ofi_emitted_count": len(segment_packets) - 1,
            "warmup_none_count": 1,
            "sequence_gap_count": 0,
            "resync_stop_event_index": None,
            "engine_completed_sample": True,
            "ofi_records": [{"datetime": 1, "ofi": 1.0}],
        }

    monkeypatch.setattr(mod, "rehearse_segment", fake_rehearsal)
    summary = mod.process_segments(segments)
    assert summary["dirty_segment_count"] == 1
    assert summary["segments_with_internal_resync"] == 1
    assert summary["all_segments_clean"] is False


def test_tiny_one_packet_segment_not_meaningful():
    packets = annotate_chain([_packet(10, prev_final_update_id=9, first_update_id=9, event_time=1)])
    segments = mod.build_segments(packets)
    summary = mod.process_segments(segments)
    assert summary["meaningful_segment_count"] == 0
    assert segments[0].packet_count == 1


def test_report_includes_no_production_statement():
    report = mod.render_report(
        {
            "l2_root": Path("/tmp/root"),
            "max_files": 12,
            "max_events_per_file": 7000,
            "ordering": "transaction_time_final_update_id",
            "symbol": "BTCUSDT",
            "executive_finding": "x",
            "file_selection": [],
            "segment_boundary_policy": "y",
            "per_file_rows": [],
            "segment_rows": [],
            "aggregate_summary": {"a": 1},
            "ofi_rows": [],
            "join_rows": [],
            "what_worked": [],
            "what_failed": [],
            "what_is_safe": [],
            "what_is_not_safe": [],
            "decision_labels": [],
            "segmented_reconstruction_globally_approved": "Not globally approved; segmented reconstruction is only a bounded rehearsal candidate.",
            "alpha_approval": "No.",
            "paper_live_approval": "No.",
            "required_next_step": "next",
        }
    )
    assert "This rehearsal does not approve OFI for production, paper trading, live trading, or alpha use." in report
