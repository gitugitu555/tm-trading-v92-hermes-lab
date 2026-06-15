# V9.2 L2 OFI Dirty Transaction-Time File Diagnostic

## Purpose
Diagnose why the remaining dirty transaction-time file still hits a strict-sequence resync under transaction-time ordering.

## Inputs
- Input file: `/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2025-08-28/09/BTCUSDT_orderbook.parquet.zst`
- Expected resync index: `4293`
- Context before: `30`
- Context after: `30`
- Max events scanned: `7000`
- Symbol filter: `BTCUSDT`

## Read-Only Guardrails
This diagnostic only reads source data and writes the markdown report. It does not regenerate OFI or bars, and it does not write any OFI artifact to disk.
This diagnostic does not approve OFI for production, paper trading, live trading, or alpha use.

## Executive Finding
Transaction-time ordering still reproduces a strict-sequence resync at packet index `4293`. The resync is not explained away by snapshot/reset semantics, and the ordering experiment indicates this dirty file remains a true failing sample under transaction-time reconstruction.

## Reproduction Summary
| rows_scanned | packet_count | processed_event_count | ofi_emitted_count | warmup_none_count | sequence_gap_count | snapshot_or_reset_event_count | resync_stop_event_index | expected_resync_index | resync_index_matches_expectation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 362040 | 7000 | 4293 | 4291 | 1 | 1 | 0 | 4293 | 4293 | true |

## Packet Schema Summary
| rows_scanned | packet_count | bad_key_row_count | bad_cast_row_count | unknown_side_row_count | packet_boundary_unknown | dropped_last_packet_for_boundary_safety | rows_have_price_and_quantity_strings | event_time_is_microseconds | final_update_id_present | first_update_id_null_in_some_packets | prev_final_update_id_null_in_some_packets | transaction_time_present_in_some_packets | received_time_present_in_some_packets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 362040 | 7000 | 0 | 0 | 0 | false | 0 | true | true | true | false | false | true | true |

## Dirty File Resync Event Summary
| resync_packet_index | engine_last_update_id_before | engine_last_update_id_after | previous_packet_final_update_id | current_packet_prev_final_update_id | current_packet_is_snapshot_or_reset | current_packet_event_time | current_packet_event_type | sequence_gap_count | snapshot_or_reset_event_count | warmup_none_count | ofi_emitted_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4293 | 8459829013238 | 8459829013238 | 8459829013238 | -1 | false | 1756371835884 | update | 1 | 0 | 1 | 4291 |

