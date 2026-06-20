# V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic Design

## Executive Purpose

Design a future aggregate-only diagnostic to test whether richer safe known-at-entry context can explain C Exhaustion recent decay.

The diagnostic must focus on:

- tail-win compression
- tail-loss expansion
- recent negative expectancy
- loss concentration
- missing historical positive-tail conditions
- whether richer context separates historical winners from recent failures

State clearly:

- this is design only
- no strategy rule is approved
- no filter is approved
- no core patch is approved
- no paper/live/production approval is granted

## Background

- MFE exit branch was rejected.
- Selective MFE path decay exit was rejected.
- Signal/regime diagnostic found mixed degradation.
- Enriched diagnostic found VWAP discount as the best stable hint.
- VWAP stability diagnostic found relative improvement but negative recent expectancy.
- Richer context source availability audit found safe usable context sources.
- Current approved path is richer-context enriched decay diagnostic design only.

## Binding Research Questions

The future diagnostic must answer:

A. Does trade_density explain recent C Exhaustion degradation?

B. Does distance_from_recent_high_low explain historical positive tails versus recent failures?

C. Does local_trend_range_state separate working and failing C Exhaustion trades?

D. Does distance_from_vwap remain useful when combined with richer context?

E. Does cvd_delta distinguish historical positive-tail trades from recent losses?

F. Does session_time_of_day_labels explain degradation?

G. Does weekday_weekend_effect explain degradation?

H. Are recent losses concentrated in a small number of safe known-at-entry context buckets?

I. Is tail-win compression reduced in any safe context segment?

J. Is tail-loss expansion avoided in any safe context segment?

K. Does any safe context segment preserve positive or materially less-negative recent descriptive expectancy?

L. Are any apparent effects stable across years, or are they sparse/year-isolated?

## Allowed Fields

Use only fields classified as `safe_available`, `safe_partial`, or `reconstructable_without_leakage` in the richer context source availability audit.

Priority allowed richer context fields:

- trade_density
- distance_from_recent_high_low
- local_trend_range_state
- distance_from_vwap
- cvd_delta
- session_time_of_day_labels
- weekday_weekend_effect

Also allowed if already safe from prior diagnostics:

- trade entry timestamp
- year / period label
- bar size
- horizon
- side if safely available
- original return bps
- gross return bps if available
- net return bps if available
- MFE / MAE if already present
- exit class if already present
- signal state if already present
- volatility_label
- range_trend_label
- regime_label, while noting prior regime label was effectively constant

## Forbidden Fields / Actions

Explicitly forbid:

- raw L2 reads
- new OFI generation
- newly constructed OFI fields
- row-level artifact export
- individual trade/event output
- future-return-derived eligibility fields
- manually assigned discretionary labels
- threshold tuning
- parameter optimization
- arbitrary interaction search
- ML training
- classifier creation
- strategy patching
- core repo modification
- paper/live/production approval

## Required Future Diagnostic Structure

The future diagnostic must be aggregate-only and must report:

### A. Population Accounting

- total C Exhaustion trades inspected
- historical-period trade count
- recent-period trade count
- by-year trade count
- safe fields used
- safe partial fields used
- reconstructable fields used
- blocked fields excluded
- missingness by field

### B. Baseline Period Comparison

Historical vs recent:

- count
- win rate
- average return bps
- median return bps
- p25 / p75 return bps
- p10 / p90 return bps
- positive-tail count
- positive-tail frequency
- large-loss count
- large-loss frequency
- average winner
- average loser
- gross expectancy if available
- net expectancy if available

### C. Single-Field Richer Context Attribution

For each priority field, report historical vs recent aggregate performance by native category or fixed preregistered bucket:

- trade_density
- distance_from_recent_high_low
- local_trend_range_state
- distance_from_vwap
- cvd_delta
- session_time_of_day_labels
- weekday_weekend_effect

For each field/bucket, report:

- historical count
- recent count
- full count
- historical expectancy
- recent expectancy
- full expectancy
- historical win rate
- recent win rate
- historical positive-tail frequency
- recent positive-tail frequency
- historical large-loss frequency
- recent large-loss frequency
- average winner
- average loser
- degradation bps
- sparse flag

### D. Preregistered Interaction Attribution

Inspect only these interactions if aggregate counts are sufficient:

- trade_density × local_trend_range_state
- trade_density × distance_from_vwap
- trade_density × cvd_delta
- distance_from_recent_high_low × local_trend_range_state
- distance_from_vwap × local_trend_range_state
- cvd_delta × local_trend_range_state
- session_time_of_day_labels × trade_density
- weekday_weekend_effect × session_time_of_day_labels

Do not search arbitrary interactions.
Do not optimize combinations.
Do not fit a model.
Do not create a classifier.

