# V9.2 Hermes C Exhaustion Richer Context Enriched Decay Diagnostic Closeout

## Executive Decision

- corrected richer-context enriched decay diagnostic completed
- coverage-integrity blocker was fixed
- `local_trend_range_context_degradation_dominant` remains the primary interpretation
- `local_trend_range_state = range` is the best explanatory context
- recent sample is sparse and not stable enough for filter approval
- VWAP discount context remains negative and not filter-approvable
- C Exhaustion remains research anchor only
- no core patch is approved
- no strategy filter is approved
- no paper/live/production approval is granted
- approved state remains `keep_anchor_alive_but_collect_more_inputs`

Final closeout label:

`close_richer_context_decay_branch_keep_anchor_alive_collect_more_inputs`

## Diagnostic Summary

- corrected commit SHA: `6278cf55d902159abf815cb662a24f95af0f3dab`
- report path: `reports/hermes_runs/v92_HERMES_C_EXHAUSTION_RICHER_CONTEXT_ENRICHED_DECAY_DIAGNOSTIC.md`
- previous coverage issue fixed: yes
- interpretation label: `local_trend_range_context_degradation_dominant`
- stop/go label: `keep_anchor_alive_but_collect_more_inputs`
- best explanatory field: `local_trend_range_state`
- best segment: `range`
- segment sparse: yes
- filter design approved: no
- core patch approved: no

## Corrected Coverage Summary

- `trade_density`: valid
- `distance_from_recent_high_low`: valid but not discriminating because all trades fall in the near-recent-low bucket
- `weekday_weekend_effect`: valid but not discriminating because all trades fall in the weekday bucket
- `local_trend_range_state`: valid and explanatory
- `distance_from_vwap`: valid but not sufficient
- `cvd_delta`: valid but sparse on the positive bucket
- `session_time_of_day_labels`: valid but not sufficient alone

## Interpretation

`local_trend_range_state` explains part of the recent C Exhaustion decay better than the prior safe fields. In the corrected diagnostic, the `range` state preserved better recent descriptive expectancy than the broader mixed or range_expansion states, which is the clearest safe known-at-entry signal in the enriched context set.

That is still not enough for filter approval. The recent sample remains small, the positive-tail pattern is still weak, and tail-win compression still exists with recent positive tails absent. The result is historically interesting but still recently unstable.

VWAP discount context remains the weaker stabilising hint rather than a repair path. It stays negative in the recent period and cannot justify a filter.

## Not-Approved Paths

The following remain explicitly not approved:

- core patch
- local_trend_range_state filter
- VWAP discount filter
- range_trend_label = range promotion
- trade_density filter
- CVD / delta filter
- session filter
- weekday / weekend filter
- MFE exit retry
- ML / classifier
- paper / live / production

## Approved Next Action Label

`keep_anchor_alive_but_collect_more_inputs`

## Future Input Collection Recommendation

Future collection should only proceed if the inputs are safe and known at entry. The next useful directions are:

- stronger derivatives context
- funding / open interest / open interest velocity
- liquidation context
- perp basis / premium
- broader market beta / ETH-BTC context
- properly timestamped cross-market regime data

No new diagnostic should be approved until a new input availability or design gate is created first.

## Validation

- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git status --short before work
- git diff --check
- git status --short after work
- confirmed only Hermes Lab files changed
- confirmed core repo was not modified
- no tests required because Markdown-only
