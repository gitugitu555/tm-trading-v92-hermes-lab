# V9.2 C_Exhaustion Non-Parametric Failure Attribution Preregistration

## Purpose

This document preregisters a non-parametric diagnostic framework for the C_Exhaustion research line.
It is intended to determine whether recent degradation is primarily caused by entry degradation, tail opportunity decay, giveback worsening, regime mismatch, exit decay, or sample-era dependence.

This is documentation only.
It does not define a new trading rule.
This is not a trading rule.
It does not select any execution threshold.
It does not approve any future exit experiment.
It does not change strategy logic, replay logic, or diagnostic logic.
No new diagnostic run is included in this commit.
No backtest run is included in this commit.

## Current Gate Status

* Post-regime-fix C_Exhaustion anchor: established
* Fixed MFE+12 diagnostic: completed
* Param Set 001 diagnostic: failed
* Param Set 001 review / closure: complete
* Gate 4: not started
* Alpha is not approved
* Paper/live trading remains blocked
* Full reconstruction remains blocked
* Full OFI reconstruction remains blocked

## Background Evidence

### Post-Regime-Fix Anchor

* trade_count: `310`
* win_rate: `0.567742` in the canonical anchor, with report-compatible original win rate `0.597` in the latest diagnostic comparison because of basis differences
* net_expectancy_bps at 12 bps stress: approximately `44.003 bps`
* profit_factor: approximately `1.929`
* alpha remains unapproved
* paper/live remains blocked

### Fixed MFE+12 Diagnostic

* trades loaded: `310`
* bar rows loaded: `204124`
* matched rows: `310`
* unresolved rows: `0`
* MFE+12 availability: `61.613%`
* giveback-loss available count: `116`
* giveback-loss average MFE+12 return: `-101.475 bps`
* giveback-loss median MFE+12 return: `-78.760 bps`
* giveback-loss still positive at MFE+12: `6.034%`
* giveback-loss lost more than 50% of MFE by MFE+12: `97.414%`
* weak-positive available count: `37`
* weak-positive average MFE+12 return: `64.047 bps`
* weak-positive still positive at MFE+12: `83.784%`

### Param Set 001 Diagnostic Failure

* activation_count: `249`
* activation_rate: `80.323%`
* protective_exit_count: `220`
* protective_exit_rate: `70.968%`
* original win rate: `0.597`
* diagnostic win rate: `0.706`
* original gross expectancy: `56.003 bps`
* diagnostic gross expectancy: `26.768 bps`
* gross expectancy delta: `-29.235 bps`
* original 12 bps net expectancy: `44.003 bps`
* diagnostic 12 bps net expectancy: `14.768 bps`
* original average win: `194.865 bps`
* diagnostic average win: `80.047 bps`
* original average loss: `-149.513 bps`
* diagnostic average loss: `-101.451 bps`
* original payoff ratio: `1.303`
* diagnostic payoff ratio: `0.789`
* conclusion: fixed live peak-retention guard improved win rate but damaged payoff and expectancy
* result: `fixed_param_set_001_retired_failed_no_variant_tuning`

## Pre-Registered Diagnostic Families

The families below are descriptive diagnostics only.
They are not trading rules and they do not define execution thresholds.

### A. Entry Degradation

Purpose:
Determine whether recent trades fail soon after entry before any meaningful favorable excursion.

Metrics to pre-register:

* return after first completed bar
* return after third completed bar
* return after sixth completed bar
* early adverse excursion
* early favorable excursion
* percentage of trades that never reach positive territory after entry
* percentage of trades that reach `+25 bps`, `+50 bps`, `+100 bps` at any point before original exit

Clarification:
These checkpoints are descriptive diagnostics only.
They are not proposed exit windows.

### B. Tail Opportunity Decay

Purpose:
Determine whether the large positive excursions that historically paid for C_Exhaustion still exist in 2025/2026.

Metrics to pre-register:

* maximum favorable excursion distribution
* median MFE
* 75th percentile MFE
* 90th percentile MFE
* 95th percentile MFE
* percentage of trades reaching `+50 bps`
* percentage of trades reaching `+100 bps`
* percentage of trades reaching `+200 bps`
* percentage of trades reaching `+300 bps`

Clarification:
MFE is allowed here only as hindsight diagnostic information, not as a live-tradable signal.

### C. Giveback Worsening

