from __future__ import annotations

from features.microstructure_event_classifier import (
    ADD,
    AMEND,
    CANCEL,
    TRUNCATE,
    UNCHANGED,
    classify_levels,
    classify_packet,
)
from features.microstructure_ofi import (
    OFIEngine,
    EventStreamRecord,
    process_event_stream,
)


def test_classify_levels_add_when_prior_empty():
    out = classify_levels("bid", [(100.5, 1.0)], {})
    assert len(out) == 1
    assert out[0].kind == ADD
    assert out[0].is_addition is True
    assert out[0].size_delta == 1.0


def test_classify_levels_cancel_when_qty_zero_and_prior_positive():
    out = classify_levels("ask", [(101.0, 0.0)], {101.0: 2.5})
    assert len(out) == 1
    assert out[0].kind == CANCEL
    assert out[0].is_removal is True
    assert out[0].size_delta == -2.5


def test_classify_levels_amend_and_truncate():
    amended = classify_levels("bid", [(100.0, 5.0)], {100.0: 3.0})
    assert amended[0].kind == AMEND
    assert amended[0].size_delta == 2.0

    truncated = classify_levels("bid", [(100.0, 1.0)], {100.0: 4.0})
    assert truncated[0].kind == TRUNCATE
    assert truncated[0].size_delta == -3.0


def test_classify_levels_unchanged_when_size_matches():
    out = classify_levels("bid", [(100.0, 3.0)], {100.0: 3.0})
    assert out[0].kind == UNCHANGED
    assert out[0].is_addition is False
    assert out[0].is_removal is False
    assert out[0].size_delta == 0.0


def test_classify_packet_returns_bid_and_ask_lists():
    bid_events, ask_events = classify_packet(
        packet_bids=[(100.0, 1.0)],
        packet_asks=[(101.0, 0.0)],
        prior_bids={},
        prior_asks={101.0: 2.0},
    )
    assert bid_events[0].kind == ADD
    assert ask_events[0].kind == CANCEL
    assert ask_events[0].side == "ask"


def test_classify_levels_rejects_unknown_side():
    try:
        classify_levels("buy", [(100.0, 1.0)], {})
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-'bid'/'ask' side")


def _seeded_engine() -> OFIEngine:
    engine = OFIEngine(max_levels=5)
    engine.process_event(
        bids=[(100.0, 1.0), (99.0, 2.0)],
        asks=[(101.0, 1.5), (102.0, 2.5)],
        final_update_id=10,
    )
    return engine


def test_process_event_with_classification_returns_add_on_new_level():
    engine = _seeded_engine()
    ofi, bid_events, ask_events = engine.process_event_with_classification(
        bids=[(99.5, 1.0)],
        asks=[],
        final_update_id=11,
    )
    assert ofi is not None
    assert len(bid_events) == 1
    assert bid_events[0].kind == ADD
    assert ask_events == []


def test_process_event_with_classification_returns_cancel_on_qty_zero():
    engine = _seeded_engine()
    ofi, bid_events, ask_events = engine.process_event_with_classification(
        bids=[(100.0, 0.0)],
        asks=[],
        final_update_id=11,
    )
    assert ofi is not None
    assert bid_events[0].kind == CANCEL
    # The cancelled level should NOT appear in the engine's book anymore.
    assert 100.0 not in engine.bids


def test_process_event_with_classification_returns_empty_lists_on_resync():
    engine = _seeded_engine()
    engine.last_update_id = 10  # simulate prior history
    ofi, bid_events, ask_events = engine.process_event_with_classification(
        bids=[(101.0, 1.0)],
        asks=[],
        previous_update_id=99,  # mismatch -> resync
        final_update_id=11,
    )
    assert ofi is None
    assert engine.requires_resync is True
    assert bid_events == []
    assert ask_events == []


def test_process_event_with_classification_preserves_ofi_contract():
    """Same OFI value as the canonical process_event path."""

    engine = _seeded_engine()
    ofi_plain = engine.process_event(
        bids=[(101.0, 2.0)],
        asks=[],
        final_update_id=11,
    )
    # rebuild engine so the next call has identical prior state
    engine = _seeded_engine()
    ofi_classified, _, _ = engine.process_event_with_classification(
        bids=[(101.0, 2.0)],
        asks=[],
        final_update_id=11,
    )
    assert ofi_plain == ofi_classified


def test_process_event_stream_warms_up_only_once():
    """Streaming multiple events through one engine should warm up after the
    first event and emit OFI on the second, matching what the canonical
    process_event path produces.
    """

    events = [
        {
            "bids": [(100.0, 1.0), (99.0, 2.0)],
            "asks": [(101.0, 1.5), (102.0, 2.5)],
            "final_update_id": 10,
        },
        {
            "bids": [(101.0, 2.0)],
            "asks": [],
            "final_update_id": 11,
        },
        {
            "bids": [],
            "asks": [(100.5, 2.0)],
            "final_update_id": 12,
        },
    ]
    records = list(process_event_stream(events))
    assert len(records) == 3
    assert records[0].ofi is None  # warmup
    assert records[1].ofi is not None and records[1].ofi > 0
    assert records[2].ofi is not None and records[2].ofi < 0
    assert records[-1].final_update_id == 12


def test_process_event_stream_propagates_sequence_gap_into_records():
    events = [
        {
            "bids": [(100.0, 1.0)],
            "asks": [(101.0, 1.0)],
            "final_update_id": 10,
        },
        {
            "bids": [(100.0, 1.0)],
            "asks": [(101.0, 1.0)],
            "previous_update_id": 99,  # gap
            "final_update_id": 11,
        },
        {
            "bids": [(100.0, 1.0)],
            "asks": [(101.0, 1.0)],
            "previous_update_id": 11,
            "final_update_id": 12,
        },
    ]
    records = list(process_event_stream(events))
    assert records[0].requires_resync is False
    assert records[1].requires_resync is True
    assert records[1].ofi is None
    # After resync the engine stays in requires_resync and emits None.
    assert records[2].requires_resync is True
    assert records[2].ofi is None


def test_process_event_stream_uses_caller_engine_when_supplied():
    """The caller-owned engine path must surface the engine's state
    mutations so warmup carries across calls.
    """

    engine = OFIEngine()
    event = {
        "bids": [(100.0, 1.0)],
        "asks": [(101.0, 1.0)],
        "final_update_id": 10,
    }
    list(process_event_stream([event], engine=engine))
    # engine has been warmed up by the previous event
    assert engine.prev_best_bid_price == 100.0
    assert engine.prev_best_ask_price == 101.0


def test_process_event_stream_accepts_tuple_bids():
    events = [
        {
            "bids": ((100.0, 1.0), (99.0, 2.0)),
            "asks": ((101.0, 1.5),),
            "final_update_id": 10,
        },
    ]
    records = list(process_event_stream(events))
    assert len(records) == 1
    assert records[0].requires_resync is False


def test_event_stream_record_dataclass():
    rec = EventStreamRecord(
        index=7,
        ofi=0.5,
        event_time=1234,
        final_update_id=99,
        requires_resync=False,
    )
    assert rec.index == 7
    assert rec.ofi == 0.5
    assert rec.final_update_id == 99
