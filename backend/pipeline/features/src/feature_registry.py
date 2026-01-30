from __future__ import annotations
from typing import Callable, Dict, List, Set
import pandas as pd
from dataclasses import dataclass, field

@dataclass
class Recipe:
    name: str
    requires: Set[str]           # canonical columns needed
    level: str                   # 'order', 'order_lines', 'customer', 'session'
    func: Callable[[pd.DataFrame], pd.DataFrame]
    description: str = ""

class FeatureRegistry:
    def __init__(self):
        self._recipes: Dict[str, Recipe] = {}

    def register(self, recipe: Recipe):
        if recipe.name in self._recipes:
            raise ValueError(f"Duplicate recipe {recipe.name}")
        self._recipes[recipe.name] = recipe

    def available_for(self, df: pd.DataFrame, level: str) -> List[Recipe]:
        cols = set(df.columns)
        return [r for r in self._recipes.values()
                if r.level == level and r.requires.issubset(cols)]

    def names(self):
        return list(self._recipes.keys())

REGISTRY = FeatureRegistry()

def recipe(name: str, requires: List[str], level: str, description: str = ""):
    def deco(fn):
        REGISTRY.register(Recipe(name, set(requires), level, fn, description))
        return fn
    return deco
