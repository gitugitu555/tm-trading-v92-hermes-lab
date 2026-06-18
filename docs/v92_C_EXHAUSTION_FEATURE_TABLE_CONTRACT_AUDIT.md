# V9.2 C_Exhaustion Feature Table Contract Audit

## Purpose

Formalize the approved signal-time feature schema and verify feature availability, nullness, and finite coverage by year before any Gate 3 meta-label or predictive experiment.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- max_trades: `5000`
- max_bar_files: `120`
- max_bars: `250000`
- inspected_trade_rows: `310`
- inspected_bar_rows: `203900`
- inspected_bar_files: `90`

## Read-Only Guardrails

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No feature-table artifacts were written.
- No market-data artifacts were written.
- No strategy backtest was run.
- No model was trained.
- No predictive metrics were computed.
- No alpha claim is made.
- Full reconstruction remains blocked.

## Alignment Convention Used

- signal_time = signal bar close_time
- entry_time = entry bar open_time
- exit_time = exit bar open_time

## Feature Contract Summary

- model_feature_column_count: `24`
- audit_identity_column_count: `7`
- blocked_feature_family_count: `7`
- row_count_preserved: `true`
- years_covered: `[2020, 2021, 2022, 2023, 2024, 2025, 2026]`
- total_rows: `310`

## Feature Contract Table

| column | family | role | timestamp_basis | leakage_safe | required_source_columns | nullable_allowed | finite_required | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| signal_index | audit_identity | audit_identity | identity_only | true | signal_index | false | true | audit / row-identity only |
| entry_index | audit_identity | audit_identity | identity_only | true | entry_index | false | true | audit / row-identity only |
| exit_index | audit_identity | audit_identity | identity_only | true | exit_index | false | true | audit / row-identity only |
| signal_time | audit_identity | audit_identity | identity_only | true | signal_time | false | true | audit / row-identity only |
| entry_time | audit_identity | audit_identity | identity_only | true | entry_time | false | true | audit / row-identity only |
| exit_time | audit_identity | audit_identity | identity_only | true | exit_time | false | true | audit / row-identity only |
| signal_open | OHLCV context | model_feature | signal_bar_close | true | open | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_high | OHLCV context | model_feature | signal_bar_close | true | high | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_low | OHLCV context | model_feature | signal_bar_close | true | low | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_close | OHLCV context | model_feature | signal_bar_close | true | close | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_volume | OHLCV context | model_feature | signal_bar_close | true | volume | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_range | OHLCV context | model_feature | signal_bar_close | true | high, low | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_body | OHLCV context | model_feature | signal_bar_close | true | open, close | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_body_to_range | OHLCV context | model_feature | signal_bar_close | true | open, high, low, close | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_close_location_in_range | OHLCV context | model_feature | signal_bar_close | true | high, low, close | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_return_1_bar | OHLCV context | model_feature | past_bar_close | true | close | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_return_3_bar | OHLCV context | model_feature | past_bar_close | true | close | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_return_5_bar | OHLCV context | model_feature | past_bar_close | true | close | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| rolling_vol_20_past | OHLCV context | model_feature | rolling_past_only | true | volume | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| rolling_range_mean_20_past | OHLCV context | model_feature | rolling_past_only | true | high, low | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_zscore_20_past | OHLCV context | model_feature | rolling_past_only | true | volume | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| signal_volume_delta | volume_delta | model_feature | signal_bar_close | true | volume_delta | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_delta_abs | volume_delta | model_feature | signal_bar_close | true | volume_delta | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_delta_sign | volume_delta | model_feature | signal_bar_close | true | volume_delta | false | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_delta_rolling_sum_3_past | volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_delta_rolling_sum_5_past | volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| volume_delta_rolling_zscore_20_past | volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| cvd_proxy_at_signal | CVD/delta proxy from volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| cvd_proxy_slope_3_past | CVD/delta proxy from volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| cvd_proxy_slope_5_past | CVD/delta proxy from volume_delta | model_feature | rolling_past_only | true | volume_delta | true | true | leakage-safe by construction from the aligned signal bar or past-only windows |
| year | audit_identity | audit_identity | identity_only | true | year field in trade log or signal_time-derived audit year | false | true | audit / row-identity only |

