# V9.2 L2 OFI Unexercised Policy Path Discovery

## Purpose
Find bounded raw L2 files that may exercise policy paths not yet observed in the bounded segmented reconstruction rehearsals, focusing on snapshot/reset-like packets, missing transaction_time fallback cases, source-gap hints, ordering anomalies, and side-mapping anomalies.

## Inputs
- `l2_root`: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- `symbol`: `BTCUSDT`
- `max_candidate_files`: `360`
- `candidate_file_count`: `8074`
- `max_selected_findings`: `40`

## Read-Only Guardrails
- Read-only bounded discovery only.
- No OFI artifacts are written.
- No alpha, paper, or live approval is granted.
- No full-corpus reconstruction is attempted.

## Discovery Method
Deterministic candidate selection used anchored files, neighboring files around the known anomaly files, first and last files, month-open and hour-boundary files, evenly spaced corpus files, and 2026 files where present. Each candidate was previewed only on bounded rows and scored from packet-level hints.

## Candidate Selection
- Candidate files discovered: `8074`
- Candidate files previewed: `360`
- Selected findings reported: `40`

## Executive Finding
Bounded discovery previewed `360` candidate raw L2 files and ranked `40` findings.
Raw snapshot/reset-like candidates found: `2`.
Raw missing transaction_time fallback candidates found: `0`.
Raw source-gap candidates found: `6`.
Timestamp ordering hints found: `5`.
Unknown side-mapping hints found: `0`.
This discovery does not approve OFI for production, paper trading, live trading, or alpha use.

## Top Candidate Findings
| candidate_file_path | file_date | file_hour | candidate_score | candidate_reasons | preview_row_count | preview_packet_count | snapshot_like_packet_count | missing_transaction_time_count | estimated_source_gap_count | timestamp_non_monotonic_hint_count | side_mapping_unknown_count | missing_required_column_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 6105150 | snapshot_reset_like, missing_first_update_id, missing_prev_final_update_id, event_time_non_monotonicity | 25000 | 460 | 1 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 6105100 | snapshot_reset_like, missing_first_update_id, missing_prev_final_update_id, repeated_final_update_id | 25000 | 553 | 1 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 | 839400 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 25000 | 3529 | 0 | 0 | 663 | 252 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 | 810200 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 25000 | 2320 | 0 | 0 | 673 | 196 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 | 647000 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 25000 | 2168 | 0 | 0 | 458 | 270 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 | 278900 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 25000 | 1159 | 0 | 0 | 169 | 157 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 | 276300 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 25000 | 1903 | 0 | 0 | 165 | 159 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2025-12-22 | 07 | 2000 | estimated_source_gap | 25000 | 484 | 0 | 0 | 2 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 | 0 |  | 25000 | 48 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 06 | 0 |  | 25000 | 102 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 07 | 0 |  | 25000 | 112 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 08 | 0 |  | 25000 | 73 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/23/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 23 | 0 |  | 25000 | 126 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-29/03/BTCUSDT_orderbook.parquet.zst | 2025-06-29 | 03 | 0 |  | 25000 | 65 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-30/02/BTCUSDT_orderbook.parquet.zst | 2025-06-30 | 02 | 0 |  | 25000 | 73 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/20/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 20 | 0 |  | 25000 | 309 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-04/18/BTCUSDT_orderbook.parquet.zst | 2025-07-04 | 18 | 0 |  | 25000 | 288 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-05/17/BTCUSDT_orderbook.parquet.zst | 2025-07-05 | 17 | 0 |  | 25000 | 304 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-06/15/BTCUSDT_orderbook.parquet.zst | 2025-07-06 | 15 | 0 |  | 25000 | 277 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-07/14/BTCUSDT_orderbook.parquet.zst | 2025-07-07 | 14 | 0 |  | 25000 | 88 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-08/12/BTCUSDT_orderbook.parquet.zst | 2025-07-08 | 12 | 0 |  | 25000 | 168 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-09/11/BTCUSDT_orderbook.parquet.zst | 2025-07-09 | 11 | 0 |  | 25000 | 471 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-10/09/BTCUSDT_orderbook.parquet.zst | 2025-07-10 | 09 | 0 |  | 25000 | 334 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-11/00/BTCUSDT_orderbook.parquet.zst | 2025-07-11 | 00 | 0 |  | 25000 | 165 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-11/08/BTCUSDT_orderbook.parquet.zst | 2025-07-11 | 08 | 0 |  | 25000 | 145 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-12/06/BTCUSDT_orderbook.parquet.zst | 2025-07-12 | 06 | 0 |  | 25000 | 523 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-13/05/BTCUSDT_orderbook.parquet.zst | 2025-07-13 | 05 | 0 |  | 25000 | 391 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-14/03/BTCUSDT_orderbook.parquet.zst | 2025-07-14 | 03 | 0 |  | 25000 | 230 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-15/02/BTCUSDT_orderbook.parquet.zst | 2025-07-15 | 02 | 0 |  | 25000 | 45 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-16/00/BTCUSDT_orderbook.parquet.zst | 2025-07-16 | 00 | 0 |  | 25000 | 265 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-16/23/BTCUSDT_orderbook.parquet.zst | 2025-07-16 | 23 | 0 |  | 25000 | 154 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-17/21/BTCUSDT_orderbook.parquet.zst | 2025-07-17 | 21 | 0 |  | 25000 | 55 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-18/20/BTCUSDT_orderbook.parquet.zst | 2025-07-18 | 20 | 0 |  | 25000 | 162 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-19/00/BTCUSDT_orderbook.parquet.zst | 2025-07-19 | 00 | 0 |  | 25000 | 342 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-19/18/BTCUSDT_orderbook.parquet.zst | 2025-07-19 | 18 | 0 |  | 25000 | 300 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-20/17/BTCUSDT_orderbook.parquet.zst | 2025-07-20 | 17 | 0 |  | 25000 | 171 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-21/15/BTCUSDT_orderbook.parquet.zst | 2025-07-21 | 15 | 0 |  | 25000 | 134 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-22/14/BTCUSDT_orderbook.parquet.zst | 2025-07-22 | 14 | 0 |  | 25000 | 102 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-23/12/BTCUSDT_orderbook.parquet.zst | 2025-07-23 | 12 | 0 |  | 25000 | 312 | 0 | 0 | 0 | 0 | 0 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-24/11/BTCUSDT_orderbook.parquet.zst | 2025-07-24 | 11 | 0 |  | 25000 | 593 | 0 | 0 | 0 | 0 | 0 | 0 |

