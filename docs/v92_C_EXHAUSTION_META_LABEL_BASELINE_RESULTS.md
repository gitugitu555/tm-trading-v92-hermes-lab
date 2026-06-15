# C_ExhaustionFade Meta-Label Baseline Results

## Purpose

Establish the canonical ex-ante meta-label dataset and a purged walk-forward evaluator scaffold for C_ExhaustionFade.

This task does not approve a production model, production gate, paper-trading rule, or live-trading rule.

## Research-Only Guardrails

- No random split.
- No shuffle split.
- No train/test leakage.
- No post-signal features as inputs.
- No production approval.

## Data Sources

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay context and regime labels from the repaired C_ExhaustionFade replay path

## Dataset Construction

- Canonical C trades: `310`
- `label_trade_win` positive rate: `0.567742`
- `label_bad_context_36` positive rate: `0.322581`
- `label_recent_decay` positive rate: `0.080645`

## Allowed Features

| feature | available | null_count |
| --- | --- | --- |
| pre_signal_return_12_bars_bps | true | 0 |
| pre_signal_return_24_bars_bps | true | 0 |
| pre_signal_return_36_bars_bps | true | 0 |
| realized_vol_12_bars_bps | true | 0 |
| realized_vol_24_bars_bps | true | 0 |
| realized_vol_36_bars_bps | true | 0 |
| range_expansion_ratio_12 | true | 0 |
| range_expansion_ratio_24 | true | 0 |
| range_expansion_ratio_36 | true | 0 |
| body_to_range_ratio | true | 0 |
| volume_over_vol95_ratio | true | 0 |
| close_vs_local_low_bps | true | 0 |
| adr_stretch | true | 0 |
| rv_1d | true | 0 |
| rv_15th_pct | true | 13 |
| bar_range | true | 0 |
| body_size | true | 0 |
| volume | true | 0 |
| vol_roll_95 | true | 0 |

## Forbidden Features

- `net_return_bps`
- `gross_return_bps`
- `exit_time`
- `exit_price`
- `mfe_bps`
- `mae_bps`
- `post_signal_return_`
- `trend_continuation_flag_`
- `failed_reversal_flag_`
- `bad_context_label_`
- `label_recent_decay`
- `year >= 2025`
- `anything computed after signal_time`

## Labels

| label | definition | positive_count | positive_rate |
| --- | --- | --- | --- |
| label_trade_win | net_return_bps > 0 | 176 | 0.567742 |
| label_positive_tail | net_return_bps >= 200 | 60 | 0.193548 |
| label_negative_tail | net_return_bps <= -200 | 40 | 0.129032 |
| label_bad_context_36 | trend_continuation_flag_36 OR failed_reversal_flag_36 | 100 | 0.322581 |
| label_recent_decay | year >= 2025 | 25 | 0.080645 |

## Purged Walk-Forward Design

Validation is time-ordered only with a conservative bar-index purge and embargo around fold boundaries.

| split | train_years | validate_year | test_year | purge_bars | embargo_bars | train_count | validate_count | test_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| walk_forward_1 | 2020-2021 | 2022 | 2023 | 48 | 48 | 103 | 82 | 72 |
| walk_forward_2 | 2020-2021-2022 | 2023 | 2024 | 48 | 48 | 186 | 72 | 25 |
| walk_forward_3 | 2020-2021-2022-2023 | 2024 | 2025 | 48 | 48 | 259 | 25 | 15 |
| walk_forward_4 | 2020-2021-2022-2023-2024 | 2025 | 2026 | 48 | 48 | 285 | 15 | 8 |

## Model Families

- `sklearn_available`: `true`
- `logistic_regression_l2`
- `decision_tree_depth_2`
- `decision_tree_depth_3`

## Fold Results