## Context Window Around Transaction-Time Resync
| packet_index | transaction_time_min | transaction_time_max | event_time | first_update_id | final_update_id | prev_final_update_id | expected_prev_final_update_id | matches_previous_final_update_id | sequence_gap_size | first_update_gap_from_prev | update_range_overlap_with_prev | is_snapshot_or_reset | bid_level_count | ask_level_count | event_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4263 | 1756371821467 | 1756371821467 | 1756371821467 | 8459828872742 | 8459828875701 | 8459828872632 | 8459828872632 | true | 0 | 110 | false | false | 14 | 20 | update |
| 4264 | 1756371821515 | 1756371821515 | 1756371821519 | 8459828875736 | 8459828878566 | 8459828875701 | 8459828875701 | true | 0 | 35 | false | false | 16 | 11 | update |
| 4265 | 1756371821570 | 1756371821570 | 1756371821570 | 8459828878679 | 8459828880913 | 8459828878566 | 8459828878566 | true | 0 | 113 | false | false | 8 | 11 | update |
| 4266 | 1756371821621 | 1756371821621 | 1756371821621 | 8459828880925 | 8459828883549 | 8459828880913 | 8459828880913 | true | 0 | 12 | false | false | 11 | 10 | update |
| 4267 | 1756371821672 | 1756371821672 | 1756371821673 | 8459828883598 | 8459828885564 | 8459828883549 | 8459828883549 | true | 0 | 49 | false | false | 9 | 7 | update |
| 4268 | 1756371821722 | 1756371821722 | 1756371821724 | 8459828885565 | 8459828887606 | 8459828885564 | 8459828885564 | true | 0 | 1 | false | false | 10 | 7 | update |
| 4269 | 1756371821773 | 1756371821773 | 1756371821776 | 8459828887676 | 8459828889267 | 8459828887606 | 8459828887606 | true | 0 | 70 | false | false | 12 | 7 | update |
| 4270 | 1756371821828 | 1756371821828 | 1756371821830 | 8459828889381 | 8459828891402 | 8459828889267 | 8459828889267 | true | 0 | 114 | false | false | 13 | 14 | update |
| 4271 | 1756371821881 | 1756371821881 | 1756371821881 | 8459828891455 | 8459828894919 | 8459828891402 | 8459828891402 | true | 0 | 53 | false | false | 20 | 9 | update |
| 4272 | 1756371821933 | 1756371821933 | 1756371821933 | 8459828895036 | 8459828898469 | 8459828894919 | 8459828894919 | true | 0 | 117 | false | false | 13 | 7 | update |
| 4273 | 1756371821983 | 1756371821983 | 1756371821984 | 8459828898479 | 8459828901020 | 8459828898469 | 8459828898469 | true | 0 | 10 | false | false | 11 | 5 | update |
| 4274 | 1756371822034 | 1756371822034 | 1756371822035 | 8459828901106 | 8459828904036 | 8459828901020 | 8459828901020 | true | 0 | 86 | false | false | 18 | 18 | update |
| 4275 | 1756371822086 | 1756371822086 | 1756371822087 | 8459828904117 | 8459828906792 | 8459828904036 | 8459828904036 | true | 0 | 81 | false | false | 19 | 24 | update |
| 4276 | 1756371822139 | 1756371822139 | 1756371822139 | 8459828906899 | 8459828909510 | 8459828906792 | 8459828906792 | true | 0 | 107 | false | false | 14 | 16 | update |
| 4277 | 1756371822182 | 1756371822182 | 1756371822192 | 8459828909579 | 8459828910950 | 8459828909510 | 8459828909510 | true | 0 | 69 | false | false | 14 | 8 | update |
| 4278 | 1756371822243 | 1756371822243 | 1756371822244 | 8459828911326 | 8459828913469 | 8459828910950 | 8459828910950 | true | 0 | 376 | false | false | 18 | 13 | update |
| 4279 | 1756371822296 | 1756371822296 | 1756371822296 | 8459828913591 | 8459828915354 | 8459828913469 | 8459828913469 | true | 0 | 122 | false | false | 14 | 13 | update |
| 4280 | 1756371822342 | 1756371822342 | 1756371822347 | 8459828915364 | 8459828917613 | 8459828915354 | 8459828915354 | true | 0 | 10 | false | false | 15 | 12 | update |
| 4281 | 1756371822399 | 1756371822399 | 1756371822400 | 8459828917896 | 8459828919610 | 8459828917613 | 8459828917613 | true | 0 | 283 | false | false | 22 | 21 | update |
| 4282 | 1756371822452 | 1756371822452 | 1756371822453 | 8459828919776 | 8459828921557 | 8459828919610 | 8459828919610 | true | 0 | 166 | false | false | 18 | 10 | update |
| 4283 | 1756371822505 | 1756371822505 | 1756371822506 | 8459828921623 | 8459828924389 | 8459828921557 | 8459828921557 | true | 0 | 66 | false | false | 16 | 22 | update |
| 4284 | 1756371822559 | 1756371822559 | 1756371822559 | 8459828924553 | 8459828926932 | 8459828924389 | 8459828924389 | true | 0 | 164 | false | false | 16 | 18 | update |
| 4285 | 1756371822607 | 1756371822607 | 1756371822611 | 8459828926985 | 8459828929262 | 8459828926932 | 8459828926932 | true | 0 | 53 | false | false | 13 | 11 | update |
| 4286 | 1756371822661 | 1756371822661 | 1756371822663 | 8459828929418 | 8459828931767 | 8459828929262 | 8459828929262 | true | 0 | 156 | false | false | 14 | 14 | update |
| 4287 | 1756371822714 | 1756371822714 | 1756371822716 | 8459828931880 | 8459828933928 | 8459828931767 | 8459828931767 | true | 0 | 113 | false | false | 10 | 7 | update |
| 4288 | 1756371822768 | 1756371822768 | 1756371822768 | 8459828934044 | 8459828945821 | 8459828933928 | 8459828933928 | true | 0 | 116 | false | false | 111 | 64 | update |
| 4289 | 1756371822818 | 1756371822818 | 1756371822819 | 8459828945865 | 8459828964962 | 8459828945821 | 8459828945821 | true | 0 | 44 | false | false | 107 | 86 | update |
| 4290 | 1756371822869 | 1756371822869 | 1756371822870 | 8459828965022 | 8459828984201 | 8459828964962 | 8459828964962 | true | 0 | 60 | false | false | 78 | 81 | update |
| 4291 | 1756371822921 | 1756371822921 | 1756371822921 | 8459828984241 | 8459829004277 | 8459828984201 | 8459828984201 | true | 0 | 40 | false | false | 76 | 52 | update |
| 4292 | 1756371822955 | 1756371822955 | 1756371822972 | 8459829004281 | 8459829013238 | 8459829004277 | 8459829004277 | true | 0 | 4 | false | false | 26 | 19 | update |
| 4293 | 1756371835882 | 1756371835882 | 1756371835884 | 8459829498784 | 8459829692989 | -1 | 8459829013238 | false | 8459829013239 | 485546 | false | false | 501 | 503 | update |
| 4294 | 1756371835935 | 1756371835935 | 1756371835936 | 8459829693311 | 8459829701560 | 8459829692989 | 8459829692989 | true | 0 | 322 | false | false | 806 | 808 | update |
| 4295 | 1756371835987 | 1756371835987 | 1756371835987 | 8459829701577 | 8459829706284 | 8459829701560 | 8459829701560 | true | 0 | 17 | false | false | 38 | 36 | update |
| 4296 | 1756371836038 | 1756371836038 | 1756371836038 | 8459829706316 | 8459829710868 | 8459829706284 | 8459829706284 | true | 0 | 32 | false | false | 24 | 32 | update |
| 4297 | 1756371836089 | 1756371836089 | 1756371836090 | 8459829710922 | 8459829715313 | 8459829710868 | 8459829710868 | true | 0 | 54 | false | false | 30 | 7 | update |
| 4298 | 1756371836143 | 1756371836143 | 1756371836144 | 8459829715592 | 8459829720232 | 8459829715313 | 8459829715313 | true | 0 | 279 | false | false | 17 | 20 | update |
| 4299 | 1756371836197 | 1756371836197 | 1756371836197 | 8459829720472 | 8459829725926 | 8459829720232 | 8459829720232 | true | 0 | 240 | false | false | 30 | 49 | update |
| 4300 | 1756371836247 | 1756371836247 | 1756371836249 | 8459829726002 | 8459829732923 | 8459829725926 | 8459829725926 | true | 0 | 76 | false | false | 43 | 35 | update |
| 4301 | 1756371836300 | 1756371836300 | 1756371836301 | 8459829733127 | 8459829739365 | 8459829732923 | 8459829732923 | true | 0 | 204 | false | false | 81 | 80 | update |
| 4302 | 1756371836352 | 1756371836352 | 1756371836353 | 8459829739749 | 8459829746924 | 8459829739365 | 8459829739365 | true | 0 | 384 | false | false | 44 | 36 | update |
| 4303 | 1756371836404 | 1756371836404 | 1756371836406 | 8459829747734 | 8459829756203 | 8459829746924 | 8459829746924 | true | 0 | 810 | false | false | 79 | 64 | update |
| 4304 | 1756371836453 | 1756371836453 | 1756371836459 | 8459829756753 | 8459829762872 | 8459829756203 | 8459829756203 | true | 0 | 550 | false | false | 30 | 24 | update |
| 4305 | 1756371836507 | 1756371836507 | 1756371836510 | 8459829763557 | 8459829770671 | 8459829762872 | 8459829762872 | true | 0 | 685 | false | false | 13 | 12 | update |
| 4306 | 1756371836560 | 1756371836560 | 1756371836563 | 8459829771359 | 8459829784062 | 8459829770671 | 8459829770671 | true | 0 | 688 | false | false | 16 | 26 | update |
| 4307 | 1756371836613 | 1756371836613 | 1756371836615 | 8459829784681 | 8459829791175 | 8459829784062 | 8459829784062 | true | 0 | 619 | false | false | 12 | 24 | update |
| 4308 | 1756371836665 | 1756371836665 | 1756371836666 | 8459829791250 | 8459829796722 | 8459829791175 | 8459829791175 | true | 0 | 75 | false | false | 64 | 95 | update |
| 4309 | 1756371836715 | 1756371836715 | 1756371836719 | 8459829797105 | 8459829802277 | 8459829796722 | 8459829796722 | true | 0 | 383 | false | false | 64 | 17 | update |
| 4310 | 1756371836766 | 1756371836766 | 1756371836770 | 8459829802517 | 8459829806345 | 8459829802277 | 8459829802277 | true | 0 | 240 | false | false | 15 | 7 | update |
| 4311 | 1756371836821 | 1756371836821 | 1756371836822 | 8459829806933 | 8459829811179 | 8459829806345 | 8459829806345 | true | 0 | 588 | false | false | 12 | 8 | update |
| 4312 | 1756371836873 | 1756371836873 | 1756371836873 | 8459829811300 | 8459829815877 | 8459829811179 | 8459829811179 | true | 0 | 121 | false | false | 16 | 5 | update |
| 4313 | 1756371836922 | 1756371836922 | 1756371836924 | 8459829815878 | 8459829820316 | 8459829815877 | 8459829815877 | true | 0 | 1 | false | false | 17 | 14 | update |
| 4314 | 1756371836973 | 1756371836973 | 1756371836977 | 8459829820783 | 8459829824666 | 8459829820316 | 8459829820316 | true | 0 | 467 | false | false | 4 | 2 | update |
| 4315 | 1756371837027 | 1756371837027 | 1756371837028 | 8459829824912 | 8459829829940 | 8459829824666 | 8459829824666 | true | 0 | 246 | false | false | 46 | 16 | update |
| 4316 | 1756371837079 | 1756371837079 | 1756371837079 | 8459829829945 | 8459829836833 | 8459829829940 | 8459829829940 | true | 0 | 5 | false | false | 50 | 37 | update |
| 4317 | 1756371837127 | 1756371837127 | 1756371837131 | 8459829837032 | 8459829842238 | 8459829836833 | 8459829836833 | true | 0 | 199 | false | false | 11 | 9 | update |
| 4318 | 1756371837182 | 1756371837182 | 1756371837184 | 8459829842767 | 8459829847277 | 8459829842238 | 8459829842238 | true | 0 | 529 | false | false | 39 | 35 | update |
| 4319 | 1756371837224 | 1756371837224 | 1756371837236 | 8459829847430 | 8459829850922 | 8459829847277 | 8459829847277 | true | 0 | 153 | false | false | 8 | 2 | update |
| 4320 | 1756371837288 | 1756371837288 | 1756371837288 | 8459829851927 | 8459829854960 | 8459829850922 | 8459829850922 | true | 0 | 1005 | false | false | 8 | 3 | update |
| 4321 | 1756371837339 | 1756371837339 | 1756371837341 | 8459829855046 | 8459829857984 | 8459829854960 | 8459829854960 | true | 0 | 86 | false | false | 8 | 4 | update |
| 4322 | 1756371837393 | 1756371837393 | 1756371837394 | 8459829858224 | 8459829861818 | 8459829857984 | 8459829857984 | true | 0 | 240 | false | false | 28 | 10 | update |
| 4323 | 1756371837444 | 1756371837444 | 1756371837445 | 8459829861819 | 8459829865864 | 8459829861818 | 8459829861818 | true | 0 | 1 | false | false | 38 | 31 | update |

