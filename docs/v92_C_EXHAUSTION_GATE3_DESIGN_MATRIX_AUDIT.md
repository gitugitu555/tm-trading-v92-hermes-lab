# V9.2 C_Exhaustion Gate 3 Design Matrix Audit

## Purpose

Build the final X/y design matrix in memory under the pre-registered Gate 3 contract, then verify shape, mask integrity, forbidden-feature exclusion, and the train-only scaler plan without fitting a model or scaler.

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

## Read-Only Guardrails

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No feature-table artifacts were written.
- No model artifacts were written.
- No market-data artifacts were written.
- No strategy backtest was run.
- No model was trained.
- No scaler was fitted.
- No predictive metrics were computed.
- No alpha claim is made.
- Full reconstruction remains blocked.

## Pre-Registered Protocol Applied

- primary_label_rule: `net_return_bps > 0`
- split_policy: `train=2020-2023, validation=2024, holdout=2025-2026, out_of_protocol=otherwise`
- purge_rule: `purge any train row whose [signal_time, exit_time] interval overlaps any validation or holdout interval`
- embargo_rule: `use observed max holding interval as a conservative embargo window near the split boundaries`
- approved_feature_count: `24`
- audit_identity_count: `7`
- forbidden_feature_count: `24`

## Design Matrix Summary

- x_row_count: `310`
- y_row_count: `310`
- x_column_count: `24`
- approved_feature_count: `24`
- x_y_row_alignment: `true`
- x_columns_match_contract: `true`
- x_numeric_all_columns: `true`
- x_finite_all_values: `true`
- y_binary: `true`
- y_positive_count: `176`
- y_negative_count: `134`

## Split Mask Summary

- train_rows_before_purge: `259`
- train_rows_after_purge: `259`
- train_rows_after_purge_and_embargo: `259`
- validation_rows: `26`
- holdout_rows: `25`
- out_of_protocol_rows: `0`
- split_mask_exclusive: `true`
- split_mask_complete: `true`
- purge_candidate_count: `0`
- embargo_candidate_count: `1`

## Feature Contract Audit

- approved_features_present_count: `24`
- approved_features_missing_count: `0`
- forbidden_features_present_in_x_count: `0`
- identity_columns_present_in_x_count: `0`
- outcome_columns_present_in_x_count: `0`
- label_column_present_in_x: `false`
- l2_ofi_columns_present_in_x_count: `0`

## Train-Only Scaler Plan

- scaler_required_later: `true`
- scaler_fit_scope: `train_after_purge_and_embargo_only`
- scaler_transform_scope: `validation_and_holdout_after_train_fit_only`
- scaler_fitted: `false`
- validation_seen_during_fit: `false`
- holdout_seen_during_fit: `false`

## Baseline Keep-All Label Distribution

- overall positive_count: `176`
- overall negative_count: `134`
- train positive_count_after_purge_and_embargo: `149`
- train negative_count_after_purge_and_embargo: `110`
- validation positive_count: `18`
- validation negative_count: `8`
- holdout positive_count: `9`
- holdout negative_count: `16`

## What This Proves

- X/y can be built in memory under the pre-registered contract.
- Split masks can be represented.
- Purge and embargo masks can be represented.
- Forbidden columns are excluded.
- Scaler train-only plan can be represented without fitting.
- The system is ready for a future separately approved no-artifact model dry run.

## What This Does Not Prove

- no alpha
- no predictive performance
- no model viability
- no strategy improvement
- no full reconstruction approval
- no paper/live approval

## Gate 3 Status

- Gate 3 protocol checker: pass
- Gate 3 real-data label/split/purge dry run: pass
- Gate 3 no-training design-matrix audit: `pass`
- Gate 3 model training: not started

## Recommended Next Step

Run a bounded Gate 3 logistic-regression-only model dry run with train-only standardization, no model artifacts, validation-only threshold selection if any, and holdout untouched until final reporting.

## What Is Safe

- no-training design-matrix audit
- feature contract verification
- split mask audit
- leakage audit
- future bounded logistic-regression-only model dry run if separately approved

## What Is Not Safe

- model training in this task
- predictive metrics in this task
- alpha claims in this task
- strategy optimization
- backtesting new logic
- full reconstruction
- OFI artifact generation
- paper/live trading

## Decision

- `c_exhaustion_gate3_design_matrix_audit_created`
- `real_trade_log_read`
- `real_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_strategy_backtest_run`
- `no_model_trained`
- `no_scaler_fitted`
- `no_predictive_metrics_computed`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_3_model_training_not_started`
- `gate_3_design_matrix_audit_pass`
