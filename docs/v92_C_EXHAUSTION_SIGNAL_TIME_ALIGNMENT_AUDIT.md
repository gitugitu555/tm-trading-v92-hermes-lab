# V9.2 C_Exhaustion Signal-Time Alignment Audit

## Purpose

Resolve the mixed timestamp basis between the C_Exhaustion replay output and the bounded 750btc bar frame before any Gate 2 feature table dry run.

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
- No market-data artifacts were written.
- No strategy backtest was run.
- No alpha claim is made.
- Full reconstruction remains blocked.

## Trade-Log Time Range

- min_signal_time: `2020-09-02 11:09:58.270000`
- max_signal_time: `2026-05-07 14:07:47.113084`
- min_entry_time: `2020-09-02 11:09:58.270000`
- max_entry_time: `2026-05-07 14:07:47.113084`
- min_exit_time: `2020-09-02 14:59:44.128000`
- max_exit_time: `2026-05-09 07:27:02.915893`

## Bar Shards Inspected

- `BTCUSDT_tier2_750btc_2020-05-22.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-23.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-24.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-25.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-26.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-27.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-28.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-29.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-30.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-05-31.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2020-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2021-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2022-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2023-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2024-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-09.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-10.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-11.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2025-12.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-01.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-02.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-03.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-04.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-05.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-06.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-07.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-08.parquet`: prefix anchor for absolute index mapping
- `BTCUSDT_tier2_750btc_2026-05-09.parquet`: overlaps trade-log range

## Bar Time Range

- min_open_time: `2020-05-22 00:00:00.125000`
- max_close_time: `2026-05-09 23:59:59.658719`

## Index Alignment Checks

- signal_index_in_range_pct: `100.00`
- entry_index_in_range_pct: `100.00`
- exit_index_in_range_pct: `100.00`
- signal_lte_entry_lte_exit_index_pct: `100.00`
- holding_bars_consistency_pct: `100.00`

## Timestamp Basis Checks

- signal_time_matches_signal_bar_open_pct: `0.00`
- signal_time_matches_signal_bar_close_pct: `100.00`
- entry_time_matches_entry_bar_open_pct: `100.00`
- entry_time_matches_entry_bar_close_pct: `0.00`
- exit_time_matches_exit_bar_open_pct: `100.00`
- exit_time_matches_exit_bar_close_pct: `0.00`

## Inferred Timestamp Convention

- convention: `mixed`
- confidence_pct: `100.00`
- exact field-level note: the replay output should be interpreted only through the matched open/close basis, not as a timing claim about future bars.

## Volume Delta Availability

- volume_delta column present: `true`
- volume_delta non-null pct: `100.00`
- volume_delta finite pct: `100.00`
- volume_delta usable for future Gate 2 schema-only feature table: `true`

## Feature Eligibility After Alignment Audit

| feature family | schema available? | alignment-safe? | eligible for Gate 2 dry run? | blocker | notes |
| --- | --- | --- | --- | --- | --- |
| OHLCV context | true | yes | yes | none | uses deterministic bar ordering and past-only bars |
| regime | false | yes | yes | missing stored regime column; may be derived in memory from OHLCV using canonical classifier | only if materialized from existing OHLCV and shifted safely |
| volume_delta | true | yes | yes | none | present in overlapping bar schema when selected files include it |
| CVD / delta proxy from volume_delta | true | yes | yes | none | derived from existing bar schema; no predictive claim |
| absorption proxy | false | no | no | missing raw signed-trade schema columns | requires trade tape fields not present in the replay output or bar schema |
| VPIN / toxicity | false | no | no | missing raw signed-trade bucket columns | requires signed-flow buckets not present here |
| footprint | false | no | no | missing raw trade tape columns | price-level aggregation requires trade tape that is not in scope |
| OFI / MLOFI | false | no | no | blocked by unapproved L2 / OFI artifacts | cannot use until reconstruction and artifact approval exist |
| microprice / spread / depth | false | no | no | blocked by unapproved L2 / OFI artifacts | requires book-state inputs that remain infrastructure-only |
| spoofing / iceberg / L2 whale pressure | false | no | no | blocked by unapproved L2 / OFI artifacts and missing event history | requires event-level L2 coverage that is not approved |
| funding / OI / liquidation / basis | false | no | no | missing verified historical source | not present in the inspected trade log or bar schema |

## Gate 1 Finding

- Gate 1 static inventory: pass
- Gate 1 schema availability: pass
- Gate 1 timestamp alignment: `pass`
- Gate 2 feature table dry run: not started

## Recommended Next Step

Run a bounded read-only Gate 2 feature table dry run using only OHLCV/regime/volume_delta features on a tiny sample, writing only a Markdown report and no data artifacts.

## What Is Safe

- timestamp alignment audit
- schema-only audit
- leakage audit
- bounded read-only feature availability diagnostics

## What Is Not Safe

- alpha claims
- strategy optimization
- backtesting as part of this task
- full reconstruction
- OFI artifact generation
- paper/live trading
- using unapproved L2 features

## Decision

- `c_exhaustion_signal_time_alignment_audit_created`
- `gate_1_alignment_audit_completed`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_market_data_artifacts_written`
- `no_strategy_backtest_run`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_1_alignment_pass`
