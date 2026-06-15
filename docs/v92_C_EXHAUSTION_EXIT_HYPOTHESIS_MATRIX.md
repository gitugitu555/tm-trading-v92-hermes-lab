# C_ExhaustionFade Exit Hypothesis Matrix

## Purpose

This matrix tests whether the repaired C_ExhaustionFade entries still contain exploitable post-entry excursion under a small, pre-registered set of diagnostic exit families.

## Data Sources

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical trade population: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Cost model: `round_trip_cost_bps = 12.0`

## Method

The matrix reuses the already-executed canonical C trades and reconstructs post-entry paths from the raw bars. It evaluates only pre-registered diagnostic exit families and reports the realized metrics under the same 12 bps round-trip cost used by the anchor.

## Candidate Families

- Family A: fixed horizons (`horizon_3`, `horizon_6`, `horizon_9`, `horizon_12`, `horizon_18`, `horizon_24`, `horizon_36`, `horizon_48`)
- Family B: TP fallback to 36-bar exit (`tp_50_bps`, `tp_100_bps`, `tp_150_bps`, `tp_200_bps`)
- Family C: giveback fallback to 36-bar exit (`giveback_50_bps`, `giveback_100_bps`, `giveback_150_bps`)
- Family D: `first_positive_close` fallback to 36-bar exit

## All-Period Results

