# V9.2 Hermes Selective MFE Path Decay Exit Experiment

## Background

* The fixed running-MFE giveback protection rule was rejected as net destructive.
* The full-sample fixed-rule net delta was negative.
* The clean-winner clipping cost exceeded the giveback-loss rescue benefit.
* The MFE path selectivity diagnostic found weak but measurable separation.
* The triggered rescued giveback-loss and triggered clipped clean-winner distributions overlap materially.
* The next step is therefore a conservative design-only preregistration, not a rule patch.

## Binding Hypothesis

A selective exit rule using only trigger-time path-state fields can reduce giveback-loss damage without materially clipping clean winners, but only if eligibility is narrowed beyond the rejected blunt fixed giveback trigger.

## Fixed Candidate Rule

Proposed fixed selective candidate rule name:

`selective_mfe_path_decay_exit_experiment`

This is one fixed candidate rule only. No variants.

Retained activation structure:

* Activation remains `running_mfe_bps >= 75 bps`
* Minimum delay remains `12` completed 750btc bars
* Review remains at completed 750btc bar close
* Long-only unless side is safely available

Selective eligibility gates, added only after activation:

| Gate | Field | Fixed preregistered value |
| --- | --- | --- |
| 1 | `current_return_at_trigger_bps` | `<= 0 bps` |
| 2 | `giveback_depth_at_trigger_bps` | `>= 150 bps` |
| 3 | `trigger_offset_bars` | `<= 15 bars` |

Candidate rule definition:

* If activation conditions are met and all three eligibility gates are true, the selective exit is eligible for consideration.
* If any eligibility gate fails, the trade remains under the original fixed-horizon handling.
* `running_mfe_at_trigger_bps` is retained as a diagnostic and comparison field, not as an additional eligibility gate.

This candidate uses only fields identified by the selectivity diagnostic as the strongest separators:

* `current_return_at_trigger_bps`
* `giveback_depth_at_trigger_bps`
* `running_mfe_at_trigger_bps`
* `trigger_offset_bars`

Only three additional eligibility gates are added.

## Required Caution

This preregistration is high risk.

The selectivity diagnostic showed only weak separability, so the experiment is expected to fail unless false-positive clean-winner clipping is materially reduced. The purpose of this preregistration is to test whether a narrow trigger-time path-state filter can preserve the giveback-loss rescue signal while removing the dominant clean-winner damage.

## Forbidden Actions

* No parameter search
* No threshold search
* No alternative rules
* No multiple variants
* No ML classifier training
* No regime optimization
* No use of future path information after trigger
* No raw L2 reads
* No OFI generation
* No row-level artifact exports
* No core repo modification
* No paper/live/production approval

## Allowed Inputs

Allowed trigger-time or pre-trigger fields only:

* `running_mfe_at_trigger_bps`
* `current_return_at_trigger_bps`
* `giveback_depth_at_trigger_bps`
* `trigger_offset_bars`
* `activation_offset_bars` if already available
* `delay_activation_to_trigger_bars` if already available
* original class labels only for aggregate post-hoc diagnostics
* original realized return only for aggregate post-hoc diagnostics
* mechanical selective-exit return only for aggregate post-hoc diagnostics

## Required Aggregate Outputs For The Future Experiment

The future experiment must report:

* total trades inspected
* activated trades
* blunt fixed-rule triggered trades
* selective-rule eligible trades
* giveback-loss rescue count
* clean-winner clipped count
* weak-positive clipped/protected count
* aggregate original return
* aggregate selective mechanical return
* aggregate delta bps
* average delta bps per inspected trade
* average delta bps per selective eligible trade
* median delta bps per selective eligible trade
* clean-winner clipping cost
* giveback-loss rescue benefit
* false-positive ratio
* rescue-to-clipping ratio
* by-year breakdown
* recent-period breakdown if prior reports define the recent decay period
* synthetic causality checks

## Population Accounting

| category | count |
| --- | --- |
| total_inspected | 310 |
| activated_trades | 211 |
| blunt_fixed_rule_triggered_trades | 166 |
| selective_rule_eligible_trades | 28 |
| giveback_loss_rescue_count | 17 |
| clean_winner_clipped_count | 6 |
| weak_positive_clipped_protected_count | 5 |
| other_uncategorized_count | 0 |

## Economic Attribution

- aggregate original return bps: `17360.963`
- aggregate selective mechanical return bps: `14219.779`
- gross delta bps: `-3141.184`
- aggregate original net return bps: `13640.963`
- aggregate selective mechanical net return bps: `10499.779`
- net delta bps: `-3141.184`
- average delta bps per inspected trade: `-10.133`
- average delta bps per selective eligible trade: `-112.185`
- median delta bps per selective eligible trade: `-77.169`
- gross and net deltas available: `yes`

## False-Positive Accounting

- clean-winner clipped count: `6`
- clean-winner aggregate original return: `1649.190`
- clean-winner aggregate selective mechanical return: `-627.764`
- clean-winner clipping cost bps: `-2276.954`
- average clipping cost per clipped clean winner: `-379.492`
- median clipping cost: `-320.958`
- false-positive ratio (clipped / rescued): `0.353`

## Rescue Accounting

- giveback-loss rescued count: `17`
- giveback-loss aggregate original return: `-2534.257`
- giveback-loss aggregate selective mechanical return: `-2448.853`
- giveback-loss rescue benefit bps: `85.404`
- average rescue benefit per rescued trade: `5.024`
- median rescue benefit: `-4.398`
- rescue-to-clipping ratio (rescued / clipped): `2.833`

## Comparison Against Rejected Fixed Rule

