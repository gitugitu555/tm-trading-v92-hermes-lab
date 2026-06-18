# V9.2 L2 OFI Reconstruction Dry-Run Manifest

## Purpose
Estimate which raw L2 files would be selected, skipped, rejected, quarantined, or deferred under the current segmented OFI policy without writing any OFI artifacts.

## Inputs
- `symbol`: `BTCUSDT`
- `max_candidate_files`: `120`
- `preview_rows_per_file`: `5000`
- `max_policy_check_files`: `20`
- `bar_size`: `750btc`
- `candidate_batch_index`: `0`
- `candidate_batch_count`: `4`
- `selected_file_count`: `30`
- `selected_file_count_for_batch`: `30`
- `files_previewed`: `30`
- `files_previewed_for_batch`: `30`
- `files_policy_checked`: `20`
- `files_policy_checked_for_batch`: `20`
- `discovered_file_count`: `8074`
- `discovered_bar_count`: `102`
- `bar_month_shard_count`: `71`
- `bar_day_shard_count`: `31`
- `previewed_file_count`: `30`
- `policy_checked_file_count`: `20`
- `join_attempted_count`: `17`
- `join_deferred_count`: `3`
- `join_preserved_count`: `17`
- `join_not_preserved_count`: `0`

## Read-Only Guardrails
- Read-only bounded dry-run only.
- No OFI artifacts are written.
- No packet tables are written.
- No derived OFI data are written.
- No full-corpus reconstruction is attempted.

## Current Policy Status
- Reusable segmented L2 OFI policy module is present and reused directly.
- Source-gap behavior remains validated in bounded regression.
- Snapshot/reset bridge behavior remains validated in bounded regression.
- Quarantine behavior remains bounded and read-only.

## Dry-Run Scope
- `full_bounded_manifest_batch`
- `candidate_batch_index`: `0`
- `candidate_batch_count`: `4`

## Candidate Selection Method
Deterministic bounded selection anchored on known sample files, source-gap-heavy files, snapshot/reset bridge files, first/last chronological files, month-open files, day-boundary/hour-boundary files, 2026 files, and evenly spaced corpus files, capped to the configured preview budget.

## Candidate Preview Summary
| dry_run_policy_class | count |
| --- | --- |
| likely_clean_preview | 10 |
| policy_check_selected | 20 |

## Policy-Check Selection
| file_path | candidate_reason | candidate_score | dry_run_policy_class |
| --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 104050 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 100450 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 61450 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 27700 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 19600 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | known_snapshot_reset_bridge | 1388 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | known_snapshot_reset_bridge | 1345 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | known_source_gap_heavy | 1279 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | known_original_sample | 1040 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | known_original_sample | 1026 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | known_original_sample | 1018 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | first_chronological | 57 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/19/BTCUSDT_orderbook.parquet.zst | first_chronological | 54 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | first_chronological | 53 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/23/BTCUSDT_orderbook.parquet.zst | first_chronological | 52 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/14/BTCUSDT_orderbook.parquet.zst | first_chronological | 51 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | first_chronological | 49 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | first_chronological | 48 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | first_chronological | 48 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/15/BTCUSDT_orderbook.parquet.zst | first_chronological | 48 | policy_check_selected |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/20/BTCUSDT_orderbook.parquet.zst | first_chronological | 48 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/21/BTCUSDT_orderbook.parquet.zst | first_chronological | 48 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/16/BTCUSDT_orderbook.parquet.zst | first_chronological | 46 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/22/BTCUSDT_orderbook.parquet.zst | first_chronological | 46 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | first_chronological | 45 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | first_chronological | 45 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/18/BTCUSDT_orderbook.parquet.zst | first_chronological | 45 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/12/BTCUSDT_orderbook.parquet.zst | first_chronological | 44 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/17/BTCUSDT_orderbook.parquet.zst | first_chronological | 42 | likely_clean_preview |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-29/00/BTCUSDT_orderbook.parquet.zst | first_chronological | 41 | likely_clean_preview |

## Executive Finding
Discovered files under `l2_root`: `8074`.
Discovered bar files under `bar_dir`: `102`.
Files previewed: `30`.
Files policy-checked: `20`.
Join-readiness attempted: `17`.
Join-readiness deferred: `3`.
Join-readiness preserved where attempted: `17`.
Join-readiness not preserved where attempted: `0`.
Accepted bounded-clean candidates: `20`.
Source-gap-clean candidates: `6`.
Snapshot-bridge-clean candidates: `2`.
Quarantined candidates: `0`.
Rejected/dirty candidates: `0`.
Deferred candidates: `0`.
Selected files for batch: `30`.
Join-readiness checks attempted: `True`.
Join-readiness checks deferred: `True`.
Bar-count preservation maintained where attempted: `True`.
This dry-run manifest does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.

