# C_ExhaustionFade Recent-Period Decay Diagnostics

This report investigates why the canonical post-regime-fix C_ExhaustionFade anchor is positive overall but degraded badly in 2025 and remains weak in 2026.

Source artifacts:
- `reports/c_exhaustion_replay_post_regime_fix/`

The report values were generated from local replay artifacts. The `reports/` directory is not committed to the repository.

## Frozen Canonical Anchor

| metric | value |
|---|---:|
| trade_count | 310 |
| net_expectancy_bps | 44.003106 |
| win_rate | 0.567742 |
| profit_factor | 1.674411 |
| calendar_daily_sharpe_365 | 1.473205 |
| business_day_sharpe_252 | 1.224101 |

## Year-Bucket Comparison

Buckets:
- `early_period = 2020-2021`
- `middle_period = 2022-2024`
- `recent_period = 2025-2026`

| bucket | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | p10_trade_bps | p25_trade_bps | p75_trade_bps | p90_trade_bps | max_win_bps | max_loss_bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| early_period | 103 | 127.104273 | 0.660194 | 2.857439 | 296.176676 | -201.379252 | 110.658593 | -239.486324 | -75.666998 | 291.786831 | 501.139969 | 1835.851662 | -1103.637030 |
| middle_period | 182 | 17.954874 | 0.543956 | 1.339784 | 130.151932 | -115.870533 | 13.882601 | -190.791804 | -69.460090 | 83.846207 | 201.598405 | 701.762188 | -509.660803 |
| recent_period | 25 | -108.742570 | 0.360000 | 0.236562 | 93.598335 | -222.559328 | -91.340308 | -305.999875 | -242.845193 | 34.888705 | 151.085945 | 195.518996 | -516.872446 |

## Year-By-Year Diagnostics

| year | trade_count | net_expectancy_bps | win_rate | profit_factor | avg_win_bps | avg_loss_bps | median_trade_bps | p10_trade_bps | p90_trade_bps | max_loss_bps | max_win_bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 21 | 91.086037 | 0.619048 | 2.579614 | 240.287691 | -151.366651 | 111.138480 | -181.482032 | 347.035649 | -516.990644 | 499.645789 |
| 2021 | 82 | 136.328455 | 0.670732 | 2.915073 | 309.386799 | -216.197800 | 107.062016 | -241.797047 | 596.977924 | -1103.637030 | 1835.851662 |
| 2022 | 83 | 4.204122 | 0.518072 | 1.068219 | 127.068509 | -127.875093 | 13.777798 | -232.060297 | 190.090900 | -509.660803 | 681.568001 |
| 2023 | 73 | -0.478353 | 0.520548 | 0.987271 | 71.272560 | -78.379344 | 1.396007 | -114.386567 | 106.126158 | -367.952847 | 226.174436 |
| 2024 | 26 | 113.606331 | 0.692308 | 2.679255 | 261.818781 | -219.871682 | 122.030185 | -264.463698 | 429.260952 | -300.364831 | 701.762188 |
| 2025 | 16 | -160.751555 | 0.250000 | 0.082751 | 58.009453 | -233.671891 | -194.858866 | -305.426248 | 19.885364 | -417.078643 | 190.709441 |
| 2026 | 9 | -16.282152 | 0.555556 | 0.806392 | 122.069439 | -189.221641 | 52.320933 | -274.220217 | 190.755138 | -516.872446 | 195.518996 |

## Stability Warning

The edge is not stable across the full period. 2025 and 2026 are negative after costs, with 2025 showing severe degradation. This anchor is therefore research-valid but not production-valid. No live, paper-production, or sizing decision should be made until recent-period decay is explained.

## Recent-Period Monthly Diagnostics

