# V9.2 L2 OFI Snapshot/Reset Dirty Case Diagnostic

## Purpose
Determine why the observed raw snapshot/reset-like candidate files remained dirty under the reusable segmented OFI reconstruction policy.

## Inputs
- `max_events_per_file`: `75000`
- `context_packets_around_snapshot`: `10`
- `selected_candidate_count`: `2`

## Read-Only Guardrails
- Read-only bounded diagnostic only.
- No OFI artifacts are written.
- No policy or OFIEngine behavior is changed.
- No full-corpus reconstruction is attempted.

## Diagnostic Method
- Raw rows were converted to `L2Packet` objects in memory.
- Packets were ordered using the reusable policy `packet_sort_key`.
- Snapshot/reset-like packets were identified with `is_snapshot_or_reset`.
- Segmentation and OFIEngine replay were delegated to the reusable policy module.

## Candidate Files
| file_path | candidate_reason | file_date | file_hour |
| --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | dirty_snapshot_reset_candidate | 2026-05-26 | 00 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | dirty_snapshot_reset_candidate | 2026-05-26 | 07 |

## Executive Finding
2 dirty snapshot/reset candidate files were processed in bounded read-only mode.
Raw snapshot/reset-like packets were observed in `2` files.
Dirty snapshot/reset candidates remained dirty in `2` files.
This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use.

## Per-File Dirty Case Results
| file_path | file_date | file_hour | rows_scanned | packet_count | snapshot_like_packet_count | snapshot_like_packet_indexes | first_packet_is_snapshot_reset | segment_count | snapshot_reset_boundary_count | source_gap_boundary_count | dirty_segment_count | clean_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | dirty_segment_ids | dirty_segment_contains_snapshot_reset | snapshot_packet_position_in_dirty_segment | dirty_segment_first_packet_is_snapshot_reset | next_packet_after_snapshot_prev_final_update_id | snapshot_packet_final_update_id | next_packet_chains_to_snapshot | hypothesis_a_first_packet_snapshot_supported | hypothesis_b_next_packet_chain_failure_supported | hypothesis_c_seed_insufficient_supported | root_cause_classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 75000 | 1405 | 1 | (1,) | true | 1 | 0 | 0 | 1 | 0 | false | 0 | 1 | 1 | (1,) | true | 1 | true | 10630308765301 | 10630308766039 | false | true | true | false | post_snapshot_chain_failure |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 75000 | 2059 | 1 | (1,) | true | 1 | 0 | 0 | 1 | 0 | false | 0 | 1 | 1 | (1,) | true | 1 | true | 10632397663856 | 10632397665344 | false | true | true | false | post_snapshot_chain_failure |

