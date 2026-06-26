"""V9.2 OFI engine.

This module computes order flow imbalance (OFI) from level-2 order book
updates. It is designed to be warmup-safe, sequence-gap aware, and bounded in
book depth.

OFI formula:

    OFI = ΔW - ΔV

where ΔW is the bid-side contribution and ΔV is the ask-side contribution,
computed from the best bid / best ask transition between events.

This repairs OFI infrastructure only. It does not approve any strategy,
paper-trading rule, or live-trading rule.

Optional surfaces
-----------------

Two opt-in helpers sit alongside the canonical ``process_event`` /
``process_update`` API and never change its return value or behavior:

* ``OFIEngine.process_event_with_classification`` returns the same OFI as
  ``process_event`` plus a list of ``LevelEvent`` records (ADD/AMEND/
  CANCEL/TRUNCATE/UNCHANGED) computed relative to the engine's prior book
  view. Classification is provided by
  ``features.microstructure_event_classifier`` and is a pure
  post-processing step.

* ``process_event_stream(events)`` runs an iterable of event dicts through a
  single engine instance and yields per-event records. This is the path
  intended for streaming historical replay and avoids the per-row engine
  allocation overhead that ``process_chunk`` historically paid when callers
  re-implemented their own loop.
"""

from __future__ import annotations

from ast import literal_eval
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

import pandas as pd

try:  # pragma: no cover - optional companion, exercised when classifier is used
    from features.microstructure_event_classifier import (
        LevelEvent,
        classify_levels,
    )
except ImportError:  # pragma: no cover
    LevelEvent = None  # type: ignore[assignment]
    classify_levels = None  # type: ignore[assignment]

try:  # pragma: no cover - dependency path is exercised in integration tests
    from sortedcontainers import SortedDict
except ImportError:  # pragma: no cover - fallback keeps the module usable
    SortedDict = None  # type: ignore[assignment]


@dataclass
class _BestQuote:
    price: float | None
    qty: float | None


