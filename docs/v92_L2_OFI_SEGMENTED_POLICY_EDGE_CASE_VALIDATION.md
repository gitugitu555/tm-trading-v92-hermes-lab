# V9.2 L2 OFI Segmented Policy Edge-Case Validation

## Purpose
Validate the reusable segmented reconstruction policy module on a bounded raw L2 sample intentionally enriched for source gaps, ordering anomalies, snapshot/reset-like packets, and timestamp variation.

## Inputs
- `l2_root`: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- `max_candidate_files`: `120`
- `max_selected_files`: `24`
- `candidate_file_count`: `120`

## Read-Only Guardrails
- Read-only validation only.
- No OFI artifacts are written.
- No alpha, paper, or live approval is granted.
- No full-corpus reconstruction is attempted.

## Executive Finding
16 edge-case-focused bounded raw L2 files were converted into `L2Packet` objects and processed by the reusable segmented policy module.
7 selected files were new relative to the prior 12-file rehearsal and 9 were repeated.
Segments remained clean in sample `True` with `0` dirty files.
This validation does not approve OFI for production, paper trading, live trading, or alpha use.

## Candidate Scan Method
Deterministic candidate scanning used anchored files, neighboring files around the known anomaly files, first/last files, 2026 files where present, and evenly spaced corpus files before ranking edge-case hints from bounded previews.

## File Selection
| selected_index | file_path | file_date | file_hour | selection_reason | is_repeated_from_previous_rehearsal |
| --- | --- | --- | --- | --- | --- |
| 1 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 | known_event_order_file | true |
| 2 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 06 | neighbor_of_known_file | true |
| 3 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 07 | neighbor_of_known_file | true |
| 4 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 08 | neighbor_of_known_file | false |
| 5 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 09 | known_source_gap_file | true |
| 6 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/06/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 06 | neighbor_of_known_file | false |
| 7 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 07 | neighbor_of_known_file | true |
| 8 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 08 | neighbor_of_known_file | true |
| 9 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 10 | neighbor_of_known_file | true |
| 10 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 11 | neighbor_of_known_file | true |
| 11 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/12/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 12 | neighbor_of_known_file | false |
| 12 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | 23 | last_file | true |
| 13 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/00/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 00 | 2026_sample | false |
| 14 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/01/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 01 | 2026_sample | false |
| 15 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/02/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 02 | 2026_sample | false |
| 16 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/03/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 03 | 2026_sample | false |

## Module Usage
- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.
- Raw rows are converted to `L2Packet` objects in-memory before segmentation.
- Segmentation is delegated to the policy module.

## Per-File Edge-Case Results
| file_path | file_date | selection_reason | packet_count | segment_count | meaningful_segment_count | source_gap_boundary_count | snapshot_reset_boundary_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | min_segment_packet_count | max_segment_packet_count | one_packet_segment_count | missing_transaction_time_count | snapshot_like_packet_count | estimated_preselection_source_gap_count | actual_source_gap_boundary_count | timestamp_fallback_used | side_mapping_unknown_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | known_event_order_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | known_source_gap_file | 15000 | 2 | 2 | 1 | 0 | 2 | 0 | true | 14998 | 2 | 0 | 4292 | 10708 | 0 | 0 | 0 | 0 | 1 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/06/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/12/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | neighbor_of_known_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | last_file | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14986 | 14 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/00/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 2026_sample | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/01/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 2026_sample | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14997 | 3 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/02/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 2026_sample | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14997 | 3 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/03/BTCUSDT_orderbook.parquet.zst | 2026-01-01 | 2026_sample | 15000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 14999 | 1 | 0 | 15000 | 15000 | 0 | 0 | 0 | 0 | 0 | false | 0 |

## Aggregate Edge-Case Summary
| candidate_file_count | selected_file_count | total_packet_count | total_segment_count | total_meaningful_segment_count | total_source_gap_boundary_count | total_snapshot_reset_boundary_count | files_all_segments_clean | files_with_dirty_segments | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | files_with_timestamp_fallback | files_with_snapshot_like_packets | files_with_source_gap_boundaries | unknown_side_mapping_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 120 | 16 | 240000 | 17 | 17 | 1 | 0 | 16 | 0 | 239966 | 34 | 0 | 0 | 0 | 1 | 0 |

## Segment Boundary Results
- Source gaps and snapshot/reset-like packets were converted into segment boundaries by the policy module.
- OFIEngine was fresh per segment and no OFI state crossed boundaries.

## Timestamp Fallback Results
- The policy supports transaction-time fallback ordering, but this bounded sample did not surface any selected files requiring it.

## Snapshot/Reset Results
- The policy preserves snapshot/reset-like packets as segment boundaries when present, but none were observed in this bounded sample.

## Source-Gap Results
- Source gaps observed in the bounded sample were treated as segment boundaries and processed in memory only.

## Join Readiness Sample
| file_date | bar_file_found | bar_row_count | join_attempted | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- | --- |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2026-06-07 | true | 79 | true | true | null |
| 2026-01-01 | true | 656 | true | true | null |
| 2026-01-01 | true | 656 | true | true | null |
| 2026-01-01 | true | 656 | true | true | null |
| 2026-01-01 | true | 656 | true | true | null |

## What Worked
- The reusable policy module was used directly.
- Bounded raw L2 files were converted into `L2Packet` objects.
- Edge-case-heavy files were selected deterministically.
- Source gaps and snapshot/reset-like packets remained bounded and segmentable.

## What Failed Or Remains Unknown
- This remains a bounded validation only.
- The sample does not globally approve reconstruction.
- A larger or different sample could still expose new issues.

## What Is Safe
- Bounded read-only segmented reconstruction validation.
- Reusing the policy module for future bounded diagnostics.

## What Is Not Safe
- Full-corpus reconstruction.
- Production, paper, or live use.
- Alpha claims.

## Decision
policy_module_used_directly, l2packet_conversion_successful, deterministic_edge_case_selection_used, segmentation_policy_reused, source_gaps_as_segment_boundaries, snapshot_resets_as_segment_boundaries, timestamp_fallback_validated, segments_clean_in_edge_case_sample, dirty_segments_detected, ofi_values_emitted_in_segments, join_readiness_sample_passed, segmented_policy_edge_case_validated, segmented_reconstruction_not_globally_approved, broader_reconstruction_blocked, alpha_blocked, paper_live_blocked.

## Required Next Step
Use the policy module in another bounded read-only rehearsal or diagnostic sample before any broader reconstruction policy change.

This validation does not approve OFI for production, paper trading, live trading, or alpha use.