# src/fea/entity_detector.py

from typing import Dict, Tuple
import pandas as pd


class EntityDetector:
    """
    Detect which uploaded tables are:
      - customers
      - products
      - transactions

    Uses BOTH filename patterns and column name patterns.
    """

    def __init__(self) -> None:
        self.customer_name_keywords = ["customer", "cust", "client", "shopper", "user"]
        self.product_name_keywords = ["product", "sku", "item", "inventory", "catalog", "stock"]
        self.txn_name_keywords = ["order", "transaction", "sale", "sales", "purchase", "fact", "events"]

        self.customer_col_keywords = ["customer", "cust", "client", "user", "shopper"]
        self.product_col_keywords = ["product", "sku", "item", "brand", "category", "unit_cost", "unit_price"]
        self.txn_col_keywords = [
            "order", "transaction", "invoice", "receipt",
            "qty", "quantity", "amount", "price", "total", "discount",
            "date", "time", "timestamp"
        ]

    def detect_entities(
        self, raw_tables: Dict[str, pd.DataFrame]
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
        """
        Parameters
        ----------
        raw_tables : dict
            {filename: df}

        Returns
        -------
        entities : dict
            {"customers": df or None, "products": df or None, "transactions": df or None}
        mapping : dict
            {"customers": filename or None, ...}
        """
        scores = {fname: {"customers": 0, "products": 0, "transactions": 0}
                  for fname in raw_tables.keys()}

        # Score each table for each possible role
        for fname, df in raw_tables.items():
            lower_name = fname.lower()
            cols = [c.lower() for c in df.columns]

            # --- filename-based scores ---
            for kw in self.customer_name_keywords:
                if kw in lower_name:
                    scores[fname]["customers"] += 3
            for kw in self.product_name_keywords:
                if kw in lower_name:
                    scores[fname]["products"] += 3
            for kw in self.txn_name_keywords:
                if kw in lower_name:
                    scores[fname]["transactions"] += 3

            # --- column-based scores ---
            for c in cols:
                # customers
                for kw in self.customer_col_keywords:
                    if kw in c:
                        scores[fname]["customers"] += 1
                # products
                for kw in self.product_col_keywords:
                    if kw in c:
                        scores[fname]["products"] += 1
                # transactions
                for kw in self.txn_col_keywords:
                    if kw in c:
                        scores[fname]["transactions"] += 1

            # extra bonus for "transaction-like": has both customer & product id-ish columns
            if any(kw in " ".join(cols) for kw in self.customer_col_keywords) and \
               any(kw in " ".join(cols) for kw in self.product_col_keywords):
                scores[fname]["transactions"] += 3

        # Pick best file per role
        entities: Dict[str, pd.DataFrame] = {"customers": None, "products": None, "transactions": None}
        mapping: Dict[str, str] = {"customers": None, "products": None, "transactions": None}

        for role in ["customers", "products", "transactions"]:
            best_file = None
            best_score = 0
            for fname, sc in scores.items():
                if sc[role] > best_score:
                    best_score = sc[role]
                    best_file = fname
            if best_file is not None and best_score > 0:
                entities[role] = raw_tables[best_file]
                mapping[role] = best_file

        return entities, mapping
