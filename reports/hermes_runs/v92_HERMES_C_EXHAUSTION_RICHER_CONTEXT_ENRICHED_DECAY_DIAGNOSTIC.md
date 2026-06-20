# V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic

## Purpose

- Determine whether richer safe known-at-entry and pre-entry explanatory fields can explain recent C Exhaustion decay.
- Aggregate-only diagnostic against the frozen core replay output and bounded 750btc bars.
- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, modeling dataset, or trading approval.

## Population Accounting

- total trades inspected: `310`
- historical-period trade count: `285`
- recent-period trade count: `25`
- by-year trade count: `2020:21, 2021:82, 2022:83, 2023:73, 2024:26, 2025:16, 2026:9`

### Fields

| field | status | notes |
| --- | --- | --- |
| trade entry timestamp | available | entry_time |
| year / period label | available | year -> historical/recent split |
| trade_density | available | trade_count from 750btc bars |
| local_trend_range_state | available | native range-trend state carried forward |
| weekday_weekend_effect | available | weekday/weekend flag from entry_time |
| bar size | available | static replay config: 750 |
| horizon | available | static replay config: 36 bars |
| side | available | long-only assumed; side column absent |
| original return bps | available | gross_return_bps |
| gross return bps | available | gross_return_bps |
| net return bps | available | net_return_bps |
| MFE / MAE | available | computed from trade log and bounded bars |
| exit class | available | excursion_class / exit_class |
| signal state | available | c_signal / excursion-class context |
| regime_label | available | EXHAUSTED regime dominates |
| volatility_label | available | 24-bar realized-vol bucket |
| range_trend_label | available | 24-bar trend / failed-reversal / range label |
| distance_from_recent_high_low | available | normalized position inside prior 24-bar range |
| distance_from_vwap | available | close-vwap basis points |
| prior_bar_return_path | available | pre-signal 24-bar return bucket |
| cvd_delta | available | volume_delta sign bucket |
| session_time_of_day_labels | available | UTC session bucket |
| raw L2 | blocked | not read |
| OFI | blocked | not generated |
| row-level export | blocked | not written |
| future-return-derived eligibility labels | blocked | post-hoc only |

- fields available: `trade entry timestamp, year / period label, trade_density, local_trend_range_state, weekday_weekend_effect, bar size, horizon, side, original return bps, gross return bps, net return bps, MFE / MAE, exit class, signal state, regime_label, volatility_label, range_trend_label, distance_from_recent_high_low, distance_from_vwap, prior_bar_return_path, cvd_delta, session_time_of_day_labels`
- fields missing: `none among the safe field set`
- fields used: `trade entry timestamp, year / period label, bar size, horizon, side, trade_density, local_trend_range_state, weekday_weekend_effect, original return bps, gross return bps, net return bps, MFE / MAE, exit class, signal state, regime_label, volatility_label, range_trend_label, distance_from_recent_high_low, distance_from_vwap, prior_bar_return_path, cvd_delta, session_time_of_day_labels`
- fields blocked: `raw L2, OFI, row-level export, future-return-derived eligibility labels, raw L2, OFI, row-level export, future-return-derived eligibility labels`

## Baseline Period Comparison

| period | count | win_rate | average_return_bps | median_return_bps | p25_return_bps | p75_return_bps | p10_return_bps | p90_return_bps | gross_expectancy_bps | net_expectancy_bps | profit_factor | max_drawdown_bps | positive_tail_count | large_loss_count | average_winner_bps | average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| historical | 285 | 0.586 | 57.402 | 39.374 | -72.414 | 160.169 | -220.998 | 337.370 | 69.402 | 57.402 | 1.982 | -1769.609 | 60 | 30 | 197.755 | -141.233 |
| recent | 25 | 0.360 | -108.743 | -91.340 | -242.845 | 34.889 | -306.000 | 151.086 | -96.743 | -108.743 | 0.237 | -2828.542 | 0 | 10 | 93.598 | -222.559 |

## By-Year Breakdown

