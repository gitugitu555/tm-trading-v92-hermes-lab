# V9.2 C_Exhaustion Signal-Time Schema Audit

## Purpose

Verify which C_Exhaustion signal-time and bar schema columns are actually present in local replay outputs and 750btc bars, without joining new OFI artifacts or running any strategy evaluation.

## Inputs

- audit_mode: `static + optional schema audit`
- explicit_bar_file: `null`
- explicit_trade_log: `null`
- discovered_bar_file: `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet`
- discovered_trade_log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- max_rows: `5000`

## Read-Only Guardrails

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No market-data artifacts were written.
- No strategy backtest was run.
- No alpha claim is made.
- Full reconstruction remains blocked.

## Candidate Files

- Discovered trade-log file: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Discovered bar file: `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet`
- Inspected trade-log file: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- Inspected bar file: `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet`

## Current Signal-Time Columns / Inputs

- present columns: `signal_time, entry_time, exit_time, signal_index, entry_index, exit_index, open_time, close_time, open, high, low, close, volume, volume_delta`
- required signal-time columns present: `signal_time=true, entry_time=true, exit_time=true, signal_index=true, entry_index=true, exit_index=true`
- required bar columns present: `open_time=true, close_time=true, open=true, high=true, low=true, close=true, volume=true`

## Replay / Trade-Log Schema

- file inspected: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- row sample count: `310`
- columns: `signal_index, entry_index, exit_index, signal_time, entry_time, exit_time, entry_price, exit_price, gross_return_bps, net_return_bps, holding_bars, year`
- required column presence: `signal_time=true, entry_time=true, exit_time=true, signal_index=true, entry_index=true, exit_index=true`
- missing required columns: `none`
- optional signal-time columns present: `entry_price, exit_price`
- parseable_timestamp_signal_time: `True`
- parseable_timestamp_entry_time: `True`
- parseable_timestamp_exit_time: `True`
- signal_time_lte_entry_time: `True`
- entry_time_lte_exit_time: `True`

## Bar Schema

- file inspected: `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet`
- row sample count: `79`
- columns: `bar_id, open_time, close_time, open, high, low, close, volume, volume_delta, total_notional, trade_count, vwap`
- required column presence: `open_time=true, close_time=true, open=true, high=true, low=true, close=true, volume=true`
- missing required columns: `none`
- optional bar columns present: `volume_delta, trade_count`
- parseable_open_time: `True`
- parseable_close_time: `True`
- open_time_lte_close_time: `True`
- volume_delta present: `None`
- trade-flow columns beyond OHLCV/regime: `bar_id, total_notional, trade_count, volume_delta, vwap`

## Signal-Time Alignment Checks

- signal_time values appear within inspected bar range: `False`
- matching timestamp basis: `mixed`
- full join avoided: `true`

## Feature Availability From Actual Schema

| feature family | required columns | replay/trade-log available? | bar available? | eligible now? | requires L2/OFI approval? | leakage guard | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OHLCV context | open_time, close_time, open, high, low, close, volume | yes | yes | yes | no | completed bars only; no future bars; rolling windows must be shifted | none |
| regime | regime | no | no | yes | no | close-of-bar labels only; no future confirmation | none if present; otherwise missing schema column |
| volume_delta | volume_delta | no | yes | yes | no | past-only derived signed volume; avoid same-bar leakage | missing schema column if absent |
| CVD / delta | volume_delta, delta, cvd | yes | yes | yes | no | use only past trades or bar-level signed volume; shift if derived from rolling windows | missing schema column if no signed-flow source exists |
| absorption proxy | side, price, size_base, buyer_is_maker, native_aggressor_side, volume_delta | no | no | no | no | strict past-only window; never use post-signal move | missing schema columns for signed-trade inputs |
| VPIN / toxicity | side, size_base, buy_volume, sell_volume | no | no | no | no | past-only buckets or completed bar splits only | missing buy/sell bucket columns or signed trade fields |
| footprint | price, size_base, side | no | no | no | no | price-level binning must stop at signal time | missing raw trade tape columns |
| OFI / MLOFI | bids, asks, ofi, mlofi_weighted_aggregate | no | no | no | yes | bounded L2 snapshots only; no future-book contamination | requires approved OFI/L2 artifacts and historical provenance |
| microprice / spread / depth | bids, asks, microprice, spread_bps, depth_top5, depth_top10 | no | no | no | yes | bounded L2 snapshots only; no future-book contamination | requires approved OFI/L2 artifacts |
| spoofing / iceberg / L2 whale pressure | ts_event, bids, asks, refill_count, whale_pressure | no | no | no | yes | timestamp ordering and missing-update sensitivity | requires approved L2 history and historical event coverage |
| funding / OI / liquidation / basis | funding, open_interest, liquidation, basis | no | no | no | no | point-in-time publication timing must be audited | missing verified historical source |

## Blocked Features

### Blocked by OFI/L2 approval
- OFI
- MLOFI
- microprice
- spread
- depth
- queue imbalance
- L2 imbalance
- spoofing
- iceberg
- L2 whale pressure

### Blocked by missing historical source
- funding
- OI
- liquidation
- derivatives crowding
- basis

### Blocked by missing schema columns
- none for required columns

### Blocked by timestamp ambiguity
- none for the inspected schema sample

## Gate 1 Finding

- Gate 1 static inventory: already passed
- Gate 1 schema availability: `pass`
- Gate 2 feature table dry run: not started

## Recommended Next Step

Run a bounded read-only signal-time alignment audit on the discovered replay output and 750btc bar sample to resolve the mixed timestamp basis before any feature table dry run.

## What Is Safe

- schema-only audit
- timestamp alignment audit
- leakage audit
- bounded read-only diagnostics

## What Is Not Safe

- alpha claims
- strategy optimization
- backtesting as part of this task
- full reconstruction
- OFI artifact generation
- paper/live trading
- using unapproved L2 features

## Decision

- `c_exhaustion_signal_time_schema_audit_created`
- `gate_1_schema_audit_completed_or_partial`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_market_data_artifacts_written`
- `no_strategy_backtest_run`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