## Alternate Ordering Experiment
| ordering_name | sequence_gap_count | first_gap_index | duplicate_final_update_id_count | non_monotonic_event_time_count | non_monotonic_transaction_time_count | would_resync_be_avoided |
| --- | --- | --- | --- | --- | --- | --- |
| transaction_time_final_update_id | 1 | 4293 | 0 | 0 | 0 | false |
| event_time_final_update_id | 1 | 4293 | 0 | 0 | 0 | false |
| final_update_id | 1 | 4293 | 0 | 0 | 0 | false |
| received_time_final_update_id | 1 | 4293 | 0 | 0 | 0 | false |

## Root-Cause Classification
- Classification: `source_sequence_gap`
- Reason: All tested orderings show the same prev/final mismatch at the resync boundary.

## Segmentability Check
| segment_before_gap_packet_count | segment_after_gap_packet_count | segment_before_ofi_emitted_count | segment_after_ofi_emitted_count | segment_before_clean | segment_after_clean | segmented_reconstruction_possible | before_run | after_run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4292 | 2708 | 4291 | 2707 | true | true | true | {'processed_event_count': 4292, 'ofi_emitted_count': 4291, 'warmup_none_count': 1, 'snapshot_or_reset_event_count': 0, 'sequence_gap_count': 0, 'resync_stop_event_index': None, 'engine_last_update_id_before': None, 'engine_last_update_id_after': None, 'engine_completed_sample': True} | {'processed_event_count': 2708, 'ofi_emitted_count': 2707, 'warmup_none_count': 1, 'snapshot_or_reset_event_count': 0, 'sequence_gap_count': 0, 'resync_stop_event_index': None, 'engine_last_update_id_before': None, 'engine_last_update_id_after': None, 'engine_completed_sample': True} |

