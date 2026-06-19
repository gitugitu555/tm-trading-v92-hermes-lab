# V9.2 C_Exhaustion MFE/MAE Source Remediation Pre-Registration

## Purpose

This document pre-registers a future source-remediation investigation after the MFE/MAE source-construction dry run failed to match any trade intervals to the bounded 750btc bars.

It does not patch code, compute MFE/MAE, rerun diagnostics, optimize exits, or approve trading use.

## Current Gate Status

* Gate 3 logistic model dry run: pass
* Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
* Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
* Gate 3 exit/giveback diagnostic pre-registration: proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist
* Gate 3 exit/giveback source availability audit: source_missing_reconstruction_requires_separate_preregistration
* Gate 3 MFE/MAE source pre-registration: proceed_to_bounded_mfe_mae_source_construction_dry_run_only
* Gate 3 MFE/MAE source construction dry run: bounded_mfe_mae_source_construction_blocked
* Gate 4: not started
* Alpha is not approved
* Paper/live trading remains blocked
* Full reconstruction remains blocked

## Safety Boundary

* No MFE/MAE is computed in this task.
* No bar reconstruction is performed in this task.
* No source-construction script is patched in this task.
* No exit horizon is optimized.
* No target/stop tuning is performed.
* No threshold tuning is performed.
* No model is trained.
* No model is refit.
* No scaler is refit.
* No strategy backtest is run.
* No strategy/replay logic is changed.
* No raw L2 data is read.
* No OFI artifacts are read or written.
* No feature-table artifacts are written.
* No model artifacts are written.
* No row-level artifacts are written.
* No paper/live trading is approved.
* No production approval is given.
* Alpha is not approved.
* Full reconstruction remains blocked.

## Source-Construction Failure Being Addressed

The observed failure was:

* trade_rows_loaded: 310
* bar_rows_loaded: 204124
* bar_files_read: 102
* rows_with_matched_bars: 0
* rows_without_matched_bars: 310
* unresolved_rows: 310

Interpretation:

* The trade log and bounded bar source both exist.
* The script could read both sources.
* The failure is not absence of all bars.
* The failure is interval/bar matching.
* The failure blocks row-level MFE/MAE and giveback classification.

## Candidate Failure Modes To Investigate Later

1. Timestamp timezone mismatch between trade log and bar files.
2. Timestamp unit mismatch, for example milliseconds, microseconds, nanoseconds, or naive/aware timestamps.
3. Entry/exit interval convention mismatch.
4. Earlier audit convention mismatch:
   * signal_time = signal bar close_time
   * entry_time = entry bar open_time
   * exit_time = exit bar open_time
5. Bar matching used open_time when close_time or half-open interval semantics were required.
6. Bar date shard discovery mismatch.
7. Bar file naming or date coverage mismatch.
8. Trade indices align but timestamps do not.
9. Trade log references replay bars from a different materialized bar set.
10. Bar rows were loaded but filtered out due to strict time boundaries.
11. The script expected bar_id but only timestamps should be used, or vice versa.
12. Trade intervals are outside loaded bar time range despite apparent year coverage.
13. Duplicate or month/day shard overlap confused ordering.
14. Time parsing silently produced mismatched dtype or timezone normalization.
15. Entry/exit endpoints need inclusive/exclusive handling.

These are hypotheses only. Do not test them in this document.

## Future Source-Remediation Diagnostic Questions

1. What are the min/max signal_time, entry_time, and exit_time in the trade log?
2. What are the min/max open_time and close_time in the loaded bounded bars?
3. Do trade intervals fall inside the loaded bar time range?
4. Are trade times and bar times timezone-naive or timezone-aware?
5. Are timestamps parsed at the same unit/precision?
6. Do entry_index and exit_index map to bar_id or row positions?
7. Does entry_time match any bar open_time?
8. Does entry_time match any bar close_time?
9. Does exit_time match any bar open_time?
10. Does exit_time match any bar close_time?
11. Do intervals match under half-open convention `[entry_time, exit_time)`?
12. Do intervals match under closed convention `[entry_time, exit_time]`?
13. Do intervals match by index even when timestamp matching fails?
14. Are loaded bars from the same 750btc materialization used by the replay?
15. Is the mismatch caused by day/month shard selection?
16. Is any wrong-day fallback or missing-month fallback happening?
17. Can a safe matching convention be identified without changing trade intervals?