## Policy-Check Results
| file_path | file_date | file_hour | rows_scanned | packet_count | segment_count | meaningful_segment_count | clean_segment_count | dirty_segment_count | all_segments_clean | source_gap_boundary_count | snapshot_like_packet_count | snapshot_bridge_event_count | snapshot_reset_clean_seed_count | snapshot_reset_chain_failure_count | quarantined_segment_count | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | ofi_suppressed_due_to_snapshot_bridge_count | ofi_suppressed_due_to_quarantine_count | policy_check_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 | 5000 | 18 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 | 5000 | 422 | 125 | 8 | 125 | 0 | true | 124 | 0 | 0 | 0 | 0 | 0 | 0 | 422 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 | 5000 | 1409 | 664 | 34 | 664 | 0 | true | 663 | 0 | 0 | 0 | 0 | 0 | 0 | 1409 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 | 5000 | 751 | 179 | 20 | 179 | 0 | true | 178 | 0 | 0 | 0 | 0 | 0 | 0 | 751 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 | 5000 | 1067 | 688 | 60 | 688 | 0 | true | 687 | 0 | 0 | 0 | 0 | 0 | 0 | 1067 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 | 5000 | 717 | 404 | 48 | 404 | 0 | true | 403 | 0 | 0 | 0 | 0 | 0 | 0 | 717 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 09 | 5000 | 26 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2025-12-22 | 07 | 5000 | 79 | 3 | 2 | 3 | 0 | true | 2 | 0 | 0 | 0 | 0 | 0 | 76 | 3 | 0 | 0 | 0 | accepted_bounded_source_gap_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 5000 | 88 | 1 | 1 | 1 | 0 | true | 0 | 1 | 1 | 1 | 0 | 0 | 86 | 1 | 0 | 1 | 0 | accepted_bounded_snapshot_bridge_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 5000 | 45 | 1 | 1 | 1 | 0 | true | 0 | 1 | 1 | 1 | 0 | 0 | 43 | 1 | 0 | 1 | 0 | accepted_bounded_snapshot_bridge_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | 23 | 5000 | 40 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 38 | 2 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 07 | 5000 | 19 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 09 | 5000 | 27 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 10 | 5000 | 18 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 11 | 5000 | 18 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 13 | 5000 | 23 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 22 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/14/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 14 | 5000 | 21 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/15/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 15 | 5000 | 18 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/19/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 19 | 5000 | 24 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 1 | 0 | 0 | 0 | accepted_bounded_clean |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/23/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 23 | 5000 | 22 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 1 | 0 | 0 | 0 | accepted_bounded_clean |

## Join-Readiness Results
| file_date | bar_file_found | bar_file_path | bar_shard_resolution_strategy | bar_row_count | join_attempted | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-07-01 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | month | 646 | true | true | null |
| 2025-07-01 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | month | 646 | true | true | null |
| 2025-07-01 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | month | 646 | true | true | null |
| 2025-07-02 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | month | 646 | true | true | null |
| 2025-07-03 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | month | 646 | true | true | null |
| 2025-08-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-08.parquet | month | 629 | true | true | null |
| 2025-12-22 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-12.parquet | month | 655 | true | true | null |
| 2026-05-26 | false | null | null | null | false | null | bar_file_missing |
| 2026-05-26 | false | null | null | null | false | null | bar_file_missing |
| 2026-06-07 | false | null | null | null | false | null | bar_file_missing |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |
| 2025-06-28 | true | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | month | 571 | true | true | null |

## Bar Shard Results
- `bar_size`: `750btc`
- `bar_shard_resolution_strategy`: `day -> month -> bar-size-filtered fallback`
- `bar_month_shard_count`: `71`
- `bar_day_shard_count`: `31`

## Dry-Run Classification Summary
| policy_check_status | count |
| --- | --- |
| accepted_bounded_clean | 12 |
| accepted_bounded_snapshot_bridge_clean | 2 |
| accepted_bounded_source_gap_clean | 6 |

## Accepted Bounded Clean Candidates
| file_path | policy_check_status | all_segments_clean |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/14/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/15/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/19/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/23/BTCUSDT_orderbook.parquet.zst | accepted_bounded_clean | true |

## Quarantined Candidates


## Rejected Or Deferred Candidates


## Estimated Output Plan
- Metadata-only projection: `symbol=BTCUSDT/date=YYYY-MM-DD/hour=HH`.
- The plan is estimated from bounded dry-run classification only.
- No OFI output partitions were written.
- Bar shard resolution strategy: `day` first, then `month`, then a bar-size-filtered fallback scan.

## What Worked
- The reusable policy module was used directly.
- Candidate files were selected deterministically.
- Source-gap and snapshot/reset bridge validation paths were exercised without writing OFI artifacts.
- Join-readiness was evaluated as metadata, and the manifest now resolves 750 BTC day/month bar shards before deferring any unresolved dates.
- The report distinguishes join attempts, deferrals, and bar-count preservation outcomes.

## What Failed Or Remains Unknown
- The manifest is bounded; it does not guarantee full-corpus cleanliness.
- Some candidates may still be deferred or rejected in a future broader pass.
- This remains a bounded validation only.

## What Is Safe
- Use this manifest as a read-only estimate of broader reconstruction behavior.
- Use accepted bounded-clean candidates only for further bounded validation work.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
bounded_read_only_dry_run, candidate_selection_deterministic, policy_module_used_directly, policy_check_bounded_only, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked, join_readiness_checked_where_possible, full_bounded_manifest_batch_completed, accepted_bounded_clean_candidates_found, source_gap_clean_candidates_found, snapshot_bridge_clean_candidates_found, bar_count_preserved_where_attempted, join_readiness_deferred_bar_files_missing, bar_month_shards_resolved.

## Required Next Step
Continue bounded read-only regression checks only; do not promote the workflow to full reconstruction or artifact generation.

This dry-run manifest does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.