class OFIEngine:
    """Warmup-safe OFI engine with bounded book depth."""

    def __init__(self, max_levels: int = 50):
        self.max_levels = int(max_levels)
        self.bids = self._make_book()
        self.asks = self._make_book()
        self.prev_best_bid_price: float | None = None
        self.prev_best_bid_qty: float | None = None
        self.prev_best_ask_price: float | None = None
        self.prev_best_ask_qty: float | None = None
        self.last_update_id: int | None = None
        self.requires_resync: bool = False
        self.last_event_time: Any = None

    def _make_book(self):
        if SortedDict is not None:
            return SortedDict()
        return {}

    def reset(self) -> None:
        """Clear all book state and remove any resync requirement."""
        self.bids = self._make_book()
        self.asks = self._make_book()
        self.prev_best_bid_price = None
        self.prev_best_bid_qty = None
        self.prev_best_ask_price = None
        self.prev_best_ask_qty = None
        self.last_update_id = None
        self.requires_resync = False
        self.last_event_time = None

    def _book_best(self, book, *, side: str) -> _BestQuote:
        if not book:
            return _BestQuote(None, None)
        if SortedDict is not None and isinstance(book, SortedDict):
            price = book.peekitem(-1 if side == "bid" else 0)[0]
        else:
            price = max(book.keys()) if side == "bid" else min(book.keys())
        return _BestQuote(float(price), float(book[price]))

    def _prune_book(self, book, *, side: str) -> None:
        if self.max_levels <= 0:
            return
        while len(book) > self.max_levels:
            if SortedDict is not None and isinstance(book, SortedDict):
                # SortedDict is ascending; remove the far side.
                book.popitem(0 if side == "bid" else -1)
            else:
                ordered = sorted(book.keys())
                drop_price = ordered[0] if side == "bid" else ordered[-1]
                book.pop(drop_price, None)

    def _apply_level(self, side: str, price: float, qty: float) -> None:
        book = self.bids if side == "bid" else self.asks
        if qty <= 0.0:
            book.pop(price, None)
        else:
            book[price] = qty
        self._prune_book(book, side=side)

    def _update_previous_best(self, best_bid: _BestQuote, best_ask: _BestQuote) -> None:
        self.prev_best_bid_price = best_bid.price
        self.prev_best_bid_qty = best_bid.qty
        self.prev_best_ask_price = best_ask.price
        self.prev_best_ask_qty = best_ask.qty

    def _is_warmed_up(self) -> bool:
        return (
            self.prev_best_bid_price is not None
            and self.prev_best_bid_qty is not None
            and self.prev_best_ask_price is not None
            and self.prev_best_ask_qty is not None
        )

    def _compute_ofi(self, best_bid: _BestQuote, best_ask: _BestQuote) -> float:
        if not self._is_warmed_up() or best_bid.price is None or best_ask.price is None:
            return 0.0

        prev_bid_price = float(self.prev_best_bid_price)
        prev_bid_qty = float(self.prev_best_bid_qty)
        prev_ask_price = float(self.prev_best_ask_price)
        prev_ask_qty = float(self.prev_best_ask_qty)

        if best_bid.price > prev_bid_price:
            delta_w = float(best_bid.qty or 0.0)
        elif best_bid.price == prev_bid_price:
            delta_w = float(best_bid.qty or 0.0) - prev_bid_qty
        else:
            delta_w = 0.0

        if best_ask.price < prev_ask_price:
            delta_v = float(best_ask.qty or 0.0)
        elif best_ask.price == prev_ask_price:
            delta_v = float(best_ask.qty or 0.0) - prev_ask_qty
        else:
            delta_v = 0.0

        return delta_w - delta_v

    def process_event(
        self,
        bids: list[tuple[float, float]] | None = None,
        asks: list[tuple[float, float]] | None = None,
        event_time=None,
        first_update_id=None,
        final_update_id=None,
        previous_update_id=None,
    ) -> float | None:
        """Apply all updates in an event and compute OFI once.

        Returns ``None`` during warmup or when a sequence gap forces resync.
        """

        if self.requires_resync:
            return None

        if previous_update_id is not None and self.last_update_id is not None:
            if int(previous_update_id) != int(self.last_update_id):
                self.requires_resync = True
                return None

        bids = bids or []
        asks = asks or []
        for price, qty in bids:
            self._apply_level("bid", float(price), float(qty))
        for price, qty in asks:
            self._apply_level("ask", float(price), float(qty))

        best_bid = self._book_best(self.bids, side="bid")
        best_ask = self._book_best(self.asks, side="ask")
        self.last_event_time = event_time

        if not self._is_warmed_up():
            if best_bid.price is not None and best_ask.price is not None:
                self._update_previous_best(best_bid, best_ask)
            if final_update_id is not None:
                self.last_update_id = int(final_update_id)
            return None

        ofi = self._compute_ofi(best_bid, best_ask)
        self._update_previous_best(best_bid, best_ask)
        if final_update_id is not None:
            self.last_update_id = int(final_update_id)
        elif first_update_id is not None and self.last_update_id is None:
            self.last_update_id = int(first_update_id)
        return float(ofi)

    def process_update(self, side: str, price: float, qty: float) -> float:
        """Legacy single-update mode.

        The method remains for backward compatibility. Warmup returns 0.0 and
        the update is processed as a one-event batch.
        """

        event_ofi = self.process_event(
            bids=[(price, qty)] if side == "bid" else [],
            asks=[(price, qty)] if side == "ask" else [],
        )
        return 0.0 if event_ofi is None else float(event_ofi)

    def process_event_with_classification(
        self,
        bids: list[tuple[float, float]] | None = None,
        asks: list[tuple[float, float]] | None = None,
        event_time=None,
        first_update_id=None,
        final_update_id=None,
        previous_update_id=None,
    ) -> tuple[float | None, list[Any], list[Any]]:
        """Like :meth:`process_event` but also returns classified level events.

        The returned tuple is ``(ofi, classified_bids, classified_asks)``:

        * ``ofi`` -- identical to :meth:`process_event` return value.
        * ``classified_bids`` / ``classified_asks`` -- lists of
          ``LevelEvent`` records describing how each (price, qty) update in
          this event relates to the engine's prior book view.

        Classification is computed against the engine's *prior* book (the
        state immediately before this event was applied) so the engine's
        own diff application is the source of truth. If a sequence gap
        forces ``requires_resync`` before this call, both classification
        lists are empty and ``ofi`` is ``None``.

        This method never mutates the engine differently from
        :meth:`process_event`; the only side effect is the same OFI /
        warmup bookkeeping the canonical path already performs.
        """

        bids = bids or []
        asks = asks or []
        if classify_levels is None:
            raise RuntimeError(
                "features.microstructure_event_classifier is not importable;"
                " install/import the module before calling process_event_with_classification"
            )

        prior_bids = {float(p): float(q) for p, q in self.bids.items()}
        prior_asks = {float(p): float(q) for p, q in self.asks.items()}

        ofi = self.process_event(
            bids=bids,
            asks=asks,
            event_time=event_time,
            first_update_id=first_update_id,
            final_update_id=final_update_id,
            previous_update_id=previous_update_id,
        )

        if self.requires_resync:
            return ofi, [], []

        classified_bids = classify_levels("bid", bids, prior_bids)
        classified_asks = classify_levels("ask", asks, prior_asks)
        return ofi, classified_bids, classified_asks


