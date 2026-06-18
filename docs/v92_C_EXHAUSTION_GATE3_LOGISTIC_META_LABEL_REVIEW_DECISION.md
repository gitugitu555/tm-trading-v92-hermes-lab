# V9.2 C_Exhaustion Gate 3 Logistic Meta-Label Review / Decision

## Purpose

This document reviews the first pre-registered Gate 3 logistic meta-label dry run and records a research decision only. It does not train a model, tune thresholds, or approve any trading use.

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
- Gate 4: not started

## Safety Boundary

- No new model is trained in this task.
- No new predictive metrics are computed in this task.
- No threshold is tuned in this task.
- No feature set is changed in this task.
- No strategy/replay logic is changed.
- No raw L2 data is read.
- No OFI artifacts are read or written.
- No feature-table artifacts are written.
- No model artifacts are written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Dry-Run Protocol Recap

- Logistic regression only.
- Approved 24 model features only.
- Option A label: `net_return_bps > 0`.
- Train: 2020-2023.
- Validation: 2024.
- Holdout: 2025-2026.
- Train-only `StandardScaler`.
- Default threshold `0.50` only.
- Holdout untouched until final reporting.
- No model artifacts.

## Contract / Leakage Review

- `X`/`y` row alignment passed.
- 24 approved features were used.
- No forbidden features were present in `X`.
- No identity columns were present in `X`.
- No outcome columns were present in `X`.
- No label column was present in `X`.
- No L2/OFI features were present in `X`.
- The scaler was fit on train only.
- The model was fit on train only.
- Holdout was not used for threshold selection.

## Result Summary

| Split | Keep-All Mean bps | Logistic Kept Mean bps | Predicted Keep | Keep Rate | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Train | 51.760 | 85.810 | 175 | 0.676 | 0.663 | 0.779 | 0.716 |
| Validation | 113.606 | 154.520 | 13 | 0.500 | 0.692 | 0.500 | 0.581 |
| Holdout | -108.743 | -70.052 | 9 | 0.360 | 0.444 | 0.444 | 0.444 |

## What Worked

- Validation kept mean improved versus keep-all.
- Holdout aggregate was less negative than keep-all.
- Contract and leakage checks passed.
- Holdout was not used for training, scaler fitting, or threshold selection.
- Trade count did not collapse at threshold `0.50`.
- The protocol is now executable end-to-end.

## What Did Not Work / Caution Flags

- Holdout kept mean remained negative.
- 2026 holdout worsened versus keep-all.
- Holdout sample size is small: 25 total, 9 kept.
- Validation sample size is small: 26 total, 13 kept.
- The positive validation result may not be robust.
- No Sharpe, drawdown, execution simulation, or portfolio-level robustness was approved.
- This does not justify paper/live trading.
- This does not justify production.
- This does not justify adding more model classes without a new protocol.

## Acceptance Gate Review

| Gate | Review | Interpretation |
| --- | --- | --- |
| row_count_preserved_before_filtering | pass | The matrix was preserved end-to-end before model fitting. |
| feature_contract_exact_match | pass | The logistic dry run stayed on the pre-registered 24-feature contract. |
| no_forbidden_columns | pass | No forbidden inputs leaked into the model matrix. |
| no_leakage_audit_failures | pass | The train-only scaler and train-only fit discipline were respected. |
| chronological_splits | pass | Train, validation, and holdout were kept chronologically separated. |
| holdout_nontrivial_trade_count | pass | Holdout had enough trades to evaluate once, but still small. |
| validation_net_expectancy_vs_keep_all_improved | pass | Validation improved, but this is not enough for approval. |
| validation_trade_count_not_collapsed | pass | The threshold did not collapse validation trade count. |
| holdout_not_materially_worse_than_keep_all | pass with caution | Aggregate holdout improved, but it remained negative and 2026 worsened. |
| yearly_results_not_one_lucky_year | pass with caution | Results are mixed across years, so robustness is not established. |
| explicit_cost_model_preserved | pass | The report retained the explicit cost-aware framing. |
| report_includes_failures | pass | The report exposed weaknesses rather than hiding them. |

## Decision

The logistic dry run is promising enough to justify a bounded diagnostic review, but not strong enough to approve alpha, paper trading, live trading, production, or broader model-class exploration.

Decision: `proceed_to_bounded_diagnostic_review_only`

## Approved Next Task

Create a Gate 3 bounded diagnostic review document that inspects the existing logistic dry-run outputs only, focusing on:

- why 2026 worsened,
- holdout year split behavior,
- kept vs skipped distribution by year,
- feature distribution drift by split/year,
- whether validation/holdout instability suggests stopping,
- whether a stricter no-trade or stop rule is needed.

This next task should not train models, tune thresholds, compute new predictive metrics, or add features.

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

## What Would Be Required Before Any Further Model Experiment

- A separate pre-registration for any threshold experiment.
- A separate pre-registration for any new model class.
- A fixed hypothesis for why 2026 failed.
- Strict prohibition on holdout retuning.
- A clear stop rule if diagnostics show instability.
- No artifact/model persistence unless separately approved.

## What Is Safe

- Reviewing the existing logistic dry-run report.
- Bounded diagnostic review.
- Stop/go decision writing.
- Separate pre-registration for any future experiment.

## What Is Not Safe

- Paper/live trading.
- Production deployment.
- Threshold retuning on holdout.
- Feature fishing.
- Model class fishing.
- Adding OFI/L2 features.
- Full reconstruction.
- Claiming alpha from one dry run.

## Decision Labels

- `c_exhaustion_gate3_logistic_review_decision_created`
- `documentation_only`
- `no_new_model_trained`
- `no_new_predictive_metrics_computed`
- `no_threshold_tuning`
- `no_feature_changes`
- `no_strategy_backtest_run`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_ofi_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `production_not_approved`
- `proceed_to_bounded_diagnostic_review_only`
