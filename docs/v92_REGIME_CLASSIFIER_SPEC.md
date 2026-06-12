# V9.2 Regime Classifier Specification

## Motivation
The autopsy of the V7.x D4 signal confirmed that "faux alpha" collapses when subjected to realistic taker fees and the structural changes of the 2024-2026 market. The primary missing piece to gate these signals is a strict **Regime Classifier**. 

We cannot trade a breakout signal in a mean-reverting environment. We cannot trade an absorption signal during a parabolic trend. The Regime Classifier acts as the supreme gatekeeper for the V9.2 Alpha tests.

## 1. The Three Primary Regimes

### A. Compress / Breakout Regime (Trend)
*   **Definition:** Market volatility has contracted significantly, building energy for a directional move.
*   **Metrics:** 
    *   `Realized Volatility (HTF)` < 15th percentile of 30-day rolling.
    *   `Bollinger Band Width` contraction.
    *   `Price` is tight within the No-Leakage Swing High/Low.
*   **Action:** Enable **Branch A (Structural Breakout)**. Wait for massive taker Volume Delta to validate the breakout.

### B. Exhaustion Regime (Contrarian / Mean Reversion)
*   **Definition:** Market has made a parabolic move and stretched the limits of its statistical daily range. Late retail FOMO provides exit liquidity for institutions.
*   **Metrics:**
    *   `ADR Stretch` (Current Price - Daily Open) / Average Daily Range > 85%.
    *   RSI or structural equivalent shows extreme deviation from the rolling VWAP.
*   **Action:** Enable **Branch C (ADR Exhaustion Fade)**. Look for a terminal volume spike (liquidation cascade) at the highs to short the reversal.

### C. Heavy Absorption Regime (Market Maker Dominance)
*   **Definition:** High volume and order flow are printing, but the price is completely pinned. Market makers are absorbing all taker flow.
*   **Metrics:**
    *   `Volume` > 80th percentile.
    *   `OFI` heavily skewed (e.g., negative).
    *   `Price Return` per bar is near 0 (Doji bars).
*   **Action:** Enable **Branch B (Microstructure Absorption)**. Fade the aggressive taker flow by trading *with* the absorbing whales.

## 2. Implementation Architecture

The Regime Classifier will sit completely independent of the execution logic. 

1.  **Inputs:** It will consume the 500-BTC Volume Bars.
2.  **State Machine:** It updates its state at the close of every bar.
3.  **Output:** It exposes a `current_regime` enum (`TREND_BUILDUP`, `EXHAUSTED`, `ABSORPTION`, `NOISE`).
4.  **No-Leakage Guarantee:** The classifier will strictly only use data available at `bar.close`. No forward-peeking normalization.

## 3. Next Steps
Once the OFI L2 cache finishes building, our very first V9.2 test will be evaluating the pure OFI signal, but **gated** by this regime classifier. We will test the OFI signal exclusively under the `2024-2026` timeframe, demanding real expectancy after 5bps costs.
