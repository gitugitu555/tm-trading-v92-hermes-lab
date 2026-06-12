# V9.2 Microstructure Strategy Branches

With our Tier-2 Cache producing true **Volume Delta**, **OFI (Order Flow Imbalance)**, and **No-Leakage Swing Structures**, we are no longer guessing at fake time-based indicators. We can trade pure market mechanics.

Here are three distinct, high-probability strategy branches we can build utilizing the new V9.2 foundation:

## Branch A: Structural Breakout with Taker Confirmation (Trend Following)
* **The Logic:** False breakouts happen because market makers pull liquidity, letting price slip past a swing-high before slamming it back down. A *true* breakout requires aggressive taker buying.
* **Context Filter:** `regime_high_vol == False` (We want low volatility consolidation preceding the move).
* **Signal:** Price breaks `last_confirmed_swing_high`.
* **Confirmation:** The current 500-BTC Volume Bar must have a heavily positive `volume_delta` (e.g. > +150 BTC net taker buy).
* **Dynamic Exit:** `atr_trailing_stop` (Ride the trend until volatility expands and whipsaws).

## Branch B: Microstructure Absorption (Mean Reversion)
* **The Logic:** Large limit orders (whales) absorb aggressive market orders. If we see a massive amount of market selling but the price stops moving down, the selling is being absorbed.
* **Context Filter:** `regime_high_vol == True` (Needs active participation and panic).
* **Signal:** `OFI` and `volume_delta` are heavily negative (massive taker selling).
* **Confirmation:** The `close` of the volume bar is > the `open` of the bar, or the bar is a doji. This means despite the massive selling, price was absorbed and rejected by limit bids.
* **Dynamic Exit:** `cvd_reversal_exit` (Exit the moment the absorption fails and taker flow resumes pushing price down).

## Branch C: ADR Exhaustion & Liquidation Fade (Contrarian)
* **The Logic:** Markets rarely move in a straight line forever. When the daily range is stretched to its mathematical limit, the late-arriving retail traders usually get liquidated by institutions fading the move.
* **Context Filter:** `regime_adr_exhausted == True` (The day has moved > 85% of its 14-day Average Daily Range).
* **Signal:** Price hits a new intraday high.
* **Confirmation:** A sudden, extreme spike in `volume_delta` at the highs (representing FOMO market buying or short liquidations).
* **Dynamic Exit:** `time_stop` (Reversals should happen fast. If we don't get immediate Minimum Favorable Excursion within 5 bars, exit).

---
> [!TIP]
> All three of these branches completely avoid the pitfalls of your old V7/V8 strategies because they rely on actual order flow, not lagging moving averages.