| exit_month | trade_count | net_expectancy_bps | win_rate | profit_factor | max_loss_bps | max_win_bps |
|---|---:|---:|---:|---:|---:|---:|
| 2025-02 | 2 | -55.924335 | 0.500000 | 0.630323 | -302.558112 | 190.709441 |
| 2025-03 | 1 | -308.294383 | 0.000000 | 0.000000 | -308.294383 | -308.294383 |
| 2025-04 | 2 | -145.489146 | 0.000000 | 0.000000 | -207.002532 | -83.975760 |
| 2025-05 | 2 | -82.139958 | 0.500000 | 0.028860 | -169.161937 | 4.882022 |
| 2025-06 | 1 | -242.845193 | 0.000000 | 0.000000 | -242.845193 | -242.845193 |
| 2025-10 | 2 | -138.698244 | 0.500000 | 0.005584 | -278.954132 | 1.557644 |
| 2025-11 | 5 | -179.238879 | 0.200000 | 0.037471 | -417.078643 | 34.888705 |
| 2025-12 | 1 | -280.187542 | 0.000000 | 0.000000 | -280.187542 | -280.187542 |
| 2026-01 | 2 | 39.565329 | 0.500000 | 179.289424 | -0.443833 | 79.574491 |
| 2026-02 | 2 | -60.094278 | 0.500000 | 0.437207 | -213.557160 | 93.368604 |
| 2026-03 | 3 | -91.662447 | 0.666667 | 0.467978 | -516.872446 | 189.564173 |
| 2026-04 | 1 | 195.518996 | 1.000000 | inf | 195.518996 | 195.518996 |
| 2026-05 | 1 | -26.013126 | 0.000000 | 0.000000 | -26.013126 | -26.013126 |

## Worst 20 Trades From 2025-2026 By Net Return

| rank | signal_time | entry_time | exit_time | net_return_bps | gross_return_bps | year | exit_month |
|---|---|---|---|---:|---:|---:|---|
| 1 | 2026-03-18 12:17:59.550368 | 2026-03-18 12:17:59.551351 | 2026-03-19 13:13:33.292692 | -516.872446 | -504.872446 | 2026 | 2026-03 |
| 2 | 2025-11-04 05:48:26.248937 | 2025-11-04 05:48:26.248937 | 2025-11-04 18:32:39.025904 | -417.078643 | -405.078643 | 2025 | 2025-11 |
| 3 | 2025-03-09 10:51:57.295657 | 2025-03-09 10:51:57.343501 | 2025-03-10 02:51:22.247807 | -308.294383 | -296.294383 | 2025 | 2025-03 |
| 4 | 2025-01-31 18:55:45.541149 | 2025-01-31 18:55:45.579648 | 2025-02-02 07:51:36.444476 | -302.558112 | -290.558112 | 2025 | 2025-02 |
| 5 | 2025-12-14 20:10:29.092155 | 2025-12-14 20:10:29.092352 | 2025-12-16 08:03:05.158171 | -280.187542 | -268.187542 | 2025 | 2025-12 |
| 6 | 2025-10-29 16:15:49.290504 | 2025-10-29 16:15:49.405953 | 2025-10-30 14:50:09.092105 | -278.954132 | -266.954132 | 2025 | 2025-10 |
| 7 | 2025-06-21 21:32:21.312800 | 2025-06-21 21:32:21.312889 | 2025-06-22 19:06:41.911750 | -242.845193 | -230.845193 | 2025 | 2025-06 |
| 8 | 2025-11-20 16:47:01.967238 | 2025-11-20 16:47:01.969122 | 2025-11-21 05:48:21.487275 | -239.948948 | -227.948948 | 2025 | 2025-11 |
| 9 | 2026-02-05 15:22:13.923932 | 2026-02-05 15:22:13.924184 | 2026-02-05 19:10:00.276377 | -213.557160 | -201.557160 | 2026 | 2026-02 |
| 10 | 2025-04-06 18:49:29.429921 | 2025-04-06 18:49:29.429987 | 2025-04-07 05:21:46.812226 | -207.002532 | -195.002532 | 2025 | 2025-04 |
| 11 | 2025-11-03 03:16:53.516324 | 2025-11-03 03:16:53.531978 | 2025-11-04 01:07:52.017523 | -182.715200 | -170.715200 | 2025 | 2025-11 |
| 12 | 2025-05-28 15:58:46.443667 | 2025-05-28 15:58:46.443849 | 2025-05-30 01:21:26.134700 | -169.161937 | -157.161937 | 2025 | 2025-05 |
| 13 | 2025-11-21 07:34:28.954792 | 2025-11-21 07:34:28.954792 | 2025-11-21 12:30:21.513098 | -91.340308 | -79.340308 | 2025 | 2025-11 |
| 14 | 2025-04-02 23:04:04.579711 | 2025-04-02 23:04:04.579829 | 2025-04-03 20:10:49.898894 | -83.975760 | -71.975760 | 2025 | 2025-04 |
| 15 | 2026-05-07 14:07:47.113084 | 2026-05-07 14:07:47.113084 | 2026-05-09 07:27:02.915893 | -26.013126 | -14.013126 | 2026 | 2026-05 |
| 16 | 2026-01-07 18:56:50.871172 | 2026-01-07 18:56:50.872085 | 2026-01-09 15:25:34.632981 | -0.443833 | 11.556167 | 2026 | 2026-01 |
| 17 | 2025-10-14 05:34:44.926668 | 2025-10-14 05:34:44.926668 | 2025-10-15 00:43:33.326291 | 1.557644 | 13.557644 | 2025 | 2025-10 |
| 18 | 2025-05-23 23:48:59.337118 | 2025-05-23 23:48:59.337118 | 2025-05-25 15:22:03.067959 | 4.882022 | 16.882022 | 2025 | 2025-05 |
| 19 | 2025-11-16 22:05:45.034816 | 2025-11-16 22:05:45.035740 | 2025-11-17 17:35:39.134235 | 34.888705 | 46.888705 | 2025 | 2025-11 |
| 20 | 2026-03-27 10:55:26.040837 | 2026-03-27 10:55:26.040837 | 2026-03-28 19:54:33.239209 | 52.320933 | 64.320933 | 2026 | 2026-03 |

