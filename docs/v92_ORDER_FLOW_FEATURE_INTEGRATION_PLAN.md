# V9.2 Order-Flow Feature Integration Plan

## Executive Summary

The L2 OFI infrastructure boundary is now documented and bounded-validated, but it is still infrastructure-only. No OFI artifacts are approved for generation, no full reconstruction is approved, and none of that work is a basis for production use.

C_Exhaustion still has a credible historical anchor, but the repo evidence shows recent decay, weaker positive tails, and regime/context mismatch in 2025-2026. The OHLCV-only proxy gates already tested are not enough to restore recent-period expectancy.

The next credible research path is ex-ante order-flow confirmation and meta-labeling using features that are observable at or before the signal timestamp. That path must stay leakage-controlled and split by time. It can inform future research, but it does not approve alpha, trading, OFI artifacts, or reconstruction.

This document is a planning and inventory artifact only.

## Current Safety Boundary

- No OFI data artifacts are approved; only documentation and bounded-validation reports exist.
- No full L2 reconstruction is approved.
- No paper/live use is approved.
- L2 OFI remains infrastructure-only.
- Any feature integration must be ex-ante and leakage-controlled.
- Any feature derived from unapproved L2 artifacts is blocked until reconstruction approval exists.
- Any use of future bar data, post-signal outputs, or same-bar leakage is blocked.

## Repo Inventory Method

### Inspected Directories

- `features/`
- `scripts/`
- `docs/`
- `tests/`
- `replays/`

### Missing Top-Level Directories

- `strategy/` was not present.
- `strategies/` was not present.

### Search Terms Used

- `C_Exhaustion`
- `Exhaustion`
- `CVD`
- `cumulative volume delta`
- `delta`
- `absorption`
- `VPIN`
- `OFI`
- `order flow imbalance`
- `MLOFI`
- `footprint`
- `microprice`
- `imbalance`
- `book pressure`
- `liquidity`
- `spread`
- `depth`
- `queue`
- `aggressive`
- `taker`
- `trade sign`
- `BVC`
- `meta label`
- `triple barrier`
- `label`
- `regime`
- `replay`
- `attribution`
- `feature ledger`

### Files Found

- `features/cvd.py`
- `features/delta.py`
- `features/footprint.py`
- `features/absorption.py`
- `features/iceberg.py`
- `features/l2_imbalance.py`
- `features/microprice.py`
- `features/microstructure_ofi.py`
- `features/microstructure_numba_ofi.py`
- `features/mlofi.py`
- `features/queue_imbalance.py`
- `features/vpin.py`
- `features/trade_signing.py`
- `features/spoofing.py`
- `features/whale.py`
- `features/market_profile.py`
- `features/market_structure.py`
- `features/contextual_filters.py`
- `features/regime_classifier.py`
- `features/anti_patterns.py`
- `features/v92_data_policy.py`
- `replays/c_exhaustion_replay.py`
- `scripts/diagnose_c_exhaustion_meta_label_baseline.py`
- `scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py`
- `scripts/diagnose_c_exhaustion_signal_state.py`
- `scripts/diagnose_c_exhaustion_regime_context.py`
- `scripts/diagnose_c_exhaustion_exit_hypothesis_matrix.py`
- `scripts/run_c_exhaustion_replay.py`
- `scripts/v92_regime_validation.py`
- `scripts/v92_regime_freq_diagnostic.py`
- `scripts/v92_contextual_filter_diagnostics.py`
- `scripts/v92_alpha_strategy_test.py`
- `scripts/audit_ofi_downstream_consumers.py`
- `scripts/audit_ofi_historical_provenance_coverage.py`
- `docs/v92_C_EXHAUSTION_RECENT_DECAY_DIAGNOSTICS.md`
- `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md`
- `docs/v92_C_EXHAUSTION_REGIME_CONTEXT_MISMATCH.md`
- `docs/v92_C_EXHAUSTION_EX_ANTE_PROXY_GATE_MATRIX.md`
- `docs/v92_C_EXHAUSTION_META_LABEL_BASELINE_RESULTS.md`
- `docs/v92_C_EXHAUSTION_RESEARCH_DECISION.md`
- `docs/v92_OFI_DOWNSTREAM_CONSUMER_AUDIT.md`
- `docs/v92_OFI_HISTORICAL_PROVENANCE_COVERAGE_AUDIT.md`
- `docs/v92_REGIME_CLASSIFIER_SPEC.md`
- `docs/v92_STRATEGY_MEMORY_LEDGER.md`