- rejected fixed-rule full-sample net delta: `-6450.394 bps`
- rejected fixed-rule clean-winner clipping cost: `-12394.355 bps`
- rejected fixed-rule giveback-loss rescue benefit: `5986.279 bps`
- selective rule improves aggregate delta: `false`
- selective rule reduces clean-winner clipping cost: `true`
- selective rule improves rescue-to-clipping ratio: `true`
- selective rule avoids single-year concentration: `true`

## Trigger-Time Field Comparison

| field | rescued_count | rescued_mean | rescued_median | rescued_p25 | rescued_p75 | rescued_min | rescued_max | clipped_count | clipped_mean | clipped_median | clipped_p25 | clipped_p75 | clipped_min | clipped_max | mean_diff | median_diff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| activation_offset_bars | 17 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 6 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 0.000 | 0.000 |
| trigger_offset_bars | 17 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 6 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 12.000 | 0.000 | 0.000 |
| delay_activation_to_trigger_bars | 17 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| running_mfe_at_trigger_bps | 17 | 123.711 | 110.873 | 86.434 | 145.955 | 76.207 | 275.311 | 6 | 213.799 | 233.219 | 124.425 | 255.780 | 81.081 | 383.813 | -90.088 | -122.346 |
| current_return_at_trigger_bps | 17 | -144.050 | -132.533 | -157.782 | -116.669 | -338.956 | -53.772 | 6 | -104.627 | -73.177 | -136.150 | -59.924 | -252.808 | -15.955 | -39.423 | -59.357 |
| giveback_depth_at_trigger_bps | 17 | 267.761 | 231.577 | 224.177 | 294.311 | 161.154 | 484.400 | 6 | 318.426 | 283.833 | 243.102 | 311.421 | 156.128 | 636.621 | -50.665 | -52.257 |
| original_realized_return_bps | 17 | -149.074 | -100.875 | -208.995 | -59.780 | -497.661 | -18.000 | 6 | 274.865 | 255.732 | 215.290 | 294.137 | 115.465 | 513.514 | -423.939 | -356.607 |
| mechanical_selective_return_bps | 17 | -144.050 | -132.533 | -157.782 | -116.669 | -338.956 | -53.772 | 6 | -104.627 | -73.177 | -136.150 | -59.924 | -252.808 | -15.955 | -39.423 | -59.357 |
| selective_delta_bps | 17 | 5.024 | -4.398 | -73.403 | 49.877 | -185.640 | 258.077 | 6 | -379.492 | -320.958 | -459.363 | -276.873 | -666.622 | -200.740 | 384.516 | 316.560 |

## By-Year Breakdown

| year | selective_eligible_trades | rescued_giveback_losses | clean_winner_clips | weak_positive_clipped_or_protected | mean_trigger_offset_bars | mean_current_return_at_trigger_bps | mean_giveback_depth_bps | mean_selective_delta_bps | mean_selective_net_delta_bps | rescue_benefit_bps | clipping_cost_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 1 | 1 | 0 | 0 | 12.000 | -132.533 | 285.143 | -72.753 | -72.753 | -72.753 | 0.000 |
| 2021 | 15 | 6 | 6 | 3 | 12.000 | -119.055 | 291.603 | -221.208 | -221.208 | -282.194 | -2276.954 |
| 2022 | 7 | 6 | 0 | 1 | 12.000 | -150.101 | 280.063 | 34.023 | 34.023 | 359.485 | 0.000 |
| 2023 | 1 | 1 | 0 | 0 | 12.000 | -120.591 | 207.024 | -80.935 | -80.935 | -80.935 | 0.000 |
| 2024 | 3 | 3 | 0 | 0 | 12.000 | -118.770 | 217.329 | 53.934 | 53.934 | 161.801 | 0.000 |
| 2025 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | 0.000 | 0.000 |
| 2026 | 1 | 0 | 0 | 1 | 12.000 | -57.781 | 155.577 | -69.337 | -69.337 | 0.000 | 0.000 |

## Recent-Period Breakdown

| period | selective_eligible_trades | rescued_giveback_losses | clean_winner_clips | weak_positive_clipped_or_protected | mean_trigger_offset_bars | mean_current_return_at_trigger_bps | mean_giveback_depth_bps | aggregate_delta_bps | rescue_benefit_bps | clipping_cost_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| historical | 27 | 17 | 6 | 4 | 12.000 | -127.628 | 276.987 | -3071.847 | 85.404 | -2276.954 |
| recent_decay | 1 | 0 | 0 | 1 | 12.000 | -57.781 | 155.577 | -69.337 | 0.000 | 0.000 |

## Synthetic Causality Checks

- future-bars-do-not-change-eligibility: `passed` (baseline_eligible=False, future_eligible=False)
- original-exit-labels-do-not-decide-eligibility: `passed` (eligibility stayed fixed after mutating original exit fields)
- trigger-time-fields-drive-eligibility: `passed` (current_return=349.9999999999992, giveback_depth=850.0000000000019, trigger_offset=12.0)

## Interpretation

A. Does the selective rule improve aggregate delta?

false. The selected rule's aggregate delta is `-3141.184` bps.

B. Does it reduce clean-winner clipping cost?

true. Clean-winner clipping cost is `-2276.954` bps versus the rejected fixed rule's `-12,394.355 bps`.

C. Does it improve rescue-to-clipping ratio?

true. The observed count ratio is `2.833` versus the rejected fixed rule's `0.605`.

D. Does it avoid single-year concentration?

true. The benefit is spread across multiple years, but the recent-period contribution remains important.

## Stop / Go Conclusion

- decision: `reject_selective_mfe_path_decay_exit_rule`

