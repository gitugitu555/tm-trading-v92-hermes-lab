# V9.2 L2 OFI Reconstruction Sample Validation

## Purpose
Validate that OFI reconstruction remains stable across a larger bounded sample of raw L2 files and that packet grouping is safe across row-order, packet-boundary, and cross-file concerns.

## Inputs
- L2 root: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- Bar dir: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Selected files: `6`
- Max events per file: `2000`

## Read-Only Guardrails
This validation only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any derived parquet/csv/json artifacts.
This validation does not approve OFI for production, paper trading, live trading, or alpha use.

## File Selection
Deterministic selection used the first chronological file, the last chronological file, and evenly spaced files in between. The sample is bounded and read-only; it is not a full-corpus pass.

| selected_file | file_date |
| --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | 2025-09-03 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | 2025-11-09 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | 2026-01-16 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | 2026-03-24 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 |

## Packet Grouping Validation
| file_path | row_order_packet_count | global_packet_count | packet_grouping_order_risk | row_order_duplicate_packet_key_count | global_duplicate_packet_key_count | first_packet_key | last_packet_key |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1751086799938, 7900531561583, 7900531558427, update) | (BTCUSDT, 1751087005583, 7900543632039, 7900543629265, update) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1756900799920, 8505809848913, 8505809847291, update) | (BTCUSDT, 1756900903570, 8505820387901, 8505820383682, update) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1762711199885, 9140668563487, 9140668558501, update) | (BTCUSDT, 1762711303554, 9140680290009, 9140680283118, update) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1768525199923, 9676583188167, 9676583185391, update) | (BTCUSDT, 1768525304892, 9676590705194, 9676590702204, update) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1774335599912, 10178103349321, 10178103346055, update) | (BTCUSDT, 1774335703860, 10178113822385, 10178113819525, update) |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2000 | 2000 | false | 0 | 0 | (BTCUSDT, 1780873199904, 10746772680607, 10746772678865, update) | (BTCUSDT, 1780873253076, 10746780802484, 10746780790994, update) |

## Packet Boundary Safety
| file_path | packet_boundary_unknown | dropped_last_packet_for_boundary_safety |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | false | 0 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | false | 0 |

## Per-File Reconstruction Results
| file_path | rows_scanned | processed_event_count | ofi_emitted_count | warmup_none_count | snapshot_or_reset_event_count | sequence_gap_count | resync_stop_event_index | bad_cast_row_count | unknown_side_row_count | ofi_positive_count | ofi_negative_count | ofi_zero_count | ofi_mean | ofi_min | ofi_max | ofi_abs_sum | event_time_min | event_time_max | final_update_id_min | final_update_id_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 391967 | 1218 | 1215 | 2 | 1 | 1 | 1218 | 0 | 0 | 504 | 455 | 256 | 0.075388 | -31.381000 | 22.179000 | 448.186000 | 1751086799938 | 1751087005583 | 7900531561583 | 7900543632039 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | 153643 | 2000 | 1999 | 1 | 0 | 0 | null | 0 | 0 | 840 | 792 | 367 | 0.021598 | -58.984000 | 45.914000 | 3532.630000 | 1756900799920 | 1756900903570 | 8505809848913 | 8505820387901 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | 91720 | 2000 | 1999 | 1 | 0 | 0 | null | 0 | 0 | 601 | 534 | 864 | 0.002906 | -15.394000 | 21.106000 | 734.957000 | 1762711199885 | 1762711303554 | 9140668563487 | 9140680290009 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | 79400 | 2000 | 1999 | 1 | 0 | 0 | null | 0 | 0 | 485 | 671 | 843 | -0.073771 | -31.896000 | 25.521000 | 717.104000 | 1768525199923 | 1768525304892 | 9676583188167 | 9676590705194 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | 165486 | 2000 | 1998 | 2 | 0 | 0 | null | 0 | 0 | 753 | 653 | 592 | -0.052521 | -24.333000 | 19.053000 | 1883.209000 | 1774335599912 | 1774335703860 | 10178103349321 | 10178113822385 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 195682 | 2000 | 1998 | 2 | 0 | 0 | null | 0 | 0 | 914 | 806 | 278 | 0.075312 | -16.916000 | 16.500000 | 1547.031000 | 1780873199904 | 1780873253076 | 10746772680607 | 10746780802484 |

## Aggregate OFI Summary
| selected_file_count | total_rows_scanned | total_processed_event_count | total_ofi_emitted_count | files_with_packet_grouping_order_risk | files_with_resync_stop | files_with_snapshot_reset | files_with_bad_casts | files_with_unknown_sides |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 1077898 | 11218 | 11208 | 0 | 1 | 1 | 0 | 0 |

## Cross-File Continuity
| left_file | right_file | continuity_status |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | cross_file_unknown |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-09-03/12/BTCUSDT_orderbook.parquet.zst | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | cross_file_unknown |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-11-09/18/BTCUSDT_orderbook.parquet.zst | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | cross_file_unknown |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-16/01/BTCUSDT_orderbook.parquet.zst | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | cross_file_unknown |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-24/07/BTCUSDT_orderbook.parquet.zst | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | cross_file_unknown |

## Join Readiness Sample
| file_date | bar_file_found | bar_row_count | join_attempted | joined_row_count | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-06-28 | true | 571 | true | 571 | true | null |
| 2025-09-03 | true | 500 | true | 500 | true | null |
| 2025-11-09 | true | 1047 | true | 1047 | true | null |
| 2026-01-16 | true | 656 | true | 656 | true | null |
| 2026-03-24 | true | 941 | true | 941 | true | null |
| 2026-06-07 | true | 79 | true | 79 | true | null |

## What Worked
- Multiple raw L2 files were readable.
- Global packet grouping on bounded samples completed.
- OFI values were emitted in-memory for the bounded sample set.
- The join helper was importable and callable.

## What Failed Or Remains Unknown
- Cross-file continuity is only sample-evidenced and may be unknown across distant dates.
- At least one selected file hit a strict-sequence resync stop during sample processing.
- Packet boundary safety is conservative; incomplete trailing packets are not promoted into the reconstruction.
- This validation does not prove the full corpus gap-free or production-ready.

## What Is Safe
- Read-only reconstruction on a bounded multi-file sample.
- In-memory OFI processing and summary statistics only.
- Coverage-preserving join checks without writing output.

## What Is Not Safe
- Using this sample as OFI alpha evidence.
- Writing reconstructed OFI artifacts to disk in this task.
- Claiming the full raw L2 corpus is gap-free from a bounded sample.

## Decision
Decision labels: alpha_blocked, paper_live_blocked, multi_file_l2_sample_readable, global_packet_grouping_successful, ofi_values_emitted_multi_file, strict_sequence_resync_detected, join_readiness_sample_passed, larger_sample_validation_blocked

## Required Next Step
If this bounded sample remains stable, extend to a slightly larger read-only sample before any broader reconstruction work; do not treat this sample as OFI approval.

## Explicit Answers
- Were multiple raw L2 files readable? Yes.
- Did global packet grouping work? Yes.
- Did row-order packet grouping differ from global grouping? No.
- Were packet-boundary risks detected or mitigated? No.
- Were OFI values emitted across multiple files? Yes.
- Did strict sequence mode hit resync in any file? Yes.
- Were join checks coverage-preserving where attempted? Yes.
- Was any OFI output written to disk? No.
- Is OFI approved for alpha, paper, or live use? No.
- What is the next safe validation step? Use this bounded sample as proof-of-life, then extend to a slightly larger read-only sample only if the packet-grouping and join-readiness signals remain stable.
