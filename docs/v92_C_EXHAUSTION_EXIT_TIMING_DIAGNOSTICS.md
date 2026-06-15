# C_ExhaustionFade Exit-Timing Diagnostics

## Purpose

This report tests whether the repaired C_ExhaustionFade strategy is losing edge because the fixed 36-bar exit is too slow for the recent market, because favorable excursion is decaying, because adverse continuation is worse, or because the alpha has died.

## Data Sources

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay helpers: `load_750btc_bars`, `normalize_v92_bar_timestamps`
- Replay artifacts: `reports/c_exhaustion_replay_post_regime_fix/`

Signal-field note: All requested signal fields were available directly from the canonical signal frame or derivable from retained primitives. `volume_over_vol95_ratio` and `body_to_range_ratio` were computed from `volume / vol_roll_95` and `body_size / bar_range` respectively.

## Executive Finding

Recent-period decay is most consistent with exit-horizon mismatch and positive-tail decay, with adverse continuation also contributing. Recent trades reach their favorable move earlier than the early-period sample, but the fixed 36-bar exit often gives that move back before realization.

Canonical anchor reference:

| trade_count | net_expectancy_bps | win_rate | profit_factor | calendar_daily_sharpe_365 | business_day_sharpe_252 |
| --- | --- | --- | --- | --- | --- |
| 310 | 44.003106 | 0.567742 | 1.674411 | 1.473205 | 1.224101 |

## Early vs Middle vs Recent Exit Timing

| period | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | median_mfe_bps | avg_mae_bps | median_mae_bps | avg_time_to_mfe_bars | median_time_to_mfe_bars | avg_time_to_mae_bars | median_time_to_mae_bars | avg_mfe_giveback_bps | median_mfe_giveback_bps | avg_mfe_capture_ratio | median_mfe_capture_ratio | share_mfe_before_6_bars | share_mfe_before_12_bars | share_mfe_before_18_bars | share_mfe_before_24_bars | share_mfe_before_36_bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 103 | 127.104273 | 0.660194 | 2.857439 | 331.241537 | 275.310689 | -209.788936 | -156.640715 | 19.320388 | 19.000000 | 12.320388 | 6.000000 | 192.137263 | 137.338237 | -0.889348 | 0.489345 | 0.213592 | 0.339806 | 0.456311 | 0.563107 | 1.000000 |
| middle_period | 182 | 17.954874 | 0.543956 | 1.339784 | 142.873869 | 91.798045 | -112.062019 | -75.307963 | 17.164835 | 15.500000 | 15.670330 | 14.000000 | 112.918995 | 74.407922 | -1.484531 | 0.317126 | 0.252747 | 0.423077 | 0.543956 | 0.631868 | 1.000000 |
| recent_period | 25 | -108.742570 | 0.360000 | 0.236562 | 153.631562 | 129.630909 | -233.962608 | -230.278520 | 12.360000 | 7.000000 | 21.760000 | 26.000000 | 250.374132 | 260.577352 | -5.234371 | -0.420109 | 0.440000 | 0.600000 | 0.680000 | 0.720000 | 1.000000 |

Answer to question 1: yes. Recent average time-to-MFE is 12.360000 bars versus 19.320388 early, and the median is 7.000000 versus 19.000000 early.
Answer to question 2: yes. Recent average MFE giveback is 250.374132 bps, and the favorable move is often handed back before the fixed exit, so much of it is not retained.

## Diagnostic Horizon Comparison

Diagnostic horizons indicate where favorable excursion existed, but this report does not select or approve a replacement exit rule.

