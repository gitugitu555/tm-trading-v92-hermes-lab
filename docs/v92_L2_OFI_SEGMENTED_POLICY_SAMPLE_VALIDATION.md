# V9.2 L2 OFI Segmented Policy Sample Validation

## Purpose
Validate the reusable segmented reconstruction policy module on a second bounded raw L2 sample using the module as the source of truth for ordering, segmentation, gap handling, and OFIEngine segment processing.

## Inputs
- `l2_root`: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- `max_files`: `18`
- `selected_file_count`: `18`

## Read-Only Guardrails
- Read-only validation only.
- No OFI artifacts are written.
- No alpha, paper, or live approval is granted.
- No full-corpus reconstruction is attempted.

## Executive Finding
18 bounded raw L2 files were converted into `L2Packet` objects and processed by the reusable segmented policy module.
9 selected files were new relative to the prior 12-file rehearsal and 9 were repeated.
Segments remained clean in sample `True` with `0` dirty files.
This validation does not approve OFI for production, paper trading, live trading, or alpha use.

## File Selection
| selected_index | file_path | file_date | is_repeated_from_previous_rehearsal |
| --- | --- | --- | --- |
| 1 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true |
| 2 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true |
| 3 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true |
| 4 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true |
| 5 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true |
| 6 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true |
| 7 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true |
| 8 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true |
| 9 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | true |
| 10 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 11 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 12 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 13 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 14 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/12/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 15 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false |
| 16 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-18/00/BTCUSDT_orderbook.parquet.zst | 2025-07-18 | false |
| 17 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-06/19/BTCUSDT_orderbook.parquet.zst | 2025-08-06 | false |
| 18 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-26/14/BTCUSDT_orderbook.parquet.zst | 2025-08-26 | false |

## Module Usage
- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.
- Raw rows are converted to `L2Packet` objects in-memory before segmentation.
- Segmentation is delegated to the policy module.

## Per-File Policy Results
| file_path | file_date | is_repeated_from_previous_rehearsal | rows_scanned | packet_count | segment_count | meaningful_segment_count | source_gap_boundary_count | snapshot_reset_boundary_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | min_segment_packet_count | max_segment_packet_count | one_packet_segment_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true | 6399093 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true | 2939969 | 10000 | 2 | 2 | 1 | 0 | 2 | 0 | true | 9998 | 2 | 0 | 4292 | 5708 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true | 6145542 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | true | 6237009 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true | 3695019 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true | 3925684 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true | 2981156 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | true | 2847415 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | true | 8286270 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9990 | 10 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 6450069 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 6214563 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 6273087 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 5937414 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/12/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 5830161 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | false | 6460860 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-18/00/BTCUSDT_orderbook.parquet.zst | 2025-07-18 | false | 4383254 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-06/19/BTCUSDT_orderbook.parquet.zst | 2025-08-06 | false | 3319845 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-26/14/BTCUSDT_orderbook.parquet.zst | 2025-08-26 | false | 8989160 | 10000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 9999 | 1 | 0 | 10000 | 10000 | 0 |

## Aggregate Policy Summary
| selected_file_count | new_file_count | repeated_file_count | total_packet_count | total_segment_count | total_meaningful_segment_count | total_source_gap_boundary_count | total_snapshot_reset_boundary_count | files_all_segments_clean | files_with_dirty_segments | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | 9 | 9 | 180000 | 19 | 19 | 1 | 0 | 18 | 0 | 179972 | 28 | 0 |

## Segment Boundary Results
- Source gaps and snapshot/reset packets were converted into segment boundaries by the policy module.
- OFIEngine was fresh per segment and no OFI state crossed boundaries.

## Join Readiness Sample
| file_date | bar_file_found | bar_row_count | join_attempted | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- | --- |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2026-06-07 | true | 79 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-07-18 | true | 646 | true | true | null |
| 2025-08-06 | true | 629 | true | true | null |
| 2025-08-26 | true | 629 | true | true | null |

## What Worked
- The reusable policy module was used directly.
- L2Packet conversion succeeded on bounded raw rows.
- Segments remained clean in this bounded sample.
- Join-readiness checks preserved bar count where attempted.

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
policy_module_used_directly, l2packet_conversion_successful, segmentation_policy_reused, source_gaps_as_segment_boundaries, snapshot_resets_as_segment_boundaries, segments_clean_in_second_sample, dirty_segments_detected, ofi_values_emitted_in_segments, join_readiness_sample_passed, segmented_policy_sample_validated, segmented_reconstruction_not_globally_approved, broader_reconstruction_blocked, alpha_blocked, paper_live_blocked.

## Required Next Step
Use the policy module in another bounded read-only rehearsal or diagnostic sample before any broader reconstruction policy change.

This validation does not approve OFI for production, paper trading, live trading, or alpha use.