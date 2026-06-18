# V9.2 C_Exhaustion Exit/Giveback Source Availability Audit

## Purpose

This document checks whether the required inputs exist for a future descriptive exit/giveback audit. It does not compute the audit.

## Current Gate Status

- Gate 3 logistic model dry run: pass
- Gate 3 logistic review/decision: proceed_to_bounded_diagnostic_review_only
- Gate 3 diagnostic action plan: proceed_to_exit_giveback_diagnostic_preregistration_only
- Gate 3 exit/giveback diagnostic pre-registration: proceed_to_exit_giveback_descriptive_audit_only_if_inputs_exist
- Gate 4: not started
- Alpha is not approved.
- Paper/live trading remains blocked.
- Full reconstruction remains blocked.

## Safety Boundary

- No new model is trained.
- No model is refit.
- No scaler is refit.
- No threshold is tuned.
- No exit horizon is optimized.
- No strategy backtest is run.
- No strategy/replay logic is changed.
- No MFE/MAE reconstruction is performed.
- No raw L2 data is read.
- No OFI artifacts are read or written.
- No feature-table artifacts are written.
- No model artifacts are written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Required Inputs For Future Diagnostic

Required minimum:

- trade identifier or row identity
- year
- signal_time
- entry_time
- exit_time
- entry_price
- exit_price
- net_return_bps
- whether trade was logistic-kept or logistic-skipped, if available from committed dry-run outputs or recomputable only as a read-only report field

For MFE/giveback classification:

- MFE or max favorable excursion
- MAE or max adverse excursion
- intra-trade high/low or equivalent approved diagnostic
- time-to-MFE if available
- time-from-MFE-to-exit if available
- peak favorable excursion before exit
- final return

## Sources Inspected

| path | exists? | type | inspected? | relevant columns or terms found | safe for future diagnostic? | notes |
| --- | --- | --- | --- | --- | --- | --- |
| `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv` | yes | csv | yes | `signal_time`, `entry_time`, `exit_time`, `entry_price`, `exit_price`, `gross_return_bps`, `net_return_bps`, `holding_bars`, `year` | yes | Canonical row-level trade log exists. It does not contain MFE/MAE or intra-trade high/low. |
| `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md` | yes | doc | yes | train/validation/holdout split counts, logistic kept/skipped counts, keep-all vs logistic kept means | yes | Useful for logistic-kept/skipped lookup only. No row-level excursion fields. |
| `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_REVIEW_DECISION.md` | yes | doc | yes | holdout weakness, 2025 vs 2026 caution flags, conservative decision | yes | Provides decision context only. |
| `docs/v92_C_EXHAUSTION_GATE3_BOUNDED_DIAGNOSTIC_REVIEW.md` | yes | doc | yes | exit/giveback hypothesis, MFE/giveback motivation, stop/go framing | yes | Diagnostic framing only, not row-level data. |
| `docs/v92_C_EXHAUSTION_GATE3_DIAGNOSTIC_ACTION_PLAN.md` | yes | doc | yes | exit-horizon / giveback workstreams and required inputs | yes | Pre-registration only. |
| `docs/v92_C_EXHAUSTION_EXIT_GIVEBACK_DIAGNOSTIC_PREREGISTRATION.md` | yes | doc | yes | explicit MFE/MAE requirement, classification framework, input constraints | yes | Confirms the future diagnostic is only safe if inputs already exist. |
| `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md` | yes | doc | yes | aggregate `avg_mfe_bps`, `avg_mae_bps`, `time_to_mfe`, `mfe_giveback_bps`, year/month summaries | partially | Contains aggregate MFE/MAE/giveback summaries only, not row-level trade diagnostics. |
| `docs/v92_C_EXHAUSTION_EXIT_TIMING_DIAGNOSTICS.md` | yes | doc | yes | aggregate `avg_mfe_bps`, `avg_mae_bps`, `avg_time_to_mfe_bars`, `avg_mfe_giveback_bps`, recent-period summaries | partially | Contains aggregate excursion/timing evidence only, not row-level classification inputs. |
| `docs/v92_C_EXHAUSTION_EXIT_HYPOTHESIS_MATRIX.md` | yes | doc | yes | aggregate fixed-horizon, take-profit, and giveback family results | partially | Useful for hypothesis context only. No row-level MFE/MAE source. |
| `scripts/diagnose_c_exhaustion_exit_timing.py` | yes | script | yes | computes `mfe_bps`, `mae_bps`, `time_to_mfe_bars`, `time_to_mae_bars`, `mfe_giveback_bps` from bars | no | This is a computation path, not an existing approved output. Using it would require a separate preregistration because it reconstructs row-level excursion diagnostics from bars. |
| `scripts/diagnose_c_exhaustion_signal_state.py` | yes | script | yes | computes aggregate signal-state attribution with `mfe_bps` and `mae_bps` buckets | no | Same limitation: source code exists, but the row-level diagnostic outputs are not already present as approved artifacts. |

