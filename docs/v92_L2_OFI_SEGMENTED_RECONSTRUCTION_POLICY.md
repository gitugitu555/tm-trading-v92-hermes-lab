# V9.2 L2 OFI Segmented Reconstruction Policy

## Purpose
Define a reusable, read-only policy for segmented OFI reconstruction on bounded raw L2 samples.

## Inputs
- Raw L2 packet streams
- Packet-level bid/ask updates
- Packet timestamps and update IDs

## Policy Rules
- Packets are ordered by `transaction_time ASC, final_update_id ASC`.
- Snapshot/reset packets and source sequence gaps terminate the current segment and begin a new one.
- Each segment is processed in memory only with a fresh OFIEngine instance.
- Segments may be one packet long, but one-packet segments are not meaningful OFI coverage.

## Packet Ordering
- Primary key: `transaction_time ASC, final_update_id ASC`
- Conservative fallback when `transaction_time` is missing: `event_time ASC, final_update_id ASC`
- The policy is deterministic and does not rely on `received_time`.

## Segment Boundary Rules
- `snapshot_or_reset` packets split segments.
- `source_sequence_gap` splits segments.
- `file_start` is captured as the `start_reason` of the first segment.
- `sample_end` closes the terminal segment and is represented as the `boundary_reason` of the final segment.

## OFIEngine State Rules
- A fresh `OFIEngine` instance is used per segment.
- Engine state is never carried across a segment boundary.
- If strict sequence handling is enabled and a segment resyncs internally, the segment is marked dirty and processing stops for that segment.

## Source Gap Handling
- A normal diff packet whose `prev_final_update_id` does not match the previous processed packet's `final_update_id` is treated as a source gap.
- The gap ends the current segment and starts a new one.

## Snapshot / Reset Handling
- Packets with null `first_update_id` or null `prev_final_update_id` are treated as snapshot/reset packets.
- Snapshot/reset packets begin a new segment and reseed OFIEngine state within that segment.

## What This Module Does
- It provides deterministic packet ordering.
- It provides segment boundary detection.
- It provides in-memory OFIEngine segment rehearsal helpers.
- It summarizes segmented reconstruction without writing artifacts.

## What This Module Does Not Do
- It does not generate full historical OFI.
- It does not write OFI artifacts.
- It does not run alpha tests.
- It does not approve production, paper, or live trading.

## Current Approval Status
This policy module does not approve OFI for production, paper trading, live trading, or alpha use.

## Required Next Step
Use the policy module only for bounded, read-only validation and keep broader reconstruction approval blocked until additional bounded samples confirm the same behavior.
