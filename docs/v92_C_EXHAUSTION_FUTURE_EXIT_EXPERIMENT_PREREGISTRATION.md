# V9.2 C_Exhaustion Future Exit Experiment Pre-Registration

## Purpose

The prior fixed post-MFE diagnostic found real post-MFE decay in C_Exhaustion trades, but MFE itself is hindsight information and therefore cannot be used directly as a live exit trigger.

This document pre-registers the next safe future exit experiment only. It does not change strategy logic, replay logic, or any existing exit behavior.

## Prior Evidence Summary

The fixed post-MFE review-window diagnostic reported:

* 310 trades loaded
* 204124 bar rows loaded
* 310 matched rows
* 0 unresolved rows
* 61.613% MFE+12 availability
* giveback-loss available count 116
* giveback-loss average MFE+12 return -101.475 bps
* giveback-loss median MFE+12 return -78.760 bps
* giveback-loss still positive at MFE+12 6.034%
* giveback-loss lost more than 50% of MFE by MFE+12 97.414%
* weak-positive available count 37
* weak-positive average MFE+12 return 64.047 bps
* weak-positive still positive at MFE+12 83.784%

Interpretation:

* Giveback-loss trades usually are not salvageable by MFE+12.
* Weak-positive exits are more salvageable, but still show substantial decay after MFE.
* The next experiment must use only live-observable information available at or before the decision bar.

## Non-Leaky Translation Requirement

Any future exit experiment must use only live-observable information available at or before the decision bar.

Explicitly forbidden inputs:

* final MFE
* future maximum high
* future minimum low
* final trade outcome
* future exit price
* future path after the decision point
* labels generated from the completed trade

The experiment must be expressible without hindsight-derived features from the completed trade path.

No OFI reconstruction is introduced or approved here; if a later task requires OFI reconstruction, it must be separately approved elsewhere.

## Pre-Registered Experiment Candidates

This document pre-registers candidate live-safe exit families. It does not select optimized values from a sweep.

### A. Fixed Post-Entry Review Clock

Description:

Enter the trade, then evaluate a fixed review clock after entry and decide whether to tighten, protect, or exit.

Live-observable inputs:

* entry_time
* elapsed bars since entry
* current close/high/low
* current unrealized return
* explicit cost assumptions

Required timestamp convention:

* decision bar must be treated as half-open safe
* future bars after the decision timestamp must not be read

Forbidden hindsight inputs:

* final MFE
* final exit price
* completed-trade labels

Pass/fail metrics:

* net expectancy after realistic costs
* profit factor
* average win / average loss
* max drawdown
* calendar-year stability

Failure modes:

* improvement only comes from a higher win rate with worse payoff ratio
* improvement is concentrated in one year
* trade count collapses

Why it is connected to the MFE+12 diagnostic:

* The fixed review clock is a live-safe analog to the observed post-MFE decay, but it does not use hindsight MFE.

### B. Live Peak-Retention / Giveback Guard

Description:

Monitor live favorable excursion from the entry and trigger a protective action if the trade gives back too much from its live peak.

Live-observable inputs:

* entry_price
* live high-water mark since entry
* current close/high/low
* live unrealized return
* explicit cost assumptions

Required timestamp convention:

* live peak tracking must only use bars observed up to the current decision bar
* decision logic must be half-open safe at the bar boundary

Forbidden hindsight inputs:

* completed-trade MFE
* future maximum high
* future exit price
* completed-trade labels

Pass/fail metrics:

* net expectancy after realistic costs
* profit factor
* average win / average loss
* max drawdown
* calendar-year stability

Failure modes:

* the guard exits too late to matter
* the guard exits too early and destroys winners
* the result only works in one year

Why it is connected to the MFE+12 diagnostic:

* The diagnostic showed that many losses had already given back most of their favorable move by MFE+12, so a live peak-retention guard is the closest non-leaky translation.

### C. Favorable-Excursion Activation Followed by Fixed Review Clock

Description:

Activate a protective review only after a minimum live favorable excursion is observed, then apply a fixed review clock.

Live-observable inputs:

* live high-water mark since entry
* current close/high/low
* elapsed bars since activation
* explicit cost assumptions

Required timestamp convention:

* activation and review timestamps must be based only on observed bars
* decision bar must be half-open safe

Forbidden hindsight inputs:

* final MFE
* future maximum high
* future exit price
* completed-trade labels

