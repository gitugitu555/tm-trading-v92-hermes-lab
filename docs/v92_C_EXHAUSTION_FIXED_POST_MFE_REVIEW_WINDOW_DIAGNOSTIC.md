# V9.2 C_Exhaustion Fixed Post-MFE Review Window Diagnostic

## Purpose

This is a bounded descriptive diagnostic of the fixed MFE+12 review window. It does not optimize exits, change strategy logic, run a backtest, or approve trading.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bounded_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- row_level_artifacts_written: `false`
- feature_table_artifacts_written: `false`
- model_artifacts_written: `false`

## Safety Boundary

- No exit optimization was performed.
- No target/stop tuning was performed.
- No threshold tuning was performed.
- No alternative review windows were tested.
- No strategy backtest was run.
- No strategy/replay logic was changed.
- No model was trained.
- No model was refit.
- No scaler was refit.
- No raw L2 data was read.
- No OFI artifacts were read or written.
- No row-level artifacts were written.
- No feature-table artifacts were written.
- No model artifacts were written.
- No paper/live trading is approved.
- No production approval is given.
- Alpha is not approved.
- Full reconstruction remains blocked.

## Pre-Registered Protocol Applied

- preregistration file path: `docs/v92_C_EXHAUSTION_EXIT_MANAGEMENT_HYPOTHESIS_PREREGISTRATION.md`
- review window anchor: first MFE bar
- review window length: 12 bars after MFE
- review point: MFE+12
- interval convention: `half_open_open_time_convention`
- review-point price basis: review-bar close relative to entry_price
- no alternative windows tested
- no parameter search
- no holdout tuning
- MFE treated as hindsight diagnostic information, not a live-tradable signal

## Source Construction Summary

- trade_rows_loaded: `310`
- bar_rows_loaded: `204124`
- bar_files_read: `102`
- rows_with_matched_bars: `310`
- unresolved_rows: `0`
- year_min: `2020`
- year_max: `2026`
- side_basis: `long-only (assumed; side column absent)`
- final_return_basis: `gross_return_bps`

## MFE+12 Availability Summary

- trades_inspected: `310`
- giveback_loss_trades_inspected: `125`
- weak_positive_exit_trades_inspected: `55`
- rows_with_mfe_plus_12_available: `191`
- rows_without_mfe_plus_12_available: `119`
- insufficient_post_mfe_window_count: `119`
- availability_rate: `61.613%`

| year | total_trades | giveback_loss_count | weak_positive_exit_count | mfe_plus_12_available_count | mfe_plus_12_unavailable_count | availability_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 8 | 1 | 12 | 9 | 0.571 |
| 2021 | 82 | 27 | 16 | 46 | 36 | 0.561 |
| 2022 | 83 | 36 | 13 | 54 | 29 | 0.651 |
| 2023 | 73 | 31 | 15 | 47 | 26 | 0.644 |
| 2024 | 26 | 8 | 4 | 14 | 12 | 0.538 |
| 2025 | 16 | 12 | 3 | 13 | 3 | 0.812 |
| 2026 | 9 | 3 | 3 | 5 | 4 | 0.556 |

## Giveback Loss MFE+12 Diagnostic

- count: `125`
- mfe_plus_12_available_count: `116`
- avg_mfe_plus_12_return_bps: `-101.475`
- median_mfe_plus_12_return_bps: `-78.760`
- pct_still_positive_at_mfe_plus_12: `6.034%`
- pct_lost_more_than_50pct_mfe_by_mfe_plus_12: `97.414%`
- avg_mfe_plus_12_giveback_bps: `185.599`
- median_mfe_plus_12_giveback_bps: `156.757`
- avg_retained_mfe_ratio: `-3.556`
- median_retained_mfe_ratio: `-1.373`

| year | count | mfe_plus_12_available_count | avg_mfe_plus_12_return_bps | median_mfe_plus_12_return_bps | pct_still_positive_at_mfe_plus_12 | pct_lost_more_than_50pct_mfe_by_mfe_plus_12 | avg_mfe_plus_12_giveback_bps | median_mfe_plus_12_giveback_bps | avg_retained_mfe_ratio | median_retained_mfe_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8 | 7 | -49.813 | -50.483 | 0.143 | 0.857 | 179.620 | 211.887 | -0.589 | -0.388 |
| 2021 | 27 | 25 | -175.684 | -134.536 | 0.000 | 1.000 | 292.221 | 280.581 | -3.918 | -1.685 |
| 2022 | 36 | 35 | -85.861 | -71.453 | 0.143 | 0.943 | 161.099 | 135.284 | -2.451 | -1.151 |
| 2023 | 31 | 27 | -55.273 | -54.263 | 0.000 | 1.000 | 94.178 | 85.822 | -6.258 | -1.577 |
| 2024 | 8 | 7 | -132.854 | -131.999 | 0.000 | 1.000 | 220.259 | 243.232 | -2.717 | -1.406 |
| 2025 | 12 | 12 | -92.209 | -82.413 | 0.083 | 1.000 | 210.732 | 256.661 | -1.783 | -0.877 |
| 2026 | 3 | 3 | -165.439 | -130.152 | 0.000 | 1.000 | 238.251 | 141.863 | -5.080 | -2.494 |

## Weak Positive Exit MFE+12 Diagnostic

- count: `55`
- mfe_plus_12_available_count: `37`
- avg_mfe_plus_12_return_bps: `64.047`
- median_mfe_plus_12_return_bps: `58.282`
- pct_still_positive_at_mfe_plus_12: `83.784%`
- pct_lost_more_than_50pct_mfe_by_mfe_plus_12: `64.865%`
- avg_mfe_plus_12_giveback_bps: `162.487`
- median_mfe_plus_12_giveback_bps: `142.116`
- avg_retained_mfe_ratio: `0.241`
- median_retained_mfe_ratio: `0.328`

