# V9.2 C_Exhaustion Exit-Management Hypothesis Pre-Registration

## Purpose

This document pre-registers one bounded future exit-management diagnostic hypothesis.
It does not run a diagnostic, optimize exits, alter strategy logic, rerun backtests, train models, or approve trading use.

## Current Gate Status

* Gate 3 logistic model dry run: pass
* Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
* Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
* Gate 3 exit/giveback diagnostic pre-registration: proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist
* Gate 3 exit/giveback source availability audit: source_missing_reconstruction_requires_separate_preregistration
* Gate 3 MFE/MAE source pre-registration: proceed_to_bounded_mfe_mae_source_construction_dry_run_only
* Gate 3 source-remediation pre-registration: proceed_to_source_remediation_alignment_diagnostic_only
* Gate 3 source-alignment diagnostic: source_alignment_diagnostic_pass
* Gate 3 MFE/MAE source construction dry run: bounded_mfe_mae_source_construction_pass
* Gate 3 exit-management diagnostic review: proceed_to_exit_management_hypothesis_preregistration_only
* Gate 4: not started
* Alpha is not approved
* Paper/live trading remains blocked
* Full reconstruction remains blocked

## Safety Boundary

* No exit optimization is performed.
* No target/stop tuning is performed.
* No threshold tuning is performed.
* No model is trained.
* No model is refit.
* No scaler is refit.
* No strategy backtest is run.
* No strategy/replay logic is changed.
* No raw L2 data is read.
* No OFI artifacts are read or written.
* No row-level artifacts are written.
* No feature-table artifacts are written.
* No model artifacts are written.
* No paper/live trading is approved.
* No production approval is given.
* Alpha is not approved.
* Full reconstruction remains blocked.

## Diagnostic Motivation

The successful MFE/MAE source-construction dry run found that all 125 losing trades had positive MFE before ending negative.
The immediate failure mode appears to be exit giveback / trade management, not bad entries.

* losing_trade_count: 125
* losing_trades_with_positive_mfe: 125
* losing_trades_without_positive_mfe: 0
* positive_mfe_before_loss_rate: 1.000
* giveback_loss_count: 125
* bad_entry_loss_count: 0

## Single Pre-Registered Hypothesis

Fixed post-MFE review-window hypothesis:

C_Exhaustion should be diagnostically reviewed under a fixed post-MFE window because many losing trades reached favorable excursion and then spent a long period after MFE before final exit.

This is not a proposed trading rule.
This is not an optimized exit.
This is not a target/stop change.
This is only a future descriptive diagnostic hypothesis.

## Fixed Diagnostic Parameters

* Review window anchor: the first bar where the trade reaches MFE.
* Review window length: 12 bars after MFE.
* Holdout years must be reported separately: 2025 and 2026.
* Train/validation/holdout years must not be pooled to hide bad years.
* Weak-positive threshold remains fixed at 50% giveback of MFE if used.
* No parameter search is allowed.
* No selection of review window based on performance is allowed.
* No alternative window lengths are allowed in the first diagnostic.

Rationale:

* 2025 median time_to_mfe_bars was 5.500 and median time_from_mfe_to_exit_bars was 29.500.
* 2026 median time_to_mfe_bars was 18.000 and median time_from_mfe_to_exit_bars was 17.000.
* A fixed 12-bar post-MFE review window is intentionally conservative and pre-registered, not optimized.

## Future Diagnostic Questions

1. For giveback_loss trades, what was the return 12 bars after MFE?
2. How many giveback_loss trades had already lost more than 50% of MFE by MFE+12 bars?
3. How many giveback_loss trades were still profitable at MFE+12 bars?
4. How many weak_positive_exit trades showed similar post-MFE decay by MFE+12 bars?
5. Does 2025 show worse post-MFE decay than 2026?
6. Does the post-MFE review window identify a descriptive risk pattern without changing exits?
7. Does the result support a future separately pre-registered exit-management experiment?
8. Does the result instead show that MFE is too late or too unstable to be useful?

## Allowed Future Inputs

Allowed future inputs for the separately approved diagnostic:

* Existing trade log:
  /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv

* Existing bounded 750btc bars:
  /home/tokio/tm-trading-v92-phase1f/bars_750btc