Pass/fail metrics:

* net expectancy after realistic costs
* profit factor
* average win / average loss
* max drawdown
* calendar-year stability

Failure modes:

* activation rarely occurs
* activation only happens after the trade is already effectively finished
* the rule is brittle across years

Why it is connected to the MFE+12 diagnostic:

* It preserves the idea of a review after favorable excursion without using hindsight MFE to define the review point.

### D. Time-Stop After Activation

Description:

After live favorable-excursion activation, allow only a fixed amount of time before forcing a decision.

Live-observable inputs:

* activation timestamp
* elapsed bars since activation
* current close/high/low
* explicit cost assumptions

Required timestamp convention:

* activation must be recorded from observed bars only
* time-stop checks must be half-open safe

Forbidden hindsight inputs:

* final MFE
* future exit price
* completed-trade labels

Pass/fail metrics:

* net expectancy after realistic costs
* profit factor
* average win / average loss
* max drawdown
* calendar-year stability

Failure modes:

* the time-stop is too short and truncates winners
* the time-stop is too long and does not prevent giveback
* results concentrate in one year

Why it is connected to the MFE+12 diagnostic:

* The diagnostic showed that meaningful decay can occur after favorable excursion, so a fixed post-activation time-stop is a live-safe candidate.

### E. Weak-Positive Protection Rule

Description:

If a trade becomes weak-positive under a live-observable rule, apply a protective exit or stop tightening.

Live-observable inputs:

* entry_price
* live unrealized return
* live high-water mark
* current close/high/low
* explicit cost assumptions

Required timestamp convention:

* the weak-positive state must be defined from live-observed data only
* decision bar must be half-open safe

Forbidden hindsight inputs:

* completed-trade weak-positive labels
* final MFE
* future exit price
* completed-trade labels

Pass/fail metrics:

* net expectancy after realistic costs
* profit factor
* average win / average loss
* max drawdown
* calendar-year stability

Failure modes:

* weak-positive state is too noisy to use
* protection hurts already good winners
* the improvement is not stable across years

Why it is connected to the MFE+12 diagnostic:

* Weak-positive exits still showed decay after MFE, so a live-safe protection rule is a direct non-hindsight translation of that observation.

## Required Fixed-Parameter Rule Before Any Future Test

Before any experiment is run, the selected rule must have one fixed parameter set written into this document or a successor preregistration document.

The parameter set must include:

* activation condition
* review clock
* protective-exit condition
* stop condition
* target condition
* time horizon
* cost assumptions
* bar-size scope
* sample period
* pass/fail gates

No parameter search is allowed before the first future test.
No holdout-based selection is allowed.

## Pass/Fail Gates

Any later experiment must satisfy all of the following gates:

* improve net expectancy after realistic costs
* not merely improve win rate while damaging payoff ratio
* report profit factor
* report average win / average loss
* report max drawdown
* report calendar-year stability
* separately report 2020-2023 and 2024-2026
* separately report 2025 and 2026
* compare against the existing post-regime-fix anchor
* include trade count and availability
* preserve no-leakage timestamp discipline
* fail if improvement is concentrated in one year only

If a later experiment fails any of these gates, it should be treated as non-approvable for trading use.

## Required Implementation Guardrails For Any Later Code Task

A later implementation task must include tests proving:

* no future bars are read before the decision timestamp
* decision bar is half-open interval safe
* entry price basis is explicit
* close/high/low basis is explicit
* activation cannot depend on final MFE
* unavailable review windows are counted, not silently dropped
* yearly metrics are emitted
* cost assumptions are explicit
* no row-level artifacts are written unless separately approved

## Decision

decision: `future_exit_experiment_preregistration_only`

Confirm:

* no strategy/replay logic changed
* no backtest run
* no model trained
* no thresholds tuned
* no alternative windows tested
* no execution approved
* no paper/live approved
* alpha remains blocked

## Decision Labels

* `c_exhaustion_future_exit_experiment_preregistration_created`
* `documentation_only`
* `non_leaky_translation_required`
* `fixed_parameter_set_required`
* `no_strategy_replay_changes`
* `no_backtest_run`
* `no_model_trained`
* `no_thresholds_tuned`
* `no_alternative_windows_tested`
* `no_execution_approved`
* `paper_live_blocked`
* `alpha_not_approved`
* `full_reconstruction_not_approved`