## Yearly Coverage Summary

| year | trade_rows | feature_rows | row_count_preserved | model_feature_count | feature_null_issue_count | feature_nonfinite_issue_count |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 21 | True | 24 | 0 | 0 |
| 2021 | 82 | 82 | True | 24 | 0 | 0 |
| 2022 | 83 | 83 | True | 24 | 0 | 0 |
| 2023 | 73 | 73 | True | 24 | 0 | 0 |
| 2024 | 26 | 26 | True | 24 | 0 | 0 |
| 2025 | 16 | 16 | True | 24 | 0 | 0 |
| 2026 | 9 | 9 | True | 24 | 0 | 0 |

## Model Feature Null / Finite Audit

### Year 2020
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2021
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2022
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2023
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2024
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2025
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

### Year 2026
| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
| signal_high | 0.000 | 100.000 |
| signal_low | 0.000 | 100.000 |
| signal_close | 0.000 | 100.000 |
| signal_volume | 0.000 | 100.000 |
| signal_range | 0.000 | 100.000 |
| signal_body | 0.000 | 100.000 |
| signal_body_to_range | 0.000 | 100.000 |
| signal_close_location_in_range | 0.000 | 100.000 |
| signal_return_1_bar | 0.000 | 100.000 |
| signal_return_3_bar | 0.000 | 100.000 |
| signal_return_5_bar | 0.000 | 100.000 |
| rolling_vol_20_past | 0.000 | 100.000 |
| rolling_range_mean_20_past | 0.000 | 100.000 |
| volume_zscore_20_past | 0.000 | 100.000 |
| signal_volume_delta | 0.000 | 100.000 |
| volume_delta_abs | 0.000 | 100.000 |
| volume_delta_sign | 0.000 | 100.000 |
| volume_delta_rolling_sum_3_past | 0.000 | 100.000 |
| volume_delta_rolling_sum_5_past | 0.000 | 100.000 |
| volume_delta_rolling_zscore_20_past | 0.000 | 100.000 |
| cvd_proxy_at_signal | 0.000 | 100.000 |
| cvd_proxy_slope_3_past | 0.000 | 100.000 |
| cvd_proxy_slope_5_past | 0.000 | 100.000 |

## Feature Distribution Sanity Summary

### Year 2020
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 9900.000 | 26415.000 | 16752.060 | 4906.773 |
| signal_high | 9957.670 | 26449.430 | 16782.641 | 4921.214 |
| signal_low | 9827.800 | 26250.000 | 16616.888 | 4831.068 |
| signal_close | 9844.360 | 26310.000 | 16636.950 | 4841.999 |
| signal_volume | 752.521 | 859.267 | 765.365 | 24.025 |
| signal_range | 29.880 | 978.000 | 165.753 | 193.872 |
| signal_body | -721.450 | -14.560 | -115.110 | 146.217 |
| signal_body_to_range | -0.989 | -0.300 | -0.679 | 0.203 |
| signal_close_location_in_range | 0.000 | 0.572 | 0.137 | 0.162 |
| signal_return_1_bar | -0.032 | -0.001 | -0.006 | 0.006 |
| signal_return_3_bar | -0.056 | -0.003 | -0.012 | 0.011 |
| signal_return_5_bar | -0.056 | -0.005 | -0.018 | 0.011 |
| rolling_vol_20_past | 749.884 | 750.287 | 750.020 | 0.073 |
| rolling_range_mean_20_past | 37.373 | 258.864 | 111.342 | 58.006 |
| volume_zscore_20_past | 0.142 | 3.162 | 2.310 | 0.796 |
| signal_volume_delta | -447.258 | 89.294 | -199.312 | 167.143 |
| volume_delta_abs | 1.251 | 447.258 | 211.506 | 151.416 |
| volume_delta_sign | -1.000 | 1.000 | -0.810 | 0.587 |
| volume_delta_rolling_sum_3_past | -1335.724 | 143.642 | -506.403 | 378.891 |
| volume_delta_rolling_sum_5_past | -1884.126 | 263.182 | -675.799 | 472.086 |
| volume_delta_rolling_zscore_20_past | -3.297 | 0.798 | -1.227 | 1.209 |
| cvd_proxy_at_signal | -395708.346 | -207625.908 | -327687.332 | 60223.485 |
| cvd_proxy_slope_3_past | -445.241 | 47.881 | -168.801 | 126.297 |
| cvd_proxy_slope_5_past | -376.825 | 52.636 | -135.160 | 94.417 |

