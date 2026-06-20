# V9.2 Hermes Fixed Exit Experiment Result

## Purpose

* Descriptive aggregate result for the single pre-registered fixed running-MFE giveback protection experiment.
* Lab-only execution against the frozen core trade log and bounded 750btc bars.
* No strategy patch, replay patch, optimization, or trading approval.

## Inputs

- trade log: `/home/tokio/tm-trading-v92-core/reports/c_exhaustion_replay_post_regime_fix/trade_log.csv`
- bar dir: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- bars read: `102`
- trades inspected: `310`
- side basis: `long-only (assumed; side column absent)`
- activation threshold: `75 bps running MFE`
- giveback trigger: `current_return_bps <= 0.50 * running_mfe_bps`
- minimum delay: `12` completed bars

## Synthetic Causality Tests

- future-bars-do-not-change-first-trigger: `passed` (baseline_trigger=12.0, future_trigger=12.0)
- minimum-delay-gates-early-bar-activation: `passed` (trigger_completed_bars=12.0)
- no-activation-no-trigger: `passed` (activation and trigger remained false)

## Aggregate Counts

- activated_trades: `211`
- activation_rate: `68.065%`
- triggered_trades: `166`
- trigger_rate_among_activated: `78.673%`
- original giveback_loss triggered: `46` / `125`
- original weak_positive_exit triggered: `44` / `55`
- original clean_winner triggered: `76` / `130`
- original bad_entry_loss triggered: `0` / `0`
- unavailable_or_untriggered_trades: `144`

## Activation Distribution

- mean activation MFE: `186.492 bps`
- median activation MFE: `132.690 bps`
- mean activation delay: `13.986` completed bars
- median activation delay: `12.000` completed bars

## Trigger Distribution

- mean trigger return: `35.217 bps`
- median trigger return: `42.730 bps`
- mean trigger MFE: `184.077 bps`
- median trigger MFE: `155.709 bps`
- mean giveback magnitude: `148.860 bps`
- median giveback magnitude: `122.495 bps`
- mean delay-to-trigger: `16.873` completed bars
- median delay-to-trigger: `13.000` completed bars

## Triggered Trade Return Distributions

| metric | gross | net |
| --- | --- | --- |
| triggered | mean=74.075 bps, median=75.662 bps, count=166 | mean=62.075 bps, median=63.662 bps, count=166 |
| not_triggered | mean=35.170 bps, median=-7.012 bps, count=144 | mean=23.170 bps, median=-19.012 bps, count=144 |

## Mechanical Fixed-Exit Comparison

- synthetic gross mean: `35.195 bps`
- synthetic gross median: `31.519 bps`
- synthetic net mean: `23.195 bps`
- synthetic net median: `19.519 bps`
- original gross mean: `56.003 bps`
- original gross median: `45.124 bps`
- original net mean: `44.003 bps`
- original net median: `33.124 bps`

### Original To Synthetic Class Transition Table

| original_final_class | synthetic_final_class | count |
| --- | --- | --- |
| clean_winner | clean_winner | 54 |
| clean_winner | giveback_loss | 10 |
| clean_winner | weak_positive_exit | 66 |
| giveback_loss | giveback_loss | 104 |
| giveback_loss | weak_positive_exit | 21 |
| weak_positive_exit | giveback_loss | 6 |
| weak_positive_exit | weak_positive_exit | 49 |

## By-Year Results

| year | trades | activated | triggered | activation_rate | trigger_rate | original_mean_return_bps | original_median_return_bps | synthetic_mean_return_bps | synthetic_median_return_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 20 | 16 | 0.952 | 0.762 | 103.086 | 123.138 | 85.063 | 54.224 |
| 2021 | 82 | 67 | 53 | 0.817 | 0.646 | 148.328 | 119.062 | 91.834 | 46.004 |
| 2022 | 83 | 54 | 40 | 0.651 | 0.482 | 16.204 | 25.778 | 10.313 | 32.682 |
| 2023 | 73 | 30 | 22 | 0.411 | 0.301 | 11.522 | 13.396 | 0.959 | 13.396 |
| 2024 | 26 | 23 | 18 | 0.885 | 0.692 | 125.606 | 134.030 | 69.512 | 30.052 |
| 2025 | 16 | 10 | 10 | 0.625 | 0.625 | -148.752 | -182.859 | -56.166 | 2.054 |
| 2026 | 9 | 7 | 7 | 0.778 | 0.778 | -4.282 | 64.321 | -26.745 | 19.313 |

## Leakage and Bias Checks

* Bars were evaluated only up to each trade's original exit boundary.
* Trigger logic used running highs and bar closes accumulated sequentially inside the original trade window.
* Synthetic tests verified that later bars outside the original trade window do not change the trigger result.
* The minimum delay gate prevented early activation before the preregistered bar count.
* No raw L2 data, OFI features, parameter sweeps, or replay patches were used.

## Stop / Go Conclusion

- decision: `proceed_to_review_fixed_giveback_results`
- conclusion: The fixed rule is causally implementable bar by bar and the result is evaluable as a descriptive aggregate comparison.

## Decision Inputs

- original giveback_loss count: `125`
- triggered giveback_loss count: `46`
- triggered clean_winner count: `76`
- triggered weak_positive_exit count: `44`
- triggered bad_entry_loss count: `0`
- 2025 triggered trades: `10`
- 2026 triggered trades: `7`

