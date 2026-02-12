from __future__ import annotations

from typing import Optional

import numpy as np

from .math_utils import jenks_breaks


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def confidence_score(
    coverage_count: int,
    universe_count: int,
    support_count: int,
    support_universe: int,
) -> float:
    """
    Confidence is a continuous score driven by:
    - Coverage: how many entities are affected
    - Support: how much significant hypothesis support exists (relative to all significant in that dataset)
    No fixed thresholds; smooth transforms only.
    """
    if universe_count <= 0:
        base = 0.5
    else:
        cov = coverage_count / universe_count
        base = 1.0 - np.exp(-6.0 * cov)

    if support_universe <= 0:
        sup = 0.0
    else:
        frac = support_count / support_universe
        sup = 1.0 - np.exp(-6.0 * frac)

    return clamp01(0.6 * float(base) + 0.4 * float(sup))


def severity_from_metric(
    metric_value: Optional[float],
    reference_values: list[float],
) -> str:
    """
    Severity label from a metric (e.g., revenue share, prevalence) using natural breaks (Jenks).
    If metric_value is missing, fall back to prevalence-like reference handling.
    """
    if metric_value is None or not np.isfinite(metric_value):
        metric_value = 0.0

    ref = [v for v in reference_values if np.isfinite(v)]
    if len(ref) < 12:
        # Not enough to create stable breaks -> relative rank only
        # (still no business thresholds; just "best effort")
        ref_sorted = sorted(ref)
        if not ref_sorted:
            return "low"
        rank = sum(1 for v in ref_sorted if v <= metric_value) / len(ref_sorted)
        if rank >= 2/3:
            return "high"
        if rank >= 1/3:
            return "medium"
        return "low"

    breaks = jenks_breaks(ref, k=3)
    if not breaks or len(breaks) != 4:
        # same rank fallback
        ref_sorted = sorted(ref)
        rank = sum(1 for v in ref_sorted if v <= metric_value) / len(ref_sorted)
        if rank >= 2/3:
            return "high"
        if rank >= 1/3:
            return "medium"
        return "low"

    b0, b1, b2, b3 = breaks
    if metric_value <= b1:
        return "low"
    if metric_value <= b2:
        return "medium"
    return "high"
