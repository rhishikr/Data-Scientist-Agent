from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Tuple

def infer_column_types(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """
    Returns (numeric_cols, categorical_cols)
    """
    numeric_cols: List[str] = []
    categorical_cols: List[str] = []

    for c in df.columns:
        s = df[c]
        if pd.api.types.is_bool_dtype(s):
            categorical_cols.append(c)
            continue
        if pd.api.types.is_numeric_dtype(s):
            numeric_cols.append(c)
            continue

        # try coerce to numeric; if mostly numeric -> numeric
        coerced = pd.to_numeric(s, errors="coerce")
        ratio_numeric = coerced.notna().mean()
        if ratio_numeric >= 0.85:
            numeric_cols.append(c)
        else:
            categorical_cols.append(c)

    # prune ID-like columns from hypothesis spam
    categorical_cols = [c for c in categorical_cols if not _looks_like_id(df[c])]

    return numeric_cols, categorical_cols

def _looks_like_id(series: pd.Series) -> bool:
    """
    Heuristic: if almost all values unique OR looks like SKU/CUST/ORD ids.
    """
    s = series.dropna().astype(str)
    if s.empty:
        return True
    uniq_ratio = s.nunique() / len(s)
    sample = " ".join(s.head(20).tolist()).upper()
    if uniq_ratio > 0.95:
        return True
    if any(tok in sample for tok in ["SKU", "CUST", "ORD", "ID"]):
        return True
    return False

def cap_categories(df: pd.DataFrame, col: str, max_levels: int = 12) -> pd.Series:
    """
    Buckets rare categories into 'Other' so Chi-square/ANOVA is feasible.
    """
    s = df[col].astype("string")
    vc = s.value_counts(dropna=True)
    keep = set(vc.head(max_levels).index)
    return s.where(s.isin(keep), other="Other")
