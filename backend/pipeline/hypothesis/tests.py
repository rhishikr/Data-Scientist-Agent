from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

def _safe_float(x) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        return float(x)
    except Exception:
        return None

def _clean_num(s: pd.Series) -> pd.Series:
    s2 = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return s2

def cramers_v(confusion: pd.DataFrame) -> Optional[float]:
    """
    Effect size for chi-square.
    """
    try:
        chi2 = stats.chi2_contingency(confusion)[0]
        n = confusion.to_numpy().sum()
        r, k = confusion.shape
        phi2 = chi2 / n
        return float(np.sqrt(phi2 / max(1, min(k - 1, r - 1))))
    except Exception:
        return None

def pearson_spearman(df: pd.DataFrame, x: str, y: str) -> List[Dict[str, Any]]:
    a = _clean_num(df[x])
    b = _clean_num(df[y])
    merged = pd.concat([a, b], axis=1).dropna()
    if len(merged) < 10:
        return []

    xvals = merged.iloc[:, 0].values
    yvals = merged.iloc[:, 1].values

    out = []
    r, p = stats.pearsonr(xvals, yvals)
    out.append({"test": "Pearson", "stat": _safe_float(r), "p_value": _safe_float(p)})

    r2, p2 = stats.spearmanr(xvals, yvals)
    out.append({"test": "Spearman", "stat": _safe_float(r2), "p_value": _safe_float(p2)})

    return out

def cat_vs_num(df: pd.DataFrame, cat: str, num: str) -> Dict[str, Any]:
    """
    Auto-select:
    - 2 groups: Welch t-test, plus nonparam Mann–Whitney U fallback
    - 3+ groups: ANOVA, plus nonparam Kruskal fallback
    """
    sub = df[[cat, num]].dropna()
    if sub.empty:
        return {}

    groups = []
    names = []
    for g, gdf in sub.groupby(cat):
        vals = _clean_num(gdf[num])
        if len(vals) >= 5:
            groups.append(vals.values)
            names.append(str(g))

    if len(groups) < 2:
        return {}

    if len(groups) == 2:
        t_stat, t_p = stats.ttest_ind(groups[0], groups[1], equal_var=False, nan_policy="omit")
        # nonparam
        try:
            u_stat, u_p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        except Exception:
            u_stat, u_p = (None, None)

        return {
            "test": "Welch t-test",
            "p_value": _safe_float(t_p),
            "stat": _safe_float(t_stat),
            "alt_test": "Mann-Whitney U",
            "alt_p_value": _safe_float(u_p),
            "groups": names,
            "n": int(len(sub)),
        }

    # 3+ groups
    f_stat, f_p = stats.f_oneway(*groups)
    try:
        h_stat, h_p = stats.kruskal(*groups)
    except Exception:
        h_stat, h_p = (None, None)

    return {
        "test": "ANOVA",
        "p_value": _safe_float(f_p),
        "stat": _safe_float(f_stat),
        "alt_test": "Kruskal",
        "alt_p_value": _safe_float(h_p),
        "groups": names,
        "n": int(len(sub)),
    }

def cat_vs_cat(df: pd.DataFrame, a: str, b: str) -> Dict[str, Any]:
    sub = df[[a, b]].dropna()
    if sub.empty:
        return {}
    table = pd.crosstab(sub[a], sub[b])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {}

    chi2, p, dof, exp = stats.chi2_contingency(table)
    return {
        "test": "Chi-square",
        "p_value": _safe_float(p),
        "stat": _safe_float(chi2),
        "dof": int(dof),
        "effect_size": cramers_v(table),
        "n": int(table.to_numpy().sum()),
    }

def bh_fdr(pvals: list[float | None]) -> list[float | None]:
    """
    Benjamini-Hochberg FDR correction (correct version).
    """
    # indices of valid p-values
    valid = [(i, p) for i, p in enumerate(pvals) if p is not None]

    if not valid:
        return [None for _ in pvals]

    # sort by p-value
    valid.sort(key=lambda x: x[1])
    m = len(valid)

    # compute raw adjusted
    qvals = [0.0] * m
    for rank, (idx, p) in enumerate(valid, start=1):
        qvals[rank - 1] = p * m / rank

    # enforce monotonicity (must be non-decreasing when moving backward)
    for i in range(m - 2, -1, -1):
        qvals[i] = min(qvals[i], qvals[i + 1])

    # cap at 1
    qvals = [min(q, 1.0) for q in qvals]

    # put back into original positions
    adj = [None] * len(pvals)
    for (rank_item, (idx, p)) in enumerate(valid):
        adj[idx] = float(qvals[rank_item])

    return adj