## Loss Anatomy

| metric | recent_period | early_period | delta |
|---|---:|---:|---:|
| recent_avg_loss_vs_early_avg_loss | -222.559328 | -201.379252 | -21.180077 |
| recent_avg_win_vs_early_avg_win | 93.598335 | 296.176676 | -202.578341 |
| recent_win_rate_vs_early_win_rate | 0.360000 | 0.660194 | -0.300194 |
| recent_max_loss_vs_early_max_loss | -516.872446 | -1103.637030 | 586.764584 |

Additional tail diagnostics:
- Positive outliers largely disappeared in 2025-2026. There are 0 trades at or above +200 bps in the recent period, versus 39 in 2020-2021.
- There are 0 trades at or above +300 bps in the recent period, versus 23 in 2020-2021.
- Negative tail events are more concentrated in the recent period: 4 of 25 recent trades are at or below -300 bps, versus 6 of 103 early-period trades.

Diagnosis:
- The decay is driven primarily by a much lower win rate and much smaller winners.
- Larger losers are a secondary contributor because recent average losses are worse than early-period losses, but the maximum single loss is not the main change signal.
- Fewer positive outlier trades are a major explanation for the collapse in expectancy.
- Larger negative tail events exist in the recent sample, but the more important structural break is that the positive tail has largely vanished.

## Drawdown Diagnostics

| metric | value |
|---|---:|
| max_drawdown_pct | 11.154946 |
| max_drawdown_date | 2026-03-19 |
| equity_at_peak_before_max_dd | 263595.271496 |
| equity_at_trough | 234191.361025 |
| peak_to_end_drawdown_pct | -10.313403 |

## Decision

### What is still valid

- The strategy remains research-valid as a historical anchor.
- The post-regime-fix replay path is internally consistent and the canonical anchor is frozen.
- The anchor still demonstrates positive long-run expectancy across the full sample.

### What is not valid

- The strategy is not production-valid because 2025 and 2026 show recent-period degradation.
- The recent-period win rate, average winner size, and positive tail frequency are materially weaker than 2020-2021.
- The recent negative expectancy makes the historical anchor unsafe as a forward production proxy.

### Required next research

- Compare 2025-2026 market regimes against 2020-2024.
- Inspect whether recent losses cluster around high volatility, low liquidity, trend-continuation, or failed reversal states.
- Test whether C_ExhaustionFade requires an additional recent-period regime gate.
- Only after diagnostics, consider PSR/DSR/PBO.