## Snapshot Context Windows
| file_path | snapshot_packet_indexes | snapshot_context_windows |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | (1,) | ({'snapshot_packet_index': 1, 'previous_packets': [], 'snapshot_packet': {'packet_index': 1, 'event_time': 1779753602691, 'transaction_time': 1779753602680, 'received_time': 1779753602691000064, 'first_update_id': None, 'final_update_id': 10630308766039, 'prev_final_update_id': None, 'event_type': 'snapshot', 'is_snapshot_or_reset': True, 'bid_level_count': 1000, 'ask_level_count': 1000, 'total_level_count': 2000}, 'next_packets': [{'packet_index': 2, 'event_time': 1779753602702, 'transaction_time': 1779753602680, 'received_time': 1779753602855823616, 'first_update_id': 10630308765743, 'final_update_id': 10630308766039, 'prev_final_update_id': 10630308765301, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 5, 'ask_level_count': 1, 'total_level_count': 6}, {'packet_index': 3, 'event_time': 1779753602728, 'transaction_time': 1779753602716, 'received_time': 1779753602914366464, 'first_update_id': 10630308766817, 'final_update_id': 10630308767436, 'prev_final_update_id': 10630308766039, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 3, 'ask_level_count': 4, 'total_level_count': 7}, {'packet_index': 4, 'event_time': 1779753602760, 'transaction_time': 1779753602757, 'received_time': 1779753602915563008, 'first_update_id': 10630308768382, 'final_update_id': 10630308769605, 'prev_final_update_id': 10630308767436, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 7, 'ask_level_count': 7, 'total_level_count': 14}, {'packet_index': 5, 'event_time': 1779753602786, 'transaction_time': 1779753602783, 'received_time': 1779753602915883776, 'first_update_id': 10630308769724, 'final_update_id': 10630308770684, 'prev_final_update_id': 10630308769605, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 5, 'ask_level_count': 3, 'total_level_count': 8}, {'packet_index': 6, 'event_time': 1779753602814, 'transaction_time': 1779753602805, 'received_time': 1779753602938336256, 'first_update_id': 10630308770877, 'final_update_id': 10630308771601, 'prev_final_update_id': 10630308770684, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 3, 'ask_level_count': 3, 'total_level_count': 6}, {'packet_index': 7, 'event_time': 1779753602842, 'transaction_time': 1779753602819, 'received_time': 1779753602959836672, 'first_update_id': 10630308772166, 'final_update_id': 10630308772330, 'prev_final_update_id': 10630308771601, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 1, 'ask_level_count': 1, 'total_level_count': 2}, {'packet_index': 8, 'event_time': 1779753602870, 'transaction_time': 1779753602845, 'received_time': 1779753602987692800, 'first_update_id': 10630308773165, 'final_update_id': 10630308773237, 'prev_final_update_id': 10630308772330, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 0, 'ask_level_count': 1, 'total_level_count': 1}, {'packet_index': 9, 'event_time': 1779753602898, 'transaction_time': 1779753602886, 'received_time': 1779753603014735616, 'first_update_id': 10630308774563, 'final_update_id': 10630308775316, 'prev_final_update_id': 10630308773237, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 2, 'ask_level_count': 0, 'total_level_count': 2}, {'packet_index': 10, 'event_time': 1779753602926, 'transaction_time': 1779753602925, 'received_time': 1779753603042661120, 'first_update_id': 10630308775880, 'final_update_id': 10630308777864, 'prev_final_update_id': 10630308775316, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 6, 'ask_level_count': 3, 'total_level_count': 9}, {'packet_index': 11, 'event_time': 1779753602952, 'transaction_time': 1779753602948, 'received_time': 1779753603068716288, 'first_update_id': 10630308778060, 'final_update_id': 10630308781435, 'prev_final_update_id': 10630308777864, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 8, 'ask_level_count': 11, 'total_level_count': 19}]},) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | (1,) | ({'snapshot_packet_index': 1, 'previous_packets': [], 'snapshot_packet': {'packet_index': 1, 'event_time': 1779778804101, 'transaction_time': 1779778804093, 'received_time': 1779778804100999936, 'first_update_id': None, 'final_update_id': 10632397665344, 'prev_final_update_id': None, 'event_type': 'snapshot', 'is_snapshot_or_reset': True, 'bid_level_count': 1000, 'ask_level_count': 1000, 'total_level_count': 2000}, 'next_packets': [{'packet_index': 2, 'event_time': 1779778804098, 'transaction_time': 1779778804097, 'received_time': 1779778804605573632, 'first_update_id': 10632397663969, 'final_update_id': 10632397665664, 'prev_final_update_id': 10632397663856, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 25, 'ask_level_count': 9, 'total_level_count': 34}, {'packet_index': 3, 'event_time': 1779778804124, 'transaction_time': 1779778804122, 'received_time': 1779778804605573632, 'first_update_id': 10632397665774, 'final_update_id': 10632397668363, 'prev_final_update_id': 10632397665664, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 11, 'ask_level_count': 10, 'total_level_count': 21}, {'packet_index': 4, 'event_time': 1779778804152, 'transaction_time': 1779778804151, 'received_time': 1779778804605573632, 'first_update_id': 10632397668626, 'final_update_id': 10632397671617, 'prev_final_update_id': 10632397668363, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 17, 'ask_level_count': 3, 'total_level_count': 20}, {'packet_index': 5, 'event_time': 1779778804178, 'transaction_time': 1779778804174, 'received_time': 1779778804605573632, 'first_update_id': 10632397671673, 'final_update_id': 10632397673781, 'prev_final_update_id': 10632397671617, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 15, 'ask_level_count': 19, 'total_level_count': 34}, {'packet_index': 6, 'event_time': 1779778804204, 'transaction_time': 1779778804201, 'received_time': 1779778804605573632, 'first_update_id': 10632397674003, 'final_update_id': 10632397676051, 'prev_final_update_id': 10632397673781, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 17, 'ask_level_count': 10, 'total_level_count': 27}, {'packet_index': 7, 'event_time': 1779778804232, 'transaction_time': 1779778804229, 'received_time': 1779778804605573632, 'first_update_id': 10632397676585, 'final_update_id': 10632397679154, 'prev_final_update_id': 10632397676051, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 11, 'ask_level_count': 9, 'total_level_count': 20}, {'packet_index': 8, 'event_time': 1779778804260, 'transaction_time': 1779778804259, 'received_time': 1779778804608458240, 'first_update_id': 10632397679459, 'final_update_id': 10632397683004, 'prev_final_update_id': 10632397679154, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 13, 'ask_level_count': 12, 'total_level_count': 25}, {'packet_index': 9, 'event_time': 1779778804286, 'transaction_time': 1779778804285, 'received_time': 1779778804609493760, 'first_update_id': 10632397683136, 'final_update_id': 10632397686409, 'prev_final_update_id': 10632397683004, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 18, 'ask_level_count': 11, 'total_level_count': 29}, {'packet_index': 10, 'event_time': 1779778804314, 'transaction_time': 1779778804313, 'received_time': 1779778804610010368, 'first_update_id': 10632397686559, 'final_update_id': 10632397690373, 'prev_final_update_id': 10632397686409, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 21, 'ask_level_count': 11, 'total_level_count': 32}, {'packet_index': 11, 'event_time': 1779778804342, 'transaction_time': 1779778804341, 'received_time': 1779778804610738176, 'first_update_id': 10632397690489, 'final_update_id': 10632397693871, 'prev_final_update_id': 10632397690373, 'event_type': 'update', 'is_snapshot_or_reset': False, 'bid_level_count': 15, 'ask_level_count': 5, 'total_level_count': 20}]},) |

