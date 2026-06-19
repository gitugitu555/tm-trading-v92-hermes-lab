# V9.2 Hermes MFE Path Selectivity Diagnostic Experiment

## Purpose

* Determine whether triggered rescued giveback-loss trades and triggered clipped clean-winner trades are separable using only information available before or at the fixed trigger point.
* This is aggregate-only diagnostic work in Hermes Lab.
* No trading rule is implemented, tuned, or approved.

Proposed experiment name:

`mfe_path_selectivity_diagnostic_experiment`

## Population Accounting

| category | count |
| --- | --- |
| total_inspected | 310 |
| activated_trades | 211 |
| triggered_trades | 166 |
| triggered_rescued_giveback_losses | 46 |
| triggered_clipped_clean_winners | 76 |
| triggered_weak_positive_trades | 44 |
| other_uncategorized_triggered | 0 |

## Trigger Class Accounting

- rescued giveback-loss triggers: `46`
- clipped clean-winner triggers: `76`
- weak-positive triggers: `44`
- other/uncategorized triggered: `0`

## Synthetic Causality Checks

- future-bars-do-not-change-trigger: `passed` (baseline_trigger=12.0, future_trigger=12.0)
- original-exit-labels-do-not-decide-trigger: `passed` (trigger fields stayed fixed after mutating original exit return fields)
- trigger-uses-running-mfe-and-current-return-only: `passed` (trigger_mfe=1200.0000000000011, trigger_return=349.9999999999992)

## Triggered Group Comparison

- activation threshold used only for labeling: `75 bps`
- giveback ratio used only for labeling: `0.50`
- minimum delay used only for labeling: `12` bars

| field | rescued_count | rescued_mean | rescued_median | rescued_p25 | rescued_p75 | rescued_min | rescued_max | clipped_count | clipped_mean | clipped_median | clipped_p25 | clipped_p75 | clipped_min | clipped_max | mean_diff | median_diff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| activation_offset_bars | 46 | 12.087 | 12.000 | 12.000 | 12.000 | 12.000 | 14.000 | 76 | 13.697 | 12.000 | 12.000 | 12.000 | 12.000 | 27.000 | -1.610 | 0.000 |
| trigger_offset_bars | 46 | 13.065 | 12.000 | 12.000 | 13.000 | 12.000 | 22.000 | 76 | 17.737 | 14.000 | 12.000 | 22.250 | 12.000 | 35.000 | -4.672 | -2.000 |
| delay_activation_to_trigger_bars | 46 | 0.978 | 0.000 | 0.000 | 1.000 | 0.000 | 9.000 | 76 | 4.039 | 1.000 | 0.000 | 6.250 | 0.000 | 23.000 | -3.061 | -1.000 |
| running_mfe_at_activation_bps | 46 | 145.330 | 126.813 | 89.653 | 185.287 | 75.078 | 327.943 | 76 | 161.933 | 126.573 | 87.537 | 230.003 | 76.777 | 452.163 | -16.603 | 0.240 |
| running_mfe_at_trigger_bps | 46 | 149.932 | 132.224 | 91.715 | 190.665 | 75.078 | 327.943 | 76 | 185.307 | 155.531 | 93.729 | 249.949 | 76.777 | 452.163 | -35.376 | -23.306 |
| current_return_at_trigger_bps | 46 | -27.711 | -21.041 | -119.610 | 54.161 | -338.956 | 125.104 | 76 | 52.855 | 42.870 | 27.641 | 92.409 | -252.808 | 222.805 | -80.566 | -63.910 |
| giveback_depth_at_trigger_bps | 46 | 177.642 | 142.209 | 116.051 | 225.444 | 50.044 | 484.400 | 76 | 132.452 | 99.512 | 65.718 | 164.400 | 39.796 | 636.621 | 45.191 | 42.697 |
| original_realized_return_bps | 46 | -157.847 | -116.998 | -241.794 | -66.691 | -504.991 | -7.740 | 76 | 215.939 | 202.137 | 121.612 | 265.419 | 51.184 | 822.854 | -373.786 | -319.134 |
| mechanical_fixed_rule_return_bps | 46 | -27.711 | -21.041 | -119.610 | 54.161 | -338.956 | 125.104 | 76 | 52.855 | 42.870 | 27.641 | 92.409 | -252.808 | 222.805 | -80.566 | -63.910 |
| mechanical_minus_original_delta_bps | 46 | 130.137 | 161.191 | 7.229 | 213.053 | -185.640 | 598.003 | 76 | -163.084 | -127.587 | -235.305 | -60.219 | -666.622 | -7.299 | 293.220 | 288.778 |

## By-Year Breakdown

