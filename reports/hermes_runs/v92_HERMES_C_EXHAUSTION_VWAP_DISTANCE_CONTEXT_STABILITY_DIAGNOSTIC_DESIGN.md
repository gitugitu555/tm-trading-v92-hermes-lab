# V9.2 Hermes C Exhaustion VWAP Distance Context Stability Diagnostic Design

## Executive Purpose

Design a future aggregate-only diagnostic to test whether the fixed VWAP-distance segment `distance_from_vwap = -100 to -25 bps` is stable enough to justify a later context-filter preregistration.

The diagnostic must not approve implementation.

## Background

- MFE exit branch rejected.
- Mixed-decay diagnostic found no single dominant driver.
- Input availability audit found safe explanatory fields.
- Enriched diagnostic found `distance_from_vwap = -100 to -25 bps` as the strongest stable design-only segment.
- `range_trend_label = range` had the raw best point estimate but was too sparse.
- No strategy rule, filter, paper/live approval, or core patch is approved.

## Binding Research Question

Does the fixed `distance_from_vwap = -100 to -25 bps` segment preserve better C Exhaustion descriptive expectancy across both historical and recent periods, without being year-isolated, sparse, or driven by unacceptable tail-risk expansion?

## Fixed Target Segment

The only target segment is:

- `distance_from_vwap = -100 to -25 bps`

This segment must not be changed.

Forbidden:

- do not test `-125 to -25`
- do not test `-100 to 0`
- do not test alternative VWAP bands
- do not merge adjacent bins
- do not optimize the band
- do not search thresholds

## Required Comparison Bins

Compare the target segment against the preregistered VWAP bins from the enriched diagnostic:

- below `-100 bps`
- `-100 to -25 bps`
- `-25 to +25 bps`
- `+25 to +100 bps`
- above `+100 bps`

Do not create new bins.

## Allowed Inputs

Use only fields already confirmed safe in the input availability audit and used in the enriched diagnostic:

- trade entry timestamp
- year / period label
- distance_from_vwap
- VWAP-distance bin
- original return bps
- gross return bps if available
- net return bps if available
- MFE / MAE if already present
- exit class if already present
- side if safely available
- bar size
- horizon
- cost assumptions already used in prior reports

## Forbidden Inputs / Actions

Explicitly forbid:

- raw L2 reads
- OFI generation
- newly constructed OFI fields
- row-level artifact export
- individual trade/event output
- future-return-derived eligibility fields
- manually assigned labels
- threshold tuning
- alternative VWAP bands
- parameter optimization
- ML training
- classifier creation
- strategy patching
- core repo modification
- paper/live/production approval

## Required Future Aggregate Outputs

The future diagnostic must report aggregate-only:

### Population Accounting

- total C Exhaustion trades inspected
- trades with safe `distance_from_vwap` available
- trades in target segment
- trades in each other VWAP bin
- historical count
- recent count
- by-year count

### Segment Comparison

For each VWAP bin:

- historical expectancy
- recent expectancy
- full-sample expectancy
- historical win rate
- recent win rate
- average winner
- average loser
- positive-tail frequency
- large-loss frequency
- p10 / p25 / median / p75 / p90 return bps
- gross expectancy if available
- net expectancy if available
- degradation bps

### Target-Segment Stability

For `distance_from_vwap = -100 to -25 bps`:

- historical count
- recent count
- by-year count
- by-year expectancy
- by-year win rate
- whether positive expectancy appears in more than one year
- whether recent result is dominated by one year
- whether recent sample is sufficient
- whether positive-tail compression remains
- whether tail-loss expansion remains
- whether average loser worsened
- whether large-loss frequency worsened

### Comparison Versus Full Recent Sample

For the target segment, compare against full recent C Exhaustion sample:

- recent expectancy delta
- recent win-rate delta
- positive-tail frequency delta
- large-loss frequency delta
- average winner delta
- average loser delta
- net expectancy delta if available

### Sparse Alternative Control

Document why `range_trend_label = range` remains not promoted unless future evidence changes:

- count
- recent count
- year concentration
- sparse status
- no filter approval

### Causality / Leakage Checks

Confirm:

- `distance_from_vwap` is known at or before entry
- VWAP bins are fixed and preregistered
- no future returns are used for eligibility
- outcomes are used only for aggregate attribution
- no raw L2 is read
- OFI is not generated
- no row-level artifacts are exported
- no modeling dataset is created
- core repo is not modified

## Required Future Interpretation Labels

The future diagnostic must choose exactly one:

- `vwap_discount_segment_stable_descriptive_edge`
- `vwap_discount_segment_hint_but_sparse`
- `vwap_discount_segment_year_isolated`
- `vwap_discount_segment_tail_risk_unacceptable`
- `vwap_discount_segment_not_different_from_others`
- `blocked_due_to_missing_required_inputs`

## Required Future Stop/Go Labels

The future diagnostic must choose exactly one:

- `proceed_to_vwap_context_filter_preregistration_design_only`
- `keep_anchor_alive_but_collect_more_inputs`
- `reject_vwap_context_followup`
- `blocked_due_to_missing_required_inputs`

## Hard Proceed Criteria

The future diagnostic may only choose `proceed_to_vwap_context_filter_preregistration_design_only` if all are true:

- target segment has better recent descriptive expectancy than the full recent C Exhaustion sample
- target segment has sufficient recent sample count
- improvement is not isolated to one year
- positive-tail compression is materially reduced or expectancy remains positive despite compression
- tail-loss expansion is not worse than full recent sample
- large-loss frequency is not worse than full recent sample
- synthetic causality checks pass
- no raw L2 was read
- OFI was not generated
- no row-level artifacts were exported
- no core repo files were modified

The future diagnostic must reject the VWAP follow-up if:

- target segment remains negative
- target segment is sparse
- benefit is year-isolated
- large-loss frequency or average loser is worse than full sample
- target segment is not materially better than other bins
- causality checks fail

## Validation For This Design Task

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short` before work
- `git diff --check`
- `git status --short` after work
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only