### Year 2021
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 29575.000 | 64732.720 | 42813.918 | 9354.332 |
| signal_high | 29811.070 | 64745.810 | 42902.513 | 9350.764 |
| signal_low | 29333.000 | 64062.820 | 42490.610 | 9279.698 |
| signal_close | 29439.340 | 64294.900 | 42547.751 | 9288.868 |
| signal_volume | 751.289 | 828.065 | 758.249 | 10.695 |
| signal_range | 180.750 | 1384.750 | 411.903 | 197.783 |
| signal_body | -751.790 | -59.070 | -266.166 | 162.177 |
| signal_body_to_range | -1.000 | -0.264 | -0.633 | 0.203 |
| signal_close_location_in_range | 0.000 | 0.736 | 0.157 | 0.176 |
| signal_return_1_bar | -0.016 | -0.001 | -0.006 | 0.003 |
| signal_return_3_bar | -0.059 | -0.004 | -0.016 | 0.009 |
| signal_return_5_bar | -0.075 | -0.005 | -0.021 | 0.011 |
| rolling_vol_20_past | 749.715 | 750.492 | 750.006 | 0.088 |
| rolling_range_mean_20_past | 207.921 | 1328.967 | 384.978 | 151.613 |
| volume_zscore_20_past | 0.096 | 3.234 | 2.317 | 0.850 |
| signal_volume_delta | -419.279 | 117.420 | -182.974 | 117.212 |
| volume_delta_abs | 4.767 | 419.279 | 188.206 | 108.613 |
| volume_delta_sign | -1.000 | 1.000 | -0.878 | 0.479 |
| volume_delta_rolling_sum_3_past | -1057.765 | 252.876 | -382.645 | 237.469 |
| volume_delta_rolling_sum_5_past | -1385.228 | 415.948 | -495.970 | 338.897 |
| volume_delta_rolling_zscore_20_past | -3.093 | 1.055 | -1.281 | 0.990 |
| cvd_proxy_at_signal | -797485.535 | -391440.301 | -586264.371 | 125804.817 |
| cvd_proxy_slope_3_past | -352.588 | 84.292 | -127.548 | 79.156 |
| cvd_proxy_slope_5_past | -277.046 | 83.190 | -99.194 | 67.779 |

### Year 2022
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 15750.000 | 46465.430 | 24054.455 | 8939.771 |
| signal_high | 15759.790 | 46509.900 | 24084.429 | 8957.424 |
| signal_low | 15656.220 | 46131.460 | 23944.102 | 8874.266 |
| signal_close | 15656.220 | 46171.390 | 23964.843 | 8889.302 |
| signal_volume | 751.306 | 791.778 | 757.072 | 7.979 |
| signal_range | 24.050 | 621.780 | 140.327 | 118.387 |
| signal_body | -441.250 | -7.660 | -89.611 | 82.407 |
| signal_body_to_range | -0.998 | -0.259 | -0.631 | 0.201 |
| signal_close_location_in_range | 0.000 | 0.669 | 0.172 | 0.169 |
| signal_return_1_bar | -0.019 | -0.000 | -0.004 | 0.003 |
| signal_return_3_bar | -0.044 | -0.001 | -0.009 | 0.007 |
| signal_return_5_bar | -0.032 | -0.002 | -0.011 | 0.007 |
| rolling_vol_20_past | 749.898 | 750.175 | 750.005 | 0.043 |
| rolling_range_mean_20_past | 20.795 | 421.296 | 123.468 | 106.413 |
| volume_zscore_20_past | 0.073 | 3.443 | 2.383 | 0.824 |
| signal_volume_delta | -527.515 | 260.063 | -133.806 | 128.604 |
| volume_delta_abs | 8.526 | 527.515 | 148.827 | 110.875 |
| volume_delta_sign | -1.000 | 1.000 | -0.759 | 0.651 |
| volume_delta_rolling_sum_3_past | -1282.721 | 558.756 | -285.487 | 300.717 |
| volume_delta_rolling_sum_5_past | -2277.646 | 617.188 | -354.822 | 412.586 |
| volume_delta_rolling_zscore_20_past | -3.239 | 2.136 | -1.032 | 1.014 |
| cvd_proxy_at_signal | -1113515.659 | -798991.774 | -982286.670 | 90329.821 |
| cvd_proxy_slope_3_past | -427.574 | 186.252 | -95.162 | 100.239 |
| cvd_proxy_slope_5_past | -455.529 | 123.438 | -70.964 | 82.517 |