| year | count | mfe_plus_12_available_count | avg_mfe_plus_12_return_bps | median_mfe_plus_12_return_bps | pct_still_positive_at_mfe_plus_12 | pct_lost_more_than_50pct_mfe_by_mfe_plus_12 | avg_mfe_plus_12_giveback_bps | median_mfe_plus_12_giveback_bps | avg_retained_mfe_ratio | median_retained_mfe_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 1 | 1 | 114.743 | 114.743 | 1.000 | 0.000 | 72.178 | 72.178 | 0.614 | 0.614 |
| 2021 | 16 | 11 | 104.408 | 123.705 | 0.818 | 0.818 | 277.639 | 227.414 | 0.205 | 0.407 |
| 2022 | 13 | 11 | 78.313 | 68.818 | 0.909 | 0.364 | 127.401 | 130.125 | 0.403 | 0.564 |
| 2023 | 15 | 9 | 46.664 | 13.182 | 0.889 | 0.667 | 51.297 | 34.543 | 0.361 | 0.306 |
| 2024 | 4 | 3 | -43.095 | 5.079 | 0.667 | 1.000 | 208.646 | 247.285 | -0.227 | 0.020 |
| 2025 | 3 | 1 | 75.914 | 75.914 | 1.000 | 1.000 | 177.460 | 177.460 | 0.300 | 0.300 |
| 2026 | 3 | 1 | -121.547 | -121.547 | 0.000 | 1.000 | 219.344 | 219.344 | -1.243 | -1.243 |

## 2025 vs 2026 Comparison

### 2025

- total trades: `16`
- giveback_loss trades: `12`
- weak_positive_exit trades: `3`
- MFE+12 availability: `81.250%`
- percentage of giveback_loss trades still positive at MFE+12: `8.333%`
- percentage of giveback_loss trades that lost more than 50% of MFE by MFE+12: `100.000%`
- average MFE+12 return: `-92.209`
- median MFE+12 return: `-82.413`
- interpretation: 2025 shows early favorable excursion but long post-MFE decay before exit.

### 2026

- total trades: `9`
- giveback_loss trades: `3`
- weak_positive_exit trades: `3`
- MFE+12 availability: `55.556%`
- percentage of giveback_loss trades still positive at MFE+12: `0.000%`
- percentage of giveback_loss trades that lost more than 50% of MFE by MFE+12: `100.000%`
- average MFE+12 return: `-165.439`
- median MFE+12 return: `-130.152`
- interpretation: 2026 is smaller, but still shows post-MFE decay in the losing trades.

## Diagnostic Interpretation

- MFE+12 is available for a meaningful subset of trades, but not universally.
- Giveback_loss trades are not usually still positive at MFE+12.
- Giveback_loss trades have often already lost most of MFE by MFE+12.
- 2025 is the weaker holdout year relative to 2026 if its giveback losses decay more sharply or its MFE+12 returns are lower.
- The fixed MFE+12 review window reveals a descriptive post-MFE risk pattern.
- The result supports preregistering a future exit experiment only if the next hypothesis remains fixed and non-leaky.
- The result does not claim a better strategy or tradable edge.

## What This Proves

- Fixed MFE+12 can be computed safely from the existing trade intervals and bounded 750btc bars.
- Fixed MFE+12 is available before exit for at least some trades, and the diagnostic can measure post-MFE decay.
- Giveback can be visible by MFE+12.
- 2025 and 2026 can be compared descriptively without changing exits.

## What This Does Not Prove

- no alpha approval
- no trading rule
- no exit improvement
- no target/stop approval
- no paper/live readiness
- no production readiness
- no execution/slippage validity
- no proof this can be captured live
- no out-of-sample exit-test result

## Risk Register

- MFE is hindsight diagnostic information.
- MFE+12 depends on knowing the MFE bar after the fact.
- Intrabar path is unknown.
- final_return_basis is gross_return_bps if used.
- long-only (assumed; side column absent).
- 750btc bars are not tick data.
- 2026 sample size is small.
- No row-level logistic kept/skipped source.
- No execution/slippage simulation.
- Fixed MFE+12 may still be too late or too early.

## Stop / Go Assessment

- Stop or pause if MFE+12 is unavailable for most recent trades.
- Stop or pause if post-MFE decay does not appear before original exit.
- Stop or pause if the signal is inconsistent across years.
- Stop or pause if the result only looks useful after excluding bad years.
- Stop or pause if the next step would require tuning the review window.
- Continue only if the result yields a non-leaky separately pre-registerable future exit experiment.
- Continue only if the future experiment uses fixed parameters.
- Continue only if the future experiment does not change holdout protocol.
- Continue only if the next task remains documentation-first.

## Recommended Next Step

Recommend a documentation-only future exit-experiment preregistration with fixed parameters, not execution.

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
- No trading approval from MFE hindsight.
- No review-window optimization.

## Decision

Decision: `fixed_post_mfe_review_window_diagnostic_partial`

## Decision Labels

- `c_exhaustion_fixed_post_mfe_review_window_diagnostic_created`
- `bounded_descriptive_only`
- `single_hypothesis_only`
- `fixed_post_mfe_review_window`
- `mfe_plus_12_window`
- `real_trade_log_read`
- `real_bounded_bar_data_read`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_review_window_optimization`
- `no_exit_optimization`
- `no_target_stop_tuning`
- `no_threshold_tuning`
- `no_new_model_trained`
- `no_strategy_backtest_run`
- `no_strategy_replay_changes`
- `no_row_level_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_not_approved`
- `paper_live_blocked`
- `production_not_approved`
- `fixed_post_mfe_review_window_diagnostic_partial`