| period | horizon_bars | gross_expectancy_bps | win_rate | profit_factor | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 3 | 35.524815 | 0.601942 | 2.084765 | 8 | 0.077670 | 5 | 0.048544 |
| early_period | 6 | 57.951122 | 0.660194 | 2.887622 | 12 | 0.116505 | 3 | 0.029126 |
| early_period | 9 | 67.953716 | 0.660194 | 2.624234 | 21 | 0.203883 | 6 | 0.058252 |
| early_period | 12 | 90.746079 | 0.640777 | 3.163844 | 28 | 0.271845 | 4 | 0.038835 |
| early_period | 18 | 113.893950 | 0.660194 | 3.575396 | 33 | 0.320388 | 7 | 0.067961 |
| early_period | 24 | 120.861933 | 0.669903 | 3.253692 | 35 | 0.339806 | 9 | 0.087379 |
| early_period | 36 | 139.104273 | 0.660194 | 3.161610 | 41 | 0.398058 | 13 | 0.126214 |
| early_period | 48 | 112.094799 | 0.582524 | 2.204120 | 42 | 0.407767 | 20 | 0.194175 |
| middle_period | 3 | 12.887615 | 0.631868 | 1.789306 | 3 | 0.016484 | 1 | 0.005495 |
| middle_period | 6 | 22.599865 | 0.615385 | 2.375294 | 5 | 0.027473 | 1 | 0.005495 |
| middle_period | 9 | 18.950520 | 0.598901 | 1.854910 | 4 | 0.021978 | 3 | 0.016484 |
| middle_period | 12 | 17.932554 | 0.604396 | 1.672315 | 6 | 0.032967 | 2 | 0.010989 |
| middle_period | 18 | 27.165969 | 0.598901 | 1.854289 | 16 | 0.087912 | 5 | 0.027473 |
| middle_period | 24 | 26.815263 | 0.587912 | 1.679705 | 17 | 0.093407 | 9 | 0.049451 |
| middle_period | 36 | 29.954874 | 0.587912 | 1.628065 | 22 | 0.120879 | 17 | 0.093407 |
| middle_period | 48 | 29.618080 | 0.571429 | 1.509138 | 25 | 0.137363 | 21 | 0.115385 |
| recent_period | 3 | 11.079259 | 0.480000 | 1.498968 | 1 | 0.040000 | 0 | 0.000000 |
| recent_period | 6 | 4.576398 | 0.480000 | 1.095116 | 1 | 0.040000 | 0 | 0.000000 |
| recent_period | 9 | -1.267180 | 0.400000 | 0.979984 | 2 | 0.080000 | 1 | 0.040000 |
| recent_period | 12 | 10.638843 | 0.400000 | 1.232113 | 3 | 0.120000 | 0 | 0.000000 |
| recent_period | 18 | -20.002339 | 0.400000 | 0.728520 | 3 | 0.120000 | 3 | 0.120000 |
| recent_period | 24 | -47.334977 | 0.400000 | 0.419417 | 1 | 0.040000 | 4 | 0.160000 |
| recent_period | 36 | -96.742570 | 0.400000 | 0.284555 | 3 | 0.120000 | 9 | 0.360000 |
| recent_period | 48 | -113.580655 | 0.320000 | 0.330442 | 4 | 0.160000 | 9 | 0.360000 |

Answer to question 3: yes. For the recent period, 3-bar gross expectancy is 11.079259, 6-bar is 4.576398, 12-bar is 10.638843, and 36-bar is -96.742570. The shorter horizons capture more of the recent edge than the configured 36-bar exit.

## Recent Failure Modes

Recent losers still showed favorable excursion: 16 of 16 recent losers had positive MFE.
Recent trades reaching >200 bps MFE: 7; recent trades realizing >=200 bps net: 0.
Recent average MAE is -233.962608 bps versus -209.788936 early, so adverse continuation is also more severe.

| time_bucket | trade_count | net_expectancy_bps | win_rate | avg_mfe_bps | avg_mae_bps | avg_mfe_giveback_bps | avg_mfe_capture_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-3 | 10 | -247.988135 | 0.000000 | 50.287759 | -338.768076 | 286.275894 | -12.968412 |
| 4-6 | 2 | -261.516368 | 0.000000 | 189.469075 | -320.929341 | 438.985443 | -1.319618 |
| 7-12 | 3 | -56.811348 | 0.333333 | 255.384570 | -111.575090 | 300.195918 | -0.188235 |
| 13-24 | 4 | -24.946580 | 0.500000 | 255.116511 | -187.357951 | 268.063091 | -0.289662 |
| 25-36 | 6 | 92.428369 | 1.000000 | 195.392261 | -122.561448 | 90.963892 | 0.531238 |
| >36 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

| cap_bucket | trade_count | net_expectancy_bps | win_rate | avg_mfe_bps | avg_mae_bps | avg_mfe_giveback_bps | avg_mfe_capture_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <0 | 15 | -237.367028 | 0.000000 | 109.380634 | -315.799913 | 334.747662 | -9.010467 |
| 0-0.25 | 4 | 10.221135 | 0.750000 | 183.036211 | -111.664515 | 160.815076 | 0.130433 |
| 0.25-0.50 | 2 | 72.844768 | 1.000000 | 243.131139 | -158.743461 | 158.286371 | 0.395820 |
| 0.50-0.75 | 2 | 190.136807 | 1.000000 | 323.198476 | -43.082846 | 121.061669 | 0.625472 |
| 0.75-1.00 | 2 | 137.546744 | 1.000000 | 167.637735 | -130.877914 | 18.090991 | 0.866699 |
| >1.00 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

| gb_bucket | trade_count | net_expectancy_bps | win_rate | avg_mfe_bps | avg_mae_bps | avg_mfe_giveback_bps | avg_mfe_capture_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| 0-50 | 3 | 83.026787 | 0.666667 | 122.877137 | -138.483769 | 27.850349 | 0.437763 |
| 50-100 | 3 | 17.811582 | 0.666667 | 100.312033 | -184.009910 | 70.500451 | 0.266262 |
| 100-200 | 3 | 65.852805 | 0.666667 | 216.608690 | -124.576054 | 138.755885 | -16.177693 |
| >200 | 16 | -201.164860 | 0.187500 | 157.587218 | -281.741000 | 346.752078 | -5.277393 |

