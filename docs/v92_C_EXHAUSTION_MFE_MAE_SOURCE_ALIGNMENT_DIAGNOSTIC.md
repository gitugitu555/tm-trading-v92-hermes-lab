# V9.2 C_Exhaustion MFE/MAE Source Alignment Diagnostic

## Purpose

This is a bounded source-remediation alignment diagnostic only. It inspects timestamp, index, and bar-shard matching feasibility after the MFE/MAE source-construction dry run failed to match any trade intervals.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bounded_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- row_level_artifacts_written: `false`
- mfe_mae_computed: `false`
- giveback_classified: `false`
- source_script_patched: `false`

## Safety Boundary

- No MFE/MAE was computed.
- No giveback classification was performed.
- No source-construction script was patched.
- No exit horizon was optimized.
- No target/stop tuning was performed.
- No threshold tuning was performed.
- No model was trained.
- No strategy backtest was run.
- No strategy/replay logic was changed.
- No raw L2 data was read.
- No OFI artifacts were read or written.
- No row-level artifacts were written.
- No feature-table artifacts were written.
- No model artifacts were written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Source-Construction Failure Recap

- trade_rows_loaded: `310`
- bar_rows_loaded: `204124`
- bar_files_read: `102`
- rows_with_matched_bars: `0`
- unresolved_rows: `310`
- decision from previous dry run: `bounded_mfe_mae_source_construction_blocked`

## Trade Log Timestamp Audit

| metric | value | dtype | timezone | precision |
| --- | --- | --- | --- | --- |
| min_signal_time | 2020-09-02 11:09:58.270000 | datetime64[us] | timezone-naive | 1607120ms |
| max_signal_time | 2026-05-07 14:07:47.113084 | datetime64[us] | timezone-naive | 1607120ms |
| min_entry_time | 2020-09-02 11:09:58.270000 | datetime64[us] | timezone-naive | 1607120ms |
| max_entry_time | 2026-05-07 14:07:47.113084 | datetime64[us] | timezone-naive | 1607120ms |
| min_exit_time | 2020-09-02 14:59:44.128000 | datetime64[us] | timezone-naive | 1643502ms |
| max_exit_time | 2026-05-09 07:27:02.915893 | datetime64[us] | timezone-naive | 1643502ms |

## Bar Timestamp Audit

| metric | value | dtype | timezone | precision |
| --- | --- | --- | --- | --- |
| min_open_time | 2020-05-22 00:00:00.125000 | datetime64[ns] | timezone-naive | 25ms |
| max_open_time | 2026-05-21 23:45:47.866763 | datetime64[ns] | timezone-naive | 25ms |
| min_close_time | 2020-05-22 00:12:03.705000 | datetime64[ns] | timezone-naive | 24ms |
| max_close_time | 2026-05-21 23:59:59.849615 | datetime64[ns] | timezone-naive | 24ms |
| number_of_bar_files_loaded | 102 | datetime64[ns] | timezone-naive | 25ms |
| number_of_bar_rows_loaded | 204124 | datetime64[ns] | timezone-naive | 25ms |

## Time Range Coverage

- signal_time_inside_bar_range_count: `310`
- entry_time_inside_bar_range_count: `310`
- exit_time_inside_bar_range_count: `310`
- all_interval_inside_bar_range_count: `310`
- outside_range_count: `0`

## Exact Timestamp Match Rates

| label | matched_count | match_rate |
| --- | --- | --- |
| signal_time == bar open_time | 0 | 0.000000 |
| signal_time == bar close_time | 310 | 1.000000 |
| entry_time == bar open_time | 310 | 1.000000 |
| entry_time == bar close_time | 0 | 0.000000 |
| exit_time == bar open_time | 310 | 1.000000 |
| exit_time == bar close_time | 0 | 0.000000 |

## Nearest Timestamp Distance Summary

