# V9.2 Hermes Fixed Exit Experiment Pre-Registration

## Purpose

* This document pre-registers one fixed, live-feasible exit experiment hypothesis in Hermes Lab.
* It inherits evidence from the read-only core checkpoint.
* It does not implement the experiment.
* It does not run a backtest.
* It does not optimize exits.
* It does not approve trading.

## Repository Context

* tm-trading-v92-core is frozen/read-only.
* tm-trading-v92-hermes-lab is active research continuation.
* This pre-registration belongs only in Hermes Lab.
* Core should not be modified by this task.

## Inherited Core Evidence

### Giveback dominance

* losing_trade_count: 125
* losing_trades_with_positive_mfe: 125
* losing_trades_without_positive_mfe: 0
* positive_mfe_before_loss_rate: 1.000
* giveback_loss_count: 125
* bad_entry_loss_count: 0

### Fixed MFE+12 diagnostic

* trades_inspected: 310
* giveback_loss_trades_inspected: 125
* weak_positive_exit_trades_inspected: 55
* rows_with_mfe_plus_12_available: 191
* rows_without_mfe_plus_12_available: 119
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

### 2025 / 2026

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

## Critical Lookahead Boundary

* Final MFE is hindsight-only.
* A live exit cannot know final MFE before the original exit.
* The future experiment must use running favorable excursion observed so far.
* The experiment must not use the final MFE bar as an execution anchor.
* The future experiment must not use future highs/lows after the candidate exit point.
* Any implementation must prove bar-by-bar causality.

## Single Pre-Registered Future Experiment

Name:

fixed_running_mfe_giveback_protection_experiment

Hypothesis:

A fixed running-MFE giveback protection rule may reduce C_Exhaustion giveback losses by exiting after a trade has first achieved a minimum favorable excursion and subsequently gives back a fixed fraction of the running favorable excursion.

This is not a claim that it will improve performance.

## Fixed Parameters

* Activation threshold: running_mfe_bps >= 75 bps
* Giveback trigger: current_return_bps <= 0.50 * running_mfe_bps
* Minimum bars after entry before trigger is allowed: 12 bars
* Maximum original horizon remains unchanged for comparison
* Direction assumption: long-only unless existing side column is safely available
* Review frequency: once per completed 750btc bar
* Price basis: bar close for trigger evaluation
* Cost basis for future experiment reporting: report both gross and net if available; do not choose one based on performance
* Years must be reported separately
* 2025 and 2026 must be reported separately
* No parameter search
* No alternative activation thresholds
* No alternative giveback thresholds
* No alternative minimum-bar delays
* No holdout-based tuning

Rationale:

* 75 bps activation is a fixed, conservative favorable-excursion floor chosen before the experiment.
* 50% giveback is inherited from the existing weak-positive/giveback diagnostic convention.
* 12 bars is inherited from the fixed post-MFE diagnostic window.
* These parameters are not optimized.

## Future Experiment Questions

1. How many trades activate the running-MFE rule?
2. How many original giveback_loss trades would have triggered the fixed rule before original exit?
3. How many original clean_winner trades would have triggered the fixed rule before original exit?
4. How many original weak_positive_exit trades would have triggered the fixed rule before original exit?
5. What is the descriptive gross/net return at the fixed trigger point?
6. Does the rule reduce giveback losses descriptively without destroying clean winners?
7. Does 2025 improve descriptively under the fixed rule?
8. Does 2026 improve descriptively under the fixed rule?
9. Is the result consistent across years, or concentrated in one period?
10. Does the result justify a later formal replay/backtest pre-registration?
11. Does the result fail because activation is too rare, too late, or damaging to clean winners?

## Future Allowed Inputs

Allowed for the separately approved future experiment:

* Existing trade log:
  /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv

* Existing bounded 750btc bars:
  /home/tokio/tm-trading-v92-phase1f/bars_750btc

* Existing Hermes handover document:
  docs/v92_HERMES_LAB_BOOTSTRAP_AND_CORE_CHECKPOINT_HANDOVER.md

* Existing core-derived diagnostic documents, read-only.

Forbidden:

