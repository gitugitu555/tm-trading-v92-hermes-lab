# V9.2 Hermes C Exhaustion Richer Context Source Availability Audit Design

## Executive Purpose

Design a future aggregate-only audit to determine which richer known-at-entry market-context sources are:

- already available
- safely reconstructable
- partially available
- missing
- timestamp unsafe
- leakage unsafe
- blocked due to raw L2 requirement
- blocked due to OFI generation requirement
- blocked due to row-level export requirement

The audit supports future enriched diagnostics only.

It must not approve a strategy rule, filter, core patch, paper trading, live trading, or production use.

## Background

- MFE exit branch rejected.
- Selective MFE exit branch rejected.
- Signal/regime attribution found mixed degradation.
- Enriched diagnostic found VWAP discount as the best safe context hint.
- VWAP stability diagnostic showed relative improvement but negative recent expectancy.
- VWAP filter was not approved.
- C Exhaustion remains research anchor only.
- Current approved path is richer known-at-entry source availability audit design-only.

## Binding Research Questions

The future audit must answer:

A. Which richer context sources exist across the historical C Exhaustion sample?

B. Which sources exist across the recent decay period?

C. Which sources are known at or before trade entry?

D. Which sources have timestamp ambiguity?

E. Which sources would introduce future leakage?

F. Which sources require raw L2 and are therefore blocked?

G. Which sources require newly generated OFI and are therefore blocked?

H. Which sources can safely support a future richer-context enriched decay diagnostic?

I. Which sources are too sparse, incomplete, unsafe, or missing?

## Candidate Source Groups

The future audit must cover these groups where discoverable from existing artifacts only.

### A. Derivatives Context

- funding rate
- open interest
- open interest velocity
- liquidation prints
- long/short ratio if available
- perp basis / premium

### B. Trade-Flow Context

- CVD / delta
- aggressive buy/sell imbalance
- large trade clusters
- trade density
- volume burst
- notional burst

### C. Market-Structure Context

- spread
- microprice if safely available
- top-of-book imbalance if safely materialized
- depth imbalance if already safely materialized
- volatility expansion/compression
- range/trend state
- VWAP distance
- recent high/low distance

### D. Cross-Market Context

- BTC market beta
- ETH/BTC context if available
- market-wide crypto risk regime
- dollar index / macro proxy only if safely timestamped
- session/time-of-day
- weekday/weekend effect

### E. Unsafe / Blocked Unless Explicitly Approved Later

- raw L2
- newly generated OFI
- reconstructed order book features from unsafe timestamps
- row-level trade export
- future-return-derived labels

## Required Future Audit Classification Labels

Each candidate source or field must be classified as exactly one:

- `safe_available`
- `safe_partial`
- `reconstructable_without_leakage`
- `blocked_missing`
- `blocked_insufficient_coverage`
- `blocked_timestamp_unsafe`
- `blocked_requires_raw_l2`
- `blocked_requires_new_ofi`
- `blocked_future_leakage_risk`
- `blocked_row_level_export_required`

## Required Future Aggregate Outputs

For each candidate field or source, the future audit must report aggregate-only:

- field name
- source group
- source type
- source path pattern or provider if known
- historical coverage percentage
- recent coverage percentage
- full-sample coverage percentage
- earliest timestamp
- latest timestamp
- timestamp granularity
- known-at-entry status
- timestamp safety status
- leakage risk
- reconstruction risk
- requires raw L2 yes/no
- requires OFI generation yes/no
- requires row-level export yes/no
- safe for future enriched diagnostic yes/no
- blocked reason if blocked
- final classification label

## Strict Safety Constraints

The future audit must not:

- read raw L2
- generate OFI
- export row-level artifacts
- create a modeling dataset
- use future returns as eligibility features
- patch strategy code
- modify core repo
- approve paper/live/production trading

## Required Future Safety Checks

The future audit must confirm:

- no raw L2 files are read
- OFI is not generated
- no row-level artifact is exported
- no modeling dataset is created
- no core repo files are modified
- known-at-entry status is documented for every usable field
- timestamp safety is documented for every usable field
- missing fields are not silently treated as safe
- future-return-derived fields are blocked

## Required Future Stop / Go Labels

The future audit must choose exactly one:

- `proceed_to_richer_context_enriched_decay_diagnostic_design_only`
- `keep_anchor_alive_but_data_still_insufficient`
- `reject_c_exhaustion_anchor_due_to_unrecoverable_context_gap`
- `blocked_due_to_missing_required_inputs`

## Hard Proceed Criteria

The future audit may only choose `proceed_to_richer_context_enriched_decay_diagnostic_design_only` if:

- at least one richer non-outcome context source is `safe_available` or `reconstructable_without_leakage`
- both historical and recent coverage are sufficient for aggregate comparison
- known-at-entry status is confirmed
- timestamp safety is confirmed
- no raw L2 read is required
- no new OFI generation is required
- no row-level artifact export is required
- no core repo modification is required

## Approved Next Action

`proceed_to_c_exhaustion_richer_context_source_availability_audit_only`

Do not run the audit in this task.

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