| label | median | min | max |
| --- | --- | --- | --- |
| signal_time_nearest_open | 0 days 00:00:00 | 0 days 00:00:00 | 0 days 00:00:00.150000 |
| signal_time_nearest_close | 0 days 00:00:00 | 0 days 00:00:00 | 0 days 00:00:00 |
| entry_time_nearest_open | 0 days 00:00:00 | 0 days 00:00:00 | 0 days 00:00:00 |
| entry_time_nearest_close | 0 days 00:00:00 | 0 days 00:00:00 | 0 days 00:00:00.150000 |
| exit_time_nearest_open | 0 days 00:00:00 | 0 days 00:00:00 | 0 days 00:00:00 |
| exit_time_nearest_close | 0 days 00:00:00.001000 | 0 days 00:00:00 | 0 days 00:00:01.480000 |

## Interval Overlap Convention Audit

| convention | matched_trade_count | zero_match_trade_count | median_matched_bar_count | 2025_matched_trade_count | 2026_matched_trade_count |
| --- | --- | --- | --- | --- | --- |
| half_open_open_time_convention | 310 | 0 | 36.000000 | 16 | 9 |
| closed_open_time_convention | 310 | 0 | 37.000000 | 16 | 9 |
| close_time_convention | 310 | 0 | 36.000000 | 16 | 9 |
| broad_overlap_convention | 310 | 0 | 38.000000 | 16 | 9 |

## Index Mapping Feasibility

| metric | value |
| --- | --- |
| bar_id_available | true |
| entry_index_min | 7496 |
| entry_index_max | 203856 |
| exit_index_min | 7532 |
| exit_index_max | 203892 |
| bar_row_count | 204124 |
| indices_within_row_range | true |
| entry_index_count_in_bar_id | 9 |
| exit_index_count_in_bar_id | 9 |
| both_indices_count_in_bar_id | 9 |
| entry_index_le_exit_index_count | 310 |
| valid_bar_id_range_count | 9 |

## Shard Coverage Audit

| metric | value |
| --- | --- |
| number_of_bar_files_discovered | 102 |
| number_loaded | 102 |
| first_shard_name | BTCUSDT_tier2_750btc_2020-05-22.parquet |
| last_shard_name | BTCUSDT_tier2_750btc_2026-05-21.parquet |
| date_month_tokens | 2020-05-22, 2020-05-23, 2020-05-24, 2020-05-25, 2020-05-26, 2020-05-27, 2020-05-28, 2020-05-29, 2020-05-30, 2020-05-31 |
| trade_years_covered | true |
| day_month_duplication_present | true |
| wrong_day_fallback_risk_detected | false |
| coverage_2026_05 | true |
| coverage_2026_05_09 | true |

## Candidate Root Cause

- candidate_root_cause: `timestamp_precision_or_timezone_mismatch`

Explanation:
- The timestamps appear parseable but differ in timezone or precision normalization.

## Safe Matching Convention Decision

- decision: `safe_timestamp_open_time_convention_identified`

## What This Proves

- whether trade and bar sources overlap in time
- whether exact timestamp matching is viable
- whether interval overlap is viable
- whether index mapping is viable
- whether source construction can be retried safely

## What This Does Not Prove

- no MFE/MAE
- no giveback classification
- no exit optimization
- no strategy improvement
- no alpha approval
- no paper/live readiness
- no production readiness

## Recommended Next Step

Recommend a separate preregistered patch to the MFE/MAE source-construction script using the fixed convention, followed by a bounded rerun.

## Explicitly Not Approved

- No MFE/MAE computation.
- No giveback classification.
- No paper trading.
- No live trading.
- No production deployment.
- No additional model classes.
- No threshold tuning.
- No feature fishing.
- No OFI/L2 integration.
- No full reconstruction.
- No claims of alpha.
- No strategy/replay changes.
- No exit-horizon optimization.
- No target/stop tuning.
- No backtest reruns.
- No row-level artifact persistence.

## Decision

Decision: `source_alignment_diagnostic_pass`

## Decision Labels

- `c_exhaustion_mfe_mae_source_alignment_diagnostic_created`
- `source_alignment_only`
- `real_trade_log_read`
- `real_bounded_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_mfe_mae_computed`
- `no_giveback_classification`
- `no_source_script_patch`
- `no_row_level_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_strategy_backtest_run`
- `no_strategy_replay_changes`
- `no_exit_optimization`
- `no_target_stop_tuning`
- `no_threshold_tuning`
- `no_new_model_trained`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `production_not_approved`
- `source_alignment_diagnostic_pass`
