# V9.2 Hermes C Exhaustion Mixed Decay Input Availability Audit

## Purpose

- Audit which explanatory fields are already available, safely reconstructable, partially available, missing, or blocked for future enriched C Exhaustion decay diagnostics.
- Aggregate-only availability and safety summaries only.
- No trading rule approval, no strategy patch, no raw L2, and no OFI generation.

## Population / Artifact Accounting

- artifacts inspected: `10`
- artifact types inspected: `csv, md, parquet, py`
- prior replay outputs available: `true`
- prior diagnostic reports available: `true`
- schema inspection succeeded: `true`
- any required source missing: `false`

### Artifacts Inspected

- `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- `/home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet`
- `replays/c_exhaustion_replay.py`
- `scripts/run_c_exhaustion_replay.py`
- `scripts/diagnose_c_exhaustion_regime_context.py`
- `scripts/diagnose_c_exhaustion_signal_state.py`
- `scripts/audit_c_exhaustion_signal_time_feature_availability.py`
- `scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py`
- `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RECENT_DECAY_SIGNAL_REGIME_ATTRIBUTION_DIAGNOSTIC.md`
- `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_MIXED_DECAY_CLOSEOUT_AND_INPUT_COLLECTION_DESIGN.md`

## Field Availability Table

| field_name | category | source_artifact | source_path_pattern | historical_coverage_percentage | recent_coverage_percentage | full_sample_coverage_percentage | missingness_percentage | earliest_timestamp_covered | latest_timestamp_covered | known_at_entry_status | timestamp_safety_status | leakage_risk | reconstruction_risk | requires_raw_l2 | requires_ofi_generation | requires_row_level_export | safe_for_future_diagnostic | blocked_reason | final_classification_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_entry_timestamp | Existing replay fields | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | none | low | no | no | no | yes | none | safe_available |
| year_period_label | Existing replay fields | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | none | low | no | no | no | yes | none | safe_available |
| bar_size | Existing replay fields | replays/c_exhaustion_replay.py | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | none | low | no | no | no | yes | none | reconstructable_without_leakage |
| horizon | Existing replay fields | replays/c_exhaustion_replay.py | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | none | low | no | no | no | yes | none | reconstructable_without_leakage |
| side | Existing replay fields | replays/c_exhaustion_replay.py | scripts/run_c_exhaustion_replay.py | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | none | low | no | no | no | yes | none | safe_partial |
| original_return_bps | Existing replay fields | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| gross_return_bps | Existing replay fields | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| net_return_bps | Existing replay fields | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| mfe_bps | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py / /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| mae_bps | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py / /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| exit_class | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py / /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | post-hoc | safe | none | low | no | no | no | yes | none | safe_available |
| signal_state | Existing replay fields | scripts/diagnose_c_exhaustion_signal_state.py / replays/c_exhaustion_replay.py via attach_c_exhaustion_signal | replays/c_exhaustion_replay.py via attach_c_exhaustion_signal | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | none | low | no | no | no | yes | none | reconstructable_without_leakage |
| regime_label | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py / replays/c_exhaustion_replay.py | /home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | none | low | no | no | no | yes | none | safe_available |
| mtf_alignment | Existing replay fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified MTF alignment field in current artifacts | blocked_missing |
| range_trend_label | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | safe_available |
| volatility_label | Existing replay fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | safe_available |
| pre_entry_volatility_expansion_compression | Potential pre-entry context fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_bar_return_path | Potential pre-entry context fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_bar_range | Potential pre-entry context fields | bars_750btc parquet columns | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_bar_volume_notional | Potential pre-entry context fields | bars_750btc parquet columns | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| prior_trade_density | Potential pre-entry context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified point-in-time trade-density source in repo surface | blocked_missing |
| signal_intensity_score | Potential pre-entry context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no signal intensity or score magnitude exists in current artifacts | blocked_missing |
| distance_from_vwap | Potential pre-entry context fields | bars_750btc parquet columns | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| distance_from_recent_high_low | Potential pre-entry context fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | safe_available |
| local_trend_range_state | Potential pre-entry context fields | scripts/diagnose_c_exhaustion_regime_context.py | scripts/diagnose_c_exhaustion_regime_context.py | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | safe_available |
| funding | External or missing market-context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified historical funding source in inspected repo surface | blocked_missing |
| open_interest | External or missing market-context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified historical open-interest source in inspected repo surface | blocked_missing |
| liquidation_data | External or missing market-context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified liquidation source in inspected repo surface | blocked_missing |
| cvd_delta | External or missing market-context fields | scripts/diagnose_c_exhaustion_regime_context.py / bars_750btc volume_delta | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_*.parquet | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| ofi | External or missing market-context fields | features/microstructure_ofi.py | OFI artifact not approved | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | yes | no | no | requires new OFI generation; blocked by design | blocked_requires_new_ofi |
| l2_imbalance | External or missing market-context fields | features/l2_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| spread | External or missing market-context fields | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| microprice | External or missing market-context fields | features/microprice.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| order_book_depth | External or missing market-context fields | features/queue_imbalance.py | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | no | no | no | requires raw L2 snapshots | blocked_requires_raw_l2 |
| whale_large_print_context | External or missing market-context fields | features/whale.py / features/large_prints.py | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified whale / large-print source in inspected repo surface | blocked_missing |
| market_wide_beta_btc_regime_context | External or missing market-context fields | missing | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | no verified market-wide beta source in inspected repo surface | blocked_missing |
| session_time_of_day_labels | External or missing market-context fields | trade entry timestamp | trade log / entry_time | 100.000 | 100.000 | 100.000 | 0.000 | 2020-09-02 11:09:58.270000 | 2026-05-07 14:07:47.113084 | yes | safe | low | low | no | no | no | yes | none | reconstructable_without_leakage |
| raw_l2_derived_fields | Unsafe or restricted fields | raw L2 files | raw L2 files | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | no | yes | no | raw L2-derived fields are blocked unless already safely materialized | blocked_requires_raw_l2 |
| newly_generated_ofi | Unsafe or restricted fields | features/microstructure_ofi.py | OFI artifacts not approved | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | yes | yes | no | no | new OFI generation is blocked | blocked_requires_new_ofi |
| row_level_trade_export_required | Unsafe or restricted fields | trade log / row-level export | row-level export | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | yes | no | row-level export is not allowed | blocked_row_level_export_required |
| future_return_derived_labels | Unsafe or restricted fields | future path outcomes | post-hoc labels only | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | post-hoc | unsafe | high | high | no | no | no | no | future-return-derived features cannot be used as inputs | blocked_future_leakage_risk |
| manually_assigned_discretionary_labels | Unsafe or restricted fields | manual review | missing | 0.000 | 0.000 | 0.000 | 100.000 | n/a | n/a | unknown | unsafe | high | high | no | no | no | no | manual discretionary labels are not allowed as feature inputs | blocked_future_leakage_risk |

## Safe Field Summary

- safe_available count: `13`
- safe_partial count: `1`
- reconstructable_without_leakage count: `10`

- `trade_entry_timestamp`
- `year_period_label`
- `original_return_bps`
- `gross_return_bps`
- `net_return_bps`
- `mfe_bps`
- `mae_bps`
- `exit_class`
- `regime_label`
- `range_trend_label`
- `volatility_label`
- `distance_from_recent_high_low`
- `local_trend_range_state`
- `side`
- `bar_size`
- `horizon`
- `signal_state`
- `pre_entry_volatility_expansion_compression`
- `prior_bar_return_path`
- `prior_bar_range`
- `prior_bar_volume_notional`
- `distance_from_vwap`
- `cvd_delta`
- `session_time_of_day_labels`

## Blocked Field Summary

| blocked_reason | count | example_fields |
| --- | --- | --- |
| requires raw L2 snapshots | 4 | l2_imbalance, microprice, order_book_depth, spread |
| future-return-derived features cannot be used as inputs | 1 | future_return_derived_labels |
| manual discretionary labels are not allowed as feature inputs | 1 | manually_assigned_discretionary_labels |
| new OFI generation is blocked | 1 | newly_generated_ofi |
| no signal intensity or score magnitude exists in current artifacts | 1 | signal_intensity_score |
| no verified MTF alignment field in current artifacts | 1 | mtf_alignment |
| no verified historical funding source in inspected repo surface | 1 | funding |
| no verified historical open-interest source in inspected repo surface | 1 | open_interest |
| no verified liquidation source in inspected repo surface | 1 | liquidation_data |
| no verified market-wide beta source in inspected repo surface | 1 | market_wide_beta_btc_regime_context |
| no verified point-in-time trade-density source in repo surface | 1 | prior_trade_density |
| no verified whale / large-print source in inspected repo surface | 1 | whale_large_print_context |
| raw L2-derived fields are blocked unless already safely materialized | 1 | raw_l2_derived_fields |
| requires new OFI generation; blocked by design | 1 | ofi |
| row-level export is not allowed | 1 | row_level_trade_export_required |

## Historical vs Recent Coverage Summary

- balanced historical/recent coverage: `bar_size, horizon, side, original_return_bps, gross_return_bps, net_return_bps, mfe_bps, mae_bps, prior_bar_range, prior_bar_volume_notional, distance_from_vwap, session_time_of_day_labels`
- historical-only coverage: `none`
- recent-only coverage: `none`
- poor coverage both periods: `trade_entry_timestamp, year_period_label, exit_class, signal_state, regime_label, mtf_alignment, range_trend_label, volatility_label, pre_entry_volatility_expansion_compression, prior_bar_return_path, prior_trade_density, signal_intensity_score, distance_from_recent_high_low, local_trend_range_state, funding, open_interest, liquidation_data, cvd_delta, ofi, l2_imbalance, spread, microprice, order_book_depth, whale_large_print_context, market_wide_beta_btc_regime_context, raw_l2_derived_fields, newly_generated_ofi, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`
- timestamp ambiguity: `mtf_alignment, prior_trade_density, signal_intensity_score, funding, open_interest, liquidation_data, ofi, l2_imbalance, spread, microprice, order_book_depth, whale_large_print_context, market_wide_beta_btc_regime_context, raw_l2_derived_fields, newly_generated_ofi, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`

## Known-at-Entry Safety Summary

- fields clearly known at entry: `trade_entry_timestamp, year_period_label, bar_size, horizon, side, signal_state, regime_label, range_trend_label, volatility_label, pre_entry_volatility_expansion_compression, prior_bar_return_path, prior_bar_range, prior_bar_volume_notional, distance_from_vwap, distance_from_recent_high_low, local_trend_range_state, cvd_delta, session_time_of_day_labels`
- fields known only post-hoc: `original_return_bps, gross_return_bps, net_return_bps, mfe_bps, mae_bps, exit_class, future_return_derived_labels`
- fields blocked due to future leakage risk: `future_return_derived_labels, manually_assigned_discretionary_labels`
- ambiguous fields: `mtf_alignment, prior_trade_density, signal_intensity_score, funding, open_interest, liquidation_data, ofi, l2_imbalance, spread, microprice, order_book_depth, whale_large_print_context, market_wide_beta_btc_regime_context, raw_l2_derived_fields, newly_generated_ofi, row_level_trade_export_required, future_return_derived_labels, manually_assigned_discretionary_labels`

## Raw L2 / OFI Safety Summary

- no raw L2 files were read
- OFI was not generated
- fields requiring raw L2 are blocked unless already safely materialized
- fields requiring new OFI are blocked

## Synthetic Safety Checks

| check | status | details |
| --- | --- | --- |
| raw L2 files were not read | passed | The audit only inspects trade log, 750btc bars, and repository text/schemas. |
| OFI was not generated | passed | No OFI engine or OFI artifact creation path is invoked. |
| row-level artifacts were not exported | passed | The audit writes markdown only. |
| timestamp coverage checked before approval | passed | Coverage is calculated from entry_time / year splits. |
| known-at-entry documented for every field | passed | Each field row includes an explicit status. |
| future outcome fields marked post-hoc only | passed | Gross/net/MFE/MAE/exit-class rows are labelled post-hoc. |
| missing fields not silently treated as safe | passed | Missing or blocked fields receive explicit blocked labels. |
| block raw-L2 or OFI-only fields | passed | 7 fields remain blocked. |

## Enriched Diagnostic Readiness

- at least one non-outcome explanatory field is safe_available or reconstructable_without_leakage: `yes`
- historical and recent coverage sufficient for aggregate comparison: `true`
- timestamp safety confirmed for usable fields: `true`
- known-at-entry status confirmed for usable fields: `true`
- future enriched diagnostic design possible without raw L2, new OFI, or row-level exports: `yes`
- readiness note: At least one safe explanatory field is available with sufficient historical and recent coverage.

## Stop / Go Conclusion

- decision: `proceed_to_enriched_signal_regime_decay_diagnostic_design_only`

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
