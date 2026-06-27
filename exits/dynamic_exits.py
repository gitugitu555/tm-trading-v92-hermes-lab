"""V9.2 Dynamic Exits — research implementations.

Three priority exit mechanisms for the C_ExhaustionFade family:

1. ATR trailing stop  — lock in gains as price moves in favour.
2. Time stop          — exit early when minimum favourable excursion is not
                        reached within a given bar budget.
3. CVD reversal exit  — exit when cumulative volume delta z-score flips
                        against the trade direction past a threshold.

These functions operate on already-opened positions; ``side`` therefore
represents position direction ("long" / "short"), not the entry trade side
("BUY" / "SELL") used by ``core.types.SignedTrade``.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

PositionSide = Literal["long", "short"]

_VALID_SIDES: frozenset[str] = frozenset({"long", "short"})


def _validate_side(side: str) -> None:
    if side not in _VALID_SIDES:
        raise ValueError(f"side must be 'long' or 'short', got {side!r}")


def atr_trailing_stop(
    entry_price: float,
    side: PositionSide,
    atr_series: pd.Series,
    price_series: pd.Series,
    atr_multiplier: float = 2.0,
) -> pd.Series:
    """Return the trailing stop level for each bar while a trade is active.

    Parameters
    ----------
    entry_price:
        The fill price at which the position was opened.
    side:
        Position direction — ``"long"`` or ``"short"``.
    atr_series:
        ATR values aligned with ``price_series`` (same index).
    price_series:
        High prices for long positions, low prices for short positions,
        both aligned bar-by-bar from the entry bar onward.
    atr_multiplier:
        Number of ATR units below the running high (long) or above the
        running low (short) to place the stop.  Default: 2.0.

    Returns
    -------
    pd.Series
        Stop price at each bar, same index as ``price_series``.
    """
    _validate_side(side)
    if atr_multiplier <= 0:
        raise ValueError(f"atr_multiplier must be positive, got {atr_multiplier}")

    if side == "long":
        running_extreme = price_series.cummax()
        return running_extreme - (atr_series * atr_multiplier)
    else:  # "short"
        running_extreme = price_series.cummin()
        return running_extreme + (atr_series * atr_multiplier)


def time_stop(
    entry_index: int,
    current_index: int,
    mfe_bps: float,
    max_bars: int = 12,
    required_mfe_bps: float = 5.0,
) -> bool:
    """Return ``True`` when the trade has not moved enough within its bar budget.

    The trade is flagged for exit when *both* conditions hold:
    - ``current_index - entry_index >= max_bars``
    - ``mfe_bps < required_mfe_bps``

    Parameters
    ----------
    entry_index:
        Bar index at which the position was entered.
    current_index:
        Bar index being evaluated now.
    mfe_bps:
        Maximum favourable excursion so far, in basis points.
    max_bars:
        Number of bars after which the position is considered stale.
    required_mfe_bps:
        Minimum MFE (bps) the trade must have achieved by ``max_bars``.

    Returns
    -------
    bool
        ``True`` → exit the position now.
    """
    if max_bars <= 0:
        raise ValueError(f"max_bars must be positive, got {max_bars}")
    bars_in_trade = current_index - entry_index
    return bars_in_trade >= max_bars and mfe_bps < required_mfe_bps


def cvd_reversal_exit(
    cvd_zscore: float,
    side: PositionSide,
    threshold: float = 1.0,
) -> bool:
    """Return ``True`` when CVD z-score turns against the open position.

    Parameters
    ----------
    cvd_zscore:
        Rolling z-score of cumulative volume delta at the current bar.
    side:
        Position direction — ``"long"`` or ``"short"``.
    threshold:
        Absolute z-score level at which the reversal signal is triggered.
        Must be positive.  Default: 1.0.

    Returns
    -------
    bool
        ``True`` → exit the position now.
    """
    _validate_side(side)
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")

    if side == "long":
        return float(cvd_zscore) < -threshold
    else:  # "short"
        return float(cvd_zscore) > threshold
