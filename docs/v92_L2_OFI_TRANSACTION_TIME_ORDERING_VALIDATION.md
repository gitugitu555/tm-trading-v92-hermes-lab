# V9.2 L2 OFI Transaction-Time Ordering Validation

## Purpose
Validate whether `transaction_time ASC, final_update_id ASC` is consistently safer than `event_time ASC, final_update_id ASC` for strict-sequence OFI reconstruction on the sampled Binance futures L2 corpus.

## Inputs
- L2 root: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- Max files: `12`
- Max events per file: `5000`
- Symbol filter: `BTCUSDT`

## Read-Only Guardrails
This validation only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.
This validation does not approve OFI for production, paper trading, live trading, or alpha use.

## Executive Finding
Transaction-time ordering was sample-validated across a bounded multi-file set. The known failing file was rechecked and transaction-time ordering again avoided the strict resync there. Across the sampled files, transaction-time ordering was not globally perfect, but it was cleaner than event-time ordering in the failing file and no sampled file required writing OFI output to disk.

## Explicit Answers
- Was the known failing file rechecked? Yes.
- Did transaction-time ordering avoid the known resync again? Yes.
- Across sampled files, was transaction-time ordering consistently cleaner than event-time ordering? Partially.
- Did any sampled file still hit resync under transaction-time ordering? Yes.
- Were snapshot/reset packets handled without being counted as source gaps? Yes.
- Were OFI values emitted in the transaction-time rehearsal? Yes.
- Was any OFI output written to disk? No.
- Is transaction-time ordering approved as the reconstruction ordering policy? Not globally approved yet; only validated for this bounded sample.
- Is OFI approved for alpha, paper, or live use? No.
- What is the next safe validation step? Validate the same ordering policy on a second bounded L2 sample before any reconstruction policy change.

## File Selection
| selected_index | file_path | priority_note | file_date |
| --- | --- | --- | --- |
| 1 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | known_failing_file | 2025-06-28 |
| 2 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-06-28 |
| 3 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-06-28 |
| 4 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2026-06-07 |
| 5 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-07-28 |
| 6 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-08-28 |
| 7 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-09-27 |
| 8 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-10-28 |
| 9 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-28/03/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-11-28 |
| 10 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-28/16/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2025-12-28 |
| 11 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-28/06/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2026-01-28 |
| 12 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-02-27/20/BTCUSDT_orderbook.parquet.zst | deterministic_sample | 2026-02-27 |

## Ordering Comparison Summary
| selected_file_count | files_with_transaction_time_better | files_with_event_time_better | files_with_both_clean | files_with_both_dirty | files_with_resync_stop | total_tx_processed_event_count | total_tx_ofi_emitted_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | 3 | 0 | 8 | 1 | 1 | 59293 | 59267 |

## Per-File Ordering Results
| file_path | ordering_classification | event_time_reset_aware_gaps | transaction_time_reset_aware_gaps | final_update_reset_aware_gaps | received_time_reset_aware_gaps | event_time_first_gap_index | transaction_time_first_gap_index | packet_count | snapshot_reset_count | matched_prev_chain_count | mismatched_prev_chain_count | gap_rate_tx | gap_rate_event |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | transaction_time_better | 2 | 0 | 2 | 2 | 1218 | null | 5000 | 2 | 4998 | 0 | 0.000000 | 0.000400 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | transaction_time_better | 2 | 0 | 2 | 2 | 1214 | null | 5000 | 2 | 4998 | 0 | 0.000000 | 0.000400 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | transaction_time_better | 2 | 0 | 2 | 2 | 1217 | null | 5000 | 2 | 4998 | 0 | 0.000000 | 0.000400 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | both_dirty | 1 | 1 | 1 | 1 | 4293 | 4293 | 5000 | 0 | 4999 | 1 | 0.000200 | 0.000200 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-28/03/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-28/16/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-28/06/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-02-27/20/BTCUSDT_orderbook.parquet.zst | both_clean | 0 | 0 | 0 | 0 | null | null | 5000 | 0 | 5000 | 0 | 0.000000 | 0.000000 |

## Snapshot / Reset Handling
Snapshot/reset packets were treated as chain reseeds, not source gaps. They were excluded from normal diff-gap counting and then processed through the transaction-time rehearsal with engine resets.

## OFIEngine Transaction-Time Rehearsal
| file_path | processed_event_count | ofi_emitted_count | warmup_none_count | snapshot_or_reset_event_count | sequence_gap_count | resync_stop_event_index | engine_completed_sample |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 5000 | 4997 | 3 | 2 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 5000 | 4997 | 3 | 2 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 5000 | 4997 | 3 | 2 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 5000 | 4996 | 4 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | 5000 | 4999 | 1 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 4293 | 4291 | 1 | 0 | 1 | 4293 | false |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | 5000 | 4999 | 1 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | 5000 | 4999 | 1 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-28/03/BTCUSDT_orderbook.parquet.zst | 5000 | 4999 | 1 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-28/16/BTCUSDT_orderbook.parquet.zst | 5000 | 4998 | 2 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-28/06/BTCUSDT_orderbook.parquet.zst | 5000 | 4998 | 2 | 0 | 0 | null | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-02-27/20/BTCUSDT_orderbook.parquet.zst | 5000 | 4997 | 3 | 0 | 0 | null | true |

## Known Failing File Recheck
The known failing file was rechecked. Event-time ordering still shows `2` reset-aware gap(s) at index `1218`. Transaction-time ordering shows `0` reset-aware gap(s) and the OFI rehearsal completed: `True`.

## What Worked
- The known failing file was included in the sample set: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst`.
- Transaction-time ordering avoided the known resync again on the failing file.
- Snapshot/reset packets were handled as reseeds rather than normal source gaps.
- OFI values were emitted in the transaction-time rehearsal across the sample: `59267` emitted values.
- `8` sampled file(s) were clean under both orderings.

## What Failed Or Remains Unknown
- Transaction-time ordering is not globally approved from this bounded sample alone.
- At least one sampled file still showed a transaction-time resync under the strict rehearsal.
- This validation does not establish OFI alpha or production readiness.
- `1` sampled file(s) still hit resync under transaction-time ordering.

## What Is Safe
- Bounded read-only ordering comparison on sampled raw L2 files.
- Strict transaction-time OFI rehearsal on sampled files only.
- In-memory comparison of event-time versus transaction-time sequence gaps.

## What Is Not Safe
- Treating transaction-time ordering as globally approved for the full raw corpus.
- Writing OFI outputs to disk in this validation.
- Using OFI for alpha, paper trading, or live trading.

## Decision
- Decision labels: `known_failing_file_rechecked, transaction_time_avoids_known_resync, transaction_time_ordering_better, snapshot_reset_handled, transaction_time_ordering_sample_validated, targeted_ordering_policy_candidate, broader_reconstruction_still_blocked, alpha_blocked, paper_live_blocked, transaction_time_resync_detected, ofi_values_emitted_transaction_time`
- Transaction-time ordering approved globally: `Not globally approved yet; only validated for this bounded sample.`
- OFI alpha approval: `No.`
- OFI paper/live approval: `No.`

## Required Next Step
Use this bounded sample result to decide whether a slightly larger read-only transaction-time check is warranted before any reconstruction policy change. Do not promote the ordering policy globally from this sample alone.
