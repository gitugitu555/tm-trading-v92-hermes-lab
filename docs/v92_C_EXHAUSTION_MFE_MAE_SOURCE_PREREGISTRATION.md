# V9.2 C_Exhaustion MFE/MAE Source Pre-Registration

## Purpose

This document pre-registers a future row-level MFE/MAE source construction protocol. It does not compute MFE/MAE, reconstruct bars, optimize exits, or approve trading use.

## Current Gate Status

- Gate 3 logistic model dry run: pass
- Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
- Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
- Gate 3 exit/giveback diagnostic pre-registration: proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist
- Gate 3 exit/giveback source availability audit: source_missing_reconstruction_requires_separate_preregistration
- Gate 4: not started
- Alpha is not approved.
- Paper/live trading remains blocked.
- Full reconstruction remains blocked.

## Safety Boundary

- No MFE/MAE is computed in this task.
- No bar reconstruction is performed in this task.
- No exit horizon is optimized.
- No target/stop tuning is performed.
- No threshold tuning is performed.
- No model is trained.
- No model is refit.
- No scaler is refit.
- No strategy backtest is run.
- No strategy/replay logic is changed.
- No raw L2 data is read.
- No OFI artifacts are read or written.
- No feature-table artifacts are written.
- No model artifacts are written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Source Gap Being Addressed

The source-availability audit found that row-level MFE/MAE, positive-MFE-before-loss, giveback magnitude, time-to-MFE, time-from-MFE-to-exit, and intra-trade high/low are not available as committed approved outputs.

Existing scripts can compute these from bars, but using them would reconstruct missing row-level excursion data and therefore requires separate preregistration before execution.

## Future Diagnostic Objective

Create a bounded, read-only, row-level C_Exhaustion excursion diagnostic table in memory or Markdown summary only, using the existing trade log and bounded 750btc bars, to classify trades into `bad_entry_loss`, `giveback_loss`, `weak_positive_exit`, `clean_winner`, or `unresolved`.

Important:

- The future task is descriptive only.
- It must not change trades, exits, labels, or thresholds.

## Allowed Future Inputs

Allowed future inputs for the separately approved descriptive audit:

- Existing trade log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Existing bounded 750btc bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Existing committed reports:
  - `docs/v92_C_EXHAUSTION_EXIT_GIVEBACK_SOURCE_AVAILABILITY_AUDIT.md`
  - `docs/v92_C_EXHAUSTION_EXIT_GIVEBACK_DIAGNOSTIC_PREREGISTRATION.md`
  - `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md`
  - `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md`
  - `docs/v92_C_EXHAUSTION_EXIT_TIMING_DIAGNOSTICS.md`

Forbidden future inputs:

- Raw L2
- OFI artifacts
- Packet tables
- Newly reconstructed L2 features
- Live/paper systems
- Production systems

## Future Reconstruction Boundary

This is not full reconstruction.
This is not L2 reconstruction.
This is not OFI reconstruction.
This is not strategy replay.
This is not target/stop optimization.
This is a bounded descriptive reconstruction of intra-trade OHLC path from already approved 750btc bars for existing C_Exhaustion trade intervals only.

## Future Row-Level Fields To Derive

Identity / audit:

- `signal_index`
- `entry_index`
- `exit_index`
- `signal_time`
- `entry_time`
- `exit_time`
- `year`

Existing trade result:

- `entry_price`
- `exit_price`
- `net_return_bps`
- `gross_return_bps` if available
- `holding_bars`

Excursion fields:

- `max_favorable_price`
- `max_adverse_price`
- `mfe_bps`
- `mae_bps`
- `time_to_mfe_bars`
- `time_to_mae_bars`
- `mfe_giveback_bps`
- `final_return_bps`
- `positive_mfe_before_loss`
- `excursion_class`

Optional if safely derivable:

- `time_from_mfe_to_exit_bars`
- `peak_to_exit_return_bps`
- `intra_trade_bar_count`

## Future Classification Definitions

Use the existing preregistered classification framework:

