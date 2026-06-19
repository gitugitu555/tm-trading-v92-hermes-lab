# V9.2 C_Exhaustion Exit Param Set 001 Diagnostic

## Purpose

This is a diagnostic overlay only for the fixed C_Exhaustion exit parameter set 001. It applies the preregistered live peak-retention / giveback guard in memory, compares it against the existing post-regime-fix anchor, and writes only a Markdown summary.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- real_trade_log_read: `true`
- real_bar_data_read: `true`
- raw_l2_data_read: `false`
- ofi_artifacts_read: `false`
- row_level_artifacts_written: `false`
- feature_table_artifacts_written: `false`
- model_artifacts_written: `false`

## Safety Boundary

- No strategy/replay logic changed.
- No backtest engine changed.
- No entry logic changed.
- No model trained.
- No thresholds tuned.
- No alternative thresholds tested.
- No alternative windows tested.
- No row-level artifacts written.
- No feature-table artifacts written.
- No model artifacts written.
- No OFI artifacts written.
- Same-bar close diagnostic basis only.
- Not paper/live executable.
- Alpha remains blocked.
- Full reconstruction remains blocked.
- OFI reconstruction remains blocked unless separately approved elsewhere.

## Fixed Parameter Set Applied

- experiment name: `C_EXHAUSTION_EXIT_PARAM_SET_001_LIVE_PEAK_RETENTION_GUARD`
- symbol: BTCUSDT
- bar size: 750 BTC bars only
- direction basis: `long-only (assumed; side column absent)`
- entry logic: unchanged from the existing post-regime-fix C Exhaustion replay anchor
- baseline comparison: existing post-regime-fix C Exhaustion anchor
- horizon: preserve existing 36-bar horizon
- original stop/target: preserve existing baseline stop/target geometry
- decision timing: completed bar close only
- timestamp convention: `half_open_open_time_convention`
- entry price basis: existing trade-log `entry_price`
- live peak return basis: completed-bar high relative to `entry_price`
- decision return basis: completed-bar close relative to `entry_price`
- activation condition: activate protection only after `live_peak_return_bps >= +50.0 bps`
- protective exit condition: after activation, diagnostic protective exit occurs on a completed bar close if `close_return_bps <= 0.50 * live_peak_return_bps`
- protective exit execution basis: same completed-bar close diagnostic basis only
- cost ladder: 1, 2, 3, 5, 8, 12 bps

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

## Rule Activation Summary

- trades_inspected: `310`
- activation_count: `249`
- activation_rate: `80.323%`
- protective_exit_count: `220`
- protective_exit_rate: `70.968%`
- unchanged_exit_count: `90`
- unavailable_count: `0`
- unmatched_count: `0`

## Performance Summary

| split | trade_count | activation_count | protective_exit_count | unchanged_exit_count | unavailable_count | unmatched_count | original_win_rate | diagnostic_win_rate | original_gross_expectancy_bps | diagnostic_gross_expectancy_bps | gross_expectancy_delta_bps | original_profit_factor | diagnostic_profit_factor | original_average_win_bps | diagnostic_average_win_bps | original_average_loss_bps | diagnostic_average_loss_bps | original_payoff_ratio | diagnostic_payoff_ratio | original_max_drawdown_pct | diagnostic_max_drawdown_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 249 | 220 | 90 | 0 | 0 | 0.597 | 0.706 | 56.003 | 26.768 | -29.235 | 1.929 | 1.899 | 194.865 | 80.047 | -149.513 | -101.451 | 1.303 | 0.789 | 23.905 | 12.444 |
| 2020-2023 | 259 | 205 | 177 | 82 | 0 | 0 | 0.606 | 0.710 | 63.760 | 32.245 | -31.515 | 2.210 | 2.165 | 192.098 | 84.336 | -133.780 | -95.553 | 1.436 | 0.883 | 16.475 | 12.444 |
| 2024-2026 | 51 | 44 | 43 | 8 | 0 | 0 | 0.549 | 0.686 | 16.612 | -1.043 | -17.655 | 1.168 | 0.974 | 210.381 | 57.496 | -219.282 | -129.098 | 0.959 | 0.445 | 23.905 | 9.809 |
| 2025 | 16 | 12 | 12 | 4 | 0 | 0 | 0.250 | 0.688 | -148.752 | -28.039 | 120.712 | 0.105 | 0.549 | 70.009 | 49.632 | -221.672 | -198.916 | 0.316 | 0.250 | 20.730 | 3.661 |
| 2026 | 9 | 7 | 7 | 2 | 0 | 0 | 0.667 | 0.444 | -4.282 | -46.989 | -42.707 | 0.947 | 0.277 | 113.651 | 40.485 | -240.148 | -116.969 | 0.473 | 0.346 | 5.087 | 5.479 |

## Cost Stress Ladder

The table below reports the original-anchor 12 bps stress benchmark alongside the diagnostic net expectancy at each fixed cost level.

| split | original_net_expectancy_bps_12bps | diagnostic_net_expectancy_bps_1bps | diagnostic_net_expectancy_bps_2bps | diagnostic_net_expectancy_bps_3bps | diagnostic_net_expectancy_bps_5bps | diagnostic_net_expectancy_bps_8bps | diagnostic_net_expectancy_bps_12bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 44.003 | 25.768 | 24.768 | 23.768 | 21.768 | 18.768 | 14.768 |
| 2020-2023 | 51.760 | 31.245 | 30.245 | 29.245 | 27.245 | 24.245 | 20.245 |
| 2024-2026 | 4.612 | -2.043 | -3.043 | -4.043 | -6.043 | -9.043 | -13.043 |
| 2025 | -160.752 | -29.039 | -30.039 | -31.039 | -33.039 | -36.039 | -40.039 |
| 2026 | -16.282 | -47.989 | -48.989 | -49.989 | -51.989 | -54.989 | -58.989 |

