# V9.2 Hermes C Exhaustion Richer Context Source Availability Audit

## Executive Summary

- Audit purpose: determine which richer known-at-entry market-context sources are safely available, partially available, reconstructable without leakage, missing, timestamp unsafe, leakage unsafe, or blocked.
- Current C Exhaustion state: keep anchor alive and collect more inputs.
- Usable richer context sources found: `yes`
- Future richer-context enriched decay diagnostic design allowed: `yes`
- Readiness note: At least one richer context source is available with sufficient historical and recent coverage.

## Artifact / Source Accounting

- artifacts inspected: `14`
- artifact types inspected: `csv, md, parquet, py`
- prior replay outputs available: `true`
- prior diagnostic reports available: `true`
- schema inspection succeeded: `true`
- any required source missing: `false`

### Artifacts / Path Patterns Inspected

- `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet`
- `replays/c_exhaustion_replay.py`
- `scripts/run_c_exhaustion_replay.py`
- `scripts/diagnose_c_exhaustion_regime_context.py`
- `scripts/diagnose_c_exhaustion_signal_state.py`
- `scripts/dry_run_c_exhaustion_signal_time_feature_table.py`
- `features/queue_imbalance.py`
- `features/microprice.py`
- `features/regime_classifier.py`
- `features/atr_context.py`
- `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_ENRICHED_SIGNAL_REGIME_DECAY_DIAGNOSTIC.md`
- `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_VWAP_DISTANCE_CONTEXT_STABILITY_DIAGNOSTIC.md`
- `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_KNOWN_AT_ENTRY_CONTEXT_COLLECTION_DESIGN.md`

### Unique Source Path Patterns

- `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet`
- `OFI artifacts not approved`
- `missing`
- `post-hoc labels only`
- `raw L2 files`
- `row-level export`
- `scripts/diagnose_c_exhaustion_regime_context.py`
- `scripts/run_c_exhaustion_replay.py`
- `trade log / entry_time`
- `unsafe timestamps / raw L2`

## Classification Table

