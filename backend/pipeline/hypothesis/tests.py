from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    Effect size for chi-square test.
    """
    try:
        chi2 = stats.chi2_contingency(confusion)[0]
        n = confusion.to_numpy().sum()
        r, k = confusion.shape
        if n == 0:
            return None
        phi2 = chi2 / n
        denom = max(1, min(k - 1, r - 1))
        return float(np.sqrt(phi2 / denom))
    except Exception:
        return None


def cohens_d(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    """
    Cohen's d effect size for 2 groups.
    """
    try:
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        if len(a) < 2 or len(b) < 2:
            return None

        ma, mb = a.mean(), b.mean()
        sa, sb = a.std(ddof=1), b.std(ddof=1)
        # pooled std
        s_pooled = np.sqrt(((len(a) - 1) * sa**2 + (len(b) - 1) * sb**2) / (len(a) + len(b) - 2))
        if s_pooled == 0:
            return None
        return float((ma - mb) / s_pooled)
    except Exception:
        return None


def eta_squared_oneway(groups: List[np.ndarray]) -> Optional[float]:
    """
    Eta-squared effect size for one-way ANOVA.
    """
    try:
        # Flatten all values
        all_vals = np.concatenate(groups)
        if len(all_vals) < 3:
            return None

        grand_mean = all_vals.mean()

        ss_between = 0.0
        ss_total = float(((all_vals - grand_mean) ** 2).sum())

        for g in groups:
            if len(g) == 0:
                continue
            ss_between += len(g) * float((g.mean() - grand_mean) ** 2)

        if ss_total == 0:
            return None
        return float(ss_between / ss_total)
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
    - 2 groups: Welch t-test + Mann–Whitney U, with Cohen's d effect size
    - 3+ groups: ANOVA + Kruskal, with eta-squared effect size
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

    # 2-group case
    if len(groups) == 2:
        t_stat, t_p = stats.ttest_ind(groups[0], groups[1], equal_var=False, nan_policy="omit")
        try:
            u_stat, u_p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        except Exception:
            u_stat, u_p = (None, None)

        d = cohens_d(groups[0], groups[1])

        return {
            "test": "Welch t-test",
            "p_value": _safe_float(t_p),
            "stat": _safe_float(t_stat),
            "alt_test": "Mann-Whitney U",
            "alt_p_value": _safe_float(u_p),
            "groups": names,
            "n": int(len(sub)),
            "effect_size": _safe_float(d),  # Cohen's d
            "notes": "2 groups",
        }

    # 3+ groups case
    f_stat, f_p = stats.f_oneway(*groups)
    try:
        h_stat, h_p = stats.kruskal(*groups)
    except Exception:
        h_stat, h_p = (None, None)

    eta2 = eta_squared_oneway(groups)

    return {
        "test": "ANOVA",
        "p_value": _safe_float(f_p),
        "stat": _safe_float(f_stat),
        "alt_test": "Kruskal",
        "alt_p_value": _safe_float(h_p),
        "groups": names,
        "n": int(len(sub)),
        "effect_size": _safe_float(eta2),  # eta-squared
        "notes": f"{len(groups)} groups",
    }


def cat_vs_cat(df: pd.DataFrame, a: str, b: str) -> Dict[str, Any]:
    sub = df[[a, b]].dropna()
    if sub.empty:
        return {}

    table = pd.crosstab(sub[a], sub[b])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {}

    chi2, p, dof, _exp = stats.chi2_contingency(table)
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
    valid = [(i, p) for i, p in enumerate(pvals) if p is not None]
    if not valid:
        return [None for _ in pvals]

    valid.sort(key=lambda x: x[1])
    m = len(valid)

    qvals = [0.0] * m
    for rank, (idx, p) in enumerate(valid, start=1):
        qvals[rank - 1] = p * m / rank

    # enforce monotonicity
    for i in range(m - 2, -1, -1):
        qvals[i] = min(qvals[i], qvals[i + 1])

    qvals = [min(q, 1.0) for q in qvals]

    adj = [None] * len(pvals)
    for pos, (idx, _p) in enumerate(valid):
        adj[idx] = float(qvals[pos])

    return adj