Purpose:
Determine whether recent trades still create favorable excursions but give them back more severely.

Metrics to pre-register:

* final return minus MFE
* retained MFE ratio
* percentage of trades losing more than 25% of MFE
* percentage of trades losing more than 50% of MFE
* percentage of trades losing more than 75% of MFE
* percentage of positive-MFE trades ending negative
* median giveback by year

Clarification:
This is attribution only.
It must not propose a giveback threshold.

### D. Exit vs Entry Attribution

Purpose:
Separate trades that were poor from entry from trades that became good then decayed.

Pre-registered descriptive classes:

* no_favorable_excursion
* small_favorable_excursion_then_loss
* large_favorable_excursion_then_giveback
* weak_positive_exit
* strong_positive_exit
* immediate_adverse_path
* delayed_decay_path

These classes are diagnostic bins only.
Any numeric boundaries used to define them are descriptive reporting bins, not trading-rule thresholds.

### E. Era and Year Stability

Purpose:
Determine whether C_Exhaustion is sample-era dependent.

Required splits:

* full sample
* 2020-2023
* 2024-2026
* 2025
* 2026
* calendar year table from 2020 through 2026

Metrics:

* trade count
* win rate
* gross expectancy
* 12 bps net expectancy
* profit factor
* average win
* average loss
* payoff ratio
* max drawdown
* MFE distribution summary
* giveback distribution summary

### F. Regime / Context Attribution Using Already-Existing Fields Only

Purpose:
Determine whether degradation clusters in existing available regime or context fields without adding new features.

Rules:

* Use only fields already present in the trade log or existing report inputs.
* Do not reconstruct OFI.
* Do not create new feature tables.
* Do not add new external data.
* Do not train a classifier.
* Do not optimize regime thresholds.
* If regime or context columns are missing, report missing counts explicitly.

Metrics:

* performance by existing regime labels if present
* performance by existing signal-state labels if present
* performance by year and regime interaction if present
* missing-regime-field count if not present

## No-Leakage Rules

* Diagnostic calculations may use the final trade path only for attribution labels, never for live rule approval.
* Any future live rule must be separately preregistered.
* No final MFE can be used as a live trigger.
* No future high or low can be used as a live trigger.
* No completed-trade class can be used as a live trigger.
* No labels from completed trades can be used for live execution.

## Required Future Implementation Guardrails

A later diagnostic implementation must:

* read the existing post-regime-fix C_Exhaustion trade log only
* read the same 750 BTC bars
* preserve the half-open bar matching convention
* assume long-only trades unless a side column exists
* count unmatched rows
* count unavailable rows
* emit aggregate markdown only
* avoid row-level artifacts unless separately approved
* treat MFE/path labels as hindsight-only and not live-tradable
* require a separate preregistration before any future live rule
* include tests for timestamp discipline
* include tests that descriptive bins are not execution rules
* include tests that MFE-derived labels are marked hindsight-only
* include tests that required splits are present

## Explicitly Not Approved

* No strategy/replay logic changed
* No diagnostic logic changed
* No backtest run
* No backtest run in this commit
* no_new_diagnostic_run
* No new diagnostic run
* No new diagnostic run in this commit
* No model trained
* No thresholds tuned
* No threshold tuning
* No alternative thresholds tested
* No alternative windows tested
* No alternative exit windows
* No row-level artifacts written
* No feature-table artifacts written
* No model artifacts written
* No OFI artifacts written
* Param Set 001 remains retired
* No Param Set 001 nearby variants approved
* No Param Set 001 nearby variants are approved
* Not paper/live executable
* Paper/live remains blocked
* Alpha remains blocked
* Full reconstruction remains blocked
* OFI reconstruction remains blocked unless separately approved elsewhere
* Full OFI reconstruction remains blocked
* no_new_diagnostic_run
* no_thresholds_tuned
* alpha remains blocked

## Decision

decision: `nonparametric_failure_attribution_preregistration_only`

## Pre-Registered Later Diagnostic Decision Labels

The later diagnostic must close with exactly one of these labels:

* recent_failure_entry_degradation_dominated
* recent_failure_tail_opportunity_decay_dominated
* recent_failure_giveback_worsening_dominated
* recent_failure_regime_mismatch_dominated
* recent_failure_sample_era_dependence_dominated
* recent_failure_mixed_or_inconclusive