| year | count | win_rate | average_return_bps | median_return_bps | p25_return_bps | p75_return_bps | p10_return_bps | p90_return_bps | positive_tail_count | large_loss_count | gross_expectancy_bps | net_expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 0.619 | 91.086 | 111.138 | -43.756 | 246.913 | -181.482 | 347.036 | 8 | 2 | 103.086 | 91.086 |
| 2021 | 82 | 0.671 | 136.328 | 107.062 | -87.169 | 295.660 | -241.797 | 596.978 | 31 | 11 | 148.328 | 136.328 |
| 2022 | 83 | 0.518 | 4.204 | 13.778 | -76.551 | 77.886 | -232.060 | 190.091 | 8 | 11 | 16.204 | 4.204 |
| 2023 | 73 | 0.521 | -0.478 | 1.396 | -51.656 | 59.833 | -114.387 | 106.126 | 2 | 2 | 11.522 | -0.478 |
| 2024 | 26 | 0.692 | 113.606 | 122.030 | -130.376 | 333.368 | -264.464 | 429.261 | 11 | 4 | 125.606 | 113.606 |
| 2025 | 16 | 0.250 | -160.752 | -194.859 | -279.262 | -62.592 | -305.426 | 19.885 | 0 | 8 | -148.752 | -160.752 |
| 2026 | 9 | 0.556 | -16.282 | 52.321 | -26.013 | 93.369 | -274.220 | 190.755 | 0 | 2 | -4.282 | -16.282 |

## Single-Field Richer Context Attribution

### trade_density

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| low | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| medium | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| high | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| n/a | 285 | 25 | 57.402 | -108.743 | 0.586 | 0.360 | 0.211 | 0.000 | 0.105 | 0.400 | -166.144 | 197.755 | 93.598 | -141.233 | -222.559 | 12.000 | 12.000 |

### distance_from_vwap

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| below -100 bps | 3 | 0 | 314.199 | n/a | 1.000 | n/a | 0.667 | n/a | 0.000 | n/a | n/a | 314.199 | n/a | n/a | n/a | 12.000 | n/a |
| -100 to -25 bps | 112 | 14 | 105.360 | -83.101 | 0.607 | 0.429 | 0.286 | 0.000 | 0.134 | 0.357 | -188.460 | 280.103 | 89.535 | -164.698 | -212.577 | 12.000 | 12.000 |
| -25 to +25 bps | 170 | 11 | 21.274 | -141.378 | 0.565 | 0.273 | 0.153 | 0.000 | 0.088 | 0.455 | -162.652 | 135.786 | 101.724 | -127.281 | -232.541 | 12.000 | 12.000 |
| +25 to +100 bps | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| above +100 bps | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### distance_from_recent_high_low

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| near recent low | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| middle range | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| near recent high | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| n/a | 285 | 25 | 57.402 | -108.743 | 0.586 | 0.360 | 0.211 | 0.000 | 0.105 | 0.400 | -166.144 | 197.755 | 93.598 | -141.233 | -222.559 | 12.000 | 12.000 |

### prior_bar_return_path

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| negative | 283 | 25 | 58.461 | -108.743 | 0.590 | 0.360 | 0.212 | 0.000 | 0.106 | 0.400 | -167.203 | 197.755 | 93.598 | -142.075 | -222.559 | 12.000 | 12.000 |
| flat | 2 | 0 | -92.415 | n/a | 0.000 | n/a | 0.000 | n/a | 0.000 | n/a | n/a | n/a | n/a | -92.415 | n/a | 12.000 | n/a |
| positive | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### cvd_delta

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| negative | 265 | 24 | 57.233 | -121.172 | 0.592 | 0.333 | 0.215 | 0.000 | 0.102 | 0.417 | -178.405 | 195.290 | 81.603 | -143.461 | -222.559 | 12.000 | 12.000 |
| neutral | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| positive | 20 | 1 | 59.642 | 189.564 | 0.500 | 1.000 | 0.150 | 0.000 | 0.150 | 0.000 | 129.922 | 236.456 | 189.564 | -117.172 | n/a | 12.000 | 12.000 |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### session_time_of_day_labels

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| asia | 77 | 4 | 7.610 | -172.394 | 0.494 | 0.250 | 0.169 | 0.000 | 0.169 | 0.250 | -180.004 | 168.883 | 1.558 | -149.528 | -230.378 | 12.000 | 12.000 |
| europe | 59 | 5 | 87.182 | -77.553 | 0.627 | 0.600 | 0.237 | 0.000 | 0.051 | 0.400 | -164.734 | 195.577 | 145.801 | -95.119 | -412.583 | 12.000 | 12.000 |
| overlap | 47 | 4 | 69.758 | -54.506 | 0.596 | 0.250 | 0.191 | 0.000 | 0.085 | 0.250 | -124.264 | 197.631 | 190.709 | -118.687 | -136.244 | 12.000 | 12.000 |
| us | 102 | 12 | 72.071 | -118.600 | 0.627 | 0.333 | 0.235 | 0.000 | 0.098 | 0.500 | -190.671 | 216.211 | 53.178 | -170.691 | -204.490 | 12.000 | 12.000 |
| session_unknown | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### weekday_weekend_effect

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weekday | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| weekend | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| unknown | 285 | 25 | 57.402 | -108.743 | 0.586 | 0.360 | 0.211 | 0.000 | 0.105 | 0.400 | -166.144 | 197.755 | 93.598 | -141.233 | -222.559 | 12.000 | 12.000 |

