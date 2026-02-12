from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, Tuple, List
import pandas as pd
import yaml

@dataclass
class Match:
    canonical: str
    candidate: str
    score: float

TOKEN_SPLIT = re.compile(r"[_\-\s]+|(?<=[a-z])(?=[A-Z])")

def tokenize(name: str) -> List[str]:
    return [t.lower() for t in TOKEN_SPLIT.split(str(name)) if t]

def jaccard(a: List[str], b: List[str]) -> float:
    A, B = set(a), set(b)
    if not A or not B: return 0.0
    return len(A & B) / len(A | B)

def best_match(col: str, candidates: List[str]) -> Tuple[str, float]:
    toks = tokenize(col)
    best, score = None, 0.0
    for c in candidates:
        s = jaccard(toks, tokenize(c))
        if s > score: best, score = c, s
    return best, score

def load_ontology(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def build_candidate_strings(canonical: str, field_meta: dict) -> List[str]:
    cands = [canonical] + field_meta.get("synonyms", [])
    cands += field_meta.get("regex", [])
    return list(dict.fromkeys(cands))  # unique, keep order

def infer_mapping(df: pd.DataFrame, ontology: dict, min_score: float = 0.45) -> Dict[str, str]:
    """
    Return mapping: raw_col_name -> canonical_name for every column we can confidently map.
    Unmapped columns are left out so UI can ask user to resolve.
    """
    mapping = {}
    all_fields = {}

    for entity, meta in ontology["entities"].items():
        for canonical, field_meta in meta["fields"].items():
            all_fields[canonical] = build_candidate_strings(canonical, field_meta)

    for raw in df.columns:
        # regex pass first (if any candidate is a regex that matches)
        matched = False
        for canonical, cands in all_fields.items():
            for c in cands:
                if c.startswith(".*"):  # heuristic: treat as regex
                    if re.match(c, raw, flags=re.I):
                        mapping[raw] = canonical
                        matched = True
                        break
            if matched: break
        if matched: continue

        # similarity pass
        bm, sc, win = None, 0.0, None
        for canonical, cands in all_fields.items():
            best_cand, score = best_match(raw, cands)
            if score > sc:
                bm, sc, win = canonical, score, best_cand
        if sc >= min_score:
            mapping[raw] = bm

    return mapping

def apply_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """Rename columns; keep originals that are unmapped."""
    return df.rename(columns=mapping)

def coerce_dtypes(df: pd.DataFrame, ontology: dict) -> pd.DataFrame:
    """Try to coerce mapped columns into ontology dtypes."""
    canon_types = {}
    for entity, meta in ontology["entities"].items():
        for canonical, field_meta in meta["fields"].items():
            canon_types[canonical] = field_meta.get("dtype")

    for col, dt in canon_types.items():
        if col not in df.columns or dt is None: 
            continue
        try:
            if dt == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=False)
            elif dt == "float":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
            elif dt == "string":
                df[col] = df[col].astype(str)
        except Exception:
            pass
    return df
