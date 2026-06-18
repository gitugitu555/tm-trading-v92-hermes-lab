# V9.2 C_Exhaustion Signal-Time Feature Table Dry Run

## Purpose

Construct a leakage-safe C_Exhaustion signal-time feature table in memory using only the aligned replay output and approved existing bar schema.

## Inputs

- trade_log path: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar_dir path: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- max_trades: `5000`
- max_bar_files: `120`
- max_bars: `250000`
- preview_rows: `5`
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
- No alpha claim is made.
- Full reconstruction remains blocked.

## Alignment Convention Used

- signal_time = signal bar close_time
- entry_time = entry bar open_time
- exit_time = exit bar open_time

## Feature Table Dry-Run Summary

- trade_rows_loaded: `310`
- feature_rows_constructed: `310`
- row_count_preserved: `true`
- signal_index_missing_count: `0`
- signal_bar_missing_count: `0`
- feature_column_count: `30`
- model_feature_column_count: `24`
- audit_identity_column_count: `6`
- regime_present: `false`
- regime_features_materialized: `false`
- signal_time_matches_signal_bar_close_pct: `100.000`
- entry_time_matches_entry_bar_open_pct: `100.000`
- exit_time_matches_exit_bar_open_pct: `100.000`

## Feature Families Included

- OHLCV context
- volume_delta
- CVD/delta proxy from volume_delta
- regime if present, otherwise not materialized

## Feature Families Excluded

- absorption proxy
- VPIN / toxicity
- footprint
- OFI / MLOFI
- microprice / spread / depth
- spoofing / iceberg / L2 whale pressure
- funding / OI / liquidation / basis

## Feature Eligibility Table

| column | family | model_feature? | timestamp_basis | leakage_safe? | notes |
| --- | --- | --- | --- | --- | --- |
| signal_index | identity/audit | no | identity_only | yes | identity/audit only |
| entry_index | identity/audit | no | identity_only | yes | identity/audit only |
| exit_index | identity/audit | no | identity_only | yes | identity/audit only |
| signal_time | identity/audit | no | identity_only | yes | identity/audit only |
| entry_time | identity/audit | no | identity_only | yes | identity/audit only |
| exit_time | identity/audit | no | identity_only | yes | identity/audit only |
| signal_open | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_high | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_low | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_close | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_volume | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_range | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_body | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_body_to_range | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_close_location_in_range | OHLCV context | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| signal_return_1_bar | OHLCV context | yes | past_bar_close | yes | signal-close-safe or past-only construction |
| signal_return_3_bar | OHLCV context | yes | past_bar_close | yes | signal-close-safe or past-only construction |
| signal_return_5_bar | OHLCV context | yes | past_bar_close | yes | signal-close-safe or past-only construction |
| rolling_vol_20_past | OHLCV context | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| rolling_range_mean_20_past | OHLCV context | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| volume_zscore_20_past | OHLCV context | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| signal_volume_delta | volume_delta | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| volume_delta_abs | volume_delta | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| volume_delta_sign | volume_delta | yes | signal_bar_close | yes | signal-close-safe or past-only construction |
| volume_delta_rolling_sum_3_past | volume_delta | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| volume_delta_rolling_sum_5_past | volume_delta | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| volume_delta_rolling_zscore_20_past | volume_delta | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| cvd_proxy_at_signal | CVD/delta proxy | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| cvd_proxy_slope_3_past | CVD/delta proxy | yes | rolling_past_only | yes | signal-close-safe or past-only construction |
| cvd_proxy_slope_5_past | CVD/delta proxy | yes | rolling_past_only | yes | signal-close-safe or past-only construction |

## Preview Rows

| signal_index | signal_time | signal_open | signal_close | signal_volume | signal_volume_delta | cvd_proxy_at_signal | signal_return_1_bar | rolling_vol_20_past |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7495 | 2020-09-02 11:09:58.270000 | 11490.000 | 11425.980 | 753.302 | -289.771 | -207625.908 | -0.006 | 750.017 |
| 7614 | 2020-09-03 12:12:13.881000 | 11000.000 | 10936.360 | 807.467 | -409.881 | -216414.293 | -0.006 | 750.026 |
| 7938 | 2020-09-05 18:54:55.943000 | 9900.000 | 9844.360 | 753.092 | -413.402 | -236256.910 | -0.006 | 750.108 |
| 8823 | 2020-09-17 10:27:26.646000 | 10830.950 | 10816.390 | 754.893 | -198.731 | -258847.211 | -0.001 | 750.001 |
| 9243 | 2020-09-23 20:48:29.709000 | 10231.500 | 10210.570 | 756.617 | -139.611 | -265388.097 | -0.002 | 750.018 |

## Null / Finite Summary

| column | null_pct | finite_pct |
| --- | --- | --- |
| signal_open | 0.000 | 100.000 |
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

## Leakage Audit

- outcome_columns_excluded_from_features: `true`
- future_bar_columns_excluded: `true`
- l2_features_excluded: `true`
- ofi_features_excluded: `true`
- no_entry_bar_close_used: `true`
- no_exit_bar_data_used: `true`

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

### Blocked by absent regime column if applicable
- regime

## Gate 2 Finding

- Gate 1 static inventory: pass
- Gate 1 schema availability: pass
- Gate 1 timestamp alignment: pass
- Gate 2 feature table dry run: `pass`

## Recommended Next Step

Run a bounded read-only feature-table schema and nullness audit over a slightly larger sample or the full replay trade log, still with no model training and no output artifacts.

## What Is Safe

- feature-table dry-run reporting
- leakage audit
- nullness audit
- bounded read-only diagnostics

## What Is Not Safe

- alpha claims
- strategy optimization
- model training
- predictive metrics
- backtesting as part of this task
- full reconstruction
- OFI artifact generation
- paper/live trading
- using unapproved L2 features

## Decision

- `c_exhaustion_signal_time_feature_table_dry_run_created`
- `gate_2_feature_table_dry_run_completed_or_partial`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_feature_table_artifacts_written`
- `no_market_data_artifacts_written`
- `no_strategy_backtest_run`
- `no_model_trained`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_2_feature_table_dry_run_pass`
