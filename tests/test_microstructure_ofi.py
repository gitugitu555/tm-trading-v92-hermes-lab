from __future__ import annotations

import pandas as pd

from features.microstructure_ofi import OFIEngine, process_chunk


def _seeded_engine() -> OFIEngine:
    engine = OFIEngine(max_levels=5)
    assert engine.process_event(
        bids=[(100.0, 1.0), (99.0, 2.0)],
        asks=[(101.0, 1.5), (102.0, 2.5)],
        final_update_id=10,
    ) is None
    return engine


def test_first_update_warmup_does_not_emit_inf_ofi():
    engine = OFIEngine()
    ofi = engine.process_update("bid", 100.0, 1.0)

    assert ofi == 0.0
    assert engine.prev_best_bid_price is None or engine.prev_best_ask_price is None
    assert engine.requires_resync is False


def test_bid_improvement_produces_positive_ofi_after_warmup():
    engine = _seeded_engine()
    ofi = engine.process_update("bid", 101.0, 2.0)

    assert ofi > 0


def test_ask_improvement_produces_negative_ofi_after_warmup():
    engine = _seeded_engine()
    ofi = engine.process_update("ask", 100.5, 2.0)

    assert ofi < 0


def test_same_price_bid_size_increase_produces_positive_ofi():
    engine = _seeded_engine()
    ofi = engine.process_update("bid", 100.0, 3.0)

    assert ofi > 0


def test_same_price_ask_size_increase_produces_negative_ofi():
    engine = _seeded_engine()
    ofi = engine.process_update("ask", 101.0, 3.0)

    assert ofi < 0


def test_deleted_best_level_recomputes_bbo_correctly():
    engine = _seeded_engine()
    ofi = engine.process_update("bid", 100.0, 0.0)

    assert engine.prev_best_bid_price == 99.0
    assert engine.prev_best_ask_price == 101.0
    assert ofi <= 0.0


def test_sequence_gap_sets_requires_resync_and_returns_none():
    engine = _seeded_engine()
    engine.last_update_id = 10

    ofi = engine.process_event(
        bids=[(101.0, 1.0)],
        asks=[(102.0, 1.0)],
        previous_update_id=5,
        final_update_id=11,
    )

    assert ofi is None
    assert engine.requires_resync is True


def test_max_levels_pruning_keeps_highest_bids_and_lowest_asks():
    engine = OFIEngine(max_levels=2)
    engine.process_event(
        bids=[(100.0, 1.0), (99.0, 2.0), (98.0, 3.0)],
        asks=[(101.0, 1.0), (102.0, 2.0), (103.0, 3.0)],
        final_update_id=1,
    )

    assert sorted(engine.bids.keys()) == [99.0, 100.0]
    assert sorted(engine.asks.keys()) == [101.0, 102.0]


def test_process_chunk_does_not_mutate_input_dataframe():
    frame = pd.DataFrame(
        {
            "side": ["bid", "ask"],
            "price": [100.0, 101.0],
            "quantity": [1.0, 1.0],
        }
    )
    original = frame.copy(deep=True)

    out = process_chunk(frame)

    pd.testing.assert_frame_equal(frame, original)
    assert "ofi" in out.columns
    assert "ofi" not in frame.columns


def test_legacy_process_update_remains_available():
    engine = OFIEngine()
    assert isinstance(engine.process_update("bid", 100.0, 1.0), float)