## Calendar-Year Stability

| year | trade_count | activation_count | protective_exit_count | unchanged_exit_count | original_gross_expectancy_bps | diagnostic_gross_expectancy_bps | gross_expectancy_delta_bps | original_net_expectancy_bps_12bps | diagnostic_net_expectancy_bps_12bps | original_profit_factor | diagnostic_profit_factor | original_payoff_ratio | diagnostic_payoff_ratio | activation_rate | protective_exit_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 20 | 18 | 3 | 103.086 | 74.772 | -28.314 | 91.086 | 62.772 | 2.942 | 10.265 | 1.810 | 0.513 | 0.952 | 0.857 |
| 2021 | 82 | 75 | 68 | 14 | 148.328 | 52.039 | -96.290 | 136.328 | 40.039 | 3.206 | 2.207 | 1.574 | 1.144 | 0.915 | 0.829 |
| 2022 | 83 | 65 | 56 | 27 | 16.204 | 20.050 | 3.846 | 4.204 | 8.050 | 1.289 | 1.927 | 0.987 | 0.653 | 0.783 | 0.675 |
| 2023 | 73 | 45 | 35 | 38 | 11.522 | 11.642 | 0.120 | -0.478 | -0.358 | 1.356 | 1.510 | 1.001 | 0.786 | 0.616 | 0.479 |
| 2024 | 26 | 25 | 24 | 2 | 125.606 | 31.474 | -94.133 | 113.606 | 19.474 | 2.964 | 2.683 | 1.317 | 0.805 | 0.962 | 0.923 |
| 2025 | 16 | 12 | 12 | 4 | -148.752 | -28.039 | 120.712 | -160.752 | -40.039 | 0.105 | 0.549 | 0.316 | 0.250 | 0.750 | 0.750 |
| 2026 | 9 | 7 | 7 | 2 | -4.282 | -46.989 | -42.707 | -16.282 | -58.989 | 0.947 | 0.277 | 0.473 | 0.346 | 0.778 | 0.778 |

## Interpretation

- The fixed rule did not improve gross expectancy on the full sample.
- The fixed rule did not improve net expectancy after 12 bps stress cost on the full sample.
- The rule improved win rate while damaging payoff ratio, so the gain is not purely quality-preserving.
- The improvement is not concentrated in a single year only.
- 2025 and 2026 remain structurally poor under the fixed rule after 12 bps stress.
- Activation count is large enough to be meaningful.
- No trades were dropped or left unresolved.
- The diagnostic remains diagnostic-only and does not approve live execution.
- Paper/live is still blocked.

## What This Proves

- The fixed live-peak retention guard can be evaluated safely on the existing matched trade intervals and bounded bars.
- The rule can be applied without changing strategy logic, replay logic, or entry logic.
- The report can distinguish original-anchor exits from same-bar diagnostic protective exits.
- Calendar-year behavior can be reviewed descriptively.

## What This Does Not Prove

- no alpha approval
- no paper trading
- no live trading
- no production deployment
- no execution approval
- no strategy improvement claim
- no guarantee that the same-bar close basis is executable live
- no out-of-sample edge proof

## Risk Register

- Same-bar close basis is diagnostic only, not executable approval.
- The live peak guard is still based on hindsight bar highs, so the parameter set must remain fixed before any future test.
- Interval matching uses the verified `half_open_open_time_convention` convention.
- 750 BTC bars are not tick data.
- 2025 and 2026 can remain structurally weak even if the full sample improves.
- Activation count can be meaningful even when the later net expectancy remains negative after cost stress.
- No row-level artifact persistence.
- No OFI/L2 approval.

## Stop / Go Assessment

- This remains diagnostic-only.
- If the full-sample 12 bps stress improves and the improvement is not concentrated in one year, it is suitable only for further review, not execution.
- If 2025 and 2026 remain structurally poor or the payoff ratio deteriorates materially, the rule should not advance to execution approval.
- If the source contains unresolved or unmatched rows, that must be fixed separately before any future test.

## Recommended Next Step

Recommend a review-only decision note or a separately preregistered next experiment, not execution.

## Explicitly Not Approved

- No strategy/replay logic changed.
- No backtest run.
- No exit experiment run.
- No model trained.
- No thresholds tuned.
- No alternative thresholds tested.
- No alternative windows tested.
- No row-level artifacts written.
- No feature-table artifacts written.
- No model artifacts written.
- No OFI artifacts written.
- Same-bar close diagnostic basis only.
- Not paper/live executable.
- Alpha remains blocked.
- Full reconstruction remains blocked.
- OFI reconstruction remains blocked unless separately approved elsewhere.

## Decision

Decision: `fixed_param_set_001_diagnostic_failed`

## Decision Labels

- `c_exhaustion_exit_param_set_001_diagnostic_created`
- `fixed_param_set_001_diagnostic_overlay`
- `fixed_param_set_001_preregistered_only`
- `no_strategy_replay_changes`
- `no_backtest_run`
- `no_exit_experiment_run`
- `no_model_trained`
- `no_thresholds_tuned`
- `no_alternative_thresholds_tested`
- `no_alternative_windows_tested`
- `no_row_level_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_model_artifacts_written`
- `no_ofi_artifacts_written`
- `same_bar_close_diagnostic_basis_only`
- `not_paper_live_executable`
- `alpha_remains_blocked`
- `full_reconstruction_remains_blocked`
- `ofi_reconstruction_blocked_unless_separately_approved_elsewhere`
- `fixed_param_set_001_diagnostic_failed`
