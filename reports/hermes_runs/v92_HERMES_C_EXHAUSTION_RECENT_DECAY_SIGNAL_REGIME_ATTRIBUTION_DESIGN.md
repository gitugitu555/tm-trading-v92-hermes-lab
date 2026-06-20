# V92 Hermes C Exhaustion Recent Decay Signal Regime Attribution Design

## Executive Purpose

Design a future diagnostic to determine whether recent C Exhaustion degradation is caused by:

- signal decay
- regime mismatch
- entry selection failure
- tail-win compression
- tail-loss expansion
- cost sensitivity
- year-specific concentration
- interaction between signal state and market regime

## Background

C Exhaustion remains research-valid historically.
Recent-period performance degraded materially.
MFE exit-only repair was rejected.
Fixed MFE giveback rule was net destructive.
Selective MFE path decay rule was also rejected.
Therefore the next research step must move upstream from exits to signal, regime, and entry attribution.

## Binding Research Questions

The future diagnostic must answer:

A. Did the C Exhaustion signal itself decay?

B. Did the edge persist only in specific historical regimes?

C. Did recent trades enter in weaker signal states than historical winners?

D. Did recent performance degrade because large positive tails disappeared?

E. Did recent performance degrade because downside tails expanded?

F. Did costs turn a small gross edge into a net-negative edge?

G. Is degradation concentrated in a single year or spread across the recent period?

H. Are there specific signal/regime combinations that remain viable descriptively?

## Allowed Inputs for Future Diagnostic

Use only already existing replay/lab/core-derived aggregate inputs if available:

- trade entry timestamp
- trade year
- bar size
- horizon
- side if safely available
- entry signal state
- original return bps
- net return bps if available
- gross return bps if available
- MFE / MAE if already present
- exit class if already present
- regime labels if already present
- volatility/range/trend labels if already present
- MTF alignment labels if already present
- costs already used in prior reports
- prior C Exhaustion replay output
- prior C Exhaustion decay diagnostic output
- prior signal state attribution output

Forbidden inputs:

- raw L2
- newly generated OFI
- future path data for feature eligibility
- new labels derived from future returns except for aggregate post-hoc outcome buckets
- external discretionary/manual classifications
- row-level exported artifacts

## Required Future Aggregate Diagnostics

The future diagnostic must produce aggregate-only outputs.

### A. Period Comparison

Use only period definitions already established in prior reports.
Do not invent optimized cutoffs.

Required comparison:

- historical period
- recent decay period
- by-year breakdown

Metrics:

- trade count
- win rate
- average return bps
- median return bps
- p25 return bps
- p75 return bps
- p10 return bps
- p90 return bps
- gross expectancy bps
- net expectancy bps if available
- profit factor if available
- max drawdown if already available
- positive-tail count
- large-loss count

### B. Tail Attribution

Report whether recent degradation is driven by:

- fewer large winners
- smaller average winners
- larger average losers
- more frequent large losers
- reduced hit rate
- cost drag

### C. Signal-State Attribution

For each available signal state:

- count
- historical expectancy
- recent expectancy
- historical hit rate
- recent hit rate
- tail-win frequency
- tail-loss frequency
- net degradation bps

### D. Regime Attribution

For each available regime label:

- count
- historical expectancy
- recent expectancy
- hit rate
- average winner
- average loser
- tail-win count
- tail-loss count
- net degradation bps

### E. Signal x Regime Interaction

If enough observations exist, report aggregate tables by:

- signal state
- regime label
- period

Do not fit a model.
Do not optimize.
Do not create a classifier.

### F. Cost Sensitivity Attribution

Using already established cost assumptions only, compare:

- gross return
- net return
- cost drag
- percentage of gross edge consumed by costs
- historical vs recent cost sensitivity

Do not invent new cost values unless they are preregistered fixed stress levels.

Allowed fixed cost stress levels only if not already present:

- 0 bps
- 1 bps
- 2 bps
- 3 bps
- 5 bps
- 8 bps
- 12 bps

No optimization or selection from these levels is allowed.

## Required Synthetic Causality / Leakage Checks

The future diagnostic must confirm:

- period assignment uses timestamp only
- signal state is known at entry
- regime state is known at or before entry if used
- costs are applied mechanically
- return outcomes are used only for aggregate attribution
- no future path information is used to define trade eligibility
- no row-level artifacts are exported
- raw L2 is not read
- OFI is not generated

## Required Interpretation Framework

The future diagnostic must choose one primary degradation explanation if supported:

- signal_decay_dominant
- regime_mismatch_dominant
- entry_quality_decay_dominant
- tail_win_compression_dominant
- tail_loss_expansion_dominant
- cost_sensitivity_dominant
- mixed_degradation_no_single_driver
- inconclusive_due_to_missing_inputs

## Required Stop/Go Labels

The future diagnostic must choose exactly one:

- reject_c_exhaustion_anchor_as_recently_unrepairable
- proceed_to_regime_filtered_preregistration_design_only
- proceed_to_signal_state_filter_preregistration_design_only
- proceed_to_cost_robustness_preregistration_design_only
- keep_research_anchor_alive_but_collect_more_inputs
- blocked_due_to_missing_required_inputs

## Forbidden Follow-Up Actions

- direct strategy patch
- core repo modification
- new exit variants
- threshold tuning
- regime optimization
- ML classifier training
- paper/live approval
- production approval
- raw L2 reads
- OFI generation
- row-level artifact export

## Validation

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- no tests required because Markdown-only
