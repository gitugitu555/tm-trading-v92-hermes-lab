# V9.2 C_Exhaustion Exit Param Set 001 Review / Decision

## Purpose

This document closes out the fixed-parameter exit diagnostic for `C_EXHAUSTION_EXIT_PARAM_SET_001_LIVE_PEAK_RETENTION_GUARD_DIAGNOSTIC`.
It summarizes the failed review result and records the decision for this specific parameter set only.

This is documentation only.
It does not change strategy logic, replay logic, or diagnostic logic.
It does not run a new backtest.
It does not run a new diagnostic.
It does not train a model.
It does not optimize parameters.
It does not approve trading use.

## Source State

* Commit: `711878dfcd5b504e11c219dc0c9ace58156de6a3`
* Script: `scripts/diagnose_c_exhaustion_exit_param_set_001.py`
* Test file: `tests/test_diagnose_c_exhaustion_exit_param_set_001.py`
* Diagnostic doc: `docs/v92_C_EXHAUSTION_EXIT_PARAM_SET_001_DIAGNOSTIC.md`
* Tests: `368 passed, 11 warnings`
* git status after push: clean

## Diagnostic Rule

* Rule name: `C_EXHAUSTION_EXIT_PARAM_SET_001_LIVE_PEAK_RETENTION_GUARD`
* Activation after `live_peak_return_bps >= +50.0 bps`
* Protective diagnostic exit when `close_return_bps <= 0.50 * live_peak_return_bps`
* Completed-bar high and completed-bar close only
* Same-bar close diagnostic basis only
* Long-only assumption because side column is absent
* 750 BTC bars only
* No final MFE
* No future high
* No future low
* No completed-trade labels

## Result Summary

* Decision: `fixed_param_set_001_diagnostic_failed`
* `trade_rows_loaded`: `310`
* `bar_rows_loaded`: `204124`
* `bar_files_read`: `102`
* `rows_with_matched_bars`: `310`
* `unresolved_rows`: `0`
* `activation_count`: `249`
* `activation_rate`: `80.323%`
* `protective_exit_count`: `220`
* `protective_exit_rate`: `70.968%`
* `unchanged_exit_count`: `90`
* `unavailable_count`: `0`
* `unmatched_count`: `0`

## Performance Comparison

### Full Sample

* Original win rate: `0.597`
* Diagnostic win rate: `0.706`
* Original gross expectancy: `56.003 bps`
* Diagnostic gross expectancy: `26.768 bps`
* Gross expectancy delta: `-29.235 bps`
* Original profit factor: `1.929`
* Diagnostic profit factor: `1.899`
* Original average win: `194.865 bps`
* Diagnostic average win: `80.047 bps`
* Original average loss: `-149.513 bps`
* Diagnostic average loss: `-101.451 bps`
* Original payoff ratio: `1.303`
* Diagnostic payoff ratio: `0.789`
* Original max drawdown: `23.905%`
* Diagnostic max drawdown: `12.444%`

### 12 bps Stress

* Original net expectancy: `44.003 bps`
* Diagnostic net expectancy: `14.768 bps`

## Interpretation

1. The rule improved win rate but damaged expectancy.
2. The rule reduced average loss but crushed average win more severely.
3. The rule damaged payoff ratio from `1.303` to `0.789`.
4. The rule reduced max drawdown, but that reduction is not sufficient because expectancy and payoff geometry deteriorated.
5. The failure was meaningful because activation count was high enough to matter.
6. The failure was not caused by unresolved rows or dropped trades.
7. The result is consistent with premature winner truncation.
8. This should be treated as evidence against this specific fixed parameter set, not as proof that C_Exhaustion alpha is dead.
9. 2025 and 2026 remain structurally poor after the fixed rule.
10. Paper/live remains blocked.

High win rate alone is not a valid objective.
Expectancy, payoff ratio, profit factor, and stability dominate win-rate cosmetics.
high win rate alone is not a valid objective

## Closure Decision

decision: `fixed_param_set_001_retired_failed_no_variant_tuning`

## Closure Notes

* Do not test immediate nearby variants of the same guard as an optimization sweep.
* Do not test `40%`, `60%`, `30 bps`, `80 bps`, or alternate windows as a direct continuation.
* Any future exit experiment requires a new preregistration.
* The next safer research direction is non-parametric failure attribution, especially separating entry/regime degradation from exit decay.

## Required Confirmations

* no strategy/replay logic changed
* no diagnostic logic changed
* no backtest run
* no_new_diagnostic_run
* no new diagnostic run
* no model trained
* no_thresholds_tuned
* no thresholds tuned
* no alternative thresholds tested
* no alternative windows tested
* no row-level artifacts written
* no feature-table artifacts written
* no model artifacts written
* no OFI artifacts written
* not paper/live executable
* alpha remains blocked
* full reconstruction remains blocked
* OFI reconstruction remains blocked unless separately approved elsewhere

no_new_diagnostic_run
no_thresholds_tuned
