# V9.2 Hermes C Exhaustion Enriched Decay Closeout and VWAP Context Stability Design

## Executive Decision

- Enriched diagnostic completed.
- Primary explanation remains `mixed_context_degradation_no_single_driver`.
- Stop/go remains `keep_anchor_alive_but_collect_more_inputs`.
- No core patch is approved.
- No strategy filter is approved.
- No paper/live/production approval is granted.
- `distance_from_vwap = -100 to -25 bps` is approved only for design-only follow-up.
- `range_trend_label = range` is not promoted because it was too sparse.

Final closeout label: `keep_c_exhaustion_anchor_alive_with_vwap_context_stability_followup_design_only`

## Diagnostic Summary

- commit SHA: `5151a21fe46638e55b22e1570371b1ccec9dd465`
- report path: `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_ENRICHED_SIGNAL_REGIME_DECAY_DIAGNOSTIC.md`
- primary explanation label: `mixed_context_degradation_no_single_driver`
- stop/go label: `keep_anchor_alive_but_collect_more_inputs`
- best stable segment: `distance_from_vwap = -100 to -25 bps`
- sparse raw-best segment: `range_trend_label = range`
- confirmation: degradation remains mixed
- confirmation: no raw L2, OFI, row-level export, or core modification occurred

## Interpretation

The `distance_from_vwap = -100 to -25 bps` segment suggests that C Exhaustion may behave better when the entry is moderately below VWAP. That is consistent with more favorable mean-reversion geometry and a cleaner entry context than the broader sample.

This is still only a descriptive stability signal. It is not a rule, not a filter, and not approval for a patch.

## Not-Approved Paths

- fixed MFE giveback exit
- selective MFE path decay exit
- direct `regime_label` filter
- direct `range_trend_label = range` filter
- direct cost filter
- direct CVD/delta filter
- direct VWAP-distance filter implementation
- tuned VWAP threshold
- ML/classifier approach

## Approved Next Design-Only Branch

Approved branch name: `c_exhaustion_vwap_distance_context_stability_diagnostic_design`

Purpose:
Design a future aggregate-only diagnostic to test whether `distance_from_vwap = -100 to -25 bps` is stable enough to justify a later context-filter preregistration.

Do not run that diagnostic in this task.

## Future Diagnostic Requirements

The future diagnostic must:

- use only the fixed VWAP segment `distance_from_vwap = -100 to -25 bps`
- compare it against all other preregistered VWAP bins
- avoid threshold search
- avoid alternative VWAP bands
- avoid optimization
- avoid ML/classifiers
- avoid strategy patching
- avoid core repo modification
- avoid raw L2
- avoid new OFI
- avoid row-level artifacts

## Future Stop / Go Labels

The future diagnostic must choose exactly one:

- `proceed_to_vwap_context_filter_preregistration_design_only`
- `keep_anchor_alive_but_collect_more_inputs`
- `reject_vwap_context_followup`
- `blocked_due_to_missing_required_inputs`

## Validation

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short` before work
- `git diff --check`
- `git status --short` after work
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only