### Files Not Found

- No top-level `strategy/` or `strategies/` tree.
- No verified historical OFI artifact inventory in the current repo working tree.
- No approved OFI parquet/csv/json outputs were found or used for this plan.

### Script Usage

- No new script was used for this planning document.
- No new test harness was used for this planning document.

### Data Read

- No raw market data was read for this plan.
- No OFI artifacts were read for this plan.
- Only repo code and repo documentation were inspected.

## Existing Order-Flow / Microstructure Feature Inventory

| Feature family | Candidate module/file | Feature examples | Input data required | Current implementation status | Current consumer status | Historical coverage status | Leakage risk | Production readiness | Notes |
|---|---|---|---|---|---|---|---|---|---|
| CVD / signed trade flow | `features/cvd.py`, `features/trade_signing.py`, `features/delta.py` | `delta`, `cvd`, `velocity`, `acceleration`, signed trade side | Signed trades or trade tape with a reliable side classifier | Implemented | Used indirectly in regime diagnostics via `volume_delta` and in research docs; not wired into C_Exhaustion replay | Available from existing bars/trades if `volume_delta` or signed trades are present | Low if shifted/past-only; medium if mixed with future confirmation | Not approved | This is the cleanest non-L2 order-flow family already represented in repo code. |
| Footprint / volume-at-price | `features/footprint.py` | buy volume, sell volume, delta by price level, total volume | Trades plus tick-size bucketing | Implemented | Not wired to C_Exhaustion | No published historical footprint ledger | Low to medium depending on bucket timing | Not approved | Useful as a research feature, but it needs a careful timestamp protocol. |
| Absorption | `features/absorption.py` | ask absorption, bid absorption | Signed trades and recent price movement | Implemented | Not wired to C_Exhaustion; only conceptually referenced in docs and anti-pattern logic | No historical audited feature ledger | Medium if window alignment is sloppy | Not approved | The detector is a proxy, not a proof of true absorption. |
| Iceberg / hidden liquidity | `features/iceberg.py` | refill count, iceberg candidate | Repeated L2 level snapshots | Implemented | Not wired to C_Exhaustion | No audited historical coverage | High if L2 history is incomplete | Not approved | Only a candidate detector. Missing updates can mimic refills. |
| Spoofing / layering | `features/spoofing.py` | fast wall cancel, spoof candidate | L2 snapshots with timestamps | Implemented | Not wired to C_Exhaustion; used only as an input to `WhalePressureEngine` / diagnostics | No audited historical coverage | High | Not approved | Cancellation timing is sensitive to missing snapshots. |
| Whale / large-flow diagnostics | `features/large_prints.py`, `features/whale.py` | large print z-score, whale pressure, source mix | Signed trades, optionally book imbalance and spoof/iceberg events | Implemented | Not wired to C_Exhaustion | No audited historical feature ledger | Medium | Not approved | The code exists, but the historical feature surface is not yet proven. |
| Microprice / queue / depth / spread | `features/microprice.py`, `features/queue_imbalance.py`, `features/l2_imbalance.py`, `features/market_profile.py` | microprice, drift, top1/top5/top10 imbalance, spread bps, depth | L2 bid/ask snapshots | Implemented | Not wired to C_Exhaustion; used in diagnostics and anti-pattern scoring only | Historical L2 coverage exists as source inventory, but approved artifact generation is blocked | High | Not approved | These are the core L2-derived ex-ante candidates, but they remain blocked by approval state. |
| OFI / MLOFI | `features/microstructure_ofi.py`, `features/microstructure_numba_ofi.py`, `features/mlofi.py` | OFI, multi-level imbalance, trap score, agreement score | Ordered L2 updates / snapshots | Implemented and repaired for bounded research use | Not consumed by C_Exhaustion replay or strategy logic; only diagnostics, validation, and audit paths reference it | Historical OFI files are unavailable in the current provenance audit; full reconstruction remains blocked | High | Not approved | This is the gated infrastructure boundary, not a trading feature yet. |
| VPIN / toxicity | `features/vpin.py` | VPIN level, slope, fast/slow spread, toxicity state | Signed trades or completed buy/sell volume bars | Implemented | Not wired to C_Exhaustion replay; only reused indirectly as a concept in `anti_patterns.py` | No audited historical VPIN ledger | Medium | Not approved | Safe as a past-only diagnostic only if a strict timestamp protocol is maintained. |
| Regime / volatility filters | `features/regime_classifier.py`, `features/contextual_filters.py`, `features/market_structure.py` | `TREND_BUILDUP`, `ABSORPTION`, `EXHAUSTED`, `NOISE`, ATR regime, swing distance | Completed OHLCV bars | Implemented and actively used | Used by C_Exhaustion replay and regime diagnostics | Available from existing bars | Low when shifted/delayed correctly | Research-only, not production-approved | This is the only feature family already wired into the replay path. |
| Market profile / auction context | `features/market_profile.py` | POC, VAH, VAL, LVN, profile type, exhaustion context | Completed bars | Implemented | Used in diagnostics and strategic memory, not C_Exhaustion replay | Available from existing bars | Low to medium | Not approved | A useful context family, but not yet a promoted gate. |
| Aggressive buy/sell imbalance | `features/trade_signing.py` | BVC split, signed delta, buyer/seller aggressor side | Trade tape with mid or aggressor-side context | Implemented | Used indirectly by CVD, delta, absorption, VPIN | Available if trade signing exists | Low if past-only | Not approved | This is a supporting primitive rather than a standalone strategy claim. |
| Feature-ledger / anti-pattern gating | `features/anti_patterns.py` | exhaustion continuation, profile chase, low-liquidity breakout, trap labels | Derived features from regime, spread, MLOFI, toxicity, profile | Implemented | Research-only gating scaffold | Depends on upstream features | Medium | Not approved | This is a shadow classifier, not an execution rule. |
| Funding / OI / liquidation / derivatives context | No verified module or ledger found | funding state, open interest, liquidation cascade, basis, crowding | Point-in-time derivatives history | Not found as a verified historical ledger in this repo | Not consumed by C_Exhaustion | Blocked by missing historical coverage | Unknown to high | Not approved | The strategy memory ledger lists these as future research, but the repo does not yet provide a verified source inventory. |

