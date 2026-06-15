# V9.2 L2 OFI Resync Root-Cause Diagnostic

## Purpose
Determine why strict-sequence OFI reconstruction hit a resync in the sampled Binance futures L2 file. This is a read-only infrastructure diagnostic, not an alpha test.

## Inputs
- Input file: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-06-28/05/BTCUSDT_orderbook.parquet.zst`
- Expected resync index: `1218`
- Context before: `20`
- Context after: `20`
- Max events scanned: `3000`
- Strict sequence: `True`
- Symbol filter: `BTCUSDT`

## Read-Only Guardrails
This diagnostic only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.
This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use.

## Executive Finding
Strict-sequence resync reproduced at packet index `1218`. The triggering packet follows a snapshot/reset-style packet, but the gap disappears when packets are ordered by transaction_time. That makes the failure more consistent with ordering semantics than with a hard source-data gap.

## Reproduction Summary
| source_file_read_complete | read_mode | rows_scanned | packets_built | processed_event_count | ofi_emitted_count | warmup_none_count | sequence_gap_count | snapshot_or_reset_event_count | resync_packet_index | expected_resync_index | resync_index_matches_expectation | packet_boundary_unknown | dropped_last_packet_for_boundary_safety |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| false | bounded_packet_sample | 718214 | 3000 | 1218 | 1215 | 2 | 1 | 1 | 1218 | 1218 | true | false | 0 |

## Packet Schema Summary
| rows_scanned | global_packet_count | row_order_packet_count | packet_grouping_order_risk | bad_key_row_count | bad_cast_row_count | unknown_side_row_count | rows_have_price_and_quantity_strings | event_time_is_microseconds | final_update_id_present | first_update_id_null_in_some_packets | prev_final_update_id_null_in_some_packets | rows_sorted_by_event_time_in_source | received_time_not_used_for_grouping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 718214 | 3000 | 3000 | false | 0 | 0 | 0 | true | true | true | true | true | false | true |

## Resync Event Summary
| resync_packet_index | engine_last_update_id_before | engine_last_update_id_after | previous_packet_final_update_id | current_packet_prev_final_update_id | current_packet_is_snapshot_or_reset | current_packet_event_time | current_packet_event_type | sequence_gap_count | snapshot_or_reset_event_count | warmup_none_count | ofi_emitted_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1218 | 7900538334001 | 7900538334001 | 7900538334001 | 7900538333009 | false | 1751086924306 | update | 1 | 1 | 2 | 1215 |

## Context Window Around Resync
| packet_index | event_time | first_update_id | final_update_id | prev_final_update_id | expected_prev_final_update_id | matches_previous_final_update_id | sequence_gap_size | is_snapshot_or_reset | bid_level_count | ask_level_count | event_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1198 | 1751086922368 | 7900538245180 | 7900538249765 | 7900538245097 | 7900538245097 | true | 0 | false | 99 | 63 | update |
| 1199 | 1751086922472 | 7900538250571 | 7900538255268 | 7900538249765 | 7900538249765 | true | 0 | false | 60 | 15 | update |
| 1200 | 1751086922576 | 7900538255369 | 7900538259572 | 7900538255268 | 7900538255268 | true | 0 | false | 81 | 33 | update |
| 1201 | 1751086922677 | 7900538259596 | 7900538263528 | 7900538259572 | 7900538259572 | true | 0 | false | 78 | 60 | update |
| 1202 | 1751086922779 | 7900538264069 | 7900538269922 | 7900538263528 | 7900538263528 | true | 0 | false | 144 | 441 | update |
| 1203 | 1751086922880 | 7900538269925 | 7900538275284 | 7900538269922 | 7900538269922 | true | 0 | false | 147 | 336 | update |
| 1204 | 1751086922981 | 7900538275303 | 7900538280314 | 7900538275284 | 7900538275284 | true | 0 | false | 87 | 93 | update |
| 1205 | 1751086923082 | 7900538280356 | 7900538285902 | 7900538280314 | 7900538280314 | true | 0 | false | 84 | 78 | update |
| 1206 | 1751086923185 | 7900538286082 | 7900538291443 | 7900538285902 | 7900538285902 | true | 0 | false | 90 | 96 | update |
| 1207 | 1751086923287 | 7900538291553 | 7900538295188 | 7900538291443 | 7900538291443 | true | 0 | false | 66 | 42 | update |
| 1208 | 1751086923389 | 7900538295368 | 7900538300043 | 7900538295188 | 7900538295188 | true | 0 | false | 57 | 39 | update |
| 1209 | 1751086923492 | 7900538300143 | 7900538304019 | 7900538300043 | 7900538300043 | true | 0 | false | 84 | 54 | update |
| 1210 | 1751086923594 | 7900538304685 | 7900538308353 | 7900538304019 | 7900538304019 | true | 0 | false | 84 | 48 | update |
| 1211 | 1751086923697 | 7900538308523 | 7900538311667 | 7900538308353 | 7900538308353 | true | 0 | false | 54 | 42 | update |
| 1212 | 1751086923798 | 7900538311782 | 7900538316219 | 7900538311667 | 7900538311667 | true | 0 | false | 69 | 57 | update |
| 1213 | 1751086923901 | 7900538316362 | 7900538319736 | 7900538316219 | 7900538316219 | true | 0 | false | 81 | 78 | update |
| 1214 | 1751086924002 | 7900538319793 | 7900538323358 | 7900538319736 | 7900538319736 | true | 0 | false | 96 | 60 | update |
| 1215 | 1751086924103 | 7900538323415 | 7900538328305 | 7900538323358 | 7900538323358 | true | 0 | false | 93 | 66 | update |
| 1216 | 1751086924205 | 7900538328331 | 7900538333009 | 7900538328305 | 7900538328305 | true | 0 | false | 63 | 57 | update |
| 1217 | 1751086924229 | null | 7900538334001 | null | 7900538333009 | false | null | true | 500 | 500 | snapshot |
| 1218 | 1751086924306 | 7900538333063 | 7900538339225 | 7900538333009 | 7900538334001 | false | 992 | false | 69 | 57 | update |
| 1219 | 1751086924408 | 7900538339279 | 7900538343068 | 7900538339225 | 7900538339225 | true | 0 | false | 48 | 30 | update |
| 1220 | 1751086924509 | 7900538343352 | 7900538347653 | 7900538343068 | 7900538343068 | true | 0 | false | 60 | 42 | update |
| 1221 | 1751086924611 | 7900538348011 | 7900538351593 | 7900538347653 | 7900538347653 | true | 0 | false | 78 | 33 | update |
| 1222 | 1751086924714 | 7900538351904 | 7900538354909 | 7900538351593 | 7900538351593 | true | 0 | false | 42 | 48 | update |
| 1223 | 1751086924816 | 7900538355439 | 7900538372070 | 7900538354909 | 7900538354909 | true | 0 | false | 162 | 153 | update |
| 1224 | 1751086924918 | 7900538372303 | 7900538381502 | 7900538372070 | 7900538372070 | true | 0 | false | 84 | 90 | update |
| 1225 | 1751086925019 | 7900538381723 | 7900538386789 | 7900538381502 | 7900538381502 | true | 0 | false | 78 | 75 | update |
| 1226 | 1751086925121 | 7900538386880 | 7900538392171 | 7900538386789 | 7900538386789 | true | 0 | false | 75 | 51 | update |
| 1227 | 1751086925223 | 7900538392239 | 7900538396424 | 7900538392171 | 7900538392171 | true | 0 | false | 75 | 42 | update |
| 1228 | 1751086925324 | 7900538396476 | 7900538400658 | 7900538396424 | 7900538396424 | true | 0 | false | 78 | 96 | update |
| 1229 | 1751086925426 | 7900538400769 | 7900538405312 | 7900538400658 | 7900538400658 | true | 0 | false | 69 | 39 | update |
| 1230 | 1751086925529 | 7900538405460 | 7900538409223 | 7900538405312 | 7900538405312 | true | 0 | false | 60 | 45 | update |
| 1231 | 1751086925632 | 7900538409274 | 7900538413339 | 7900538409223 | 7900538409223 | true | 0 | false | 51 | 69 | update |
| 1232 | 1751086925735 | 7900538413423 | 7900538418022 | 7900538413339 | 7900538413339 | true | 0 | false | 96 | 240 | update |
| 1233 | 1751086925837 | 7900538418089 | 7900538421274 | 7900538418022 | 7900538418022 | true | 0 | false | 54 | 69 | update |
| 1234 | 1751086925940 | 7900538421309 | 7900538424345 | 7900538421274 | 7900538421274 | true | 0 | false | 117 | 108 | update |
| 1235 | 1751086926042 | 7900538424388 | 7900538428185 | 7900538424345 | 7900538424345 | true | 0 | false | 72 | 96 | update |
| 1236 | 1751086926148 | 7900538428649 | 7900538433005 | 7900538428185 | 7900538428185 | true | 0 | false | 84 | 72 | update |
| 1237 | 1751086926250 | 7900538433229 | 7900538437278 | 7900538433005 | 7900538433005 | true | 0 | false | 60 | 45 | update |
| 1238 | 1751086926354 | 7900538437389 | 7900538440359 | 7900538437278 | 7900538437278 | true | 0 | false | 36 | 36 | update |

## Source Sequence-Gap Analysis
The strict event-time ordering hits a resync at packet `1218`. The previous packet final_update_id is `7900538334001` and the current packet prev_final_update_id is `7900538333009`. The observed gap size is `992`. A snapshot/reset packet is present immediately before the resync: `True`. Transaction-time ordering removes the gap entirely, so the failure is more consistent with ordering semantics than a hard source gap.

## Alternate Ordering Experiment
| ordering_name | sequence_gap_count | duplicate_final_update_id_count | non_monotonic_event_time_count | first_gap_index | would_resync_be_avoided |
| --- | --- | --- | --- | --- | --- |
| event_time_final_update_id | 1 | 0 | 0 | 1218 | false |
| final_update_id | 1 | 0 | 0 | 1218 | false |
| transaction_time_final_update_id | 0 | 0 | 1 | null | true |
| received_time_final_update_id | 1 | 0 | 1 | 1217 | false |

## Root-Cause Classification
- Classification: `event_ordering_issue`
- Reason: The strict event_time/final_update_id order reproduces the resync, but transaction_time/final_update_id ordering does not. That points to ordering semantics rather than an unavoidable source gap.

## What Worked
- The raw L2 sample was readable and produced `3000` packet(s) for analysis.
- Global packet grouping reproduced the sequence used by the strict reconstruction path.
- The resync was reproduced in the event-time-ordered strict run at packet index `1218`.
- Transaction-time ordering eliminated the resync in the alternate ordering experiment.
- A compact context window around the failure is available in the report.

## What Failed Or Remains Unknown
- The file is not clean under strict event-time ordering; the packet chain fails at the recorded resync point.
- The bounded sample is still a sample, so the tail of the file remains outside this diagnostic.
- This diagnostic does not establish OFI alpha, production readiness, or a broad reconstruction approval.

## What Is Safe
- Read-only packet grouping and strict-sequence reproduction on a bounded sample.
- In-memory alternate ordering experiments.
- Read-only root-cause classification for infrastructure validation.

## What Is Not Safe
- Using this diagnostic as approval to regenerate broader OFI artifacts.
- Treating the sampled file as globally clean or gap-free.
- Using OFI for alpha, paper trading, or live trading.

## Decision
- Decision labels: `resync_reproduced, event_ordering_issue, broader_reconstruction_blocked, targeted_fix_required, alpha_blocked, paper_live_blocked`
- Broader reconstruction approval: `No.`
- OFI alpha approval: `No.`
- OFI paper/live approval: `No.`

## Required Next Step
Use this read-only root-cause result to validate whether transaction-time ordering is the correct packet sequence policy for this source family before any broader reconstruction work. Do not approve broader artifact generation yet.
