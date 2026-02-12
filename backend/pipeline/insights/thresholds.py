# backend/pipeline/insights/thresholds.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


@dataclass
class Thresholds:
    churn_recency_days: Optional[float] = None
    at_risk_recency_days: Optional[float] = None
    engaged_session_min: Optional[float] = None
    engaged_wishlist_count: Optional[float] = None
    low_rating: Optional[float] = None
    high_discount: Optional[float] = None
    high_demand_purchases: Optional[float] = None
    low_stock: Optional[float] = None


def _clean_numeric(values: Iterable) -> np.ndarray:
    arr = np.array(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    return arr


def knee_threshold(values: Iterable) -> Optional[float]:
    """
    Fully data-driven threshold via "knee"/largest deviation from line on sorted values.
    No fixed percentile constants.
    Returns None if insufficient data.
    """
    x = _clean_numeric(values)
    if x.size < 10:
        return None

    s = np.sort(x)
    n = s.size

    # Normalize to [0,1] for stable geometry
    xs = (s - s.min()) / (s.max() - s.min() + 1e-12)
    ys = np.linspace(0.0, 1.0, n)

    # Distance from diagonal line (0,0)->(1,1)
    # For monotonic sorted arrays, knee ~ max(ys - xs) or max(xs - ys) depending direction.
    # We want a threshold separating "high" tail -> use maximum (ys - xs) for heavy right tail.
    diff = ys - xs
    idx = int(np.argmax(diff))
    return float(s[idx])


def two_knees(values: Iterable) -> tuple[Optional[float], Optional[float]]:
    """
    Derive two thresholds (e.g., at-risk and churn) without hardcoding:
    - First knee on full distribution
    - Second knee on the right tail beyond first knee (if enough data)
    """
    first = knee_threshold(values)
    if first is None:
        return None, None

    x = _clean_numeric(values)
    tail = x[x >= first]
    second = knee_threshold(tail) if tail.size >= 10 else None

    # Ensure ordering (at_risk <= churn)
    at_risk = float(min(first, second)) if second is not None else float(first)
    churn = float(max(first, second)) if second is not None else None
    return at_risk, churn


def robust_center_threshold(values: Iterable, direction: str = "high") -> Optional[float]:
    """
    Data-driven threshold using robust center (median) and scale (MAD),
    without fixed multipliers by selecting the strongest separation point in z-space.
    """
    x = _clean_numeric(values)
    if x.size < 10:
        return None

    med = np.median(x)
    mad = np.median(np.abs(x - med)) + 1e-12
    z = (x - med) / (1.4826 * mad)

    # Choose threshold as knee in z scores (separating outliers) then map back to value
    z_thr = knee_threshold(z)
    if z_thr is None:
        return None

    if direction == "high":
        candidates = x[z >= z_thr]
        return float(np.min(candidates)) if candidates.size else None
    else:
        candidates = x[z <= z_thr]
        return float(np.max(candidates)) if candidates.size else None