| candidate | family | period | trade_count | gross_expectancy_bps | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | p10_trade_bps | p25_trade_bps | p75_trade_bps | p90_trade_bps | max_win_bps | max_loss_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps | avg_hold_bars | median_hold_bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| horizon_3 | A_fixed_horizon | all_period | 310 | 20.263172 | 8.263172 | 0.512903 | 1.300168 | 69.782540 | -56.515500 | 1.284191 | -77.547621 | -36.929852 | 41.087559 | 115.611443 | 769.585249 | -577.943239 | 11 | 0.035484 | 6 | 0.019355 | 3.000000 | 3.000000 |
| horizon_6 | A_fixed_horizon | all_period | 310 | 32.892100 | 20.892100 | 0.554839 | 1.727039 | 89.445734 | -64.551560 | 10.423529 | -100.916668 | -32.700689 | 57.134612 | 156.428898 | 846.536358 | -389.370310 | 17 | 0.054839 | 7 | 0.022581 | 6.000000 | 6.000000 |
| horizon_9 | A_fixed_horizon | all_period | 310 | 33.601767 | 21.601767 | 0.554839 | 1.582788 | 105.738921 | -83.264830 | 7.659147 | -123.932031 | -54.451507 | 74.653309 | 175.876298 | 1204.704135 | -486.937838 | 24 | 0.077419 | 11 | 0.035484 | 9.000000 | 9.000000 |
| horizon_12 | A_fixed_horizon | all_period | 310 | 41.537232 | 29.537232 | 0.551613 | 1.769011 | 123.178084 | -85.661225 | 9.569837 | -132.209279 | -62.106349 | 89.369227 | 198.144768 | 1792.663593 | -510.486879 | 30 | 0.096774 | 8 | 0.025806 | 12.000000 | 12.000000 |
| horizon_18 | A_fixed_horizon | all_period | 310 | 52.178144 | 40.178144 | 0.567742 | 1.907071 | 148.786859 | -102.472108 | 15.499822 | -153.705951 | -68.757448 | 115.006538 | 245.660209 | 1369.479084 | -426.757493 | 47 | 0.151613 | 16 | 0.051613 | 18.000000 | 18.000000 |
| horizon_24 | A_fixed_horizon | all_period | 310 | 52.083170 | 40.083170 | 0.548387 | 1.761359 | 169.096017 | -116.575288 | 15.009026 | -168.054734 | -70.442191 | 114.052318 | 286.135249 | 1722.458435 | -548.607000 | 52 | 0.167742 | 26 | 0.083871 | 24.000000 | 24.000000 |
| horizon_36 | A_fixed_horizon | all_period | 310 | 56.003106 | 44.003106 | 0.567742 | 1.674411 | 192.428637 | -150.943860 | 33.124045 | -241.452964 | -88.279613 | 148.494749 | 326.880210 | 1835.851662 | -1103.637030 | 60 | 0.193548 | 40 | 0.129032 | 36.000000 | 36.000000 |
| horizon_48 | A_fixed_horizon | all_period | 310 | 45.473350 | 33.473350 | 0.538710 | 1.397537 | 218.439162 | -182.535676 | 15.940618 | -280.028587 | -120.006095 | 165.829419 | 349.216238 | 1588.274897 | -723.525668 | 64 | 0.206452 | 52 | 0.167742 | 48.000000 | 48.000000 |
| tp_50_bps | B_tp_fallback | all_period | 310 | 15.731769 | 3.731769 | 0.819355 | 1.138292 | 37.488516 | -149.379188 | 38.000000 | -83.874213 | 38.000000 | 38.000000 | 38.000000 | 38.000000 | -1103.637030 | 0 | 0.000000 | 15 | 0.048387 | 10.532258 | 3.000000 |
| tp_100_bps | B_tp_fallback | all_period | 310 | 18.712582 | 6.712582 | 0.683871 | 1.139509 | 80.173746 | -152.203404 | 88.000000 | -183.664079 | -28.935682 | 88.000000 | 88.000000 | 88.000000 | -1103.637030 | 0 | 0.000000 | 29 | 0.093548 | 19.690323 | 18.500000 |
| tp_150_bps | B_tp_fallback | all_period | 310 | 33.929004 | 21.929004 | 0.645161 | 1.423283 | 114.290700 | -146.001352 | 80.109229 | -198.764530 | -44.417444 | 138.000000 | 138.000000 | 138.000000 | -1103.637030 | 0 | 0.000000 | 31 | 0.100000 | 23.709677 | 36.000000 |
| tp_200_bps | B_tp_fallback | all_period | 310 | 36.475144 | 24.475144 | 0.603226 | 1.410152 | 139.497596 | -150.396389 | 50.503859 | -231.703846 | -71.366498 | 188.000000 | 188.000000 | 188.000000 | -1103.637030 | 0 | 0.000000 | 37 | 0.119355 | 27.006452 | 36.000000 |
| giveback_50_bps | C_giveback_fallback | all_period | 310 | 4.659972 | -7.340028 | 0.300000 | 0.667070 | 49.022337 | -31.495328 | -19.863895 | -53.537455 | -38.977795 | 7.364663 | 50.348530 | 346.286517 | -61.997311 | 4 | 0.012903 | 0 | 0.000000 | 4.048387 | 0.000000 |
| giveback_100_bps | C_giveback_fallback | all_period | 310 | -3.231227 | -15.231227 | 0.341935 | 0.591063 | 64.382663 | -56.599228 | -32.028727 | -89.912032 | -68.908148 | 19.044620 | 82.254195 | 294.234826 | -111.584719 | 4 | 0.012903 | 0 | 0.000000 | 11.390323 | 5.000000 |
| giveback_150_bps | C_giveback_fallback | all_period | 310 | 10.010196 | -1.989804 | 0.438710 | 0.958054 | 103.593367 | -84.514581 | -19.266254 | -130.932778 | -95.978045 | 63.193689 | 133.233593 | 535.319899 | -161.586817 | 23 | 0.074194 | 0 | 0.000000 | 18.338710 | 14.000000 |
| first_positive_close | D_first_positive_close | all_period | 310 | 24.100148 | 12.100148 | 0.645161 | 2.064981 | 36.366084 | -32.019737 | 7.374917 | -10.307888 | -4.515959 | 29.605908 | 65.531154 | 356.551188 | -516.872446 | 4 | 0.012903 | 6 | 0.019355 | 3.977419 | 0.000000 |

