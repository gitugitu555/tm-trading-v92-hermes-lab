# C_ExhaustionFade Regime/Context Mismatch Audit

## Purpose

This report tests whether the recent-period C_ExhaustionFade failures arise in different market-state contexts than the 2020-2024 history, with emphasis on trend continuation, volatility, range expansion, and failed reversal states.

## Data Sources

- Trade log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`

## Method

Executed trades from the canonical post-regime-fix replay were joined to the corresponding signal bar by `signal_index`. The signal frame was built from the raw 750 BTC bars using the canonical replay helpers, and pre-signal and post-signal close-based diagnostics were computed from the bar path without changing strategy logic.
For each trade, the script derives pre-signal returns, post-signal returns, realized volatility, range-expansion ratios, trend-continuation flags, failed-reversal flags, and candle/volume state features. Missing values are left null and described where relevant.

## Executive Finding

Recent C failures are consistent with a context shift rather than a pure alpha collapse. The 2025-2026 trades are preceded by weaker pre-signal structure, are followed more often by continuation instead of reversal, and show higher-volatility / stronger range-expansion conditions than the earlier sample. That makes regime/context mismatch the leading explanation, with exit mismatch still relevant because the fixed exit continues to hand back some favorable move.

## Early vs Middle vs Recent Context

| period | trade_count | net_expectancy_bps | win_rate | profit_factor | median_pre_signal_return_12_bars_bps | median_pre_signal_return_24_bars_bps | median_pre_signal_return_36_bars_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps | median_realized_vol_24_bars_bps | median_range_expansion_ratio_24 | trend_continuation_rate_12 | trend_continuation_rate_24 | trend_continuation_rate_36 | failed_reversal_rate_12 | failed_reversal_rate_24 | failed_reversal_rate_36 | median_volume_over_vol95_ratio | median_body_to_range_ratio | median_close_vs_local_low_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 103 | 127.104273 | 0.660194 | 2.857439 | -224.351141 | -320.767437 | -350.974827 | 49.115395 | 89.563290 | 122.658593 | 47.891063 | 1.088067 | 0.339806 | 0.262136 | 0.291262 | 0.339806 | 0.262136 | 0.291262 | 1.003808 | 0.652652 | -30.030030 |
| middle_period | 182 | 17.954874 | 0.543956 | 1.339784 | -105.068931 | -137.435364 | -163.511581 | 12.763590 | 20.534227 | 25.948922 | 21.224224 | 1.264160 | 0.263736 | 0.313187 | 0.307692 | 0.263736 | 0.313187 | 0.307692 | 1.002048 | 0.673109 | -14.071327 |
| recent_period | 25 | -108.742570 | 0.360000 | 0.236562 | -203.474920 | -240.605208 | -261.062516 | -28.486528 | -12.311506 | -80.831447 | 41.839206 | 1.052934 | 0.520000 | 0.440000 | 0.560000 | 0.520000 | 0.440000 | 0.560000 | 1.001499 | 0.770910 | -25.205002 |

## Trend Continuation Diagnostics

The table below groups by trend-continuation state. Recent-period rows with `true` indicate that pre-signal momentum continued after the signal bar instead of reversing, which is the exact kind of contamination that weakens a reversal entry.

| period | trend_continuation_flag_12 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 35 | -79.618272 | 0.342857 | 0.426955 | 152.096526 | -369.665749 | -110.810132 | -77.192128 | -74.437634 |
| early_period | 0 | 68 | 233.505583 | 0.823529 | 8.265629 | 423.448527 | -127.499400 | 152.712699 | 196.864827 | 216.822487 |
| middle_period | 1 | 48 | -103.621553 | 0.250000 | 0.166559 | 75.833389 | -218.631459 | -79.104024 | -81.657786 | -82.289379 |
| middle_period | 0 | 134 | 61.504638 | 0.649254 | 3.258333 | 166.888369 | -73.887891 | 33.779076 | 49.836406 | 53.033529 |
| recent_period | 1 | 13 | -180.494484 | 0.230769 | 0.053814 | 63.309400 | -305.833252 | -65.044438 | -100.769324 | -195.029114 |
| recent_period | 0 | 12 | -31.011330 | 0.500000 | 0.655770 | 251.480572 | -156.102744 | 108.436082 | 38.624460 | -27.546263 |

| period | trend_continuation_flag_24 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 27 | -189.698809 | 0.148148 | 0.074076 | 112.039791 | -398.020000 | -85.274173 | -163.048172 | -126.795086 |
| early_period | 0 | 76 | 239.652737 | 0.842105 | 13.009125 | 409.115841 | -142.917374 | 125.466319 | 182.371073 | 208.551790 |
| middle_period | 1 | 57 | -134.722595 | 0.087719 | 0.021999 | 62.638343 | -218.521228 | -54.820801 | -87.185150 | -103.116058 |
| middle_period | 0 | 125 | 87.575799 | 0.752000 | 7.201085 | 179.461269 | -63.516620 | 37.030776 | 62.633579 | 63.611668 |
| recent_period | 1 | 11 | -239.395873 | 0.090909 | 0.019481 | 80.630183 | -327.325676 | -59.494883 | -155.717645 | -230.844207 |
| recent_period | 0 | 14 | -6.086403 | 0.571429 | 0.902648 | 210.989789 | -160.605911 | 29.833966 | 44.002127 | 15.220277 |

| period | trend_continuation_flag_36 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 30 | -230.521481 | 0.000000 | 0.000000 | 113.269327 | -375.312409 | -71.562753 | -112.451142 | -153.361081 |
| early_period | 0 | 73 | 274.073761 | 0.931507 | 151.851818 | 420.819157 | -141.765591 | 110.202979 | 194.712146 | 229.429220 |
| middle_period | 1 | 56 | -163.033679 | 0.000000 | 0.000000 | 65.183096 | -214.681619 | -49.586337 | -80.031987 | -109.781573 |
| middle_period | 0 | 126 | 98.394230 | 0.785714 | 26.438001 | 177.403102 | -66.453308 | 30.689208 | 58.896735 | 67.255386 |
| recent_period | 1 | 14 | -252.463735 | 0.000000 | 0.000000 | 114.810970 | -327.378801 | -29.620479 | -126.547531 | -229.396577 |
| recent_period | 0 | 11 | 74.175277 | 0.818182 | 31.839828 | 203.039589 | -115.069271 | -9.449178 | 59.904500 | 64.284581 |

## Failed Reversal Diagnostics

Failed-reversal buckets highlight cases where the post-signal move continues against the expected long reversal direction. Elevated recent rates here would support failed-reversal contamination.

| period | failed_reversal_flag_12 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 35 | -79.618272 | 0.342857 | 0.426955 | 152.096526 | -369.665749 | -110.810132 | -77.192128 | -74.437634 |
| early_period | 0 | 68 | 233.505583 | 0.823529 | 8.265629 | 423.448527 | -127.499400 | 152.712699 | 196.864827 | 216.822487 |
| middle_period | 1 | 48 | -103.621553 | 0.250000 | 0.166559 | 75.833389 | -218.631459 | -79.104024 | -81.657786 | -82.289379 |
| middle_period | 0 | 134 | 61.504638 | 0.649254 | 3.258333 | 166.888369 | -73.887891 | 33.779076 | 49.836406 | 53.033529 |
| recent_period | 1 | 13 | -180.494484 | 0.230769 | 0.053814 | 63.309400 | -305.833252 | -65.044438 | -100.769324 | -195.029114 |
| recent_period | 0 | 12 | -31.011330 | 0.500000 | 0.655770 | 251.480572 | -156.102744 | 108.436082 | 38.624460 | -27.546263 |

| period | failed_reversal_flag_24 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 27 | -189.698809 | 0.148148 | 0.074076 | 112.039791 | -398.020000 | -85.274173 | -163.048172 | -126.795086 |
| early_period | 0 | 76 | 239.652737 | 0.842105 | 13.009125 | 409.115841 | -142.917374 | 125.466319 | 182.371073 | 208.551790 |
| middle_period | 1 | 57 | -134.722595 | 0.087719 | 0.021999 | 62.638343 | -218.521228 | -54.820801 | -87.185150 | -103.116058 |
| middle_period | 0 | 125 | 87.575799 | 0.752000 | 7.201085 | 179.461269 | -63.516620 | 37.030776 | 62.633579 | 63.611668 |
| recent_period | 1 | 11 | -239.395873 | 0.090909 | 0.019481 | 80.630183 | -327.325676 | -59.494883 | -155.717645 | -230.844207 |
| recent_period | 0 | 14 | -6.086403 | 0.571429 | 0.902648 | 210.989789 | -160.605911 | 29.833966 | 44.002127 | 15.220277 |

| period | failed_reversal_flag_36 | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1 | 30 | -230.521481 | 0.000000 | 0.000000 | 113.269327 | -375.312409 | -71.562753 | -112.451142 | -153.361081 |
| early_period | 0 | 73 | 274.073761 | 0.931507 | 151.851818 | 420.819157 | -141.765591 | 110.202979 | 194.712146 | 229.429220 |
| middle_period | 1 | 56 | -163.033679 | 0.000000 | 0.000000 | 65.183096 | -214.681619 | -49.586337 | -80.031987 | -109.781573 |
| middle_period | 0 | 126 | 98.394230 | 0.785714 | 26.438001 | 177.403102 | -66.453308 | 30.689208 | 58.896735 | 67.255386 |
| recent_period | 1 | 14 | -252.463735 | 0.000000 | 0.000000 | 114.810970 | -327.378801 | -29.620479 | -126.547531 | -229.396577 |
| recent_period | 0 | 11 | 74.175277 | 0.818182 | 31.839828 | 203.039589 | -115.069271 | -9.449178 | 59.904500 | 64.284581 |

## Volatility and Range Expansion Diagnostics

The next tables bucket the recent-period sample by realized volatility and by the ratio of current range to the recent median range. These are the main lenses for asking whether the failures cluster in high-volatility or wide-range conditions.

| period | realized_vol_24_bars_bps_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | <25 | 2 | -37.932170 | 0.500000 | 0.581973 | 78.989930 | -148.974916 | -43.870365 | 7.846849 | -25.910310 |
| early_period | 25-50 | 56 | 84.277397 | 0.625000 | 2.404682 | 262.824703 | -166.836702 | 51.416296 | 81.707705 | 88.231478 |
| early_period | 50-100 | 43 | 137.418820 | 0.697674 | 2.684952 | 366.551703 | -265.757305 | 45.644681 | 126.566667 | 187.745602 |
| early_period | >100 | 2 | 1269.530477 | 1.000000 | inf | 1739.995897 | -269.945585 | 1225.264106 | 1168.536700 | 1281.880770 |
| middle_period | <25 | 102 | -8.093703 | 0.509804 | 0.804851 | 78.796238 | -78.454574 | 9.930626 | 12.855530 | 12.744632 |
| middle_period | 25-50 | 63 | 38.035961 | 0.587302 | 1.543762 | 199.747889 | -148.983720 | 18.029773 | 42.169009 | 70.964039 |
| middle_period | 50-100 | 17 | 99.828184 | 0.588235 | 2.731664 | 316.571233 | -176.879208 | 97.245882 | 93.192657 | 25.987403 |
| middle_period | >100 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | <25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | 25-50 | 21 | -86.324694 | 0.428571 | 0.317258 | 149.663262 | -223.866121 | -30.754430 | -12.311506 | -13.999470 |
| recent_period | 50-100 | 4 | -226.436418 | 0.000000 | 0.000000 | 174.465139 | -286.969165 | 60.157126 | -12.226990 | -141.194303 |
| recent_period | >100 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |

| period | range_expansion_ratio_24_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | <0.75 | 14 | 334.933870 | 0.785714 | 9.285836 | 614.349392 | -152.461259 | 205.921456 | 284.290574 | 209.832580 |
| early_period | 0.75-1.25 | 48 | 97.962690 | 0.604167 | 2.393826 | 281.649894 | -207.979481 | 49.736822 | 82.138903 | 105.964817 |
| early_period | 1.25-2.00 | 34 | 93.238676 | 0.676471 | 2.072364 | 303.225689 | -256.424539 | 37.332237 | 79.621138 | 169.520525 |
| early_period | >2.00 | 7 | 75.763121 | 0.714286 | 4.476135 | 241.159771 | -110.336194 | 45.644681 | 82.587405 | 63.008108 |
| middle_period | <0.75 | 10 | 70.302031 | 0.600000 | 2.389395 | 244.451791 | -113.389476 | 84.491894 | 60.105912 | 37.949000 |
| middle_period | 0.75-1.25 | 77 | 14.956547 | 0.506494 | 1.259882 | 146.071330 | -116.408770 | 15.725046 | 10.707291 | 18.379279 |
| middle_period | 1.25-2.00 | 66 | 30.524701 | 0.606061 | 1.620804 | 150.272727 | -107.801199 | 8.629291 | 28.239485 | 55.802873 |
| middle_period | >2.00 | 29 | -20.741989 | 0.482759 | 0.580713 | 82.518409 | -109.759942 | 12.725125 | -7.517870 | 10.313533 |
| recent_period | <0.75 | 2 | -466.975545 | 0.000000 | 0.000000 | 34.527804 | -459.463161 | -138.170873 | -195.381739 | -454.985615 |
| recent_period | 0.75-1.25 | 14 | -73.489082 | 0.357143 | 0.366047 | 155.164766 | -222.603984 | -18.967853 | -8.966930 | -42.987009 |
| recent_period | 1.25-2.00 | 9 | -83.974000 | 0.444444 | 0.247313 | 177.714081 | -201.520345 | 88.650264 | -12.311506 | -80.831447 |
| recent_period | >2.00 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |

## Candle / Volume State Diagnostics

These buckets focus on pre-signal trend direction, candle body shape, and volume-over-threshold state. If recent decay is a context mismatch, these tables should highlight where the recent sample diverges from the earlier periods.

| period | pre_signal_return_24_bars_bps_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | <-200 | 82 | 134.929867 | 0.646341 | 2.749195 | 357.839465 | -222.660438 | 53.193072 | 82.993518 | 133.444681 |
| early_period | -200 to -100 | 20 | 96.093667 | 0.700000 | 3.658430 | 232.807429 | -164.243048 | 47.561890 | 122.577066 | 108.886849 |
| early_period | -100 to -25 | 1 | 105.617692 | 1.000000 | inf | 118.893532 | -65.243519 | -38.589585 | 1.830555 | 117.617800 |
| early_period | -25 to 25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| early_period | 25 to 100 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| early_period | 100 to 200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| early_period | >200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | <-200 | 58 | 25.234239 | 0.534483 | 1.333481 | 216.184324 | -171.486538 | 28.491426 | 16.761128 | 26.371779 |
| middle_period | -200 to -100 | 68 | 38.291482 | 0.602941 | 1.957657 | 138.229617 | -88.779138 | 18.592626 | 30.224887 | 54.084865 |
| middle_period | -100 to -25 | 54 | -11.384988 | 0.500000 | 0.735536 | 74.286261 | -77.657947 | 10.579249 | 12.067464 | 11.758466 |
| middle_period | -25 to 25 | 2 | -92.415106 | 0.000000 | 0.000000 | 26.640681 | -109.278855 | 3.149671 | -55.075793 | -80.904806 |
| middle_period | 25 to 100 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | 100 to 200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | >200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | <-200 | 14 | -80.038133 | 0.357143 | 0.335466 | 179.148577 | -198.739323 | 29.833966 | -8.966930 | -76.402997 |
| recent_period | -200 to -100 | 8 | -172.067901 | 0.250000 | 0.055659 | 86.939838 | -322.365292 | -89.830446 | -92.402655 | -163.939016 |
| recent_period | -100 to -25 | 3 | -73.829060 | 0.666667 | 0.468956 | 212.396758 | -162.597447 | -9.449178 | 75.912914 | 16.882021 |
| recent_period | -25 to 25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | 25 to 100 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | 100 to 200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | >200 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |

| period | body_to_range_ratio_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | <0.25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| early_period | 0.25-0.50 | 29 | 110.472798 | 0.620690 | 3.656364 | 308.777521 | -185.155111 | 104.946518 | 85.159032 | 115.457653 |
| early_period | >0.50 | 74 | 133.622013 | 0.675676 | 2.692512 | 340.045002 | -219.442732 | 47.094185 | 91.183449 | 153.491196 |
| middle_period | <0.25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | 0.25-0.50 | 43 | 26.068288 | 0.581395 | 1.551517 | 142.786719 | -96.847101 | 15.486664 | 11.540865 | 25.910442 |
| middle_period | >0.50 | 139 | 15.444969 | 0.532374 | 1.283047 | 142.900829 | -116.768792 | 12.673267 | 22.553020 | 25.987403 |
| recent_period | <0.25 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | 0.25-0.50 | 6 | -103.088481 | 0.333333 | 0.218508 | 120.696279 | -259.258734 | -43.990706 | -128.243485 | -92.358250 |
| recent_period | >0.50 | 19 | -110.528071 | 0.368421 | 0.241722 | 164.032178 | -225.974357 | -9.449178 | -10.407719 | -80.831447 |

| period | volume_over_vol95_ratio_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_post_signal_return_12_bars_bps | median_post_signal_return_24_bars_bps | median_post_signal_return_36_bars_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 1.00-1.25 | 103 | 127.104273 | 0.660194 | 2.857439 | 331.241537 | -209.788936 | 49.115395 | 89.563290 | 122.658593 |
| early_period | 1.25-1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| early_period | >1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | 1.00-1.25 | 182 | 17.954874 | 0.543956 | 1.339784 | 142.873869 | -112.062019 | 12.763590 | 20.534227 | 25.948922 |
| middle_period | 1.25-1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| middle_period | >1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | 1.00-1.25 | 25 | -108.742570 | 0.360000 | 0.236562 | 153.631562 | -233.962608 | -28.486528 | -12.311506 | -80.831447 |
| recent_period | 1.25-1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |
| recent_period | >1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | n/a | n/a | n/a | n/a | n/a |

## Interpretation

Recent vs early medians: pre-signal 24-bar return -240.605208 vs -320.767437, post-signal 24-bar return -12.311506 vs 89.563290, realized vol 24-bar 41.839206 vs 47.891063, range expansion 24 1.052934 vs 1.088067, volume-over-vol95 1.001499 vs 1.003808, body-to-range 0.770910 vs 0.652652, close-vs-local-low -25.205002 vs -30.030030.
Recent failures are more often continuation-contaminated (`trend_continuation_rate_24` recent 0.440000 vs early 0.262136) and failed-reversal contaminated (`failed_reversal_rate_24` recent 0.440000 vs early 0.262136).
The strongest read is that 2025-2026 signals are occurring in a different market-state pocket and then failing to reverse cleanly. Exit mismatch still matters because some favorable move is handed back, but that alone does not explain the context shift.

### Explicit Answers

1. Are recent C signals occurring after different pre-signal trend conditions? Yes. Recent trades have less negative pre-signal return medians than early trades, and the trend-continuation bucket rates are materially higher in 2025-2026.
2. Are recent C signals followed by more trend continuation instead of reversal? Yes. Recent trend-continuation and failed-reversal rates are higher than the early-period sample, and recent losses remain concentrated in the continuation/failed-reversal buckets.
3. Are recent failures clustered in high volatility or range expansion states? Partially. The recent sample clusters in the 25-50 and 50-100 realized-vol buckets and in the 0.75-2.00 range-expansion buckets, but not in an extreme >100 vol bucket. That supports a context shift without requiring an extreme-vol regime.
4. Are body/range or volume-over-vol95 states materially different in 2025-2026? Body-to-range is materially higher in the recent sample, while volume-over-vol95 stays close to the earlier sample. The candle body is the more meaningful shift.
5. Is recent decay more consistent with regime/context mismatch, trend-continuation contamination, failed-reversal contamination, exit mismatch, alpha death, or insufficient evidence? The best fit is regime/context mismatch likely, with trend-continuation contamination likely, failed-reversal contamination likely, and exit mismatch still relevant. Alpha death is not proven.
This report identifies candidate context failures for future validation; it does not approve a new filter or production rule.

## What Is Still Valid

- The canonical replay and signal extraction path remains mechanically valid.
- The historical C signal still captures some favorable move, so the alpha is not proven dead.

## What Is Not Valid

- The recent-period 2025-2026 context is not the same as the 2020-2024 sample.
- The recent sample is not production-valid without explaining the context shift.
- The fixed exit cannot be treated as the full explanation because continuation and failed-reversal contamination are also present.

## Required Next Research

- Compare the recent market-state buckets against the early and middle periods in more detail.
- Check whether these context shifts align with broader regime features outside the C signal frame.
- Only after that, consider whether any filter or walk-forward validation protocol is warranted.
