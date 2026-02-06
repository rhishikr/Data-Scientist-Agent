from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

import numpy as np

from .math_utils import knee_threshold


@dataclass
class HypothesisIndex:
    """
    Index hypotheses for fast retrieval:
    - dataset -> list of rows
    - dataset+variable -> list of rows
    """
    by_dataset: dict[str, list[dict[str, Any]]]
    by_dataset_var: dict[tuple[str, str], list[dict[str, Any]]]


def build_hypothesis_index(rows: list[dict[str, Any]]) -> HypothesisIndex:
    by_ds: dict[str, list[dict[str, Any]]] = {}
    by_dsv: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for r in rows:
        ds = str(r.get("dataset", "")).strip()
        x = str(r.get("x", "")).strip()
        y = str(r.get("y", "")).strip()
        if not ds or not x or not y:
            continue

        by_ds.setdefault(ds, []).append(r)

        by_dsv.setdefault((ds, x), []).append(r)
        by_dsv.setdefault((ds, y), []).append(r)

    return HypothesisIndex(by_dataset=by_ds, by_dataset_var=by_dsv)


def _num(v: Any) -> float:
    try:
        if v is None:
            return float("nan")
        return float(v)
    except Exception:
        return float("nan")


def relevance_score(r: dict[str, Any]) -> float:
    """
    Data-driven scoring:
    - bigger |effect| is better
    - smaller p_adj is better
    - bigger n is better

    Uses smooth transforms; no fixed thresholds.
    """
    eff = abs(_num(r.get("effect_size", r.get("stat"))))
    p = _num(r.get("p_adj", r.get("p_value")))
    n = _num(r.get("n"))

    # p might be 0 in some outputs -> stabilize with tiny epsilon (algorithmic)
    p = p if np.isfinite(p) else 1.0
    n = n if np.isfinite(n) else 0.0

    # higher is better
    score = eff * (-np.log10(p + 1e-300)) * np.log1p(max(n, 0.0))
    if not np.isfinite(score):
        return 0.0
    return float(score)


def select_relevant_support(
    idx: HypothesisIndex,
    dataset: str,
    variables: Iterable[str],
    must_be_significant: bool = True,
) -> list[dict[str, Any]]:
    """
    Pull all significant hypotheses involving any of the variables, then select
    the most relevant using knee on relevance scores (no fixed top-k).
    """
    cand: list[dict[str, Any]] = []
    seen = set()

    for v in variables:
        key = (dataset, v)
        for r in idx.by_dataset_var.get(key, []):
            if must_be_significant and not bool(r.get("significant", False)):
                continue
            rid = (r.get("dataset"), r.get("x"), r.get("y"), r.get("test"))
            if rid in seen:
                continue
            seen.add(rid)
            cand.append(r)

    if not cand:
        return []

    scored = [(relevance_score(r), r) for r in cand]
    scored.sort(key=lambda t: t[0], reverse=True)

    scores = [s for s, _ in scored if np.isfinite(s) and s > 0]
    if not scores:
        return [r for _, r in scored]

    cut = knee_threshold(scores)
    if cut is None:
        # If knee cannot be computed, return all sorted (still significant-only).
        return [r for _, r in scored]

    return [r for s, r in scored if s >= cut]


def summarize_support_for_doc(rows: list[dict[str, Any]]) -> list[str]:
    """
    Create plain-English bullet lines. We keep it compact automatically
    by taking only rows above knee threshold already.
    """
    lines: list[str] = []
    for r in rows:
        ds = r.get("dataset")
        x = r.get("x")
        y = r.get("y")
        test = r.get("test")
        n = r.get("n")
        p = r.get("p_adj", r.get("p_value"))
        eff = r.get("effect_size", r.get("stat"))
        lines.append(
            f"- {ds}: {x} vs {y} ({test}) | n={n} | adj_p={p} | effect={eff}"
        )
    return lines