## What Worked
- The dirty file was readable and packet grouping could be reconstructed.
- Transaction-time ordering reproduced the strict-sequence failure at the expected packet index.
- The alternate ordering experiment was completed in memory.
- A transaction-time OFI rehearsal ran until the resync point without writing artifacts to disk.

## What Failed Or Remains Unknown
- The dirty file is not clean under transaction-time ordering.
- At least one packet chain mismatch remains in the sample.
- This diagnostic does not establish OFI alpha or broader reconstruction approval.
- The transaction-time rehearsal stopped at packet index `4293`.

## What Is Safe
- Read-only root-cause diagnosis on a bounded sample.
- In-memory packet ordering comparison.
- Strict transaction-time OFI rehearsal without output artifacts.

## What Is Not Safe
- Using this diagnostic to globally approve transaction-time reconstruction.
- Treating the dirty file as broadly clean.
- Using OFI for alpha, paper trading, or live trading.

## Decision
- Decision labels: `transaction_time_resync_reproduced, source_sequence_gap, broader_reconstruction_blocked, alpha_blocked, paper_live_blocked, segmented_reconstruction_candidate, dirty_file_segmentable`
- Broader reconstruction approval: `No.`
- OFI alpha approval: `No.`
- OFI paper/live approval: `No.`

## Required Next Step
If a second bounded sample also shows a clean transaction-time split around one source gap, only then consider a segmented reconstruction candidate. Do not promote broader OFI reconstruction yet.
