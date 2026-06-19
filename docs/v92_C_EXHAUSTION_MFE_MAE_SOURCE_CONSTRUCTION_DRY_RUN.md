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

## Pre-Registered Protocol Applied

- source preregistration file path: `docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_PREREGISTRATION.md`
- existing trade intervals only
- bounded 750btc bars only
- side_basis: `long-only (assumed; side column absent)`
- no alternative exits searched
- classification framework: `bad_entry_loss`, `giveback_loss`, `weak_positive_exit`, `clean_winner`, `unresolved`
- weak_positive_exit threshold fixed at 50% giveback of MFE
- no threshold tuning

## Source Construction Summary

- trade_rows_loaded: `310`
- bar_rows_loaded: `204124`
- bar_files_read: `102`
- rows_with_matched_bars: `0`
- rows_without_matched_bars: `310`
- unresolved_rows: `310`
- year_min: `2020`
- year_max: `2026`
- side_basis: `long-only (assumed; side column absent)`
- final_return_basis: `gross_return_bps`

## Classification Counts

| bad_entry_loss | giveback_loss | weak_positive_exit | clean_winner | unresolved |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 310 |

| year | bad_entry_loss | giveback_loss | weak_positive_exit | clean_winner | unresolved |
| --- | --- | --- | --- | --- | --- |
| 2020 | 0 | 0 | 0 | 0 | 0 |
| 2021 | 0 | 0 | 0 | 0 | 0 |
| 2022 | 0 | 0 | 0 | 0 | 0 |
| 2023 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 0 | 0 | 0 | 0 | 0 |
| 2026 | 0 | 0 | 0 | 0 | 0 |

## Losing Trade Giveback Summary

- losing_trade_count: `0`
- losing_trades_with_positive_mfe: `0`
- losing_trades_without_positive_mfe: `0`
- positive_mfe_before_loss_rate: `n/a`
- giveback_loss_count: `0`
- bad_entry_loss_count: `0`

| year | losing_trade_count | losing_trades_with_positive_mfe | losing_trades_without_positive_mfe | positive_mfe_before_loss_rate | giveback_loss_count | bad_entry_loss_count |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2021 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2022 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2023 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2024 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2025 | 0 | 0 | 0 | n/a | 0 | 0 |
| 2026 | 0 | 0 | 0 | n/a | 0 | 0 |

## Excursion Summary By Year

| year | count | avg_mfe_bps | median_mfe_bps | avg_mae_bps | median_mae_bps | avg_mfe_giveback_bps | median_mfe_giveback_bps | avg_time_to_mfe_bars | median_time_to_mfe_bars | avg_time_to_mae_bars | median_time_to_mae_bars | avg_time_from_mfe_to_exit_bars | median_time_from_mfe_to_exit_bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2021 | 82 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2022 | 83 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2023 | 73 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2024 | 26 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2025 | 16 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2026 | 9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## 2025 vs 2026 Holdout Comparison

| year | total trades | losing trades | positive-MFE-before-loss count | giveback_loss count | bad_entry_loss count | weak_positive_exit count | clean_winner count | unresolved count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Interpretation:
- 2025 improved versus keep-all in the earlier diagnostics but remained negative.
- 2026 worsened versus keep-all in the earlier diagnostics.
- This source-construction dry run is intended to determine whether those losses are more consistent with bad entries or giveback failures.

## Kept vs Skipped Comparison

Row-level logistic kept/skipped decisions were not available as an approved row-level source.
The dry run did not retrain or rerun the logistic model to reconstruct predictions.
Kept/skipped giveback comparison is deferred until row-level predictions are separately available or pre-registered.

## What This Proves

- The current bounded bar source does not overlap the trade intervals closely enough to complete row-level MFE/MAE source construction.
- The audit confirms the source gap remains blocking for trade-row excursion diagnostics.
- No descriptive giveback labels were assigned because no matching bars were found.
- 2026 and the other years remain unresolved until source availability is remediated or separately approved.

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

Recommend source-remediation preregistration, not reconstruction or optimization.

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

Decision: `bounded_mfe_mae_source_construction_blocked`

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
- `bounded_mfe_mae_source_construction_blocked`
