# backend/rag/tools.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Iterable, Union
import glob
import re

import pandas as pd


Number = Union[int, float]


@dataclass
class DataTool:
    """
    Production-friendly in-memory CSV analytics layer.

    What this gives you (deterministic, no hallucinations):
    - Loads CSVs recursively (supports backend/data/cleaned_data, featured_data, etc.)
    - Exact lookups
    - Basic "SQL-level" analytics: filters, groupby+agg, top-k, max/min, joins
    - Safe guards: table/column validation, row limits, column allowlists

    What this does NOT do by itself:
    - Decide which operation to run from a natural language question.
      (That’s the job of your service layer + LLM planner.)
    """

    tables: Dict[str, pd.DataFrame]
    # Optional: map aliases ("customers" -> "customers.csv")
    aliases: Dict[str, str]

    # ---------- Construction ----------

    @classmethod
    def from_csv_dir(
        cls,
        data_dir: Path,
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        dtype_backend: str = "numpy_nullable",
    ) -> "DataTool":
        """
        Load CSVs from a directory.

        - If recursive=True, loads **/*.csv (so subfolders are included).
        - include_patterns/exclude_patterns accept regex patterns matched against file paths.
        - dtype_backend "numpy_nullable" keeps ints nullable (good for real-world data).
        """
        data_dir = Path(data_dir)

        pattern = str(data_dir / ("**/*.csv" if recursive else "*.csv"))
        paths = sorted(glob.glob(pattern, recursive=recursive))

        if include_patterns:
            inc = [re.compile(p) for p in include_patterns]
            paths = [p for p in paths if any(r.search(p) for r in inc)]
        if exclude_patterns:
            exc = [re.compile(p) for p in exclude_patterns]
            paths = [p for p in paths if not any(r.search(p) for r in exc)]

        tables: Dict[str, pd.DataFrame] = {}
        aliases: Dict[str, str] = {}

        for p in paths:
            fp = Path(p)
            name = fp.name  # e.g., customers.csv
            df = pd.read_csv(fp, dtype_backend=dtype_backend)

            tables[name] = df

            # Basic aliasing:
            # "customers" -> "customers.csv", "cleaned_data/customers" -> "customers.csv"
            stem = fp.stem  # customers
            aliases.setdefault(stem, name)
            # add folder-based alias to help disambiguate if needed
            rel = fp.relative_to(data_dir).as_posix()
            aliases.setdefault(rel.replace(".csv", ""), name)

        return cls(tables=tables, aliases=aliases)

    # ---------- Helpers / Validation ----------

    def _resolve_table(self, table: str) -> Optional[str]:
        """Accepts 'customers.csv' or 'customers' or relative alias."""
        if table in self.tables:
            return table
        return self.aliases.get(table)

    def _get_df(self, table: str) -> Optional[pd.DataFrame]:
        t = self._resolve_table(table)
        if not t:
            return None
        return self.tables.get(t)

    def _require_df(self, table: str) -> pd.DataFrame:
        df = self._get_df(table)
        if df is None:
            raise KeyError(f"Unknown table '{table}'. Available: {sorted(self.tables.keys())}")
        return df

    def _require_cols(self, df: pd.DataFrame, cols: Iterable[str], table: str) -> None:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns {missing} in table '{table}'. Available: {list(df.columns)}")

    @staticmethod
    def _normalize_scalar(x: Any) -> Any:
        """Normalize pandas/numpy scalars to native python types for JSON friendliness."""
        if pd.isna(x):
            return None
        # numpy scalars
        if hasattr(x, "item"):
            try:
                return x.item()
            except Exception:
                pass
        return x

    # ---------- Introspection ----------

    def list_tables(self) -> Dict[str, Any]:
        return {
            name: {
                "rows": int(len(df)),
                "cols": int(df.shape[1]),
                "columns": list(df.columns),
            }
            for name, df in self.tables.items()
        }

    def table_schema(self, table: str) -> Dict[str, Any]:
        df = self._require_df(table)
        return {
            "table": self._resolve_table(table),
            "rows": int(len(df)),
            "cols": int(df.shape[1]),
            "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
        }

    # ---------- Basic retrieval ----------

    def head(self, table: str, n: int = 5) -> List[Dict[str, Any]]:
        df = self._require_df(table)
        n = max(1, min(int(n), 100))
        return df.head(n).to_dict(orient="records")

    def sample(self, table: str, n: int = 5, seed: int = 42) -> List[Dict[str, Any]]:
        df = self._require_df(table)
        n = max(1, min(int(n), 100))
        if len(df) == 0:
            return []
        return df.sample(min(n, len(df)), random_state=seed).to_dict(orient="records")

    def lookup_value(
        self,
        table: str,
        key_col: str,
        key_val: Any,
        target_col: str,
    ) -> Optional[Any]:
        """
        Exact row lookup:
          SELECT target_col FROM table WHERE key_col = key_val LIMIT 1
        """
        df = self._get_df(table)
        if df is None:
            return None
        if key_col not in df.columns or target_col not in df.columns:
            return None

        series = df[key_col].astype(str)
        hits = df[series == str(key_val)]
        if hits.empty:
            return None
        return self._normalize_scalar(hits.iloc[0][target_col])

    # ---------- Filters (SQL WHERE-ish) ----------

    def filter_rows(
        self,
        table: str,
        conditions: List[Dict[str, Any]],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Apply AND-ed conditions and return up to `limit` rows.

        Each condition is:
          {"col": "total_amount", "op": ">", "value": 100}
        Supported ops: ==, !=, >, >=, <, <=, contains, startswith, endswith, in
        """
        df = self._require_df(table)
        limit = max(1, min(int(limit), 1000))

        mask = pd.Series([True] * len(df))
        for cond in conditions:
            col = cond["col"]
            op = cond["op"]
            val = cond.get("value")
            self._require_cols(df, [col], table)

            s = df[col]

            if op == "==":
                mask &= s.astype(str) == str(val) if s.dtype == "object" else (s == val)
            elif op == "!=":
                mask &= s.astype(str) != str(val) if s.dtype == "object" else (s != val)
            elif op == ">":
                mask &= s > val
            elif op == ">=":
                mask &= s >= val
            elif op == "<":
                mask &= s < val
            elif op == "<=":
                mask &= s <= val
            elif op == "contains":
                mask &= s.astype(str).str.contains(str(val), na=False)
            elif op == "startswith":
                mask &= s.astype(str).str.startswith(str(val), na=False)
            elif op == "endswith":
                mask &= s.astype(str).str.endswith(str(val), na=False)
            elif op == "in":
                if not isinstance(val, list):
                    raise ValueError(f"'in' operator requires list value, got: {type(val)}")
                mask &= s.isin(val)
            else:
                raise ValueError(f"Unsupported op '{op}'")

        out = df[mask].head(limit)
        return out.to_dict(orient="records")

    # ---------- Aggregations (SQL GROUP BY / MAX / SUM / TOP K) ----------

    def max_value(self, table: str, col: str) -> Optional[Any]:
        df = self._require_df(table)
        self._require_cols(df, [col], table)
        if len(df) == 0:
            return None
        return self._normalize_scalar(df[col].max())

    def min_value(self, table: str, col: str) -> Optional[Any]:
        df = self._require_df(table)
        self._require_cols(df, [col], table)
        if len(df) == 0:
            return None
        return self._normalize_scalar(df[col].min())

    def sum_value(self, table: str, col: str) -> Number:
        df = self._require_df(table)
        self._require_cols(df, [col], table)
        if len(df) == 0:
            return 0
        v = df[col].sum()
        return self._normalize_scalar(v) or 0

    def group_aggregate(
        self,
        table: str,
        group_by: List[str],
        aggregations: Dict[str, Tuple[str, str]],
        # aggregations: {"total_spend": ("total_amount", "sum")}
        order_by: Optional[Tuple[str, str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        GROUP BY with multiple aggregations.

        - group_by: ["customer_id"]
        - aggregations: {"total_spend": ("total_amount", "sum")}
          supported aggs: sum, mean, max, min, count, nunique
        - order_by: ("total_spend", "desc") or ("total_spend", "asc")
        """
        df = self._require_df(table)
        limit = max(1, min(int(limit), 1000))

        # Validate columns
        agg_cols = [src for (src, _) in aggregations.values()]
        self._require_cols(df, list(group_by) + agg_cols, table)

        # Build agg dict for pandas
        agg_dict = {}
        for out_name, (src_col, agg_fn) in aggregations.items():
            if agg_fn not in {"sum", "mean", "max", "min", "count", "nunique"}:
                raise ValueError(f"Unsupported agg '{agg_fn}' for '{out_name}'")
            agg_dict[out_name] = (src_col, agg_fn)

        out = df.groupby(group_by, dropna=False).agg(**agg_dict).reset_index()

        if order_by:
            col, direction = order_by
            if col not in out.columns:
                raise KeyError(f"order_by column '{col}' not in result columns: {list(out.columns)}")
            ascending = direction.lower() == "asc"
            out = out.sort_values(by=col, ascending=ascending)

        return out.head(limit).to_dict(orient="records")

    def top_k(
        self,
        table: str,
        group_by: List[str],
        metric_col: str,
        metric_agg: str = "sum",
        k: int = 5,
        metric_name: str = "metric",
    ) -> List[Dict[str, Any]]:
        """
        Convenience method:
        Returns top-k groups ranked by an aggregated metric.

        Example:
          Most popular product (units sold):
            top_k("transactions.csv", ["sku"], "quantity", "sum", k=1, metric_name="units_sold")
        """
        res = self.group_aggregate(
            table=table,
            group_by=group_by,
            aggregations={metric_name: (metric_col, metric_agg)},
            order_by=(metric_name, "desc"),
            limit=max(1, int(k)),
        )
        return res

    # ---------- Joins (simple, controlled) ----------

    def join(
        self,
        left_table: str,
        right_table: str,
        left_on: str,
        right_on: str,
        how: str = "inner",
        select: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Controlled join between two tables.

        - select: list of columns to return from the joined result (optional)
        - limit: max rows to return (prevents huge payloads)
        """
        left = self._require_df(left_table)
        right = self._require_df(right_table)

        self._require_cols(left, [left_on], left_table)
        self._require_cols(right, [right_on], right_table)

        if how not in {"inner", "left", "right", "outer"}:
            raise ValueError(f"Unsupported join type '{how}'")

        joined = left.merge(right, how=how, left_on=left_on, right_on=right_on, suffixes=("_left", "_right"))

        if select:
            missing = [c for c in select if c not in joined.columns]
            if missing:
                raise KeyError(f"Missing selected columns {missing}. Available: {list(joined.columns)}")
            joined = joined[select]

        limit = max(1, min(int(limit), 1000))
        return joined.head(limit).to_dict(orient="records")