- `bad_entry_loss`: trade never reached positive excursion before loss
- `giveback_loss`: trade reached positive excursion but exited negative
- `weak_positive_exit`: trade exited positive but gave back most of its peak excursion
- `clean_winner`: trade reached favorable excursion and exited profitably without major giveback
- `unresolved`: insufficient diagnostic information

Do not assign these labels now. Only pre-register definitions.

Suggested fixed threshold for `weak_positive_exit` if needed:

- `weak_positive_exit` if `final_return_bps > 0` and `mfe_giveback_bps >= 50% of mfe_bps`

Do not tune this threshold.

## Future Diagnostic Questions

Pre-register exact future questions:

1. Among 2025/2026 losing trades, how many are `giveback_loss` versus `bad_entry_loss`?
2. Among logistic-kept 2025/2026 losing trades, how many are `giveback_loss`?
3. Among 2026 kept losers, did positive MFE occur before final loss?
4. Did 2026 worsen because kept trades were bad entries or because profitable excursions reversed?
5. Do winners reach MFE early enough that the fixed exit horizon may be too long?
6. Is giveback concentrated in 2026?
7. Is giveback concentrated among logistic-kept trades?
8. Does the result suggest exit-management research before further meta-label models?

## Future Allowed Outputs

Allowed:

- Markdown report only
- Aggregate tables in Markdown
- No persisted row-level CSV/parquet/json unless separately approved
- No model files
- No feature-table artifacts
- No prediction artifacts

If row-level data must be inspected, it must remain in memory and be summarized only.

## Future Forbidden Computations

- No exit optimization.
- No target/stop tuning.
- No strategy backtest.
- No model training.
- No threshold tuning.
- No feature fishing.
- No L2/OFI feature generation.
- No full reconstruction.
- No paper/live simulation.
- No production approval.
- No alpha approval.
- No replay logic changes.

## Leakage / Bias Controls

- Use existing trade intervals only.
- Do not change entry or exit timestamps.
- Do not search alternative exits.
- Do not choose thresholds from holdout.
- Do not discard bad years.
- Report 2025 and 2026 separately.
- Report kept and skipped trades separately if logistic decisions are reconstructable safely.
- Report missing/unresolved rows.
- Treat all findings as descriptive diagnostics only.

## Stop / Go Rules After Future Audit

Stop or pause further Gate 3 modeling if:

- Most 2025/2026 losses are `giveback_loss`.
- Logistic-kept 2026 losers are mostly `giveback_loss`.
- MFE/MAE reconstruction cannot be performed safely without new replay/backtest logic.
- The diagnostic suggests exit management, not entry classification, is the main failure mode.
- Any next step would require holdout tuning.

Continue only if:

- The diagnostic produces a pre-registerable non-leaky next hypothesis.
- The next hypothesis can be tested without retuning holdout.
- The next task remains bounded and separately approved.

## Approved Next Implementation Task

Run a bounded descriptive MFE/MAE source-construction dry run that reads only the existing trade log and bounded 750btc bars, computes row-level excursion diagnostics in memory, writes only a Markdown report, and does not optimize exits, rerun backtests, train models, or write row-level artifacts.

This next task must still be separately approved before execution.

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
- No target/stop tuning.
- No backtest reruns.
- No row-level artifact persistence.

## Decision

Decision: `proceed_to_bounded_mfe_mae_source_construction_dry_run_only`

The source gap can be addressed only by a separately approved bounded MFE/MAE source-construction dry run that reads existing trade intervals and bounded 750btc bars for descriptive row-level excursion diagnostics, without optimization, backtesting, artifact persistence, or trading approval.

## Decision Labels

- `c_exhaustion_mfe_mae_source_preregistration_created`
- `documentation_only`
- `no_mfe_mae_computed`
- `no_bar_reconstruction_performed`
- `no_exit_optimization`
- `no_target_stop_tuning`
- `no_threshold_tuning`
- `no_new_model_trained`
- `no_model_refit`
- `no_scaler_refit`
- `no_strategy_backtest_run`
- `no_strategy_replay_changes`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_ofi_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `production_not_approved`
- `proceed_to_bounded_mfe_mae_source_construction_dry_run_only`
