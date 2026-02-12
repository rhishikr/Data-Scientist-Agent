# auto_detector.py
from __future__ import annotations
import os, re
from typing import Dict, List, Tuple
import pandas as pd

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def _alias_map(cfg: dict, table: str) -> Dict[str, str]:
    """Return map normalized_alias -> canonical_name for a table."""
    m = {}
    aliases = cfg["tables"][table].get("aliases", {})
    for canon, alist in aliases.items():
        for a in alist:
            m[_norm(a)] = canon
        # also include the canonical itself as an alias to itself
        m[_norm(canon)] = canon
    return m

def _score_table(df_cols: List[str], table: str, cfg: dict) -> Tuple[float, Dict[str, str]]:
    """
    Score how well a set of dataframe columns matches a table spec:
    - alias coverage (most important)
    - required field coverage (hard requirement weight)
    - filename hint (minor bonus handled in caller)
    Returns (score, resolved_mapping)
    """
    norm_cols = [_norm(c) for c in df_cols]
    alias_map = _alias_map(cfg, table)
    required = set(cfg["tables"][table].get("required", []))

    resolved = {}   # df_col -> canonical_name (when alias matches)
    alias_hits = 0  # how many columns matched to a canonical field

    # resolve by alias
    for raw, nc in zip(df_cols, norm_cols):
        if nc in alias_map:
            resolved[raw] = alias_map[nc]
            alias_hits += 1

    # required coverage
    canon_cols_present = set(resolved.values())
    req_hits = len(required.intersection(canon_cols_present))
    req_total = max(1, len(required))

    # unique canon coverage (avoid overcounting multiple raw cols to the same canon)
    canon_coverage = len(set(resolved.values()))

    # weights: required matters most, then general coverage
    # scale to 0..1
    req_score = req_hits / req_total
    cov_score = canon_coverage / max(1, len(alias_map))  # rough normalization

    # final score with weights (tweakable)
    score = 0.65 * req_score + 0.35 * cov_score

    return score, resolved

def guess_table(
    df: pd.DataFrame,
    cfg: dict,
    filename: str | None = None,
    min_confidence: float = 0.45,
) -> Tuple[str | None, float, Dict[str, str], Dict[str, float]]:
    """
    Returns:
      (best_table_or_None, confidence, resolved_mapping_for_best, all_scores_dict)
    If best score < min_confidence → returns (None, best_score, mapping, scores)
    """
    df_cols = list(df.columns)
    scores = {}
    best = (None, 0.0, {})  # (table, score, mapping)

    # filename signal (minor bonus)
    fname = (filename or "").lower()

    for table in cfg["tables"].keys():
        base_score, mapping = _score_table(df_cols, table, cfg)
        name_bonus = 0.05 if table in fname else 0.0
        final = min(1.0, base_score + name_bonus)
        scores[table] = final
        if final > best[1]:
            best = (table, final, mapping)

    if best[1] < min_confidence:
        return None, best[1], best[2], scores
    return best[0], best[1], best[2], scores
