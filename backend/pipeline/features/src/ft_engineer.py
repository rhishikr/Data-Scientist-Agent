# src/fea/ft_engineer.py

import pandas as pd
import featuretools as ft
import re


class TableMetadata:
    def __init__(self, name, dataframe):
        self.name = name
        self.df = dataframe
        self.primary_key = None
        self.time_index = None


class AutoFTFeatureEngineer:

    def __init__(self, dfs_depth=2):
        self.dfs_depth = dfs_depth

    # -------------------------------------
    # 1. Detect primary key
    # -------------------------------------
    def detect_primary_key(self, df):
        id_like = [c for c in df.columns if re.search(r"(id|_id|key)$", c.lower())]
        for col in id_like:
            if df[col].nunique() == len(df):
                return col

        for col in df.columns:
            if df[col].nunique() == len(df):
                return col

        return None

    # -------------------------------------
    # 2. Detect datetime columns
    # -------------------------------------
    def detect_time_index(self, df):
        for col in df.columns:
            try:
                result = pd.to_datetime(df[col], errors="raise")
                if result.nunique() > 5:
                    return col
            except:
                pass
        return None

    # -------------------------------------
    # 3. Detect foreign key relationships
    # -------------------------------------
    def detect_relationships(self, tables):
        relationships = []

        for parent in tables:
            for child in tables:
                if parent.name == child.name:
                    continue

                if parent.primary_key and parent.primary_key in child.df.columns:
                    relationships.append((parent, child, parent.primary_key))

        return relationships

    # -------------------------------------
    # 4. Build EntitySet
    # -------------------------------------
    def build_entityset(self, tables, relationships):
        es = ft.EntitySet(id="auto_entityset")

        for t in tables:
            df = t.df.copy()

            # synthetic primary key if needed
            if t.primary_key is None:
                t.primary_key = f"{t.name}_pk"
                df[t.primary_key] = range(len(df))

            es = es.add_dataframe(
                dataframe_name=t.name,
                dataframe=df,
                index=t.primary_key,
                time_index=t.time_index
            )

        # add relationships
        for parent, child, key in relationships:
            es = es.add_relationship(
                parent_dataframe_name=parent.name,
                parent_column_name=key,
                child_dataframe_name=child.name,
                child_column_name=key
            )

        return es

    # -------------------------------------
    # 5. Build DFS features for ALL tables
    # -------------------------------------
    def build_for_all_tables(self, uploaded_dict):
        tables = []

        # A: Create table metadata
        for fname, df in uploaded_dict.items():
            name = fname.replace(".csv", "")
            t = TableMetadata(name=name, dataframe=df)

            # Detect primary key
            t.primary_key = self.detect_primary_key(df)

            # Detect REAL datetime time index
            dt_col = self.detect_time_index(df)
            if dt_col:
                df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
                t.time_index = dt_col
            else:
                t.time_index = None  # <-- IMPORTANT FIX

            tables.append(t)

        # B: Detect relationships
        relationships = self.detect_relationships(tables)

        # C: Build entityset
        es = self.build_entityset(tables, relationships)

        # D: DFS for each entity
        output = {}
        for t in tables:
            features, defs = ft.dfs(
                entityset=es,
                target_dataframe_name=t.name,
                max_depth=self.dfs_depth,
                agg_primitives=[
                    "sum", "mean", "median", "max", "min",
                    "std", "count", "num_unique"
                ],
                trans_primitives=[
                    "day", "month", "year", "weekday", "hour"
                ],
            )

            output[t.name] = features.reset_index()

        return output
