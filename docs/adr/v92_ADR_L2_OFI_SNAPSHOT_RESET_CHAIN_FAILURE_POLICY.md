# ADR: L2 OFI Snapshot/Reset Chain-Failure Policy

## Status

Proposed

## Context

The segmented L2 OFI reconstruction work established a reusable policy module and then exercised it through multiple bounded validations:

- `docs/v92_L2_OFI_SEGMENTED_RECONSTRUCTION_POLICY.md`
- `docs/v92_L2_OFI_SEGMENTED_POLICY_SAMPLE_VALIDATION.md`
- `docs/v92_L2_OFI_SEGMENTED_POLICY_EDGE_CASE_VALIDATION.md`
- `docs/v92_L2_OFI_UNEXERCISED_POLICY_PATH_DISCOVERY.md`
- `docs/v92_L2_OFI_DISCOVERED_POLICY_PATH_CANDIDATE_VALIDATION.md`
- `docs/v92_L2_OFI_SNAPSHOT_RESET_DIRTY_CASE_DIAGNOSTIC.md`

The evidence set is now consistent:

- Source-gap-heavy raw files validated cleanly under the segmented policy.
- Snapshot/reset raw candidates were discovered in real raw data.
- Those snapshot/reset raw candidates stayed dirty in bounded validation.
- The dirty-case root cause was diagnosed as `post_snapshot_chain_failure`.
- Missing `transaction_time` fallback remains unobserved in raw data.
- OFI remains research/infrastructure-only.

This ADR captures the policy decision needed before any implementation attempt on the dirty snapshot/reset path.

## Problem

A snapshot/reset-like packet cannot be treated as a clean OFI seed if the next normal diff/update packet does not satisfy chain continuity against the snapshot `final_update_id`.

That condition is unsafe because it risks OFI contamination, hides raw update-chain inconsistency, and could allow state to cross an unsafe boundary.

## Decision Drivers

- no silent OFI contamination
- no OFIEngine state crossing unsafe boundaries
- deterministic replay
- read-only validation before artifact generation
- explicit dirty/quarantine classification
- bar-count preservation for joins
- no alpha/paper/live use before reconstruction approval
- minimal policy surface area

## Options Considered

### Option A: Treat snapshot as clean seed even when next packet does not chain

Decision: reject.

Reasons:

- risks OFI contamination
- hides raw update-chain inconsistency
- previously produced dirty behavior in bounded diagnostics

### Option B: Drop the snapshot packet and start from next packet

Decision: reject or defer.

Reasons:

- may hide real exchange reset state
- could create lookahead or silent state discontinuity
- needs stronger proof before adoption

### Option C: Quarantine snapshot/reset segment until first clean chained diff sequence

Decision: recommended.

Policy idea:

- snapshot/reset-like packet opens a quarantined segment
- do not emit OFI from that segment unless chain continuity is proven
- if the next packet does not chain, segment is dirty/quarantined
- continue scanning until a safe resync point is found
- emit no OFI across the unsafe boundary
- report quarantine reason explicitly

### Option D: Block all files containing snapshot/reset-like packets

Decision: safe but too conservative.

Reasons:

- simple and safe
- may discard valid data unnecessarily
- useful as a temporary fallback if Option C is not implemented yet

## Proposed Policy

Recommend a conservative policy:

- source-gap boundaries remain approved for bounded validation because real raw candidates stayed clean
- snapshot/reset packets are not approved as clean OFI seeds unless the following diff/update chain validates
- if a snapshot/reset packet is first in the segment and the next packet fails to chain, mark the segment as `quarantined_dirty`
- OFIEngine must not emit OFI for quarantined snapshot/reset segments
- no OFI state may cross from a quarantined segment into subsequent segments
- future implementation must expose explicit counters:
  - `snapshot_reset_observed_count`
  - `snapshot_reset_clean_seed_count`
  - `snapshot_reset_chain_failure_count`
  - `quarantined_segment_count`
  - `ofi_suppressed_due_to_quarantine_count`
- full reconstruction remains blocked until this is implemented and bounded validated

## Consequences

Positive:

- avoids contaminated OFI
- preserves deterministic reconstruction
- makes dirty snapshot/reset cases auditable
- keeps source-gap progress usable

Negative:

- some raw data will be quarantined
- OFI coverage may reduce around reset windows
- extra validation is required before broader reconstruction

## Validation Required Before Implementation Approval

Next implementation gate:

1. Add synthetic tests for quarantine semantics.
2. Add bounded raw validation on the two dirty `2026-05-26` files.
3. Prove no OFI is emitted from quarantined dirty snapshot/reset segments.
4. Prove no OFIEngine state crosses a quarantine boundary.
5. Prove source-gap behavior remains unchanged.
6. Prove join-readiness/bar-count preservation remains unchanged where applicable.
7. Run the full suite successfully.

## Non-Goals

- no alpha work
- no strategy work
- no live/paper trading
- no full historical reconstruction
- no OFI artifacts
- no performance claims

## Decision

Adopt Option C as the proposed implementation direction, with Option D as a temporary safety fallback if quarantine implementation is not yet complete.

Do not mark this ADR as accepted yet. Keep status `Proposed` until implementation and bounded validation pass.

## Required Next Step

Write a bounded implementation prompt for the quarantine policy only after this ADR is committed.

This ADR does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.

## Implementation Note

The implementation candidate formalizes the Binance snapshot bridge rule:

`first_update_id <= snapshot.final_update_id <= final_update_id`

Bridge-event OFI is suppressed. Invalid bridge chains are quarantined.

Status remains `Proposed` pending review of the bounded validation results and any follow-up change request.
