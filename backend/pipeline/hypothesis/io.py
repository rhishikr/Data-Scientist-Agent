from __future__ import annotations
import os
import pandas as pd
from typing import Dict

def read_csv_folder(folder: str) -> Dict[str, pd.DataFrame]:
    """
    Reads all .csv files in folder into {stem: DataFrame}.
    Example: customers.csv -> key 'customers'
    """
    data: Dict[str, pd.DataFrame] = {}
    if not os.path.isdir(folder):
        return data

    for fname in os.listdir(folder):
        if not fname.lower().endswith(".csv"):
            continue
        path = os.path.join(folder, fname)
        key = os.path.splitext(fname)[0]
        try:
            df = pd.read_csv(path)
        except Exception:
            # fallback for weird encodings
            df = pd.read_csv(path, encoding="latin-1")
        data[key] = df
    return data
