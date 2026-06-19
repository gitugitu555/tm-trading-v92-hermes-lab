# V9.2 C_Exhaustion MFE/MAE Source Construction Dry Run

## Purpose

This is a bounded descriptive source-construction dry run only. It computes row-level MFE/MAE and giveback diagnostics in memory from the existing trade log and bounded 750btc bars, and writes only a Markdown summary.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- row_level_artifacts_written: `false`
- feature_table_artifacts_written: `false`
- model_artifacts_written: `false`

## Safety Boundary

- No model was trained.
- No model was refit.
- No scaler was refit.
- No threshold was tuned.
- No exit horizon was optimized.
- No target/stop tuning was performed.
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

## Source-Alignment Patch Applied

- source_alignment_patch_applied: `true`
- source_alignment_report: `docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_ALIGNMENT_DIAGNOSTIC.md`
- alignment decision: `safe_timestamp_open_time_convention_identified`
- primary convention: `half_open_open_time_convention`
- interval rule: `bar.open_time >= entry_time and bar.open_time < exit_time`
- no alternative exits searched
- no convention selected by performance
- no source alignment optimization

## Pre-Registered Protocol Applied

- source preregistration file path: `docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_PREREGISTRATION.md`
- existing trade intervals only
- bounded 750btc bars only
- side_basis: `long-only (assumed; side column absent)`
- interval_convention: `half_open_open_time_convention`
- no alternative exits searched
- classification framework: `bad_entry_loss`, `giveback_loss`, `weak_positive_exit`, `clean_winner`, `unresolved`
- weak_positive_exit threshold fixed at 50% giveback of MFE
- no threshold tuning

## Source Construction Summary

- trade_rows_loaded: `310`
- bar_rows_loaded: `204124`
- bar_files_read: `102`
- rows_with_matched_bars: `310`
- rows_without_matched_bars: `0`
- unresolved_rows: `0`
- year_min: `2020`
- year_max: `2026`
- side_basis: `long-only (assumed; side column absent)`
- final_return_basis: `gross_return_bps`
- interval_convention: `half_open_open_time_convention`

## Classification Counts

| bad_entry_loss | giveback_loss | weak_positive_exit | clean_winner | unresolved |
| --- | --- | --- | --- | --- |
| 0 | 125 | 55 | 130 | 0 |

| year | bad_entry_loss | giveback_loss | weak_positive_exit | clean_winner | unresolved |
| --- | --- | --- | --- | --- | --- |
| 2020 | 0 | 8 | 1 | 12 | 0 |
| 2021 | 0 | 27 | 16 | 39 | 0 |
| 2022 | 0 | 36 | 13 | 34 | 0 |
| 2023 | 0 | 31 | 15 | 27 | 0 |
| 2024 | 0 | 8 | 4 | 14 | 0 |
| 2025 | 0 | 12 | 3 | 1 | 0 |
| 2026 | 0 | 3 | 3 | 3 | 0 |

## Losing Trade Giveback Summary

- losing_trade_count: `125`
- losing_trades_with_positive_mfe: `125`
- losing_trades_without_positive_mfe: `0`
- positive_mfe_before_loss_rate: `1.000`
- giveback_loss_count: `125`
- bad_entry_loss_count: `0`

| year | losing_trade_count | losing_trades_with_positive_mfe | losing_trades_without_positive_mfe | positive_mfe_before_loss_rate | giveback_loss_count | bad_entry_loss_count |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8 | 8 | 0 | 1.000 | 8 | 0 |
| 2021 | 27 | 27 | 0 | 1.000 | 27 | 0 |
| 2022 | 36 | 36 | 0 | 1.000 | 36 | 0 |
| 2023 | 31 | 31 | 0 | 1.000 | 31 | 0 |
| 2024 | 8 | 8 | 0 | 1.000 | 8 | 0 |
| 2025 | 12 | 12 | 0 | 1.000 | 12 | 0 |
| 2026 | 3 | 3 | 0 | 1.000 | 3 | 0 |

## Excursion Summary By Year