## Early vs Middle vs Recent Stability

A candidate is marked `positive_all_periods` only when early, middle, and recent net expectancy are all positive. That is a stability flag, not an approval.

| candidate | family | period | net_expectancy_bps | win_rate | profit_factor | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| horizon_3 | A_fixed_horizon | early_period | 23.524815 | 0.533981 | 1.619459 | 7 | 5 |
| horizon_6 | A_fixed_horizon | early_period | 45.951122 | 0.601942 | 2.307194 | 11 | 5 |
| horizon_9 | A_fixed_horizon | early_period | 55.953716 | 0.621359 | 2.213530 | 19 | 6 |
| horizon_12 | A_fixed_horizon | early_period | 78.746079 | 0.640777 | 2.702687 | 23 | 4 |
| horizon_18 | A_fixed_horizon | early_period | 101.893950 | 0.640777 | 3.104117 | 30 | 7 |
| horizon_24 | A_fixed_horizon | early_period | 108.861933 | 0.640777 | 2.881978 | 34 | 12 |
| horizon_36 | A_fixed_horizon | early_period | 127.104273 | 0.660194 | 2.857439 | 39 | 13 |
| horizon_48 | A_fixed_horizon | early_period | 100.094799 | 0.582524 | 2.020309 | 38 | 21 |
| tp_50_bps | B_tp_fallback | early_period | 8.790740 | 0.922330 | 1.334786 | 0 | 4 |
| tp_100_bps | B_tp_fallback | early_period | 28.659883 | 0.815534 | 1.673238 | 0 | 8 |
| tp_150_bps | B_tp_fallback | early_period | 52.888858 | 0.757282 | 2.077088 | 0 | 9 |
| tp_200_bps | B_tp_fallback | early_period | 70.007543 | 0.718447 | 2.217513 | 0 | 11 |
| giveback_50_bps | C_giveback_fallback | early_period | 4.374445 | 0.378641 | 1.225908 | 4 | 0 |
| giveback_100_bps | C_giveback_fallback | early_period | -12.768725 | 0.339806 | 0.643831 | 2 | 0 |
| giveback_150_bps | C_giveback_fallback | early_period | 9.131216 | 0.417476 | 1.190414 | 13 | 0 |
| first_positive_close | D_first_positive_close | early_period | 33.669649 | 0.737864 | 5.339013 | 4 | 1 |

| candidate | family | period | net_expectancy_bps | win_rate | profit_factor | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| horizon_3 | A_fixed_horizon | middle_period | 0.887615 | 0.510989 | 1.041384 | 3 | 1 |
| horizon_6 | A_fixed_horizon | middle_period | 10.599865 | 0.538462 | 1.491064 | 5 | 2 |
| horizon_9 | A_fixed_horizon | middle_period | 6.950520 | 0.538462 | 1.254084 | 3 | 4 |
| horizon_12 | A_fixed_horizon | middle_period | 5.932554 | 0.521978 | 1.185600 | 4 | 3 |
| horizon_18 | A_fixed_horizon | middle_period | 15.165969 | 0.554945 | 1.410736 | 15 | 6 |
| horizon_24 | A_fixed_horizon | middle_period | 14.815263 | 0.521978 | 1.331414 | 17 | 10 |
| horizon_36 | A_fixed_horizon | middle_period | 17.954874 | 0.543956 | 1.339784 | 21 | 17 |
| horizon_48 | A_fixed_horizon | middle_period | 17.618080 | 0.543956 | 1.277542 | 23 | 22 |
| tp_50_bps | B_tp_fallback | middle_period | 6.075849 | 0.769231 | 1.270747 | 0 | 7 |
| tp_100_bps | B_tp_fallback | middle_period | 0.440955 | 0.615385 | 1.009718 | 0 | 15 |
| tp_150_bps | B_tp_fallback | middle_period | 11.213556 | 0.587912 | 1.239465 | 0 | 15 |
| tp_200_bps | B_tp_fallback | middle_period | 13.168536 | 0.565934 | 1.263180 | 0 | 16 |
| giveback_50_bps | C_giveback_fallback | middle_period | -13.502547 | 0.263736 | 0.432822 | 0 | 0 |
| giveback_100_bps | C_giveback_fallback | middle_period | -14.917239 | 0.357143 | 0.596025 | 2 | 0 |
| giveback_150_bps | C_giveback_fallback | middle_period | -0.707742 | 0.467033 | 0.983843 | 10 | 0 |
| first_positive_close | D_first_positive_close | middle_period | 4.253135 | 0.598901 | 1.464824 | 0 | 3 |

