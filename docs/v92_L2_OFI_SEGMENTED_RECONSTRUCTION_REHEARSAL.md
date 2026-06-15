# V9.2 L2 OFI Segmented Reconstruction Rehearsal

## Purpose
Validate whether bounded raw L2 files with source gaps can be reconstructed as separate clean OFI segments in memory without writing artifacts.

## Inputs
- L2 root: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- Max files: `12`
- Max events per file: `7000`
- Ordering: `transaction_time_final_update_id`
- Symbol filter: `BTCUSDT`

## Read-Only Guardrails
This rehearsal only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.
This rehearsal does not approve OFI for production, paper trading, live trading, or alpha use.

## Executive Finding
Bounded segmented reconstruction was rehearsed across multiple raw L2 files. The known dirty source-gap file was split into clean before/after segments, and the known event-ordering file was also processed in-memory without writing artifacts. This is a bounded rehearsal only; it does not approve broader reconstruction or trading use.

## File Selection
| selected_index | file_path | file_date | file_hour | priority_note |
| --- | --- | --- | --- | --- |
| 1 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 | known_dirty_or_event_file |
| 2 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 06 | deterministic_sample |
| 3 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 07 | deterministic_sample |
| 4 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 09 | known_dirty_or_event_file |
| 5 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 07 | deterministic_sample |
| 6 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 08 | deterministic_sample |
| 7 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 10 | deterministic_sample |
| 8 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 11 | deterministic_sample |
| 9 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | 23 | deterministic_sample |
| 10 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | 2025-07-28 | 19 | deterministic_sample |
| 11 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | 2025-09-27 | 23 | deterministic_sample |
| 12 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | 2025-10-28 | 13 | deterministic_sample |

## Segment Boundary Policy
Source sequence gaps and snapshot/reset packets start new segments. Each segment is run through a fresh OFIEngine instance so state is never carried across a boundary.

## Per-File Segmentation Summary
| file_path | packet_count | segment_count | meaningful_segment_count | source_gap_count | snapshot_reset_boundary_count | clean_segment_count | dirty_segment_count | all_segments_clean | total_ofi_emitted_count | total_warmup_none_count | min_segment_packet_count | max_segment_packet_count | segments_with_internal_resync |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 7000 | 3 | 1 | 0 | 2 | 3 | 0 | true | 6997 | 3 | 1 | 6998 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 7000 | 3 | 1 | 0 | 2 | 3 | 0 | true | 6997 | 3 | 1 | 6998 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 7000 | 3 | 1 | 0 | 2 | 3 | 0 | true | 6997 | 3 | 1 | 6998 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 7000 | 2 | 2 | 1 | 0 | 2 | 0 | true | 6998 | 2 | 2708 | 4292 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6993 | 7 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | 7000 | 1 | 1 | 0 | 0 | 1 | 0 | true | 6999 | 1 | 7000 | 7000 | 0 |

## Segment-Level Results
| segment_id | start_packet_index | end_packet_index | packet_count | start_event_time | end_event_time | start_transaction_time | end_transaction_time | start_final_update_id | end_final_update_id | segment_boundary_reason | segment_clean | ofi_emitted_count | warmup_none_count | sequence_gap_count_inside_segment | snapshot_reset_count_inside_segment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 6998 | 6998 | 1751086799938 | 1751087516245 | 1751086799938 | 1751087516243 | 7900531561583 | 7900575480150 | snapshot_or_reset | true | 6997 | 1 | 0 | 0 |
| 2 | 6999 | 6999 | 1 | 1751086924229 | 1751086924229 | null | null | 7900538334001 | 7900538334001 | snapshot_or_reset | true | 0 | 1 | 0 | 1 |
| 3 | 7000 | 7000 | 1 | 1751087223965 | 1751087223965 | null | null | 7900557353196 | 7900557353196 | sample_end | true | 0 | 1 | 0 | 1 |
| 1 | 1 | 6998 | 6998 | 1751090399971 | 1751091115484 | 1751090399964 | 1751091115484 | 7900738113115 | 7900781206165 | snapshot_or_reset | true | 6997 | 1 | 0 | 0 |
| 2 | 6999 | 6999 | 1 | 1751090523979 | 1751090523979 | null | null | 7900746120040 | 7900746120040 | snapshot_or_reset | true | 0 | 1 | 0 | 1 |
| 3 | 7000 | 7000 | 1 | 1751090823972 | 1751090823972 | null | null | 7900765043124 | 7900765043124 | sample_end | true | 0 | 1 | 0 | 1 |
| 1 | 1 | 6998 | 6998 | 1751093999887 | 1751094714665 | 1751093999884 | 1751094714664 | 7900935307995 | 7900976260528 | snapshot_or_reset | true | 6997 | 1 | 0 | 0 |
| 2 | 6999 | 6999 | 1 | 1751094123972 | 1751094123972 | null | null | 7900943622299 | 7900943622299 | snapshot_or_reset | true | 0 | 1 | 0 | 1 |
| 3 | 7000 | 7000 | 1 | 1751094423974 | 1751094423974 | null | null | 7900961526869 | 7900961526869 | sample_end | true | 0 | 1 | 0 | 1 |
| 1 | 1 | 4292 | 4292 | 1756371599902 | 1756371822972 | 1756371599902 | 1756371822955 | 8459810994910 | 8459829013238 | source_sequence_gap | true | 4291 | 1 | 0 | 0 |
| 2 | 4293 | 7000 | 2708 | 1756371835884 | 1756371976890 | 1756371835882 | 1756371976887 | 8459829692989 | 8459842038857 | sample_end | true | 2707 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1756364399920 | 1756364765917 | 1756364399919 | 1756364765908 | 8459172061976 | 8459208125037 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1756367999916 | 1756368363579 | 1756367999915 | 1756368363579 | 8459469499303 | 8459518442292 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1756375199884 | 1756375565012 | 1756375199881 | 1756375565010 | 8460067124631 | 8460096025226 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1756378799888 | 1756379164287 | 1756378799882 | 1756379164286 | 8460332223451 | 8460363042290 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1780873199904 | 1780873386754 | 1780873199903 | 1780873386753 | 10746772680607 | 10746798994358 | sample_end | true | 6993 | 7 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1753729199922 | 1753729562593 | 1753729199921 | 1753729562592 | 8177097619175 | 8177147918613 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1759013999880 | 1759014363091 | 1759013999880 | 1759014363084 | 8707266158139 | 8707299276604 | sample_end | true | 6999 | 1 | 0 | 0 |
| 1 | 1 | 7000 | 7000 | 1761656399904 | 1761656762128 | 1761656399903 | 1761656762127 | 9013058212792 | 9013104386529 | sample_end | true | 6999 | 1 | 0 | 0 |