### local_trend_range_state

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trend_continuation | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| failed_reversal | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion | 136 | 9 | 37.600 | -83.974 | 0.603 | 0.444 | 0.154 | 0.000 | 0.096 | 0.333 | -121.574 | 157.343 | 62.081 | -144.233 | -200.818 | 12.000 | 12.000 |
| range | 102 | 9 | 177.681 | 1.903 | 0.794 | 0.556 | 0.373 | 0.000 | 0.020 | 0.222 | -175.777 | 243.704 | 118.812 | -76.981 | -144.233 | 12.000 | 12.000 |
| mixed | 47 | 7 | -146.329 | -282.847 | 0.085 | 0.000 | 0.021 | 0.000 | 0.319 | 0.714 | -136.518 | 95.717 | n/a | -168.845 | -282.847 | 12.000 | 12.000 |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### volatility_label

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <25 | 104 | 0 | -8.668 | n/a | 0.510 | n/a | 0.019 | n/a | 0.058 | n/a | n/a | 66.235 | n/a | -86.507 | n/a | 12.000 | n/a |
| 25-50 | 119 | 21 | 59.797 | -86.325 | 0.605 | 0.429 | 0.261 | 0.000 | 0.134 | 0.381 | -146.121 | 206.701 | 93.598 | -165.249 | -221.267 | 12.000 | 12.000 |
| 50-100 | 60 | 4 | 126.768 | -226.436 | 0.667 | 0.000 | 0.417 | 0.000 | 0.133 | 0.500 | -353.205 | 302.326 | n/a | -224.348 | -226.436 | 12.000 | 12.000 |
| >100 | 2 | 0 | 1269.530 | n/a | 1.000 | n/a | 1.000 | n/a | 0.000 | n/a | n/a | 1269.530 | n/a | n/a | n/a | 12.000 | n/a |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### range_trend_label

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trend_continuation | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| failed_reversal | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion | 136 | 9 | 37.600 | -83.974 | 0.603 | 0.444 | 0.154 | 0.000 | 0.096 | 0.333 | -121.574 | 157.343 | 62.081 | -144.233 | -200.818 | 12.000 | 12.000 |
| range | 102 | 9 | 177.681 | 1.903 | 0.794 | 0.556 | 0.373 | 0.000 | 0.020 | 0.222 | -175.777 | 243.704 | 118.812 | -76.981 | -144.233 | 12.000 | 12.000 |
| mixed | 47 | 7 | -146.329 | -282.847 | 0.085 | 0.000 | 0.021 | 0.000 | 0.319 | 0.714 | -136.518 | 95.717 | n/a | -168.845 | -282.847 | 12.000 | 12.000 |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### regime_label

