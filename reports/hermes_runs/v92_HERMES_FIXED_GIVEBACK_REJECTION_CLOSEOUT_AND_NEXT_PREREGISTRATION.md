# V9.2 Hermes Fixed Giveback Rejection Closeout and Next Preregistration

## Final Rejection Summary

Fixed rule name:

`fixed_running_mfe_giveback_protection_experiment`

Original preregistered parameters:

* Activation threshold: `running_mfe_bps >= 75 bps`
* Giveback trigger: `current_return_bps <= 0.50 * running_mfe_bps`
* Minimum bars after entry before trigger is allowed: `12` completed 750btc bars
* Review frequency: once per completed 750btc bar
* Price basis: bar close
* Direction assumption: long-only unless side column is safely available
* No parameter search
* No threshold tuning
* No alternative exits
* No holdout optimization
* No strategy patch
* No production approval

Final reviewed decision:

`reject_fixed_giveback_rule_as_net_destructive`

Economic outcome:

* Full-sample net bps delta: `-6,450.394 bps`
* Clean-winner clipping cost: `-12,394.355 bps`
* Giveback-loss rescue benefit: `+5,986.279 bps`

Why the rule is rejected:

The rule does rescue some giveback losses, but it clips too many profitable trades. The clean-winner clipping cost is larger than the giveback-loss rescue benefit by `6,408.076 bps`, so the aggregate effect is economically destructive rather than accretive.

## False-Positive Explanation

Triggering on `76 / 130` original clean winners invalidates direct implementation because the rule is not selective enough. More than half of the clean winners are forced into earlier exits, which converts durable positive expectancy into truncated positive expectancy.

That is the core failure mode:

* The rule is not simply catching pathological giveback losses.
* It is also interfering with a large block of trades that were already behaving well.
* The false-positive rate on clean winners is high enough that the rescue from losing trades does not compensate.

Direct implementation would therefore trade away more high-quality continuation than it saves from decay.

## Preserved Hypothesis

The exit-horizon mismatch hypothesis remains partially alive.

The rejected conclusion is specific to the blunt fixed giveback protection rule, not to every possible exit-horizon refinement. The next step should focus on selectivity, not threshold tuning.

What is preserved:

* Exit-horizon mismatch remains a live explanation for part of the loss profile.
* The fixed blunt giveback protection rule is rejected.
* Future work must discriminate between rescueable giveback losses and clean winners before any execution rule is considered.

## Next Experiment Preregistration Design Only

Proposed experiment name:

`mfe_path_selectivity_diagnostic_experiment`

Purpose:

Determine whether rescued giveback-loss trades and clipped clean-winner trades are separable using only information available before or at the fixed trigger point.

This is a design-only preregistration. It does not implement a strategy rule and does not search thresholds.

## Allowed Descriptive Inputs

Use only already available lab/replay fields, if present:

* Trade entry timestamp and year
* Completed 750btc bar index
* Running MFE before trigger
* Current return at trigger
* Activation bar offset
* Trigger bar offset
* Delay from activation to trigger
* Original exit class
* Original realized return
* Mechanical fixed-rule return
* Regime labels only if already present in existing replay artifacts

Forbidden:

* Raw L2
* OFI
* Future information after trigger except for class labeling in aggregate diagnostics

## Forbidden Actions

* No parameter search
* No threshold optimization
* No ML model training
* No classifier approval
* No strategy patch
* No paper/live approval
* No row-level artifact export
* No core repo modification

## Required Aggregate Diagnostics For The Future Experiment

The future diagnostic must compare rescued giveback-loss triggers versus clipped clean-winner triggers using aggregate-only outputs.

Required diagnostics:

* Activation timing distribution
* Trigger timing distribution
* MFE-at-trigger distribution
* Giveback depth distribution
* Return-at-trigger distribution
* By-year separability
* Recent-period separability if enough data exists
* Aggregate-only tables
* Synthetic causality checks

## Required Future Questions

The future experiment should answer:

* Are rescued giveback-loss triggers and clipped clean-winner triggers distinguishable from pre-trigger path features?
* Does activation timing differ materially between the two groups?
* Does trigger timing differ materially between the two groups?
* Do MFE-at-trigger and giveback-depth distributions show separability?
* Is there stable by-year separability?
* Is any recent-period effect persistent enough to justify a later design of a selective exit rule?

## Stop / Go Criteria

Choose exact label:

`proceed_to_pre_registered_selective_exit_rule_design_only`

Rationale:

The blunt fixed rule is rejected, but the hypothesis that selectivity can separate rescueable giveback-loss trades from clipped clean winners remains worth designing around. The next step is design-only preregistration, not implementation.

## Closeout Position

The reviewed experiment is closed as a net-destructive false-positive-heavy rule. The only acceptable continuation is a selectivity diagnostic that studies pre-trigger path structure without tuning or deploying a new exit rule.
