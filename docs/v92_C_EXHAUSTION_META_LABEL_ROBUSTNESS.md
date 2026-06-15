# C_ExhaustionFade Meta-Label Robustness Scaffold

## Purpose

Assess whether the observed meta-label improvement is robust enough to justify deeper research.

This task does not approve a production model, production gate, paper-trading rule, or live-trading rule.

## Research-Only Guardrails

- Candidate universe is frozen to the baseline models already evaluated.
- No new models, features, labels, thresholds, or walk-forward splits were introduced.
- No production approval.

## Inputs

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Baseline results doc: `docs/v92_C_EXHAUSTION_META_LABEL_BASELINE_RESULTS.md`

## Candidate Universe

- `baseline_no_gate`
- `logistic_regression_l2`
- `decision_tree_depth_2`
- `decision_tree_depth_3`

## Candidate-Selection Protocol

A model is only a serious research candidate if all are true:

1. Mean test delta_vs_baseline_bps across walk-forward folds > 0
2. Median test delta_vs_baseline_bps across folds > 0
3. 2025 test delta_vs_baseline_bps > 0
4. 2026 test delta_vs_baseline_bps > 0
5. 2025 test_net_expectancy_bps_if_trading_kept_signals > baseline_2025
6. 2026 test_net_expectancy_bps_if_trading_kept_signals > baseline_2026
7. Total kept recent trades across 2025 and 2026 >= 10
8. No test fold has kept_trade_count < 5 unless baseline test_count itself is < 10

## Fold-Level Model Summary

| split | validate_year | test_year | model_family | model_status | validation_sample_too_small | selected_threshold | train_count | validate_count | test_count | test_kept_trade_count | test_removed_trade_count | test_kept_rate | test_net_expectancy_bps_if_trading_kept_signals | baseline_no_gate_test_net_expectancy_bps | delta_vs_baseline_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| walk_forward_1 | 2022 | 2023 | logistic_regression_l2 | model_execution_completed | false | 0.600000 | 103 | 82 | 72 | 68 | 4 | 0.944444 | 1.202139 | -1.316009 | 2.518147 |
| walk_forward_1 | 2022 | 2023 | decision_tree_depth_2 | model_execution_completed | false | 0.700000 | 103 | 82 | 72 | 65 | 7 | 0.902778 | -8.690700 | -1.316009 | -7.374692 |
| walk_forward_1 | 2022 | 2023 | decision_tree_depth_3 | model_execution_completed | false | 0.700000 | 103 | 82 | 72 | 9 | 63 | 0.125000 | -41.073572 | -1.316009 | -39.757563 |
| walk_forward_2 | 2023 | 2024 | logistic_regression_l2 | model_execution_completed | false | 0.650000 | 186 | 72 | 25 | 20 | 5 | 0.800000 | 115.205125 | 108.461973 | 6.743152 |
| walk_forward_2 | 2023 | 2024 | decision_tree_depth_2 | model_execution_completed | false | 0.400000 | 186 | 72 | 25 | 25 | 0 | 1.000000 | 108.461973 | 108.461973 | 0.000000 |
| walk_forward_2 | 2023 | 2024 | decision_tree_depth_3 | model_execution_completed | false | 0.300000 | 186 | 72 | 25 | 25 | 0 | 1.000000 | 108.461973 | 108.461973 | 0.000000 |
| walk_forward_3 | 2024 | 2025 | logistic_regression_l2 | model_execution_completed | false | 0.650000 | 259 | 25 | 15 | 13 | 2 | 0.866667 | -155.800103 | -151.297784 | -4.502319 |
| walk_forward_3 | 2024 | 2025 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 259 | 25 | 15 | 14 | 1 | 0.933333 | -144.965558 | -151.297784 | 6.332226 |
| walk_forward_3 | 2024 | 2025 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 259 | 25 | 15 | 14 | 1 | 0.933333 | -144.965558 | -151.297784 | 6.332226 |
| walk_forward_4 | 2025 | 2026 | logistic_regression_l2 | model_execution_completed | false | 0.700000 | 285 | 15 | 8 | 3 | 5 | 0.375000 | -22.622541 | -18.261942 | -4.360599 |
| walk_forward_4 | 2025 | 2026 | decision_tree_depth_2 | model_execution_completed | false | 0.550000 | 285 | 15 | 8 | 8 | 0 | 1.000000 | -18.261942 | -18.261942 | 0.000000 |
| walk_forward_4 | 2025 | 2026 | decision_tree_depth_3 | model_execution_completed | false | 0.550000 | 285 | 15 | 8 | 7 | 1 | 0.875000 | 9.637375 | -18.261942 | 27.899317 |

## Candidate Stability Summary

