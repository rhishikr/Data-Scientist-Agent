import pandas as pd
from scipy import stats

def run_tests(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame):
    out = []

    # Example: AOV differs by device_type (requires join)
    if "device_type" in customers.columns:
        tx = transactions.groupby("customer_id")["total_amount"].mean().reset_index().rename(columns={"total_amount":"aov"})
        joined = customers[["customer_id","device_type"]].merge(tx, on="customer_id", how="inner").dropna()

        groups = [g["aov"].values for _, g in joined.groupby("device_type")]
        if len(groups) >= 2 and all(len(g) >= 5 for g in groups):
            f, p = stats.f_oneway(*groups)
            out.append({
                "name": "Avg order value differs by device_type",
                "method": "ANOVA",
                "pValue": float(p),
                "result": "significant" if p < 0.05 else "not_significant"
            })

    return out