@dataclass(frozen=True)
class EventStreamRecord:
    """Per-event record yielded by :func:`process_event_stream`."""

    index: int
    ofi: float | None
    event_time: Any
    final_update_id: int | None
    requires_resync: bool


def process_event_stream(
    events: Iterable[dict[str, Any]],
    engine: OFIEngine | None = None,
) -> Iterator[EventStreamRecord]:
    """Replay an iterable of L2 event dicts through a single ``OFIEngine``.

    Each input event is a dict with the same shape accepted by
    :meth:`OFIEngine.process_event` (``bids``, ``asks``, optionally
    ``event_time`` / ``first_update_id`` / ``final_update_id`` /
    ``previous_update_id``).

    A single engine instance is constructed when none is supplied and
    reused across every event in the iterable, which preserves warmup
    state and the sequence-gap guard across packets. Callers that need a
    fresh segment should construct their own ``OFIEngine`` and pass it in
    -- this matches what ``run_segment_with_ofi_engine`` already does.

    The iterator yields ``EventStreamRecord`` per input event so callers
    can route results into a polars/pandas sink row by row without ever
    allocating a second engine instance.
    """

    if engine is None:
        engine = OFIEngine()

    for idx, event in enumerate(events):
        bids = event.get("bids")
        asks = event.get("asks")
        # Coerce tuple-like input to lists so the engine path is uniform.
        if bids is not None and not isinstance(bids, list):
            bids = list(bids)
        if asks is not None and not isinstance(asks, list):
            asks = list(asks)

        ofi = engine.process_event(
            bids=bids,
            asks=asks,
            event_time=event.get("event_time"),
            first_update_id=event.get("first_update_id"),
            final_update_id=event.get("final_update_id"),
            previous_update_id=event.get("previous_update_id"),
        )

        yield EventStreamRecord(
            index=idx,
            ofi=ofi,
            event_time=event.get("event_time"),
            final_update_id=engine.last_update_id,
            requires_resync=engine.requires_resync,
        )


def _parse_levels(cell: Any) -> list[tuple[float, float]]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    if isinstance(cell, str):
        cell = literal_eval(cell)
    if not isinstance(cell, Iterable):
        return []
    levels: list[tuple[float, float]] = []
    for item in cell:
        if isinstance(item, dict):
            price = item.get("price", item.get(0))
            qty = item.get("quantity", item.get("qty", item.get(1)))
        else:
            price, qty = item
        levels.append((float(price), float(qty)))
    return levels


def process_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """Annotate a chunk of L2 updates with OFI.

    The input DataFrame is never mutated. Legacy single-update rows with
    ``side``, ``price``, and ``quantity`` are supported. Event-level rows with
    ``bids`` and ``asks`` are also supported when present.

    Warmup semantics
    ----------------

    A single ``OFIEngine`` is constructed for the chunk and reused across
    every row. The first emission of OFI therefore happens once the engine
    has observed both a full bid and a full ask best quote -- this is the
    warmup guard, not a bug. Callers streaming multiple chunks through a
    single replay (e.g. multi-hour / multi-day historical runs) should use
    :func:`process_event_stream` with a caller-supplied engine to preserve
    warmup state across chunks; building a new chunk per file or per hour
    discards all warmup and forces the engine to re-seed itself on each
    call, which is correct but expensive.

    The pandas loop body deliberately uses ``itertuples`` rather than
    ``iterrows``; rebuilding the chunk into a polars frame is the right
    move when the loop becomes the bottleneck, but the canonical
    ``process_event`` semantics stay ahead of any vectorized rewrite --
    any vectorized replacement must preserve the warmup/sequence-gap
    contract verified by ``tests/test_microstructure_ofi.py``.
    """

    out = df.copy()
    engine = OFIEngine()
    ofi_values: list[float] = []

    if {"side", "price", "quantity"}.issubset(out.columns):
        for row in out.itertuples(index=False):
            ofi = engine.process_update(str(row.side), float(row.price), float(row.quantity))
            ofi_values.append(ofi)
    elif {"bids", "asks"}.issubset(out.columns):
        for row in out.itertuples(index=False):
            bids = _parse_levels(getattr(row, "bids"))
            asks = _parse_levels(getattr(row, "asks"))
            ofi = engine.process_event(bids=bids, asks=asks)
            ofi_values.append(0.0 if ofi is None else float(ofi))
    else:
        raise ValueError("process_chunk requires either side/price/quantity or bids/asks columns")

    out["ofi"] = ofi_values
    return out
