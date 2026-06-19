# C_Exhaustion Nonparametric Failure Attribution Diagnostic

## Purpose

This is the `nonparametric_failure_attribution_diagnostic` for C_Exhaustion. It is a diagnostic only, not a trading rule, and it uses the existing post-regime-fix trade log with the same 750 BTC bars to attribute recent failure modes without changing any execution logic.

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

- This is not a trading rule.
- No strategy logic was changed.
- No replay logic was changed.
- No entry logic was changed.
- No exit logic was changed.
- No OFI logic was changed.
- No OFI reconstruction was performed.
- No external data was added.
- No model was trained.
- No thresholds were optimized.
- No exit parameters were tuned.
- No Param Set 001 nearby variants were tested.
- No row-level artifacts were created.
- No feature artifacts were created.
- No model artifacts were created.
- No workflows were created.
- Alpha remains blocked.
- Paper/live remains blocked.
- Full OFI reconstruction remains blocked.

## Source Summary

- trade_rows_loaded: `310`
- bar_rows_loaded: `204124`
- bar_files_read: `102`
- rows_with_matched_bars: `310`
- unresolved_rows: `0`
- unmatched_rows: `0`
- unavailable_path_rows: `0`
- year_min: `2020`
- year_max: `2026`
- side_basis: `long-only (assumed; side column absent)`
- final_return_basis: `gross_return_bps`
- bar_size_basis: `750 BTC bars`
- convention_basis: `half_open_open_time_convention`

## Method Notes

- Half-open matching convention: `bar.open_time >= entry_time and bar.open_time < exit_time`.
- Completed bars only are used for checkpoint returns.
- MFE and attribution labels are hindsight-only diagnostic labels, not live-tradable signals.
- Entry checkpoints use the first 1, 3, and 6 completed bars only.
- Any missing regime or context columns are reported explicitly rather than treated as a failure.

## 1. Entry Degradation

Checkpoint returns and early excursion measures use completed bars only.

| split | trade_count | matched_rows | unmatched_rows | unavailable_path_rows | avg_checkpoint_return_1_bps | avg_checkpoint_return_3_bps | avg_checkpoint_return_6_bps | avg_early_favorable_excursion_6_bps | avg_early_adverse_excursion_6_bps | pct_never_positive_after_entry | pct_reaching_25_bps_before_original_exit | pct_reaching_50_bps_before_original_exit | pct_reaching_100_bps_before_original_exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 310 | 0 | 0 | 7.495 | 20.202 | 32.890 | 99.433 | -66.399 | 0.048 | 0.932 | 0.803 | 0.584 |
| 2020-2023 | 259 | 259 | 0 | 0 | 7.157 | 21.286 | 35.037 | 99.045 | -63.543 | 0.042 | 0.931 | 0.792 | 0.564 |
| 2024-2026 | 51 | 51 | 0 | 0 | 9.212 | 14.697 | 21.989 | 101.404 | -80.904 | 0.078 | 0.941 | 0.863 | 0.686 |
| 2025 | 16 | 16 | 0 | 0 | 20.167 | 11.279 | 18.344 | 104.366 | -78.481 | 0.125 | 0.938 | 0.750 | 0.562 |
| 2026 | 9 | 9 | 0 | 0 | -3.558 | 10.830 | -19.896 | 88.708 | -88.044 | 0.111 | 0.889 | 0.778 | 0.667 |

| year | trade_count | matched_rows | unmatched_rows | unavailable_path_rows | avg_checkpoint_return_1_bps | avg_checkpoint_return_3_bps | avg_checkpoint_return_6_bps | avg_early_favorable_excursion_6_bps | avg_early_adverse_excursion_6_bps | pct_never_positive_after_entry | pct_reaching_25_bps_before_original_exit | pct_reaching_50_bps_before_original_exit | pct_reaching_100_bps_before_original_exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 21 | 0 | 0 | 29.320 | 78.198 | 70.826 | 145.135 | -54.791 | 0.000 | 1.000 | 0.952 | 0.905 |
| 2021 | 82 | 82 | 0 | 0 | 4.379 | 24.316 | 54.641 | 155.117 | -104.768 | 0.049 | 0.988 | 0.915 | 0.780 |
| 2022 | 83 | 83 | 0 | 0 | 6.884 | 23.378 | 35.856 | 84.420 | -41.846 | 0.036 | 0.940 | 0.783 | 0.482 |
| 2023 | 73 | 73 | 0 | 0 | 4.211 | -0.867 | 1.790 | 39.432 | -44.421 | 0.055 | 0.836 | 0.616 | 0.315 |
| 2024 | 26 | 26 | 0 | 0 | 6.890 | 18.138 | 38.730 | 103.975 | -79.923 | 0.038 | 0.962 | 0.962 | 0.769 |
| 2025 | 16 | 16 | 0 | 0 | 20.167 | 11.279 | 18.344 | 104.366 | -78.481 | 0.125 | 0.938 | 0.750 | 0.562 |
| 2026 | 9 | 9 | 0 | 0 | -3.558 | 10.830 | -19.896 | 88.708 | -88.044 | 0.111 | 0.889 | 0.778 | 0.667 |