## Dirty Segment Anatomy
| file_path | dirty_segment_details |
| --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | ({'segment_id': 1, 'start_reason': 'file_start', 'boundary_reason': 'sample_end', 'packet_count': 1405, 'contains_snapshot_reset_packet': True, 'snapshot_packet_position_in_segment': 1, 'first_packet_is_snapshot_reset': True, 'sequence_gap_count': 1, 'warmup_none_count': 1, 'ofi_emitted_count': 0, 'previous_final_update_id': None, 'snapshot_packet_final_update_id': 10630308766039, 'next_packet_prev_final_update_id': 10630308765301, 'next_packet_chains_to_snapshot': False},) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | ({'segment_id': 1, 'start_reason': 'file_start', 'boundary_reason': 'sample_end', 'packet_count': 2059, 'contains_snapshot_reset_packet': True, 'snapshot_packet_position_in_segment': 1, 'first_packet_is_snapshot_reset': True, 'sequence_gap_count': 1, 'warmup_none_count': 1, 'ofi_emitted_count': 0, 'previous_final_update_id': None, 'snapshot_packet_final_update_id': 10632397665344, 'next_packet_prev_final_update_id': 10632397663856, 'next_packet_chains_to_snapshot': False},) |

## Hypothesis A: First Packet Snapshot/Reset
| file_path | first_packet_is_snapshot_reset | hypothesis_a_first_packet_snapshot_supported |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | true | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | true | true |

## Hypothesis B: Post-Snapshot Chain Failure
| file_path | dirty_segment_contains_snapshot_reset | next_packet_after_snapshot_prev_final_update_id | snapshot_packet_final_update_id | next_packet_chains_to_snapshot | hypothesis_b_next_packet_chain_failure_supported |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | true | 10630308765301 | 10630308766039 | false | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | true | 10632397663856 | 10632397665344 | false | true |

## Hypothesis C: Snapshot Seed Insufficient
| file_path | dirty_segment_contains_snapshot_reset | dirty_segment_first_packet_is_snapshot_reset | dirty_segment_count | all_segments_clean | hypothesis_c_seed_insufficient_supported |
| --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | true | true | 1 | false | false |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | true | true | 1 | false | false |

## Aggregate Summary
| selected_candidate_count | total_rows_scanned | total_packet_count | total_snapshot_like_packet_count | files_with_first_packet_snapshot_reset | total_segment_count | total_snapshot_reset_boundary_count | total_source_gap_boundary_count | files_all_segments_clean | files_with_dirty_segments | total_dirty_segment_count | total_sequence_gap_count | hypothesis_a_supported_file_count | hypothesis_b_supported_file_count | hypothesis_c_supported_file_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 150000 | 3464 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | 0 |

## What Worked
- The reusable policy module was used directly.
- The dirty snapshot/reset candidate files were used deterministically.
- Snapshot/reset-like packets were observed in the bounded raw sample.
- The diagnostic remained in-memory and read-only.

## What Failed Or Remains Unknown
- The observed snapshot/reset-like packets did not produce clean segmented OFI processing in this bounded sample.
- No policy or OFIEngine behavior was changed.
- A different bounded sample could still produce a different hypothesis mix.

## What Is Safe
- Bounded read-only diagnostics on the discovered dirty snapshot/reset files.
- Using the observed patterns for future bounded diagnostics.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
policy_module_used_directly, dirty_snapshot_candidates_used_deterministically, raw_snapshot_reset_packets_observed, dirty_segments_associated_with_snapshot_reset, snapshot_first_packet_hypothesis_evaluated, post_snapshot_chain_hypothesis_evaluated, snapshot_seed_insufficient_hypothesis_evaluated, root_cause_classified_bounded_only, no_policy_change_made, no_ofi_engine_change_made, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked.

## Required Next Step
Use the dirty snapshot/reset candidates only for bounded follow-up diagnostics; do not change the policy or promote the workflow to full reconstruction.

This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use.