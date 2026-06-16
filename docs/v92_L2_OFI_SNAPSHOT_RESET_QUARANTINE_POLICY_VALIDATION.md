# V9.2 L2 OFI Snapshot/Reset Quarantine Policy Validation

## Purpose
Validate the reusable segmented reconstruction policy module with snapshot/reset quarantine and bridge handling on the two real raw dirty candidate files.

## Inputs
- `max_events_per_file`: `10`
- `selected_candidate_count`: `2`

## Read-Only Guardrails
- Read-only bounded validation only.
- No OFI artifacts are written.
- No policy or OFIEngine behavior is changed.
- No full-corpus reconstruction is attempted.

## Binance Snapshot Bridge Rule
- First processed diff event after a snapshot must satisfy `first_update_id <= snapshot.final_update_id <= final_update_id`.
- After that bridge event, normal continuity resumes with `current.prev_final_update_id == previous.final_update_id`.

## Module Changes
- `L2Segment` and `SegmentRunResult` carry quarantine metadata.
- The policy module now recognizes valid post-snapshot bridge events.
- Invalid snapshot/reset chains are quarantined and suppress OFI.

## Executive Finding
2 dirty snapshot/reset candidate files were processed in bounded read-only mode.
Snapshot/reset-like packets were observed in `2` files.
Bridge events were detected in `0` files.
Quarantined segments were observed in `2` files.
This validation does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.

## Per-File Snapshot/Reset Results
| file_path | file_date | file_hour | rows_scanned | packet_count | snapshot_like_packet_count | snapshot_like_packet_indexes | first_packet_is_snapshot_reset | bridge_rule_satisfied | bridge_event_detected_count | snapshot_reset_observed_count | snapshot_reset_clean_seed_count | snapshot_reset_chain_failure_count | snapshot_bridge_event_count | quarantined_segment_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | ofi_suppressed_due_to_quarantine_count | ofi_suppressed_due_to_snapshot_bridge_count | quarantined | quarantine_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 10 | 1 | 1 | (1,) | true | false | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | false | 0 | 1 | 0 | 0 | 0 | true | snapshot_reset_bridge_failure |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 10 | 1 | 1 | (1,) | true | false | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | false | 0 | 1 | 0 | 0 | 0 | true | snapshot_reset_bridge_failure |

## Bridge Event Results
| file_path | bridge_rule_satisfied | bridge_event_detected_count | snapshot_reset_clean_seed_count | snapshot_bridge_event_count | ofi_suppressed_due_to_snapshot_bridge_count |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | false | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | false | 0 | 0 | 0 | 0 |

## Quarantine Results
| file_path | quarantined | quarantine_reason | snapshot_reset_chain_failure_count | quarantined_segment_count | ofi_suppressed_due_to_quarantine_count |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | true | snapshot_reset_bridge_failure | 1 | 1 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | true | snapshot_reset_bridge_failure | 1 | 1 | 0 |

## OFI Suppression Results
| file_path | total_ofi_emitted_count | ofi_suppressed_due_to_quarantine_count | ofi_suppressed_due_to_snapshot_bridge_count | total_warmup_none_count |
| --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 1 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 1 |

## Segment Cleanliness Results
| file_path | clean_segment_count | dirty_segment_count | all_segments_clean | total_sequence_gap_count |
| --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 0 | 1 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 0 | 1 | false | 0 |

## Source-Gap Regression Check
Synthetic source-gap regression passed; the reusable policy still splits source gaps into `source_sequence_gap` boundaries and keeps those segments clean.

## What Worked
- The reusable policy module was used directly.
- The dirty snapshot/reset files were used deterministically.
- The Binance bridge rule was applied to the raw files.
- No OFI artifacts were written.

## What Failed Or Remains Unknown
- Some snapshot/reset candidates remain quarantined if the bridge rule is not satisfied.
- A different bounded sample could still expose additional edge cases.
- This remains a bounded validation only.

## What Is Safe
- Bounded read-only validation of the dirty snapshot/reset candidates.
- Quarantine of unsafe snapshot/reset chains.
- Preservation of source-gap behavior.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
policy_module_used_directly, ofi_engine_behavior_unchanged, binance_snapshot_bridge_rule_implemented, snapshot_reset_bridge_events_detected, snapshot_reset_bridge_ofi_suppressed, invalid_snapshot_reset_chains_quarantined, quarantined_segments_emit_no_ofi, no_ofi_state_crosses_quarantine, source_gap_behavior_unchanged, bounded_raw_snapshot_reset_validation_completed, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked.

## Required Next Step
Use the quarantine behavior only after this bounded validation is reviewed; do not promote the workflow to full reconstruction.

This validation does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.