| year | count | avg_mfe_bps | median_mfe_bps | avg_mae_bps | median_mae_bps | avg_mfe_giveback_bps | median_mfe_giveback_bps | avg_time_to_mfe_bars | median_time_to_mfe_bars | avg_time_to_mae_bars | median_time_to_mae_bars | avg_time_from_mfe_to_exit_bars | median_time_from_mfe_to_exit_bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 252.320 | 209.071 | -154.109 | -89.990 | 149.234 | 122.683 | 20.190 | 18.000 | 9.048 | 5.000 | 14.810 | 17.000 |
| 2021 | 82 | 351.453 | 299.425 | -224.048 | -166.753 | 203.125 | 153.997 | 19.098 | 19.500 | 13.159 | 8.500 | 15.902 | 15.500 |
| 2022 | 83 | 149.459 | 94.734 | -118.247 | -79.267 | 133.255 | 90.635 | 16.325 | 13.000 | 16.337 | 17.000 | 18.675 | 22.000 |
| 2023 | 73 | 88.236 | 68.516 | -87.712 | -60.791 | 76.715 | 58.268 | 16.932 | 16.000 | 14.877 | 12.000 | 18.068 | 19.000 |
| 2024 | 26 | 275.258 | 251.376 | -160.684 | -133.095 | 149.651 | 122.702 | 20.500 | 21.000 | 15.769 | 7.500 | 14.500 | 14.000 |
| 2025 | 16 | 148.943 | 141.610 | -256.960 | -279.982 | 297.695 | 313.279 | 9.562 | 5.500 | 25.625 | 30.000 | 25.438 | 29.500 |
| 2026 | 9 | 161.966 | 129.631 | -193.079 | -163.987 | 166.248 | 86.240 | 17.333 | 18.000 | 14.889 | 14.000 | 17.667 | 17.000 |

## 2025 vs 2026 Holdout Comparison

| year | total trades | losing trades | positive-MFE-before-loss count | giveback_loss count | bad_entry_loss count | weak_positive_exit count | clean_winner count | unresolved count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 | 16 | 12 | 12 | 12 | 0 | 3 | 1 | 0 |
| 2026 | 9 | 3 | 3 | 3 | 0 | 3 | 3 | 0 |

Interpretation:
- 2025 improved versus keep-all in the earlier diagnostics but remained negative.
- 2026 worsened versus keep-all in the earlier diagnostics.
- This source-construction dry run is intended to determine whether those losses are more consistent with bad entries or giveback failures.

## Kept vs Skipped Comparison

Row-level logistic kept/skipped decisions were not available as an approved row-level source.
The dry run did not retrain or rerun the logistic model to reconstruct predictions.
Kept/skipped giveback comparison is deferred until row-level predictions are separately available or pre-registered.

## What This Proves

- Row-level MFE/MAE source construction can be performed safely from the matched trade intervals and bounded bars that were found under `half_open_open_time_convention`.
- Descriptive giveback labels can be assigned without changing strategy logic.
- The output can distinguish bad entries from giveback failures for matched rows.
- The resulting diagnostics can show whether 2026 requires further investigation.

## What This Does Not Prove

- no alpha approval
- no strategy improvement
- no exit optimization
- no target/stop approval
- no paper/live readiness
- no production readiness
- no OFI/L2 approval

## Stop / Go Assessment

- stop/pause modeling if most 2025/2026 losses are giveback_loss
- stop/pause modeling if logistic-kept 2026 losers are mostly giveback_loss, if known
- stop/pause if reconstruction is unsafe or incomplete
- continue only if the next hypothesis is non-leaky and separately pre-registered

## Recommended Next Step

Recommend an exit-management diagnostic review document, not an optimization run.

## Explicitly Not Approved

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

Decision: `bounded_mfe_mae_source_construction_pass`

## Decision Labels

- `c_exhaustion_mfe_mae_source_construction_dry_run_created`
- `bounded_descriptive_only`
- `real_trade_log_read`
- `real_bounded_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
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
- `bounded_mfe_mae_source_construction_pass`
