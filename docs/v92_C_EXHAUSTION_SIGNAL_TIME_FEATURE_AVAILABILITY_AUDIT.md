# V9.2 C_Exhaustion Signal-Time Feature Availability Audit

## Purpose

Identify which existing repo features are available at C_Exhaustion signal time, which are leakage-safe when shifted, and which remain blocked by unapproved OFI/L2 artifacts or missing historical sources.

## Inputs

- Audit mode: `static-only audit`
- Repo root: `/home/tokio/tm-trading-v92-core`
- Static signal-source files found: `6`

## Read-Only Guardrails

- No raw L2 data was read.
- No OFI artifacts were read.
- No OFI artifacts were written.
- No market-data artifacts were written.
- No strategy backtest was run.
- No alpha claim is made.
- Full reconstruction remains blocked.

## C_Exhaustion Signal Source

The signal path is defined in `replays/c_exhaustion_replay.py`, where `attach_c_exhaustion_signal` builds the past-only `c_signal` and `replay_c_exhaustionfade` converts signal bars into trades with `signal_time`, `entry_time`, and `exit_time`.
The replay consumes `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`, `regime`, `vol_roll_95`, and `local_low`. `run_c_exhaustion_replay.py` is the CLI entry point, while the diagnostics scripts reconstruct the same signal set for attribution and meta-label research.

## Current Signal-Time Columns / Inputs

- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `regime`
- `vol_roll_95`
- `local_low`
- `c_signal`
- `signal_index`
- `entry_index`
- `exit_index`
- `signal_time`
- `entry_time`
- `exit_time`

## Static Feature Inventory

| feature family | implementation files | feature examples | consumed by C_Exhaustion replay? | consumed by C_Exhaustion diagnostics? | requires trades? | requires L2? | requires approved OFI artifact? | current eligibility | leakage notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OHLCV / regime | replays/c_exhaustion_replay.py, features/regime_classifier.py, features/contextual_filters.py, features/market_structure.py | open, high, low, close, volume, regime, local_low, vol_roll_95 | yes | yes | no | no | no | available_now | safe when based on completed bars and properly shifted rolling windows |
| volume_delta / signed-flow | features/trade_signing.py, features/cvd.py, features/delta.py | volume_delta, delta, cvd, velocity, acceleration, signed side | no | yes | yes | no | no | available_with_existing_trade_columns | safe only if sourced from past trades or precomputed bar columns with signal-time alignment |
| absorption proxy | features/absorption.py | ask absorption, bid absorption, delta threshold, price move | no | yes | yes | no | no | available_with_existing_trade_columns | requires a strict past-only window and no post-signal price movement |
| VPIN / toxicity | features/vpin.py | vpin_level, vpin_slope, toxicity_state, toxicity_score | no | yes | yes | no | no | available_with_existing_trade_columns | safe only with past-only buckets or completed bar splits |
| footprint | features/footprint.py | buy_volume, sell_volume, delta, total_volume by price level | no | no | yes | no | no | available_with_existing_trade_columns | requires strict binning at or before signal time |
| microstructure / book state | features/microprice.py, features/queue_imbalance.py, features/l2_imbalance.py | microprice, spread_bps, depth_top5, depth_top10, weighted_imbalance | no | yes | no | yes | yes | blocked_by_ofi_l2_approval | needs L2 snapshots with no future-book contamination |
| OFI / MLOFI | features/microstructure_ofi.py, features/microstructure_numba_ofi.py, features/mlofi.py | ofi, mlofi_weighted_aggregate, book_trap_score, book_agreement_score | no | yes | no | yes | yes | blocked_by_ofi_l2_approval | blocked until approved OFI artifacts and historical provenance are available |
| spoofing / iceberg / whale pressure | features/spoofing.py, features/iceberg.py, features/whale.py, features/large_prints.py | spoof candidate, iceberg candidate, whale pressure, large print z-score | no | yes | yes | yes | no | blocked_by_missing_historical_source | needs verified historical event coverage and stable timestamp ordering |
| funding / OI / liquidation / basis | none | funding, open interest, liquidation, crowding, basis | no | no | no | no | no | blocked_by_missing_historical_source | no verified point-in-time historical source was found in the inspected repo surface |

## Available Now Without L2 Reconstruction

- OHLCV context: returns, volatility, range, body/range, close-vs-local-low, ADR stretch, regime, and volume.
- `volume_delta` if the bar or trade file already carries it.
- CVD/delta if signed trade columns already exist in a local trade-derived source.
- Absorption proxy if signed trade and price-move inputs exist.
- VPIN / toxicity if buy/sell bucket inputs already exist.

## Blocked Until OFI / L2 Artifact Approval

- OFI
- MLOFI
- microprice
- spread
- depth
- queue imbalance
- L2 imbalance
- spoofing
- iceberg
- L2 whale pressure

## Blocked By Missing Historical Source

- funding
- OI
- liquidation
- derivatives crowding
- basis

## Leakage Risk Assessment

- Same-bar leakage
- Future bar leakage
- Post-entry outcome leakage
- Label leakage
- Rolling-window endpoint leakage
- Feature timestamp after signal timestamp
- Bar close vs signal timing ambiguity

## Gate 1 Finding

Gate 1 static inventory: pass.
Gate 1 data availability: partial because no optional schema files were supplied.
Gate 2 feature table dry run: not started.

## Recommended Next Step

Create a bounded read-only signal-time schema audit using a known C_Exhaustion replay output and a bar file, if available, to verify actual columns and timestamp alignment before any feature table dry run.

## What Is Safe

- Static inventory
- Schema-only audit
- Timestamp alignment audit
- Leakage audit
- Bounded read-only feature availability diagnostics

## What Is Not Safe

- Alpha claims
- Strategy optimization
- Full reconstruction
- OFI artifact generation
- Paper/live trading
- Using unapproved L2 features

## Decision

- `c_exhaustion_signal_time_feature_audit_created`
- `gate_1_static_inventory_completed`
- `no_raw_l2_data_read`
- `no_ofi_artifacts_read`
- `no_ofi_artifacts_written`
- `no_strategy_backtest_run`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `data_availability_audit_partial`
