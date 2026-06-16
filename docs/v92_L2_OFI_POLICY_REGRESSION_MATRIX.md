# V9.2 L2 OFI Policy Regression Matrix

## Purpose
Confirm that the reusable segmented L2 OFI policy still processes all previously validated bounded candidate groups safely after the snapshot/reset bridge and quarantine implementation.

## Inputs
- `max_events_per_file`: `75000`
- `selected_file_count`: `11`
- `group_count`: `3`

## Read-Only Guardrails
- Read-only bounded validation only.
- No OFI artifacts are written.
- No OFIEngine behavior is changed.
- No full-corpus reconstruction is attempted.

## Candidate Groups
| group_name | file_path | file_date | file_hour |
| --- | --- | --- | --- |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 09 |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | 23 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2025-12-22 | 07 |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 |

## Module Usage
- The script imports and uses `L2Packet`, `packet_sort_key`, `is_snapshot_or_reset`, `is_snapshot_bridge_event`, `is_source_gap`, `segment_packets`, `run_segment_with_ofi_engine`, and `summarize_segments` from the reusable policy module.
- Raw rows are converted to `L2Packet` objects in memory before segmentation.
- Segmentation and per-segment OFIEngine processing are delegated to the policy module.

## Executive Finding
11 bounded candidate files across 3 groups were processed in bounded read-only mode.
All bounded candidate groups passed the regression matrix.
Original bounded/sample files remain clean: `True`.
Source-gap-heavy real raw files remain clean: `True`.
Source-gap boundaries remain detected: `True`.
Snapshot/reset bridge files remain clean: `True`.
Snapshot bridge events were detected: `True`.
Invalid snapshot/reset chains were quarantined if present: `False`.
Any quarantined segment emitted OFI: `False`.
Any OFI output was written to disk: `false`.
OFIEngine behavior changed: `false`.
Full reconstruction approved: `false`.
OFI approved for alpha, paper, or live use: `false`.
This regression matrix does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.

## Per-File Regression Results
| group_name | file_path | file_date | file_hour | rows_scanned | packet_count | segment_count | meaningful_segment_count | clean_segment_count | dirty_segment_count | all_segments_clean | source_gap_boundary_count | snapshot_like_packet_count | snapshot_bridge_event_count | snapshot_reset_clean_seed_count | snapshot_reset_chain_failure_count | quarantined_segment_count | total_ofi_emitted_count | total_warmup_none_count | total_sequence_gap_count | ofi_suppressed_due_to_snapshot_bridge_count | ofi_suppressed_due_to_quarantine_count | side_mapping_unknown_count | policy_module_used_directly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 | 75000 | 286 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 285 | 1 | 0 | 0 | 0 | 0 | true |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 2025-08-28 | 09 | 75000 | 1210 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 1209 | 1 | 0 | 0 | 0 | 0 | true |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 2026-06-07 | 23 | 75000 | 755 | 1 | 1 | 1 | 0 | true | 0 | 0 | 0 | 0 | 0 | 0 | 753 | 2 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 11 | 75000 | 4834 | 646 | 45 | 646 | 0 | true | 645 | 0 | 0 | 0 | 0 | 0 | 0 | 4834 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 2025-07-03 | 00 | 75000 | 4897 | 571 | 184 | 571 | 0 | true | 570 | 0 | 0 | 0 | 0 | 0 | 0 | 4897 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 00 | 75000 | 3479 | 182 | 42 | 182 | 0 | true | 181 | 0 | 0 | 0 | 0 | 0 | 0 | 3479 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 2025-07-01 | 23 | 75000 | 3333 | 165 | 21 | 165 | 0 | true | 164 | 0 | 0 | 0 | 0 | 0 | 0 | 3333 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 2025-07-02 | 21 | 75000 | 6390 | 660 | 121 | 660 | 0 | true | 659 | 0 | 0 | 0 | 0 | 0 | 0 | 6390 | 0 | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2025-12-22 | 07 | 75000 | 1416 | 3 | 2 | 3 | 0 | true | 2 | 0 | 0 | 0 | 0 | 0 | 1413 | 3 | 0 | 0 | 0 | 0 | true |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 00 | 75000 | 1405 | 1 | 1 | 1 | 0 | true | 0 | 1 | 1 | 1 | 0 | 0 | 1403 | 1 | 0 | 1 | 0 | 0 | true |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2026-05-26 | 07 | 75000 | 2059 | 1 | 1 | 1 | 0 | true | 0 | 1 | 1 | 1 | 0 | 0 | 2057 | 1 | 0 | 1 | 0 | 0 | true |