## Existing Strategy Consumer Inventory

| Strategy / script / module | Current inputs | Current feature dependencies | Order-flow features currently used | Order-flow features absent | Leakage concerns | Notes |
|---|---|---|---|---|---|---|
| `replays/c_exhaustion_replay.py` | 750 BTC bars, regime labels, volume, OHLCV primitives, `vol_roll_95`, `local_low` | Canonical regime classifier and past-only signal construction | Only `volume_delta` can influence the replay indirectly through regime labeling when present | CVD, delta, footprint, VPIN, microprice, queue imbalance, OFI, MLOFI, spoofing, iceberg, whale pressure | Low if the current-barfuture boundary is preserved; medium if new features are joined without strict shift rules | This is the actual C_Exhaustion consumer path today. |
| `scripts/diagnose_c_exhaustion_meta_label_baseline.py` | trade log + bars | OHLCV-derived context, pre-signal returns, volatility, range expansion, body/range, location metrics | None beyond existing `volume_delta`-adjacent context in the regime chain | L2-derived order flow, OFI, microprice, VPIN, spread/depth, footprint | High if future labels or post-signal fields leak in | Uses a strict allowed-feature list and time-ordered validation scaffold. |
| `scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py` | trade log + bars | pre-signal returns, body/range, range expansion, realized vol, ADR stretch, close-vs-local-low | None | All L2-derived order-flow features | High if any post-signal labels are used as gates | Best existing ex-ante proxy benchmark. |
| `scripts/diagnose_c_exhaustion_signal_state.py` | replay trade log + bars | signal-state attribution, MFE/MAE, pre/post returns, regime and candle-state buckets | None | All L2-derived order-flow features | High for any feature that looks at post-signal path | This is diagnostic only. |
| `scripts/diagnose_c_exhaustion_regime_context.py` | replay trade log + bars | pre/post-signal context buckets, trend continuation flags, failed reversal flags, regime | None | All L2-derived order-flow features | High if post-signal labels are promoted into features | Confirms the recent-period context shift. |
| `scripts/diagnose_c_exhaustion_exit_hypothesis_matrix.py` | replay trade log + bars | horizon, TP, giveback, exit timing diagnostics | None | All L2-derived order-flow features | High if exit-derived labels are used as features | Exit research only. |
| `scripts/v92_regime_validation.py` | 500 BTC bars | canonical regime classifier | Indirect `volume_delta` use through regime classification | OFI, microprice, queue, VPIN, L2 imbalance | Low in current implementation because it is close-of-bar and past-only | Confirms the regime classifier is the current market-state gate. |
| `scripts/v92_regime_freq_diagnostic.py` | 500 BTC bars | regime classifier frequencies | Indirect `volume_delta` through the classifier | OFI, microprice, queue, VPIN, L2 imbalance | Low | Descriptive only. |
| `scripts/v92_contextual_filter_diagnostics.py` | synthetic demo or Tier-2 bars | `market_structure` + ATR regime | None | OFI, microprice, queue, VPIN, L2 imbalance | Low in the demo, but not a production path | Diagnostics only; not a strategy consumer. |
| `scripts/v92_alpha_strategy_test.py` | bars, regime labels, data policy helpers | regime labels plus a research harness | None in the current wiring | OFI and other order-flow features | Medium if treated as execution evidence | Not part of the approved C_Exhaustion replay path. |
| `features/anti_patterns.py` consumers | derived snapshot inputs | regime, toxicity, spread, MLOFI, profile context | Indirect via `toxicity_state`, `spread_bps`, `mlofi_zscore` | Raw OFI and approved L2 features are absent | Medium if upstream features are not strictly past-only | Shadow gating only. |

