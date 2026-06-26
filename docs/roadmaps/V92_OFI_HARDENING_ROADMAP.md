# V9.2 OFI Hardening Roadmap

## Objective

Close the real gaps in `features/microstructure_ofi.py` that block
production-tier historical replay and downstream absorption / spoofing
detection, **without** cascading rewrites of unaffected feature modules.
This roadmap supersedes speculative architecture prompts. Each task below
ships behind (a) the existing test contract in
`tests/test_microstructure_ofi.py` and (b) the segment quarantine contract
in `tests/test_l2_ofi_snapshot_reset_quarantine_policy.py`.

## Status

| Task | State | Evidence |
| --- | --- | --- |
| 1. Event classification primitive | **DONE** | `features/microstructure_event_classifier.py` + 15 tests in `tests/test_microstructure_event_classifier.py` (383+15 = 398 baseline tests pass; zero regressions to existing 383) |
| 2. Streaming event replay | **DONE** | `process_event_stream(events, engine=None)` in `features/microstructure_ofi.py` |
| 3. OFIEngine classification opt-in | **DONE** | `OFIEngine.process_event_with_classification(...)` returns `(ofi, bid_events, ask_events)`; OFI value byte-identical to canonical path. Proof: `test_process_event_with_classification_preserves_ofi_contract`. |
| 4. Kilo review of the patch | **PENDING** | blocked on free-tier model session-limit recovery; document evidence below matches the prompt |
| 5. polars-backed `process_chunk_fast` | **NOT STARTED** | subclass of task 4 — do NOT start without review verdict |
| 6. Backfill numba path with sequence-gap guard | **NOT STARTED** | breaks backtest invariants if rushed; see task 5 |

## Governing constraints

- No `process_event` / `process_update` return-value changes. Existing
  callers in `features/l2_ofi_segmented_reconstruction.py` and the audit
  scripts under `scripts/` must continue to receive the same value type.
- Warmup, sequence-gap, and `requires_resync` behavior is load-bearing.
  Any new helper that touches engine state must thread the same
  contract — see `test_sequence_gap_sets_requires_resync_and_returns_none`
  in `tests/test_microstructure_ofi.py`.
- No new files under `features/` may import
  `l2_ofi_segmented_reconstruction`. Direction of dependency stays:
  reconstruction imports engine, never the reverse.
- Free-tier external agents (kilo / opencode) have **zero retention**
  for this repo. Always inline file content into the prompt — see
  `skills/autonomous-ai-agents/kilo/SKILL.md` §Pitfalls.

## Task 1 — Event classification primitive — DONE

**Files**
- `features/microstructure_event_classifier.py` (new, 123 lines)
- `tests/test_microstructure_event_classifier.py` (new, 209 lines, 15 tests)

**Contract added**
- `LevelEvent(side, price, new_qty, prior_qty, kind)` dataclass.
- `classify_levels(side, levels, prior_book) -> list[LevelEvent]`.
- `classify_packet(packet_bids, packet_asks, prior_bids, prior_asks) -> (list, list)`.
- `kind ∈ {ADD, AMEND, CANCEL, TRUNCATE, UNCHANGED}`.

**Why a separate module, not engine method**

A speculative review correctly identified the engine conflates *price
movement* with *liquidity removal/addition*. Adding classification
inline would either (a) change `process_event`'s return type and break
the segment layer's expectations, or (b) force every call site to
opt-in via a flag — same end-state as keeping it external. The pure
module form preserves the engine's surface for the segment quarantine
pipeline and exposes the same semantics to absorption / spoofing /
iceberg features.

**Verification (executed 2026-06-26)**
- `pytest tests/ -q` → 383 passed before patch, 383+15 = 398 passed after.
- Side-effect parity test
  `test_process_event_with_classification_preserves_ofi_contract`
  proves the opt-in path returns OFI values byte-identical to the
  canonical path.

## Task 2 — Streaming event replay — DONE

**File**: `features/microstructure_ofi.py` (added)