| field_name | source_group | source_type | source_path_pattern | historical_coverage_percentage | recent_coverage_percentage | full_sample_coverage_percentage | missingness_percentage | earliest_timestamp_covered | latest_timestamp_covered | timestamp_granularity | known_at_entry_status | timestamp_safety_status | leakage_risk | reconstruction_risk | requires_raw_l2 | requires_ofi_generation | requires_row_level_export | safe_for_future_diagnostic | blocked_reason | final_classification_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_entry_timestamp | Existing replay fields | trade log | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | entry_time | yes | safe | none | low | no | no | no | yes | none | safe_available |
| year_period_label | Existing replay fields | trade log | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | year | yes | safe | none | low | no | no | no | yes | none | safe_available |
| bar_size | Existing replay fields | replay config | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | static | yes | safe | none | low | no | no | no | yes | none | reconstructable_without_leakage |
| horizon | Existing replay fields | replay config | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | static | yes | safe | none | low | no | no | no | yes | none | reconstructable_without_leakage |
| side | Existing replay fields | replay config | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | static | yes | safe | none | low | no | no | no | yes | none | safe_partial |
| regime_label | Existing replay fields | trade log / regime context | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | none | low | no | no | no | yes | none | safe_available |
| range_trend_label | Existing replay fields | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | safe_available |
| volatility_label | Existing replay fields | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | safe_available |
| pre_entry_volatility_expansion_compression | Pre-entry context | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | rolling_24_bars | yes | safe | low | low | no | no | no | yes | none | safe_partial |
| prior_bar_return_path | Pre-entry context | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | rolling_24_bars | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_bar_range | Pre-entry context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_bar_volume_notional | Pre-entry context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| distance_from_vwap | Market-structure context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| distance_from_recent_high_low | Market-structure context | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | rolling_24_bars | yes | safe | low | low | no | no | no | yes | none | safe_available |
| local_trend_range_state | Market-structure context | regime context | scripts/diagnose_c_exhaustion_regime_context.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | rolling_24_bars | yes | safe | low | low | no | no | no | yes | none | safe_available |
| trade_density | Trade-flow context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | safe_available |
| volume_burst | Trade-flow context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | safe_partial |
| notional_burst | Trade-flow context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | safe_partial |
| aggressive_buy_sell_imbalance | Trade-flow context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| cvd_delta | Trade-flow context | bars_750btc parquet | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | bar_close | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| session_time_of_day_labels | Cross-market context | trade entry timestamp | trade log / entry_time | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | entry_time | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| weekday_weekend_effect | Cross-market context | trade entry timestamp | trade log / entry_time | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | entry_time | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| funding_rate | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified historical funding source in inspected repo surface | blocked_missing |
| open_interest | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified historical open-interest source in inspected repo surface | blocked_missing |
| open_interest_velocity | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified point-in-time open-interest velocity source in inspected repo surface | blocked_missing |
| liquidation_prints | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified liquidation source in inspected repo surface | blocked_missing |
| long_short_ratio | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified long/short ratio source in inspected repo surface | blocked_missing |
| perp_basis_premium | Derivatives context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified perp basis / premium source in inspected repo surface | blocked_missing |
| large_trade_clusters | Trade-flow context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified large-trade cluster source in current artifacts | blocked_missing |
| trade_flow_imbalance_top_of_book | Market-structure context | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| spread | Market-structure context | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| microprice | Market-structure context | features/microprice.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| top_of_book_imbalance | Market-structure context | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| depth_imbalance | Market-structure context | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| btc_market_beta | Cross-market context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified BTC beta source in inspected repo surface | blocked_missing |
| eth_btc_context | Cross-market context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified ETH/BTC context source in inspected repo surface | blocked_missing |
| market_wide_crypto_risk_regime | Cross-market context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified crypto risk regime source in inspected repo surface | blocked_missing |
| dollar_index_macro_proxy | Cross-market context | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified macro proxy source in inspected repo surface | blocked_missing |
| raw_l2_derived_fields | Unsafe or restricted fields | raw L2 files | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | yes | no | raw L2-derived fields are blocked unless already safely materialized | blocked_requires_raw_l2 |
| newly_generated_ofi | Unsafe or restricted fields | features/microstructure_ofi.py | OFI artifacts not approved | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | yes | no | no | new OFI generation is blocked | blocked_requires_new_ofi |
| reconstructed_order_book_features_from_unsafe_timestamps | Unsafe or restricted fields | reconstructed order book features | unsafe timestamps / raw L2 | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | reconstructed order book features from unsafe timestamps are blocked | blocked_timestamp_unsafe |
| row_level_trade_export_required | Unsafe or restricted fields | trade log / row-level export | row-level export | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | yes | no | row-level export is not allowed | blocked_row_level_export_required |
| future_return_derived_labels | Unsafe or restricted fields | future path outcomes | post-hoc labels only | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | post-hoc | post-hoc | unsafe | high | high | no | no | no | no | future-return-derived features cannot be used as inputs | blocked_future_leakage_risk |
| manually_assigned_discretionary_labels | Unsafe or restricted fields | manual review | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | manual discretionary labels are not allowed as feature inputs | blocked_future_leakage_risk |

## Safe Source Summary

- safe_available count: `8`
- safe_partial count: `4`
- reconstructable_without_leakage count: `10`

- `trade_entry_timestamp`
- `year_period_label`
- `regime_label`
- `range_trend_label`
- `volatility_label`
- `distance_from_recent_high_low`
- `local_trend_range_state`
- `trade_density`
- `side`
- `pre_entry_volatility_expansion_compression`
- `volume_burst`
- `notional_burst`
- `bar_size`
- `horizon`
- `prior_bar_return_path`
- `prior_bar_range`
- `prior_bar_volume_notional`
- `distance_from_vwap`
- `aggressive_buy_sell_imbalance`
- `cvd_delta`
- `session_time_of_day_labels`
- `weekday_weekend_effect`

## Blocked Source Summary

| blocked_reason | count | example_fields |
| --- | --- | --- |
| requires raw L2 snapshots | 5 | depth_imbalance, microprice, spread, top_of_book_imbalance, trade_flow_imbalance_top_of_book |
| future-return-derived features cannot be used as inputs | 1 | future_return_derived_labels |
| manual discretionary labels are not allowed as feature inputs | 1 | manually_assigned_discretionary_labels |
| new OFI generation is blocked | 1 | newly_generated_ofi |
| no verified BTC beta source in inspected repo surface | 1 | btc_market_beta |
| no verified ETH/BTC context source in inspected repo surface | 1 | eth_btc_context |
| no verified crypto risk regime source in inspected repo surface | 1 | market_wide_crypto_risk_regime |
| no verified historical funding source in inspected repo surface | 1 | funding_rate |
| no verified historical open-interest source in inspected repo surface | 1 | open_interest |
| no verified large-trade cluster source in current artifacts | 1 | large_trade_clusters |
| no verified liquidation source in inspected repo surface | 1 | liquidation_prints |
| no verified long/short ratio source in inspected repo surface | 1 | long_short_ratio |
| no verified macro proxy source in inspected repo surface | 1 | dollar_index_macro_proxy |
| no verified perp basis / premium source in inspected repo surface | 1 | perp_basis_premium |
| no verified point-in-time open-interest velocity source in inspected repo surface | 1 | open_interest_velocity |
| raw L2-derived fields are blocked unless already safely materialized | 1 | raw_l2_derived_fields |
| reconstructed order book features from unsafe timestamps are blocked | 1 | reconstructed_order_book_features_from_unsafe_timestamps |
| row-level export is not allowed | 1 | row_level_trade_export_required |