## C_Exhaustion Current Evidence

The repo evidence supports a clear picture:

- Historical anchor: the canonical post-regime-fix replay is still valid as a research anchor, with documented overall positive expectancy.
- Recent decay: `docs/v92_C_EXHAUSTION_RECENT_DECAY_DIAGNOSTICS.md` shows 2025 and 2026 are materially weaker, with negative recent-period expectancy and a much weaker positive tail.
- Signal attribution: `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md` shows recent losers still had favorable excursion, but that move was given back before the fixed exit.
- Positive MFE giveback: recent trades can reach favorable excursion but fail to monetize it consistently.
- Regime label degeneracy: `docs/v92_C_EXHAUSTION_SIGNAL_STATE_ATTRIBUTION.md` states the executed sample is entirely `EXHAUSTED`, so the regime label does not separate executed trades by itself.
- OHLCV-only filtering is insufficient: `docs/v92_C_EXHAUSTION_EX_ANTE_PROXY_GATE_MATRIX.md` shows the best pre-registered OHLCV proxy gates do not restore a robust recent-period edge.
- The credible next path is order-flow confirmation and meta-labeling: `docs/v92_C_EXHAUSTION_RESEARCH_DECISION.md` and `docs/v92_C_EXHAUSTION_META_LABEL_BASELINE_RESULTS.md` both point to ex-ante feature research, not a production gate.

