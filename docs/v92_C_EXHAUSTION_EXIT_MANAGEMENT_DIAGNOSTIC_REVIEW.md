# V9.2 C_Exhaustion Exit-Management Diagnostic Review

## Purpose

This document reviews the successful bounded MFE/MAE source-construction dry run and interprets the result as a diagnostic finding only.

It does not optimize exits, alter strategy logic, rerun backtests, train models, or approve trading use.

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

## Source Construction Result Recap

* trade_rows_loaded: 310
* bar_rows_loaded: 204124
* bar_files_read: 102
* rows_with_matched_bars: 310
* rows_without_matched_bars: 0
* unresolved_rows: 0
* interval_convention: half_open_open_time_convention
* final_return_basis: gross_return_bps
* side_basis: long-only assumed; side column absent

## Core Diagnostic Finding

All 125 losing trades reached positive MFE before ending negative. Within this bounded diagnostic, the observed losses are therefore classified as giveback_loss rather than bad_entry_loss.

* losing_trade_count: 125
* losing_trades_with_positive_mfe: 125
* losing_trades_without_positive_mfe: 0
* positive_mfe_before_loss_rate: 1.000
* giveback_loss_count: 125
* bad_entry_loss_count: 0

This does not prove the strategy is profitable.
This does not prove an exit fix exists.
It does strongly suggest the immediate failure mode is trade management and exit giveback, not entry failure.

## Classification Summary

Overall:

* bad_entry_loss: 0
* giveback_loss: 125
* weak_positive_exit: 55
* clean_winner: 130
* unresolved: 0

By year:

* 2020: 0 bad entries, 8 giveback, 1 weak positive, 12 clean winner, 0 unresolved
* 2021: 0 bad entries, 27 giveback, 16 weak positive, 39 clean winner, 0 unresolved
* 2022: 0 bad entries, 36 giveback, 13 weak positive, 34 clean winner, 0 unresolved
* 2023: 0 bad entries, 31 giveback, 15 weak positive, 27 clean winner, 0 unresolved
* 2024: 0 bad entries, 8 giveback, 4 weak positive, 14 clean winner, 0 unresolved
* 2025: 0 bad entries, 12 giveback, 3 weak positive, 1 clean winner, 0 unresolved
* 2026: 0 bad entries, 3 giveback, 3 weak positive, 3 clean winner, 0 unresolved

## 2025 / 2026 Holdout Interpretation

2025:

* 16 total trades
* 12 losing trades
* 12 giveback losses
* 0 bad-entry losses
* 3 weak-positive exits
* 1 clean winner
* interpretation: 2025 weakness is heavily giveback dominated

2026:

* 9 total trades
* 3 losing trades
* 3 giveback losses
* 0 bad-entry losses
* 3 weak-positive exits
* 3 clean winners
* interpretation: 2026 has a smaller sample, but the losing trades are still giveback losses

2025 and 2026 do not show bad-entry dominance.
The recent failure mode appears linked to failure to retain favorable excursion.
This supports exit-management research before additional entry/meta-label model exploration.

## Excursion Timing Interpretation

* 2025 avg_time_to_mfe_bars: 9.562
* 2025 median_time_to_mfe_bars: 5.500
* 2025 avg_time_from_mfe_to_exit_bars: 25.438
* 2025 median_time_from_mfe_to_exit_bars: 29.500
* 2026 avg_time_to_mfe_bars: 17.333
* 2026 median_time_to_mfe_bars: 18.000
* 2026 avg_time_from_mfe_to_exit_bars: 17.667
* 2026 median_time_from_mfe_to_exit_bars: 17.000

2025 reached MFE relatively early and then spent many bars after MFE before exit.
2026 is less extreme but still shows time after MFE before exit.
This is consistent with an exit/giveback problem, not proof of an optimized alternative exit.

## What This Supports

* Exit-management diagnostics should be prioritized.
* Entry/meta-label expansion should pause.
* More model classes are not justified by this result.
* Threshold tuning is not justified by this result.
* Future work should pre-register one exit-management diagnostic hypothesis at a time.
* The next task should remain documentation-first.

## What This Does Not Support

* No alpha approval.
* No paper trading.
* No live trading.
* No production deployment.
* No target/stop optimization.
* No exit-horizon optimization.
* No replay changes.
* No backtest reruns.
* No claim that a specific exit rule improves performance.
* No claim that MFE could have been captured live without slippage or execution degradation.
* No claim that this result survives out-of-sample exit testing.

## Risk Register

* Long-only assumption because the side column is absent.
* final_return_basis uses gross_return_bps.
* MFE/MAE is reconstructed from 750btc bars, not tick path.
* Intrabar path is unknown.
* No row-level logistic kept/skipped source yet.
* This is descriptive, not causal.
* This could overstate achievable capture because MFE is a hindsight peak excursion.
* Any exit rule built from MFE risks lookahead if not pre-registered carefully.
* 2026 sample size is small.
* No execution or slippage simulation was run.

## Stop / Go Assessment

Pause additional Gate 3 entry/meta-label modeling.

Proceed only to an exit-management hypothesis pre-registration.

Do not proceed to:

* threshold tuning
* random forest
* XGBoost
* new features
* paper/live trading
* target/stop optimization
* exit optimization

## Approved Next Task

Create a documentation-only exit-management hypothesis pre-registration.

This pre-registration should define one bounded, non-optimized future diagnostic hypothesis, for example:

* fixed earlier review checkpoint after MFE timing
* fixed giveback warning threshold
* fixed max-hold diagnostic bucket
* fixed post-MFE decay bucket

The next task must still not run a backtest or optimize parameters. It should only pre-register the hypothesis and guardrails.

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

## Decision

Decision must be:

proceed_to_exit_management_hypothesis_preregistration_only

Decision wording:

The C_Exhaustion MFE/MAE diagnostic shows that losses are giveback-dominated rather than bad-entry-dominated. This supports exit-management hypothesis pre-registration, but not optimization, backtesting, paper/live trading, or production approval.

## Decision Labels

* c_exhaustion_exit_management_diagnostic_review_created
* documentation_only
* giveback_dominated_failure_mode
* pause_entry_meta_label_modeling
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
* proceed_to_exit_management_hypothesis_preregistration_only
