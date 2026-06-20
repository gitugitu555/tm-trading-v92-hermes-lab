# V9.2 Hermes C Exhaustion Known-at-Entry Context Collection Design

## Executive Purpose

Design a future data and context collection plan to determine which richer known-at-entry market-context inputs could explain C Exhaustion recent decay.

This is data collection design only.

- No strategy rule is approved.
- No filter is approved.
- No core patch is approved.
- No paper/live/production approval is granted.

## Background

- MFE exit branch rejected.
- Selective exit branch rejected.
- Signal/regime attribution found mixed degradation.
- Enriched diagnostic found VWAP discount as the best stable hint.
- VWAP stability diagnostic found relative improvement but negative recent expectancy.
- Current state is `keep_anchor_alive_but_collect_more_inputs`.

## Collection Objective

The future collection effort must focus only on known-at-entry or pre-entry context that could explain:

- tail-win compression
- tail-loss expansion
- loss concentration
- missing positive-tail conditions
- changed market microstructure around C Exhaustion entries

## Candidate Context Groups

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

## Required Future Availability Audit

Design a future audit named `c_exhaustion_richer_context_source_availability_audit`.

The audit must classify each candidate source as exactly one of:

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

## Required Future Audit Outputs

For each candidate field or source, report aggregate-only:

- field name
- source type
- source path or provider if known
- historical coverage percentage
- recent coverage percentage
- earliest timestamp
- latest timestamp
- timestamp granularity
- known-at-entry status
- leakage risk
- reconstruction risk
- requires raw L2 yes/no
- requires OFI generation yes/no
- requires row-level export yes/no
- safe for future enriched diagnostic yes/no
- blocked reason if blocked

## Strict Safety Constraints

The future audit must not:

- read raw L2
- generate OFI
- export row-level artifacts
- create modeling datasets
- use future returns as eligibility features
- patch strategy code
- modify core repo
- approve trading

## Required Future Stop / Go Labels

The future audit must choose exactly one:

- `proceed_to_richer_context_enriched_decay_diagnostic_design_only`
- `keep_anchor_alive_but_data_still_insufficient`
- `reject_c_exhaustion_anchor_due_to_unrecoverable_context_gap`
- `blocked_due_to_missing_required_inputs`

## Approved Next Action Label

`proceed_to_c_exhaustion_richer_context_source_availability_audit_design_only`

Do not run that audit in this task.

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

