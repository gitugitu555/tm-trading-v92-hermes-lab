# V9.2 Hermes Fixed Running-MFE Giveback Protection Review Memo

## Scope

This memo reviews commit `4745a419223caaafcca17c5e35084d361612c431` using the existing lab-only result report at [reports/hermes_runs/v92_HERMES_FIXED_RUNNING_MFE_GIVEBACK_PROTECTION_EXPERIMENT.md](/home/tokio/tm-trading-v92-hermes-lab/reports/hermes_runs/v92_HERMES_FIXED_RUNNING_MFE_GIVEBACK_PROTECTION_EXPERIMENT.md), the experiment script at [scripts/v92_fixed_running_mfe_giveback_protection_experiment.py](/home/tokio/tm-trading-v92-hermes-lab/scripts/v92_fixed_running_mfe_giveback_protection_experiment.py), and the focused test at [tests/test_fixed_running_mfe_giveback_protection_experiment.py](/home/tokio/tm-trading-v92-hermes-lab/tests/test_fixed_running_mfe_giveback_protection_experiment.py).

The existing report already contains the trigger counts, the triggered-versus-not-triggered return distributions, the class transition table, and the by-year tables. This memo converts those aggregates into strict economic attribution.

## Review Outcome

### A. Aggregate improvement

No. The fixed rule reduced aggregate realized return versus original exits.

- Original gross aggregate return: `17,360.963 bps`
- Mechanical gross aggregate return: `10,910.569 bps`
- Gross delta: `-6,450.394 bps`
- Original net aggregate return: `13,640.963 bps`
- Mechanical net aggregate return: `7,190.569 bps`
- Net delta: `-6,450.394 bps`

The rule is not economically accretive on the full sample.

### B. Rescue from giveback losses

The rule rescued realized return from the original giveback-loss trades that triggered.

- Triggered giveback-loss count: `46`
- Original gross aggregate return: `-7,260.984 bps`
- Mechanical gross aggregate return: `-1,274.704 bps`
- Gross delta: `+5,986.279 bps`
- Average bps delta per trade: `+130.137 bps`
- Median bps delta per trade: `+161.191 bps`

Net attribution is identical here:

- Original net aggregate return: `-7,812.984 bps`
- Mechanical net aggregate return: `-1,826.704 bps`
- Net delta: `+5,986.279 bps`

### C. Clipping cost from clean winners

The rule gave back more than it rescued by clipping original clean winners that triggered.

- Triggered clean-winner count: `76`
- Original gross aggregate return: `16,411.363 bps`
- Mechanical gross aggregate return: `4,017.008 bps`
- Gross delta: `-12,394.355 bps`
- Average bps delta per trade: `-163.084 bps`
- Median bps delta per trade: `-127.587 bps`

Net attribution is identical here:

- Original net aggregate return: `15,499.363 bps`
- Mechanical net aggregate return: `3,105.008 bps`
- Net delta: `-12,394.355 bps`

### D. Net delta definition

The strict attribution delta is:

`mechanical_exit_return_bps - original_return_bps`

On the full 310-trade sample:

- Net delta: `-6,450.394 bps`
- Average delta per trade: `-20.8087 bps`

## Attribution By Original Class

The net delta by original class is basis-invariant here, so the gross and net deltas match.

| Original class | Count | Original aggregate return | Mechanical aggregate return | Net delta | Avg delta / trade | Median delta / trade |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| giveback_loss | 125 | -18,689.076 bps | -12,702.797 bps | +5,986.279 bps | +47.890 bps | 0.000 bps |
| clean_winner | 130 | 32,750.600 bps | 20,356.246 bps | -12,394.355 bps | -95.341 bps | -27.445 bps |
| weak_positive_exit | 55 | 3,299.439 bps | 3,257.121 bps | -42.318 bps | -0.769 bps | 0.000 bps |
| bad_entry_loss | 0 | 0.000 bps | 0.000 bps | 0.000 bps | n/a | n/a |
| unresolved | 0 | 0.000 bps | 0.000 bps | 0.000 bps | n/a | n/a |

The clean-winner clipping cost is larger than the giveback-loss rescue benefit by `6,408.076 bps` at the class level.

## Attribution By Year

| Year | Count | Original aggregate return | Mechanical aggregate return | Net delta | Avg delta / trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 21 | 2,164.807 bps | 1,786.313 bps | -378.494 bps | -18.024 bps |
| 2021 | 82 | 12,162.933 bps | 7,530.351 bps | -4,632.582 bps | -56.495 bps |
| 2022 | 83 | 1,344.942 bps | 855.966 bps | -488.976 bps | -5.891 bps |
| 2023 | 73 | 841.080 bps | 69.990 bps | -771.090 bps | -10.563 bps |
| 2024 | 26 | 3,265.765 bps | 1,807.306 bps | -1,458.459 bps | -56.095 bps |
| 2025 | 16 | -2,380.025 bps | -898.655 bps | +1,481.370 bps | +92.586 bps |
| 2026 | 9 | -38.539 bps | -240.702 bps | -202.162 bps | -22.462 bps |

## Concentration Check

The only positive yearly attribution is `2025`, which is the recent decay period already highlighted in the core diagnostic history. That said, the benefit is not stable:

- `2020-2024` are all net negative.
- `2026` is also net negative.
- `2025` alone is positive, but its gain is too small to offset the clean-winner clipping cost and the broader historical drag.

So the effect is concentrated in one recent year, not distributed robustly across the sample.

## False-Positive Section

Damage from the `76 / 130` original clean winners that triggered:

- Count: `76`
- Original aggregate return: `16,411.363 bps`
- Mechanical aggregate return: `4,017.008 bps`
- Aggregate bps delta: `-12,394.355 bps`
- Average bps delta per trade: `-163.084 bps`
- Median bps delta per trade: `-127.587 bps`

This is the dominant economic failure mode.

## Rescue Section

Benefit from the `46 / 125` original giveback losses that triggered:

- Count: `46`
- Original aggregate return: `-7,260.984 bps`
- Mechanical aggregate return: `-1,274.704 bps`
- Aggregate bps delta: `+5,986.279 bps`
- Average bps delta per trade: `+130.137 bps`
- Median bps delta per trade: `+161.191 bps`

This is real rescue, but it is smaller than the clean-winner clipping cost.

## Review of the Existing Report

The primary report sections that support this memo are:

- `Aggregate Counts`
- `Triggered Trade Return Distributions`
- `Mechanical Fixed-Exit Comparison`
- `Original To Synthetic Class Transition Table`
- `By-Year Results`

Those sections are enough to validate the trigger counts and the direction of the effect; this memo adds the strict economic attribution sums and deltas.

## Stop / Go Conclusion

`reject_fixed_giveback_rule_as_net_destructive`

Reason: the fixed rule is mechanically implementable and it does rescue some giveback losses, but the clean-winner clipping cost is larger than the rescue benefit by a wide margin. The net effect is economically destructive on the full sample.
