# V9.2 L2 OFI Dry-Run Micro-Batch Aggregate

## Purpose
Summarize the four existing micro batch markdown reports as a metadata-only aggregate, without reading raw L2 data, bar data, or writing any OFI artifacts.

## Inputs
- `aggregate_scope`: `micro_bounded_batch_aggregate`
- `batch_count`: `4`
- `source_batch_reports`:
  - `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_00.md`
  - `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_01.md`
  - `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_02.md`
  - `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_03.md`
- `max_candidate_files`: `120`
- `preview_rows_per_file`: `5000`
- `max_policy_check_files`: `20`

## Read-Only Guardrails
- This aggregate was built from existing markdown batch reports only.
- No raw L2 parquet or zst data was read.
- No bar parquet data was read.
- No OFI artifacts were written.
- No packet tables were written.
- No derived OFI data were written.

## Batch Reports Included
- `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_00.md`
- `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_01.md`
- `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_02.md`
- `docs/v92_L2_OFI_RECONSTRUCTION_DRY_RUN_BATCH_03.md`

## Aggregate Counts
- `total_selected_files`: `120`
- `total_previewed_files`: `120`
- `total_policy_checked_files`: `80`
- `accepted_total`: `80`
- `accepted_bounded_clean`: `76`
- `accepted_bounded_source_gap_clean`: `0`
- `accepted_bounded_snapshot_bridge_clean`: `4`
- `quarantined_total`: `0`
- `rejected_dirty_total`: `0`
- `deferred_total`: `0`

## Policy Classification Aggregate
| policy_check_status | count |
| --- | ---: |
| `accepted_bounded_clean` | `76` |
| `accepted_bounded_snapshot_bridge_clean` | `4` |
| `accepted_bounded_source_gap_clean` | `0` |

## Join-Readiness Aggregate
- `join_attempted_total`: `17`
- `join_deferred_total`: `63`
- `join_preserved_total`: `17`
- `join_not_preserved_total`: `0`

## Batch Consistency Checks
- All four batch reports exist.
- Batch indices are exactly `0`, `1`, `2`, and `3`.
- Each batch has `candidate_batch_count = 4`.
- Each batch has `dry_run_scope = full_bounded_manifest_batch`.
- No batch claims `full_bounded_manifest_completed`.
- Each batch includes `full_bounded_manifest_batch_completed`.
- Each batch includes the required safety statement.
- The aggregate does not claim `full_bounded_manifest_completed`.
- The aggregate does not approve full reconstruction.

## What Worked
- The four batch reports provide a complete micro-batch metadata summary.
- The aggregate totals reconcile to the known per-batch counts.
- Join-readiness was preserved for the 17 attempts that were made.

## What Failed Or Remains Unknown
- This aggregate is metadata-only and does not validate any new raw data paths.
- It does not change policy, replay, or OFIEngine behavior.
- It does not establish broader reconstruction approval.

## What Is Safe
- Using this aggregate as a metadata summary of the four pushed batch reports.
- Treating the counted batch outcomes as bounded-validation evidence only.
- Continuing with metadata-only validation and reporting.

## What Is Not Safe
- Approving full reconstruction.
- Approving OFI for production, paper trading, live trading, or alpha use.
- Inferring broader raw-data coverage beyond the four included batch reports.

## Decision
`micro_bounded_batch_aggregate_completed`, `batch_reports_parsed_only`, `no_raw_l2_data_read`, `no_bar_data_read`, `no_ofi_artifacts_written`, `full_reconstruction_not_approved`, `segmented_reconstruction_still_bounded_only`, `alpha_blocked`, `paper_live_blocked`

## Required Next Step
Use this aggregate only as a bounded-validation summary. Do not promote the workflow to full reconstruction or artifact generation.

This aggregate does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.
