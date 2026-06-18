# V9.2 C_Exhaustion Gate 3 Bounded Diagnostic Review

## Purpose

This document reviews the existing Gate 3 logistic dry-run results and investigates the caution flags without retraining, tuning, or approving trading use. It is a bounded diagnostic review only.

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

## Source Reports Reviewed

- `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_DRY_RUN.md`
- `docs/v92_C_EXHAUSTION_GATE3_LOGISTIC_META_LABEL_REVIEW_DECISION.md`

## Logistic Dry-Run Recap

The existing logistic dry run showed:

- Train keep-all mean: 51.760 bps versus logistic kept mean: 85.810 bps
- Validation keep-all mean: 113.606 bps versus logistic kept mean: 154.520 bps
- Holdout keep-all mean: -108.743 bps versus logistic kept mean: -70.052 bps
- Train keep count: 175 / 259
- Validation keep count: 13 / 26
- Holdout keep count: 9 / 25

This is encouraging at validation and in aggregate holdout, but it is not alpha approval.

## Holdout Year Diagnosis

Using the committed dry-run report:

2025:

- Total: 16
- Keep: 4
- Skip: 12
- Kept positive: 1
- Kept negative: 3
- Kept mean: -56.863 bps
- Keep-all mean: -160.752 bps

2026:

- Total: 9
- Keep: 5
- Skip: 4
- Kept positive: 3
- Kept negative: 2
- Kept mean: -80.603 bps
- Keep-all mean: -16.282 bps

Interpretation:

- 2025 improved but remained negative.
- 2026 worsened versus keep-all.
- The holdout aggregate improvement hides year-level instability.
- The model did not solve recent positive-tail decay.
- The sample is too small for robust approval.

## Kept vs Skipped Interpretation

The holdout model kept 9 of 25 trades. That is not a collapse in trade count, but the kept holdout trades were still negative on average. The 2026 subset is the clearest caution signal: the model selected 5 trades, yet those kept trades were worse than the 2026 keep-all average.

This supports diagnostic review, not tuning.

## Feature/Regime Diagnostic Hypotheses

These are hypotheses, not conclusions:

- 2026 market regime differs from train and validation.
- OHLCV plus volume_delta proxy is insufficient for recent decay.
- A missing stored regime column limits model context.
- Missing true L2, OFI, and footprint features may leave adverse selection unresolved.
- The model may be learning historical exhaustion continuation patterns that do not transfer.
- C_Exhaustion recent losers may require exit-management diagnostics, not just entry keep/skip filtering.

## Stop / Pause / Continue Assessment

Options considered:

1. Stop Gate 3 entirely.
2. Continue diagnostic review only.
3. Pre-register a future threshold experiment.
4. Pre-register a future model-class experiment.
5. Return to exit-horizon / giveback diagnostics.
6. Return to data-feature expansion only after OFI/L2 approval.

Recommended assessment:

- Continue diagnostic review only.
- Do not proceed to more model classes yet.
- Do not tune threshold yet.
- Strongly consider exit-horizon / giveback diagnostics because prior C_Exhaustion evidence showed recent losers had favorable excursion then gave back.

## Risk Register

- Small validation sample
- Small holdout sample
- Negative holdout expectancy
- 2026 degradation
- Threshold 0.50 may not be robust
- Model-class overfitting risk
- Feature insufficiency risk
- Missing regime risk
- No L2/OFI approval
- Risk of tuning on holdout

## Approved Next Task

Create a documentation-only Gate 3 diagnostic action plan that pre-registers one of the following paths:

Preferred path:

- Exit-horizon / giveback diagnostic plan for C_Exhaustion recent losers, using existing reports and no new model training.

Alternative allowed path:

- Pre-register a threshold-sensitivity audit, but no execution until separately approved.

Do not recommend immediate threshold tuning.
Do not recommend random forest.
Do not recommend XGBoost.
Do not recommend adding OFI/L2.
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

## Decision

The bounded diagnostic review confirms that the logistic model is a useful research probe but not a tradable alpha approval. The next safe move is to investigate the recent holdout failure mode, especially 2026 and possible exit/giveback dynamics, before any further model experiment.

Decision: `proceed_to_diagnostic_action_plan_only`

## Decision Labels

- `c_exhaustion_gate3_bounded_diagnostic_review_created`
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
- `proceed_to_diagnostic_action_plan_only`