## Historical vs Recent Coverage

- balanced historical/recent coverage: `trade_entry_timestamp, year_period_label, bar_size, horizon, side, regime_label, range_trend_label, volatility_label, pre_entry_volatility_expansion_compression, prior_bar_return_path, prior_bar_range, prior_bar_volume_notional, distance_from_vwap, distance_from_recent_high_low, local_trend_range_state, trade_density, volume_burst, notional_burst, aggressive_buy_sell_imbalance, cvd_delta, session_time_of_day_labels, weekday_weekend_effect`
- historical-only coverage: `none`
- recent-only coverage: `none`
- poor coverage both periods: `funding_rate, open_interest, open_interest_velocity, liquidation_prints, long_short_ratio, perp_basis_premium, large_trade_clusters, trade_flow_imbalance_top_of_book, spread, microprice, top_of_book_imbalance, depth_imbalance, btc_market_beta, eth_btc_context, market_wide_crypto_risk_regime, dollar_index_macro_proxy, raw_l2_derived_fields, newly_generated_ofi, reconstructed_order_book_features_from_unsafe_timestamps, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`
- timestamp ambiguity: `funding_rate, open_interest, open_interest_velocity, liquidation_prints, long_short_ratio, perp_basis_premium, large_trade_clusters, trade_flow_imbalance_top_of_book, spread, microprice, top_of_book_imbalance, depth_imbalance, btc_market_beta, eth_btc_context, market_wide_crypto_risk_regime, dollar_index_macro_proxy, raw_l2_derived_fields, newly_generated_ofi, reconstructed_order_book_features_from_unsafe_timestamps, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`

## Known-at-Entry and Timestamp Safety

- fields clearly known at entry: `trade_entry_timestamp, year_period_label, bar_size, horizon, side, regime_label, range_trend_label, volatility_label, pre_entry_volatility_expansion_compression, prior_bar_return_path, prior_bar_range, prior_bar_volume_notional, distance_from_vwap, distance_from_recent_high_low, local_trend_range_state, trade_density, volume_burst, notional_burst, aggressive_buy_sell_imbalance, cvd_delta, session_time_of_day_labels, weekday_weekend_effect`
- fields known only post-hoc: `future_return_derived_labels`
- fields blocked due to future leakage risk: `future_return_derived_labels, manually_assigned_discretionary_labels`
- ambiguous fields: `funding_rate, open_interest, open_interest_velocity, liquidation_prints, long_short_ratio, perp_basis_premium, large_trade_clusters, trade_flow_imbalance_top_of_book, spread, microprice, top_of_book_imbalance, depth_imbalance, btc_market_beta, eth_btc_context, market_wide_crypto_risk_regime, dollar_index_macro_proxy, raw_l2_derived_fields, newly_generated_ofi, reconstructed_order_book_features_from_unsafe_timestamps, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`

## Raw L2 / OFI / Row-Level Safety

- no raw L2 files were read
- OFI was not generated
- no row-level artifacts were exported
- no modeling dataset was created
- fields requiring raw L2 are blocked unless already safely materialized
- fields requiring new OFI are blocked
- fields requiring row-level export are blocked

## Future Diagnostic Readiness

- richer non-outcome context source available for future diagnostic design: `yes`
- historical and recent coverage sufficient for aggregate comparison: `true`
- timestamp safety confirmed for usable fields: `true`
- known-at-entry status confirmed for usable fields: `true`
- future richer-context enriched decay diagnostic design possible without raw L2, new OFI, or row-level exports: `yes`
- readiness note: At least one richer context source is available with sufficient historical and recent coverage.

## Stop / Go Conclusion

- decision: `proceed_to_richer_context_enriched_decay_diagnostic_design_only`

## Required Validation

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short before work`
- `git diff --check`
- `git status --short after work`
- confirm only Hermes Lab files changed
- confirm core repo was not modified
- no tests required because Markdown-only
