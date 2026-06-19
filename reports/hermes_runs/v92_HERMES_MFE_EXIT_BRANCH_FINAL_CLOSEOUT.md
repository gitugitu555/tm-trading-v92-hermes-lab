# V92 Hermes MFE Exit Branch Final Closeout

## Executive Decision

The `fixed_running_mfe_giveback_protection_experiment` is rejected.
The `selective_mfe_path_decay_exit_experiment` is rejected.
No exit rule is approved.
No core patch is approved.
No paper, live, or production approval is granted.
No further threshold tuning should be performed on this branch.

Final branch decision label: `reject_mfe_exit_branch_return_to_signal_regime_diagnostics`

## Fixed Rule Summary

- Total inspected trades: 310
- Activated trades: 211
- Triggered trades: 166
- Full-sample net delta: -6,450.394 bps
- Clean-winner clipping cost: -12,394.355 bps
- Giveback-loss rescue benefit: +5,986.279 bps
- Rejection reason: clean-winner clipping dominated rescue benefit

## Selectivity Diagnostic Summary

- Diagnostic decision: `proceed_to_pre_registered_selective_exit_rule_design_only`
- Separability result: weak, with materially overlapping distributions
- Strongest fields:
  - `current_return_at_trigger_bps`
  - `giveback_depth_at_trigger_bps`
  - `running_mfe_at_trigger_bps`
  - `trigger_offset_bars`
- Caution: weak separability justified only one fixed design experiment, not implementation

## Selective Rule Experiment Summary

- Final decision: `reject_selective_mfe_path_decay_exit_rule`
- Selective eligible trade count: 28
- Aggregate delta bps: -3,141.184
- Clean-winner clipping cost: -2,276.954
- Giveback-loss rescue benefit: +85.404
- Comparison versus fixed rule:
  - clipping cost improved
  - rescue benefit collapsed
  - aggregate delta remained negative
  - rule not promotable

## Final Interpretation

MFE giveback exists descriptively.
Blunt protection is economically destructive.
Selective path gates reduced false positives but removed most rescue value.
Exit-only repair is unsupported.

The next research focus should move upstream to:
- signal decay
- regime mismatch
- entry quality
- recent-period attribution
- cost sensitivity
- tail-loss and tail-win distribution changes

## Forbidden Follow-Up Actions

- tuning activation threshold
- tuning giveback ratio
- tuning trigger offset
- adding more exit variants
- strategy patching
- core repo modification
- paper/live/production approval
- using row-level artifacts
- raw L2 reads
- OFI generation

## Approved Next Research Direction

next_pre_registered_research_design_only: `c_exhaustion_recent_decay_signal_regime_attribution_design`

Purpose: design a diagnostic to determine whether recent C Exhaustion degradation is caused by signal decay, regime mismatch, entry selection failure, tail compression, or cost sensitivity.

Do not run the new diagnostic in this task. Design only.

## Validation

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- no tests required because Markdown-only
