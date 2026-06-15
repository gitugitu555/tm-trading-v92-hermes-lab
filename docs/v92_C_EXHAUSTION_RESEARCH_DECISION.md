# C_ExhaustionFade Research Decision

## Current Status

C_ExhaustionFade is a repaired historical replay anchor with a documented canonical post-regime-fix baseline and multiple diagnostics covering decay, signal state, exit timing, hypothesis matrices, regime/context mismatch, and data provenance.

## What Was Repaired

- The replay path now delegates to the canonical regime classifier.
- The stale local fallback classifier path was removed.
- The fixed replay runner now reports calendar-daily metrics instead of trade-count Sharpe.
- The Tier-2 bar builder was hardened against `is_buyer_maker` parsing and write-path corruption.
- Existing 750 BTC bars were audited, and a targeted raw-rebuild parity sample matched the hardened builder.

## What Was Validated

- The canonical post-regime-fix anchor is documented.
- Recent-period decay is real and materially worse than the early anchor.
- The 36-bar exit is not enough to rescue the recent period.
- Regime/context mismatch is the leading explanation for the recent failures.
- Simple ex-ante proxy gates do not restore recent-period positive expectancy.

## What Failed

- No simple fixed exit restored the recent period.
- No diagnostic exit family is approved for production use.
- No regime gate is approved for live or paper use.
- No ex-ante proxy gate was good enough to be treated as a production filter.

## What Remains Useful

- The canonical C_ExhaustionFade replay remains a research-valid historical anchor.
- The decay, signal-state, exit-timing, and regime/context diagnostics remain useful as evidence for future research.
- The ex-ante proxy matrix remains useful for identifying candidate hypotheses, not approved rules.

## Decision

C_ExhaustionFade remains a research-valid historical anchor.
C_ExhaustionFade is not production-valid.
C_ExhaustionFade should not be paper-traded from the current rule set.
No simple fixed exit, diagnostic exit, regime gate, or ex-ante proxy gate is approved.
Simple ex-ante rule gates failed to restore recent-period positive expectancy.

## Allowed Next Research

The only justified continuation path is meta-labeling and model-based bad-context prediction using strictly ex-ante features with purged walk-forward validation.

If the meta-label baseline fails, C_ExhaustionFade should be archived as a historical research anchor while infrastructure work moves to OFI/CVD.

## Not Allowed Yet

- No live trading.
- No paper trading.
- No production filter.
- No approved exit replacement.
- No new alpha logic.
- No broad refactor of the replay or strategy.

## Required Infrastructure Before Production

- A meta-label baseline using ex-ante features only.
- Purged walk-forward validation with embargo.
- Calibration and confusion-matrix reporting by period.
- PSR, DSR, and PBO checks after candidate selection.
- A documented candidate-selection protocol.