## Allowed Future Inputs For Source-Remediation Diagnostic

* Existing trade log:
  `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
* Existing bounded 750btc bars:
  `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
* Existing source-construction script:
  `scripts/dry_run_c_exhaustion_mfe_mae_source_construction.py`
* Existing synthetic tests:
  `tests/test_dry_run_c_exhaustion_mfe_mae_source_construction.py`
* Existing docs listed above

Forbidden future inputs:

* raw L2
* OFI artifacts
* packet tables
* newly reconstructed L2 features
* production systems
* paper/live systems

## Future Allowed Diagnostics

Allowed in the future source-remediation diagnostic, if separately approved:

* print/report timestamp min/max ranges
* report timestamp dtypes/timezones
* report matching rates for entry_time against open_time and close_time
* report matching rates for exit_time against open_time and close_time
* report interval overlap counts under fixed matching conventions
* report index-based mapping feasibility without computing MFE/MAE
* report shard coverage by date/month
* report whether a safe convention exists

Forbidden in that future diagnostic:

* computing MFE/MAE
* classifying giveback
* changing exits
* changing entries
* optimizing horizons
* running a backtest
* training models
* writing row-level data artifacts
* adding OFI/L2
* approving alpha

## Required Future Output

A future source-remediation diagnostic report, if separately approved, must be Markdown-only and include:

* trade log timestamp range
* bar timestamp range
* timestamp dtype/timezone audit
* precision/unit audit
* index mapping audit
* open_time match rate
* close_time match rate
* interval overlap count under fixed conventions
* shard coverage audit
* candidate root cause
* safe matching convention if one exists
* unresolved blockers
* decision on whether MFE/MAE source construction can be retried

## Stop / Go Criteria After Future Source-Remediation Diagnostic

Stop or pause if:

* trade intervals are not from the same bar materialization
* safe timestamp/index mapping cannot be established
* any solution requires changing trade intervals
* any solution requires rerunning strategy replay
* any solution requires backtest or optimization
* any solution requires raw L2 or OFI artifacts
* any next step would tune around holdout behavior

Continue only if:

* a safe fixed matching convention is identified
* no trade intervals are changed
* no exit logic is altered
* no optimization is performed
* the next source-construction rerun remains bounded, descriptive, and Markdown-only

## Approved Next Implementation Task

Recommend exactly one next task.

Recommended:

Run a bounded source-remediation diagnostic that audits timestamp, index, and bar-shard alignment only, writes a Markdown report, and does not compute MFE/MAE or classify trades.

This next task must still be separately approved before execution.

## Explicitly Not Approved

* No MFE/MAE computation.
* No giveback classification.
* No paper trading.
* No live trading.
* No production deployment.
* No additional model classes.
* No threshold tuning.
* No feature fishing.
* No OFI/L2 integration.
* No full reconstruction.
* No claims of alpha.
* No strategy/replay changes.
* No exit-horizon optimization.
* No target/stop tuning.
* No backtest reruns.
* No row-level artifact persistence.

## Decision

Decision must be:

`proceed_to_source_remediation_alignment_diagnostic_only`

Decision wording:

The MFE/MAE dry run is blocked by a source-alignment failure. The next approved move is a bounded source-remediation alignment diagnostic that inspects timestamp, index, and bar-shard matching only, without computing MFE/MAE, classifying trades, optimizing exits, rerunning backtests, or altering replay logic.

## Decision Labels

* `c_exhaustion_mfe_mae_source_remediation_preregistration_created`
* `documentation_only`
* `no_mfe_mae_computed`
* `no_giveback_classification`
* `no_bar_reconstruction_performed`
* `no_source_script_patch`
* `no_exit_optimization`
* `no_target_stop_tuning`
* `no_threshold_tuning`
* `no_new_model_trained`
* `no_model_refit`
* `no_scaler_refit`
* `no_strategy_backtest_run`
* `no_strategy_replay_changes`
* `no_feature_table_artifacts_written`
* `no_model_artifacts_written`
* `no_row_level_artifacts_written`
* `no_ofi_artifacts_written`
* `full_reconstruction_not_approved`
* `alpha_not_approved`
* `paper_live_blocked`
* `production_not_approved`
* `proceed_to_source_remediation_alignment_diagnostic_only`