### Year 2023
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 18016.300 | 43511.100 | 24878.676 | 4927.440 |
| signal_high | 18031.730 | 43543.710 | 24891.889 | 4930.852 |
| signal_low | 17964.720 | 43291.100 | 24781.982 | 4866.956 |
| signal_close | 17979.880 | 43340.770 | 24799.117 | 4879.806 |
| signal_volume | 750.694 | 778.399 | 754.748 | 6.395 |
| signal_range | 21.070 | 629.890 | 109.907 | 98.326 |
| signal_body | -571.750 | -9.660 | -79.559 | 87.828 |
| signal_body_to_range | -1.000 | -0.257 | -0.673 | 0.193 |
| signal_close_location_in_range | 0.000 | 0.690 | 0.158 | 0.144 |
| signal_return_1_bar | -0.013 | -0.000 | -0.003 | 0.003 |
| signal_return_3_bar | -0.021 | -0.001 | -0.006 | 0.004 |
| signal_return_5_bar | -0.022 | -0.001 | -0.007 | 0.005 |
| rolling_vol_20_past | 726.174 | 750.151 | 749.680 | 2.770 |
| rolling_range_mean_20_past | 17.392 | 222.331 | 70.125 | 45.734 |
| volume_zscore_20_past | 0.071 | 3.332 | 2.312 | 0.807 |
| signal_volume_delta | -424.961 | 167.275 | -133.360 | 106.942 |
| volume_delta_abs | 8.528 | 424.961 | 140.119 | 97.918 |
| volume_delta_sign | -1.000 | 1.000 | -0.918 | 0.397 |
| volume_delta_rolling_sum_3_past | -946.883 | 252.674 | -263.203 | 209.507 |
| volume_delta_rolling_sum_5_past | -967.345 | 189.260 | -315.733 | 238.637 |
| volume_delta_rolling_zscore_20_past | -3.996 | 2.529 | -1.249 | 1.126 |
| cvd_proxy_at_signal | -1428879.313 | -1143126.551 | -1207411.622 | 67618.632 |
| cvd_proxy_slope_3_past | -315.628 | 84.225 | -87.734 | 69.836 |
| cvd_proxy_slope_5_past | -193.469 | 37.852 | -63.147 | 47.727 |