| year | group | count | mean_activation_offset_bars | mean_trigger_offset_bars | mean_delay_activation_to_trigger_bars | mean_running_mfe_at_activation_bps | mean_running_mfe_at_trigger_bps | mean_current_return_at_trigger_bps | mean_giveback_depth_bps | mean_original_return_bps | mean_mechanical_return_bps | mean_mechanical_delta_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | rescued_giveback_loss | 7 | 12.286 | 13.857 | 1.571 | 131.099 | 134.949 | 1.276 | 133.673 | -135.064 | 1.276 | 136.341 |
| 2020 | clipped_clean_winner | 8 | 12.125 | 18.125 | 6.000 | 184.260 | 233.850 | 87.146 | 146.704 | 251.187 | 87.146 | -164.041 |
| 2020 | weak_positive | 1 | 12.000 | 17.000 | 5.000 | 162.174 | 186.921 | 58.219 | 128.702 | 78.770 | 58.219 | -20.551 |
| 2021 | rescued_giveback_loss | 13 | 12.000 | 13.462 | 1.462 | 163.207 | 170.626 | -36.152 | 206.778 | -152.079 | -36.152 | 115.927 |
| 2021 | clipped_clean_winner | 24 | 12.833 | 15.583 | 2.750 | 212.141 | 235.455 | 47.614 | 187.840 | 297.562 | 47.614 | -249.948 |
| 2021 | weak_positive | 16 | 13.625 | 19.125 | 5.500 | 242.608 | 282.150 | 92.979 | 189.171 | 101.784 | 92.979 | -8.805 |
| 2022 | rescued_giveback_loss | 11 | 12.000 | 12.455 | 0.455 | 147.406 | 147.406 | -68.980 | 216.386 | -173.203 | -68.980 | 104.223 |
| 2022 | clipped_clean_winner | 18 | 13.389 | 16.778 | 3.389 | 136.410 | 152.162 | 56.592 | 95.570 | 166.436 | 56.592 | -109.844 |
| 2022 | weak_positive | 11 | 12.727 | 20.182 | 7.455 | 170.530 | 208.521 | 74.223 | 134.298 | 43.154 | 74.223 | 31.069 |
| 2023 | rescued_giveback_loss | 2 | 12.000 | 12.000 | 0.000 | 84.264 | 84.264 | -44.270 | 128.534 | -24.379 | -44.270 | -19.891 |
| 2023 | clipped_clean_winner | 13 | 16.846 | 24.000 | 7.154 | 99.358 | 121.401 | 50.791 | 70.611 | 88.375 | 50.791 | -37.585 |
| 2023 | weak_positive | 7 | 13.429 | 21.286 | 7.857 | 123.690 | 148.982 | 44.040 | 104.942 | 78.712 | 44.040 | -34.673 |
| 2024 | rescued_giveback_loss | 5 | 12.400 | 13.200 | 0.800 | 104.300 | 121.952 | -54.330 | 176.282 | -182.699 | -54.330 | 128.368 |
| 2024 | clipped_clean_winner | 9 | 12.556 | 15.333 | 2.778 | 144.416 | 168.509 | 32.849 | 135.660 | 268.032 | 32.849 | -235.183 |
| 2024 | weak_positive | 4 | 12.000 | 13.750 | 1.750 | 145.715 | 155.419 | 46.102 | 109.318 | 42.014 | 46.102 | 4.087 |
| 2025 | rescued_giveback_loss | 7 | 12.000 | 12.857 | 0.857 | 174.497 | 174.497 | 43.713 | 130.784 | -181.352 | 43.713 | 225.066 |
| 2025 | clipped_clean_winner | 1 | 12.000 | 12.000 | 0.000 | 132.690 | 132.690 | -9.450 | 142.141 | 202.709 | -9.450 | -212.160 |
| 2025 | weak_positive | 2 | 12.000 | 21.500 | 9.500 | 255.357 | 279.546 | 90.921 | 188.625 | 31.885 | 90.921 | 59.035 |
| 2026 | rescued_giveback_loss | 1 | 12.000 | 12.000 | 0.000 | 112.837 | 112.837 | -0.678 | 113.516 | -201.557 | -0.678 | 200.879 |
| 2026 | clipped_clean_winner | 3 | 17.000 | 21.667 | 4.667 | 187.321 | 198.405 | 70.659 | 127.746 | 166.886 | 70.659 | -96.227 |
| 2026 | weak_positive | 3 | 18.667 | 20.000 | 1.333 | 111.114 | 119.319 | 22.295 | 97.024 | 60.415 | 22.295 | -38.120 |

## Recent-Period Focus

| period | group | count | mean_trigger_offset_bars | mean_delay_activation_to_trigger_bars | mean_current_return_at_trigger_bps | mean_giveback_depth_bps | mean_mechanical_delta_bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| historical | rescued_giveback_loss | 38 | 13.132 | 1.026 | -41.579 | 187.962 | 110.788 |
| historical | clipped_clean_winner | 72 | 17.653 | 4.069 | 52.979 | 132.513 | -165.188 |
| historical | weak_positive | 39 | 19.205 | 6.077 | 73.206 | 148.835 | -1.180 |
| recent_decay | rescued_giveback_loss | 8 | 12.750 | 0.750 | 38.164 | 128.625 | 222.042 |
| recent_decay | clipped_clean_winner | 4 | 19.250 | 3.500 | 50.632 | 131.345 | -125.210 |
| recent_decay | weak_positive | 5 | 20.600 | 4.600 | 49.745 | 133.664 | 0.742 |

## Interpretation

A. Are rescued giveback-loss trades and clipped clean-winner trades visibly separable before or at trigger?

Only weakly. Several timing and path features differ in the aggregate, but the distributions overlap materially.

B. Which fields, if any, show the strongest aggregate separation?

The strongest aggregate separation is in `current_return_at_trigger_bps` by mean-difference magnitude, followed by giveback depth and trigger timing.

C. Is the separation stable by year?

No. Year-by-year aggregates move around enough that no stable separability pattern is visible.

D. Is the separation concentrated in the recent decay period?

Yes, partially. The recent-period rows show more contrast than the older periods, but the sample is still small and the pattern is not cleanly isolated.

E. Is there enough evidence to design a second preregistered selective exit rule?

Yes for design-only work, not for implementation. The aggregate differences are sufficient to justify a selectivity-focused preregistration, but not a patched trading rule.

## Stop / Go Conclusion

- decision: `proceed_to_pre_registered_selective_exit_rule_design_only`
- rationale: aggregate path fields show some separation, but not enough to approve a rule. The next step is a design-only selective-exit preregistration, not implementation.

