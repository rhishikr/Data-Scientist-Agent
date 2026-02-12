from __future__ import annotations
import pandas as pd
from typing import Dict, List
from .schema_mapper import load_ontology, infer_mapping, apply_mapping, coerce_dtypes
from .feature_registry import REGISTRY
# Import recipes so they register
from . import feature_recipes  # noqa

class FeatureEngineer:

    def __init__(self, ontology_path: str):
        self.ontology = load_ontology(ontology_path)

    def auto_map(self, df: pd.DataFrame) -> Dict[str, str]:
        return infer_mapping(df, self.ontology)

    def standardize(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        df2 = apply_mapping(df, mapping)
        df2 = coerce_dtypes(df2, self.ontology)
        return df2

    def build(self, df: pd.DataFrame, level: str, selected: List[str] | None = None) -> pd.DataFrame:
        """
        level: 'order' | 'order_lines' | 'customer' | 'session'
        selected: list of recipe names to apply; if None, apply all available
        """
        available = REGISTRY.available_for(df, level)
        if selected:
            by_name = {r.name: r for r in available}
            recipes = [by_name[n] for n in selected if n in by_name]
        else:
            recipes = available

        out = df.copy()
        for r in recipes:
            out = r.func(out)
        return out

    def list_available(self, df: pd.DataFrame, level: str):
        return [r.name for r in REGISTRY.available_for(df, level)]
