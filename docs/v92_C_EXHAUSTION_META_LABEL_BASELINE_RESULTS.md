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

- `sklearn_available`: `false`
- Model execution is blocked in this environment because `sklearn` is not installed.
- `logistic_regression_l2`
- `decision_tree_depth_2`
- `decision_tree_depth_3`

## Fold Results

| split | model_family | model_status | train_count | validate_count | test_count | selected_threshold | validate_precision | validate_recall | validate_f1 | test_precision | test_recall | test_f1 | test_accuracy | test_auc_if_available | test_kept_trade_count | test_removed_trade_count | test_kept_rate | test_net_expectancy_bps_if_trading_kept_signals | test_win_rate_if_trading_kept_signals | test_profit_factor_if_trading_kept_signals | baseline_no_gate_test_net_expectancy_bps | delta_vs_baseline_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| walk_forward_1 | logistic_regression_l2 | blocked_missing_sklearn | 103 | 82 | 72 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -1.316009 | n/a |
| walk_forward_1 | decision_tree_depth_2 | blocked_missing_sklearn | 103 | 82 | 72 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -1.316009 | n/a |
| walk_forward_1 | decision_tree_depth_3 | blocked_missing_sklearn | 103 | 82 | 72 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -1.316009 | n/a |
| walk_forward_2 | logistic_regression_l2 | blocked_missing_sklearn | 186 | 72 | 25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 108.461973 | n/a |
| walk_forward_2 | decision_tree_depth_2 | blocked_missing_sklearn | 186 | 72 | 25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 108.461973 | n/a |
| walk_forward_2 | decision_tree_depth_3 | blocked_missing_sklearn | 186 | 72 | 25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 108.461973 | n/a |
| walk_forward_3 | logistic_regression_l2 | blocked_missing_sklearn | 259 | 25 | 15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -151.297784 | n/a |
| walk_forward_3 | decision_tree_depth_2 | blocked_missing_sklearn | 259 | 25 | 15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -151.297784 | n/a |
| walk_forward_3 | decision_tree_depth_3 | blocked_missing_sklearn | 259 | 25 | 15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -151.297784 | n/a |
| walk_forward_4 | logistic_regression_l2 | blocked_missing_sklearn | 285 | 15 | 8 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -18.261942 | n/a |
| walk_forward_4 | decision_tree_depth_2 | blocked_missing_sklearn | 285 | 15 | 8 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -18.261942 | n/a |
| walk_forward_4 | decision_tree_depth_3 | blocked_missing_sklearn | 285 | 15 | 8 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | -18.261942 | n/a |

## Recent-Period Results

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

1. Does any baseline model improve test-period expectancy versus no-gate baseline? No model was executed in this environment because `sklearn` is unavailable, so no improvement is demonstrated.
2. Does any model improve 2025 and 2026 separately? No model was executed, so there is no improvement evidence for either year.
3. Does any model preserve at least 10 trades in recent test windows? The test windows are sized, but model preservation cannot be assessed until model execution is unblocked.
4. Does any model show stable validation-to-test behavior? No model results are available in this environment, so stability cannot be claimed.
5. Is there enough evidence to approve a production filter? No. This baseline can only determine whether meta-labeling is worth deeper research.

## What Is Still Valid

- The canonical C_ExhaustionFade replay anchor remains valid as a research dataset.
- The ex-ante feature set and label definitions are usable for a later model task.
- The purged walk-forward scaffolding is ready for a future evaluation run.

## What Is Not Valid

- No model has been approved.
- No production or paper-trading rule has been approved.
- No improvement claim can be made from this blocked environment.

## Decision

The task establishes the baseline dataset and evaluation protocol, but model results remain blocked until `sklearn` is available in the execution environment.

## Required Next Step

Run the same dataset and evaluator on an environment with `sklearn` installed, then compare validation-selected thresholds and test metrics against `baseline_no_gate` and the best simple ex-ante proxy gate.

## Model Execution Notes

- Model execution status: `blocked_missing_sklearn`
- Purged walk-forward folds built: `4`
- Thresholds are selected on validation only when model execution is available.
- Test labels are never used for threshold selection.