| year | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | median_mfe_bps | avg_mae_bps | median_mae_bps | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 91.086037 | 0.619048 | 2.579614 | 252.320152 | 209.071081 | -154.109099 | -89.990264 | 8 | 2 |
| 2021 | 82 | 136.328455 | 0.670732 | 2.915073 | 351.453111 | 299.425298 | -224.048406 | -166.752797 | 31 | 11 |
| 2022 | 83 | 4.204122 | 0.518072 | 1.068219 | 149.459047 | 94.733721 | -118.247235 | -79.267214 | 8 | 11 |
| 2023 | 73 | -0.478353 | 0.520548 | 0.987271 | 88.236265 | 68.515946 | -87.712245 | -60.790912 | 2 | 2 |
| 2024 | 26 | 113.606331 | 0.692308 | 2.679255 | 275.257537 | 251.376019 | -160.683581 | -133.094992 | 11 | 4 |
| 2025 | 16 | -160.751555 | 0.250000 | 0.082751 | 148.943370 | 141.609541 | -256.959582 | -279.981793 | 0 | 8 |
| 2026 | 9 | -16.282152 | 0.555556 | 0.806392 | 161.966127 | 129.630909 | -193.079098 | -163.986784 | 0 | 2 |

| exit_month | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | median_mfe_bps | avg_mae_bps | median_mae_bps | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-02 | 2 | -55.924335 | 0.500000 | 0.630323 | 177.395644 | 177.395644 | -213.352724 | -213.352724 | 0 | 1 |
| 2025-03 | 1 | -308.294383 | 0.000000 | 0.000000 | 36.090516 | 36.090516 | -565.187713 | -565.187713 | 0 | 1 |
| 2025-04 | 2 | -145.489146 | 0.000000 | 0.000000 | 148.757905 | 148.757905 | -224.252676 | -224.252676 | 0 | 1 |
| 2025-05 | 2 | -82.139958 | 0.500000 | 0.028860 | 211.957098 | 211.957098 | -119.400496 | -119.400496 | 0 | 0 |
| 2025-06 | 1 | -242.845193 | 0.000000 | 0.000000 | 193.500762 | 193.500762 | -272.401114 | -272.401114 | 0 | 1 |
| 2025-10 | 2 | -138.698244 | 0.500000 | 0.005584 | 79.044716 | 79.044716 | -293.924321 | -293.924321 | 0 | 1 |
| 2025-11 | 5 | -179.238879 | 0.200000 | 0.037471 | 146.750905 | 57.344483 | -240.489298 | -287.562472 | 0 | 2 |
| 2025-12 | 1 | -280.187542 | 0.000000 | 0.000000 | 185.437389 | 185.437389 | -369.457568 | -369.457568 | 0 | 1 |
| 2026-01 | 2 | 39.565329 | 0.500000 | 179.289424 | 107.400510 | 107.400510 | -182.047677 | -182.047677 | 0 | 0 |
| 2026-02 | 2 | -60.094278 | 0.500000 | 0.437207 | 265.000342 | 265.000342 | -250.020137 | -250.020137 | 0 | 1 |
| 2026-03 | 3 | -91.662447 | 0.666667 | 0.467978 | 153.755597 | 129.630909 | -219.411171 | -132.411370 | 0 | 1 |
| 2026-04 | 1 | 195.518996 | 1.000000 | inf | 218.270704 | 218.270704 | -61.647257 | -61.647257 | 0 | 0 |
| 2026-05 | 1 | -26.013126 | 0.000000 | 0.000000 | 33.355940 | 33.355940 | -153.695479 | -153.695479 | 0 | 0 |

## Interpretation

Recent MFE is happening earlier than the fixed 36-bar exit, and a large share of the favorable move is being given back before realization.
The recent period has 7 trades with >200 bps MFE but 0 realized >=200 bps net, which is consistent with positive-tail decay plus exit-horizon mismatch.
Recent losses still show positive MFE on every loser, so alpha death is not proven by excursion behavior alone.
The data therefore supports: exit-horizon mismatch likely, positive-tail decay likely, adverse continuation likely, alpha death not proven.

## What Is Still Valid

- The canonical replay path is mechanically valid and reproducible.
- The signal still creates intratrade favorable excursion.
- Diagnostic horizons are useful for locating where the edge appears in time.

## What Is Not Valid

- The configured 36-bar exit is not reliably capturing the recent-period favorable move.
- The recent-period positive tail is not stable enough to treat the anchor as production evidence.
- This report does not approve a replacement exit rule.

## Required Next Research

- Compare 2025-2026 market regimes against 2020-2024.
- Inspect whether the fast recent bounce is tied to specific microstructure states or session effects.
- Test whether the fixed exit is systematically too slow only in recent regimes.
- Only after diagnostics, consider PSR/DSR/PBO.
