# V9.2 Hermes C Exhaustion VWAP Distance Context Stability Closeout

## Executive Decision

- VWAP stability diagnostic completed.
- Target segment `distance_from_vwap = -100 to -25 bps` showed stable relative improvement.
- Target segment beat full recent C Exhaustion expectancy.
- Target segment was not year-isolated.
- Tail-loss expansion was acceptable.
- However target segment recent expectancy remained negative at `-83.101 bps`.
- Recent sample count was only `14` trades.
- Therefore VWAP context filter preregistration is not approved.
- No strategy patch is approved.
- No paper/live/production approval is granted.
- C Exhaustion remains a research anchor only.

Final closeout label: `close_vwap_context_stability_branch_keep_anchor_alive_collect_more_inputs`

## Diagnostic Summary

- commit SHA: `3d7c474c0a74078f37f2579cbd1d70f8e4896c32`
- report path: `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_VWAP_DISTANCE_CONTEXT_STABILITY_DIAGNOSTIC.md`
- interpretation label: `vwap_discount_segment_stable_descriptive_edge`
- stop/go label: `keep_anchor_alive_but_collect_more_inputs`
- target segment: `distance_from_vwap = -100 to -25 bps`
- target recent expectancy: `-83.101 bps`
- full recent expectancy: `-108.743 bps`
- relative improvement in bps: `25.642 bps`
- recent target count: `14`
- year-isolation status: `not year-isolated`
- tail-loss status: `acceptable`
- filter preregistration approval status: `not approved`

## Interpretation

`distance_from_vwap = -100 to -25 bps` is a stabilising context, not a complete repair.

The segment improves recent expectancy by `25.642 bps` versus the full recent sample, but expectancy remains negative. That is not enough to justify filter preregistration.

The result suggests context matters, but C Exhaustion still lacks sufficient recent edge.

## Not-Approved Paths

The following are not approved:

- core patch
- VWAP context filter
- tuned VWAP threshold
- merged VWAP bins
- alternative VWAP band search
- `range_trend_label = range` promotion
- MFE exit retry
- cost filter
- ML/classifier
- paper/live/production

## Research State After Closeout

- C Exhaustion historical anchor remains research-valid.
- Recent production validity remains unproven.
- Current best safe context is VWAP discount, but it is insufficient alone.
- Next step should be either collect richer known-at-entry market-context inputs or close/archive C Exhaustion as recently unstable.

## Approved Next Action Label

`keep_anchor_alive_but_collect_more_inputs`

Do not approve another diagnostic unless explicitly justified by missing-input collection.

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

