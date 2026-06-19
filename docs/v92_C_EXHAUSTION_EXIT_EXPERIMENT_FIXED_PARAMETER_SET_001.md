# V9.2 C_Exhaustion Exit Experiment Fixed Parameter Set 001

## Purpose

This document freezes exactly one live-safe exit experiment parameter set before any implementation or testing.

The selected family is the live peak-retention / giveback guard. This is a documentation-only preregistration and does not change strategy logic, replay logic, or any existing exit behavior.

## Fixed Parameter Set

Experiment name:

`C_EXHAUSTION_EXIT_PARAM_SET_001_LIVE_PEAK_RETENTION_GUARD`

Frozen parameters:

* Symbol: BTCUSDT
* Bar size: 750 BTC bars only
* Direction basis: long-only, because the side column is absent in the current trade log
* Entry logic: unchanged from existing post-regime-fix C_Exhaustion replay anchor
* Baseline comparison: existing post-regime-fix C_Exhaustion anchor
* Horizon: preserve existing 36-bar horizon
* Original stop/target: preserve existing baseline stop/target geometry
* Decision timing: completed bar close only
* Timestamp convention: half-open open-time convention
* Price basis:
  * entry price: existing trade-log `entry_price`
  * live peak return: completed-bar high relative to `entry_price`
  * decision return: completed-bar close relative to `entry_price`
* Activation condition:
  * activate protection only after `live_peak_return_bps >= +50.0 bps`
* Protective exit condition:
  * after activation, exit on a completed bar close if `close_return_bps <= 0.50 * live_peak_return_bps`
* Protective exit execution basis:
  * diagnostic simulation should use the same completed-bar close that triggered the protective condition unless a later implementation document explicitly requires next-bar execution testing
* No intrabar lookahead:
  * high/low/close from a bar may only be used after that bar is complete
* No hindsight MFE:
  * final MFE is forbidden
  * future highs are forbidden
  * future lows are forbidden
  * final outcome is forbidden
  * completed-trade labels are forbidden
  * future path after the decision bar is forbidden
* Cost reporting:
  * report gross return
  * report net return under a fixed cost stress ladder of 1, 2, 3, 5, 8, and 12 bps
  * primary conservative gate should include the 12 bps stress case
* Required split reporting:
  * full sample
  * 2020-2023
  * 2024-2026
  * 2025
  * 2026
* Required metrics:
  * trade count
  * activation count
  * protective exit count
  * unchanged exit count
  * win rate
  * gross expectancy bps
  * net expectancy bps at each cost level
  * profit factor
  * average win
  * average loss
  * payoff ratio
  * max drawdown
  * calendar-year stability
  * comparison against existing post-regime-fix anchor

## Why This Set Is Connected To The Fixed MFE+12 Diagnostic

The prior diagnostic showed giveback-loss trades were rarely still positive at MFE+12.
The prior diagnostic showed most giveback-loss trades had lost more than 50% of MFE by MFE+12.
The new rule does not use hindsight MFE.
The new rule translates the insight into a live-observable peak-retention guard.

## Required Fixed-Parameter Rule Before Any Future Test

Before any experiment is run, this exact parameter set must remain fixed in this document or a successor preregistration document.

The parameter set includes:

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
No threshold sweep is allowed.
No alternative windows are allowed.
No holdout-based selection is allowed.

## Pass/Fail Gates

Any later experiment using this parameter set must satisfy all of the following gates:

* must improve net expectancy after realistic costs
* must not merely improve win rate while damaging payoff ratio
* must report profit factor
* must report average win / average loss
* must report max drawdown
* must report calendar-year stability
* must separately report 2020-2023 and 2024-2026
* must separately report 2025 and 2026
* must compare against the existing post-regime-fix anchor
* must include trade count and availability
* must preserve no-leakage timestamp discipline
* must fail if improvement is concentrated in one year only
* must fail if 2025/2026 remain structurally poor
* must fail if trade count or activation count is too small to be meaningful
* must fail if unavailable windows or unmatched bars are silently dropped

If a later experiment fails any of these gates, it is not approved for trading use.

## Required Later Implementation Tests

A later implementation task must include tests proving:

* no future bars are read before the decision timestamp
* activation cannot depend on final MFE
* live peak uses only completed bars
* protective exit uses only completed bars
* half-open interval convention is preserved
* entry price basis is explicit
* high/close basis is explicit
* unavailable bars are counted, not silently dropped
* yearly metrics are emitted
* cost assumptions are explicit
* no row-level artifacts are written unless separately approved

## Decision

decision: `fixed_parameter_set_001_preregistered_only`

Confirm:

* no strategy/replay logic changed
* no backtest run
* no exit experiment run
* no model trained
* no thresholds tuned
* no alternative windows tested
* no execution approved
* no paper/live approved
* alpha remains blocked
* full reconstruction remains blocked
* OFI reconstruction remains blocked unless separately approved elsewhere

## Decision Labels

* `c_exhaustion_exit_experiment_fixed_parameter_set_001_created`
* `documentation_only`
* `fixed_parameter_set_001_preregistered_only`
* `no_strategy_replay_changes`
* `no_backtest_run`
* `no_exit_experiment_run`
* `no_model_trained`
* `no_thresholds_tuned`
* `no_alternative_windows_tested`
* `no_execution_approved`
* `paper_live_blocked`
* `alpha_not_approved`
* `full_reconstruction_not_approved`
* `ofi_reconstruction_blocked_unless_separately_approved_elsewhere`
