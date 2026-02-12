from __future__ import annotations

from typing import Iterable, Optional

import numpy as np


def clean_numeric(values: Iterable) -> np.ndarray:
    arr = np.array(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    return arr


def knee_threshold(values: Iterable, min_n: int = 10) -> Optional[float]:
    """
    Data-driven threshold using "knee" (largest deviation from diagonal) on sorted values.
    Returns None if insufficient data.
    """
    x = clean_numeric(values)
    if x.size < min_n:
        return None

    s = np.sort(x)
    n = s.size

    # Normalize to [0,1] for stable geometry
    denom = (s.max() - s.min())
    xs = (s - s.min()) / (denom + 1e-12)
    ys = np.linspace(0.0, 1.0, n)

    # right-tail knee: maximize (ys - xs)
    diff = ys - xs
    idx = int(np.argmax(diff))
    return float(s[idx])


def two_knees(values: Iterable, min_n: int = 10) -> tuple[Optional[float], Optional[float]]:
    """
    Two-stage knee split: find a first knee; then find another knee within the right tail.
    Useful to split (at-risk, churn) from a single distribution.
    """
    first = knee_threshold(values, min_n=min_n)
    if first is None:
        return None, None

    x = clean_numeric(values)
    tail = x[x >= first]
    second = knee_threshold(tail, min_n=min_n) if tail.size >= min_n else None

    if second is None:
        return float(first), None

    # order them
    a = float(min(first, second))
    b = float(max(first, second))
    return a, b


def jenks_breaks(values: Iterable, k: int = 3, min_n: int = 12) -> Optional[list[float]]:
    """
    Jenks natural breaks for 1D values into k classes.
    Purely data-driven cut points; returns class breakpoints (k+1 values) or None.
    """
    x = clean_numeric(values)
    if x.size < min_n:
        return None
    x = np.sort(x)
    n = x.size

    # DP matrices
    mat1 = np.zeros((n + 1, k + 1), dtype=int)
    mat2 = np.full((n + 1, k + 1), np.inf, dtype=float)
    mat2[0, 0] = 0.0

    for i in range(1, n + 1):
        mat1[i, 1] = 1
        mat2[i, 1] = np.var(x[:i]) * (i - 1) if i > 1 else 0.0

    for cls in range(2, k + 1):
        for i in range(cls, n + 1):
            s1 = s2 = w = 0.0
            for m in range(i, cls - 1, -1):
                val = x[m - 1]
                s1 += val
                s2 += val * val
                w += 1.0
                v = s2 - (s1 * s1) / (w + 1e-12)
                if m - 1 >= 0:
                    if mat2[m - 1, cls - 1] + v < mat2[i, cls]:
                        mat2[i, cls] = mat2[m - 1, cls - 1] + v
                        mat1[i, cls] = m

    # backtrack breaks
    breaks = [0.0] * (k + 1)
    breaks[k] = float(x[-1])
    breaks[0] = float(x[0])

    idx = n
    for cls in range(k, 1, -1):
        m = mat1[idx, cls]
        breaks[cls - 1] = float(x[m - 1])
        idx = m - 1

    # enforce monotonic
    breaks = sorted(breaks)
    return breaks
