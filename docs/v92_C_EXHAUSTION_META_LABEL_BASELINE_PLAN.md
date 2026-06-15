# C_ExhaustionFade Meta-Label Baseline Plan

## Purpose

Define a strictly ex-ante meta-label baseline for C_ExhaustionFade so future research can predict bad-context trades without leaking post-signal information.

This is a plan only. No model is trained, no gate is selected, and no production or paper-trading approval is granted.

## Why Meta-Labeling Is the Only Remaining C Path

The repaired replay, the fixed-exit diagnostics, the regime/context audit, the exit-hypothesis matrix, and the ex-ante proxy matrix all converged on the same conclusion: simple rule gates do not rescue the recent-period decay. A meta-label baseline is the only remaining path that can still use the canonical entries while learning to avoid the bad contexts ex-ante.

## Data Sources

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay context: existing C_ExhaustionFade replay helpers and regime labels

## Candidate Labels

| label | definition | positive_count | positive_rate |
| --- | --- | --- | --- |
| label_trade_win | net_return_bps > 0 | 176 | 0.567741935483871 |
| label_positive_tail | net_return_bps >= 200 | 60 | 0.1935483870967742 |
| label_negative_tail | net_return_bps <= -200 | 40 | 0.12903225806451613 |
| label_bad_context_36 | trend_continuation_flag_36 OR failed_reversal_flag_36 | 100 | 0.3225806451612903 |
| label_recent_decay | year >= 2025 | 25 | 0.08064516129032258 |

## Allowed Ex-Ante Features

| feature | class | available | null_count |
| --- | --- | --- | --- |
| pre_signal_return_12_bars_bps | allowed_ex_ante | true | 0 |
| pre_signal_return_24_bars_bps | allowed_ex_ante | true | 0 |
| pre_signal_return_36_bars_bps | allowed_ex_ante | true | 0 |
| realized_vol_12_bars_bps | allowed_ex_ante | true | 0 |
| realized_vol_24_bars_bps | allowed_ex_ante | true | 0 |
| realized_vol_36_bars_bps | allowed_ex_ante | true | 0 |
| range_expansion_ratio_12 | allowed_ex_ante | true | 0 |
| range_expansion_ratio_24 | allowed_ex_ante | true | 0 |
| range_expansion_ratio_36 | allowed_ex_ante | true | 0 |
| body_to_range_ratio | allowed_ex_ante | true | 0 |
| volume_over_vol95_ratio | allowed_ex_ante | true | 0 |
| close_vs_local_low_bps | allowed_ex_ante | true | 0 |
| adr_stretch | allowed_ex_ante | true | 0 |
| rv_1d | allowed_ex_ante | true | 0 |
| rv_15th_pct | allowed_ex_ante | true | 13 |
| bar_range | allowed_ex_ante | true | 0 |
| body_size | allowed_ex_ante | true | 0 |
| volume | allowed_ex_ante | true | 0 |
| vol_roll_95 | allowed_ex_ante | true | 0 |

## Forbidden Features / Leakage Guardrails

The following are forbidden as model inputs:
- `net_return_bps`
- `gross_return_bps`
- `exit_time`
- `exit_price`
- `mfe_bps`
- `mae_bps`
- `post_signal_return_*`
- `trend_continuation_flag_*`
- `failed_reversal_flag_*`
- `anything computed after signal_time`

## Time-Ordered Validation Design

Validation must be time-ordered only, with purged walk-forward splits and embargo. No random split, no shuffle split, and no same-period tuning.

| split | train | validate | test |
| --- | --- | --- | --- |
| walk_forward_1 | 2020-2021 | 2022 | 2023 |
| walk_forward_2 | 2020-2022 | 2023 | 2024 |
| walk_forward_3 | 2020-2023 | 2024 | 2025 |
| walk_forward_4 | 2020-2024 | 2025 | 2026 |

- purge window = 48 bars
- embargo window = 48 bars
- no random split
- no shuffle split
- no same-period tuning

## Baseline Models For Later Evaluation

- `logistic_regression_l1`
- `logistic_regression_l2`
- `decision_tree_depth_2`
- `decision_tree_depth_3`
- `calibrated_gradient_boosting_small`

## Acceptance Criteria

A future model is not useful unless it improves recent-period net expectancy after costs without destroying early/middle validation.
A future model must beat `baseline_no_gate` and the best simple ex-ante proxy gate.
A future model must pass PSR/DSR/PBO checks before being considered a serious research candidate.
A future model must report calibration and confusion matrix by period.
A future model must preserve minimum recent test sample count >= 10.
A model cannot be promoted from this task.

## Failure Criteria

- The model leaks post-signal information.
- The model fails to beat the canonical baseline and the best simple ex-ante proxy gate.
- The model degrades early or middle validation materially.
- The model cannot keep recent test sample count above the minimum threshold.
- The model is not calibrated or cannot be summarized by period.

## Decision Boundary

If the meta-label baseline does not improve recent-period performance with clean leakage controls, C_ExhaustionFade should be archived as a historical research anchor while infrastructure work moves to OFI/CVD.

## Required Next Step

Implement the first meta-label baseline exactly as planned, then evaluate it with the time-ordered validation design and the acceptance criteria above.

## Feature / Label Manifest

- Context rows evaluated: `310`
- Missing requested features in the current context builder: `none`

Sample context rows:

| signal_time | entry_time | exit_time | year | net_return_bps | trend_continuation_flag_36 | failed_reversal_flag_36 | bad_context_label_36 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-09-02 11:09:58.270000 | 2020-09-02 11:09:58.270000 | 2020-09-02 14:59:44.128000 | 2020 | -181.4820317539225 | true | true | true |
| 2020-09-03 12:12:13.881000 | 2020-09-03 12:12:13.885000 | 2020-09-03 14:47:39.954000 | 2020 | -71.780469272106 | true | true | true |
| 2020-09-05 18:54:55.943000 | 2020-09-05 18:54:55.943000 | 2020-09-06 01:57:21.331000 | 2020 | 267.02157571817463 | false | false | false |
| 2020-09-17 10:27:26.646000 | 2020-09-17 10:27:26.703000 | 2020-09-17 21:08:45.198000 | 2020 | 105.6176916534155 | false | false | false |
| 2020-09-23 20:48:29.709000 | 2020-09-23 20:48:29.709000 | 2020-09-24 11:05:20.397000 | 2020 | 201.9351671845935 | false | false | false |