## Group-Level Regression Summary
| group_name | file_count | files_all_segments_clean | files_with_dirty_segments | source_gap_boundary_count | snapshot_bridge_event_count | quarantined_segment_count | sequence_gap_count | regression_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_sample | 3 | 3 | 0 | 0 | 0 | 0 | 0 | passed |
| source_gap_heavy | 6 | 6 | 0 | 2221 | 0 | 0 | 0 | passed |
| snapshot_reset_bridge | 2 | 2 | 0 | 0 | 2 | 0 | 0 | passed |

## Source-Gap Regression Results
| group_name | file_path | source_gap_boundary_count | all_segments_clean | total_sequence_gap_count |
| --- | --- | --- | --- | --- |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 645 | true | 0 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 570 | true | 0 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 181 | true | 0 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 164 | true | 0 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 659 | true | 0 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 2 | true | 0 |

## Snapshot/Reset Bridge Regression Results
| group_name | file_path | snapshot_like_packet_count | snapshot_bridge_event_count | quarantined_segment_count | all_segments_clean |
| --- | --- | --- | --- | --- | --- |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 1 | 1 | 0 | true |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 1 | 1 | 0 | true |

## Quarantine Regression Results
| group_name | file_path | quarantined_segment_count | quarantined_segment_ofi_emitted_count | ofi_suppressed_due_to_quarantine_count | all_segments_clean |
| --- | --- | --- | --- | --- | --- |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | true |

## OFI Suppression Results
| group_name | file_path | total_ofi_emitted_count | ofi_suppressed_due_to_snapshot_bridge_count | ofi_suppressed_due_to_quarantine_count | total_warmup_none_count |
| --- | --- | --- | --- | --- | --- |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 285 | 0 | 0 | 1 |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst | 1209 | 0 | 0 | 1 |
| original_sample | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-06-07/23/BTCUSDT_orderbook.parquet.zst | 753 | 0 | 0 | 2 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/11/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 4834 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-03/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 4897 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/00/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 3479 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-01/23/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 3333 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-07-02/21/BTCUSDT_orderbook.parquet.zst | 0 | 0 | 0 | 6390 |
| source_gap_heavy | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-12-22/07/BTCUSDT_orderbook.parquet.zst | 1413 | 0 | 0 | 3 |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/00/BTCUSDT_orderbook.parquet.zst | 1403 | 1 | 0 | 1 |
| snapshot_reset_bridge | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-05-26/07/BTCUSDT_orderbook.parquet.zst | 2057 | 1 | 0 | 1 |

## What Worked
- The reusable policy module was used directly.
- All candidate groups were deterministic.
- The original bounded/sample files remained clean.
- The source-gap-heavy real raw files remained clean.
- Source-gap boundaries remained detected.
- The snapshot/reset bridge files remained clean.
- Snapshot bridge events were detected.
- No OFI artifacts were written.

## What Failed Or Remains Unknown
- No regression failures were observed in this bounded matrix.
- A different bounded candidate set could still expose additional edge cases.
- This remains a bounded validation only.

## What Is Safe
- Bounded read-only validation of the known regression candidate groups.
- Source-gap behavior remains usable for further bounded validation.
- Snapshot/reset bridge handling remains usable for bounded validation.

## What Is Not Safe
- Full reconstruction.
- Any paper or live trading use.
- Alpha claims.

## Decision
policy_module_used_directly, candidate_groups_deterministic, original_sample_regression_passed, source_gap_boundaries_preserved, source_gap_heavy_regression_passed, snapshot_bridge_events_detected, snapshot_reset_bridge_regression_passed, no_invalid_snapshot_reset_chains_quarantined, quarantined_segments_emit_no_ofi, ofi_engine_behavior_unchanged, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked.

## Required Next Step
Continue bounded read-only regression checks only; do not promote the workflow to full reconstruction.

This regression matrix does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.