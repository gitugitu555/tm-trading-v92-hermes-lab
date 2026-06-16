# V9.2 Research Agent Prompt Bank

Status: `RESEARCH_ONLY`  
Authority: non-canonical prompt bank. These prompts do **not** define strategy behavior.  
Scope: future research guidance for `tm-trading-v92-core` only.

## Safety Rules

- Do not implement any recommendation from this file without replay validation, cost stress, yearly split, and no-leakage tests.
- Do not hardcode old `C_ExhaustionFade` anchor metrics as current truth. Always use the latest canonical replay or paper-sim report from `master`.
- Do not fake L2, OFI, funding, liquidation, or derivatives history with OHLCV proxies.
- `B_Absorption`, MLOFI/OFI, iceberg, whale pressure, funding, OI, and liquidation research remain data-gated until verified historical coverage exists.
- `C_ExhaustionFade` exit diagnostics are the current priority before adding new signal gates.
- This file is a research control surface, not executable alpha logic.

## Current Priority Map

### Active Now

1. Exit Optimization
2. Statistical Validation

### Blocked Until Verified Data Exists

1. MLOFI / OFI
2. Absorption / Iceberg
3. Derivatives / Funding / OI / Liquidations

### Later Research

1. VPIN / Toxicity
2. Regime Classification v2
3. Meta-Labeling

---

## Agent 1 — VPIN / Toxicity

**Status:** Later research.  
**Relevant repo area:** `features/vpin.py`.  
**Risk:** medium. VPIN can become a disguised volatility proxy if not tested carefully.

### Prompt

You are a quant researcher auditing the VPIN engine in `tm-trading-v92-core`.

The repo has a VPIN engine implementing Easley, Lopez de Prado, and O'Hara style volume-bucket VPIN with fast/slow windows, z-score, and toxicity state classification.

Strategy context: `C_ExhaustionFade` is an ADR/exhaustion reversal strategy on BTCUSDT volume bars. VPIN is not canonical signal logic and should be evaluated only as a skip gate, diagnostic, or research feature.

Research and recommend specific improvements to make VPIN useful as either:

1. signal filter,
2. skip gate,
3. entry context,
4. post-trade diagnostic.

Cover:

- bulk-volume VPIN vs tick-rule VPIN and whether the current implementation is appropriate for crypto;
- critiques that VPIN may proxy volatility rather than informed flow;
- VPIN as a skip gate vs entry condition for an exhaustion fade;
- toxicity state thresholds and calibration;
- bucket size relative to BTC volume bars;
- fast/slow window ratios and z-score windows;
- one exact backtest that proves or disproves VPIN as a blocked-loser gate.

### Acceptance Gate

VPIN only graduates if it improves out-of-sample expectancy or drawdown at cost12 and cost20 without hiding bad years through a no-trade overfit filter.

---

## Agent 2 — MLOFI / OFI

**Status:** Blocked until verified L2 coverage exists.  
**Relevant repo area:** `features/mlofi.py`, L2 reconstruction policy, OFI cache work.  
**Risk:** high if built from fake or incomplete book data.

### Prompt

You are a quant researcher auditing the MLOFI engine in `tm-trading-v92-core`.

The repo has an MLOFI engine implementing multi-level order-flow imbalance with distance-decay weights, near/far book split, book agreement score, book trap score, and rolling z-score.

Strategy context: `C_ExhaustionFade` is currently the main candidate. MLOFI is a candidate for the next alpha family only if true L2 history is verified and joined without coverage loss.

Research and recommend improvements to make MLOFI the next alpha family.

Cover:

- Cont-Kukanov-Stoikov OFI vs Xu-Gould multi-level OFI;
- whether fixed distance-decay weights are justified or should be learned/calibrated;
- attention-style order-book ideas and whether a simpler non-deep version is adequate;
- whether book trap score requires cancellation/refill semantics rather than static depth divergence;
- MLOFI as standalone alpha vs filter for `C_ExhaustionFade`;
- whether MLOFI should confirm the fade direction or contradict the final push;
- microprice displacement vs MLOFI;
- max levels, near levels, z-score windows, and BTC/USDT calibration;
- exact backtest design using verified L2 history.

