# V9.2 C_Exhaustion Exit-Horizon / Giveback Diagnostic Pre-Registration

## Purpose

This document pre-registers a future diagnostic only. It does not compute the diagnostic, optimize exits, alter strategy logic, or approve trading use.

## Current Gate Status

- Gate 1 static inventory: pass
- Gate 1 schema availability: pass
- Gate 1 timestamp alignment: pass
- Gate 2 feature table dry run: pass
- Gate 2 feature contract/nullness audit: pass
- Gate 3 pre-registration: complete
- Gate 3 synthetic protocol checker: pass
- Gate 3 real-data label/split/purge dry run: pass
- Gate 3 no-training design-matrix audit: pass
- Gate 3 logistic model dry run: pass
- Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
- Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
- Gate 4: not started

## Safety Boundary

- No new model is trained.
- No model is refit.
- No scaler is refit.
- No threshold is tuned.
- No exit horizon is optimized.
- No strategy backtest is run.
- No strategy/replay logic is changed.
- No new predictive metrics are computed.
- No feature set is changed.
- No raw L2 data is read.
- No OFI artifacts are read or written.
- No feature-table artifacts are written.
- No model artifacts are written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Diagnostic Motivation

The logistic meta-label dry run improved validation and aggregate holdout versus keep-all, but holdout stayed negative and 2026 worsened versus keep-all. This suggests entry keep/skip classification alone may not solve the recent failure mode.

- 2025 improved versus keep-all but remained negative.
- 2026 worsened versus keep-all.
- Aggregate holdout improvement hides year-level instability.
- Prior C_Exhaustion evidence suggested recent losers may have had favorable excursion before giving back.

## Primary Diagnostic Question

Are recent C_Exhaustion failures, especially 2025/2026 losers, primarily caused by:

- bad entries,
- insufficient entry filtering,
- fixed-horizon giveback,
- exit delay after favorable excursion,
- regime mismatch,
- or insufficient approved features?

## Diagnostic Questions

Future diagnostic questions to answer:

1. Among 2025/2026 losing trades, how many had positive MFE before ending negative?
2. Among logistic-kept 2025/2026 losers, how many had positive MFE before ending negative?
3. Did 2026 kept losers have worse giveback than skipped losers?
4. Did winners reach favorable excursion earlier than the current exit horizon?
5. Is loss driven by bad entries that never move favorably, or by profitable excursions that later reverse?
6. Does giveback concentrate in specific years, especially 2026?
7. Does giveback concentrate in logistic-kept trades?
8. Does giveback suggest exit-management research is higher priority than more entry/meta-label models?

## Allowed Future Inputs

Allowed only if already existing/committed or separately approved:

- Existing `trade_log.csv`
- Existing replay diagnostics
- Existing signal-state diagnostics
- Existing MFE/MAE or favorable-excursion diagnostics if already generated
- Existing bar data from the bounded 750btc directory only if needed for descriptive reconstruction
- Committed docs/reports

Forbidden:

- Raw L2 data
- OFI artifacts
- New OFI reconstruction
- New feature-table artifacts
- New model artifacts
- Paper/live systems
- Production systems

## Required Future Diagnostic Output

A future diagnostic report, if separately approved, must be Markdown-only unless separately authorized.

It must report:

- Number of trades inspected
- Year coverage
- Losing trade count by year
- Logistic-kept losing trade count by year
- Skipped losing trade count by year
- Positive-MFE-before-loss count
- No-positive-MFE loss count
- Giveback magnitude distribution
- Time-to-MFE if already available
- Time-from-MFE-to-exit if already available
- 2025 vs 2026 comparison
- Kept vs skipped comparison
- Bad-entry vs giveback classification
- Limitations and missing data

## Forbidden Future Computations

- No exit optimization.
- No target/stop tuning.
- No threshold tuning.
- No new model training.
- No strategy backtest.
- No paper/live simulation.
- No feature fishing.
- No holdout retuning.
- No changing replay mechanics.
- No approving alpha.

## Diagnostic Classification Framework

Future classification labels:

- `bad_entry_loss`: trade never reached positive excursion before loss
- `giveback_loss`: trade reached positive excursion but exited negative
- `weak_positive_exit`: trade exited positive but gave back most of its peak excursion
- `clean_winner`: trade reached favorable excursion and exited profitably without major giveback
- `unresolved`: insufficient diagnostic information

Do not assign these labels now. Only pre-register definitions.

## Stop / Go Criteria After Future Diagnostic

Stop or pause modeling if:

- Most recent losses are `giveback_loss` rather than `bad_entry_loss`.
- 2026 weakness is dominated by exit/giveback behavior.
- Logistic-kept losses are mostly giveback failures.
- Required MFE/MAE data is unavailable and cannot be safely reconstructed.
- Any proposed next step requires holdout tuning.

Continue only if:

- The diagnostic yields a pre-registerable, non-leaky hypothesis.
- The hypothesis can be tested without changing holdout protocol.
- The next step does not require paper/live approval.
- The next step remains documentation-first or descriptive-only.

## Approved Next Implementation Task

Run the pre-registered exit-horizon / giveback diagnostic as a bounded descriptive audit, only if the required MFE/MAE or signal-state data already exists or can be read safely from existing approved outputs.

If required MFE/MAE data is missing, the next task must be a source-availability audit, not a reconstruction or backtest.

## Explicitly Not Approved

- No paper trading.
- No live trading.
- No production deployment.
- No additional model classes.
- No threshold tuning.
- No feature fishing.
- No OFI/L2 integration.
- No full reconstruction.
- No claims of alpha.
- No strategy/replay changes.
- No exit-horizon optimization.
- No backtest reruns.

## Decision

The next approved move is a bounded descriptive exit/giveback audit, but only after verifying that the required diagnostic inputs already exist or can be safely read without reconstruction, optimization, or backtesting.

Decision: `proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist`

## Decision Labels

- `c_exhaustion_exit_giveback_preregistration_created`
- `documentation_only`
- `no_new_model_trained`
- `no_model_refit`
- `no_scaler_refit`
- `no_threshold_tuning`
- `no_exit_optimization`
- `no_new_predictive_metrics_computed`
- `no_feature_changes`
- `no_strategy_backtest_run`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_ofi_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `production_not_approved`
- `proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist`