* Existing source-construction script:
  scripts/dry_run_c_exhaustion_mfe_mae_source_construction.py

* Existing source-construction Markdown report:
  docs/v92_C_EXHAUSTION_MFE_MAE_SOURCE_CONSTRUCTION_DRY_RUN.md

Forbidden future inputs:

* raw L2
* OFI artifacts
* packet tables
* newly reconstructed L2 features
* production systems
* paper/live systems

## Future Allowed Outputs

Allowed:

* Markdown report only
* aggregate tables in Markdown
* no persisted row-level CSV/parquet/json
* no model files
* no feature-table artifacts
* no prediction artifacts

If row-level diagnostic values must be inspected, they must remain in memory and be summarized only.

## Future Forbidden Computations

* No exit optimization.
* No target/stop tuning.
* No threshold tuning.
* No strategy backtest.
* No model training.
* No model refit.
* No feature fishing.
* No L2/OFI feature generation.
* No full reconstruction.
* No paper/live simulation.
* No production approval.
* No alpha approval.
* No replay logic changes.
* No selecting review-window length based on performance.
* No comparing multiple post-MFE windows in the first diagnostic.

## Leakage / Bias Controls

* Use existing trade intervals only.
* Do not change entry or exit timestamps.
* Do not search alternative exits.
* Do not choose parameters from holdout.
* Do not discard bad years.
* Report 2025 and 2026 separately.
* Report all years individually.
* Treat MFE as hindsight diagnostic information, not live-tradable signal.
* Report whether MFE+12 occurs before exit; if not, mark row as insufficient post-MFE window.
* Report missing or unresolved rows.
* Treat all findings as descriptive diagnostics only.

## Required Future Diagnostic Output

A future diagnostic report, if separately approved, must include:

* number of trades inspected
* number of giveback_loss trades inspected
* number of weak_positive_exit trades inspected
* number of rows with MFE+12 available before exit
* number of rows where MFE+12 is unavailable before exit
* by-year MFE+12 availability
* by-year average return at MFE+12
* by-year median return at MFE+12
* by-year percentage of giveback_loss trades still positive at MFE+12
* by-year percentage of giveback_loss trades that had lost more than 50% of MFE by MFE+12
* 2025 vs 2026 comparison
* limitations and missing data
* decision on whether to preregister a future exit experiment

## Stop / Go Criteria After Future Diagnostic

Stop or pause if:

* MFE+12 is unavailable for most recent trades.
* Post-MFE decay does not appear before the original exit.
* The signal is inconsistent across years.
* The diagnostic only looks good after excluding bad years.
* Any next step would require tuning the review window or holdout-based parameter selection.

Continue only if:

* The diagnostic yields a non-leaky, separately pre-registerable future exit experiment.
* The proposed future experiment uses fixed parameters.
* The proposed future experiment does not change holdout protocol.
* The next task remains documentation-first.

## Approved Next Implementation Task

Run the fixed post-MFE review-window diagnostic as a bounded descriptive audit, Markdown-only, using the fixed MFE+12 window and no optimization.

This next task must still be separately approved before execution.

## Explicitly Not Approved

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
* No trading approval from MFE hindsight.
* No review-window optimization.

## Decision

Decision must be:

proceed_to_fixed_post_mfe_review_window_diagnostic_only

Decision wording:

The next approved move is a bounded descriptive diagnostic of a fixed 12-bar post-MFE review window. This is not an optimized exit rule, not a backtest, and not a trading approval.

## Decision Labels

* c_exhaustion_exit_management_hypothesis_preregistration_created
* documentation_only
* single_hypothesis_only
* fixed_post_mfe_review_window
* mfe_plus_12_window
* no_review_window_optimization
* no_exit_optimization
* no_target_stop_tuning
* no_threshold_tuning
* no_new_model_trained
* no_strategy_backtest_run
* no_strategy_replay_changes
* no_row_level_artifacts_written
* no_feature_table_artifacts_written
* no_model_artifacts_written
* no_ofi_artifacts_written
* full_reconstruction_not_approved
* alpha_not_approved
* paper_live_blocked
* production_not_approved
* proceed_to_fixed_post_mfe_review_window_diagnostic_only
