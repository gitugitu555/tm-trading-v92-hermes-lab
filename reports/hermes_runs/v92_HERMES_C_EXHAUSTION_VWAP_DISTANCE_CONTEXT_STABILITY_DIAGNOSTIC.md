# V9.2 Hermes C Exhaustion VWAP Distance Context Stability Diagnostic

## Purpose

- Test whether `distance_from_vwap = -100 to -25 bps` is stable enough to justify a later context-filter preregistration.
- Aggregate-only diagnostic against the frozen core replay output and bounded 750btc bars.
- No strategy patch, replay patch, parameter search, classifier, raw L2, OFI, modeling dataset, or trading approval.

## Population Accounting

- total C Exhaustion trades inspected: `310`
- trades with safe distance_from_vwap available: `310`
- historical count: `285`
- recent count: `25`
- by-year count: `2020:21, 2021:82, 2022:83, 2023:73, 2024:26, 2025:16, 2026:9`

### VWAP Bin Counts

| bucket | count |
| --- | --- |
| below -100 bps | 3 |
| -100 to -25 bps | 126 |
| -25 to +25 bps | 181 |
| +25 to +100 bps | 0 |
| above +100 bps | 0 |

## Segment Comparison

| bucket | historical_expectancy_bps | recent_expectancy_bps | full_sample_expectancy_bps | historical_win_rate | recent_win_rate | average_winner_bps | average_loser_bps | positive_tail_frequency | large_loss_frequency | p10_return_bps | p25_return_bps | median_return_bps | p75_return_bps | p90_return_bps | gross_expectancy_bps | net_expectancy_bps | degradation_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| below -100 bps | 314.199 | n/a | 314.199 | 1.000 | n/a | 314.199 | n/a | 0.667 | 0.000 | 116.573 | 202.997 | 347.036 | 441.819 | 498.689 | 326.199 | 314.199 | n/a |
| -100 to -25 bps | 105.360 | -83.101 | 84.420 | 0.607 | 0.429 | 264.651 | -172.064 | 0.254 | 0.159 | -255.525 | -104.839 | 42.082 | 200.696 | 445.155 | 96.420 | 84.420 | -188.460 |
| -25 to +25 bps | 21.274 | -141.378 | 11.390 | 0.565 | 0.273 | 134.754 | -137.551 | 0.144 | 0.110 | -231.653 | -83.225 | 24.240 | 95.866 | 226.174 | 23.390 | 11.390 | -162.652 |
| +25 to +100 bps | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| above +100 bps | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Target-Segment Stability

| historical_count | recent_count | by_year_count | by_year_expectancy | by_year_win_rate | positive_expectancy_years | year_isolated | recent_sample_sufficient | positive_tail_compression_remains | tail_loss_expansion_remains | average_loser_worsened | large_loss_frequency_worsened | dominant_year_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 112 | 14 | 2020:7, 2021:49, 2022:26, 2023:12, 2024:18, 2025:8, 2026:6 | 2020:219.267, 2021:163.345, 2022:-14.089, 2023:23.212, 2024:130.515, 2025:-185.022, 2026:52.795 | 2020:85.71%, 2021:63.27%, 2022:42.31%, 2023:58.33%, 2024:72.22%, 2025:25.00%, 2026:66.67% | 5 | 0 | 1 | 1 | 0 | 0 | 0 | 0.389 |

## Comparison Versus Full Recent Sample

| recent_expectancy_delta | recent_win_rate_delta | positive_tail_frequency_delta | large_loss_frequency_delta | average_winner_delta | average_loser_delta | net_expectancy_delta |
| --- | --- | --- | --- | --- | --- | --- |
| 25.642 | 0.069 | 0.000 | -0.043 | -4.063 | 9.982 | 25.642 |

## Sparse Alternative Control

- count: `0`
- recent count: `0`
- year concentration: `n/a`
- sparse status: `sparse`
- no filter approval

## Synthetic Causality / Leakage Checks

- distance_from_vwap-known-at-entry: `passed` (distance_from_vwap=59.1715976331364)
- bins-fixed-and-preregistered: `passed` (VWAP bins map deterministically)
- return-outcomes-post-hoc-only: `passed` (outcomes changed without affecting entry-context fields)
- raw-L2-OFI-row-level-blocked: `passed` (no raw L2 read; OFI not generated; no row-level export)
- distance_from_vwap is known at or before entry
- VWAP bins are fixed and preregistered
- no future returns are used for eligibility
- outcomes are used only for aggregate attribution
- no raw L2 is read
- OFI is not generated
- no row-level artifacts are exported
- no modeling dataset is created
- core repo is not modified

## Interpretation

- interpretation label: `vwap_discount_segment_stable_descriptive_edge`
- target recent expectancy: `-83.101` bps
- full recent C Exhaustion expectancy: `-108.743` bps
- target recent trade count: `14`
- target beats full recent sample: `1`
- target is year-isolated: `0`
- tail-loss expansion acceptable: `1`
- proceed_to_vwap_context_filter_preregistration_design_only allowed: `0`

## Stop / Go Conclusion

- decision: `keep_anchor_alive_but_collect_more_inputs`
- no segment is approved for strategy use in this diagnostic.

