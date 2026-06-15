# V9.2 L2 / OFI Source Inventory Audit

## Purpose
Inventory read-only historical L2 and OFI-related source files on the Seagate drive and classify whether they are usable for OFI reconstruction research.

## Inputs
- Search roots supplied on the CLI.
- Historical Seagate HFT order-book, trade, and documentation files discovered by filename/path scan.
- Existing 750 BTC bar outputs under the phase1f workspace are treated as context only.

## Read-Only Guardrails
This audit only reads file metadata, schemas for sampled parquet files, and short text headers where applicable.
It does not extract archives, regenerate OFI, regenerate bars, or modify any source data.
This audit does not approve OFI for production, paper trading, live trading, or alpha use.

## Executive Finding
Historical OFI output files were not found, but a substantial Binance futures order-book corpus exists on Seagate under `cryptohftdata/orderbook/binance_futures/BTCUSDT`, and the sampled parquet schema contains timestamp and update-id fields suitable for OFI reconstruction research.

- Historical OFI output files found: no.
- L2 snapshot/diff/TBT/full-depth files found: yes.
- Only trades/aggTrades/bars found: no; this inventory includes raw L2 order-book sources.
- Enough source data to reconstruct OFI: yes.
- OFI approved for alpha/paper/live use: No.
- Next safe validation step: read-only provenance and sequence/coverage verification on the raw L2 order-book corpus, then validate any OFI join helper against those files.

## Search Root Status
| path | exists | candidate_count | note |
| --- | --- | --- | --- |
| /mnt/seagate | True | 8341 | l2_diff:8074, agg_trades:134, manifest:133 |
| /mnt/seagate/tm-trading-v555/data | True | 8341 | l2_diff:8074, agg_trades:134, manifest:133 |
| /home/tokio/tm-trading-v92-phase1f | True | 513 | ohlcv:511, manifest:2 |

## Candidate Inventory Summary
| data_type_guess | file_count |
| --- | --- |
| l2_diff | 8074 |
| ohlcv | 511 |
| manifest | 135 |
| agg_trades | 134 |

Readiness summary:
| readiness | file_count |
| --- | --- |
| ofi_reconstruction_ready | 8074 |
| not_ready_ohlcv_only | 511 |
| not_ready_manifest_only | 135 |
| not_ready_trades_only | 134 |

## Candidate File Inventory
| data_type_guess | venue_guess | symbol_guess | file_count | example_path | time_coverage_guess | schema_hint | usable_for_ofi_reconstruction_guess | risk | required_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| agg_trades | binance_spot | BTCUSDT | 134 | /mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21/BTCUSDT-aggTrades-2020-05-22.zip | 2020-05-22..2026-05-21 | schema_not_applicable | not_ready_trades_only | high | Not an L2 source; cannot reconstruct OFI from trades alone. |
| l2_diff | binance_futures | BTCUSDT | 8074 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | received_time, event_time, transaction_time, symbol, event_type, first_update_id, final_update_id, prev_final_update_id, last_update_id, side, price, quantity | ofi_reconstruction_ready | moderate | Likely L2 diff/order-book source; confirm schema. |
| manifest | binance_spot | BTCUSDT | 133 | /mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21/BTCUSDT-aggTrades-2020-05-22.zip.CHECKSUM | 2020-05-22..2026-05-21 | schema_not_applicable | not_ready_manifest_only | high | Document-only. |
| manifest | unknown | UNKNOWN | 2 | /home/tokio/tm-trading-v92-phase1f/d4_bar_size_summary.md | unknown | schema_not_applicable | not_ready_manifest_only | high | Document-only. |
| ohlcv | unknown | BTCUSDT | 102 | /home/tokio/tm-trading-v92-phase1f/bars_1000btc/BTCUSDT_tier2_1000btc_2020-05-22.parquet | 2020-05-22 | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |
| ohlcv | unknown | BTCUSDT | 102 | /home/tokio/tm-trading-v92-phase1f/bars_1500btc/BTCUSDT_tier2_1500btc_2020-05-22.parquet | 2020-05-22 | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |
| ohlcv | unknown | BTCUSDT | 102 | /home/tokio/tm-trading-v92-phase1f/bars_300btc/BTCUSDT_tier2_300btc_2020-05-22.parquet | 2020-05-22 | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |
| ohlcv | unknown | BTCUSDT | 102 | /home/tokio/tm-trading-v92-phase1f/bars_500btc/BTCUSDT_tier2_500btc_2020-05-22.parquet | 2020-05-22 | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |
| ohlcv | unknown | BTCUSDT | 102 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet | 2020-05-22 | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |
| ohlcv | unknown | UNKNOWN | 1 | /home/tokio/tm-trading-v92-phase1f/d4_bar_size_surface.csv | unknown | schema_not_applicable | not_ready_ohlcv_only | high | OHLCV bars are not L2 OFI sources. |