| model_family | fold_count | mean_test_delta_bps | median_test_delta_bps | min_test_delta_bps | max_test_delta_bps | positive_delta_fold_count | negative_delta_fold_count | recent_2025_delta_bps | recent_2026_delta_bps | recent_total_kept_trades | recent_total_removed_trades | recent_kept_rate | mean_test_expectancy_bps | median_test_expectancy_bps | mean_baseline_expectancy_bps | median_baseline_expectancy_bps | passes_candidate_selection_protocol | sample_too_small | unstable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression_l2 | 4 | 0.099595 | -0.921226 | -4.502319 | 6.743152 | 2 | 2 | -4.502319 | -4.360599 | 16 | 7 | 0.695652 | -15.503845 | -10.710201 | -15.603441 | -9.788975 | false | true | false |
| decision_tree_depth_2 | 4 | -0.260616 | 0.000000 | -7.374692 | 6.332226 | 1 | 1 | 6.332226 | 0.000000 | 22 | 1 | 0.956522 | -15.864057 | -13.476321 | -15.603441 | -9.788975 | false | true | true |
| decision_tree_depth_3 | 4 | -1.381505 | 3.166113 | -39.757563 | 27.899317 | 2 | 1 | 6.332226 | 27.899317 | 21 | 2 | 0.913043 | -16.984946 | -15.718098 | -15.603441 | -9.788975 | false | true | false |

## Recent-Year Summary

| test_year | test_count | baseline_no_gate_test_net_expectancy_bps | baseline_no_gate_test_win_rate | baseline_no_gate_test_profit_factor |
| --- | --- | --- | --- | --- |
| 2023 | 72 | -1.316009 | 0.513889 | 0.965460 |
| 2024 | 25 | 108.461973 | 0.680000 | 2.541552 |
| 2025 | 15 | -151.297784 | 0.266667 | 0.092759 |
| 2026 | 8 | -18.261942 | 0.625000 | 0.806865 |

## PSR Scaffold

| candidate | trade_count | mean_bps | std_bps | trade_sharpe | skew | kurtosis | psr_vs_zero | psr_unreliable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression_l2 | 104 | 2.813259 | 180.324429 | 0.015601 | 0.751497 | 5.346255 | 0.563264 | false |
| decision_tree_depth_2 | 112 | -0.258567 | 188.755098 | -0.001370 | 0.499650 | 4.909191 | 0.494245 | false |
| decision_tree_depth_3 | 55 | 6.906018 | 251.176110 | 0.027495 | 0.400991 | 3.107442 | 0.580482 | false |

## DSR Scaffold

- model families: `3`
- threshold candidates: `9`
- number_of_trials: `27`
- dsr_scaffold_only: `true`
- dsr_penalty_note: `DSR requires a fuller multiple-testing implementation; this scaffold records candidate count and PSR only.`

## PBO Scaffold

| split | validation_best_model | validation_best_validate_rank | validation_best_test_rank | below_median_on_test |
| --- | --- | --- | --- | --- |
| walk_forward_1 | decision_tree_depth_3 | 1 | 3 | true |
| walk_forward_2 | logistic_regression_l2 | 1 | 1 | false |
| walk_forward_3 | decision_tree_depth_2 | 1 | 2 | true |
| walk_forward_4 | logistic_regression_l2 | 1 | 3 | true |

- pbo_fold_count: `4`
- pbo_bad_fold_count: `3`
- pbo_rate: `0.750000`
- pbo_low_power: `true`

## Interpretation

1. Does any model pass the candidate-selection protocol? No.
2. Is the 2026 improvement sufficient for standalone approval? No. The 2026 fold has only 8 baseline trades, so the strongest 2026 lift remains sample-too-small for standalone approval.
3. Does PSR provide strong evidence after sample-size caveats? No. The scaffold records PSR, but it is descriptive only and does not override the recent sample-size caveats.
4. Does DSR provide strong evidence after multiple-testing caveats? No. DSR remains a scaffold only with `number_of_trials = 27`.
5. Does PBO indicate severe overfitting risk? Inconclusive / low power. The fold count is small, so the PBO estimate has low power.
6. Is there enough evidence to approve a production or paper filter? No.

## What Is Still Valid

- The canonical C_ExhaustionFade replay anchor remains valid as a research dataset.
- The meta-label baseline results remain useful as a bounded research signal.
- The candidate-selection and robustness scaffolding is now documented and testable.

## What Is Not Valid

- Model execution completed, but no model is approved.
- No production or paper filter is approved.
- No live-trading rule is approved.
- No candidate-selection result should be treated as a final endorsement.
- The 2026 improvement is sample-too-small for standalone approval.
- The 2025 improvement is small and remains negative in absolute expectancy.
- Stable validation-to-test robustness is not proven.
- DSR is not fully implemented; it is a scaffold only.

## Decision

Decision label: `archive_C_recommended`.
No model passed the candidate-selection protocol. Archive C as a historical anchor unless stronger ex-ante features are introduced.
Production status: `production_invalid`.
Paper/live status: `paper_live_blocked`.

## Required Next Step

Use this scaffold to decide whether the next research step is stronger ex-ante features or a larger holdout. Do not approve production, paper trading, or live trading until a separate candidate-selection and PSR/DSR/PBO process is completed.

## Robustness Notes

- Candidate-selection protocol and robustness metrics are frozen to the already-evaluated meta-label baseline.
- PBO is low-power by construction here because only four walk-forward folds and three candidate models are available.
- DSR is explicitly a scaffold; it records the multiple-testing burden without claiming certainty.