## Snapshot/Reset Candidate Findings
| candidate_file_path | file_date | file_hour | candidate_score | candidate_reasons | snapshot_like_row_count | snapshot_like_packet_count |
| --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 6105100 | snapshot_reset_like, missing_first_update_id, missing_prev_final_update_id, repeated_final_update_id | 2000 | 1 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 6105150 | snapshot_reset_like, missing_first_update_id, missing_prev_final_update_id, event_time_non_monotonicity | 2000 | 1 |

## Transaction-Time Fallback Candidate Findings
No raw missing transaction_time fallback candidates were found in this bounded discovery window.

## Source-Gap Candidate Findings
| candidate_file_path | file_date | file_hour | candidate_score | candidate_reasons | estimated_source_gap_count | snapshot_like_packet_count |
| --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 | 810200 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 673 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 | 647000 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 458 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 | 278900 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 169 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 | 276300 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 165 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 | 839400 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 663 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2025-12-22 | 07 | 2000 | estimated_source_gap | 2 | 0 |

## Timestamp Ordering Candidate Findings
| candidate_file_path | file_date | file_hour | candidate_score | candidate_reasons | timestamp_non_monotonic_hint_count | event_time_non_monotonic_hint_count | transaction_time_non_monotonic_hint_count | received_time_non_monotonic_hint_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 | 810200 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 196 | 196 | 196 | 196 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 | 647000 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 270 | 270 | 270 | 270 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 | 278900 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 157 | 157 | 157 | 157 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 | 276300 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 159 | 159 | 159 | 159 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 | 839400 | estimated_source_gap, timestamp_non_monotonicity, event_time_non_monotonicity, transaction_time_non_monotonicity, received_time_non_monotonicity | 252 | 252 | 252 | 252 |

## Side Mapping Candidate Findings
No unknown side mappings were found in this bounded discovery window.

## Missing Column Findings
No missing required columns were found in this bounded discovery window.

## What Worked
- Discovery was bounded and read-only.
- Candidate selection was deterministic.
- Snapshot/reset-like, fallback, source-gap, timestamp, side-mapping, and missing-column hints were scored without writing derived artifacts.

## What Failed Or Remains Unknown
- This is a discovery pass only.
- A bounded preview can miss rare paths outside the sampled window.
- No OFI reconstruction or trading approval was attempted.

## What Is Safe
- Bounded read-only discovery of candidate raw L2 files.
- Using the previews to choose future bounded tests or diagnostics.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
bounded_read_only_discovery, candidate_selection_deterministic, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked, raw_snapshot_reset_candidates_found, raw_source_gap_candidates_found, timestamp_ordering_hints_found.

## Required Next Step
Use any discovered candidate files only for bounded read-only diagnostics or synthetic reproductions of the unexercised policy paths.

This discovery does not approve OFI for production, paper trading, live trading, or alpha use.