## 2. Tail Opportunity Decay

MFE is hindsight-only diagnostic information and not a live-tradable signal.

| split | trade_count | median_mfe_bps | p75_mfe_bps | p90_mfe_bps | p95_mfe_bps | pct_reaching_25_bps_before_original_exit | pct_reaching_50_bps_before_original_exit | pct_reaching_100_bps_before_original_exit | pct_unavailable_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 131.888 | 289.029 | 447.778 | 610.749 | 0.932 | 0.803 | 0.584 | 0.000 |
| 2020-2023 | 259 | 124.788 | 278.989 | 447.824 | 636.052 | 0.931 | 0.792 | 0.564 | 0.000 |
| 2024-2026 | 51 | 184.837 | 318.414 | 400.488 | 488.326 | 0.941 | 0.863 | 0.686 | 0.000 |
| 2025 | 16 | 141.610 | 208.469 | 316.969 | 326.840 | 0.938 | 0.750 | 0.562 | 0.000 |
| 2026 | 9 | 129.631 | 218.271 | 327.266 | 341.949 | 0.889 | 0.778 | 0.667 | 0.000 |

| year | trade_count | median_mfe_bps | p75_mfe_bps | p90_mfe_bps | p95_mfe_bps | pct_reaching_25_bps_before_original_exit | pct_reaching_50_bps_before_original_exit | pct_reaching_100_bps_before_original_exit | pct_unavailable_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 209.071 | 397.681 | 452.516 | 481.718 | 1.000 | 0.952 | 0.905 | 0.000 |
| 2021 | 82 | 299.425 | 447.452 | 701.717 | 845.209 | 0.988 | 0.915 | 0.780 | 0.000 |
| 2022 | 83 | 94.734 | 199.117 | 298.439 | 408.610 | 0.940 | 0.783 | 0.482 | 0.000 |
| 2023 | 73 | 68.516 | 119.352 | 179.230 | 244.098 | 0.836 | 0.616 | 0.315 | 0.000 |
| 2024 | 26 | 251.376 | 390.708 | 488.326 | 563.733 | 0.962 | 0.962 | 0.769 | 0.000 |
| 2025 | 16 | 141.610 | 208.469 | 316.969 | 326.840 | 0.938 | 0.750 | 0.562 | 0.000 |
| 2026 | 9 | 129.631 | 218.271 | 327.266 | 341.949 | 0.889 | 0.778 | 0.667 | 0.000 |

## 3. Giveback Worsening

Giveback is computed as `final_return_bps - mfe_bps`; retained MFE ratio is `final_return_bps / mfe_bps` when `mfe_bps > 0`.

| split | trade_count | median_mfe_bps | median_giveback_bps | pct_positive_mfe_ended_negative | pct_lost_more_than_25pct_mfe | pct_lost_more_than_50pct_mfe | pct_lost_more_than_75pct_mfe | pct_unavailable_path | net_expectancy_bps_12bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 131.888 | -104.066 | 0.403 | 0.761 | 0.581 | 0.471 | 0.000 | 44.003 |
| 2020-2023 | 259 | 124.788 | -95.544 | 0.394 | 0.757 | 0.568 | 0.448 | 0.000 | 51.760 |
| 2024-2026 | 51 | 184.837 | -176.505 | 0.451 | 0.784 | 0.647 | 0.588 | 0.000 | 4.612 |
| 2025 | 16 | 141.610 | -313.279 | 0.750 | 1.000 | 0.938 | 0.938 | 0.000 | -160.752 |
| 2026 | 9 | 129.631 | -86.240 | 0.333 | 0.778 | 0.667 | 0.444 | 0.000 | -16.282 |