| candidate | family | period | net_expectancy_bps | win_rate | profit_factor | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| horizon_3 | A_fixed_horizon | recent_period | -0.920741 | 0.440000 | 0.967971 | 1 | 0 |
| horizon_6 | A_fixed_horizon | recent_period | -7.423602 | 0.480000 | 0.863421 | 1 | 0 |
| horizon_9 | A_fixed_horizon | recent_period | -13.267180 | 0.400000 | 0.811839 | 2 | 1 |
| horizon_12 | A_fixed_horizon | recent_period | -1.361157 | 0.400000 | 0.974335 | 3 | 1 |
| horizon_18 | A_fixed_horizon | recent_period | -32.002339 | 0.360000 | 0.604564 | 2 | 3 |
| horizon_24 | A_fixed_horizon | recent_period | -59.334977 | 0.360000 | 0.333785 | 1 | 4 |
| horizon_36 | A_fixed_horizon | recent_period | -108.742570 | 0.360000 | 0.236562 | 0 | 10 |
| horizon_48 | A_fixed_horizon | recent_period | -125.580655 | 0.320000 | 0.293678 | 3 | 9 |
| tp_50_bps | B_tp_fallback | recent_period | -34.176089 | 0.760000 | 0.458005 | 0 | 4 |
| tp_100_bps | B_tp_fallback | recent_period | -38.052847 | 0.640000 | 0.581447 | 0 | 6 |
| tp_150_bps | B_tp_fallback | recent_period | -27.617131 | 0.600000 | 0.721588 | 0 | 7 |
| tp_200_bps | B_tp_fallback | recent_period | -80.806235 | 0.400000 | 0.417757 | 0 | 10 |
| giveback_50_bps | C_giveback_fallback | recent_period | -10.740520 | 0.240000 | 0.470620 | 0 | 0 |
| giveback_100_bps | C_giveback_fallback | recent_period | -27.662559 | 0.240000 | 0.389678 | 0 | 0 |
| giveback_150_bps | C_giveback_fallback | recent_period | -57.141814 | 0.320000 | 0.203632 | 0 | 0 |
| first_positive_close | D_first_positive_close | recent_period | -19.639948 | 0.600000 | 0.535750 | 0 | 2 |

## Recent-Period Results

Recent-period positive expectancy is the key filter here. The matrix is designed to show whether any pre-registered family still earns enough in 2025-2026 to justify further validation.

