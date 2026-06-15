# C_ExhaustionFade Signal-State Attribution

## Purpose

This report attributes the recent-period C_ExhaustionFade decay to signal-state context, using the canonical post-regime-fix replay artifacts and the raw 750 BTC bar stream.

## Data Sources

- Trade log: `reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Raw bars: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Canonical replay helpers: `attach_c_exhaustion_signal`, `normalize_v92_bar_timestamps`, `add_v92_regime_labels`
- Canonical anchor values: `reports/c_exhaustion_replay_post_regime_fix/` summary artifacts

Signal-field note: All requested signal fields were available directly from the canonical signal frame or derivable from retained primitives. `volume_over_vol95_ratio` and `body_to_range_ratio` were computed from `volume / vol_roll_95` and `body_size / bar_range` respectively. No future information was introduced.

## Executive Finding

Recent-period failures are not explained by one catastrophic loss. The strategy still produces favorable excursion on every recent loser, but the favorable move is much smaller than in 2020-2021 and is often given back before the fixed-horizon exit. The realized +200 bps tail disappears even though some recent trades still reach >200 bps MFE. That is most consistent with exit-horizon mismatch and positive-tail decay, with a regime/context shift likely contributing inside the EXHAUSTED label.

## Early vs Middle vs Recent Comparison

| period | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| early_period | 103 | 127.104273 | 0.660194 | 2.857439 | 296.176676 | -201.379252 | 110.658593 | 331.241537 | -209.788936 | 275.310689 | -156.640715 | 665.884249 | -514.290227 | 39 | 0.378641 | 13 | 0.126214 |
| middle_period | 182 | 17.954874 | 0.543956 | 1.339784 | 130.151932 | -115.870533 | 13.882601 | 142.873869 | -112.062019 | 91.798045 | -75.307963 | 308.780885 | -255.788413 | 21 | 0.115385 | 17 | 0.093407 |
| recent_period | 25 | -108.742570 | 0.360000 | 0.236562 | 93.598335 | -222.559328 | -91.340308 | 153.631562 | -233.962608 | 129.630909 | -230.278520 | 323.853220 | -395.113339 | 0 | 0.000000 | 10 | 0.400000 |

## Forward Path Diagnostics

The raw path metrics show that the recent period still gets bounce, but the bounce is materially smaller and is commonly not monetized at the fixed exit.

| year | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 91.086037 | 0.619048 | 2.579614 | 252.320152 | -154.109099 | 209.071081 | -89.990264 | 452.516430 | -292.752373 | 8 | 2 |
| 2021 | 82 | 136.328455 | 0.670732 | 2.915073 | 351.453111 | -224.048406 | 299.425298 | -166.752797 | 701.716690 | -523.153230 | 31 | 11 |
| 2022 | 83 | 4.204122 | 0.518072 | 1.068219 | 149.459047 | -118.247235 | 94.733721 | -79.267214 | 298.439170 | -285.473913 | 8 | 11 |
| 2023 | 73 | -0.478353 | 0.520548 | 0.987271 | 88.236265 | -87.712245 | 68.515946 | -60.790912 | 179.229698 | -168.170448 | 2 | 2 |
| 2024 | 26 | 113.606331 | 0.692308 | 2.679255 | 275.257537 | -160.683581 | 251.376019 | -133.094992 | 488.325550 | -303.783104 | 11 | 4 |
| 2025 | 16 | -160.751555 | 0.250000 | 0.082751 | 148.943370 | -256.959582 | 141.609541 | -279.981793 | 316.969126 | -390.837377 | 0 | 8 |
| 2026 | 9 | -16.282152 | 0.555556 | 0.806392 | 161.966127 | -193.079098 | 129.630909 | -163.986784 | 327.266080 | -353.313606 | 0 | 2 |

| exit_month | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | positive_tail_count_ge_200bps | negative_tail_count_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-02 | 2 | -55.924335 | 0.500000 | 0.630323 | 177.395644 | -213.352724 | 177.395644 | -213.352724 | 0 | 1 |
| 2025-03 | 1 | -308.294383 | 0.000000 | 0.000000 | 36.090516 | -565.187713 | 36.090516 | -565.187713 | 0 | 1 |
| 2025-04 | 2 | -145.489146 | 0.000000 | 0.000000 | 148.757905 | -224.252676 | 148.757905 | -224.252676 | 0 | 1 |
| 2025-05 | 2 | -82.139958 | 0.500000 | 0.028860 | 211.957098 | -119.400496 | 211.957098 | -119.400496 | 0 | 0 |
| 2025-06 | 1 | -242.845193 | 0.000000 | 0.000000 | 193.500762 | -272.401114 | 193.500762 | -272.401114 | 0 | 1 |
| 2025-10 | 2 | -138.698244 | 0.500000 | 0.005584 | 79.044716 | -293.924321 | 79.044716 | -293.924321 | 0 | 1 |
| 2025-11 | 5 | -179.238879 | 0.200000 | 0.037471 | 146.750905 | -240.489298 | 57.344483 | -287.562472 | 0 | 2 |
| 2025-12 | 1 | -280.187542 | 0.000000 | 0.000000 | 185.437389 | -369.457568 | 185.437389 | -369.457568 | 0 | 1 |
| 2026-01 | 2 | 39.565329 | 0.500000 | 179.289424 | 107.400510 | -182.047677 | 107.400510 | -182.047677 | 0 | 0 |
| 2026-02 | 2 | -60.094278 | 0.500000 | 0.437207 | 265.000342 | -250.020137 | 265.000342 | -250.020137 | 0 | 1 |
| 2026-03 | 3 | -91.662447 | 0.666667 | 0.467978 | 153.755597 | -219.411171 | 129.630909 | -132.411370 | 0 | 1 |
| 2026-04 | 1 | 195.518996 | 1.000000 | inf | 218.270704 | -61.647257 | 218.270704 | -61.647257 | 0 | 0 |
| 2026-05 | 1 | -26.013126 | 0.000000 | 0.000000 | 33.355940 | -153.695479 | 33.355940 | -153.695479 | 0 | 0 |

## Signal-State Attribution

Executed trades by regime: EXHAUSTED=310. The regime label is therefore degenerate on the executed sample; the useful separation comes from location and candle-shape features within EXHAUSTED.

### adr_stretch bucket

| adr_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <0.15 | 8 | -47.570158 | 0.500000 | 0.493833 | 92.821921 | -187.962237 | -28.225801 | 221.470399 | -187.201775 | 240.417687 | -179.108018 | 336.549360 | -312.195798 | 0 | 0.000000 | 3 | 0.375000 |
| 0.15-0.35 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| 0.35-0.65 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| 0.65-0.85 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| >0.85 | 17 | -137.529587 | 0.294118 | 0.167704 | 94.219465 | -234.091692 | -169.161937 | 121.707404 | -255.967706 | 97.796256 | -255.631575 | 232.311860 | -450.013966 | 0 | 0.000000 | 7 | 0.411765 |

### body_to_range_ratio bucket

| body_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <0.10 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| 0.10-0.25 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| 0.25-0.50 | 6 | -103.088481 | 0.333333 | 0.218508 | 86.471547 | -197.868495 | -104.364163 | 120.696279 | -259.258734 | 75.180353 | -243.835521 | 271.034379 | -364.555166 | 0 | 0.000000 | 2 | 0.333333 |
| >0.50 | 19 | -110.528071 | 0.368421 | 0.241722 | 95.634559 | -230.789606 | -91.340308 | 164.032178 | -225.974357 | 170.540601 | -230.278520 | 321.234245 | -431.115576 | 0 | 0.000000 | 8 | 0.421053 |

### volume_over_vol95_ratio bucket

| volume_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <1.00 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| 1.00-1.25 | 25 | -108.742570 | 0.360000 | 0.236562 | 93.598335 | -222.559328 | -91.340308 | 153.631562 | -233.962608 | 129.630909 | -230.278520 | 323.853220 | -395.113339 | 0 | 0.000000 | 10 | 0.400000 |
| 1.25-1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |
| >1.75 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 0.000000 |

### mfe_bps bucket

| mfe_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <50 | 6 | -262.733703 | 0.000000 | 0.000000 | 0.000000 | -262.733703 | -271.253530 | 25.079645 | -363.969447 | 30.837516 | -335.330940 | 36.831299 | -535.948424 | 0 | 0.000000 | 4 | 0.666667 |
| 50-100 | 4 | -173.729741 | 0.250000 | 0.002236 | 1.557644 | -232.158869 | -139.698982 | 78.307543 | -291.013153 | 79.044716 | -293.924321 | 93.831528 | -388.217151 | 0 | 0.000000 | 2 | 0.500000 |
| 100-200 | 8 | -133.104337 | 0.250000 | 0.110213 | 65.947712 | -199.455021 | -188.082235 | 158.374944 | -246.015902 | 171.954958 | -251.339817 | 187.856401 | -331.312577 | 0 | 0.000000 | 4 | 0.500000 |
| >200 | 7 | 88.227376 | 0.857143 | 7.761436 | 118.155324 | -91.340308 | 93.368604 | 301.440209 | -76.152669 | 319.924758 | -61.647257 | 339.418219 | -177.914512 | 0 | 0.000000 | 0 | 0.000000 |

### mae_bps bucket

| mae_bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | avg_mfe_bps | avg_mae_bps | median_mfe_bps | median_mae_bps | p90_mfe_bps | p10_mae_bps | positive_tail_count_ge_200bps | positive_tail_rate_ge_200bps | negative_tail_count_le_minus_200bps | negative_tail_rate_le_minus_200bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| >-50 | 3 | 76.444967 | 1.000000 | inf | 76.444967 | 0.000000 | 34.888705 | 293.588137 | -15.384236 | 307.466058 | -18.517229 | 317.433018 | -18.993852 | 0 | 0.000000 | 0 | 0.000000 |
| -100 to -50 | 2 | 193.114219 | 1.000000 | inf | 193.114219 | 0.000000 | 193.114219 | 272.371449 | -64.349970 | 272.371449 | -64.349970 | 315.652046 | -66.512141 | 0 | 0.000000 | 0 | 0.000000 |
| -200 to -100 | 6 | -9.347248 | 0.333333 | 0.722047 | 72.844768 | -50.443257 | -13.228479 | 188.365765 | -160.228664 | 157.234119 | -158.841131 | 342.287077 | -179.108018 | 0 | 0.000000 | 0 | 0.000000 |
| <-200 | 14 | -234.146007 | 0.142857 | 0.024152 | 40.566068 | -279.931352 | -241.397070 | 91.791940 | -336.631469 | 79.044716 | -312.986920 | 181.816967 | -478.361551 | 0 | 0.000000 | 10 | 0.714286 |

## Recent Failure Modes

- Recent losers still showed favorable excursion: 16 of 16 recent losers had positive MFE, and 7 reached at least +100 bps MFE.
- The realized +200 bps tail disappeared because the move was often given back before exit: 7 recent trades reached >200 bps MFE, but 0 recent trades realized >=200 bps net.
- Recent losses still carried adverse continuation too: 12 of 16 recent losers had MAE <= -200 bps.
- The median recent loss had MFE/realized-return ratio of 0.634639 and abs(MAE)/realized-return ratio of 1.490152.
- These diagnostics fit a mixed failure mode: bounce exists, but it is both smaller than before and frequently handed back before the fixed exit. The loss tail also remains active, so this is not pure exit drift alone.

## What Is Still Valid

- The canonical replay path is still mechanically valid and reproducible.
- The signal still captures some favorable excursion, so the alpha is not fully dead.

## What Is Not Valid

- The recent-period performance is not production-valid.
- The signal cannot be treated as stable across 2025-2026 without explaining the recent decay.
- The fixed-horizon exit is not reliably capturing the favorable move that still appears intratrade.

## Required Next Research

- Compare 2025-2026 market regimes against 2020-2024.
- Inspect whether recent losses cluster around high volatility, low liquidity, trend-continuation, or failed reversal states.
- Test whether C_ExhaustionFade requires an additional recent-period regime gate.
- Only after diagnostics, consider PSR/DSR/PBO.
