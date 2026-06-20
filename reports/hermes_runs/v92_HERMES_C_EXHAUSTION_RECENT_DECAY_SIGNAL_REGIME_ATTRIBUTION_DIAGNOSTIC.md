# V9.2 Hermes C Exhaustion Recent Decay Signal Regime Attribution Diagnostic

## Purpose

- Determine whether recent C Exhaustion degradation is driven by signal decay, regime mismatch, entry quality decay, tail-win compression, tail-loss expansion, cost sensitivity, year-specific concentration, or mixed degradation.
- Aggregate-only diagnostic against the frozen core trade log and bounded 750btc bars.
- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, or trading approval.

## Data and Field Availability

- trade log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar dir: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- trades inspected: `310`
- historical period: `2020-2024`
- recent decay period: `2025-2026`
- signal-state available: `true`
- regime labels available: `true`
- gross/net available: `true`
- MFE/MAE available: `true`
- cost assumptions available: `true`
- historical-period trade count: `285`
- recent-period trade count: `25`

### Field Status

| field_group | available | note |
| --- | --- | --- |
| trade entry timestamp | 1 | entry_time |
| trade year | 1 | year |
| bar size | 0 | not stored in the retained trade/context frame |
| horizon | 0 | not stored in the retained trade/context frame |
| side | 0 | not stored in the retained trade/context frame |
| entry signal state | 1 | derived signal-state buckets are available |
| original return bps | 1 | gross_return_bps |
| net return bps | 1 | net_return_bps |
| gross return bps | 1 | gross_return_bps |
| MFE / MAE | 1 | mfe_bps / mae_bps |
| exit class | 0 | original_final_class |
| regime labels | 1 | regime |
| volatility/range/trend labels | 1 | bucketed volatility/range/trend labels are present |
| MTF alignment labels | 0 | not present in the retained context |
| cost assumptions | 1 | gross/net returns imply mechanical cost drag |

### Missing Fields

- bar size
- horizon
- side
- exit class
- MTF alignment labels

### By-Year Trade Count

| year | count |
| --- | --- |
| 2020 | 21 |
| 2021 | 82 |
| 2022 | 83 |
| 2023 | 73 |
| 2024 | 26 |
| 2025 | 16 |
| 2026 | 9 |

## Synthetic Causality Checks

- period-label-uses-timestamp-only: `passed` (period=historical)
- future-bars-do-not-change-signal-context: `passed` (bucketed signal context remained unchanged)
- return-values-are-mechanical-only: `passed` (base_cost_drag=1.0, mutated_cost_drag=1.0)

## Period Comparison

| period | count | win_rate | average_return_bps | median_return_bps | p25_return_bps | p75_return_bps | p10_return_bps | p90_return_bps | gross_expectancy_bps | net_expectancy_bps | profit_factor | max_drawdown_bps | positive_tail_count | large_loss_count | average_winner_bps | average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| historical | 285 | 0.586 | 57.402 | 39.374 | -72.414 | 160.169 | -220.998 | 337.370 | 69.402 | 57.402 | 1.982 | -1769.609 | 60 | 30 | 197.755 | -141.233 |
| recent_decay | 25 | 0.360 | -108.743 | -91.340 | -242.845 | 34.889 | -306.000 | 151.086 | -96.743 | -108.743 | 0.237 | -2828.542 | 0 | 10 | 93.598 | -222.559 |

## By-Year Breakdown

| year | count | win_rate | average_return_bps | median_return_bps | p25_return_bps | p75_return_bps | p10_return_bps | p90_return_bps | gross_expectancy_bps | net_expectancy_bps | positive_tail_count | large_loss_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 0.619 | 91.086 | 111.138 | -43.756 | 246.913 | -181.482 | 347.036 | 103.086 | 91.086 | 8 | 2 |
| 2021 | 82 | 0.671 | 136.328 | 107.062 | -87.169 | 295.660 | -241.797 | 596.978 | 148.328 | 136.328 | 31 | 11 |
| 2022 | 83 | 0.518 | 4.204 | 13.778 | -76.551 | 77.886 | -232.060 | 190.091 | 16.204 | 4.204 | 8 | 11 |
| 2023 | 73 | 0.521 | -0.478 | 1.396 | -51.656 | 59.833 | -114.387 | 106.126 | 11.522 | -0.478 | 2 | 2 |
| 2024 | 26 | 0.692 | 113.606 | 122.030 | -130.376 | 333.368 | -264.464 | 429.261 | 125.606 | 113.606 | 11 | 4 |
| 2025 | 16 | 0.250 | -160.752 | -194.859 | -279.262 | -62.592 | -305.426 | 19.885 | -148.752 | -160.752 | 0 | 8 |
| 2026 | 9 | 0.556 | -16.282 | 52.321 | -26.013 | 93.369 | -274.220 | 190.755 | -4.282 | -16.282 | 0 | 2 |

