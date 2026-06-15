# 750 BTC Raw Rebuild Parity Audit

## Purpose

This targeted audit checks whether high-risk existing 750 BTC bar outputs rebuild to the same OHLCV and signed-flow values from available raw aggTrades using the hardened builder.
This targeted audit does not prove all historical bars are perfect. It only tests whether high-risk existing bars match a hardened rebuild for available raw archives.

## Data Sources

- Existing bar directory: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- Raw aggTrades directory: `/mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21`
- Existing 750 BTC parquet outputs only; no regeneration was written back to the bar directory

## Method

The selected existing files were rebuilt in memory from their matching raw aggTrades ZIP archives using `build_features_lazy(..., volume_bucket_size=750.0)` and compared row-by-row against the existing parquet outputs.
Exact rebuild parity was evaluated with strict tolerances for price, volume, VWAP, and signed flow, and files missing raw archives were recorded separately as inconclusive.

## Selected Files

Selection includes all suspicious files from the existing audit plus the top 10 files by absolute `volume_delta_sum / volume_sum` and the top 10 by `volume_delta_abs_over_volume_ratio`, deduplicated.

| file_name | suspicious_flag_count | suspicious_reasons | volume_delta_abs_over_volume_ratio | volume_delta_positive_rate | volume_delta_negative_rate |
| --- | --- | --- | --- | --- | --- |
| BTCUSDT_tier2_750btc_2021-02.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.005099 | 0.467540 | 0.532460 |
| BTCUSDT_tier2_750btc_2021-05.parquet | 1 | volume_max > 1000 | 0.031991 | 0.389396 | 0.610604 |
| BTCUSDT_tier2_750btc_2021-07.parquet | 2 | volume_delta_abs_over_volume_ratio < 0.01, volume_max > 1000 | 0.009802 | 0.452782 | 0.547218 |
| BTCUSDT_tier2_750btc_2021-08.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.000595 | 0.489684 | 0.510316 |
| BTCUSDT_tier2_750btc_2021-10.parquet | 2 | volume_delta_abs_over_volume_ratio < 0.01, volume_max > 1000 | 0.000519 | 0.488027 | 0.511973 |
| BTCUSDT_tier2_750btc_2022-02.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.007417 | 0.481459 | 0.518541 |
| BTCUSDT_tier2_750btc_2022-06.parquet | 1 | volume_max > 1000 | 0.020822 | 0.451132 | 0.548868 |
| BTCUSDT_tier2_750btc_2022-07.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.000990 | 0.503236 | 0.496764 |
| BTCUSDT_tier2_750btc_2022-08.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.002434 | 0.495652 | 0.504348 |
| BTCUSDT_tier2_750btc_2022-09.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.001238 | 0.496532 | 0.503468 |
| BTCUSDT_tier2_750btc_2022-10.parquet | 2 | volume_delta_abs_over_volume_ratio < 0.01, volume_max > 1000 | 0.001668 | 0.493049 | 0.506951 |
| BTCUSDT_tier2_750btc_2022-11.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.006354 | 0.476296 | 0.523704 |
| BTCUSDT_tier2_750btc_2022-12.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.007181 | 0.458974 | 0.541026 |
| BTCUSDT_tier2_750btc_2023-01.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.004575 | 0.469869 | 0.530131 |
| BTCUSDT_tier2_750btc_2023-02.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.003097 | 0.482037 | 0.517963 |
| BTCUSDT_tier2_750btc_2023-03.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.001134 | 0.504926 | 0.495074 |
| BTCUSDT_tier2_750btc_2023-04.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.001370 | 0.492393 | 0.507607 |
| BTCUSDT_tier2_750btc_2024-01.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.007865 | 0.524038 | 0.475962 |
| BTCUSDT_tier2_750btc_2024-03.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.006177 | 0.507909 | 0.492091 |
| BTCUSDT_tier2_750btc_2024-10.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.009358 | 0.462834 | 0.537166 |
| BTCUSDT_tier2_750btc_2024-11.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.001885 | 0.473214 | 0.526786 |
| BTCUSDT_tier2_750btc_2025-04.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.009165 | 0.472144 | 0.527856 |
| BTCUSDT_tier2_750btc_2026-03.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.009732 | 0.475027 | 0.524973 |
| BTCUSDT_tier2_750btc_2026-05-20.parquet | 1 | volume_delta_abs_over_volume_ratio < 0.01 | 0.007431 | 0.500000 | 0.500000 |
| BTCUSDT_tier2_750btc_2026-05-14.parquet | 0 |  | 0.089850 | 0.592593 | 0.407407 |
| BTCUSDT_tier2_750btc_2020-05-24.parquet | 0 |  | 0.089330 | 0.372340 | 0.627660 |
| BTCUSDT_tier2_750btc_2026-05-12.parquet | 0 |  | 0.077009 | 0.352941 | 0.647059 |
| BTCUSDT_tier2_750btc_2026-05-17.parquet | 0 |  | 0.076630 | 0.500000 | 0.500000 |
| BTCUSDT_tier2_750btc_2026-05-02.parquet | 0 |  | 0.072055 | 0.666667 | 0.333333 |
| BTCUSDT_tier2_750btc_2026-05-09.parquet | 0 |  | 0.068495 | 0.727273 | 0.272727 |
| BTCUSDT_tier2_750btc_2026-05-03.parquet | 0 |  | 0.066789 | 0.300000 | 0.700000 |
| BTCUSDT_tier2_750btc_2020-05-29.parquet | 0 |  | 0.065115 | 0.363636 | 0.636364 |
| BTCUSDT_tier2_750btc_2026-05-10.parquet | 0 |  | 0.062943 | 0.705882 | 0.294118 |
| BTCUSDT_tier2_750btc_2026-05-06.parquet | 0 |  | 0.061419 | 0.576923 | 0.423077 |

