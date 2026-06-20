# V92 Hermes C Exhaustion Mixed Decay Closeout and Input Collection Design

## Executive Decision

C Exhaustion recent decay is not explained by a single dominant driver.
Current evidence supports mixed degradation.
Tail-win compression and tail-loss expansion are both material.
Existing regime labels are not sufficiently discriminative because regime is effectively constant `EXHAUSTED`.
Existing cost analysis does not explain the decay because cost drag stays flat.
No strategy patch is approved.
No core repo modification is approved.
No paper, live, or production approval is granted.
The next step is missing-input collection design only.

Final closeout label: `keep_c_exhaustion_anchor_alive_but_collect_more_inputs`

## Current Rejected Branches

The following are not approved:

- fixed MFE giveback exit
- selective MFE path decay exit
- direct regime filter using the current `EXHAUSTED` label
- direct cost robustness filter
- direct signal-state filter without richer input context

## Diagnostic Summary

- diagnostic commit: `b14e8ce7c95bf270661fe4d044027f143197535a`
- report path: `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RECENT_DECAY_SIGNAL_REGIME_ATTRIBUTION_DIAGNOSTIC.md`
- primary degradation label: `mixed_degradation_no_single_driver`
- stop/go label: `keep_research_anchor_alive_but_collect_more_inputs`
- signal-state attribution available: yes
- regime attribution available: yes
- cost sensitivity available: yes
- key conclusion: mixed distributional decay

## Tail-Distribution Interpretation

Tail-win compression means the historical positive tail weakened or disappeared.
Tail-loss expansion means downside events became more damaging or more frequent.
Taken together, those effects imply that the entry context or market microstructure around the signal changed.
That is upstream of exits and cannot be repaired by simple MFE giveback protection.

## Missing-Input Inventory

### A. Existing but Needs Verification

- entry signal state
- bar size
- horizon
- MTF alignment
- range/trend labels
- volatility labels
- MFE/MAE
- gross/net returns
- exit class
- year/period labels

### B. Potentially Available From Current Replay Artifacts

- pre-entry volatility expansion or compression
- prior bar return path
- signal intensity or score magnitude if present
- distance from local VWAP or anchored VWAP if present
- volume / notional context if present
- prior trade density if present

### C. Missing or Incomplete Historical Inputs

- funding
- open interest
- liquidation data
- CVD / delta
- OFI
- L2 imbalance
- spread / microprice
- order book depth
- whale / large print context
- market-wide beta / BTC regime context if not already present

### D. Data Currently Unsafe or Restricted

- raw L2
- newly generated OFI
- row-level exported artifacts

## Future Collection Design

Design a future input collection / availability audit named:

`c_exhaustion_mixed_decay_input_availability_audit`

Purpose: determine which additional pre-entry or at-entry explanatory fields are already available, safely reconstructable, missing, or unsafe for historical use.

The audit must be aggregate-only.
It must not generate new trading signals.
It must not approve a strategy rule.
It must not write row-level artifacts.

## Allowed Future Audit Outputs

The future audit may report only aggregate availability and quality tables:

- field name
- source artifact
- period coverage
- historical coverage percentage
- recent coverage percentage
- missingness percentage
- timestamp safety status
- known-at-entry status
- leakage risk
- reconstruction risk
- whether field is safe for future diagnostic use
- whether field is blocked

## Forbidden Future Audit Actions

- strategy patching
- core repo modification
- threshold tuning
- parameter optimization
- ML training
- classifier creation
- raw L2 reads
- OFI generation
- row-level export
- future-return-derived feature construction
- paper/live/production approval

## Required Future Stop/Go Labels

The future audit must choose exactly one:

- proceed_to_enriched_signal_regime_decay_diagnostic_design_only
- keep_anchor_alive_but_data_insufficient
- reject_anchor_due_to_unrecoverable_missing_inputs
- blocked_due_to_missing_required_inputs

## Approved Next Action

Approved next action label: `proceed_to_c_exhaustion_mixed_decay_input_availability_audit_design_only`

Do not run the audit in this task.

## Validation

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only
