# V92 Hermes C Exhaustion Enriched Signal Regime Decay Diagnostic Design

## Executive Purpose

Design a future aggregate-only enriched diagnostic to determine whether C Exhaustion recent mixed degradation can be explained by safe known-at-entry or pre-entry explanatory fields.

The diagnostic must investigate whether tail-win compression and tail-loss expansion are associated with:

- volatility state
- range / trend state
- distance from VWAP
- distance from recent high / low
- prior bar return path
- CVD / delta context
- session / time-of-day
- regime label, while noting the prior regime label was effectively constant `EXHAUSTED`

## Background

The MFE exit branch was rejected.
Fixed MFE giveback rule was net destructive.
Selective MFE path decay rule was rejected.
C Exhaustion recent decay diagnostic found mixed degradation.
Tail-win compression and tail-loss expansion were both material.
Current regime label alone was not discriminative.
Cost drag was flat and did not explain the decay.
Input availability audit found enough safe fields to design an enriched diagnostic.
Therefore the next step is design-only preregistration for aggregate enriched attribution.

## Binding Research Questions

The future diagnostic must answer:

A. Are recent C Exhaustion losses concentrated in specific volatility states?

B. Are recent losses concentrated in range or trend regimes?

C. Did historical positive tails occur at different distance-from-VWAP or distance-from-recent-high / low contexts than recent trades?

D. Did prior bar return path change between historical winners and recent failures?

E. Does CVD / delta context distinguish historical positive-tail trades from recent tail-loss trades?

F. Is degradation session / time-of-day dependent?

G. Are tail-win compression and tail-loss expansion explained by any safe field or field interaction?

H. Does any safe aggregate segment preserve descriptive expectancy across historical and recent periods?

I. Are observed differences broad and stable, or year-specific / sparse?

## Allowed Fields

Allowed only if confirmed safe by the input availability audit:

- `regime_label`
- `volatility_label`
- `range_trend_label`
- `distance_from_recent_high_low`
- `distance_from_vwap`
- `prior_bar_return_path`
- `cvd_delta`
- `session_time_of_day_labels`
- trade entry timestamp
- year / period label
- bar size
- horizon
- side if safely available
- gross return bps if available
- net return bps if available
- original return bps
- MFE / MAE if already present
- exit class if already present
- signal state if already present

## Forbidden Fields / Actions

Explicitly forbid:

- raw L2 reads
- new OFI generation
- newly constructed OFI fields
- row-level artifact export
- individual trade / event output
- future-return-derived fields as eligibility inputs
- manually assigned discretionary labels
- threshold tuning
- parameter optimization
- ML training
- classifier creation
- strategy patching
- core repo modification
- paper/live/production approval

## Required Future Diagnostic Structure

The future diagnostic must be aggregate-only and must report:

### A. Population Accounting

- total trades inspected
- historical-period trade count
- recent-period trade count
- by-year trade count
- fields available
- fields missing
- fields used
- fields blocked

### B. Period Comparison

Historical vs recent:

- count
- win rate
- average return bps
- median return bps
- p25 / p75 return bps
- p10 / p90 return bps
- positive-tail count
- large-loss count
- average winner
- average loser
- gross expectancy if available
- net expectancy if available

### C. Single-Field Attribution

For each safe explanatory field, report aggregate historical vs recent performance by fixed field bucket or native categorical value.

Required fields:

- `volatility_label`
- `range_trend_label`
- `distance_from_vwap`
- `distance_from_recent_high_low`
- `prior_bar_return_path`
- `cvd_delta`
- `session_time_of_day_labels`
- `regime_label`, but explicitly note if effectively constant

For each field / bucket, report:

- historical count
- recent count
- historical expectancy
- recent expectancy
- historical win rate
- recent win rate
- historical positive-tail frequency
- recent positive-tail frequency
- historical large-loss frequency
- recent large-loss frequency
- degradation bps

### D. Interaction Attribution

If aggregate counts are sufficient, inspect only these preregistered interactions:

- `volatility_label × range_trend_label`
- `distance_from_vwap × range_trend_label`
- `distance_from_recent_high_low × range_trend_label`
- `prior_bar_return_path × volatility_label`
- `cvd_delta × range_trend_label`
- `session_time_of_day_labels × volatility_label`

Do not search arbitrary interactions.
Do not optimize combinations.
Do not fit a model.
Do not create a classifier.

### E. Tail Attribution

For each safe field and preregistered interaction, report whether recent degradation is driven by:

- fewer large winners
- smaller average winners
- more frequent large losses
- larger average losses
- lower hit rate
- cost drag if net / gross available

### F. Segment Stability

For any segment that appears descriptively better, report:

- historical count
- recent count
- by-year count
- by-year expectancy
- whether benefit appears in more than one year
- whether recent sample is too sparse
- whether segment is stable enough only for future design or should be rejected

No segment may be approved for strategy use.

## Fixed Bucketing Rules

The diagnostic must avoid threshold optimization.

Use only native categorical values where available.

For continuous safe fields, use fixed preregistered bins.

Suggested fixed bins:

`distance_from_vwap_bps`:

- below -100 bps
- -100 to -25 bps
- -25 to +25 bps
- +25 to +100 bps
- above +100 bps

`distance_from_recent_high_low_bps`:

- near recent low
- middle range
- near recent high

Use only if these states already exist or can be reconstructed without leakage. Otherwise mark blocked.

`prior_bar_return_path_bps`:

- negative
- flat / small absolute move
- positive

Use conservative fixed cutoffs:

- negative: <= -25 bps
- flat: > -25 bps and < +25 bps
- positive: >= +25 bps

`cvd_delta`:

Use only if safely materialized and known at entry.
Use native sign or fixed bins:

- negative
- neutral
- positive

`session_time_of_day_labels`:

Use native labels if already present.
If not present but safely reconstructable from entry timestamp, use fixed UTC session buckets:

- Asia
- Europe
- US
- overlap

The report must document the exact session definition.

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

## Required Interpretation Labels

The future diagnostic must choose one primary enriched explanation:

- `volatility_context_degradation_dominant`
- `range_trend_context_degradation_dominant`
- `vwap_distance_context_degradation_dominant`
- `high_low_distance_context_degradation_dominant`
- `prior_path_context_degradation_dominant`
- `cvd_delta_context_degradation_dominant`
- `session_context_degradation_dominant`
- `mixed_context_degradation_no_single_driver`
- `no_safe_context_explains_degradation`
- `inconclusive_due_to_sparse_segments`
- `blocked_due_to_missing_required_inputs`

## Required Stop/Go Labels

The future diagnostic must choose exactly one:

- `proceed_to_preregistered_context_filter_design_only`
- `keep_anchor_alive_but_collect_more_inputs`
- `reject_c_exhaustion_anchor_as_unexplained_recent_decay`
- `blocked_due_to_missing_required_inputs`

## Hard Proceed Criteria

The future diagnostic may only choose `proceed_to_preregistered_context_filter_design_only` if all are true:

- at least one safe known-at-entry context field or preregistered interaction shows materially better recent descriptive expectancy
- the improvement is not caused only by one isolated year
- recent sample count is sufficient for aggregate comparison
- tail-win compression or tail-loss expansion is reduced in the segment
- synthetic causality checks pass
- no raw L2 was read
- OFI was not generated
- no row-level artifacts were exported
- no core repo files were modified

The diagnostic must choose `reject_c_exhaustion_anchor_as_unexplained_recent_decay` if:

- no safe context field explains degradation
- all apparent segments are sparse or year-isolated
- tail-win compression and tail-loss expansion persist across all safe contexts

The diagnostic must choose `keep_anchor_alive_but_collect_more_inputs` if:

- safe fields show hints but insufficient coverage
- CVD / delta or other promising fields are partial
- stronger market-context inputs are required before designing a filter

## Required Validation for This Design Task

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only

## Approved Next Action

Approved next action label: `proceed_to_c_exhaustion_enriched_signal_regime_decay_diagnostic_only`

Do not run the diagnostic in this task.