## Aggregate Findings

| file_count | total_rows | global_min_open_time | global_max_close_time | total_volume | total_volume_delta | global_volume_delta_positive_rate | global_volume_delta_negative_rate | global_volume_delta_zero_rate | global_volume_delta_abs_over_volume_ratio | suspicious_file_count | suspicious_file_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 102 | 204124 | 1590105600125 | 1779407999849615 | 153051117.444677 | -1814671.366651 | 0.457888 | 0.542112 | 0.000000 | 0.011857 | 24 | 0.235294 |

## Per-File Parity Results

| file_name | raw_archive | raw_archive_found | old_row_count | rebuilt_row_count | row_count_delta | old_min_open_time | rebuilt_min_open_time | old_max_close_time | rebuilt_max_close_time | common_comparable_rows | open_time_match_rate | close_time_match_rate | open_match_rate | high_match_rate | low_match_rate | close_match_rate | volume_match_rate | vwap_match_rate | trade_count_match_rate | volume_delta_exact_match_rate | volume_delta_sign_match_rate | volume_delta_correlation | volume_delta_mean_abs_diff | volume_delta_median_abs_diff | volume_delta_max_abs_diff | old_volume_delta_sum | rebuilt_volume_delta_sum | old_volume_delta_abs_over_volume_ratio | rebuilt_volume_delta_abs_over_volume_ratio | old_positive_rate | rebuilt_positive_rate | old_negative_rate | rebuilt_negative_rate | parity_flag_count | parity_class | parity_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BTCUSDT_tier2_750btc_2021-02.parquet | BTCUSDT-aggTrades-2021-02.zip | 1 | 3358 | 3358 | 0 | 1612137600018 | 1612137600018 | 1614556799971 | 1614556799971 | 3358 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -12841.159711 | -12841.159711 | 0.005099 | 0.005099 | 0.467540 | 0.467540 | 0.532460 | 0.532460 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2021-05.parquet | BTCUSDT-aggTrades-2021-05.zip | 1 | 4715 | 4715 | 0 | 1619827200133 | 1619827200133 | 1622505599978 | 1622505599978 | 4715 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -113128.678599 | -113128.678599 | 0.031991 | 0.031991 | 0.389396 | 0.389396 | 0.610604 | 0.610604 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2021-07.parquet | BTCUSDT-aggTrades-2021-07.zip | 1 | 2372 | 2372 | 0 | 1625097600041 | 1625097600041 | 1627775999971 | 1627775999971 | 2372 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -17432.501709 | -17432.501709 | 0.009802 | 0.009802 | 0.452782 | 0.452782 | 0.547218 | 0.547218 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2021-08.parquet | BTCUSDT-aggTrades-2021-08.zip | 1 | 2181 | 2181 | 0 | 1627776000011 | 1627776000011 | 1630454399980 | 1630454399980 | 2181 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -973.297877 | -973.297877 | 0.000595 | 0.000595 | 0.489684 | 0.489684 | 0.510316 | 0.510316 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2021-10.parquet | BTCUSDT-aggTrades-2021-10.zip | 1 | 2088 | 2088 | 0 | 1633046400199 | 1633046400199 | 1635724799994 | 1635724799994 | 2088 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -812.140167 | -812.140167 | 0.000519 | 0.000519 | 0.488027 | 0.488027 | 0.511973 | 0.511973 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-02.parquet | BTCUSDT-aggTrades-2022-02.zip | 1 | 1672 | 1672 | 0 | 1643673600000 | 1643673600000 | 1646092799999 | 1646092799999 | 1672 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -9297.361180 | -9297.361180 | 0.007417 | 0.007417 | 0.481459 | 0.481459 | 0.518541 | 0.518541 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-06.parquet | BTCUSDT-aggTrades-2022-06.zip | 1 | 3755 | 3755 | 0 | 1654041600002 | 1654041600002 | 1656633599998 | 1656633599998 | 3755 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -58636.651600 | -58636.651600 | 0.020822 | 0.020822 | 0.451132 | 0.451132 | 0.548868 | 0.548868 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-07.parquet | BTCUSDT-aggTrades-2022-07.zip | 1 | 6645 | 6645 | 0 | 1656633600003 | 1656633600003 | 1659311999999 | 1659311999999 | 6645 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 4932.985680 | 4932.985680 | 0.000990 | 0.000990 | 0.503236 | 0.503236 | 0.496764 | 0.496764 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-08.parquet | BTCUSDT-aggTrades-2022-08.zip | 1 | 7590 | 7590 | 0 | 1659312000000 | 1659312000000 | 1661990399999 | 1661990399999 | 7590 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -13854.091710 | -13854.091710 | 0.002434 | 0.002434 | 0.495652 | 0.495652 | 0.504348 | 0.504348 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-09.parquet | BTCUSDT-aggTrades-2022-09.zip | 1 | 13119 | 13119 | 0 | 1661990400000 | 1661990400000 | 1664582399998 | 1664582399998 | 13119 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -12177.080990 | -12177.080990 | 0.001238 | 0.001238 | 0.496532 | 0.496532 | 0.503468 | 0.503468 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-10.parquet | BTCUSDT-aggTrades-2022-10.zip | 1 | 9999 | 9999 | 0 | 1664582400000 | 1664582400000 | 1667260799994 | 1667260799994 | 9999 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -12507.129940 | -12507.129940 | 0.001668 | 0.001668 | 0.493049 | 0.493049 | 0.506951 | 0.506951 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-11.parquet | BTCUSDT-aggTrades-2022-11.zip | 1 | 12171 | 12171 | 0 | 1667260800000 | 1667260800000 | 1669852799999 | 1669852799999 | 12171 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -57998.912923 | -57998.912923 | 0.006354 | 0.006354 | 0.476296 | 0.476296 | 0.523704 | 0.523704 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2022-12.parquet | BTCUSDT-aggTrades-2022-12.zip | 1 | 7739 | 7739 | 0 | 1669852800000 | 1669852800000 | 1672531199999 | 1672531199999 | 7739 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -41675.379750 | -41675.379750 | 0.007181 | 0.007181 | 0.458974 | 0.458974 | 0.541026 | 0.541026 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2023-01.parquet | BTCUSDT-aggTrades-2023-01.zip | 1 | 10637 | 10637 | 0 | 1672531200001 | 1672531200001 | 1675209599999 | 1675209599999 | 10637 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -36498.408930 | -36498.408930 | 0.004575 | 0.004575 | 0.469869 | 0.469869 | 0.530131 | 0.530131 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2023-02.parquet | BTCUSDT-aggTrades-2023-02.zip | 1 | 11524 | 11524 | 0 | 1675209600000 | 1675209600000 | 1677628799999 | 1677628799999 | 11524 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -26770.681050 | -26770.681050 | 0.003097 | 0.003097 | 0.482037 | 0.482037 | 0.517963 | 0.517963 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2023-03.parquet | BTCUSDT-aggTrades-2023-03.zip | 1 | 12689 | 12689 | 0 | 1677628800000 | 1677628800000 | 1680307199999 | 1680307199999 | 12689 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 10792.144860 | 10792.144860 | 0.001134 | 0.001134 | 0.504926 | 0.504926 | 0.495074 | 0.495074 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2023-04.parquet | BTCUSDT-aggTrades-2023-04.zip | 1 | 2169 | 2169 | 0 | 1680307200003 | 1680307200003 | 1682899199998 | 1682899199998 | 2169 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 2228.532640 | 2228.532640 | 0.001370 | 0.001370 | 0.492393 | 0.492393 | 0.507607 | 0.507607 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2024-01.parquet | BTCUSDT-aggTrades-2024-01.zip | 1 | 1872 | 1872 | 0 | 1704067200000 | 1704067200000 | 1706745599998 | 1706745599998 | 1872 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 11037.900500 | 11037.900500 | 0.007865 | 0.007865 | 0.524038 | 0.524038 | 0.475962 | 0.475962 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2024-03.parquet | BTCUSDT-aggTrades-2024-03.zip | 1 | 2276 | 2276 | 0 | 1709251200000 | 1709251200000 | 1711929599999 | 1711929599999 | 2276 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 10542.828430 | 10542.828430 | 0.006177 | 0.006177 | 0.507909 | 0.507909 | 0.492091 | 0.492091 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2024-10.parquet | BTCUSDT-aggTrades-2024-10.zip | 1 | 1009 | 1009 | 0 | 1727740800020 | 1727740800020 | 1730419199787 | 1730419199787 | 1009 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -7074.876150 | -7074.876150 | 0.009358 | 0.009358 | 0.462834 | 0.462834 | 0.537166 | 0.537166 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2024-11.parquet | BTCUSDT-aggTrades-2024-11.zip | 1 | 1792 | 1792 | 0 | 1730419200187 | 1730419200187 | 1733011199987 | 1733011199987 | 1792 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 2533.105504 | 2533.105504 | 0.001885 | 0.001885 | 0.473214 | 0.473214 | 0.526786 | 0.526786 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2025-04.parquet | BTCUSDT-aggTrades-2025-04.zip | 1 | 1059 | 1059 | 0 | 1743465600003164 | 1743465600003164 | 1746057599161596 | 1746057599161596 | 1059 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -7273.505450 | -7273.505450 | 0.009165 | 0.009165 | 0.472144 | 0.472144 | 0.527856 | 0.527856 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-03.parquet | BTCUSDT-aggTrades-2026-03.zip | 1 | 941 | 941 | 0 | 1772323200005709 | 1772323200005709 | 1775001599618442 | 1775001599618442 | 941 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -6867.513240 | -6867.513240 | 0.009732 | 0.009732 | 0.475027 | 0.475027 | 0.524973 | 0.524973 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-20.parquet | BTCUSDT-aggTrades-2026-05-20.zip | 1 | 16 | 16 | 0 | 1779235200183703 | 1779235200183703 | 1779321599640499 | 1779321599640499 | 16 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -83.938230 | -83.938230 | 0.007431 | 0.007431 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-14.parquet | BTCUSDT-aggTrades-2026-05-14.zip | 1 | 27 | 27 | 0 | 1778716800112799 | 1778716800112799 | 1778803199853148 | 1778803199853148 | 27 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 1772.547430 | 1772.547430 | 0.089850 | 0.089850 | 0.592593 | 0.592593 | 0.407407 | 0.407407 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2020-05-24.parquet | BTCUSDT-aggTrades-2020-05-24.zip | 1 | 94 | 94 | 0 | 1590278400059 | 1590278400059 | 1590364799975 | 1590364799975 | 94 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -6287.043562 | -6287.043562 | 0.089330 | 0.089330 | 0.372340 | 0.372340 | 0.627660 | 0.627660 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-12.parquet | BTCUSDT-aggTrades-2026-05-12.zip | 1 | 17 | 17 | 0 | 1778544000122511 | 1778544000122511 | 1778630399977309 | 1778630399977309 | 17 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -953.849060 | -953.849060 | 0.077009 | 0.077009 | 0.352941 | 0.352941 | 0.647059 | 0.647059 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-17.parquet | BTCUSDT-aggTrades-2026-05-17.zip | 1 | 12 | 12 | 0 | 1778976000181551 | 1778976000181551 | 1779062399758039 | 1779062399758039 | 12 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -646.966800 | -646.966800 | 0.076630 | 0.076630 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-02.parquet | BTCUSDT-aggTrades-2026-05-02.zip | 1 | 9 | 9 | 0 | 1777680000096399 | 1777680000096399 | 1777766398440237 | 1777766398440237 | 9 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 443.202740 | 443.202740 | 0.072055 | 0.072055 | 0.666667 | 0.666667 | 0.333333 | 0.333333 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-09.parquet | BTCUSDT-aggTrades-2026-05-09.zip | 1 | 11 | 11 | 0 | 1778284800040998 | 1778284800040998 | 1778371199658719 | 1778371199658719 | 11 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 517.029550 | 517.029550 | 0.068495 | 0.068495 | 0.727273 | 0.727273 | 0.272727 | 0.272727 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-03.parquet | BTCUSDT-aggTrades-2026-05-03.zip | 1 | 10 | 10 | 0 | 1777766400117041 | 1777766400117041 | 1777852799991798 | 1777852799991798 | 10 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -495.964660 | -495.964660 | 0.066789 | 0.066789 | 0.300000 | 0.300000 | 0.700000 | 0.700000 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2020-05-29.parquet | BTCUSDT-aggTrades-2020-05-29.zip | 1 | 77 | 77 | 0 | 1590710400158 | 1590710400158 | 1590796799973 | 1590796799973 | 77 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -3735.937173 | -3735.937173 | 0.065115 | 0.065115 | 0.363636 | 0.363636 | 0.636364 | 0.636364 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-10.parquet | BTCUSDT-aggTrades-2026-05-10.zip | 1 | 17 | 17 | 0 | 1778371200125821 | 1778371200125821 | 1778457599594603 | 1778457599594603 | 17 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 757.474380 | 757.474380 | 0.062943 | 0.062943 | 0.705882 | 0.705882 | 0.294118 | 0.294118 | 0 | parity_ok |  |
| BTCUSDT_tier2_750btc_2026-05-06.parquet | BTCUSDT-aggTrades-2026-05-06.zip | 1 | 26 | 26 | 0 | 1778025600076850 | 1778025600076850 | 1778111998251555 | 1778111998251555 | 26 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 1154.602140 | 1154.602140 | 0.061419 | 0.061419 | 0.576923 | 0.576923 | 0.423077 | 0.423077 | 0 | parity_ok |  |