## Tail Attribution

| period | count | win_rate | average_winner_bps | average_loser_bps | positive_tail_count | large_loss_count |
| --- | --- | --- | --- | --- | --- | --- |
| historical | 285 | 0.586 | 197.755 | -141.233 | 60 | 30 |
| recent_decay | 25 | 0.360 | 93.598 | -222.559 | 0 | 10 |

- historical positive tails: `60`
- recent positive tails: `0`
- historical large losses: `30`
- recent large losses: `10`
- historical average win: `197.755` bps
- recent average win: `93.598` bps
- historical average loss: `-141.233` bps
- recent average loss: `-222.559` bps

## Signal-State Attribution

### realized_vol_24_bars_bps_bucket

| bucket | count | historical_expectancy_bps | recent_expectancy_bps | historical_hit_rate | recent_hit_rate | average_winner_bps | average_loser_bps | tail_win_frequency | tail_loss_frequency | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <25 | 104 | -8.668 | n/a | 0.510 | n/a | 66.235 | -86.507 | 0.019 | 0.058 | n/a |
| 25-50 | 140 | 59.797 | -86.325 | 0.605 | 0.429 | 194.134 | -176.642 | 0.221 | 0.171 | -146.121 |
| 50-100 | 64 | 126.768 | -226.436 | 0.667 | 0.000 | 302.326 | -224.696 | 0.391 | 0.156 | -353.205 |
| >100 | 2 | 1269.530 | n/a | 1.000 | n/a | 1269.530 | n/a | 1.000 | 0.000 | n/a |

### range_expansion_ratio_24_bucket

| bucket | count | historical_expectancy_bps | recent_expectancy_bps | historical_hit_rate | recent_hit_rate | average_winner_bps | average_loser_bps | tail_win_frequency | tail_loss_frequency | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <0.75 | 26 | 224.671 | -466.976 | 0.708 | 0.000 | 380.235 | -222.873 | 0.346 | 0.192 | -691.646 |
| 0.75-1.25 | 139 | 46.831 | -73.489 | 0.544 | 0.357 | 195.246 | -142.848 | 0.216 | 0.137 | -120.320 |
| 1.25-2.00 | 109 | 51.847 | -83.974 | 0.630 | 0.444 | 173.649 | -171.559 | 0.183 | 0.128 | -135.821 |
| >2.00 | 36 | -1.977 | n/a | 0.528 | n/a | 79.790 | -93.364 | 0.028 | 0.056 | n/a |

### pre_signal_return_24_bars_bps_bucket

| bucket | count | historical_expectancy_bps | recent_expectancy_bps | historical_hit_rate | recent_hit_rate | average_winner_bps | average_loser_bps | tail_win_frequency | tail_loss_frequency | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <-200 | 154 | 89.485 | -80.038 | 0.600 | 0.357 | 267.502 | -190.775 | 0.292 | 0.182 | -169.523 |
| -200 to -100 | 96 | 51.428 | -172.068 | 0.625 | 0.250 | 141.205 | -125.630 | 0.146 | 0.073 | -223.496 |
| -100 to -25 | 58 | -9.258 | -73.829 | 0.509 | 0.667 | 67.036 | -97.919 | 0.017 | 0.086 | -64.571 |
| -25 to 25 | 2 | -92.415 | n/a | 0.000 | n/a | n/a | -92.415 | 0.000 | 0.000 | n/a |
| 25 to 100 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 100 to 200 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| >200 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### body_to_range_ratio_bucket

