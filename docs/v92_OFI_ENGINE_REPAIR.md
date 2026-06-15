# V9.2 OFI Engine Repair

## Purpose

Repair the OFI infrastructure so it is warmup-safe, sequence-gap aware, and bounded in book depth.

This repairs OFI infrastructure only. It does not approve any strategy, paper-trading rule, or live-trading rule.

## Problems Fixed

- Cold-start best ask handling no longer uses `float("inf")`.
- OFI is computed from an event-level BBO transition instead of per-level update noise.
- Sequence gaps can be detected and require resync.
- Book depth is bounded.
- `process_chunk` no longer mutates the caller DataFrame.
- Legacy single-update compatibility remains available.

## OFI Formula

The engine computes:

```text
OFI = ΔW - ΔV
```

where:

- `ΔW` is the bid-side contribution from the best bid transition.
- `ΔV` is the ask-side contribution from the best ask transition.

## Warmup / Resync Semantics

- Uninitialized best bid / best ask state is represented with `None`.
- The first usable snapshot seeds state and returns `None`.
- If a sequence gap is detected, `requires_resync` is set to `True`.
- Once resync is required, the engine does not silently continue.

## Event-Level Processing

`process_event()` applies all bid and ask updates in the event first, then computes OFI once from the resulting BBO transition.

This avoids the old behavior of computing a separate OFI contribution for every level update in the same event.

## Sequence Gap Detection

The engine tracks `last_update_id`.

If `previous_update_id` is provided and does not match `last_update_id`, the engine returns `None` and marks itself as requiring resync.

## Bounded Book Depth

The engine prunes both sides of the book to `max_levels` after every update batch.

- Bids keep the highest prices.
- Asks keep the lowest prices.

## Backward Compatibility

`process_update(side, price, qty)` remains available for legacy single-update code paths.

It is implemented through the event-level processor and returns a warmup-safe `0.0` when the first observation only seeds state.

## Tests

The regression tests cover:

- warmup behavior
- bid and ask improvement signs
- same-price size changes
- best-level deletion and recomputation
- sequence-gap resync handling
- bounded depth pruning
- `process_chunk` non-mutation
- legacy compatibility

## What Is Still Not Production-Ready

- The engine still depends on the calling pipeline to provide correctly ordered data.
- Sequence resync handling is conservative and requires upstream recovery logic.
- This repair does not validate live market data feeds.

## Required Next Step

Use the repaired engine in read-only or research contexts first, then validate downstream consumers separately before any production integration.