### Acceptance Gate

No MLOFI result is valid unless the run manifest proves exchange, symbol, depth, date range, sequence-gap policy, reset policy, and coverage-preserving joins.

---

## Agent 3 — Regime Classification

**Status:** Later research; do not modify before preserving canonical replay parity.  
**Relevant repo area:** `features/regime_classifier.py`, `replays/c_exhaustion_replay.py`.  
**Risk:** very high if classifier changes silently alter historical signal identity.

### Prompt

You are a quant researcher auditing the canonical regime classifier in `tm-trading-v92-core`.

The current classifier uses volatility, volume percentile, ADR stretch, body/range structure, and delta efficiency to classify regimes such as `TREND_BUILDUP`, `ABSORPTION`, `EXHAUSTED`, and `NOISE`.

`C_ExhaustionFade` depends on the `EXHAUSTED` state. Any classifier change can alter the strategy identity and must be tested as a new candidate, not silently merged into the old C baseline.

Research:

- rule-based classifier vs Hamilton HMM / filtered probabilities;
- no-leakage filtered probabilities vs smoothed probabilities;
- regime parsimony: whether a simpler `EXHAUSTED` detector is better than a four-state classifier;
- rolling standard deviation vs GARCH or regime-switching volatility;
- crypto session overlay and whether UTC session should be separate gate or regime feature;
- adaptive estimation windows for 2024-2026 non-stationarity;
- one regime change most likely to improve recent C behavior.

### Acceptance Gate

Any classifier change must produce a new named candidate and must report old-vs-new signal count, overlap percentage, yearly metrics, cost stress, and recent split metrics.

---

## Agent 4 — Exit Optimization

**Status:** Active now / highest priority.  
**Relevant repo area:** `exits/dynamic_exits.py`, C replay, paper-sim, MFE/MAE diagnostics.  
**Risk:** medium. Exit overfitting can destroy a real entry edge.

### Prompt

You are a quant researcher auditing the exit logic in `tm-trading-v92-core`.

The repo has research exit functions such as ATR trailing stop, time stop, and CVD reversal exit, but the canonical `C_ExhaustionFade` replay uses fixed `horizon_bars=36`.

Strategy context: exhaustion fades expect reversal after an ADR/structure extreme. The known research question is whether trades produce favorable excursion before the fixed horizon and then give it back.

Research the optimal exit architecture for exhaustion-fade strategies.

Cover:

- triple-barrier labels as training labels vs live exits;
- optimal stopping for mean-reversion / exhaustion fades;
- MFE/MAE path analysis and how to classify trade paths;
- whether CVD reversal is the wrong exit signal for a fade;
- MLOFI or absorption-completion exits once L2 is verified;
- partial exits and staged exits for reversal trades vs trend-following;
- ATR trailing stop suitability for non-trending regimes;
- exact MFE/MAE experiment needed to reveal optimal exit for C.

### Minimum Experiment

Build a C exit surface over:

- horizons: 6, 12, 18, 24, 30, 36, 42, 48;
- cost bps: 5, 8, 12, 20;
- metrics: trade_count, win_rate, net_expectancy_bps, profit_factor, max_drawdown_bps, average MFE, average MAE, MFE capture ratio, positive years, worst year, recent split.

### Acceptance Gate

An exit change only graduates if it improves recent and full-period risk-adjusted metrics without collapsing positive-year count or cost20 robustness.

---

## Agent 5 — Meta-Labeling

**Status:** Later.  
**Relevant repo area:** future research only.  
**Risk:** high with small samples.

### Prompt

You are a quant researcher auditing meta-labeling opportunities in `tm-trading-v92-core`.

The primary model is the `C_ExhaustionFade` signal. A secondary model would predict whether to take, skip, or size down a fired signal.

Current caution: current bar-level features may be too weak, and a small trade sample can make meta-labeling unstable.

Research:

- Lopez de Prado meta-labeling failure modes with insufficient features;
- exhaustion-fade features that predict reversal success;
- intra-bar / multi-scale features needed at signal time;
- target design: profitable-after-cost vs MFE threshold vs drawdown-safe winner;
- precision-recall vs ROC-AUC for skip-gate use;
- logistic regression vs tree models vs gradient boosting for small financial samples;
- minimum viable meta-labeling experiment with limited trade count;
- whether more events are required before ML is valid.

