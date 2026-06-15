# V9.2 L2 OFI Reconstruction Dry Run

## Purpose
Prove that a tiny raw Binance futures L2 sample can be grouped into event-level packets, fed into the repaired OFI engine, and produce a bounded OFI sample without dropping coverage or pretending it is production-ready.

## Inputs
- Input file: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst`
- Max events: `500`
- Strict sequence: `True`
- Symbol filter: `BTCUSDT`

## Read-Only Guardrails
This dry run only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any derived parquet/csv/json artifacts.
This dry run does not approve OFI for production, paper trading, live trading, or alpha use.

## Known Schema Quirks
- price and quantity are strings, so they must be cast to float before OFI processing.
- event_time is microseconds in the inspected sample and must be treated as a Binance-era us epoch value.
- Rows are not pre-sorted by event_time, so packet grouping must use packet metadata rather than source order alone.
- received_time is file-arrival time and is not a packet grouping key.
- first_update_id and prev_final_update_id can be null on snapshot/reset-style packets.

## Event Grouping Method
Rows are grouped sequentially by the packet key `symbol, event_time, final_update_id, prev_final_update_id, event_type`. The grouping is read-only and uses row-order packets from the bounded scan; received_time is ignored.

## Snapshot / Reset Handling
Rows whose packet metadata has null `first_update_id` or null `prev_final_update_id` are treated as snapshot/reset packets. The OFI engine is reset before processing them so they reseed state without emitting a synthetic first-tick OFI.

## Sequence / Resync Handling
Normal diff packets pass `previous_update_id=prev_final_update_id` into `OFIEngine.process_event`. If the engine raises `requires_resync`, strict mode stops immediately; non-strict mode resets and continues only because the run explicitly opted out of strict sequence enforcement.

## Dry Run Results
| read_mode | source_file_read_complete | rows_scanned | packets_built | bad_key_row_count | bad_cast_row_count | unknown_side_row_count | processed_event_count | ofi_emitted_count | warmup_none_count | sequence_gap_count | duplicate_final_update_id_count | snapshot_or_reset_event_count | resync_stop_event_index |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bounded_batch_scan_in_memory | false | 115651 | 500 | 0 | 0 | 0 | 500 | 499 | 1 | 0 | 0 | 0 | null |

## Explicit Answers
- Was the raw L2 sample readable? Yes.
- Were rows successfully grouped into event packets? Yes.
- Were price and quantity casts successful? Yes.
- Were snapshot/reset packets present? No.
- Were normal diff packets processed by OFIEngine? Yes.
- Did strict sequence handling stop on resync? No.
- Were OFI values emitted? Yes.
- Was any OFI output written to disk? No.
- Was a coverage-preserving join proven? Yes.
- Is OFI approved for alpha, paper, or live use? No.
- What is the next safe validation step? Use this sample only as a bounded rehearsal and, if needed, extend to a slightly larger read-only sample before any broader reconstruction work.

## OFI Summary Statistics
| ofi_count | ofi_null_count | ofi_positive_count | ofi_negative_count | ofi_zero_count | ofi_mean | ofi_median | ofi_min | ofi_max | ofi_abs_sum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 499 | 1 | 210 | 224 | 65 | 0.153519 | 0.000000 | -9.607000 | 22.179000 | 259.022000 |

## Join Readiness Check
| bar_file_found | bar_row_count | join_helper_importable | join_helper_callable | coverage_preserving_join_attempted | joined_row_count_if_attempted | bar_count_preserved_if_attempted | join_check_deferred |
| --- | --- | --- | --- | --- | --- | --- | --- |
| true | 571 | true | true | true | 100 | true | false |

## What Worked
- The raw sample was readable and yielded `500` packet(s).
- Rows were grouped into event packets using packet metadata rather than received_time.
- Price and quantity string casting succeeded for the processed sample.
- Snapshot/reset handling is implemented, but no snapshot/reset packets were encountered in this sample.
- Normal diff packets were passed through the repaired OFI engine.
- A sample coverage-preserving join was attempted in memory.
- Decision labels: raw_l2_sample_readable, event_grouping_successful, price_quantity_cast_successful, ofi_engine_processed_sample, ofi_reconstruction_dry_run_passed, ofi_values_emitted, coverage_preserving_join_sample_passed, alpha_blocked, paper_live_blocked
- Coverage-preserving join preserved row count in the sample attempt.

## What Failed Or Remains Unknown
- Strict sequence behavior is sample-dependent; if a resync is encountered, the run stops by design.
- Coverage-preserving join readiness is sample-only and may be deferred if the matching bar file or alignment is not available.
- This dry run does not prove alpha, production, or live-trading readiness.

## What Is Safe
- Read-only reconstruction rehearsal on a tiny sample file.
- In-memory OFI summary statistics only.
- Coverage-preserving join helper import/callability checks without writing output.

## What Is Not Safe
- Using this sample as OFI alpha evidence.
- Writing reconstructed OFI artifacts to disk in this task.
- Declaring the full raw L2 corpus gap-free from a single-file dry run.

## Required Next Step
Use this dry-run output to decide whether a larger bounded reconstruction sample is worth attempting. Do not treat the sample as OFI approval.
