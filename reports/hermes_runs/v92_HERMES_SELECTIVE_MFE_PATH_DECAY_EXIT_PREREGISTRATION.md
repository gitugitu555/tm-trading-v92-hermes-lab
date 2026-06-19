# V9.2 Hermes Selective MFE Path Decay Exit Preregistration

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
* average delta bps per trade
* median delta bps per trade
* clean-winner clipping cost
* giveback-loss rescue benefit
* false-positive ratio
* rescue-to-clipping ratio
* by-year breakdown
* recent-period breakdown if prior reports define the recent decay period
* synthetic causality checks

## Required Synthetic Causality Checks

The future experiment must show that:

* trigger formation uses only running MFE available up to trigger
* current return at trigger uses only trigger-time information
* original exit result is not used to decide trigger eligibility
* no future return path after trigger is used as an input
* class labels are used only for aggregate post-hoc diagnostics

## Hard Pass/Fail Conditions

The selective rule may only proceed to core patch design review if all are true:

* aggregate delta bps is positive
* clean-winner clipping cost is materially lower than the rejected fixed rule
* rescue-to-clipping ratio is better than the rejected fixed rule
* benefit is not isolated to a single year only
* synthetic causality checks pass
* no future information is used in rule eligibility
* no row-level artifacts are written

The rule must be rejected if:

* aggregate delta bps remains negative
* clean-winner clipping remains the dominant effect
* benefit comes only from one isolated year
* causality checks fail
* required fields are missing

## Required Stop / Go Criteria

Choose exact label:

`keep_selective_exit_hypothesis_alive_but_do_not_patch`

Rationale:

The existing evidence is not strong enough to approve a patch now, but it is strong enough to keep the hypothesis alive and to justify a design-only selective-exit follow-up using the fixed candidate rule above.

## Conclusion

This preregistration defines one narrow, trigger-time selective-exit candidate and constrains the future work to aggregate-only diagnostics. It does not approve trading, does not implement a rule, and does not relax the rejection of the blunt fixed giveback rule.
