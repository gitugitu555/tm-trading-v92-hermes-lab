# V9.2 C_Exhaustion Gate 3 Diagnostic Action Plan

## Purpose

This plan defines the next diagnostic path after the logistic Gate 3 dry run, without model training, threshold tuning, or trading approval. It is documentation-first and bounded to existing evidence.

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
- Gate 4: not started

## Safety Boundary

- No new model is trained.
- No model is refit.
- No scaler is refit.
- No threshold is tuned.
- No new predictive metrics are computed.
- No feature set is changed.
- No strategy/replay logic is changed.
- No raw L2 data is read.
- No OFI artifacts are read or written.
- No feature-table artifacts are written.
- No model artifacts are written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Problem Statement

The logistic meta-label dry run improved validation and aggregate holdout versus keep-all, but holdout stayed negative and 2026 worsened versus keep-all. The next work must diagnose the failure mode rather than tune or expand models.

## Known Evidence

| Split / Year | Keep-All Mean bps | Logistic Kept Mean bps | Interpretation |
| --- | ---: | ---: | --- |
| Train | 51.760 | 85.810 | Better than keep-all on train, but not proof of robustness |
| Validation | 113.606 | 154.520 | Better than keep-all on validation |
| Holdout | -108.743 | -70.052 | Aggregate improvement, but still negative |
| 2025 holdout | -160.752 | -56.863 | Improved, but remained negative |
| 2026 holdout | -16.282 | -80.603 | Worse than keep-all |

| Split | Predicted Keep | Predicted Skip | Kept Positive | Kept Negative | Kept Mean bps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 175 | 84 | not separately restated | not separately restated | 85.810 |
| Validation | 13 | 13 | not separately restated | not separately restated | 154.520 |
| Holdout | 9 | 16 | 3 in 2026, 1 in 2025 | 2 in 2026, 3 in 2025 | -70.052 |

## Primary Diagnostic Hypothesis

Recent C_Exhaustion weakness may be driven more by exit-horizon / giveback dynamics than by entry keep/skip classification alone.

Why this hypothesis is primary:

- Existing C_Exhaustion evidence previously suggested recent losers had favorable excursion before giving back.
- Logistic keep/skip improved validation but did not make holdout positive.
- 2026 worsened despite the same pre-registered model protocol.
- The pattern points toward trade-management diagnostics, not immediate model expansion.

## Secondary Diagnostic Hypotheses

- 2026 market regime differs from the 2020-2024 training/validation mix.
- OHLCV plus volume_delta proxy is insufficient for recent adverse selection.
- Missing stored regime context may matter.
- Missing true L2, OFI, and footprint context may matter, but that remains blocked.
- The logistic model may be learning historical patterns that do not transfer.
- Threshold 0.50 may be brittle, but threshold tuning is not approved.

## Diagnostic Workstream A: Exit-Horizon / Giveback Review

Future diagnostic questions:

1. Did 2025/2026 losers show positive MFE before losing?
2. Did the fixed exit horizon give back profits?
3. Did winners require shorter holding periods than current exit logic?
4. Are 2026 kept losers mostly giveback failures or bad entries?
5. Does C_Exhaustion need exit-management research before more entry/meta-label models?

Allowed future inputs only if already existing/committed or separately approved:

- Existing `trade_log.csv`
- Existing signal-state diagnostics reports
- Existing C_Exhaustion replay diagnostics
- No raw L2
- No OFI artifacts

Forbidden in this action plan:

- Changing exits
- Rerunning strategy backtests
- Optimizing horizon
- Changing replay logic

## Diagnostic Workstream B: Holdout Year Split Review

Future diagnostic questions:

1. What differs between 2025 and 2026 kept/skipped patterns?
2. Is 2026 weakness due to fewer trades, different label mix, or worse kept losses?
3. Did the model keep too many negative 2026 trades or skip too many positive 2026 trades?
4. Is 2026 too small for reliable inference?
5. Should 2026 be treated as unresolved rather than failed?

No threshold tuning allowed.

## Diagnostic Workstream C: Feature / Regime Sufficiency Review

Future diagnostic questions:

1. Are approved features stable across train, validation, and holdout years?
2. Is `volume_delta_sign` constant or low-information in recent years?
3. Is missing regime context a blocker?
4. Are L2, OFI, and footprint features still unavailable?
5. Should future work prioritize regime materialization before more models?

No new feature search allowed.

## Stop / Go Rules

Stop or pause Gate 3 modeling if:

- 2026 weakness appears driven by structural regime mismatch.
- Exit/giveback failures dominate recent losses.
- Approved features cannot explain recent instability.
- Any diagnostic requires holdout tuning to look good.
- The only path forward is model or threshold fishing.

Continue only if:

- Diagnostics identify a pre-registerable, non-leaky next hypothesis.
- The next hypothesis can be tested without changing the holdout protocol.
- The next task can remain bounded and documentation-first.

## Approved Next Implementation Task

Create a documentation-only or descriptive-only C_Exhaustion exit-horizon / giveback diagnostic pre-registration.

This next preregistration should define:

- Exact questions
- Allowed existing inputs
- Forbidden changes
- No backtest rule
- No optimization rule
- No paper/live rule
- No alpha approval rule
- Expected output report

It should not compute the diagnostic yet unless separately approved.

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
- No exit-horizon optimization yet.
- No backtest reruns.

## Decision

The Gate 3 logistic model remains a useful research probe, but the 2026 degradation and negative holdout expectancy require exit-horizon / giveback diagnostic pre-registration before any further modeling or strategy changes.

Decision: `proceed_to_exit_giveback_diagnostic_preregistration_only`

## Decision Labels

- `c_exhaustion_gate3_diagnostic_action_plan_created`
- `documentation_only`
- `no_new_model_trained`
- `no_model_refit`
- `no_scaler_refit`
- `no_threshold_tuning`
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
- `proceed_to_exit_giveback_diagnostic_preregistration_only`