## Signed-Flow Parity

- `parity_ok`: 34 files
- `signed_flow_mismatch`: 0 files
- `inconclusive_missing_raw`: 0 files

## OHLCV Parity

OHLCV parity is treated as the primary structural check. If OHLCV matches but signed flow diverges, that is strong evidence that the old `is_buyer_maker` handling affected `volume_delta` while leaving the candle shape intact.

## Missing Raw Archives

No selected file was missing a matching raw archive.

## Interpretation

1. Files that rebuild cleanly for OHLCV and signed flow are consistent with the hardened builder path for the sampled archives.
2. If rebuilt `volume_delta` deviates materially while OHLCV stays aligned, that is evidence the old `is_buyer_maker` parsing risk affected signed flow in the existing bars.
3. Missing raw archives keep the audit inconclusive for those files; the audit cannot claim full-historical proof from a partial sample.
4. The existing C anchor can remain a research baseline for research work because the sampled high-risk files showed parity.
5. The existing C anchor should not be treated as production evidence from this audit alone.

## Decision

Decision: parity_ok_for_sample. Regeneration status: full_regeneration_not_yet_required. This targeted audit does not prove all historical bars are perfect. It only tests whether high-risk existing bars match a hardened rebuild for available raw archives.

## Required Next Step

Run the same read-only parity check on any additional high-risk files if more raw archives become available, then decide whether a broader historical regeneration is warranted.
