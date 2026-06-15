# C_ExhaustionFade Regime-Gate Hypothesis Matrix

## Purpose

This report tests whether a small, pre-registered set of regime/context gates can reduce recent trend-continuation and failed-reversal contamination while preserving early and middle-period robustness.

## Data Sources

- Trade log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`

## Method

The matrix filters the already-executed canonical C trade set by pre-registered diagnostic gates and recomputes metrics on the kept subset only. No new entries, exits, or classifier logic were introduced.
Gates are applied conservatively: a trade is kept only when the selected condition is true; null context values are treated as false and therefore excluded from the gated subset.

## Candidate Gate Families

The candidate set includes trend-continuation exclusions, failed-reversal exclusions, candle body/range thresholds, range-expansion thresholds, and a small set of pre-registered combined gates. No additional combinations were added.

## All-Period Results

| candidate | family | period | input_trade_count | kept_trade_count | removed_trade_count | kept_rate | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | p10_trade_bps | p25_trade_bps | p75_trade_bps | p90_trade_bps | max_win_bps | max_loss_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps | early_positive | middle_positive | recent_positive | positive_all_periods | min_period_trade_count | sample_too_small | early_net_expectancy_bps | middle_net_expectancy_bps | recent_net_expectancy_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | all_period | 150 | 150 | 0 | 1.000000 | 175.608542 | 0.853333 | 65.250967 | 208.994189 | -18.635221 | 109.855216 | -12.636439 | 29.163133 | 238.985287 | 416.150844 | 1835.851662 | -35.758136 | 50 | 0.333333 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 11 | 0 | 278.940732 | 121.233488 | 74.175277 |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | all_period | 150 | 150 | 0 | 1.000000 | 175.608542 | 0.853333 | 65.250967 | 208.994189 | -18.635221 | 109.855216 | -12.636439 | 29.163133 | 238.985287 | 416.150844 | 1835.851662 | -35.758136 | 50 | 0.333333 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 11 | 0 | 278.940732 | 121.233488 | 74.175277 |
| exclude_trend_cont_36 | trend_continuation_exclusion | all_period | 210 | 210 | 0 | 1.000000 | 158.195170 | 0.838095 | 52.389515 | 192.428637 | -19.013369 | 81.492981 | -14.926184 | 29.163133 | 219.477277 | 395.141101 | 1835.851662 | -35.758136 | 60 | 0.285714 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 11 | 0 | 274.073761 | 98.394230 | 74.175277 |
| exclude_failed_reversal_36 | failed_reversal_exclusion | all_period | 210 | 210 | 0 | 1.000000 | 158.195170 | 0.838095 | 52.389515 | 192.428637 | -19.013369 | 81.492981 | -14.926184 | 29.163133 | 219.477277 | 395.141101 | 1835.851662 | -35.758136 | 60 | 0.285714 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 11 | 0 | 274.073761 | 98.394230 | 74.175277 |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | all_period | 163 | 163 | 0 | 1.000000 | 184.661769 | 0.889571 | 107.321699 | 209.537726 | -15.727880 | 110.658593 | -1.020206 | 39.885649 | 248.921100 | 458.074368 | 1835.851662 | -32.484421 | 55 | 0.337423 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 6 | 1 | 318.261437 | 114.537584 | 118.155324 |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | all_period | 163 | 163 | 0 | 1.000000 | 184.661769 | 0.889571 | 107.321699 | 209.537726 | -15.727880 | 110.658593 | -1.020206 | 39.885649 | 248.921100 | 458.074368 | 1835.851662 | -32.484421 | 55 | 0.337423 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 6 | 1 | 318.261437 | 114.537584 | 118.155324 |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | all_period | 188 | 188 | 0 | 1.000000 | 174.885131 | 0.882979 | 93.818612 | 200.196546 | -16.101005 | 105.180472 | -1.262006 | 39.326812 | 240.697000 | 421.436488 | 1835.851662 | -35.448551 | 59 | 0.313830 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 9 | 1 | 293.148225 | 111.141547 | 87.735583 |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | all_period | 188 | 188 | 0 | 1.000000 | 174.885131 | 0.882979 | 93.818612 | 200.196546 | -16.101005 | 105.180472 | -1.262006 | 39.326812 | 240.697000 | 421.436488 | 1835.851662 | -35.448551 | 59 | 0.313830 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 9 | 1 | 293.148225 | 111.141547 | 87.735583 |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | all_period | 97 | 97 | 0 | 1.000000 | 165.748058 | 0.855670 | 58.203857 | 197.091794 | -20.075522 | 110.658593 | -14.393519 | 33.551263 | 240.414023 | 380.358524 | 810.853866 | -35.758136 | 36 | 0.371134 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 267.900416 | 102.685998 | 48.976656 |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | all_period | 97 | 97 | 0 | 1.000000 | 165.748058 | 0.855670 | 58.203857 | 197.091794 | -20.075522 | 110.658593 | -14.393519 | 33.551263 | 240.414023 | 380.358524 | 810.853866 | -35.758136 | 36 | 0.371134 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 267.900416 | 102.685998 | 48.976656 |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | all_period | 135 | 135 | 0 | 1.000000 | 150.964144 | 0.844444 | 47.661804 | 182.604584 | -20.798248 | 89.535992 | -18.304898 | 35.682042 | 224.916368 | 345.183108 | 810.853866 | -35.758136 | 42 | 0.311111 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 266.802572 | 88.413167 | 48.976656 |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | all_period | 135 | 135 | 0 | 1.000000 | 150.964144 | 0.844444 | 47.661804 | 182.604584 | -20.798248 | 89.535992 | -18.304898 | 35.682042 | 224.916368 | 345.183108 | 810.853866 | -35.758136 | 42 | 0.311111 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 266.802572 | 88.413167 | 48.976656 |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | all_period | 117 | 117 | 0 | 1.000000 | 149.154058 | 0.829060 | 41.303516 | 184.371288 | -21.649507 | 79.574491 | -19.351736 | 30.671586 | 223.658300 | 354.100102 | 810.853866 | -35.758136 | 35 | 0.299145 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 270.398839 | 85.174554 | 48.976656 |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | all_period | 117 | 117 | 0 | 1.000000 | 149.154058 | 0.829060 | 41.303516 | 184.371288 | -21.649507 | 79.574491 | -19.351736 | 30.671586 | 223.658300 | 354.100102 | 810.853866 | -35.758136 | 35 | 0.299145 | 0 | 0.000000 | 1 | 1 | 1 | 1 | 3 | 1 | 270.398839 | 85.174554 | 48.976656 |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | all_period | 183 | 183 | 0 | 1.000000 | 152.320608 | 0.792350 | 12.112978 | 209.537726 | -66.007868 | 82.341994 | -44.461539 | 16.322452 | 230.365123 | 418.507131 | 1835.851662 | -260.592940 | 55 | 0.300546 | 3 | 0.016393 | 1 | 1 | 1 | 1 | 9 | 1 | 285.204601 | 89.886123 | 35.562079 |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | all_period | 183 | 183 | 0 | 1.000000 | 152.320608 | 0.792350 | 12.112978 | 209.537726 | -66.007868 | 82.341994 | -44.461539 | 16.322452 | 230.365123 | 418.507131 | 1835.851662 | -260.592940 | 55 | 0.300546 | 3 | 0.016393 | 1 | 1 | 1 | 1 | 9 | 1 | 285.204601 | 89.886123 | 35.562079 |
| exclude_trend_cont_24 | trend_continuation_exclusion | all_period | 215 | 215 | 0 | 1.000000 | 135.234294 | 0.772093 | 7.993890 | 200.196546 | -84.841906 | 77.716794 | -71.498257 | 7.278455 | 211.406709 | 392.792097 | 1835.851662 | -416.268957 | 59 | 0.274419 | 7 | 0.032558 | 1 | 1 | 0 | 0 | 14 | 0 | 239.652737 | 87.575799 | -6.086403 |
| exclude_failed_reversal_24 | failed_reversal_exclusion | all_period | 215 | 215 | 0 | 1.000000 | 135.234294 | 0.772093 | 7.993890 | 200.196546 | -84.841906 | 77.716794 | -71.498257 | 7.278455 | 211.406709 | 392.792097 | 1835.851662 | -416.268957 | 59 | 0.274419 | 7 | 0.032558 | 1 | 1 | 0 | 0 | 14 | 0 | 239.652737 | 87.575799 | -6.086403 |
| exclude_trend_cont_12 | trend_continuation_exclusion | all_period | 214 | 214 | 0 | 1.000000 | 110.971333 | 0.696262 | 4.433805 | 205.797114 | -106.398535 | 59.940892 | -114.227035 | -17.862113 | 201.390621 | 385.777188 | 1835.851662 | -516.990644 | 56 | 0.261682 | 11 | 0.051402 | 1 | 1 | 0 | 0 | 12 | 0 | 233.505583 | 61.504638 | -31.011330 |
| exclude_failed_reversal_12 | failed_reversal_exclusion | all_period | 214 | 214 | 0 | 1.000000 | 110.971333 | 0.696262 | 4.433805 | 205.797114 | -106.398535 | 59.940892 | -114.227035 | -17.862113 | 201.390621 | 385.777188 | 1835.851662 | -516.990644 | 56 | 0.261682 | 11 | 0.051402 | 1 | 1 | 0 | 0 | 12 | 0 | 233.505583 | 61.504638 | -31.011330 |
| range_expansion_24_lt_1_50 | range_expansion_gate | all_period | 222 | 222 | 0 | 1.000000 | 56.662871 | 0.576577 | 1.887600 | 208.994189 | -150.767009 | 32.111424 | -252.656695 | -89.867311 | 187.299208 | 336.139657 | 1835.851662 | -516.990644 | 50 | 0.225225 | 29 | 0.130631 | 1 | 1 | 0 | 0 | 23 | 0 | 138.427275 | 33.676312 | -99.695820 |
| range_expansion_24_lt_2_00 | range_expansion_gate | all_period | 274 | 274 | 0 | 1.000000 | 50.044302 | 0.572993 | 1.735658 | 206.060057 | -159.310172 | 34.219984 | -250.756933 | -93.440078 | 172.507852 | 337.417138 | 1835.851662 | -1103.637030 | 59 | 0.215328 | 38 | 0.138686 | 1 | 1 | 0 | 0 | 25 | 0 | 130.847899 | 25.289573 | -108.742570 |
| range_expansion_24_lt_1_25 | range_expansion_gate | all_period | 165 | 165 | 0 | 1.000000 | 56.261573 | 0.545455 | 1.811904 | 230.188563 | -152.450816 | 24.240013 | -259.474636 | -97.671619 | 190.709441 | 350.809136 | 1835.851662 | -516.990644 | 39 | 0.236364 | 24 | 0.145455 | 1 | 1 | 0 | 0 | 16 | 0 | 151.472311 | 21.318097 | -122.674890 |
| body_to_range_lt_0_70 | body_range_gate | all_period | 170 | 170 | 0 | 1.000000 | 39.206513 | 0.570588 | 1.594096 | 184.371288 | -153.683669 | 38.593648 | -245.441307 | -72.255646 | 134.216810 | 322.672276 | 810.853866 | -1103.637030 | 35 | 0.205882 | 21 | 0.123529 | 1 | 1 | 0 | 0 | 10 | 0 | 107.967003 | 19.282654 | -174.117842 |
| body_to_range_lt_0_65 | body_range_gate | all_period | 141 | 141 | 0 | 1.000000 | 28.632247 | 0.546099 | 1.416387 | 178.348257 | -151.494828 | 24.930186 | -257.443143 | -78.919957 | 113.566979 | 307.110948 | 810.853866 | -1103.637030 | 28 | 0.198582 | 18 | 0.127660 | 1 | 1 | 0 | 0 | 10 | 0 | 109.924996 | 4.780492 | -174.117842 |
| body_to_range_lt_0_75 | body_range_gate | all_period | 194 | 194 | 0 | 1.000000 | 43.919785 | 0.587629 | 1.692917 | 182.604584 | -153.706055 | 43.425525 | -239.487512 | -72.255646 | 153.152938 | 317.683010 | 810.853866 | -1103.637030 | 42 | 0.216495 | 24 | 0.123711 | 1 | 1 | 0 | 0 | 11 | 0 | 118.901702 | 20.724378 | -177.107359 |
| body_to_range_lt_0_60 | body_range_gate | all_period | 116 | 116 | 0 | 1.000000 | 38.679084 | 0.568966 | 1.589555 | 183.291167 | -152.208865 | 28.129822 | -239.218847 | -74.040518 | 130.818137 | 324.505804 | 810.853866 | -1103.637030 | 26 | 0.224138 | 13 | 0.112069 | 1 | 1 | 0 | 0 | 9 | 1 | 111.668619 | 21.313540 | -166.481469 |

## Early vs Middle vs Recent Stability

Stability is judged by whether the gated subset remains positive in early, middle, and recent periods, and whether each period retains at least 10 trades.

| candidate | family | period | input_trade_count | kept_trade_count | removed_trade_count | kept_rate | net_expectancy_bps | win_rate | profit_factor | early_positive | middle_positive | recent_positive | positive_all_periods | min_period_trade_count | sample_too_small |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exclude_trend_cont_12 | trend_continuation_exclusion | early_period | 68 | 68 | 0 | 1.000000 | 233.505583 | 0.823529 | 8.265629 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_12 | trend_continuation_exclusion | middle_period | 134 | 134 | 0 | 1.000000 | 61.504638 | 0.649254 | 3.258333 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_12 | trend_continuation_exclusion | recent_period | 12 | 12 | 0 | 1.000000 | -31.011330 | 0.500000 | 0.655770 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24 | trend_continuation_exclusion | early_period | 76 | 76 | 0 | 1.000000 | 239.652737 | 0.842105 | 13.009125 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24 | trend_continuation_exclusion | middle_period | 125 | 125 | 0 | 1.000000 | 87.575799 | 0.752000 | 7.201085 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24 | trend_continuation_exclusion | recent_period | 14 | 14 | 0 | 1.000000 | -6.086403 | 0.571429 | 0.902648 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36 | trend_continuation_exclusion | early_period | 73 | 73 | 0 | 1.000000 | 274.073761 | 0.931507 | 151.851818 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36 | trend_continuation_exclusion | middle_period | 126 | 126 | 0 | 1.000000 | 98.394230 | 0.785714 | 26.438001 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36 | trend_continuation_exclusion | recent_period | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | early_period | 61 | 61 | 0 | 1.000000 | 285.204601 | 0.901639 | 39.756730 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | middle_period | 113 | 113 | 0 | 1.000000 | 89.886123 | 0.743363 | 7.080162 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | recent_period | 9 | 9 | 0 | 1.000000 | 35.562079 | 0.666667 | 1.823041 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | early_period | 67 | 67 | 0 | 1.000000 | 293.148225 | 0.955224 | 220.883386 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | middle_period | 112 | 112 | 0 | 1.000000 | 111.141547 | 0.839286 | 48.070018 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | recent_period | 9 | 9 | 0 | 1.000000 | 87.735583 | 0.888889 | 1780.094745 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | early_period | 56 | 56 | 0 | 1.000000 | 318.261437 | 0.982143 | 752.076258 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | middle_period | 101 | 101 | 0 | 1.000000 | 114.537584 | 0.831683 | 45.601111 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | recent_period | 6 | 6 | 0 | 1.000000 | 118.155324 | 1.000000 | inf | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12 | failed_reversal_exclusion | early_period | 68 | 68 | 0 | 1.000000 | 233.505583 | 0.823529 | 8.265629 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12 | failed_reversal_exclusion | middle_period | 134 | 134 | 0 | 1.000000 | 61.504638 | 0.649254 | 3.258333 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12 | failed_reversal_exclusion | recent_period | 12 | 12 | 0 | 1.000000 | -31.011330 | 0.500000 | 0.655770 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24 | failed_reversal_exclusion | early_period | 76 | 76 | 0 | 1.000000 | 239.652737 | 0.842105 | 13.009125 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24 | failed_reversal_exclusion | middle_period | 125 | 125 | 0 | 1.000000 | 87.575799 | 0.752000 | 7.201085 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24 | failed_reversal_exclusion | recent_period | 14 | 14 | 0 | 1.000000 | -6.086403 | 0.571429 | 0.902648 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36 | failed_reversal_exclusion | early_period | 73 | 73 | 0 | 1.000000 | 274.073761 | 0.931507 | 151.851818 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36 | failed_reversal_exclusion | middle_period | 126 | 126 | 0 | 1.000000 | 98.394230 | 0.785714 | 26.438001 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36 | failed_reversal_exclusion | recent_period | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | early_period | 61 | 61 | 0 | 1.000000 | 285.204601 | 0.901639 | 39.756730 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | middle_period | 113 | 113 | 0 | 1.000000 | 89.886123 | 0.743363 | 7.080162 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | recent_period | 9 | 9 | 0 | 1.000000 | 35.562079 | 0.666667 | 1.823041 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | early_period | 67 | 67 | 0 | 1.000000 | 293.148225 | 0.955224 | 220.883386 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | middle_period | 112 | 112 | 0 | 1.000000 | 111.141547 | 0.839286 | 48.070018 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | recent_period | 9 | 9 | 0 | 1.000000 | 87.735583 | 0.888889 | 1780.094745 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | early_period | 56 | 56 | 0 | 1.000000 | 318.261437 | 0.982143 | 752.076258 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | middle_period | 101 | 101 | 0 | 1.000000 | 114.537584 | 0.831683 | 45.601111 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | recent_period | 6 | 6 | 0 | 1.000000 | 118.155324 | 1.000000 | inf | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_75 | body_range_gate | early_period | 68 | 68 | 0 | 1.000000 | 118.901702 | 0.676471 | 2.696987 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_75 | body_range_gate | middle_period | 115 | 115 | 0 | 1.000000 | 20.724378 | 0.573913 | 1.440468 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_75 | body_range_gate | recent_period | 11 | 11 | 0 | 1.000000 | -177.107359 | 0.181818 | 0.081534 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_70 | body_range_gate | early_period | 60 | 60 | 0 | 1.000000 | 107.967003 | 0.650000 | 2.392632 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_70 | body_range_gate | middle_period | 100 | 100 | 0 | 1.000000 | 19.282654 | 0.560000 | 1.414400 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_70 | body_range_gate | recent_period | 10 | 10 | 0 | 1.000000 | -174.117842 | 0.200000 | 0.090351 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_65 | body_range_gate | early_period | 49 | 49 | 0 | 1.000000 | 109.924996 | 0.653061 | 2.586213 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_65 | body_range_gate | middle_period | 82 | 82 | 0 | 1.000000 | 4.780492 | 0.524390 | 1.089379 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_65 | body_range_gate | recent_period | 10 | 10 | 0 | 1.000000 | -174.117842 | 0.200000 | 0.090351 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_60 | body_range_gate | early_period | 41 | 41 | 0 | 1.000000 | 111.668619 | 0.634146 | 2.521383 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_60 | body_range_gate | middle_period | 66 | 66 | 0 | 1.000000 | 21.313540 | 0.575758 | 1.480134 | n/a | n/a | n/a | n/a | n/a | n/a |
| body_to_range_lt_0_60 | body_range_gate | recent_period | 9 | 9 | 0 | 1.000000 | -166.481469 | 0.222222 | 0.103480 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_25 | range_expansion_gate | early_period | 62 | 62 | 0 | 1.000000 | 151.472311 | 0.645161 | 3.383869 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_25 | range_expansion_gate | middle_period | 87 | 87 | 0 | 1.000000 | 21.318097 | 0.517241 | 1.375635 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_25 | range_expansion_gate | recent_period | 16 | 16 | 0 | 1.000000 | -122.674890 | 0.312500 | 0.232340 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_50 | range_expansion_gate | early_period | 78 | 78 | 0 | 1.000000 | 138.427275 | 0.641026 | 3.308580 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_50 | range_expansion_gate | middle_period | 121 | 121 | 0 | 1.000000 | 33.676312 | 0.570248 | 1.640731 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_1_50 | range_expansion_gate | recent_period | 23 | 23 | 0 | 1.000000 | -99.695820 | 0.391304 | 0.268670 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_2_00 | range_expansion_gate | early_period | 96 | 96 | 0 | 1.000000 | 130.847899 | 0.656250 | 2.821626 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_2_00 | range_expansion_gate | middle_period | 153 | 153 | 0 | 1.000000 | 25.289573 | 0.555556 | 1.472868 | n/a | n/a | n/a | n/a | n/a | n/a |
| range_expansion_24_lt_2_00 | range_expansion_gate | recent_period | 25 | 25 | 0 | 1.000000 | -108.742570 | 0.360000 | 0.236562 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | early_period | 48 | 48 | 0 | 1.000000 | 266.802572 | 0.958333 | 296.727954 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | middle_period | 84 | 84 | 0 | 1.000000 | 88.413167 | 0.785714 | 21.211749 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | early_period | 41 | 41 | 0 | 1.000000 | 270.398839 | 0.951220 | 257.005802 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | middle_period | 73 | 73 | 0 | 1.000000 | 85.174554 | 0.767123 | 18.097120 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | early_period | 48 | 48 | 0 | 1.000000 | 266.802572 | 0.958333 | 296.727954 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | middle_period | 84 | 84 | 0 | 1.000000 | 88.413167 | 0.785714 | 21.211749 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | early_period | 41 | 41 | 0 | 1.000000 | 270.398839 | 0.951220 | 257.005802 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | middle_period | 73 | 73 | 0 | 1.000000 | 85.174554 | 0.767123 | 18.097120 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | early_period | 55 | 55 | 0 | 1.000000 | 278.940732 | 0.909091 | 116.673761 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | middle_period | 84 | 84 | 0 | 1.000000 | 121.233488 | 0.821429 | 41.590192 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | recent_period | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | early_period | 55 | 55 | 0 | 1.000000 | 278.940732 | 0.909091 | 116.673761 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | middle_period | 84 | 84 | 0 | 1.000000 | 121.233488 | 0.821429 | 41.590192 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | recent_period | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | early_period | 38 | 38 | 0 | 1.000000 | 267.900416 | 0.947368 | 236.081316 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | middle_period | 56 | 56 | 0 | 1.000000 | 102.685998 | 0.803571 | 28.158026 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | early_period | 38 | 38 | 0 | 1.000000 | 267.900416 | 0.947368 | 236.081316 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | middle_period | 56 | 56 | 0 | 1.000000 | 102.685998 | 0.803571 | 28.158026 | n/a | n/a | n/a | n/a | n/a | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | recent_period | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | n/a | n/a | n/a | n/a | n/a | n/a |

## Recent-Period Results

| candidate | family | input_trade_count | kept_trade_count | removed_trade_count | kept_rate | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | p10_trade_bps | p25_trade_bps | p75_trade_bps | p90_trade_bps | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps | sample_too_small |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exclude_trend_cont_12 | trend_continuation_exclusion | 12 | 12 | 0 | 1.000000 | -31.011330 | 0.500000 | 0.655770 | 118.155324 | -180.177983 | -39.546869 | -239.916390 | -180.260743 | 117.417496 | 190.594915 | 0 | 3 | n/a |
| exclude_trend_cont_24 | trend_continuation_exclusion | 14 | 14 | 0 | 1.000000 | -6.086403 | 0.571429 | 0.902648 | 98.758010 | -145.878954 | 3.219833 | -211.590771 | -89.499171 | 89.920076 | 190.365861 | 0 | 3 | n/a |
| exclude_trend_cont_36 | trend_continuation_exclusion | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | 93.598335 | -13.228479 | 52.320933 | -0.443833 | 3.219833 | 141.466388 | 190.709441 | 0 | 0 | n/a |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | 9 | 9 | 0 | 1.000000 | 35.562079 | 0.666667 | 1.823041 | 118.155324 | -129.624409 | 34.888705 | -115.783678 | -83.975760 | 189.564173 | 191.671352 | 0 | 1 | n/a |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | 9 | 9 | 0 | 1.000000 | 87.735583 | 0.888889 | 1780.094745 | 98.758010 | -0.443833 | 79.574491 | 1.157349 | 4.882022 | 189.564173 | 191.671352 | 0 | 0 | n/a |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | 6 | 6 | 0 | 1.000000 | 118.155324 | 1.000000 | inf | 118.155324 | 0.000000 | 141.466388 | 19.885364 | 49.508680 | 190.423124 | 193.114219 | 0 | 0 | n/a |
| exclude_failed_reversal_12 | failed_reversal_exclusion | 12 | 12 | 0 | 1.000000 | -31.011330 | 0.500000 | 0.655770 | 118.155324 | -180.177983 | -39.546869 | -239.916390 | -180.260743 | 117.417496 | 190.594915 | 0 | 3 | n/a |
| exclude_failed_reversal_24 | failed_reversal_exclusion | 14 | 14 | 0 | 1.000000 | -6.086403 | 0.571429 | 0.902648 | 98.758010 | -145.878954 | 3.219833 | -211.590771 | -89.499171 | 89.920076 | 190.365861 | 0 | 3 | n/a |
| exclude_failed_reversal_36 | failed_reversal_exclusion | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | 93.598335 | -13.228479 | 52.320933 | -0.443833 | 3.219833 | 141.466388 | 190.709441 | 0 | 0 | n/a |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | 9 | 9 | 0 | 1.000000 | 35.562079 | 0.666667 | 1.823041 | 118.155324 | -129.624409 | 34.888705 | -115.783678 | -83.975760 | 189.564173 | 191.671352 | 0 | 1 | n/a |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | 9 | 9 | 0 | 1.000000 | 87.735583 | 0.888889 | 1780.094745 | 98.758010 | -0.443833 | 79.574491 | 1.157349 | 4.882022 | 189.564173 | 191.671352 | 0 | 0 | n/a |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | 6 | 6 | 0 | 1.000000 | 118.155324 | 1.000000 | inf | 118.155324 | 0.000000 | 141.466388 | 19.885364 | 49.508680 | 190.423124 | 193.114219 | 0 | 0 | n/a |
| body_to_range_lt_0_75 | body_range_gate | 11 | 11 | 0 | 1.000000 | -177.107359 | 0.181818 | 0.081534 | 86.471547 | -235.680449 | -207.002532 | -302.558112 | -279.570837 | -54.994443 | 79.574491 | 0 | 6 | n/a |
| body_to_range_lt_0_70 | body_range_gate | 10 | 10 | 0 | 1.000000 | -174.117842 | 0.200000 | 0.090351 | 86.471547 | -239.265189 | -212.780197 | -323.989546 | -279.879189 | -40.503784 | 80.953902 | 0 | 5 | n/a |
| body_to_range_lt_0_65 | body_range_gate | 10 | 10 | 0 | 1.000000 | -174.117842 | 0.200000 | 0.090351 | 86.471547 | -239.265189 | -212.780197 | -323.989546 | -279.879189 | -40.503784 | 80.953902 | 0 | 5 | n/a |
| body_to_range_lt_0_60 | body_range_gate | 9 | 9 | 0 | 1.000000 | -166.481469 | 0.222222 | 0.103480 | 86.471547 | -238.753760 | -182.715200 | -345.420979 | -280.187542 | -26.013126 | 82.333314 | 0 | 4 | n/a |
| range_expansion_24_lt_1_25 | range_expansion_gate | 16 | 16 | 0 | 1.000000 | -122.674890 | 0.312500 | 0.232340 | 118.812048 | -232.441680 | -126.568849 | -362.686513 | -284.855127 | 46.060152 | 142.039023 | 0 | 7 | n/a |
| range_expansion_24_lt_1_50 | range_expansion_gate | 23 | 23 | 0 | 1.000000 | -99.695820 | 0.391304 | 0.268670 | 93.598335 | -223.956347 | -83.975760 | -307.147129 | -259.451540 | 43.604819 | 170.325059 | 0 | 9 | n/a |
| range_expansion_24_lt_2_00 | range_expansion_gate | 25 | 25 | 0 | 1.000000 | -108.742570 | 0.360000 | 0.236562 | 93.598335 | -222.559328 | -91.340308 | -305.999875 | -242.845193 | 34.888705 | 151.085945 | 0 | 10 | n/a |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | 93.598335 | -13.228479 | 52.320933 | -0.443833 | 3.219833 | 141.466388 | 190.709441 | 0 | 0 | n/a |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | 11 | 11 | 0 | 1.000000 | 74.175277 | 0.818182 | 31.839828 | 93.598335 | -13.228479 | 52.320933 | -0.443833 | 3.219833 | 141.466388 | 190.709441 | 0 | 0 | n/a |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | 3 | 3 | 0 | 1.000000 | 48.976656 | 0.666667 | 6.648301 | 86.471547 | -26.013126 | 79.574491 | -4.895603 | 26.780683 | 86.471547 | 90.609781 | 0 | 0 | n/a |

## Candidate Ranking

Candidates are ranked for future validation using the pre-registered order: positive across all periods, recent positive, middle positive, minimum period trade count, then recent expectancy, then all-period expectancy. This is not a production selection.

| candidate | family | net_expectancy_bps | win_rate | profit_factor | kept_trade_count | removed_trade_count | kept_rate | early_positive | middle_positive | recent_positive | positive_all_periods | min_period_trade_count | sample_too_small |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exclude_trend_cont_36_and_range_lt_1_50 | trend_continuation_exclusion | 175.608542 | 0.853333 | 65.250967 | 150 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 11 | 0 |
| exclude_failed_reversal_36_and_range_lt_1_50 | failed_reversal_exclusion | 175.608542 | 0.853333 | 65.250967 | 150 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 11 | 0 |
| exclude_trend_cont_36 | trend_continuation_exclusion | 158.195170 | 0.838095 | 52.389515 | 210 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 11 | 0 |
| exclude_failed_reversal_36 | failed_reversal_exclusion | 158.195170 | 0.838095 | 52.389515 | 210 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 11 | 0 |
| exclude_trend_cont_any_12_24_36 | trend_continuation_exclusion | 184.661769 | 0.889571 | 107.321699 | 163 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 6 | 1 |
| exclude_failed_reversal_any_12_24_36 | failed_reversal_exclusion | 184.661769 | 0.889571 | 107.321699 | 163 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 6 | 1 |
| exclude_trend_cont_24_or_36 | trend_continuation_exclusion | 174.885131 | 0.882979 | 93.818612 | 188 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 9 | 1 |
| exclude_failed_reversal_24_or_36 | failed_reversal_exclusion | 174.885131 | 0.882979 | 93.818612 | 188 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 9 | 1 |
| exclude_trend_cont_36_and_body_lt_0_75_and_range_lt_1_50 | trend_continuation_exclusion | 165.748058 | 0.855670 | 58.203857 | 97 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_failed_reversal_36_and_body_lt_0_75_and_range_lt_1_50 | failed_reversal_exclusion | 165.748058 | 0.855670 | 58.203857 | 97 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_trend_cont_36_and_body_lt_0_75 | trend_continuation_exclusion | 150.964144 | 0.844444 | 47.661804 | 135 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_failed_reversal_36_and_body_lt_0_75 | failed_reversal_exclusion | 150.964144 | 0.844444 | 47.661804 | 135 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_trend_cont_36_and_body_lt_0_70 | trend_continuation_exclusion | 149.154058 | 0.829060 | 41.303516 | 117 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_failed_reversal_36_and_body_lt_0_70 | failed_reversal_exclusion | 149.154058 | 0.829060 | 41.303516 | 117 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 3 | 1 |
| exclude_trend_cont_12_or_24 | trend_continuation_exclusion | 152.320608 | 0.792350 | 12.112978 | 183 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 9 | 1 |
| exclude_failed_reversal_12_or_24 | failed_reversal_exclusion | 152.320608 | 0.792350 | 12.112978 | 183 | 0 | 1.000000 | 1 | 1 | 1 | 1 | 9 | 1 |
| exclude_trend_cont_24 | trend_continuation_exclusion | 135.234294 | 0.772093 | 7.993890 | 215 | 0 | 1.000000 | 1 | 1 | 0 | 0 | 14 | 0 |
| exclude_failed_reversal_24 | failed_reversal_exclusion | 135.234294 | 0.772093 | 7.993890 | 215 | 0 | 1.000000 | 1 | 1 | 0 | 0 | 14 | 0 |
| exclude_trend_cont_12 | trend_continuation_exclusion | 110.971333 | 0.696262 | 4.433805 | 214 | 0 | 1.000000 | 1 | 1 | 0 | 0 | 12 | 0 |
| exclude_failed_reversal_12 | failed_reversal_exclusion | 110.971333 | 0.696262 | 4.433805 | 214 | 0 | 1.000000 | 1 | 1 | 0 | 0 | 12 | 0 |

## Interpretation

1. Does any pre-registered regime/context gate restore recent-period positive expectancy? Yes. The trend-continuation exclusions `exclude_trend_cont_36`, `exclude_trend_cont_24_or_36`, and `exclude_trend_cont_any_12_24_36` all turn the recent bucket positive, and the closest combined gate `exclude_trend_cont_36_and_range_lt_1_50` remains positive with 11 recent trades. Body-only gates do not restore recent positivity.
2. Does any candidate remain positive across early, middle, and recent periods? Yes. The trend-continuation and failed-reversal exclusions at 36 bars satisfy `positive_all_periods`, and the strongest ranked candidates preserve positive expectancy in all three periods. They still require walk-forward validation.
3. Are trend-continuation gates stronger than body/range gates? Yes. Trend-continuation exclusions are the only single-family gates that recover recent positive expectancy, while body-only gates remain negative in the recent period and range-only gates are mixed but weaker.
4. Are combined gates materially better than single gates? Not materially. The combined gates are useful as hypotheses, but they do not dominate the 36-bar trend-continuation exclusions enough to justify any production conclusion.
5. Is there enough evidence to approve a production filter? No. This matrix can nominate gate hypotheses for further validation, but it does not approve a production filter.

## What Is Still Valid

- The canonical replay and the regime/context diagnosis remain valid.
- The gate matrix preserves the same canonical trade population and is suitable for hypothesis generation.

## What Is Not Valid

- No gate is production-approved.
- No gate should be used as a live or paper filter based on this report alone.
- Any apparent improvement could still be sample-specific and must not be treated as evidence of robustness.

## Required Next Research

- Take the top-ranked diagnostic gate candidates and validate them with walk-forward testing on separate periods.
- After candidate selection, apply PSR/DSR/PBO before considering any research gate as a serious contender.
- Do not convert this matrix into a production rule without a separate approval process.
