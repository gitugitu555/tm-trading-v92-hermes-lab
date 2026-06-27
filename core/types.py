"""Shared data types for deterministic feature engines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Side = Literal["BUY", "SELL", "UNKNOWN"]


@dataclass(frozen=True)
class SignedTrade:
    ts_event: datetime
    exchange: str
    symbol: str
    price: float
    size_base: float
    notional_quote: float
    side: Side
    confidence: float
    method: str
    trade_id: str | None = None


@dataclass(frozen=True)
class BookSnapshot:
    ts_event: datetime
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class FeatureSnapshot:
    ts_event: datetime
    instrument: str
    cvd: float
    delta_velocity: float
    delta_acceleration: float
    vpin: float
    microprice: float | None
    book_imbalance: float
    queue_imbalance_top1: float | None
    queue_imbalance_top5: float | None
    queue_imbalance_top10: float | None
    queue_pressure_score: float | None
    microprice_drift_bps: float | None
    absorption: str
    spoof_regime: str
    iceberg_side: str
    whale_pressure: float
    reason_codes: tuple[str, ...]