This evidence does not prove alpha death. It does show that the existing OHLCV-only gate surface is not enough to justify promotion.

## Feature Eligibility Matrix

| Feature | Eligible now? | Reason | Required data | Required validation | Suggested first test | Blocker |
|---|---|---|---|---|---|---|
| CVD / signed trade flow | Available from existing bars/trades without new L2 reconstruction | The repo already has `volume_delta`, trade signing, CVD, and delta engines | Signed trades or bars with `volume_delta` | Signal-time availability audit; purged walk-forward meta-label test | Check `volume_delta` at signal bar and one-bar shift safety | Not yet wired into C_Exhaustion |
| Delta velocity / acceleration | Available from existing bars/trades without new L2 reconstruction | Built on top of CVD and does not require new L2 history | CVD series | Shift audit and fold stability audit | Compare baseline vs baseline + delta velocity | Not yet wired into C_Exhaustion |
| Footprint / volume-at-price | Available from existing bars/trades without new L2 reconstruction | The engine is present, but no historical ledger is promoted | Trades and tick size | Timestamp sanity and price-level binning audit | Generate a small read-only footprint snapshot from existing trade inputs only | No approved historical footprint ledger |
| Absorption proxy | Available from existing bars/trades without new L2 reconstruction | The detector is implemented from signed trades and price move | Signed trades and recent price movement | No-future-window audit; calibration against known examples | Compare absorption events against current C signal timestamps | No historical performance ledger |
| VPIN / toxicity | Available from existing bars/trades without new L2 reconstruction | Can be built from signed trades or completed buy/sell volume bars | Signed trades or completed bar split | Bucket alignment audit; no same-bar leakage audit | Build a signal-time VPIN snapshot from past-only buckets | No audited historical VPIN ledger |
| Spread / depth / liquidity | Requires approved L2 artifact generation | Needs L2 snapshots or joins that are not approved for artifact generation yet | Historical L2 updates or snapshots | Provenance and sequence-gap audit plus bar/L2 alignment audit | Only after artifact approval, compare past-only spread to signal time | L2 artifact generation not approved |
| Microprice / book imbalance | Requires approved L2 artifact generation | Needs best-bid/best-ask state and historical L2 coverage | L2 snapshots | Timestamp preservation and no-future-bar audit | Validate on a bounded read-only sample after approval | L2 artifact generation not approved |
| OFI / MLOFI | Requires approved L2 artifact generation | The engine exists, but historical OFI coverage is unavailable and reconstruction is blocked | Ordered L2 updates | Segment continuity, quarantine, and join-preservation checks | Not now; only after reconstruction approval | Historical OFI inventory unavailable and approval missing |
| Spoofing / iceberg / whale pressure | Blocked by missing historical coverage | The detectors exist, but historical event coverage is not yet audited | L2 snapshots and signed trades | Missing-update sensitivity audit and label stability audit | Audit historical availability before any feature proposal | No verified historical event ledger |
| Regime / volatility filters | Immediately inspectable from existing repo outputs | The classifier and diagnostics already exist and are wired into replay | Completed bars | Purged walk-forward and early/middle/recent split audit | Reuse as the baseline context layer | None for research use; still not production-approved |
| Funding / OI / liquidation diagnostics | Blocked by missing historical coverage | No verified ledger exists in the repo inventory | Point-in-time derivatives history | Source inventory and publication-timing audit | Inventory data sources before modeling | Missing source inventory |
| Feature ledger / meta-label labels | Immediately inspectable from existing repo outputs | The meta-label scaffold and label definitions already exist | Trade log + bars | Purged walk-forward and calibration audit | Build a read-only feature availability table at signal time | No alpha claim and no promotion without validation |

