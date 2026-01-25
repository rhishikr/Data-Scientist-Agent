import os
import pandas as pd

def _read_csv(path: str) -> pd.DataFrame:
    # Your sample uses tab-separated columns (looks like TSV). This handles both.
    return pd.read_csv(path, sep=None, engine="python")

def load_all(data_dir: str):
    customers = _read_csv(os.path.join(data_dir, "customers.csv"))
    transactions = _read_csv(os.path.join(data_dir, "transactions.csv"))

    # optional
    payments_path = os.path.join(data_dir, "payments.csv")
    products_path = os.path.join(data_dir, "products.csv")

    payments = _read_csv(payments_path) if os.path.exists(payments_path) else None
    products = _read_csv(products_path) if os.path.exists(products_path) else None

    return {
        "customers": customers,
        "transactions": transactions,
        "payments": payments,
        "products": products,
    }