| year | trade_count | median_mfe_bps | median_giveback_bps | pct_positive_mfe_ended_negative | pct_lost_more_than_25pct_mfe | pct_lost_more_than_50pct_mfe | pct_lost_more_than_75pct_mfe | pct_unavailable_path | net_expectancy_bps_12bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 209.071 | -122.683 | 0.381 | 0.714 | 0.429 | 0.381 | 0.000 | 91.086 |
| 2021 | 82 | 299.425 | -153.997 | 0.329 | 0.695 | 0.524 | 0.390 | 0.000 | 136.328 |
| 2022 | 83 | 94.734 | -90.635 | 0.434 | 0.759 | 0.590 | 0.518 | 0.000 | 4.204 |
| 2023 | 73 | 68.516 | -58.268 | 0.425 | 0.836 | 0.630 | 0.452 | 0.000 | -0.478 |
| 2024 | 26 | 251.376 | -122.702 | 0.308 | 0.654 | 0.462 | 0.423 | 0.000 | 113.606 |
| 2025 | 16 | 141.610 | -313.279 | 0.750 | 1.000 | 0.938 | 0.938 | 0.000 | -160.752 |
| 2026 | 9 | 129.631 | -86.240 | 0.333 | 0.778 | 0.667 | 0.444 | 0.000 | -16.282 |

## 4. Exit vs Entry Attribution Classes

These attribution bins are descriptive only. They are not execution rules and must not be used as live exits.

| split | trade_count | no_favorable_excursion | small_favorable_excursion_then_loss | large_favorable_excursion_then_giveback | weak_positive_exit | strong_positive_exit | immediate_adverse_path | delayed_decay_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 0 (0.000) | 53 (0.171) | 0 (0.000) | 77 (0.248) | 108 (0.348) | 0 (0.000) | 72 (0.232) |
| 2020-2023 | 259 | 0 (0.000) | 46 (0.178) | 0 (0.000) | 67 (0.259) | 90 (0.347) | 0 (0.000) | 56 (0.216) |
| 2024-2026 | 51 | 0 (0.000) | 7 (0.137) | 0 (0.000) | 10 (0.196) | 18 (0.353) | 0 (0.000) | 16 (0.314) |
| 2025 | 16 | 0 (0.000) | 4 (0.250) | 0 (0.000) | 3 (0.188) | 1 (0.062) | 0 (0.000) | 8 (0.500) |
| 2026 | 9 | 0 (0.000) | 2 (0.222) | 0 (0.000) | 3 (0.333) | 3 (0.333) | 0 (0.000) | 1 (0.111) |

| year | trade_count | no_favorable_excursion | small_favorable_excursion_then_loss | large_favorable_excursion_then_giveback | weak_positive_exit | strong_positive_exit | immediate_adverse_path | delayed_decay_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 0 (0.000) | 1 (0.048) | 0 (0.000) | 1 (0.048) | 12 (0.571) | 0 (0.000) | 7 (0.333) |
| 2021 | 82 | 0 (0.000) | 7 (0.085) | 0 (0.000) | 17 (0.207) | 38 (0.463) | 0 (0.000) | 20 (0.244) |
| 2022 | 83 | 0 (0.000) | 16 (0.193) | 0 (0.000) | 24 (0.289) | 23 (0.277) | 0 (0.000) | 20 (0.241) |
| 2023 | 73 | 0 (0.000) | 22 (0.301) | 0 (0.000) | 25 (0.342) | 17 (0.233) | 0 (0.000) | 9 (0.123) |
| 2024 | 26 | 0 (0.000) | 1 (0.038) | 0 (0.000) | 4 (0.154) | 14 (0.538) | 0 (0.000) | 7 (0.269) |
| 2025 | 16 | 0 (0.000) | 4 (0.250) | 0 (0.000) | 3 (0.188) | 1 (0.062) | 0 (0.000) | 8 (0.500) |
| 2026 | 9 | 0 (0.000) | 2 (0.222) | 0 (0.000) | 3 (0.333) | 3 (0.333) | 0 (0.000) | 1 (0.111) |