| bucket | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | historical_positive_tail_frequency | recent_positive_tail_frequency | historical_large_loss_frequency | recent_large_loss_frequency | degradation_bps | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps | historical_cost_drag_bps | recent_cost_drag_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXHAUSTED | 285 | 25 | 57.402 | -108.743 | 0.586 | 0.360 | 0.211 | 0.000 | 0.105 | 0.400 | -166.144 | 197.755 | 93.598 | -141.233 | -222.559 | 12.000 | 12.000 |
| n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Tail Attribution Summary

- The detailed bucket tables above show whether the recent deterioration comes from fewer large winners, smaller winners, larger losers, more frequent large losses, a lower hit rate, or flat cost drag.
- The regime label is effectively constant EXHAUSTED, so any apparent regime separation should be treated as descriptive only and not over-interpreted.

## Preregistered Interaction Attribution

### trade_density_bucket × local_trend_range_state

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a × mixed | 47 | 7 | -146.329 | -282.847 | 0.085 | 0.000 | -0.021 | 0.395 | -136.518 | 1 | 95.717 | n/a | -168.845 | -282.847 |
| n/a × range | 102 | 9 | 177.681 | 1.903 | 0.794 | 0.556 | -0.373 | 0.203 | -175.777 | 1 | 243.704 | 118.812 | -76.981 | -144.233 |
| n/a × range_expansion | 136 | 9 | 37.600 | -83.974 | 0.603 | 0.444 | -0.154 | 0.238 | -121.574 | 1 | 157.343 | 62.081 | -144.233 | -200.818 |

### trade_density_bucket × distance_from_vwap_bucket

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a × -100 to -25 bps | 112 | 14 | 105.360 | -83.101 | 0.607 | 0.429 | -0.286 | 0.223 | -188.460 | 1 | 280.103 | 89.535 | -164.698 | -212.577 |
| n/a × -25 to +25 bps | 170 | 11 | 21.274 | -141.378 | 0.565 | 0.273 | -0.153 | 0.366 | -162.652 | 1 | 135.786 | 101.724 | -127.281 | -232.541 |
| n/a × below -100 bps | 3 | 0 | 314.199 | n/a | 1.000 | n/a | n/a | n/a | n/a | 0 | 314.199 | n/a | n/a | n/a |

### trade_density_bucket × cvd_delta_bucket

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a × negative | 265 | 24 | 57.233 | -121.172 | 0.592 | 0.333 | -0.215 | 0.315 | -178.405 | 1 | 195.290 | 81.603 | -143.461 | -222.559 |
| n/a × positive | 20 | 1 | 59.642 | 189.564 | 0.500 | 1.000 | -0.150 | -0.150 | 129.922 | 0 | 236.456 | 189.564 | -117.172 | n/a |

### distance_from_recent_high_low_bucket × local_trend_range_state

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a × mixed | 47 | 7 | -146.329 | -282.847 | 0.085 | 0.000 | -0.021 | 0.395 | -136.518 | 1 | 95.717 | n/a | -168.845 | -282.847 |
| n/a × range | 102 | 9 | 177.681 | 1.903 | 0.794 | 0.556 | -0.373 | 0.203 | -175.777 | 1 | 243.704 | 118.812 | -76.981 | -144.233 |
| n/a × range_expansion | 136 | 9 | 37.600 | -83.974 | 0.603 | 0.444 | -0.154 | 0.238 | -121.574 | 1 | 157.343 | 62.081 | -144.233 | -200.818 |

### distance_from_vwap_bucket × local_trend_range_state

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -100 to -25 bps × mixed | 17 | 2 | -175.855 | -362.687 | 0.059 | 0.000 | 0.000 | 0.588 | -186.831 | 0 | 14.778 | n/a | -187.770 | -362.687 |
| -100 to -25 bps × range | 34 | 4 | 306.583 | 18.722 | 0.824 | 0.500 | -0.588 | 0.221 | -287.861 | 0 | 403.007 | 144.444 | -143.396 | -107.000 |
| -100 to -25 bps × range_expansion | 61 | 8 | 71.574 | -64.115 | 0.639 | 0.500 | -0.197 | 0.135 | -135.689 | 1 | 198.667 | 62.081 | -153.728 | -190.311 |
| -25 to +25 bps × mixed | 30 | 5 | -129.598 | -250.911 | 0.100 | 0.000 | -0.033 | 0.333 | -121.313 | 1 | 122.697 | n/a | -157.631 | -250.911 |
| -25 to +25 bps × range | 68 | 5 | 113.230 | -11.551 | 0.779 | 0.600 | -0.265 | 0.185 | -124.781 | 1 | 159.544 | 101.724 | -50.415 | -181.465 |
| -25 to +25 bps × range_expansion | 72 | 1 | -2.709 | -242.845 | 0.556 | 0.000 | -0.097 | 0.917 | -240.137 | 0 | 105.289 | n/a | -137.705 | -242.845 |
| below -100 bps × range_expansion | 3 | 0 | 314.199 | n/a | 1.000 | n/a | n/a | n/a | n/a | 0 | 314.199 | n/a | n/a | n/a |