* raw L2
* OFI artifacts
* packet tables
* newly reconstructed L2 features
* paper/live systems
* production systems
* parameter sweeps
* optimizer outputs

## Future Allowed Outputs

Allowed:

* Markdown report only
* Aggregate tables only
* Synthetic tests for causal rule implementation
* No row-level CSV/parquet/json
* No model files
* No prediction artifacts
* No feature-table artifacts
* No OFI artifacts

## Required Future Experiment Output

If separately approved, the future experiment report must include:

* trades inspected
* activated trades
* activation rate
* trigger count
* trigger rate among activated trades
* original giveback_loss trigger count
* original weak_positive_exit trigger count
* original clean_winner trigger count
* original bad_entry_loss trigger count
* average trigger return bps
* median trigger return bps
* gross and net return summaries if available
* original outcome class transition table
* by-year results
* 2025 vs 2026 results
* clean-winner damage audit
* giveback-loss mitigation audit
* unavailable/untriggered rows
* limitations
* decision on whether a formal replay/backtest preregistration is justified

## Leakage / Bias Controls

* Use only information available up to each candidate trigger bar.
* Track running MFE bar by bar.
* Do not use final MFE.
* Do not use future highs/lows after candidate trigger.
* Do not change entry conditions.
* Do not change original signal generation.
* Do not tune parameters.
* Do not discard bad years.
* Report all years separately.
* Report 2025 and 2026 separately.
* Report clean-winner damage explicitly.
* Report activated and non-activated trades.
* Treat output as descriptive, not causal.
* Do not claim tradability.

## Stop / Go Criteria After Future Experiment

Stop or pause if:

* Activation is too rare to evaluate.
* Trigger damages many clean winners.
* Result only helps 2025 while hurting 2026.
* Result only looks good by excluding bad years.
* Result requires changing fixed parameters.
* Result requires target/stop tuning.
* Result requires holdout selection.
* Result requires full replay changes before descriptive evidence is stable.

Continue only if:

* Fixed rule is causally implementable bar by bar.
* Results are not concentrated in one favorable period.
* Clean-winner damage is explicitly bounded.
* Giveback-loss mitigation is visible under fixed parameters.
* Next step is a separate formal replay/backtest pre-registration, not immediate implementation.

## Approved Next Implementation Task

Run the fixed running-MFE giveback protection descriptive experiment in Hermes Lab, Markdown-only, using the pre-registered fixed parameters and synthetic causality tests.

This next task still requires separate approval.

Do not implement it in this pre-registration task.

## Explicitly Not Approved

* No paper trading.
* No live trading.
* No production deployment.
* No alpha claim.
* No immediate strategy deployment.
* No target/stop optimization.
* No exit-horizon optimization.
* No threshold tuning.
* No parameter sweep.
* No model expansion.
* No feature fishing.
* No OFI/L2 integration.
* No full reconstruction.
* No replay changes.
* No backtest rerun.
* No row-level artifact persistence.
* No trading approval from MFE hindsight.

## Decision

proceed_to_fixed_running_mfe_giveback_experiment_only

The next approved move is a separately approved, bounded descriptive fixed running-MFE giveback protection experiment in Hermes Lab. This pre-registration does not implement the experiment, does not run a backtest, and does not approve trading.

## Decision Labels

* hermes_fixed_exit_experiment_preregistration_created
* documentation_only
* single_experiment_only
* fixed_running_mfe_giveback_protection
* live_observable_running_mfe_only
* no_final_mfe_lookahead
* fixed_activation_75bps
* fixed_giveback_50pct
* fixed_minimum_delay_12_bars
* no_parameter_search
* no_exit_optimization
* no_target_stop_tuning
* no_threshold_tuning
* no_strategy_backtest_run
* no_strategy_replay_changes
* no_new_model_trained
* no_feature_fishing
* no_raw_l2_data_read
* no_ofi_artifacts_written
* no_row_level_artifacts_written
* full_reconstruction_not_approved
* alpha_not_approved
* paper_live_blocked
* production_not_approved
* proceed_to_fixed_running_mfe_giveback_experiment_only