| split | validate_year | test_year | model_family | model_status | validation_sample_too_small | best_available_threshold_diagnostic_only | train_count | validate_count | test_count | selected_threshold | validate_precision | validate_recall | validate_f1 | test_precision | test_recall | test_f1 | test_accuracy | test_auc_if_available | test_kept_trade_count | test_removed_trade_count | test_kept_rate | test_net_expectancy_bps_if_trading_kept_signals | test_win_rate_if_trading_kept_signals | test_profit_factor_if_trading_kept_signals | baseline_no_gate_test_net_expectancy_bps | delta_vs_baseline_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| walk_forward_1 | 2022 | 2023 | logistic_regression_l2 | model_execution_completed | false | 0.600000 | 103 | 82 | 72 | 0.600000 | 0.539683 | 0.809524 | 0.647619 | 0.529412 | 0.972973 | 0.685714 | 0.541667 | 0.504247 | 68 | 4 | 0.944444 | 1.202139 | 0.529412 | 1.032269 | -1.316009 | 2.518147 |
| walk_forward_1 | 2022 | 2023 | decision_tree_depth_2 | model_execution_completed | false | 0.700000 | 103 | 82 | 72 | 0.700000 | 0.568966 | 0.785714 | 0.660000 | 0.492308 | 0.864865 | 0.627451 | 0.472222 | 0.498842 | 65 | 7 | 0.902778 | -8.690700 | 0.492308 | 0.788576 | -1.316009 | -7.374692 |
| walk_forward_1 | 2022 | 2023 | decision_tree_depth_3 | model_execution_completed | false | 0.700000 | 103 | 82 | 72 | 0.700000 | 0.714286 | 0.238095 | 0.357143 | 0.555556 | 0.135135 | 0.217391 | 0.500000 | 0.437066 | 9 | 63 | 0.125000 | -41.073572 | 0.555556 | 0.426741 | -1.316009 | -39.757563 |
| walk_forward_2 | 2023 | 2024 | logistic_regression_l2 | model_execution_completed | false | 0.650000 | 186 | 72 | 25 | 0.650000 | 0.692308 | 0.243243 | 0.360000 | 0.650000 | 0.764706 | 0.702703 | 0.560000 | 0.441176 | 20 | 5 | 0.800000 | 115.205125 | 0.650000 | 2.579658 | 108.461973 | 6.743152 |
| walk_forward_2 | 2023 | 2024 | decision_tree_depth_2 | model_execution_completed | false | 0.400000 | 186 | 72 | 25 | 0.400000 | 0.513889 | 1.000000 | 0.678899 | 0.680000 | 1.000000 | 0.809524 | 0.680000 | 0.492647 | 25 | 0 | 1.000000 | 108.461973 | 0.680000 | 2.541552 | 108.461973 | 0.000000 |
| walk_forward_2 | 2023 | 2024 | decision_tree_depth_3 | model_execution_completed | false | 0.300000 | 186 | 72 | 25 | 0.300000 | 0.513889 | 1.000000 | 0.678899 | 0.680000 | 1.000000 | 0.809524 | 0.680000 | 0.566176 | 25 | 0 | 1.000000 | 108.461973 | 0.680000 | 2.541552 | 108.461973 | 0.000000 |
| walk_forward_3 | 2024 | 2025 | logistic_regression_l2 | model_execution_completed | false | 0.650000 | 259 | 25 | 15 | 0.650000 | 0.666667 | 0.705882 | 0.685714 | 0.230769 | 0.750000 | 0.352941 | 0.266667 | 0.659091 | 13 | 2 | 0.866667 | -155.800103 | 0.230769 | 0.088704 | -151.297784 | -4.502319 |
| walk_forward_3 | 2024 | 2025 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 259 | 25 | 15 | 0.550000 | 0.708333 | 1.000000 | 0.829268 | 0.285714 | 1.000000 | 0.444444 | 0.333333 | 0.340909 | 14 | 1 | 0.933333 | -144.965558 | 0.285714 | 0.102601 | -151.297784 | 6.332226 |
| walk_forward_3 | 2024 | 2025 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 259 | 25 | 15 | 0.550000 | 0.695652 | 0.941176 | 0.800000 | 0.285714 | 1.000000 | 0.444444 | 0.333333 | 0.340909 | 14 | 1 | 0.933333 | -144.965558 | 0.285714 | 0.102601 | -151.297784 | 6.332226 |
| walk_forward_4 | 2025 | 2026 | logistic_regression_l2 | model_execution_completed | false | 0.700000 | 285 | 15 | 8 | 0.700000 | 0.300000 | 0.750000 | 0.428571 | 0.666667 | 0.400000 | 0.500000 | 0.500000 | 0.466667 | 3 | 5 | 0.375000 | -22.622541 | 0.666667 | 0.682204 | -18.261942 | -4.360599 |
| walk_forward_4 | 2025 | 2026 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 285 | 15 | 8 | 0.550000 | 0.285714 | 1.000000 | 0.444444 | 0.625000 | 1.000000 | 0.769231 | 0.625000 | 0.533333 | 8 | 0 | 1.000000 | -18.261942 | 0.625000 | 0.806865 | -18.261942 | 0.000000 |
| walk_forward_4 | 2025 | 2026 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 285 | 15 | 8 | 0.550000 | 0.285714 | 1.000000 | 0.444444 | 0.714286 | 1.000000 | 0.833333 | 0.750000 | 0.600000 | 7 | 1 | 0.875000 | 9.637375 | 0.714286 | 1.124265 | -18.261942 | 27.899317 |

## Recent-Period Results