### Acceptance Gate

Do not ship a meta-labeler unless purged time-series validation shows stable precision improvement and the model does not simply learn to avoid entire bad years after the fact.

---

## Agent 6 — Statistical Validation

**Status:** Active now.  
**Relevant repo area:** validation scripts, robustness reports, replay summaries.  
**Risk:** low; this improves decision quality without changing strategy behavior.

### Prompt

You are a quant researcher auditing the statistical validation layer in `tm-trading-v92-core`.

The repo has bootstrap CI and calendar Sharpe work, but still needs a stronger validation stack for multiple testing, non-IID returns, and overfit probability.

Research and implement recommendations for:

- Probabilistic Sharpe Ratio;
- Deflated Sharpe Ratio;
- Probability of Backtest Overfitting;
- Combinatorially Symmetric Cross-Validation or simpler purged alternatives;
- block bootstrap vs IID bootstrap;
- Lo autocorrelation-adjusted Sharpe;
- multiple-testing control across robustness grids;
- exact implementation order and formulas using available replay statistics.

### Acceptance Gate

Validation code should be report-only and must not mutate strategy logic. Every promoted candidate should carry PSR/DSR-style diagnostics, yearly split, cost stress, and an overfit warning if applicable.

---

## Agent 7 — Absorption / Iceberg

**Status:** Blocked until verified L2 refill semantics exist.  
**Relevant repo area:** `features/absorption.py`, `features/iceberg.py`, `features/whale.py`, MLOFI/book trap.  
**Risk:** very high if inferred from aggTrades only.

### Prompt

You are a quant researcher auditing absorption and iceberg detection in `tm-trading-v92-core`.

The repo has an absorption engine based on signed delta and limited price movement. It also has planned iceberg/whale-pressure ideas. These are not canonical alpha unless verified L2 data supports refill/cancellation semantics.

Research:

- minimum data needed to distinguish iceberg/refill from ordinary limit-order coincidence;
- whether aggTrades alone can prove absorption or only suggest it;
- principled calibration for delta threshold and max pinned-price movement;
- high-volume small-body / low-delta-efficiency as proxy vs true absorption;
- Branch B hypothesis: negative OFI/CVD with pinned price as long reversal setup;
- spoofing vs genuine absorption using cancellation/refill temporal signatures;
- minimal viable absorption feature that can be built in two weeks from verified L2.

### Acceptance Gate

No Branch B test is valid without L2 coverage manifest, sequence-gap policy, and refill/cancellation evidence. AggTrade-only absorption must be labeled `proxy_absorption`, not true iceberg detection.

---

## Agent 8 — Derivatives / Funding / OI / Liquidations

**Status:** Blocked until verified point-in-time derivatives history exists.  
**Relevant repo area:** future feature cache only.  
**Risk:** high lookahead risk around funding publication and liquidation feeds.

### Prompt

You are a quant researcher auditing derivatives alpha potential in `tm-trading-v92-core`.

Funding, open interest, liquidation, long/short ratio, and perp basis are marked data-blocked until verified historical sources exist.

Research:

- funding extremes as crowding/reversal signal vs carry/basis signal;
- open interest interpretation: price down + OI up vs price down + OI down;
- liquidation cascade magnitude and reversal timing relative to C horizon;
- point-in-time funding publication rules and lookahead prevention;
- Bybit/Binance data source coverage and historical availability;
- exact feature schema for funding, OI, liquidation, and basis;
- one minimal derivatives-overlay test for C that does not leak future data.

### Acceptance Gate

No derivatives feature may enter a replay unless the event timestamp, publication timestamp, exchange, symbol, and availability lag are explicitly modeled.

---

## Operating Principle

This prompt bank exists to preserve good research questions without letting them override the current build order.

The current build order remains:

1. preserve canonical C signal truth;
2. diagnose C exits and MFE/MAE path behavior;
3. strengthen statistical validation;
4. unblock real L2/OFI data;
5. then evaluate VPIN, MLOFI, absorption, derivatives, and meta-labeling as gated candidates.