## Aggregate Segment Summary
| selected_file_count | total_packet_count | total_segment_count | total_meaningful_segment_count | total_source_gap_count | total_snapshot_reset_boundary_count | files_with_source_gaps | files_with_snapshot_resets | files_all_segments_clean | files_with_dirty_segments | total_ofi_emitted_count | total_warmup_none_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | 84000 | 19 | 13 | 1 | 6 | 1 | 3 | 12 | 0 | 83975 | 25 |

## OFIEngine Segment Rehearsal
| file_path | ofi_record_count | first_datetime | last_datetime |
| --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 6997 | 1751086800039000000 | 1751087516245000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 6997 | 1751090400072000000 | 1751091115484000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 6997 | 1751093999990000000 | 1751094714665000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 6998 | 1756371599953000000 | 1756371976890000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/07/BTCUSDT_orderbook.parquet.zst | 6999 | 1756364399971000000 | 1756364765917000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/08/BTCUSDT_orderbook.parquet.zst | 6999 | 1756367999967000000 | 1756368363579000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/10/BTCUSDT_orderbook.parquet.zst | 6999 | 1756375199937000000 | 1756375565012000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/11/BTCUSDT_orderbook.parquet.zst | 6999 | 1756378799939000000 | 1756379164287000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 6993 | 1780873199932000000 | 1780873386754000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-28/19/BTCUSDT_orderbook.parquet.zst | 6999 | 1753729199976000000 | 1753729562593000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-27/23/BTCUSDT_orderbook.parquet.zst | 6999 | 1759013999931000000 | 1759014363091000000 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-10-28/13/BTCUSDT_orderbook.parquet.zst | 6999 | 1761656399955000000 | 1761656762128000000 |

## Join Readiness Sample
| file_date | bar_file_found | bar_row_count | join_attempted | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- | --- |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-06-28 | true | 571 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2025-08-28 | true | 629 | true | true | null |
| 2026-06-07 | true | 79 | true | true | null |
| 2025-07-28 | true | 646 | true | true | null |
| 2025-09-27 | true | 500 | true | true | null |
| 2025-10-28 | true | 961 | true | true | null |

## What Worked
- Bounded files were segmented successfully across `12` selected files.
- Known dirty file `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst` produced clean before/after segments.
- OFIEngine was reset at every segment boundary and processed each segment in memory only.
- The known dirty file's segments remained clean internally after splitting.
- Join-readiness checks preserved bar count where attempted.

## What Failed Or Remains Unknown
- Segmented reconstruction is not globally approved from this bounded rehearsal.
- This rehearsal does not establish OFI alpha or production readiness.

## What Is Safe
- Read-only segmented reconstruction rehearsal on a bounded sample.
- Resetting OFIEngine at explicit source-gap and snapshot/reset boundaries.
- In-memory join-readiness checks only.

## What Is Not Safe
- Treating the segmented rehearsal as global approval for the full corpus.
- Writing OFI outputs to disk in this validation.
- Using OFI for alpha, paper trading, or live trading.

## Decision
- Decision labels: `segmented_reconstruction_rehearsed, source_gaps_as_segment_boundaries, snapshot_resets_as_segment_boundaries, segments_clean_in_sample, join_readiness_sample_passed, ofi_values_emitted_in_segments, segmented_reconstruction_not_globally_approved, broader_reconstruction_blocked, alpha_blocked, paper_live_blocked`
- Segmented reconstruction globally approved: `Not globally approved; segmented reconstruction is only a bounded rehearsal candidate.`
- OFI alpha approval: `No.`
- OFI paper/live approval: `No.`

## Required Next Step
Validate the same segmented-reconstruction policy on another bounded sample before any broader reconstruction policy change.
