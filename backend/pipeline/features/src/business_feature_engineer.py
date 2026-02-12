# src/fea/business_feature_engineer.py

from typing import Dict
import pandas as pd
import numpy as np


class BusinessFeatureEngineer:
    """
    Retail business-logic feature engineering.

    - Multi-table aware (customers + products + transactions)
    - User chooses target entity: "customers", "products", or "transactions"
    """

    # -----------------------------
    # Public API
    # -----------------------------
    def build_features(self, entities: Dict[str, pd.DataFrame], target: str) -> pd.DataFrame:
        """
        entities: {"customers": df or None, "products": df or None, "transactions": df or None}
        target: "customers" | "products" | "transactions"
        """
        customers = entities.get("customers")
        products = entities.get("products")
        transactions = entities.get("transactions")

        # Clean column names
        if customers is not None:
            customers = self._clean_columns(customers.copy())
        if products is not None:
            products = self._clean_columns(products.copy())
        if transactions is not None:
            transactions = self._clean_columns(transactions.copy())

        # Standardize schema (unify column names like customer_id, product_id, etc.)
        customers, products, transactions = self._standardize_schema(customers, products, transactions)

        if target == "customers":
            if transactions is None:
                raise ValueError("Customer-level features require a transactions table.")
            return self._customer_features(customers, transactions)
        elif target == "products":
            if transactions is None:
                raise ValueError("Product-level features require a transactions table.")
            return self._product_features(products, transactions)
        elif target == "transactions":
            if transactions is None:
                raise ValueError("Transaction-level features require a transactions table.")
            return self._transaction_features(transactions, customers, products)
        else:
            raise ValueError(f"Unknown target entity: {target}")

    # -----------------------------
    # Helpers: cleaning / schema
    # -----------------------------
    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _find_col(self, cols, patterns):
        """
        Find first column whose name contains any of the pattern substrings.
        """
        for c in cols:
            for p in patterns:
                if p in c:
                    return c
        return None

    def _standardize_schema(
        self,
        customers: pd.DataFrame | None,
        products: pd.DataFrame | None,
        transactions: pd.DataFrame | None,
    ):
        # --- customers ---
        if customers is not None:
            cols = list(customers.columns)
            cust_id_col = self._find_col(cols, ["customer_id", "cust_id", "customer", "cust", "user_id", "user"])
            if cust_id_col and cust_id_col != "customer_id":
                customers = customers.rename(columns={cust_id_col: "customer_id"})

        # --- products ---
        if products is not None:
            cols = list(products.columns)
            prod_id_col = self._find_col(cols, ["product_id", "sku", "item_id", "product", "item"])
            if prod_id_col and prod_id_col != "product_id":
                products = products.rename(columns={prod_id_col: "product_id"})

            stock_col = self._find_col(cols, ["stock", "inventory", "on_hand"])
            if stock_col and stock_col != "stock":
                products = products.rename(columns={stock_col: "stock"})

        # --- transactions ---
        if transactions is not None:
            cols = list(transactions.columns)

            cust_id_col = self._find_col(cols, ["customer_id", "cust_id", "customer", "cust", "user_id", "user"])
            if cust_id_col and cust_id_col != "customer_id":
                transactions = transactions.rename(columns={cust_id_col: "customer_id"})

            prod_id_col = self._find_col(cols, ["product_id", "sku", "item_id", "product", "item"])
            if prod_id_col and prod_id_col != "product_id":
                transactions = transactions.rename(columns={prod_id_col: "product_id"})

            order_id_col = self._find_col(
                cols, ["order_id", "transaction_id", "order", "txn_id", "invoice", "sale_id"]
            )
            if order_id_col and order_id_col != "order_id":
                transactions = transactions.rename(columns={order_id_col: "order_id"})

            dt_col = self._find_col(
                cols,
                [
                    "order_datetime",
                    "order_timestamp",
                    "order_date",
                    "timestamp",
                    "datetime",
                    "date_time",
                    "time",
                    "date",
                ],
            )
            if dt_col and dt_col != "order_datetime":
                transactions = transactions.rename(columns={dt_col: "order_datetime"})
            if "order_datetime" in transactions.columns:
                transactions["order_datetime"] = pd.to_datetime(
                    transactions["order_datetime"], errors="coerce"
                )

            qty_col = self._find_col(cols, ["quantity", "qty", "units", "items"])
            if qty_col and qty_col != "quantity":
                transactions = transactions.rename(columns={qty_col: "quantity"})

            price_col = self._find_col(cols, ["unit_price", "price", "amount", "unit_cost"])
            if price_col and price_col != "unit_price":
                transactions = transactions.rename(columns={price_col: "unit_price"})

            discount_col = self._find_col(cols, ["discount", "disc", "markdown"])
            if discount_col and discount_col != "discount":
                transactions = transactions.rename(columns={discount_col: "discount"})

            total_col = self._find_col(cols, ["total_amount", "order_value", "revenue", "sales_amount", "total"])
            if total_col and total_col != "total_amount":
                transactions = transactions.rename(columns={total_col: "total_amount"})

        return customers, products, transactions

    # -----------------------------
    # CUSTOMER FEATURES
    # -----------------------------
    def _customer_features(self, customers: pd.DataFrame | None, transactions: pd.DataFrame) -> pd.DataFrame:
        t = transactions.copy()

        if "customer_id" not in t.columns:
            raise ValueError("Transactions table must contain a customer_id-like column.")

        # Base customer frame
        if customers is not None and "customer_id" in customers.columns:
            f = customers.copy()
        else:
            # Derive customers from transactions
            f = pd.DataFrame({"customer_id": t["customer_id"].dropna().unique()})

        # Line amount
        if "total_amount" in t.columns:
            t["line_amount"] = t["total_amount"]
        else:
            if "quantity" in t.columns and "unit_price" in t.columns:
                t["line_amount"] = t["quantity"] * t["unit_price"]
            else:
                t["line_amount"] = np.nan

        # Total orders
        orders_per_customer = t.groupby("customer_id")["order_id"].nunique().rename("total_orders") \
            if "order_id" in t.columns else t.groupby("customer_id").size().rename("total_orders")

        # Total quantity
        if "quantity" in t.columns:
            qty_per_customer = t.groupby("customer_id")["quantity"].sum().rename("total_quantity")
        else:
            qty_per_customer = None

        # Total spend
        if "line_amount" in t.columns:
            spend_per_customer = t.groupby("customer_id")["line_amount"].sum().rename("total_spend")
            avg_order_value = (spend_per_customer / orders_per_customer).rename("avg_order_value")
        else:
            spend_per_customer = None
            avg_order_value = None

        # Recency (days since last order)
        if "order_datetime" in t.columns:
            max_date = t["order_datetime"].max()
            last_order = t.groupby("customer_id")["order_datetime"].max()
            recency = (max_date - last_order).dt.days.rename("recency_days")
        else:
            recency = None

        # Frequency (orders per active period)
        if "order_datetime" in t.columns:
            first_order = t.groupby("customer_id")["order_datetime"].min()
            active_days = (last_order - first_order).dt.days.replace(0, 1)
            frequency = (orders_per_customer / active_days).rename("orders_per_active_day")
        else:
            frequency = None

        # Monetary = total_spend (RFM component)
        monetary = spend_per_customer.rename("monetary_value") if spend_per_customer is not None else None

        # Most purchased product_id
        if "product_id" in t.columns:
            top_product = (
                t.groupby(["customer_id", "product_id"])
                .size()
                .reset_index(name="count")
                .sort_values(["customer_id", "count"], ascending=[True, False])
                .drop_duplicates("customer_id")
                .set_index("customer_id")["product_id"]
                .rename("top_product_id")
            )
        else:
            top_product = None

        # Merge everything
        f = f.merge(orders_per_customer, on="customer_id", how="left")

        if qty_per_customer is not None:
            f = f.merge(qty_per_customer, on="customer_id", how="left")
        if spend_per_customer is not None:
            f = f.merge(spend_per_customer, on="customer_id", how="left")
        if avg_order_value is not None:
            f = f.merge(avg_order_value, on="customer_id", how="left")
        if recency is not None:
            f = f.merge(recency, on="customer_id", how="left")
        if frequency is not None:
            f = f.merge(frequency, on="customer_id", how="left")
        if monetary is not None:
            f = f.merge(monetary, on="customer_id", how="left")
        if top_product is not None:
            f = f.merge(top_product, on="customer_id", how="left")

        return f

    # -----------------------------
    # PRODUCT FEATURES
    # -----------------------------
    def _product_features(self, products: pd.DataFrame | None, transactions: pd.DataFrame) -> pd.DataFrame:
        t = transactions.copy()

        if "product_id" not in t.columns:
            raise ValueError("Transactions table must contain a product_id-like column for product features.")

        # Base product frame
        if products is not None and "product_id" in products.columns:
            f = products.copy()
        else:
            f = pd.DataFrame({"product_id": t["product_id"].dropna().unique()})

        # line amount
        if "total_amount" in t.columns:
            t["line_amount"] = t["total_amount"]
        else:
            if "quantity" in t.columns and "unit_price" in t.columns:
                t["line_amount"] = t["quantity"] * t["unit_price"]
            else:
                t["line_amount"] = np.nan

        # Total times purchased
        times_purchased = t.groupby("product_id").size().rename("times_purchased")

        # Total quantity sold
        if "quantity" in t.columns:
            total_qty = t.groupby("product_id")["quantity"].sum().rename("total_quantity_sold")
        else:
            total_qty = None

        # Total revenue
        if "line_amount" in t.columns:
            total_revenue = t.groupby("product_id")["line_amount"].sum().rename("total_revenue")
            avg_order_value = (total_revenue / times_purchased).rename("avg_order_value_per_order")
        else:
            total_revenue = None
            avg_order_value = None

        # Number of unique customers
        if "customer_id" in t.columns:
            unique_customers = t.groupby("product_id")["customer_id"].nunique().rename("unique_customers")
        else:
            unique_customers = None

        # Demand volatility (std of quantity per order)
        if "quantity" in t.columns:
            qty_std = t.groupby("product_id")["quantity"].std().rename("quantity_std")
        else:
            qty_std = None

        f = f.merge(times_purchased, on="product_id", how="left")
        if total_qty is not None:
            f = f.merge(total_qty, on="product_id", how="left")
        if total_revenue is not None:
            f = f.merge(total_revenue, on="product_id", how="left")
        if avg_order_value is not None:
            f = f.merge(avg_order_value, on="product_id", how="left")
        if unique_customers is not None:
            f = f.merge(unique_customers, on="product_id", how="left")
        if qty_std is not None:
            f = f.merge(qty_std, on="product_id", how="left")

        return f

    # -----------------------------
    # TRANSACTION FEATURES
    # -----------------------------
    def _transaction_features(
        self,
        transactions: pd.DataFrame,
        customers: pd.DataFrame | None,
        products: pd.DataFrame | None,
    ) -> pd.DataFrame:
        t = transactions.copy()

        # line_amount
        if "total_amount" in t.columns:
            t["line_amount"] = t["total_amount"]
        else:
            if "quantity" in t.columns and "unit_price" in t.columns:
                t["line_amount"] = t["quantity"] * t["unit_price"]
            else:
                t["line_amount"] = np.nan

        # basic cart size
        if "order_id" in t.columns and "product_id" in t.columns:
            cart_size = t.groupby("order_id")["product_id"].nunique().rename("cart_unique_items")
            t = t.merge(cart_size, on="order_id", how="left")

        # merge in customer info (lightly)
        if customers is not None and "customer_id" in customers.columns and "customer_id" in t.columns:
            cust_cols = [c for c in customers.columns if c not in ["customer_id"]]
            t = t.merge(customers[["customer_id"] + cust_cols], on="customer_id", how="left", suffixes=("", "_cust"))

        # merge in product info (lightly)
        if products is not None and "product_id" in products.columns and "product_id" in t.columns:
            prod_cols = [c for c in products.columns if c not in ["product_id"]]
            t = t.merge(products[["product_id"] + prod_cols], on="product_id", how="left", suffixes=("", "_prod"))

        return t