## 5. Era and Year Stability

The tables below summarize performance and path-shape stability across the requested splits and years.

| split | trade_count | win_rate | gross_expectancy_bps | net_expectancy_bps_12bps | profit_factor | avg_win_bps | avg_loss_bps | payoff_ratio | max_drawdown_pct | median_mfe_bps | median_giveback_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full sample | 310 | 0.597 | 56.003 | 44.003 | 1.929 | 194.865 | -149.513 | 1.303 | 25.913 | 131.888 | -104.066 |
| 2020-2023 | 259 | 0.606 | 63.760 | 51.760 | 2.210 | 192.098 | -133.780 | 1.436 | 16.894 | 124.788 | -95.544 |
| 2024-2026 | 51 | 0.549 | 16.612 | 4.612 | 1.168 | 210.381 | -219.282 | 0.959 | 25.913 | 184.837 | -176.505 |
| 2025 | 16 | 0.250 | -148.752 | -160.752 | 0.105 | 70.009 | -221.672 | 0.316 | 22.073 | 141.610 | -313.279 |
| 2026 | 9 | 0.667 | -4.282 | -16.282 | 0.947 | 113.651 | -240.148 | 0.473 | 5.435 | 129.631 | -86.240 |

| year | trade_count | win_rate | gross_expectancy_bps | net_expectancy_bps_12bps | profit_factor | avg_win_bps | avg_loss_bps | payoff_ratio | max_drawdown_pct | median_mfe_bps | median_giveback_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 0.619 | 103.086 | 91.086 | 2.942 | 252.288 | -139.367 | 1.810 | 5.170 | 209.071 | -122.683 |
| 2021 | 82 | 0.671 | 148.328 | 136.328 | 3.206 | 321.387 | -204.198 | 1.574 | 16.894 | 299.425 | -153.997 |
| 2022 | 83 | 0.566 | 16.204 | 4.204 | 1.289 | 127.694 | -129.352 | 0.987 | 13.172 | 94.734 | -90.635 |
| 2023 | 73 | 0.575 | 11.522 | -0.478 | 1.356 | 76.232 | -76.150 | 1.001 | 11.378 | 68.516 | -58.268 |
| 2024 | 26 | 0.692 | 125.606 | 113.606 | 2.964 | 273.819 | -207.872 | 1.317 | 5.449 | 251.376 | -122.702 |
| 2025 | 16 | 0.250 | -148.752 | -160.752 | 0.105 | 70.009 | -221.672 | 0.316 | 22.073 | 141.610 | -313.279 |
| 2026 | 9 | 0.667 | -4.282 | -16.282 | 0.947 | 113.651 | -240.148 | 0.473 | 5.435 | 129.631 | -86.240 |

## 6. Existing Context / Regime Attribution

Only columns already present in the trade log were considered. No new features were reconstructed, no OFI was rebuilt, and no classifier or threshold optimization was performed.

| column | status | missing_count | trade_count |
| --- | --- | --- | --- |
| regime | missing | 310 | 0 |
| signal_state | missing | 310 | 0 |
| trend | missing | 310 | 0 |
| range | missing | 310 | 0 |
| volatility | missing | 310 | 0 |
| context | missing | 310 | 0 |
| signal_label | missing | 310 | 0 |
| regime_label | missing | 310 | 0 |

## Interpretation

- Is recent failure more consistent with entry degradation? `False`
- Is recent failure more consistent with tail opportunity decay? `False`
- Is recent failure more consistent with giveback worsening? `True`
- Is recent failure more consistent with regime mismatch? `False`
- Is recent failure more consistent with sample-era dependence? `False`
- Is the result mixed or inconclusive? `False`
- Did any diagnostic rely on hindsight-only labels? `true`
- Are any labels live-tradable? `no`
- Does this approve any exit rule? `no`
- Does this approve alpha? `no`
- Does this approve paper/live trading? `no`
- Does this unblock OFI reconstruction? `no`

## Decision

decision: `recent_failure_giveback_worsening_dominated`

## Safety Notes

- Hindsight-only labels are explicitly not live-tradable.
- No row-level artifacts were written.
- No scripts outside this diagnostic were changed.
- Alpha remains blocked.
- Paper/live remains blocked.
- Full OFI reconstruction remains blocked.
