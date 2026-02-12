import argparse, os
import pandas as pd
from great_expectations.dataset import PandasDataset

class RetailDS(PandasDataset):
    _data_asset_type = "RetailDataset"

    def expect_nonnegative(self, column):
        return self.expect_column_values_to_be_between(column, min_value=0, mostly=0.99)

    def expect_percentage(self, column):
        return self.expect_column_values_to_be_between(column, min_value=0, max_value=1, mostly=0.99)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--table", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    gdf = RetailDS(df)

    if args.table == "transactions":
        gdf.expect_column_values_to_not_be_null("order_id")
        gdf.expect_nonnegative("unit_price")
        gdf.expect_nonnegative("quantity")
    if args.table == "campaigns":
        gdf.expect_percentage("response_rate")

    res = gdf.validate()
    print(res)