| bucket | count | historical_expectancy_bps | recent_expectancy_bps | historical_hit_rate | recent_hit_rate | average_winner_bps | average_loser_bps | tail_win_frequency | tail_loss_frequency | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <0.25 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 0.25-0.50 | 78 | 60.065 | -103.088 | 0.597 | 0.333 | 171.913 | -122.121 | 0.231 | 0.090 | -163.153 |
| >0.50 | 232 | 56.502 | -110.528 | 0.582 | 0.368 | 199.476 | -160.361 | 0.181 | 0.142 | -167.030 |

### volume_over_vol95_ratio_bucket

| bucket | count | historical_expectancy_bps | recent_expectancy_bps | historical_hit_rate | recent_hit_rate | average_winner_bps | average_loser_bps | tail_win_frequency | tail_loss_frequency | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <1.00 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 1.00-1.25 | 310 | 57.402 | -108.743 | 0.586 | 0.360 | 192.429 | -150.944 | 0.194 | 0.129 | -166.144 |
| 1.25-1.75 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| >1.75 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Regime Attribution

| regime | count | historical_expectancy_bps | recent_expectancy_bps | hit_rate | average_winner_bps | average_loser_bps | tail_win_count | tail_loss_count | net_degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXHAUSTED | 310 | 57.402 | -108.743 | 0.568 | 192.429 | -150.944 | 60 | 40 | -166.144 |

## Signal x Regime Interaction

### realized_vol_24_bars_bps_bucket

| signal_state | signal_bucket | regime_label | period | count | win_rate | expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- |
| realized_vol_24_bars_bps_bucket | <25 | EXHAUSTED | historical | 104 | 0.510 | -8.668 |
| realized_vol_24_bars_bps_bucket | <25 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| realized_vol_24_bars_bps_bucket | 25-50 | EXHAUSTED | historical | 119 | 0.605 | 59.797 |
| realized_vol_24_bars_bps_bucket | 25-50 | EXHAUSTED | recent_decay | 21 | 0.429 | -86.325 |
| realized_vol_24_bars_bps_bucket | 50-100 | EXHAUSTED | historical | 60 | 0.667 | 126.768 |
| realized_vol_24_bars_bps_bucket | 50-100 | EXHAUSTED | recent_decay | 4 | 0.000 | -226.436 |
| realized_vol_24_bars_bps_bucket | >100 | EXHAUSTED | historical | 2 | 1.000 | 1269.530 |
| realized_vol_24_bars_bps_bucket | >100 | EXHAUSTED | recent_decay | 0 | n/a | n/a |

### range_expansion_ratio_24_bucket

| signal_state | signal_bucket | regime_label | period | count | win_rate | expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- |
| range_expansion_ratio_24_bucket | <0.75 | EXHAUSTED | historical | 24 | 0.708 | 224.671 |
| range_expansion_ratio_24_bucket | <0.75 | EXHAUSTED | recent_decay | 2 | 0.000 | -466.976 |
| range_expansion_ratio_24_bucket | 0.75-1.25 | EXHAUSTED | historical | 125 | 0.544 | 46.831 |
| range_expansion_ratio_24_bucket | 0.75-1.25 | EXHAUSTED | recent_decay | 14 | 0.357 | -73.489 |
| range_expansion_ratio_24_bucket | 1.25-2.00 | EXHAUSTED | historical | 100 | 0.630 | 51.847 |
| range_expansion_ratio_24_bucket | 1.25-2.00 | EXHAUSTED | recent_decay | 9 | 0.444 | -83.974 |
| range_expansion_ratio_24_bucket | >2.00 | EXHAUSTED | historical | 36 | 0.528 | -1.977 |
| range_expansion_ratio_24_bucket | >2.00 | EXHAUSTED | recent_decay | 0 | n/a | n/a |

### pre_signal_return_24_bars_bps_bucket