### Year 2024
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 39000.000 | 96000.000 | 63986.348 | 12874.787 |
| signal_high | 39008.970 | 96000.300 | 64054.420 | 12873.470 |
| signal_low | 38916.000 | 95163.980 | 63566.679 | 12806.388 |
| signal_close | 38961.100 | 95194.530 | 63613.675 | 12811.233 |
| signal_volume | 751.322 | 865.984 | 757.745 | 21.740 |
| signal_range | 92.970 | 1126.430 | 487.740 | 213.414 |
| signal_body | -1006.190 | -38.900 | -372.673 | 210.577 |
| signal_body_to_range | -0.966 | -0.281 | -0.730 | 0.177 |
| signal_close_location_in_range | 0.000 | 0.485 | 0.117 | 0.140 |
| signal_return_1_bar | -0.016 | -0.001 | -0.006 | 0.003 |
| signal_return_3_bar | -0.026 | -0.004 | -0.011 | 0.006 |
| signal_return_5_bar | -0.032 | -0.002 | -0.013 | 0.006 |
| rolling_vol_20_past | 737.712 | 750.181 | 749.543 | 2.367 |
| rolling_range_mean_20_past | 199.858 | 672.723 | 429.499 | 123.455 |
| volume_zscore_20_past | 0.272 | 3.539 | 2.069 | 0.851 |
| signal_volume_delta | -364.559 | -27.262 | -196.350 | 87.666 |
| volume_delta_abs | 27.262 | 364.559 | 196.350 | 87.666 |
| volume_delta_sign | -1.000 | -1.000 | -1.000 | 0.000 |
| volume_delta_rolling_sum_3_past | -770.350 | 111.910 | -361.743 | 208.843 |
| volume_delta_rolling_sum_5_past | -1029.797 | 260.595 | -450.104 | 266.190 |
| volume_delta_rolling_zscore_20_past | -2.870 | 0.065 | -1.358 | 0.760 |
| cvd_proxy_at_signal | -1512733.977 | -1375865.518 | -1436712.843 | 40276.920 |
| cvd_proxy_slope_3_past | -256.783 | 37.303 | -120.581 | 69.614 |
| cvd_proxy_slope_5_past | -205.959 | 52.119 | -90.021 | 53.238 |

### Year 2025
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 79500.000 | 113503.990 | 96700.276 | 11330.854 |
| signal_high | 79680.000 | 113691.000 | 96849.607 | 11354.625 |
| signal_low | 79000.000 | 112720.000 | 96155.851 | 11329.076 |
| signal_close | 79000.000 | 112748.190 | 96219.668 | 11341.469 |
| signal_volume | 751.864 | 758.908 | 753.408 | 1.905 |
| signal_range | 429.490 | 971.000 | 693.757 | 170.298 |
| signal_body | -855.570 | -274.260 | -480.608 | 155.898 |
| signal_body_to_range | -0.958 | -0.402 | -0.703 | 0.164 |
| signal_close_location_in_range | 0.000 | 0.231 | 0.088 | 0.086 |
| signal_return_1_bar | -0.010 | -0.003 | -0.005 | 0.002 |
| signal_return_3_bar | -0.028 | -0.004 | -0.012 | 0.006 |
| signal_return_5_bar | -0.037 | -0.005 | -0.018 | 0.008 |
| rolling_vol_20_past | 749.994 | 750.066 | 750.014 | 0.022 |
| rolling_range_mean_20_past | 492.023 | 845.551 | 634.027 | 94.237 |
| volume_zscore_20_past | 0.528 | 3.174 | 2.353 | 0.725 |
| signal_volume_delta | -452.920 | -70.356 | -206.032 | 96.912 |
| volume_delta_abs | 70.356 | 452.920 | 206.032 | 96.912 |
| volume_delta_sign | -1.000 | -1.000 | -1.000 | 0.000 |
| volume_delta_rolling_sum_3_past | -1135.352 | -13.307 | -473.377 | 259.357 |
| volume_delta_rolling_sum_5_past | -1661.769 | -61.092 | -665.122 | 360.426 |
| volume_delta_rolling_zscore_20_past | -2.340 | 0.561 | -1.013 | 0.806 |
| cvd_proxy_at_signal | -1762021.530 | -1531896.434 | -1662298.750 | 70061.420 |
| cvd_proxy_slope_3_past | -378.451 | -4.436 | -157.792 | 86.452 |
| cvd_proxy_slope_5_past | -332.354 | -12.218 | -133.024 | 72.085 |