## Source Availability Matrix

| source | available_now | source_path | safe_to_read | requires_reconstruction | requires_backtest | allowed_under_current_gate | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trade_log.csv | yes | `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv` | yes | no | no | yes | Row identity and execution fields exist. |
| logistic kept/skipped decisions | yes | `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md` | yes | no | no | yes | Split-level keep/skip counts and kept means are documented. |
| MFE | no | none as row-level committed source | no | yes | no | no | Only aggregate MFE summaries exist in docs. Row-level MFE would need reconstruction from bars. |
| MAE | no | none as row-level committed source | no | yes | no | no | Only aggregate MAE summaries exist in docs. Row-level MAE would need reconstruction from bars. |
| positive-MFE-before-loss | no | none as row-level committed source | no | yes | no | no | Needs row-level MFE plus realized return classification. |
| giveback magnitude | no | none as row-level committed source | no | yes | no | no | Aggregate giveback exists in docs; per-trade giveback does not. |
| time-to-MFE | no | none as row-level committed source | no | yes | no | no | Aggregate timing exists in docs; per-trade timing does not. |
| time-from-MFE-to-exit | no | none as row-level committed source | no | yes | no | no | Not present as a committed row-level artifact. |
| intra-trade high/low | no | none as row-level committed source | no | yes | no | no | Would require bar-path reconstruction. |
| signal-state diagnostics | yes | `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md` | yes | no | no | yes | Aggregate diagnostics are committed and readable. |
| decay diagnostics | yes | `docs/v92_C_EXHAUSTION_EXIT_TIMING_DIAGNOSTICS.md`, `docs/v92_C_EXHAUSTION_RECENT_DECAY_DIAGNOSTICS.md` | yes | no | no | yes | Aggregate decay evidence is committed and readable. |
| 2025/2026 year split | yes | `docs/v92_C_EXHAUSTION_EXIT_TIMING_DIAGNOSTICS.md`, `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md`, `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md` | yes | no | no | yes | Year split is already documented in committed outputs. |

## Findings

- `trade_log.csv` is available now and is safe to read.
- Logistic kept/skipped decisions are available now from the committed logistic dry-run report.
- Aggregate MFE/MAE, giveback, and time-to-MFE evidence exists in committed docs, but only as summaries.
- Row-level MFE/MAE, positive-MFE-before-loss, giveback magnitude, time-from-MFE-to-exit, and intra-trade high/low are not available now as committed approved outputs.
- Existing scripts can compute row-level excursion diagnostics from bars, but that would reconstruct the missing source and therefore requires separate preregistration before any execution.
- The current gate therefore does not yet have all required inputs for the future descriptive exit/giveback audit.

Classification:

- available_now: `trade_log.csv`, logistic kept/skipped decisions, aggregate signal-state diagnostics, aggregate decay diagnostics, 2025/2026 split summaries
- partially_available: aggregate MFE/MAE/giveback/timing evidence in docs
- unavailable: row-level MFE, row-level MAE, positive-MFE-before-loss, giveback magnitude, time-to-MFE, time-from-MFE-to-exit, intra-trade high/low
- unsafe_without_new_pre_registration: reconstructing row-level MFE/MAE from bars

## Decision Logic

Reconstructing MFE/MAE from bars would be required to complete the future descriptive exit/giveback audit at trade-row granularity.

Decision: `source_missing_reconstruction_requires_separate_preregistration`

## Recommended Next Task

Create a separate MFE/MAE source pre-registration that defines how row-level excursion and giveback diagnostics could be safely obtained without leakage, optimization, or full reconstruction.

Do not recommend immediate bar reconstruction.
Do not recommend backtesting.
Do not recommend changing exits.
Do not recommend paper/live trading.

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
- No MFE/MAE reconstruction unless separately pre-registered.

## Decision

Decision: `source_missing_reconstruction_requires_separate_preregistration`

## Decision Labels

- `c_exhaustion_exit_giveback_source_availability_audit_created`
- `source_availability_only`
- `no_new_model_trained`
- `no_model_refit`
- `no_scaler_refit`
- `no_threshold_tuning`
- `no_exit_optimization`
- `no_mfe_mae_reconstruction`
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
- `source_missing_reconstruction_requires_separate_preregistration`