### cvd_delta_bucket × local_trend_range_state

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| negative × mixed | 43 | 7 | -148.905 | -282.847 | 0.093 | 0.000 | -0.023 | 0.389 | -133.942 | 1 | 95.717 | n/a | -173.994 | -282.847 |
| negative × range | 91 | 9 | 183.739 | 1.903 | 0.824 | 0.556 | -0.396 | 0.211 | -181.836 | 1 | 238.197 | 118.812 | -71.532 | -144.233 |
| negative × range_expansion | 131 | 8 | 37.018 | -118.166 | 0.595 | 0.375 | -0.153 | 0.283 | -155.184 | 1 | 159.139 | 19.587 | -142.708 | -200.818 |
| positive × mixed | 4 | 0 | -118.642 | n/a | 0.000 | n/a | n/a | n/a | n/a | 0 | n/a | n/a | -118.642 | n/a |
| positive × range | 11 | 0 | 127.563 | n/a | 0.545 | n/a | n/a | n/a | n/a | 0 | 312.547 | n/a | -94.419 | n/a |
| positive × range_expansion | 5 | 1 | 52.844 | 189.564 | 0.800 | 1.000 | -0.200 | -0.200 | 136.720 | 0 | 122.321 | 189.564 | -225.062 | n/a |

### session_time_of_day_labels × trade_density_bucket

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| asia × n/a | 77 | 4 | 7.610 | -172.394 | 0.494 | 0.250 | -0.169 | 0.081 | -180.004 | 0 | 168.883 | 1.558 | -149.528 | -230.378 |
| europe × n/a | 59 | 5 | 87.182 | -77.553 | 0.627 | 0.600 | -0.237 | 0.349 | -164.734 | 1 | 195.577 | 145.801 | -95.119 | -412.583 |
| overlap × n/a | 47 | 4 | 69.758 | -54.506 | 0.596 | 0.250 | -0.191 | 0.165 | -124.264 | 0 | 197.631 | 190.709 | -118.687 | -136.244 |
| us × n/a | 102 | 12 | 72.071 | -118.600 | 0.627 | 0.333 | -0.235 | 0.402 | -190.671 | 1 | 216.211 | 53.178 | -170.691 | -204.490 |

### weekday_weekend_effect × session_time_of_day_labels

| interaction | historical_count | recent_count | historical_expectancy_bps | recent_expectancy_bps | historical_win_rate | recent_win_rate | positive_tail_frequency_change | large_loss_frequency_change | degradation_bps | sample_sufficient | historical_average_winner_bps | recent_average_winner_bps | historical_average_loser_bps | recent_average_loser_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| unknown × asia | 77 | 4 | 7.610 | -172.394 | 0.494 | 0.250 | -0.169 | 0.081 | -180.004 | 0 | 168.883 | 1.558 | -149.528 | -230.378 |
| unknown × europe | 59 | 5 | 87.182 | -77.553 | 0.627 | 0.600 | -0.237 | 0.349 | -164.734 | 1 | 195.577 | 145.801 | -95.119 | -412.583 |
| unknown × overlap | 47 | 4 | 69.758 | -54.506 | 0.596 | 0.250 | -0.191 | 0.165 | -124.264 | 0 | 197.631 | 190.709 | -118.687 | -136.244 |
| unknown × us | 102 | 12 | 72.071 | -118.600 | 0.627 | 0.333 | -0.235 | 0.402 | -190.671 | 1 | 216.211 | 53.178 | -170.691 | -204.490 |