For each valid interaction segment, report:

- historical count
- recent count
- historical expectancy
- recent expectancy
- historical win rate
- recent win rate
- positive-tail frequency change
- large-loss frequency change
- average winner change
- average loser change
- degradation bps
- whether sample is sufficient or sparse

### E. Tail Attribution

For each safe field and preregistered interaction, report whether recent degradation is driven by:

- fewer large winners
- smaller average winners
- more frequent large losses
- larger average losses
- lower hit rate
- cost drag if gross/net available

### F. Segment Stability

For any segment that appears descriptively better, report:

- historical count
- recent count
- by-year count
- by-year expectancy
- by-year win rate
- whether benefit appears in more than one year
- whether recent sample is too sparse
- whether effect is year-isolated
- whether tail-loss expansion is acceptable
- whether segment is stable enough only for future design or should be rejected

No segment may be approved for strategy use.

## Fixed Bucketing Rules

Avoid threshold optimization.

Use native categorical values where available.

For continuous fields, use only fixed preregistered bins.

Suggested bins:

### trade_density

- low
- medium
- high

Use existing/native bins if already materialized.
If continuous only, use fixed tertile-style descriptive buckets only if pre-entry and aggregate-safe, and mark as descriptive, not optimized.

### distance_from_recent_high_low

- near recent low
- middle range
- near recent high

### distance_from_vwap

- below -100 bps
- -100 to -25 bps
- -25 to +25 bps
- +25 to +100 bps
- above +100 bps

### cvd_delta

- negative
- neutral
- positive

### local_trend_range_state

Use native labels only.
Do not create tuned state definitions.

### session_time_of_day_labels

Use native labels if present.
If reconstructable safely from timestamp, use fixed UTC session buckets:

- Asia
- Europe
- US
- overlap

### weekday_weekend_effect

- weekday
- weekend

## Synthetic Causality / Leakage Checks

The future diagnostic must confirm:

- period assignment uses timestamp only
- each explanatory field is known at or before entry
- continuous bins are fixed before looking at outcomes
- native labels are not derived from future returns
- return outcomes are used only for aggregate attribution
- no future path information is used to define eligibility
- no raw L2 is read
- OFI is not generated
- no row-level artifacts are exported
- no modeling dataset is created
- missing fields are not silently treated as safe
- core repo is not modified

## Required Interpretation Labels

The future diagnostic must choose exactly one primary enriched explanation:

- trade_density_context_degradation_dominant
- high_low_distance_context_degradation_dominant
- local_trend_range_context_degradation_dominant
- vwap_distance_context_degradation_dominant
- cvd_delta_context_degradation_dominant
- session_context_degradation_dominant
- weekday_weekend_context_degradation_dominant
- mixed_richer_context_degradation_no_single_driver
- no_safe_richer_context_explains_degradation
- inconclusive_due_to_sparse_segments
- blocked_due_to_missing_required_inputs

## Required Stop / Go Labels

The future diagnostic must choose exactly one:

- proceed_to_preregistered_richer_context_filter_design_only
- keep_anchor_alive_but_collect_more_inputs
- reject_c_exhaustion_anchor_as_unexplained_recent_decay
- blocked_due_to_missing_required_inputs

## Hard Proceed Criteria

The future diagnostic may only choose `proceed_to_preregistered_richer_context_filter_design_only` if all are true:

- at least one safe known-at-entry richer context field or preregistered interaction shows materially better recent descriptive expectancy
- the segment has sufficient recent sample count
- the improvement is not caused only by one isolated year
- tail-win compression is materially reduced or recent expectancy is positive/near-flat despite compression
- tail-loss expansion is not worse than full recent sample
- large-loss frequency is not worse than full recent sample
- synthetic causality checks pass
- no raw L2 was read
- OFI was not generated
- no row-level artifacts were exported
- no core repo files were modified

The diagnostic must choose `reject_c_exhaustion_anchor_as_unexplained_recent_decay` if:

- no safe richer context field explains degradation
- all apparent segments are sparse or year-isolated
- tail-win compression and tail-loss expansion persist across all safe richer contexts

The diagnostic must choose `keep_anchor_alive_but_collect_more_inputs` if:

- safe richer fields show hints but insufficient coverage
- promising fields are partial
- stronger market-context inputs are required before designing a filter

## Validation For This Design Task

Required validation:

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only

Commit and push to the same branch.

## Final Response Must Include

- Commit SHA
- Branch
- Files changed
- Tests run or not run
- Exact design memo path
- Design name
- Confirmation that no diagnostic was run
- Confirmation that core repo was not modified
- Approved next action label:
  `proceed_to_c_exhaustion_richer_context_enriched_decay_diagnostic_only`
