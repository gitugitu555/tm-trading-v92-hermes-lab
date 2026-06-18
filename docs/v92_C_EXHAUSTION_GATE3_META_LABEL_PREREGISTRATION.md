# V9.2 C_Exhaustion Gate 3 Meta-Label Pre-Registration

## Purpose

This document pre-registers a future Gate 3 meta-label experiment. It is not the experiment itself, and it does not approve modeling, label generation, or any alpha claim.

## Current Gate Status

- Gate 1 static inventory: pass
- Gate 1 schema availability: pass
- Gate 1 timestamp alignment: pass
- Gate 2 feature table dry run: pass
- Gate 2 feature contract/nullness audit: pass
- Gate 3 model experiment: not started

## Safety Boundary

- No model is trained in this task.
- No labels are generated in this task.
- No predictive metrics are computed in this task.
- No feature-table artifacts are written.
- No alpha claim is made.
- No paper/live trading is approved.
- Full reconstruction remains blocked.
- OFI/L2 features remain blocked.

## Research Question

Can a pre-registered, leakage-safe meta-label model improve the keep/skip decision for existing C_Exhaustion signals using only approved signal-time OHLCV, `volume_delta`, and CVD/delta proxy features, under purged time splits and explicit costs?

This is only a future testable hypothesis. It does not assert that the answer is yes.

## Signal Universe

Allowed universe:

- Existing C_Exhaustion replay output from `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Existing 750btc aligned bar schema from `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Signal-time alignment convention:
  - `signal_time = signal bar close_time`
  - `entry_time = entry bar open_time`
  - `exit_time = exit bar open_time`

Forbidden universe changes:

- No new signal generation.
- No changed entries.
- No changed exits.
- No changed target/stop logic.
- No new regime gating.
- No extra signal filtering outside meta-label keep/skip research.

## Approved Feature Set

The first Gate 3 experiment is locked to the 24 Gate 2 model features:

- `signal_open`
- `signal_high`
- `signal_low`
- `signal_close`
- `signal_volume`
- `signal_range`
- `signal_body`
- `signal_body_to_range`
- `signal_close_location_in_range`
- `signal_return_1_bar`
- `signal_return_3_bar`
- `signal_return_5_bar`
- `rolling_vol_20_past`
- `rolling_range_mean_20_past`
- `volume_zscore_20_past`
- `signal_volume_delta`
- `volume_delta_abs`
- `volume_delta_sign`
- `volume_delta_rolling_sum_3_past`
- `volume_delta_rolling_sum_5_past`
- `volume_delta_rolling_zscore_20_past`
- `cvd_proxy_at_signal`
- `cvd_proxy_slope_3_past`
- `cvd_proxy_slope_5_past`

## Audit Identity Columns

Allowed only for row identity, grouping, and split logic:

- `signal_index`
- `entry_index`
- `exit_index`
- `signal_time`
- `entry_time`
- `exit_time`
- `year`

These remain audit identity only in this preregistration. They must not become model features unless a later protocol explicitly redefines them as non-leaky split variables.

## Forbidden Feature Columns

Forbidden from the model matrix:

- `entry_price`
- `exit_price`
- `gross_return_bps`
- `net_return_bps`
- `holding_bars`
- `exit_time` as a model feature
- `exit_index` as a model feature
- `entry_time` as a model feature
- `entry_index` as a model feature
- any future bar value
- any post-entry value
- any MFE/MAE column
- any target/stop outcome column
- `OFI`
- `MLOFI`
- `microprice`
- `spread`
- `depth`
- `queue imbalance`
- `L2 imbalance`
- `spoofing`
- `iceberg`
- `whale pressure`
- `funding`
- `OI`
- `liquidation`
- `derivatives crowding`
- `basis`

## Label Definition Options

Allowed future label families:

Option A: net-positive keep/skip label

- `label_keep = 1` if `net_return_bps > 0` after the existing cost model
- `label_keep = 0` otherwise

Option B: net expectancy threshold label

- `label_keep = 1` if `net_return_bps >= pre-registered threshold`
- The threshold must be fixed before the experiment starts.
- Suggested thresholds to pre-register only, not test now:
  - `0 bps`
  - `5 bps`
  - `10 bps`

Option C: adverse giveback label

- Only if it is already derivable from existing audited diagnostics.
- It must not use MFE/MAE as a model feature.
- It must be a target only, never an input.

Primary label for the first Gate 3 implementation:

- Option A: net-positive keep/skip label

## Forbidden Labels

- Any label using future data not present in the existing trade log.
- Any label that changes the replay mechanics.
- Any label requiring new exit simulation.
- Any label requiring new target/stop optimization.
- Any label that uses unapproved OFI/L2 features.
- Any label chosen after seeing model performance.
- Any label tuned across the full sample.

## Splits

Use strict chronological splits.

Primary split:

- Train: 2020, 2021, 2022, 2023
- Validation: 2024
- Holdout/recent: 2025, 2026

Additional rules:

- No random shuffle split.
- No cross-sectional shuffle.
- No leakage across adjacent signal periods.
- Apply an embargo / purge around split boundaries if overlapping holding periods exist.
- Report yearly metrics separately.