| split | test_year | model_family | model_status | validation_sample_too_small | selected_threshold | test_kept_trade_count | test_removed_trade_count | test_kept_rate | test_net_expectancy_bps_if_trading_kept_signals | test_win_rate_if_trading_kept_signals | test_profit_factor_if_trading_kept_signals | baseline_no_gate_test_net_expectancy_bps | delta_vs_baseline_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| walk_forward_3 | 2025 | logistic_regression_l2 | model_execution_completed | false | 0.650000 | 13 | 2 | 0.866667 | -155.800103 | 0.230769 | 0.088704 | -151.297784 | -4.502319 |
| walk_forward_3 | 2025 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 14 | 1 | 0.933333 | -144.965558 | 0.285714 | 0.102601 | -151.297784 | 6.332226 |
| walk_forward_3 | 2025 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 14 | 1 | 0.933333 | -144.965558 | 0.285714 | 0.102601 | -151.297784 | 6.332226 |
| walk_forward_4 | 2026 | logistic_regression_l2 | model_execution_completed | false | 0.700000 | 3 | 5 | 0.375000 | -22.622541 | 0.666667 | 0.682204 | -18.261942 | -4.360599 |
| walk_forward_4 | 2026 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 8 | 0 | 1.000000 | -18.261942 | 0.625000 | 0.806865 | -18.261942 | 0.000000 |
| walk_forward_4 | 2026 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 7 | 1 | 0.875000 | 9.637375 | 0.714286 | 1.124265 | -18.261942 | 27.899317 |

| year | trade_count | net_expectancy_bps | win_rate | profit_factor | label_bad_context_36_rate | label_trade_win_rate | label_positive_tail_rate | label_negative_tail_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 | 16 | -160.751555 | 0.250000 | 0.082751 | 0.750000 | 0.250000 | 0.000000 | 0.500000 |
| 2026 | 9 | -16.282152 | 0.555556 | 0.806392 | 0.222222 | 0.555556 | 0.000000 | 0.222222 |

## Baseline Comparison

- Overall `baseline_no_gate` expectancy: `44.003106` bps
- Overall `baseline_no_gate` win rate: `0.567742`
- Overall `baseline_no_gate` profit factor: `1.674411`

| split | test_year | test_count | baseline_no_gate_test_net_expectancy_bps | baseline_no_gate_test_win_rate | baseline_no_gate_test_profit_factor |
| --- | --- | --- | --- | --- | --- |
| walk_forward_1 | 2023 | 72 | -1.316009 | 0.513889 | 0.965460 |
| walk_forward_2 | 2024 | 25 | 108.461973 | 0.680000 | 2.541552 |
| walk_forward_3 | 2025 | 15 | -151.297784 | 0.266667 | 0.092759 |
| walk_forward_4 | 2026 | 8 | -18.261942 | 0.625000 | 0.806865 |

## Interpretation

1. Does any baseline model improve test-period expectancy versus no-gate baseline? Yes. Best fold/model: `walk_forward_4 / decision_tree_depth_3` with delta `27.899317` bps.
2. Does any model improve 2025 and 2026 separately? Yes. 2025 improvement: `true`; 2026 improvement: `true`. best 2025 fold `decision_tree_depth_2` kept `14` trades and stayed negative at `-144.965558` bps. best 2026 fold `decision_tree_depth_3` kept `7` trades and reached `9.637375` bps.
3. Does any model preserve at least 10 trades in recent test windows? Partially. The 2025 model folds preserve at least 10 kept trades, but the 2026 baseline test window itself has only 8 trades, so 2026 is sample-too-small for standalone approval.
4. Does any model show stable validation-to-test behavior? Yes. Validation is time-ordered, but recent folds remain sparse.
5. Is there enough evidence to approve a production filter? No. This baseline can only determine whether meta-labeling is worth deeper research.

## What Is Still Valid

- The canonical C_ExhaustionFade replay anchor remains valid as a research dataset.
- The ex-ante feature set and label definitions are usable for a later model task.
- The purged walk-forward scaffolding is ready for a future evaluation run.

## What Is Not Valid

- Model execution completed, but no model is approved.
- No production or paper-trading rule has been approved.
- The 2026 improvement is sample-too-small for standalone approval.
- The 2025 improvement is small and remains negative in absolute expectancy.
- Stable validation-to-test robustness is not proven.

## Decision

Decision label: `meta_labeling_worth_deeper_research`.
Meta-labeling remains worth deeper research because the bounded baseline models improved some recent fold results versus no-gate baseline. However, this is not enough for production or paper approval because 2026 is sample-too-small, 2025 remains negative after filtering, and no PSR/DSR/PBO or candidate-selection protocol has been run.

## Required Next Step

Extend the current walk-forward meta-label baseline with more recent held-out data and compare against `baseline_no_gate` and the best simple ex-ante proxy gate.
Do not promote any model without a separate candidate-selection and PSR/DSR/PBO process.

## Model Execution Notes

- Model execution status: `evaluated`
- Purged walk-forward folds built: `4`
- Thresholds are selected on validation only when model execution is available.
- Test labels are never used for threshold selection.