**Contract added**
- `EventStreamRecord(index, ofi, event_time, final_update_id, requires_resync)` dataclass.
- `process_event_stream(events, engine=None) -> Iterator[EventStreamRecord]`.
- Reuses one `OFIEngine` across the entire iterable. Caller may supply
  their own engine to preserve warmup state across chunks.

**Why**

The original `process_chunk` is correct for a single chunk but forces
the caller to pre-split their event stream into chunks. Splitting
across multi-hour / multi-file historical replays discards warmup state
at every boundary. The streaming helper is the idiom that fixes this
without changing `process_chunk`'s semantics (which match the existing
single-chunk tests).

**Verification**
- `test_process_event_stream_warms_up_only_once` — warmup on event 0,
  emit from event 1+.
- `test_process_event_stream_propagates_sequence_gap_into_records` —
  engine's `requires_resync` is correctly surfaced to the caller.
- `test_process_event_stream_uses_caller_engine_when_supplied` — proves
  the reuse path.

## Task 3 — Kilo review (rework loop) — PENDING

**Smoke status (executed 2026-06-26)**

| Call | Result |
| --- | --- |
| `kilo run ... --model kilo/poolside/laguna-m.1:free --auto --agent ask ...` | OK, `cost=0`, prompt echoed + reply within 8 s |
| `kilo run --variant high ... <25 kB review prompt>` | exit 124 (timeout), 0-byte JSON, ~25 kB stderr dump |

The high-variant review run hit timeout. The smoke runs succeed.
Hypothesis without evidence: `--variant high` on the free tier routes
through the slower reasoning path and breaches the per-request wall
budget for this profile. **Defer judgement until retry without
`--variant` and with file content moved to `-f` attachments so the
positional prompt stays under ~3 kB.**

**Next action**

1. Re-dispatch the review with `--variant` unset on the same
   `kilo/poolside/laguna-m.1:free` model.
2. Attach the four files via `-f`; keep the prompt under 4 kB; allow
   240 s minimum timeout.
3. Capture Kilo's verdict verbatim + the JSON step events into this
   file under "## Task 3 — Kilo review outcome (TBD)".
4. If verdict is `REWORK`, list the concrete failures and reopen the
   tasks they affect.

## Task 4 — polars-backed fast chunk path — BLOCKED on task 3

**Not started.** Reasons:
- `features/microstructure_numba_ofi.py` already exists with a
  single-update vectorized path. It does **not** honor `requires_resync`
  or sequence-gap guards. Replacing `process_chunk` with that path
  would silently corrupt backtest results.
- A polars-backed variant must preserve warmup, sequence-gap, and
  `requires_resync` semantics. The right surface is a
  `process_chunk_polars(df)` wrapper that funnels row-batches through
  `process_event_stream` and accumulates results in a polars Series,
  not a from-scratch rewrite.

**Definition of done (sketch, not committed)**
- New helper `process_chunk_polars(df)` that calls
  `process_event_stream` event-by-event and returns a polars
  DataFrame with an `ofi` column whose values match `process_chunk` on
  the same input.
- Bench: 5x faster than `process_chunk` on N ≥ 50_000 rows.
- Tests: equivalence on a synthetic stream, sequence-gap handling
  equivalence, warmup equivalence.

## Task 5 — Backfill numba path with guards — BLOCKED on task 4

**Not started.** The numba path used by `process_chunk_fast` (in
`features/microstructure_numba_ofi.py`) is invoked from audit scripts
(`scripts/v92_ofi_numba_diagnostic.py`) but never by the production
engine. Adding the guards correctly (especially across streaming
boundaries) is a research problem, not an integration task. Park until
the polars path (task 4) proves the engine contract is stable.

## How to update this file

- On any new task: add a row to the Status table and a new section.
- On any task completion: paste the test output verbatim before the
  "## How to update this file" section.
- On any task blocking condition: write the blocker here, in
  present-tense prose, with the exact citation (test name, line,
  commit SHA) that motivates the block.

## Task 3 — Kilo review outcome (TBD)

_Replace this section after the Kilo review run completes (see Task 3)._
