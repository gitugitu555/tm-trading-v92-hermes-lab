# V9.2 L2 OFI Discovered Policy Path Candidate Validation

## Purpose
Validate the reusable segmented reconstruction policy module on the raw L2 candidate files discovered as likely to exercise previously unobserved policy paths.

## Inputs
- `max_events_per_file`: `50000`
- `selected_candidate_count`: `8`

## Read-Only Guardrails
- Read-only bounded validation only.
- No OFI artifacts are written.
- No alpha, paper, or live approval is granted.
- No full-corpus reconstruction is attempted.

## Candidate Sources
| file_path | candidate_reason | file_date | file_hour |
| --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 2026-05-26 | 00 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 2026-05-26 | 07 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 11 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-03 | 00 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 00 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 23 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-02 | 21 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-12-22 | 07 |

## Module Usage
- The script imports and uses `L2Packet`, `packet_sort_key`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.
- Raw rows are converted to `L2Packet` objects in-memory before segmentation.
- Segmentation and per-segment OFIEngine processing are delegated to the policy module.

## Executive Finding
8 discovered raw candidate files were processed in bounded read-only mode.
Snapshot/reset-like candidates selected: `2`.
Source-gap/timestamp candidates selected: `6`.
Snapshot/reset-like raw candidates were observed, but they remained dirty in this bounded sample.
Missing transaction_time fallback observed in raw candidate sample: `False`.
This validation does not approve OFI for production, paper trading, live trading, or alpha use.

## Per-File Candidate Results
| file_path | candidate_reason | file_date | file_hour | rows_scanned | packet_count | missing_transaction_time_count | missing_first_update_id_count | missing_prev_final_update_id_count | snapshot_like_packet_count | timestamp_fallback_used | timestamp_non_monotonic_hint_count | event_time_non_monotonic_hint_count | transaction_time_non_monotonic_hint_count | received_time_non_monotonic_hint_count | source_gap_boundary_count | snapshot_reset_boundary_count | segment_count | meaningful_segment_count | one_packet_segment_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | min_segment_packet_count | max_segment_packet_count | side_mapping_unknown_count | policy_module_used_directly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 2026-05-26 | 00 | 50000 | 890 | 0 | 1 | 1 | 1 | false | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | false | 0 | 1 | 1 | 890 | 890 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 2026-05-26 | 07 | 50000 | 1178 | 0 | 1 | 1 | 1 | false | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | false | 0 | 1 | 1 | 1178 | 1178 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 11 | 50000 | 4215 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 684 | 0 | 685 | 84 | 601 | 685 | 0 | true | 0 | 4215 | 0 | 1 | 428 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-03 | 00 | 50000 | 3121 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 468 | 0 | 469 | 91 | 378 | 469 | 0 | true | 0 | 3121 | 0 | 1 | 512 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 00 | 50000 | 2582 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 190 | 0 | 191 | 48 | 143 | 191 | 0 | true | 0 | 2582 | 0 | 1 | 767 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-01 | 23 | 50000 | 2603 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 158 | 0 | 159 | 15 | 144 | 159 | 0 | true | 0 | 2603 | 0 | 1 | 612 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-07-02 | 21 | 50000 | 5036 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 656 | 0 | 657 | 122 | 535 | 657 | 0 | true | 0 | 5036 | 0 | 1 | 677 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2025-12-22 | 07 | 50000 | 828 | 0 | 0 | 0 | 0 | false | 0 | 0 | 0 | 0 | 2 | 0 | 3 | 2 | 1 | 3 | 0 | true | 825 | 3 | 0 | 1 | 798 | 0 | true |

## Aggregate Candidate Summary
| selected_candidate_count | snapshot_reset_candidate_count | source_gap_timestamp_candidate_count | total_rows_scanned | total_packet_count | total_segment_count | total_meaningful_segment_count | total_snapshot_like_packet_count | total_snapshot_reset_boundary_count | total_source_gap_boundary_count | files_with_snapshot_reset_boundaries | files_with_source_gap_boundaries | files_with_timestamp_ordering_hints | files_with_timestamp_fallback | files_all_segments_clean | files_with_dirty_segments | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | unknown_side_mapping_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 2 | 6 | 400000 | 20453 | 2166 | 364 | 2 | 0 | 2158 | 0 | 6 | 1 | 0 | 6 | 2 | 825 | 17562 | 2 | 0 |

## Snapshot/Reset Raw Candidate Results
| file_path | candidate_reason | snapshot_like_packet_count | snapshot_reset_boundary_count | segment_count | all_segments_clean |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 1 | 0 | 1 | false |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | snapshot_reset_candidate | 1 | 0 | 1 | false |

## Source-Gap Raw Candidate Results
| file_path | candidate_reason | source_gap_boundary_count | segment_count | all_segments_clean |
| --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 684 | 685 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 468 | 469 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 190 | 191 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 158 | 159 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 656 | 657 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | source_gap_timestamp_candidate | 2 | 3 | true |

## Timestamp Ordering Results
| file_path | timestamp_non_monotonic_hint_count | event_time_non_monotonic_hint_count | transaction_time_non_monotonic_hint_count | received_time_non_monotonic_hint_count | all_segments_clean |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | false |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 0 | 1 | 0 | 0 | false |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 0 | true |

## Transaction-Time Fallback Results
No raw missing transaction_time fallback candidates were found in this bounded validation window.

## OFIEngine Segment Results
| file_path | segment_count | meaningful_segment_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | min_segment_packet_count | max_segment_packet_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 1 | 1 | 0 | 1 | false | 0 | 1 | 1 | 890 | 890 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 1 | 1 | 0 | 1 | false | 0 | 1 | 1 | 1178 | 1178 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 685 | 84 | 685 | 0 | true | 0 | 4215 | 0 | 1 | 428 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 469 | 91 | 469 | 0 | true | 0 | 3121 | 0 | 1 | 512 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 191 | 48 | 191 | 0 | true | 0 | 2582 | 0 | 1 | 767 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 159 | 15 | 159 | 0 | true | 0 | 2603 | 0 | 1 | 612 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 657 | 122 | 657 | 0 | true | 0 | 5036 | 0 | 1 | 677 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 3 | 2 | 3 | 0 | true | 825 | 3 | 0 | 1 | 798 |

## What Worked
- The reusable policy module was used directly.
- Discovered raw candidate files were used deterministically.
- Observed source gaps were processed as segment boundaries.
- The bounded candidate files were handled without writing OFI artifacts.

## What Failed Or Remains Unknown
- Snapshot/reset-like raw candidates were observed, but this bounded sample did not produce clean snapshot_reset boundaries and those files remained dirty.
- No missing transaction_time fallback raw candidate was observed in this bounded candidate set.
- A different bounded candidate set could still expose additional cases.
- This remains a bounded validation only.

## What Is Safe
- Bounded read-only validation of discovered raw candidate files.
- Using these files for future bounded diagnostics or synthetic reproductions.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
policy_module_used_directly, discovered_candidates_used_deterministically, raw_snapshot_reset_candidates_validated, raw_source_gap_timestamp_candidates_validated, timestamp_ordering_candidates_validated, raw_missing_transaction_time_fallback_not_observed, segments_clean_in_discovered_candidate_sample, ofi_values_emitted_in_memory_only, no_ofi_artifacts_written, segmented_policy_discovered_candidate_validated, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked.

## Required Next Step
Use the discovered candidate files only for bounded diagnostics or additional synthetic reproductions of the unexercised policy paths.

This validation does not approve OFI for production, paper trading, live trading, or alpha use.