# V9.2 C_Exhaustion Gate 3 Logistic Meta-Label Dry Run

## Purpose

Run a bounded, in-memory logistic-regression-only meta-label dry run for the pre-registered C_Exhaustion Gate 3 protocol.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- feature_table_artifacts_written: `false`
- model_artifacts_written: `false`
- inspected_trade_rows: `310`
- inspected_bar_rows: `203900`
- inspected_bar_files: `90`

## Safety Boundary

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No feature-table artifacts were written.
- No model artifacts were written.
- No strategy logic was changed.
- No replay logic was changed.
- No strategy backtest was run.
- No paper/live trading was run.
- No production approval is given.
- No alpha approval is given.
- Full reconstruction remains blocked.

## Pre-Registered Protocol Applied

- approved feature count: `24`
- label rule: `net_return_bps > 0`
- split policy: `train=2020-2023, validation=2024, holdout=2025-2026`
- purge/embargo rule: `use the design-matrix audit masks derived from signal_time/exit_time overlap and boundary embargo`
- model class: `logistic regression only`
- scaler fit scope: `train_after_purge_and_embargo_only`
- threshold policy: `default 0.50 only`

## Contract / Leakage Audit

- x_row_count: `310`
- y_row_count: `310`
- x_column_count: `24`
- x_y_row_alignment: `true`
- x_columns_match_contract: `true`
- forbidden_features_present_in_x_count: `0`
- identity_columns_present_in_x_count: `0`
- outcome_columns_present_in_x_count: `0`
- label_column_present_in_x: `false`
- x_numeric_all_columns: `true`
- x_finite_all_values: `true`
- y_binary: `true`

## Split Summary

- train rows after purge/embargo: `259`
- validation rows: `26`
- holdout rows: `25`
- train positive: `149`
- train negative: `110`
- validation positive: `18`
- validation negative: `8`
- holdout positive: `9`
- holdout negative: `16`

## Scaler / Model Protocol

- scaler type: `StandardScaler`
- scaler_fit_scope: `train_after_purge_and_embargo_only`
- scaler_fitted_on_train_only: `true`
- validation_seen_during_scaler_fit: `false`
- holdout_seen_during_scaler_fit: `false`
- model class: `LogisticRegression(l2, liblinear, max_iter=1000, random_state=42)`
- model fitted on train only: `true`
- validation used for threshold selection: `false`
- holdout used for threshold selection: `false`

## Keep-All Baseline

| split | count | positive | negative | mean_net_return_bps |
| --- | --- | --- | --- | --- |
| train | 259 | 149 | 110 | 51.760 |
| validation | 26 | 18 | 8 | 113.606 |
| holdout | 25 | 9 | 16 | -108.743 |

## Logistic Threshold 0.50 Results

| split | predicted_keep_count | predicted_skip_count | keep_rate | accuracy | precision | recall | f1 | tn | fp | fn | tp | kept_positive_count | kept_negative_count | kept_mean_net_return_bps | keep_all_mean_net_return_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 175 | 84 | 0.676 | 0.645 | 0.663 | 0.779 | 0.716 | 51 | 59 | 33 | 116 | 116 | 59 | 85.810 | 51.760 |
| validation | 13 | 13 | 0.500 | 0.500 | 0.692 | 0.500 | 0.581 | 4 | 4 | 9 | 9 | 9 | 4 | 154.520 | 113.606 |
| holdout | 9 | 16 | 0.360 | 0.600 | 0.444 | 0.444 | 0.444 | 11 | 5 | 5 | 4 | 4 | 5 | -70.052 | -108.743 |

## Yearly Kept Diagnostics

| year | split | total rows | predicted_keep_count | predicted_skip_count | kept_positive_count | kept_negative_count | kept_mean_net_return_bps | keep_all_mean_net_return_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | train | 21 | 14 | 7 | 12 | 2 | 170.846 | 91.086 |
| 2021 | train | 82 | 72 | 10 | 50 | 22 | 149.947 | 136.328 |
| 2022 | train | 83 | 53 | 30 | 30 | 23 | 15.680 | 4.204 |
| 2023 | train | 73 | 36 | 37 | 24 | 12 | 27.716 | -0.478 |
| 2024 | validation | 26 | 13 | 13 | 9 | 4 | 154.520 | 113.606 |
| 2025 | holdout | 16 | 4 | 12 | 1 | 3 | -56.863 | -160.752 |
| 2026 | holdout | 9 | 5 | 4 | 3 | 2 | -80.603 | -16.282 |

## Holdout Discipline

- Holdout was not used for model fitting.
- Holdout was not used for scaler fitting.
- Holdout was not used for threshold selection.
- Holdout was evaluated once after the protocol was fixed.

## Acceptance Gate Check

| gate | pass |
| --- | --- |
| row_count_preserved_before_filtering | true |
| feature_contract_exact_match | true |
| no_forbidden_columns | true |
| no_leakage_audit_failures | true |
| chronological_splits | true |
| holdout_nontrivial_trade_count | true |
| validation_net_expectancy_vs_keep_all_improved | true |
| validation_trade_count_not_collapsed | true |
| holdout_not_materially_worse_than_keep_all | true |
| yearly_results_not_one_lucky_year | true |
| explicit_cost_model_preserved | true |
| report_includes_failures | true |

## What This Proves

- Logistic dry run can execute under the pre-registered protocol.
- Train-only scaler and model fitting were respected.
- Holdout was kept isolated until final reporting.
- The model diagnostics are now available for review.

## What This Does Not Prove

- no production alpha
- no live readiness
- no paper trading approval
- no full reconstruction approval
- no OFI/L2 approval
- no guarantee of robustness
- no permission to tune further without a new protocol

## Gate 3 Status

- Gate 3 protocol checker: pass
- Gate 3 real-data label/split/purge dry run: pass
- Gate 3 no-training design-matrix audit: pass
- Gate 3 logistic model dry run: `pass`

## Recommended Next Step

Write a Gate 3 review/decision document before any further model classes or experiments.

## What Is Safe

- reviewing this logistic dry-run report
- writing a stop/go decision document
- bounded diagnostic review
- separate pre-registration for any future model class

## What Is Not Safe

- paper/live trading
- production deployment
- threshold retuning on holdout
- feature fishing
- model class fishing
- adding OFI/L2 features
- full reconstruction
- claiming alpha from one dry run

## Decision

- `c_exhaustion_gate3_logistic_meta_label_dry_run_created`
- `real_trade_log_read`
- `real_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_strategy_backtest_run`
- `no_paper_live_trading_run`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `in_memory_logistic_model_trained`
- `in_memory_train_only_scaler_fitted`
- `default_threshold_only`
- `gate_3_logistic_dry_run_pass`
