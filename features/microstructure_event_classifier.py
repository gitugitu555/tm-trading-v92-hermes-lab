"""L2 update event classification.

Classifies a batch of L2 level updates relative to the prior book state into
the four standard event semantics used by institutional microstructure
analysis:

    ADD       new price level appears with non-zero size
    AMEND     existing price level's size is adjusted (size > 0)
    CANCEL    existing price level's size collapses to 0 (full deletion)
    TRUNCATE  existing price level's size shrinks (partial deletion)

This module is intentionally stateless: it is a pure consumer of
``(side, price, qty)`` triples plus a prior books-of-truth snapshot and
returns the classification tuples. It does NOT mutate the engine or its
internal book -- the caller decides whether to apply the deltas so the
existing warmup/resync/sequence-gap contract in
``features.microstructure_ofi`` stays untouched.

Why a separate module: speculative reviews have correctly identified
that the OFI engine conflates "price movement" with "liquidity
removal/addition" by treating *any* non-zero update as a flow event.
Adding classification at the engine level would risk breaking the
warmup/sequence-gap guarantees already pinned by
``tests/test_microstructure_ofi.py`` and the segment quarantine logic in
``features/l2_ofi_segmented_reconstruction``. Keeping classification as a
pure post-processing layer preserves the engine's contract while exposing
the semantics needed for absorption / iceberg / spoofing detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

ADD = "ADD"
AMEND = "AMEND"
CANCEL = "CANCEL"
TRUNCATE = "TRUNCATE"
UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class LevelEvent:
    """One classified L2 update relative to the prior book state."""

    side: str          # "bid" | "ask"
    price: float
    new_qty: float     # qty as observed in the current packet
    prior_qty: float   # qty from the previous snapshot (0 if unseen)
    kind: str          # ADD | AMEND | CANCEL | TRUNCATE | UNCHANGED

    @property
    def is_removal(self) -> bool:
        return self.kind in (CANCEL, TRUNCATE)

    @property
    def is_addition(self) -> bool:
        return self.kind == ADD

    @property
    def size_delta(self) -> float:
        """Signed delta from the prior book view to this update.

        Positive = net liquidity addition; negative = net removal.
        """
        return self.new_qty - self.prior_qty


def classify_levels(
    side: str,
    levels: Iterable[tuple[float, float]],
    prior_book: dict[float, float],
) -> list[LevelEvent]:
    """Classify every ``(price, qty)`` update on ``side``.

    Args:
        side: ``"bid"`` or ``"ask"``.
        levels: the (price, qty) pairs from the current L2 batch.
        prior_book: snapshot of the same side before this batch was
            applied. Caller is responsible for keeping this in sync with
            the engine's book between batches.

    Returns:
        One ``LevelEvent`` per input entry. Length matches ``len(levels)``.
    """
    side = str(side).lower()
    if side not in {"bid", "ask"}:
        raise ValueError(f"side must be 'bid' or 'ask', got {side!r}")

    out: list[LevelEvent] = []
    for raw_price, raw_qty in levels:
        price = float(raw_price)
        new_qty = float(raw_qty)
        prior_qty = float(prior_book.get(price, 0.0))

        if new_qty <= 0.0:
            if prior_qty <= 0.0:
                kind = UNCHANGED
            elif prior_qty > 0.0:
                kind = CANCEL
            else:
                # prior_qty cannot be negative in a well-formed L2 feed;
                # treat as a defensive cancel.
                kind = CANCEL
        else:
            if prior_qty <= 0.0:
                kind = ADD
            elif new_qty > prior_qty:
                kind = AMEND
            elif new_qty < prior_qty:
                kind = TRUNCATE
            else:
                kind = UNCHANGED

        out.append(
            LevelEvent(
                side=side,
                price=price,
                new_qty=new_qty,
                prior_qty=prior_qty,
                kind=kind,
            )
        )
    return out


def classify_packet(
    packet_bids: Iterable[tuple[float, float]],
    packet_asks: Iterable[tuple[float, float]],
    prior_bids: dict[float, float],
    prior_asks: dict[float, float],
) -> tuple[list[LevelEvent], list[LevelEvent]]:
    """Convenience wrapper for one full packet (bids + asks).

    Returns ``(classified_bids, classified_asks)`` and does NOT mutate the
    inputs. Callers that want to keep their prior_book in sync should
    apply the deltas themselves -- this matters because the canonical
    OFIEngine stores both sides as shared state and the segment layer
    decides when book state has actually committed.
    """
    bid_events = classify_levels("bid", packet_bids, prior_bids)
    ask_events = classify_levels("ask", packet_asks, prior_asks)
    return bid_events, ask_events


__all__ = [
    "ADD",
    "AMEND",
    "CANCEL",
    "TRUNCATE",
    "UNCHANGED",
    "LevelEvent",
    "classify_levels",
    "classify_packet",
]
