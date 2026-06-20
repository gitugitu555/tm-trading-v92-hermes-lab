# V92 Hermes C Exhaustion Mixed Decay Input Availability Audit Design

## Executive Purpose

Design a future aggregate-only audit to determine which explanatory fields are:

- already available
- safely reconstructable
- partially available
- missing
- unsafe due to leakage risk
- unsafe due to timestamp ambiguity
- unsafe due to historical coverage gaps

The audit must support future enriched diagnostics only.
It must not approve any trading rule.

## Background

The MFE exit branch was rejected.
C Exhaustion recent decay diagnostic found mixed degradation.
Tail-win compression and tail-loss expansion are both material.
The current `EXHAUSTED` regime label is not discriminative.
Cost drag is flat and does not explain the decay.
The current conclusion is to keep the research anchor alive but collect more inputs.
The next step must audit safe explanatory field availability before any new filter design.

## Binding Research Questions

The future audit must answer:

A. Which known-at-entry fields exist across the full historical sample?

B. Which fields exist in the recent decay period?

C. Which fields have uneven historical vs recent coverage?

D. Which fields are safely known at or before trade entry?

E. Which fields are derived from future path information and must be blocked?

F. Which fields require raw L2 or OFI generation and are currently unsafe?

G. Which fields are safe enough for a future enriched signal/regime diagnostic?

H. Which fields are too sparse, too leaky, or too incomplete to use?

## Field Inventory to Audit

The future audit must inspect availability for these groups if discoverable from existing artifacts only.

### A. Existing Replay Fields

- trade entry timestamp
- year / period label
- bar size
- horizon
- side if safely available
- original return bps
- gross return bps if available
- net return bps if available
- MFE if already present
- MAE if already present
- exit class if already present
- signal state if already present
- regime label if already present
- MTF alignment if already present
- range / trend label if already present
- volatility label if already present

### B. Potential Pre-Entry Context Fields

- pre-entry volatility expansion or compression
- prior bar return path
- prior bar range
- prior bar volume / notional
- prior trade density
- signal intensity / score magnitude if present
- distance from VWAP or anchored VWAP if present
- distance from recent high / low if present
- local trend / range state if present

### C. External or Missing Market-Context Fields

- funding
- open interest
- liquidation data
- CVD / delta
- OFI
- L2 imbalance
- spread
- microprice
- order book depth
- whale / large print context
- market-wide beta / BTC regime context
- session / time-of-day labels if present

### D. Unsafe or Restricted Fields

- raw L2-derived fields unless already safely materialized
- newly generated OFI
- fields requiring row-level trade export
- future-return-derived labels used as eligibility inputs
- manually assigned discretionary labels

## Required Future Audit Outputs

The future audit must produce aggregate-only tables.

For each audited field, report:

- field name
- category
- source artifact or missing
- source path pattern if available
- historical coverage percentage
- recent coverage percentage
- full-sample coverage percentage
- missingness percentage
- earliest timestamp covered
- latest timestamp covered
- known-at-entry status
- timestamp safety status
- leakage risk
- reconstruction risk
- requires raw L2: yes/no
- requires OFI generation: yes/no
- requires row-level export: yes/no
- safe for future diagnostic: yes/no
- blocked reason if blocked

## Coverage Classification

The future audit must classify each field as exactly one:

- safe_available
- safe_partial
- reconstructable_without_leakage
- blocked_missing
- blocked_insufficient_coverage
- blocked_timestamp_unsafe
- blocked_requires_raw_l2
- blocked_requires_new_ofi
- blocked_future_leakage_risk
- blocked_row_level_export_required

## Aggregate-Only Constraint

The future audit may inspect schemas, metadata, filenames, columns, and aggregate coverage.

It must not output row-level trade records.
It must not export individual trade rows.
It must not create a research dataset for modeling.
It must not approve any feature for live use.
It must only produce availability and safety summaries.

## Synthetic Safety Checks Required for the Future Audit

The future audit must confirm:

- no raw L2 files are read
- OFI is not generated
- row-level artifacts are not exported
- timestamp coverage is checked before field approval
- known-at-entry status is documented for every field
- future outcome fields are marked post-hoc only
- missing fields are not silently treated as safe

## Future Stop/Go Labels

The future audit must choose exactly one:

- proceed_to_enriched_signal_regime_decay_diagnostic_design_only
- keep_anchor_alive_but_data_insufficient
- reject_anchor_due_to_unrecoverable_missing_inputs
- blocked_due_to_missing_required_inputs

## Hard Proceed Criteria for Future Enriched Diagnostic Design

The future audit may only choose `proceed_to_enriched_signal_regime_decay_diagnostic_design_only` if:

- at least one non-outcome explanatory field is `safe_available` or `reconstructable_without_leakage`
- historical and recent coverage are both sufficient for aggregate comparison
- timestamp safety is confirmed
- known-at-entry status is confirmed
- no raw L2 or newly generated OFI is required
- no row-level artifact export is required

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

Approved next action label: `proceed_to_c_exhaustion_mixed_decay_input_availability_audit_only`

Do not run the audit in this task.