## Purge / Embargo Rules

- Use `signal_time` and `exit_time` to detect overlap.
- Any training sample whose holding interval overlaps validation or holdout intervals must be purged.
- At minimum, embargo all trades whose `signal_time` falls within a max holding-bars equivalent time window around split boundaries.
- Prefer existing repo purged split conventions if already implemented.

Do not implement this now; this is a pre-registered Gate 3 rule.

## Allowed Future Model Classes

For the first Gate 3 run, allow only simple, auditable models:

- Logistic regression with standardization fitted on train only
- Shallow decision tree with fixed `max_depth`
- Small random forest only if pre-registered and tightly constrained
- XGBoost only in later Gate 3b, not the first Gate 3a

Preferred first model:

- Logistic regression baseline
- Optional shallow decision tree sanity check

## Forbidden Modeling Practices

- Full-sample standardization
- Random shuffle cross-validation
- Feature selection using validation or holdout
- Hyperparameter search over many combinations
- Repeated tuning on 2025–2026
- Using holdout to choose threshold
- Model stacking
- Ensembling
- Feature importance fishing
- Dropping bad years after seeing results
- Optimizing for win rate only
- Ignoring cost or slippage
- Reporting only aggregate performance

## Baselines

Mandatory future comparisons:

1. Replay baseline: keep all C_Exhaustion trades.
2. Naive no-trade baseline.
3. OHLCV-only meta-label model.
4. OHLCV + `volume_delta` / CVD-proxy model.
5. Simple pre-registered heuristic threshold baseline if any threshold is specified before training.

Do not include L2/OFI baselines until OFI artifacts are separately approved.

## Metrics

Allowed future metrics:

- number of trades kept
- number of trades skipped
- keep rate
- precision of keep decision
- recall of profitable trades
- net expectancy bps on kept trades
- net expectancy bps on all original trades for comparison
- total net return on kept trades
- profit factor on kept trades
- max drawdown on kept trades
- yearly net expectancy
- yearly trade count
- 2025–2026 holdout metrics
- calibration / reliability curve for train and validation only
- confusion matrix

Forbidden or discouraged metrics:

- win rate alone as a success criterion
- in-sample-only performance
- full-sample tuned Sharpe
- performance after retuning thresholds on holdout
- any metric that ignores explicit cost
- any metric that hides trade-count collapse

## Acceptance Gates

A future Gate 3 run may only proceed to Gate 4 if all of the following are true:

- Row count is preserved before filtering.
- Feature contract matches Gate 2 contract exactly.
- No forbidden feature columns are present.
- No leakage audit failures occur.
- Train, validation, and holdout splits are chronological.
- Holdout 2025–2026 has non-trivial trade count.
- Model improves validation net expectancy versus keep-all baseline.
- Model does not destroy validation trade count.
- Holdout 2025–2026 is not materially worse than keep-all baseline.
- Yearly results do not depend on one lucky year.
- Cost model remains explicit.
- Full report includes failures as well as successes.

Suggested minimum non-trivial trade-count rule:

- Kept trades on validation must be at least 30% of validation trades or at least 20 trades, whichever is lower.
- Kept trades on holdout must be at least 30% of holdout trades or at least 10 trades, whichever is lower.

Do not optimize these thresholds after seeing results.

## Failure / Abandonment Rules

The future Gate 3 line should be paused or abandoned if:

- Holdout 2025–2026 worsens materially versus keep-all.
- Kept trade count collapses.
- Validation improvement does not transfer to holdout.
- A model only works by exploiting one year.
- Leakage controls fail.
- Costs erase the apparent edge.
- The model selects mostly historical winners but not recent winners.
- Any forbidden feature slips into the model matrix.

## Required Future Gate 3 Report

A future Gate 3 implementation must produce a Markdown-only report first.

No model artifacts are allowed in the first Gate 3 dry run unless separately approved.

The report must include:

- feature contract hash or explicit column list
- row counts before and after purging
- split boundaries
- purge/embargo counts
- label distribution by split and by year
- baseline metrics
- model metrics
- validation results
- holdout results
- leakage audit
- forbidden feature audit
- cost model statement
- failure cases
- decision labels

## What Is Safe

- Gate 3 pre-registration planning
- Label protocol design
- Split protocol design
- Leakage protocol design
- Metric protocol design
- Future experiment acceptance gate design

## What Is Not Safe

- Training a model in this task
- Computing predictive metrics in this task
- Optimizing features
- Backtesting new strategy logic
- Changing C_Exhaustion replay
- Full reconstruction
- OFI artifact generation
- Paper/live trading
- Alpha claims

## Decision

- `c_exhaustion_gate3_preregistration_created`
- `documentation_only`
- `no_model_trained`
- `no_predictive_metrics_computed`
- `no_strategy_backtest_run`
- `no_feature_table_artifacts_written`
- `no_ofi_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_3_not_started`

## Next Safe Task

The next allowed implementation task is a bounded read-only Gate 3 protocol checker on synthetic fixtures only, focused on verifying that the preregistered label definition, split boundaries, and purge/embargo rules can be expressed without introducing forbidden columns or any model training.