## Segment Stability

| segment_type | segment | historical_count | recent_count | by_year_count | by_year_expectancy | benefit_in_more_than_one_year | recent_sample_sparse | stable_for_design_only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| field | distance_from_vwap=-100 to -25 bps | 112 | 14 | 2020:7, 2021:49, 2022:26, 2023:12, 2024:18, 2025:8, 2026:6 | 2020:219.267, 2021:163.345, 2022:-14.089, 2023:23.212, 2024:130.515, 2025:-185.022, 2026:52.795 | 1 | 0 | 1 |
| field | session_time_of_day_labels=europe | 59 | 5 | 2020:9, 2021:20, 2022:10, 2023:16, 2024:4, 2025:1, 2026:4 | 2020:102.013, 2021:220.964, 2022:-57.709, 2023:31.642, 2024:-30.713, 2025:-308.294, 2026:-19.867 | 1 | 1 | 0 |
| field | local_trend_range_state=range | 102 | 9 | 2020:10, 2021:35, 2022:29, 2023:17, 2024:11, 2025:4, 2026:5 | 2020:178.439, 2021:299.307, 2022:91.636, 2023:34.991, 2024:237.365, 2025:-34.333, 2026:30.892 | 1 | 1 | 0 |
| field | range_trend_label=range | 102 | 9 | 2020:10, 2021:35, 2022:29, 2023:17, 2024:11, 2025:4, 2026:5 | 2020:178.439, 2021:299.307, 2022:91.636, 2023:34.991, 2024:237.365, 2025:-34.333, 2026:30.892 | 1 | 1 | 0 |
| interaction | trade_density_bucket × local_trend_range_state=n/a × range | 102 | 9 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | trade_density_bucket × distance_from_vwap_bucket=n/a × -100 to -25 bps | 112 | 14 | aggregate-only | aggregate-only | 0 | 0 | 1 |
| interaction | distance_from_recent_high_low_bucket × local_trend_range_state=n/a × range | 102 | 9 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | distance_from_vwap_bucket × local_trend_range_state=-100 to -25 bps × range_expansion | 61 | 8 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | distance_from_vwap_bucket × local_trend_range_state=-25 to +25 bps × range | 68 | 5 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | cvd_delta_bucket × local_trend_range_state=negative × range | 91 | 9 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | session_time_of_day_labels × trade_density_bucket=europe × n/a | 59 | 5 | aggregate-only | aggregate-only | 0 | 1 | 0 |
| interaction | weekday_weekend_effect × session_time_of_day_labels=unknown × europe | 59 | 5 | aggregate-only | aggregate-only | 0 | 1 | 0 |

## Synthetic Causality / Leakage Checks

- period-label-uses-timestamp-only: `passed` (period=historical)
- return-outcomes-are-post-hoc-only: `passed` (base_gross=120.0, mutated_gross=999.0)
- no-future-path-used-for-eligibility: `passed` (eligibility relies on entry-side fields only)
- raw-L2-and-OFI-blocked-by-design: `passed` (raw L2 not read; OFI not generated; row-level artifacts not exported)
- period assignment uses timestamp only
- each explanatory field is known at or before entry
- continuous bins are fixed before looking at outcomes
- native labels are not derived from future returns
- return outcomes are used only for aggregate attribution
- no future path information is used to define eligibility
- no raw L2 is read
- OFI is not generated
- no row-level artifacts are exported
- no modeling dataset is created
- missing fields are not silently treated as safe

## Interpretation

- primary enriched explanation: `local_trend_range_context_degradation_dominant`
- why: Local trend/range state separated the sample more clearly than the other safe richer-context fields.
- historical net expectancy: `57.402` bps
- recent net expectancy: `-108.743` bps
- historical win rate: `58.60%`
- recent win rate: `36.00%`
- historical positive tails: `60`
- recent positive tails: `0`
- historical large losses: `30`
- recent large losses: `10`

## Stop / Go Conclusion

- decision: `keep_anchor_alive_but_collect_more_inputs`
- no segment is approved for strategy use in this diagnostic.