| candidate | family | period | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_hold_bars | median_hold_bars | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| horizon_3 | A_fixed_horizon | recent_period | 25 | -0.920741 | 0.440000 | 0.967971 | 3.000000 | 3.000000 | 1 | 0 |
| horizon_6 | A_fixed_horizon | recent_period | 25 | -7.423602 | 0.480000 | 0.863421 | 6.000000 | 6.000000 | 1 | 0 |
| horizon_9 | A_fixed_horizon | recent_period | 25 | -13.267180 | 0.400000 | 0.811839 | 9.000000 | 9.000000 | 2 | 1 |
| horizon_12 | A_fixed_horizon | recent_period | 25 | -1.361157 | 0.400000 | 0.974335 | 12.000000 | 12.000000 | 3 | 1 |
| horizon_18 | A_fixed_horizon | recent_period | 25 | -32.002339 | 0.360000 | 0.604564 | 18.000000 | 18.000000 | 2 | 3 |
| horizon_24 | A_fixed_horizon | recent_period | 25 | -59.334977 | 0.360000 | 0.333785 | 24.000000 | 24.000000 | 1 | 4 |
| horizon_36 | A_fixed_horizon | recent_period | 25 | -108.742570 | 0.360000 | 0.236562 | 36.000000 | 36.000000 | 0 | 10 |
| horizon_48 | A_fixed_horizon | recent_period | 25 | -125.580655 | 0.320000 | 0.293678 | 48.000000 | 48.000000 | 3 | 9 |
| tp_50_bps | B_tp_fallback | recent_period | 25 | -34.176089 | 0.760000 | 0.458005 | 11.320000 | 2.000000 | 0 | 4 |
| tp_100_bps | B_tp_fallback | recent_period | 25 | -38.052847 | 0.640000 | 0.581447 | 18.640000 | 11.000000 | 0 | 6 |
| tp_150_bps | B_tp_fallback | recent_period | 25 | -27.617131 | 0.600000 | 0.721588 | 22.880000 | 36.000000 | 0 | 7 |
| tp_200_bps | B_tp_fallback | recent_period | 25 | -80.806235 | 0.400000 | 0.417757 | 29.600000 | 36.000000 | 0 | 10 |
| giveback_50_bps | C_giveback_fallback | recent_period | 25 | -10.740520 | 0.240000 | 0.470620 | 0.480000 | 0.000000 | 0 | 0 |
| giveback_100_bps | C_giveback_fallback | recent_period | 25 | -27.662559 | 0.240000 | 0.389678 | 3.720000 | 2.000000 | 0 | 0 |
| giveback_150_bps | C_giveback_fallback | recent_period | 25 | -57.141814 | 0.320000 | 0.203632 | 8.520000 | 7.000000 | 0 | 0 |
| first_positive_close | D_first_positive_close | recent_period | 25 | -19.639948 | 0.600000 | 0.535750 | 8.000000 | 0.000000 | 0 | 2 |

## Failure Modes

Shorter fixed horizons reduce recent losses relative to the configured 36-bar exit, but no pre-registered diagnostic family restores recent-period positive expectancy. Take-profit and giveback candidates still matter because they change the loss profile, but they do not create a positive recent-period anchor here.
The matrix therefore supports exit-horizon mismatch as a research direction, not as an approved replacement exit.

## Interpretation

Answer to question 1: no. Recent-period positive expectancy is restored by diagnostic candidates: none.
Answer to question 2: no candidate remains positive in early, middle, and recent periods; stable across all periods: none.
Answer to question 3: shorter fixed horizons help by reducing recent losses, and TP/giveback behavior is also informative, but no diagnostic family restores positive recent expectancy.
Answer to question 4: yes. The matrix supports exit-horizon mismatch as the next research path because the shorter horizons materially reduce recent damage versus the 36-bar baseline.
Answer to question 5: No. This matrix can nominate exit hypotheses for further validation, but it does not approve a replacement exit.

## What Is Still Valid

- The canonical entry population remains valid for research diagnostics.
- The diagnostic matrix is internally consistent with the repaired replay path.
- The least-bad recent-period diagnostic candidates are worth follow-up validation.

## What Is Not Valid

- No candidate here is production-approved.
- No candidate should be treated as a final replacement exit without walk-forward validation.
- This matrix is not optimization; it is a pre-registered hypothesis screen.

## Required Next Research

- Re-run the most promising diagnostic candidates in a walk-forward protocol.
- After candidate selection, apply PSR/DSR/PBO.
- Compare candidate behavior across regimes and session slices.
- Keep production approval out of scope until validation is complete.
