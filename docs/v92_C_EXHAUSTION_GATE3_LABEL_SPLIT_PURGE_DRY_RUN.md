# V9.2 C_Exhaustion Gate 3 Label/Split/Purge Dry Run

## Purpose

Apply the pre-registered Gate 3 label, chronological split, feature contract, forbidden-feature audit, and purge/embargo protocol to the existing real C_Exhaustion trade log and approved in-memory signal-time feature table construction.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- feature_table_artifacts_written: `false`
- inspected_trade_rows: `310`
- inspected_bar_rows: `203900`
- inspected_bar_files: `90`

## Read-Only Guardrails

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No feature-table artifacts were written.
- No market-data artifacts were written.
- No strategy backtest was run.
- No model was trained.
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

## Row Count Summary

- trade_rows_loaded: `310`
- feature_rows_constructed: `310`
- row_count_preserved_before_protocol: `true`
- row_count_after_label: `310`
- row_count_after_split_assignment: `310`
- row_count_after_purge: `310`
- row_count_after_embargo: `310`

## Feature Contract Check

- approved_features_present_count: `24`
- approved_features_missing_count: `0`
- forbidden_features_present_in_model_matrix_count: `0`
- audit_identity_columns_excluded_from_model_features: `true`
- outcome_columns_excluded_from_model_features: `true`
- l2_ofi_columns_excluded_from_model_features: `true`
- label_column_excluded_from_model_features: `true`

## Label Distribution

- overall positive_count: `176`
- overall negative_count: `134`
- overall total_count: `310`

### By Year

| year | positive | negative | total |
| --- | --- | --- | --- |
| 2020 | 13 | 8 | 21 |
| 2021 | 55 | 27 | 82 |
| 2022 | 43 | 40 | 83 |
| 2023 | 38 | 35 | 73 |
| 2024 | 18 | 8 | 26 |
| 2025 | 4 | 12 | 16 |
| 2026 | 5 | 4 | 9 |

### By Split

| split | positive | negative | total |
| --- | --- | --- | --- |
| train | 149 | 110 | 259 |
| validation | 18 | 8 | 26 |
| holdout | 9 | 16 | 25 |
| out_of_protocol | 0 | 0 | 0 |

## Split Assignment Summary

- train_count_before_purge: `259`
- validation_count: `26`
- holdout_count: `25`
- out_of_protocol_count: `0`

| year | train | validation | holdout | out_of_protocol | total |
| --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 0 | 0 | 0 | 21 |
| 2021 | 82 | 0 | 0 | 0 | 82 |
| 2022 | 83 | 0 | 0 | 0 | 83 |
| 2023 | 73 | 0 | 0 | 0 | 73 |
| 2024 | 0 | 26 | 0 | 0 | 26 |
| 2025 | 0 | 0 | 16 | 0 | 16 |
| 2026 | 0 | 0 | 9 | 0 | 9 |

## Purge / Embargo Summary

- purge_candidate_count: `0`
- embargo_candidate_count: `1`
- train_count_after_purge: `259`
- train_count_after_purge_and_embargo: `259`
- validation_embargo_candidate_count: `1`
- holdout_embargo_candidate_count: `0`
- max_holding_interval_observed: `2 days 04:39:05.466615`
- embargo_window_used: `2 days 04:39:05.466615`
- overlap_detection_exercised: `false`
- split_boundary_embargo_exercised: `true`

## Sample-Size Readiness

- validation_min_required_count: `8`
- validation_actual_count: `26`
- validation_sample_size_rule_pass: `true`
- holdout_min_required_count: `8`
- holdout_actual_count: `25`
- holdout_sample_size_rule_pass: `true`

## What This Proves

- real trade log can be labeled under the pre-registered label
- real rows can be split chronologically
- purge and embargo can be applied mechanically
- feature contract can be checked on real in-memory feature table
- forbidden features remain excluded

## What This Does Not Prove

- no alpha
- no predictive performance
- no model viability
- no strategy improvement
- no full reconstruction approval
- no paper/live approval

## Gate 3 Status

- Gate 3 protocol checker: pass
- Gate 3 real-data label/split/purge dry run: `pass`
- Gate 3 model training: not started

## Recommended Next Step

Run a Gate 3 no-training design-matrix audit that builds X/y in memory, verifies final shapes, split masks, forbidden-feature exclusion, scaler-fit-on-train-only plan, and baseline keep-all label distribution, but still trains no model and computes no predictive metrics.

## What Is Safe

- real-data label/split/purge dry run
- feature contract verification
- leakage audit
- future no-training design-matrix audit

## What Is Not Safe

- model training in this task
- predictive metrics in this task
- alpha claims
- strategy optimization
- backtesting new logic
- full reconstruction
- OFI artifact generation
- paper/live trading

## Decision

- `c_exhaustion_gate3_label_split_purge_dry_run_created`
- `real_trade_log_read`
- `real_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_strategy_backtest_run`
- `no_model_trained`
- `no_predictive_metrics_computed`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_3_model_training_not_started`
- `gate_3_label_split_purge_dry_run_pass`
