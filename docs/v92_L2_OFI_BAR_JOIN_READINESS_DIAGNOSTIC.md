# V9.2 L2 OFI Bar Join-Readiness Diagnostic

## Purpose
Determine why the dry-run manifest deferred join-readiness for every selected file and identify the correct bar-dir / filename / date mapping for future smoke checks.

## Inputs
- `bar_dir`: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- `l2_root`: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT`
- `max_bar_files`: `500`
- `max_l2_files`: `200`
- `bar_files_discovered`: `102`
- `l2_files_sampled`: `200`

## Read-Only Guardrails
- Bounded read-only diagnostic only.
- No OFI artifacts are written.
- No derived OFI data are written.
- No full-corpus reconstruction is attempted.

## Bar Directory Discovery
- Bar files discovered: `102`.
- Bar filename patterns found: `BTCUSDT_tier2_750btc_2020-05-22.parquet, BTCUSDT_tier2_750btc_2020-05-23.parquet, BTCUSDT_tier2_750btc_2020-05-24.parquet, BTCUSDT_tier2_750btc_2020-05-25.parquet, BTCUSDT_tier2_750btc_2020-05-26.parquet, BTCUSDT_tier2_750btc_2020-05-27.parquet, BTCUSDT_tier2_750btc_2020-05-28.parquet, BTCUSDT_tier2_750btc_2020-05-29.parquet, BTCUSDT_tier2_750btc_2020-05-30.parquet, BTCUSDT_tier2_750btc_2020-05-31.parquet`.
- Date hints found in bar paths/filenames: `2020-05-22, 2020-05-23, 2020-05-24, 2020-05-25, 2020-05-26, 2020-05-27, 2020-05-28, 2020-05-29, 2020-05-30, 2020-05-31`.
| bar_file_path | extension | file_name | date_hint_from_path | date_hint_from_filename | symbol_hint | bar_size_hint | row_count_if_fast | timestamp_column_candidates | open_high_low_close_volume_column_candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-22.parquet | 2020-05-22 | 2020-05-22 | BTCUSDT | 750btc | 79 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-23.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-23.parquet | 2020-05-23 | 2020-05-23 | BTCUSDT | 750btc | 59 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-24.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-24.parquet | 2020-05-24 | 2020-05-24 | BTCUSDT | 750btc | 94 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-25.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-25.parquet | 2020-05-25 | 2020-05-25 | BTCUSDT | 750btc | 84 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-26.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-26.parquet | 2020-05-26 | 2020-05-26 | BTCUSDT | 750btc | 78 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-27.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-27.parquet | 2020-05-27 | 2020-05-27 | BTCUSDT | 750btc | 92 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-28.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-28.parquet | 2020-05-28 | 2020-05-28 | BTCUSDT | 750btc | 99 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-29.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-29.parquet | 2020-05-29 | 2020-05-29 | BTCUSDT | 750btc | 77 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-30.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-30.parquet | 2020-05-30 | 2020-05-30 | BTCUSDT | 750btc | 75 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-31.parquet | .parquet | BTCUSDT_tier2_750btc_2020-05-31.parquet | 2020-05-31 | 2020-05-31 | BTCUSDT | 750btc | 65 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-06.parquet | .parquet | BTCUSDT_tier2_750btc_2020-06.parquet | 2020-06 | 2020-06 | BTCUSDT | 750btc | 2007 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-07.parquet | .parquet | BTCUSDT_tier2_750btc_2020-07.parquet | 2020-07 | 2020-07 | BTCUSDT | 750btc | 2011 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-08.parquet | .parquet | BTCUSDT_tier2_750btc_2020-08.parquet | 2020-08 | 2020-08 | BTCUSDT | 750btc | 2522 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-09.parquet | .parquet | BTCUSDT_tier2_750btc_2020-09.parquet | 2020-09 | 2020-09 | BTCUSDT | 750btc | 2308 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-10.parquet | .parquet | BTCUSDT_tier2_750btc_2020-10.parquet | 2020-10 | 2020-10 | BTCUSDT | 750btc | 2124 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-11.parquet | .parquet | BTCUSDT_tier2_750btc_2020-11.parquet | 2020-11 | 2020-11 | BTCUSDT | 750btc | 3610 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-12.parquet | .parquet | BTCUSDT_tier2_750btc_2020-12.parquet | 2020-12 | 2020-12 | BTCUSDT | 750btc | 3328 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-01.parquet | .parquet | BTCUSDT_tier2_750btc_2021-01.parquet | 2021-01 | 2021-01 | BTCUSDT | 750btc | 4588 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-02.parquet | .parquet | BTCUSDT_tier2_750btc_2021-02.parquet | 2021-02 | 2021-02 | BTCUSDT | 750btc | 3358 | open_time, close_time | open_time, close_time, open, high, low, close, volume |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-03.parquet | .parquet | BTCUSDT_tier2_750btc_2021-03.parquet | 2021-03 | 2021-03 | BTCUSDT | 750btc | 2799 | open_time, close_time | open_time, close_time, open, high, low, close, volume |

## L2 Date Discovery
- L2 files sampled: `200`.
- Available L2 dates: `2025-06-28, 2025-06-29, 2025-06-30, 2025-07-02, 2025-07-04, 2025-07-06, 2025-07-08, 2025-07-10, 2025-07-12, 2025-07-14`
| l2_file_path | file_date | file_hour |
| --- | --- | --- |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 05 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/06/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 06 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/07/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 07 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/08/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 08 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/09/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 09 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/10/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 10 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/11/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 11 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/12/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 12 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/13/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 13 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/14/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 14 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/15/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 15 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/16/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 16 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/17/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 17 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/18/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 18 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/19/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 19 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/20/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 20 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/21/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 21 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/22/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 22 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/23/BTCUSDT_orderbook.parquet.zst | 2025-06-28 | 23 |
| /mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-29/00/BTCUSDT_orderbook.parquet.zst | 2025-06-29 | 00 |

## Date Overlap Analysis
- available_bar_dates: `2020-05-22, 2020-05-23, 2020-05-24, 2020-05-25, 2020-05-26, 2020-05-27, 2020-05-28, 2020-05-29, 2020-05-30, 2020-05-31`
- overlap_dates: `2025-06-28, 2025-06-29, 2025-06-30, 2025-07-02, 2025-07-04, 2025-07-06, 2025-07-08, 2025-07-10, 2025-07-12, 2025-07-14`
- l2_dates_missing_bars: `2026-05-23, 2026-05-25, 2026-05-27, 2026-05-29, 2026-05-31, 2026-06-02, 2026-06-04, 2026-06-07`
- bar_dates_without_l2: `2020-05-22, 2020-05-23, 2020-05-24, 2020-05-25, 2020-05-26, 2020-05-27, 2020-05-28, 2020-05-29, 2020-05-30, 2020-05-31`

## Join Helper Compatibility
- helper_available: `True`.
- helper_selected_count: `0`.
- helper_errors: `[]`.
| helper_selected_file |
| --- |

## Minimal Join-Readiness Smoke
- overlap_dates considered for smoke: `2025-06-28, 2025-06-29, 2025-06-30, 2025-07-02, 2025-07-04`
| file_date | bar_file_path | join_attempted | bar_count_preserved | join_deferred_reason |
| --- | --- | --- | --- | --- |
| 2025-06-28 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | true | true | null |
| 2025-06-29 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | true | true | null |
| 2025-06-30 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | true | true | null |
| 2025-07-02 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | true | true | null |
| 2025-07-04 | /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | true | true | null |

## Root Cause
The bar directory is populated, but the dry-run manifest's join lookup is too strict for the 750 BTC bar layout: it looked for exact date files under `bar_dir`, while the available bars are mostly monthly shards such as `BTCUSDT_tier2_750btc_YYYY-MM.parquet` with some day shards. The existing helper is also hardcoded to `500btc`, so it does not locate the 750 BTC files.

## What Worked
- Bar files were discoverable under the provided bar directory.
- L2 files were discoverable and date/sample overlap could be computed from metadata alone.
- A bounded join-readiness smoke can be performed when a compatible bar file is selected by the correct date mapping.

## What Failed Or Remains Unknown
- The dry-run manifest's current exact-date lookup deferred all selected join checks.
- The existing helper is hardcoded to `500btc`, so it does not locate the 750 BTC bar files.
- This diagnostic does not establish a full-corpus join policy.

## What Is Safe
- Use the discovered mapping to update future bounded join-readiness checks.
- Use the smoke join path only as a read-only validation step.

## What Is Not Safe
- Treating the current manifest join deferral as proof that bar data is absent.
- Promoting this diagnostic to full reconstruction.
- Any alpha, paper, or live trading claim.

## Decision
bounded_read_only_diagnostic, bar_directory_scanned, l2_dates_sampled, date_overlap_computed, join_helper_checked_if_available, no_ofi_artifacts_written, full_reconstruction_not_approved, segmented_reconstruction_still_bounded_only, alpha_blocked, paper_live_blocked, date_overlap_found, bar_files_found, join_helper_does_not_locate_bar_files, join_readiness_smoke_attempted, bar_count_preserved_in_smoke.

## Required Next Step
Update the dry-run manifest join lookup to resolve 750 BTC month/day bar filenames instead of requiring exact day matches, then rerun the smoke manifest join-readiness check against the discovered bar files.

This diagnostic does not approve OFI for production, paper trading, live trading, alpha use, or full historical reconstruction.