| signal_state | signal_bucket | regime_label | period | count | win_rate | expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- |
| pre_signal_return_24_bars_bps_bucket | <-200 | EXHAUSTED | historical | 140 | 0.600 | 89.485 |
| pre_signal_return_24_bars_bps_bucket | <-200 | EXHAUSTED | recent_decay | 14 | 0.357 | -80.038 |
| pre_signal_return_24_bars_bps_bucket | -200 to -100 | EXHAUSTED | historical | 88 | 0.625 | 51.428 |
| pre_signal_return_24_bars_bps_bucket | -200 to -100 | EXHAUSTED | recent_decay | 8 | 0.250 | -172.068 |
| pre_signal_return_24_bars_bps_bucket | -100 to -25 | EXHAUSTED | historical | 55 | 0.509 | -9.258 |
| pre_signal_return_24_bars_bps_bucket | -100 to -25 | EXHAUSTED | recent_decay | 3 | 0.667 | -73.829 |
| pre_signal_return_24_bars_bps_bucket | -25 to 25 | EXHAUSTED | historical | 2 | 0.000 | -92.415 |
| pre_signal_return_24_bars_bps_bucket | -25 to 25 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | 25 to 100 | EXHAUSTED | historical | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | 25 to 100 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | 100 to 200 | EXHAUSTED | historical | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | 100 to 200 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | >200 | EXHAUSTED | historical | 0 | n/a | n/a |
| pre_signal_return_24_bars_bps_bucket | >200 | EXHAUSTED | recent_decay | 0 | n/a | n/a |

### body_to_range_ratio_bucket

| signal_state | signal_bucket | regime_label | period | count | win_rate | expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- |
| body_to_range_ratio_bucket | <0.25 | EXHAUSTED | historical | 0 | n/a | n/a |
| body_to_range_ratio_bucket | <0.25 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| body_to_range_ratio_bucket | 0.25-0.50 | EXHAUSTED | historical | 72 | 0.597 | 60.065 |
| body_to_range_ratio_bucket | 0.25-0.50 | EXHAUSTED | recent_decay | 6 | 0.333 | -103.088 |
| body_to_range_ratio_bucket | >0.50 | EXHAUSTED | historical | 213 | 0.582 | 56.502 |
| body_to_range_ratio_bucket | >0.50 | EXHAUSTED | recent_decay | 19 | 0.368 | -110.528 |

### volume_over_vol95_ratio_bucket

| signal_state | signal_bucket | regime_label | period | count | win_rate | expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- |
| volume_over_vol95_ratio_bucket | <1.00 | EXHAUSTED | historical | 0 | n/a | n/a |
| volume_over_vol95_ratio_bucket | <1.00 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| volume_over_vol95_ratio_bucket | 1.00-1.25 | EXHAUSTED | historical | 285 | 0.586 | 57.402 |
| volume_over_vol95_ratio_bucket | 1.00-1.25 | EXHAUSTED | recent_decay | 25 | 0.360 | -108.743 |
| volume_over_vol95_ratio_bucket | 1.25-1.75 | EXHAUSTED | historical | 0 | n/a | n/a |
| volume_over_vol95_ratio_bucket | 1.25-1.75 | EXHAUSTED | recent_decay | 0 | n/a | n/a |
| volume_over_vol95_ratio_bucket | >1.75 | EXHAUSTED | historical | 0 | n/a | n/a |
| volume_over_vol95_ratio_bucket | >1.75 | EXHAUSTED | recent_decay | 0 | n/a | n/a |

## Cost Sensitivity Attribution

| period | gross_expectancy_bps | net_expectancy_bps | cost_drag_bps | cost_share_of_positive_gross_edge |
| --- | --- | --- | --- | --- |
| historical | 69.402 | 57.402 | 12.000 | 0.173 |
| recent_decay | -96.743 | -108.743 | 12.000 | n/a |

### Mechanical Cost Read

- historical gross expectancy: `69.402` bps
- historical net expectancy: `57.402` bps
- recent gross expectancy: `-96.743` bps
- recent net expectancy: `-108.743` bps
- historical cost drag: `12.000` bps
- recent cost drag: `12.000` bps
- costs are mechanically applied and remain flat at the established trade-log gap; they do not explain the sign flip on their own.

## Interpretation

- primary degradation explanation: `mixed_degradation_no_single_driver`
- why: The decay is spread across win-side compression, loss-side expansion, and signal-state deterioration without a single dominant slice.
- historical vs recent net expectancy: `57.402` bps vs `-108.743` bps
- historical vs recent win rate: `58.596%` vs `36.000%`
- historical vs recent positive-tail count: `60` vs `0`
- historical vs recent large-loss count: `30` vs `10`

## Stop / Go Conclusion

- decision: `keep_research_anchor_alive_but_collect_more_inputs`
- the anchor remains research-valid historically, but the recent degradation is broad enough that the next step should be more upstream attribution rather than another exit patch.