## Ex-Ante Integration Rules

- Feature timestamp must be less than or equal to the signal timestamp.
- No future bar data is allowed.
- No same-bar close leakage is allowed unless the feature is explicitly shifted.
- No post-entry MFE/MAE values may appear in features.
- No labels may appear in features.
- All joins must preserve bar count.
- All generated features must be shift-safe.
- All filters must be evaluated with purged splits.
- Costs must remain explicit.
- No tuning is allowed on the full sample.
- Early, middle, and recent splits must be reported separately.

## Proposed C_Exhaustion Order-Flow Meta-Label Design

### 1. Baseline

- Existing C_Exhaustion signal set.
- No new filters.
- Current cost model unchanged.

### 2. Candidate Ex-Ante Features

- CVD slope / divergence.
- Delta exhaustion.
- Absorption proxy.
- VPIN / toxicity.
- OFI only if approved artifacts exist later.
- Spread, depth, and liquidity if historical coverage is later approved.
- Regime interaction features.

### 3. Labels

- Keep the existing labels already used in the repo.
- If needed for the next phase, add a triple-barrier or fixed-horizon keep/skip label.
- Labels must remain strictly leakage-free and derived only from post-signal outcomes, never from features.

### 4. Splits

- `2020-2023` train
- `2024` validation
- `2025-2026` holdout/recent

If the existing purged walk-forward convention is used instead, keep the repo’s year-based folds and embargo rules rather than inventing a new split policy.

### 5. Metrics

- Hit rate.
- Expectancy in bps.
- Net expectancy after cost.
- Profit factor.
- Drawdown.
- Precision and recall for the keep/skip decision.
- Calibration.
- Turnover reduction.
- Yearly stability.
- Recent-only performance.

### 6. Required Comparisons

- OHLCV baseline.
- OHLCV + regime.
- OHLCV + trade-flow features.
- OHLCV + L2-derived features only after approval.
- All features with purged validation.

## Validation Gates

### Gate 0

Documentation and inventory only.

This task is Gate 0 only.

### Gate 1

Feature availability and leakage audit.

### Gate 2

Read-only feature table dry run on a small bounded sample.

### Gate 3

Purged historical meta-label experiment.

### Gate 4

Recent holdout pass.

### Gate 5

Cost and slippage stress.

### Gate 6

Paper-trading candidate only if all prior gates pass.

### Gate 7

Live trading only after separate explicit approval.

## Risks

- Data leakage.
- Feature hallucination or unused modules.
- Overfitting C_Exhaustion.
- Recent regime decay.
- Missing L2 coverage.
- OFI artifact generation not approved.
- Bar/L2 date mismatch.
- False confidence from the micro-batch dry-run work.
- High win-rate and negative expectancy trap.
- Same-bar entry/exit leakage.
- Cost model underestimation.

## Recommended Next Implementation Step

Implement a read-only `C_Exhaustion` signal-time feature audit script that checks which existing features are available at each signal timestamp without joining any new OFI artifacts.

Why this step:

- It is the safest non-alpha implementation step.
- It directly answers which features are available at signal time.
- It can validate leakage controls before any model work.
- It does not require OFI artifact generation, full reconstruction, or any strategy logic change.

## What Is Safe

- Documentation-only planning.
- Repo inventory.
- Feature availability audit.
- Leakage audit.
- Bounded read-only diagnostics.

## What Is Not Safe

- Full L2 reconstruction.
- OFI artifact generation.
- Alpha claims.
- Paper trading.
- Live trading.
- Production use.
- Using unapproved L2 OFI outputs.
- Tuning on the full sample.

## Decision

- `order_flow_integration_plan_created`
- `repo_inventory_only`
- `no_raw_l2_data_read`
- `no_bar_data_modified`
- `no_ofi_artifacts_written`
- `full_reconstruction_not_approved`
- `alpha_blocked`
- `paper_live_blocked`
- `gate_0_only`
