# V9.2 Hermes Lab Bootstrap and Core Checkpoint Handover

## Purpose

* tm-trading-v92-core is now the consolidated read-only checkpoint.
* tm-trading-v92-hermes-lab is now the active research continuation repo.
* This document prevents context drift between checkpoint and lab.
* This task does not run diagnostics, backtests, optimization, model training, paper/live, or production work.

## Repository Roles

| Repository                | Role                                             | Write Policy                                    |
| ------------------------- | ------------------------------------------------ | ----------------------------------------------- |
| tm-trading-v92-core       | frozen consolidated checkpoint / evidence ledger | read-only except explicit checkpoint correction |
| tm-trading-v92-hermes-lab | active research continuation                     | new diagnostics, preregistration, experiments after guardrails |

## Core Checkpoint State To Inherit

* Gate 3 logistic model dry run: pass
* Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
* Gate 3 bounded diagnostic review: pass
* Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
* Gate 3 exit/giveback diagnostic pre-registration: proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist
* Gate 3 exit/giveback source availability audit: source_missing_reconstruction_requires_separate_preregistration
* Gate 3 MFE/MAE source pre-registration: proceed_to_bounded_mfe_mae_source_construction_dry_run_only
* Gate 3 MFE/MAE source-remediation pre-registration: proceed_to_source_remediation_alignment_diagnostic_only
* Gate 3 source-alignment diagnostic: source_alignment_diagnostic_pass
* Gate 3 MFE/MAE source construction dry run: bounded_mfe_mae_source_construction_pass
* Gate 3 exit-management diagnostic review: proceed_to_exit_management_hypothesis_preregistration_only
* Gate 3 fixed post-MFE hypothesis pre-registration: proceed_to_fixed_post_mfe_review_window_diagnostic_only
* Gate 3 fixed post-MFE MFE+12 diagnostic: fixed_post_mfe_review_window_diagnostic_partial
* Gate 4: not started
* Alpha: not approved
* Paper/live: blocked
* Production: blocked
* Full reconstruction: blocked

## Latest Core Diagnostic Findings

### MFE/MAE source construction

* trade_rows_loaded: 310
* bar_rows_loaded: 204124
* bar_files_read: 102
* rows_with_matched_bars: 310
* rows_without_matched_bars: 0
* unresolved_rows: 0
* interval_convention: half_open_open_time_convention
* final_return_basis: gross_return_bps
* side_basis: long-only assumed; side column absent

### Giveback finding

* losing_trade_count: 125
* losing_trades_with_positive_mfe: 125
* losing_trades_without_positive_mfe: 0
* positive_mfe_before_loss_rate: 1.000
* giveback_loss_count: 125
* bad_entry_loss_count: 0

### Overall classification

* bad_entry_loss: 0
* giveback_loss: 125
* weak_positive_exit: 55
* clean_winner: 130
* unresolved: 0

### Fixed MFE+12 diagnostic

* trades_inspected: 310
* giveback_loss_trades_inspected: 125
* weak_positive_exit_trades_inspected: 55
* rows_with_mfe_plus_12_available: 191
* rows_without_mfe_plus_12_available: 119
* insufficient_post_mfe_window_count: 119
* availability_rate: 61.613%
* decision: fixed_post_mfe_review_window_diagnostic_partial

### Giveback-loss MFE+12 result

* available at MFE+12: 116
* average MFE+12 return: -101.475 bps
* median MFE+12 return: -78.760 bps
* still positive at MFE+12: 6.034%
* lost more than 50% of MFE by MFE+12: 97.414%
* average MFE+12 giveback: 185.599 bps
* median MFE+12 giveback: 156.757 bps

### 2025 / 2026 MFE+12 result

2025:

* 16 total
* 12 giveback losses
* 3 weak-positive exits
* 81.250% MFE+12 availability
* 8.333% of giveback losses still positive at MFE+12
* 100.000% lost more than 50% of MFE by MFE+12
* average MFE+12 return: -92.209 bps
* median MFE+12 return: -82.413 bps

2026:

* 9 total
* 3 giveback losses
* 3 weak-positive exits
* 55.556% MFE+12 availability
* 0.000% of giveback losses still positive at MFE+12
* 100.000% lost more than 50% of MFE by MFE+12
* average MFE+12 return: -165.439 bps
* median MFE+12 return: -130.152 bps

## Active Hermes Lab Next Research Direction

The next safe continuation in Hermes Lab is not optimization. It is a documentation-only future exit-experiment pre-registration with fixed parameters.

Recommended next after this bootstrap:

docs/v92_HERMES_FIXED_EXIT_EXPERIMENT_PREREGISTRATION.md

This future preregistration should define one fixed, non-optimized exit experiment derived from the MFE+12 diagnostic. It must not run a backtest yet.

## Guardrails Carried From Core

* No alpha approval.
* No paper trading.
* No live trading.
* No production deployment.
* No full reconstruction.
* No OFI/L2 integration without separate validation.
* No additional model classes.
* No threshold tuning.
* No feature fishing.
* No target/stop optimization.
* No exit-horizon optimization.
* No backtest reruns without preregistration.
* No row-level artifact persistence unless separately approved.
* No trading approval from MFE hindsight.
* MFE is hindsight diagnostic information, not a live-tradable signal.

## Hermes Lab Allowed Work

Allowed only after explicit preregistration:

* documentation-only hypothesis preregistration
* bounded descriptive diagnostics
* fixed-parameter experiments
* source-lineage audits
* reproducibility checks
* Markdown-only summaries
* synthetic tests for scripts
* one hypothesis at a time

## Hermes Lab Blocked Work

Blocked until separately approved:

* strategy replay changes
* live/paper systems
* execution simulation
* model expansion
* threshold tuning
* optimized exits
* target/stop sweeps
* OFI/L2 feature integration
* full reconstruction
* production deployment

## Immediate Next Task After Bootstrap

Create a documentation-only fixed exit-experiment pre-registration in Hermes Lab.

Do not implement the experiment yet.

## Decision

hermes_lab_bootstrap_complete_core_checkpoint_read_only

## Decision Labels

* hermes_lab_bootstrap_created
* core_checkpoint_read_only
* active_research_moves_to_hermes_lab
* documentation_only
* no_strategy_backtest_run
* no_strategy_replay_changes
* no_exit_optimization
* no_target_stop_tuning
* no_threshold_tuning
* no_new_model_trained
* no_feature_fishing
* no_raw_l2_data_read
* no_ofi_artifacts_written
* full_reconstruction_not_approved
* alpha_not_approved
* paper_live_blocked
* production_not_approved
* proceed_to_hermes_fixed_exit_experiment_preregistration_only