### Year 2026
| column | min | max | mean | std |
| --- | --- | --- | --- | --- |
| signal_open | 66452.740 | 91281.910 | 75368.991 | 8725.170 |
| signal_high | 66516.060 | 91441.350 | 75456.584 | 8753.901 |
| signal_low | 66103.990 | 90800.000 | 74958.067 | 8732.566 |
| signal_close | 66119.900 | 90800.000 | 75037.128 | 8769.141 |
| signal_volume | 751.955 | 760.363 | 754.221 | 2.543 |
| signal_range | 334.640 | 641.350 | 498.518 | 97.959 |
| signal_body | -524.520 | -99.770 | -331.863 | 154.126 |
| signal_body_to_range | -0.954 | -0.298 | -0.645 | 0.240 |
| signal_close_location_in_range | 0.000 | 0.509 | 0.182 | 0.205 |
| signal_return_1_bar | -0.008 | -0.001 | -0.005 | 0.002 |
| signal_return_3_bar | -0.015 | -0.003 | -0.008 | 0.003 |
| signal_return_5_bar | -0.021 | -0.008 | -0.013 | 0.005 |
| rolling_vol_20_past | 714.939 | 750.021 | 746.100 | 11.017 |
| rolling_range_mean_20_past | 425.071 | 620.712 | 512.886 | 62.696 |
| volume_zscore_20_past | 0.253 | 3.295 | 2.117 | 1.163 |
| signal_volume_delta | -263.719 | 85.614 | -122.986 | 106.714 |
| volume_delta_abs | 6.185 | 263.719 | 142.011 | 79.663 |
| volume_delta_sign | -1.000 | 1.000 | -0.778 | 0.629 |
| volume_delta_rolling_sum_3_past | -628.200 | 262.068 | -200.625 | 250.851 |
| volume_delta_rolling_sum_5_past | -896.332 | 394.444 | -236.740 | 379.556 |
| volume_delta_rolling_zscore_20_past | -1.575 | 0.333 | -0.856 | 0.629 |
| cvd_proxy_at_signal | -1819529.474 | -1768698.846 | -1800053.332 | 19946.042 |
| cvd_proxy_slope_3_past | -209.400 | 87.356 | -66.875 | 83.617 |
| cvd_proxy_slope_5_past | -179.266 | 78.889 | -47.348 | 75.911 |

## Schema Issues

- features_with_any_nulls: `{}`
- features_with_nonfinite_values: `{}`
- years_with_missing_features: `[]`
- years_with_row_count_mismatch: `[]`
- features_constant_by_year: `['2024: volume_delta_sign', '2025: volume_delta_sign']`
- simple_outlier_warnings: `[]`

## Leakage Audit

- outcome_columns_excluded_from_features: `true`
- future_bar_columns_excluded: `true`
- l2_features_excluded: `true`
- ofi_features_excluded: `true`
- no_entry_bar_close_used: `true`
- no_exit_bar_data_used: `true`
- no_predictive_metrics_computed: `true`
- no_model_training_performed: `true`

## Blocked Features

### Blocked by OFI/L2 approval
- OFI / MLOFI
- microprice / spread / depth
- spoofing / iceberg / L2 whale pressure

### Blocked by missing trade tape schema
- absorption proxy
- VPIN / toxicity
- footprint

### Blocked by missing historical source
- funding / OI / liquidation / basis

### Blocked by absent regime column
- regime

## Gate 2 Finding

- Gate 1 static inventory: pass
- Gate 1 schema availability: pass
- Gate 1 timestamp alignment: pass
- Gate 2 feature table dry run: pass
- Gate 2 feature contract/nullness audit: `pass`

## Recommended Next Step

Prepare a Gate 3 pre-registration document for a future meta-label experiment, specifying splits, labels, metrics, leakage rules, and forbidden tuning, but do not train a model yet.

## What Is Safe

- feature contract reporting
- yearly nullness audit
- leakage audit
- bounded read-only diagnostics
- Gate 3 pre-registration planning

## What Is Not Safe

- alpha claims
- strategy optimization
- model training
- predictive metrics
- feature/PnL correlations
- backtesting as part of this task
- full reconstruction
- OFI artifact generation
- paper/live trading
- using unapproved L2 features

## Decision

- `c_exhaustion_feature_table_contract_audit_created`
- `gate_2_feature_contract_audit_completed_or_partial`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_market_data_artifacts_written`
- `no_strategy_backtest_run`
- `no_model_trained`
- `no_predictive_metrics_computed`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_2_feature_contract_audit_pass`