## Likely L2 Sources
| data_type_guess | venue_guess | symbol_guess | file_count | example_path | time_coverage_guess | schema_hint | usable_for_ofi_reconstruction_guess | required_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2_diff | binance_futures | BTCUSDT | 8074 | /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | received_time, event_time, transaction_time, symbol, event_type, first_update_id, final_update_id, prev_final_update_id, last_update_id, side, price, quantity | ofi_reconstruction_ready | Likely L2 diff/order-book source; confirm schema. |

## Likely HFT Full-Depth Sources
No distinct full-depth/TBT source files were discovered beyond the order-book diff corpus.

## Likely OFI Outputs
No historical OFI output files were discovered under the supplied roots.

## Trade-Only / Not-L2 Sources
| data_type_guess | venue_guess | symbol_guess | file_count | example_path | time_coverage_guess | schema_hint | usable_for_ofi_reconstruction_guess | required_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| agg_trades | binance_spot | BTCUSDT | 134 | /mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21/BTCUSDT-aggTrades-2020-05-22.zip | 2020-05-22..2026-05-21 | schema_not_applicable | not_ready_trades_only | Not an L2 source; cannot reconstruct OFI from trades alone. |

## Manifest / Documentation Sources
| data_type_guess | venue_guess | symbol_guess | file_count | example_path | time_coverage_guess | schema_hint | usable_for_ofi_reconstruction_guess | required_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| manifest | binance_spot | BTCUSDT | 133 | /mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21/BTCUSDT-aggTrades-2020-05-22.zip.CHECKSUM | 2020-05-22..2026-05-21 | schema_not_applicable | not_ready_manifest_only | Document-only. |
| manifest | unknown | UNKNOWN | 2 | /home/tokio/tm-trading-v92-phase1f/d4_bar_size_summary.md | unknown | schema_not_applicable | not_ready_manifest_only | Document-only. |

## Missing Roots
No search roots were missing.

## OFI Reconstruction Readiness
The historical Seagate order-book corpus is reconstruction-ready at the source level because the sampled parquet schema contains timestamps, update IDs, and order-book update fields.
Historical OFI output inventory is still unavailable, so no derived OFI artifact is being claimed as production-ready.

## What Is Safe
- Read-only inventory of Seagate HFT source files.
- `features.v92_data_policy.join_ofi_to_bars_preserve_coverage` is importable and callable.
- The Binance futures order-book corpus is a concrete raw L2 source family for future provenance checks.

## What Is Not Safe
- Treating this inventory as proof that OFI is production-ready.
- Treating the absence of historical OFI output files as evidence that raw L2 reconstruction is impossible.
- Treating aggTrades or OHLCV bars as sufficient OFI sources.

## Required Next Step
Run a read-only provenance and sequence-gap audit on the raw order-book corpus, then validate a coverage-preserving OFI join path against a small sample before considering any broader research use.
