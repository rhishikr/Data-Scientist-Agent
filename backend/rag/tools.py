# backend/rag/tools.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
import glob
import pandas as pd


@dataclass
class DataTool:
    """
    POC in-memory data access layer for deterministic lookups.
    Loads all CSVs once and supports safe, exact queries (no LLM guessing).
    """
    tables: Dict[str, pd.DataFrame]

    @classmethod
    def from_csv_dir(cls, data_dir: Path) -> "DataTool":
        tables: Dict[str, pd.DataFrame] = {}
        for p in sorted(glob.glob(str(Path(data_dir) / "*.csv"))):
            fp = Path(p)
            tables[fp.name] = pd.read_csv(fp)
        return cls(tables=tables)

    def list_tables(self) -> Dict[str, Any]:
        return {
            name: {"rows": len(df), "cols": df.shape[1], "columns": list(df.columns)}
            for name, df in self.tables.items()
        }

    def lookup_value(
        self,
        table: str,
        key_col: str,
        key_val: str,
        target_col: str,
    ) -> Optional[Any]:
        """
        Exact row lookup:
          SELECT target_col FROM table WHERE key_col = key_val LIMIT 1

        Returns the value if found, else None.
        """
        if table not in self.tables:
            return None
        df = self.tables[table]
        if key_col not in df.columns or target_col not in df.columns:
            return None

        # Normalize to string compare for IDs like CUST1007
        series = df[key_col].astype(str)
        hits = df[series == str(key_val)]
        if hits.empty:
            return None
        return hits.iloc[0][target_col]
