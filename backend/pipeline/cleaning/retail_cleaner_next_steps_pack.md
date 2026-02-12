# Retail Cleaner – Next Steps Pack

This package adds YAML-driven configuration, Great Expectations validation (with Data Docs), a Streamlit UI, and dbt schema tests on top of your cleaner. Copy these files into a repo and run the quick start below.

---

## 🧭 Quick Start

```bash
# 1) Create venv and install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) Run the Streamlit UI (upload CSV/Parquet → clean → download)
streamlit run streamlit_app.py

# 3) Clean via CLI
python retail_cleaner.py --input data/transactions.csv --table transactions --output out/ --report out/

# 4) Validate with Great Expectations (HTML docs in great_expectations/uncommitted/data_docs)
python ge_validate.py --table transactions --input out/transactions_transactions_clean.csv

# 5) (Optional) Run dbt tests in your warehouse after loading cleaned tables
# adjust profiles.yml before running
cd dbt && dbt test
```

---

## 📦 requirements.txt

```
pandas>=2.2
numpy>=1.26
pyyaml>=6.0.1
pandera>=0.20.0
streamlit>=1.39
great-expectations>=0.18.14
pyarrow>=16.1.0
```

---

## ⚙️ config/defaults.yaml

```yaml
version: 1
outlier_method: iqr  # iqr | mad

# Category normalizations (extend freely)
category_maps:
  transactions:
    payment_type:
      visa: card
      mastercard: card
      amex: card
      debit: card
      credit: card
      cash: cash
      paypal: paypal
      giftcard: giftcard
  web_analytics:
    device_type:
      m: mobile
      phone: mobile
      mobile: mobile
      desktop: desktop
      pc: desktop
    source:
      organic: organic
      paid: paid
      referral: referral
      email: email
      social: social
  shipments:
    delivery_status:
      delivered: delivered
      pending: pending
      failed: failed
      return: returned
  products:
    status:
      active: active
      inactive: inactive
      discontinued: discontinued

# Table specifications (subset shown; extend as needed)
tables:
  transactions:
    required: [date, store_id, order_id, sku, quantity, unit_price]
    recommended: [discount, promo_flag, payment_type, customer_id]
    aliases:
      date: [date, transaction_date, sold_at]
      store_id: [store_id, site_id, location_id]
      order_id: [order_id, txn_id, sale_id]
      sku: [sku, product_id, item_code]
      quantity: [quantity, qty, units]
      unit_price: [unit_price, price, sell_price]
      discount: [discount, disc, markdown]
      promo_flag: [promo_flag, on_promo, promotion, is_promo]
      payment_type: [payment_type, pay_type, tender_type]
      customer_id: [customer_id, cust_id, user_id]
    dtypes:
      date: datetime64[ns]
      store_id: string
      order_id: string
      sku: string
      quantity: Int64
      unit_price: float
      discount: float
      promo_flag: boolean
      payment_type: string
      customer_id: string
    primary_key: [order_id, sku]
    outlier_cols: [unit_price, quantity, discount]
    business_rules: [quantity>=0, unit_price>=0, discount>=0]

  inventory:
    required: [store_id, sku, date, opening_stock, inflow, outflow, closing_stock]
    recommended: [stock_value]
    aliases:
      store_id: [store_id, warehouse_id, location_id]
      sku: [sku, product_id, item_code]
      date: [date, as_of_date]
      opening_stock: [opening_stock, opening_qty, stock_open]
      inflow: [inflow, received, receipts]
      outflow: [outflow, issued, shipments, sold]
      closing_stock: [closing_stock, closing_qty, stock_close]
      stock_value: [stock_value, inventory_value]
    dtypes:
      store_id: string
      sku: string
      date: datetime64[ns]
      opening_stock: Int64
      inflow: Int64
      outflow: Int64
      closing_stock: Int64
      stock_value: float
    primary_key: [store_id, sku, date]
    outlier_cols: [opening_stock, inflow, outflow, closing_stock, stock_value]
    business_rules: [opening+inflow-outflow≈closing, nonnegative_all_ints]

  products:
    required: [sku, product_name, category, retail_price, status]
    recommended: [brand, subcategory, supplier_id, cost_price, launch_date]
    aliases:
      sku: [sku, product_id, item_code]
      product_name: [product_name, name, title]
      brand: [brand]
      category: [category, cat]
      subcategory: [subcategory, subcat]
      supplier_id: [supplier_id, vendor_id]
      cost_price: [cost_price, cost]
      retail_price: [retail_price, price, msrp]
      launch_date: [launch_date, introduced_on]
      status: [status, active_flag, state]
    dtypes:
      sku: string
      product_name: string
      brand: string
      category: string
      subcategory: string
      supplier_id: string
      cost_price: float
      retail_price: float
      launch_date: datetime64[ns]
      status: string
    primary_key: [sku]
    outlier_cols: [retail_price, cost_price]
    business_rules: [retail_price>=0, cost_price>=0, retail>=cost?warn]

  returns:
    required: [return_id, order_id, sku, return_date, refund_amount]
    recommended: [reason_code]
    aliases:
      return_id: [return_id, rma_id]
      order_id: [order_id, sale_id, txn_id]
      sku: [sku, product_id]
      reason_code: [reason_code, reason]
      return_date: [return_date, date]
      refund_amount: [refund_amount, refund, amount]
    dtypes:
      return_id: string
      order_id: string
      sku: string
      reason_code: string
      return_date: datetime64[ns]
      refund_amount: float
    primary_key: [return_id]
    outlier_cols: [refund_amount]
    business_rules: [refund_amount>=0]

  customers:
    required: [customer_id, signup_date]
    recommended: [gender, age_group, location, preferred_channel, lifetime_value, loyalty_tier]
    aliases:
      customer_id: [customer_id, cust_id, user_id]
      signup_date: [signup_date, joined_at]
      gender: [gender, sex]
      age_group: [age_group, age_band]
      location: [location, city_region_country]
      preferred_channel: [preferred_channel, fav_channel]
      lifetime_value: [lifetime_value, ltv]
      loyalty_tier: [loyalty_tier, tier]
    dtypes:
      customer_id: string
      signup_date: datetime64[ns]
      gender: string
      age_group: string
      location: string
      preferred_channel: string
      lifetime_value: float
      loyalty_tier: string
    primary_key: [customer_id]
    outlier_cols: [lifetime_value]
    business_rules: [lifetime_value>=0]

  web_analytics:
    required: [session_id, customer_id, page_views, time_spent]
    recommended: [device_type, source, cart_additions, checkout_flag]
    aliases:
      session_id: [session_id, visit_id]
      customer_id: [customer_id, user_id]
      page_views: [page_views, pages]
      time_spent: [time_spent, duration_seconds]
      device_type: [device_type, device]
      source: [source, utm_source, traffic_source]
      cart_additions: [cart_additions, adds_to_cart]
      checkout_flag: [checkout_flag, checked_out, is_checkout]
    dtypes:
      session_id: string
      customer_id: string
      page_views: Int64
      time_spent: float
      device_type: string
      source: string
      cart_additions: Int64
      checkout_flag: boolean
    primary_key: [session_id]
    outlier_cols: [page_views, time_spent, cart_additions]
    business_rules: [nonnegative_all_numeric]

  campaigns:
    required: [campaign_id, channel, start_date, end_date]
    recommended: [offer_type, target_segment, response_rate, sales_uplift]
    aliases:
      campaign_id: [campaign_id, cmp_id]
      channel: [channel]
      start_date: [start_date, from_date]
      end_date: [end_date, to_date]
      offer_type: [offer_type, offer]
      target_segment: [target_segment, segment]
      response_rate: [response_rate, resp_rate]
      sales_uplift: [sales_uplift, uplift]
    dtypes:
      campaign_id: string
      channel: string
      start_date: datetime64[ns]
      end_date: datetime64[ns]
      offer_type: string
      target_segment: string
      response_rate: float
      sales_uplift: float
    primary_key: [campaign_id]
    outlier_cols: [response_rate, sales_uplift]
    business_rules: [0<=response_rate<=1, start_date<=end_date]

  pricing:
    required: [sku, date, base_price]
    recommended: [promo_price, promotion_id, region_id]
    aliases:
      sku: [sku, product_id]
      date: [date, effective_date]
      base_price: [base_price, list_price]
      promo_price: [promo_price, discount_price]
      promotion_id: [promotion_id, promo_id]
      region_id: [region_id, region]
    dtypes:
      sku: string
      date: datetime64[ns]
      base_price: float
      promo_price: float
      promotion_id: string
      region_id: string
    primary_key: [sku, date, region_id]
    outlier_cols: [base_price, promo_price]
    business_rules: [base_price>=0, promo_price>=0, promo<=base?warn]

  purchase_orders:
    required: [po_id, supplier_id, sku, order_date]
    recommended: [delivery_date, ordered_qty, received_qty, cost_per_unit, payment_terms]
    aliases:
      po_id: [po_id, po_number]
      supplier_id: [supplier_id, vendor_id]
      sku: [sku, product_id]
      order_date: [order_date]
      delivery_date: [delivery_date, received_date]
      ordered_qty: [ordered_qty, qty_ordered]
      received_qty: [received_qty, qty_received]
      cost_per_unit: [cost_per_unit, unit_cost]
      payment_terms: [payment_terms, terms]
    dtypes:
      po_id: string
      supplier_id: string
      sku: string
      order_date: datetime64[ns]
      delivery_date: datetime64[ns]
      ordered_qty: Int64
      received_qty: Int64
      cost_per_unit: float
      payment_terms: string
    primary_key: [po_id, sku]
    outlier_cols: [ordered_qty, received_qty, cost_per_unit]
    business_rules: [ordered_qty>=0, received<=ordered?warn]

  shipments:
    required: [shipment_id, order_id, carrier, dispatch_date, delivery_date, delivery_status]
    recommended: [shipping_cost, region]
    aliases:
      shipment_id: [shipment_id, tracking_id]
      order_id: [order_id, sale_id, txn_id]
      carrier: [carrier, shipper]
      dispatch_date: [dispatch_date, shipped_at]
      delivery_date: [delivery_date, delivered_at]
      delivery_status: [delivery_status, status]
      shipping_cost: [shipping_cost, freight_cost]
      region: [region, destination_region]
    dtypes:
      shipment_id: string
      order_id: string
      carrier: string
      dispatch_date: datetime64[ns]
      delivery_date: datetime64[ns]
      delivery_status: string
      shipping_cost: float
      region: string
    primary_key: [shipment_id]
    outlier_cols: [shipping_cost]
    business_rules: [shipping_cost>=0, dispatch_date<=delivery_date]
```

---

## 🧠 retail_cleaner.py (YAML-driven)

> Drop-in replacement of the previous single-file cleaner. Loads `config/defaults.yaml`, then runs the same pipeline (aliases → date parsing → dtype casting → category maps → missing-data policy → business rules → de-dup → outliers → optional Pandera validation). Includes CLI & folder mode.

```python
# retail_cleaner.py
from __future__ import annotations
import os, json, argparse, yaml
import pandas as pd
from dataclasses import asdict
from retail_core import TABLES, clean_table, infer_table_type, AuditReport, load_config

__version__ = "rc-yaml-2025-10-30"

def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"): return pd.read_csv(path)
    if path.lower().endswith((".parquet", ".pq")): return pd.read_parquet(path)
    raise ValueError(f"Unsupported file: {path}")

def _write_any(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    (df.to_parquet(path, index=False) if path.endswith((".parquet",".pq")) else df.to_csv(path, index=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--table")
    ap.add_argument("--output")
    ap.add_argument("--report")
    ap.add_argument("--config", default="config/defaults.yaml")
    ap.add_argument("--outlier", default=None, choices=["iqr","mad"])  # override YAML
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.outlier: cfg["outlier_method"] = args.outlier

    if os.path.isdir(args.input):
        out_dir = args.output or os.path.join(args.input, "_cleaned")
        os.makedirs(out_dir, exist_ok=True)
        for fname in os.listdir(args.input):
            fp = os.path.join(args.input, fname)
            if not os.path.isfile(fp):
                continue
            try:
                df = _read_any(fp)
            except Exception:
                continue
            table = args.table or infer_table_type(df, filename=fname)
            if not table: table = "transactions"
            cleaned, rep = clean_table(df, table=table, cfg=cfg)
            stem, _ = os.path.splitext(fname)
            out_fp = os.path.join(out_dir, f"{stem}_{table}_clean.csv")
            rep_fp = os.path.join(out_dir, f"{stem}_{table}_report.json")
            _write_any(cleaned, out_fp)
            with open(rep_fp, "w") as f: json.dump(rep.asdict(), f, indent=2, default=str)
            print(f"[OK] {fname} -> {out_fp}")
        return

    # single file
    df = _read_any(args.input)
    table = args.table or infer_table_type(df, filename=args.input) or "transactions"
    cleaned, rep = clean_table(df, table=table, cfg=cfg)
    out_fp = args.output or os.path.splitext(args.input)[0] + f"_{table}_clean.csv"
    rep_fp = args.report or os.path.splitext(args.input)[0] + f"_{table}_report.json"
    _write_any(cleaned, out_fp)
    with open(rep_fp, "w") as f: json.dump(rep.asdict(), f, indent=2, default=str)
    print(json.dumps(rep.asdict(), indent=2, default=str))

if __name__ == "__main__":
    main()
```

> **Note:** `retail_core.py` below contains all the logic from your previous cleaner refactored to accept `cfg` from YAML.

---

## 🧩 retail_core.py (core logic)

```python
# retail_core.py
from __future__ import annotations
import os, re, json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Iterable
import pandas as pd
import numpy as np
import yaml

PANDERA_AVAILABLE = False
try:
    import pandera as pa
    PANDERA_AVAILABLE = True
except Exception:
    pass

__version__ = "rc-core-2025-10-30"

# ---------------- Config ----------------

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg

# TABLES will be derived from YAML at runtime
TABLES: Dict[str, dict] = {}

# -------------- Reporting --------------
@dataclass
class AuditReport:
    version: str = __version__
    table: str = ""
    rows_before: int = 0
    rows_after: int = 0
    columns_renamed: Dict[str, str] = field(default_factory=dict)
    missing_required: List[str] = field(default_factory=list)
    dates_fixed: int = 0
    dates_dropped: int = 0
    dtype_coercions: Dict[str, int] = field(default_factory=dict)
    duplicates_removed: int = 0
    pk_used: List[str] = field(default_factory=list)
    na_filled: Dict[str, int] = field(default_factory=dict)
    rows_dropped_for_required: int = 0
    outliers_removed: Dict[str, int] = field(default_factory=dict)
    outlier_method: str = "iqr"
    category_changes: Dict[str, Dict[str, str]] = field(default_factory=dict)
    rule_violations: Dict[str, int] = field(default_factory=dict)
    rule_warnings: Dict[str, int] = field(default_factory=dict)
    pandera_errors: List[str] = field(default_factory=list)
    def asdict(self): return asdict(self)

# -------------- Utilities --------------

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def _reverse_aliases(table_conf: dict) -> Dict[str, str]:
    out = {}
    for canon, alist in table_conf.get("aliases", {}).items():
        for a in alist:
            out[_norm(a)] = canon
    return out

def _resolve_columns(df: pd.DataFrame, table: str, cfg: dict) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    conf = cfg["tables"][table]
    rev = _reverse_aliases(conf)
    rename = {}
    for c in df.columns:
        key = _norm(c)
        if key in rev:
            rename[c] = rev[key]
    df2 = df.rename(columns=rename)
    missing = [r for r in conf.get("required", []) if r not in df2.columns]
    return df2, rename, missing

DATE_PATTERNS = [
    ("%Y-%m-%d", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("%Y-%m-%d %H:%M:%S", re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$")),
    ("%Y/%m/%d", re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")),
    ("%m/%d/%Y", re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")),
    ("%d-%m-%Y", re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")),
    ("%Y%m%d", re.compile(r"^\d{8}$")),
]

def _parse_dates(df: pd.DataFrame, cols: Iterable[str]) -> Tuple[pd.DataFrame, int, int]:
    fixed, dropped = 0, 0
    for col in cols:
        if col not in df.columns: continue
        series = df[col].astype("string")
        parsed = []
        for val in series:
            if val is None or pd.isna(val) or str(val).strip().upper() in {"", "NA", "N/A", "NULL", "NONE"}:
                parsed.append(pd.NaT); dropped += 1; continue
            sval = str(val).strip()
            dt = None
            for fmt, rgx in DATE_PATTERNS:
                if rgx.fullmatch(sval):
                    dt = pd.to_datetime(sval, format=fmt, errors="coerce"); break
            if dt is None or pd.isna(dt):
                dt = pd.to_datetime(sval, errors="coerce")
            if pd.isna(dt):
                parsed.append(pd.NaT); dropped += 1
            else:
                if not re.fullmatch(r"^\d{4}-\d{2}-\d{2}", sval): fixed += 1
                parsed.append(dt)
        df[col] = pd.to_datetime(parsed, errors="coerce")
    return df, fixed, dropped

def _to_bool(series: pd.Series) -> pd.Series:
    true_set, false_set = {"1","true","t","yes","y","on"}, {"0","false","f","no","n","off"}
    def cast(v):
        if v is None or pd.isna(v): return pd.NA
        s = str(v).strip().lower()
        if s in true_set: return True
        if s in false_set: return False
        try: return bool(float(s))
        except Exception: return pd.NA
    return series.astype("string").map(cast).astype("boolean")

def _cast_dtypes(df: pd.DataFrame, table: str, cfg: dict):
    coerced = {}
    for col, dt in cfg["tables"][table].get("dtypes", {}).items():
        if col not in df.columns: continue
        s = df[col]
        before = s.isna().sum()
        if dt == "datetime64[ns]": df[col] = pd.to_datetime(s, errors="coerce")
        elif dt == "boolean": df[col] = _to_bool(s)
        elif dt == "Int64": df[col] = pd.to_numeric(s, errors="coerce").round().astype("Int64")
        elif dt == "float": df[col] = pd.to_numeric(s, errors="coerce").astype("float")
        elif dt == "string": df[col] = s.astype("string").str.strip()
        after = df[col].isna().sum(); coerced[col] = int(max(0, after - before))
    return df, coerced

def _standardize_categories(df: pd.DataFrame, table: str, cfg: dict):
    changes = {}
    maps = cfg.get("category_maps", {}).get(table, {})
    for col, mapping in maps.items():
        if col not in df.columns: continue
        before = df[col].astype("string")
        lower = before.str.strip().str.lower()
        mapped = lower.map(mapping).fillna(lower)
        df[col] = mapped
        chg = {}
        for a, b in zip(before.fillna(""), mapped.fillna("")):
            if a != b: chg[str(a)] = str(b)
        if chg: changes[col] = chg
    return df, changes

def _fill_missing(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    req = [c for c in cfg["tables"][table].get("required", []) if c in df.columns]
    before = len(df)
    if req: df = df.dropna(subset=req)
    rep.rows_dropped_for_required = before - len(df)
    for col, dt in cfg["tables"][table].get("dtypes", {}).items():
        if col not in df.columns: continue
        if dt in ("float","Int64"):
            na = df[col].isna().sum()
            if na:
                med = pd.to_numeric(df[col], errors="coerce").median()
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(med if not np.isnan(med) else 0)
                rep.na_filled[col] = int(na)
        elif dt == "boolean":
            na = df[col].isna().sum()
            if na: df[col] = df[col].fillna(False); rep.na_filled[col] = int(na)
    return df

def _remove_duplicates(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    pk = cfg["tables"][table].get("primary_key")
    rep.pk_used = pk or []
    before = len(df)
    if pk and all(p in df.columns for p in pk):
        df = df.drop_duplicates(subset=pk, keep="last")
    else:
        df = df.drop_duplicates(keep="last")
    rep.duplicates_removed = before - len(df)
    return df

def _iqr_mask(s: pd.Series, k: float=1.5):
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0: return pd.Series([True]*len(s), index=s.index)
    low, high = q1 - k*iqr, q3 + k*iqr
    return (s>=low) & (s<=high)

def _mad_mask(s: pd.Series, z: float=5.0):
    med = s.median(); mad = np.median(np.abs(s - med))
    if mad == 0 or pd.isna(mad): return pd.Series([True]*len(s), index=s.index)
    zscore = 0.6745 * (s - med) / mad
    return zscore.abs() <= z

def _remove_outliers(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    cols = cfg["tables"][table].get("outlier_cols", [])
    method = cfg.get("outlier_method", "iqr"); rep.outlier_method = method
    for col in cols:
        if col not in df.columns: continue
        s = pd.to_numeric(df[col], errors="coerce")
        mask = _iqr_mask(s) if method == "iqr" else _mad_mask(s)
        removed = int((~mask & s.notna()).sum())
        if removed: rep.outliers_removed[col] = removed; df = df[mask | s.isna()]
    return df

def _apply_business_rules(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    rules = cfg["tables"][table].get("business_rules", [])
    vios, warns = {}, {}
    def count(mask, key, warn=False):
        cnt = int((~mask).sum());
        if cnt>0: (warns if warn else vios)[key] = cnt

    def nonneg(col):
        if col in df.columns:
            m = df[col].isna() | (pd.to_numeric(df[col], errors="coerce") >= 0)
            count(m, f"{col}>=0"); df.loc[~m, col] = 0

    for r in rules:
        if r == "quantity>=0": nonneg("quantity")
        if r == "unit_price>=0": nonneg("unit_price")
        if r == "discount>=0": nonneg("discount")
        if r == "nonnegative_all_numeric":
            for c in df.select_dtypes(include=["number"]).columns: nonneg(c)
        if r == "nonnegative_all_ints":
            for c in df.select_dtypes(include=["Int64"]).columns: nonneg(c)
        if r == "opening+inflow-outflow≈closing":
            need = {"opening_stock","inflow","outflow","closing_stock"}
            if need.issubset(df.columns):
                est = (df["opening_stock"].fillna(0)+df["inflow"].fillna(0)-df["outflow"].fillna(0))
                diff = (df["closing_stock"].fillna(0)-est).abs(); tol=1
                m = diff <= tol; count(m, "inventory_balance", warn=True)
                df.loc[df["closing_stock"].isna(), "closing_stock"] = est.loc[df["closing_stock"].isna()].round().astype("Int64")
        if r == "retail>=cost?warn" and {"retail_price","cost_price"}.issubset(df.columns):
            m = df["retail_price"].isna() | df["cost_price"].isna() | (df["retail_price"]>=df["cost_price"])
            count(m, "retail>=cost", warn=True)
        if r == "promo<=base?warn" and {"promo_price","base_price"}.issubset(df.columns):
            m = df["promo_price"].isna() | df["base_price"].isna() | (df["promo_price"]<=df["base_price"])
            count(m, "promo<=base", warn=True)
        if r == "0<=response_rate<=1" and "response_rate" in df.columns:
            m = df["response_rate"].between(0,1) | df["response_rate"].isna(); count(m, "response_rate_bounds"); df.loc[~m, "response_rate"] = df["response_rate"].clip(0,1)
        if r == "start_date<=end_date" and {"start_date","end_date"}.issubset(df.columns):
            m = df["start_date"].isna() | df["end_date"].isna() | (df["start_date"]<=df["end_date"]); count(m, "start<=end")
        if r == "dispatch_date<=delivery_date" and {"dispatch_date","delivery_date"}.issubset(df.columns):
            m = df["dispatch_date"].isna() | df["delivery_date"].isna() | (df["dispatch_date"]<=df["delivery_date"]); count(m, "dispatch<=delivery")

    rep.rule_violations, rep.rule_warnings = vios, warns
    return df

# ---------- Public API ----------

def clean_table(df: pd.DataFrame, table: str, cfg: dict):
    global TABLES
    TABLES = cfg.get("tables", {})

    rep = AuditReport(table=table, rows_before=len(df))
    df = df.copy(); df.columns = [str(c).strip() for c in df.columns]

    # 1) rename by aliases & check required
    df, ren, missing = _resolve_columns(df, table, cfg)
    rep.columns_renamed, rep.missing_required = ren, missing

    # 2) dates
    date_cols = [c for c in df.columns if "date" in c]
    df, fixed, dropped = _parse_dates(df, date_cols); rep.dates_fixed, rep.dates_dropped = fixed, dropped

    # 3) dtypes
    df, coerce = _cast_dtypes(df, table, cfg); rep.dtype_coercions = coerce

    # 4) categories
    df, chg = _standardize_categories(df, table, cfg); rep.category_changes = chg

    # 5) missing/impute
    df = _fill_missing(df, table, cfg, rep)

    # 6) business rules
    df = _apply_business_rules(df, table, cfg, rep)

    # 7) duplicates
    df = _remove_duplicates(df, table, cfg, rep)

    # 8) outliers
    df = _remove_outliers(df, table, cfg, rep)

    # 9) pandera validation
    if PANDERA_AVAILABLE:
        try:
            fields = {}
            for col, dt in cfg["tables"][table].get("dtypes", {}).items():
                if col not in df.columns: continue
                if dt == "string": fields[col] = pa.Column(pa.String, nullable=True)
                elif dt == "float": fields[col] = pa.Column(pa.Float, nullable=True)
                elif dt == "Int64": fields[col] = pa.Column(pa.Int64, nullable=True)
                elif dt == "boolean": fields[col] = pa.Column(pa.Boolean, nullable=True)
                elif dt == "datetime64[ns]": fields[col] = pa.Column(pa.DateTime, nullable=True)
            schema = pa.DataFrameSchema(fields, coerce=False)
            schema.validate(df, lazy=True)
        except Exception as e:
            rep.pandera_errors = [str(e)[:300]]

    rep.rows_after = len(df)
    return df, rep

# inference
_HINTS = [
    ("transactions", ["order_id","unit_price","quantity"]),
    ("inventory", ["opening_stock","closing_stock","inflow","outflow"]),
    ("products", ["product_name","retail_price","status"]),
    ("returns", ["return_id","refund_amount"]),
    ("customers", ["customer_id","signup_date"]),
    ("web_analytics", ["session_id","page_views","time_spent"]),
    ("campaigns", ["campaign_id","start_date","end_date"]),
    ("pricing", ["base_price","promo_price","promotion_id"]),
    ("purchase_orders", ["po_id","supplier_id","ordered_qty"]),
    ("shipments", ["shipment_id","delivery_status","shipping_cost"]),
]

def infer_table_type(df: pd.DataFrame, filename: Optional[str] = None) -> Optional[str]:
    if filename:
        name = os.path.basename(filename).lower()
        for t in TABLES:
            if t in name: return t
    for t, cols in _HINTS:
        if all(c in df.columns for c in cols): return t
    return None
```

---

## ✅ ge_validate.py (Great Expectations runner)

```python
# ge_validate.py
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
```

---

## 🖥️ streamlit_app.py (upload → clean → download)

```python
# streamlit_app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from retail_core import load_config, clean_table, infer_table_type

st.set_page_config(page_title="Retail Cleaner", layout="wide")

st.title("🧼 Retail Cleaner (YAML-driven)")
cfg_file = st.text_input("Config path", value="config/defaults.yaml")
cfg = load_config(cfg_file)

uploaded = st.file_uploader("Upload CSV or Parquet", type=["csv","parquet","pq"])
if uploaded:
    df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_parquet(uploaded)
    guess = infer_table_type(df, filename=uploaded.name) or st.selectbox("Select table", list(cfg["tables"].keys()))
    table = st.selectbox("Table type", list(cfg["tables"].keys()), index=list(cfg["tables"].keys()).index(guess) if guess in cfg["tables"] else 0)
    cleaned, report = clean_table(df, table=table, cfg=cfg)

    st.subheader("Report")
    st.json(report.asdict())

    st.subheader("Preview (first 100 rows)")
    st.dataframe(cleaned.head(100))

    # Download buttons
    csv = cleaned.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download cleaned CSV", data=csv, file_name=f"cleaned_{table}.csv", mime="text/csv")
```

---

## 🧪 dbt/models/schema.yml (sample tests)

```yaml
version: 2

models:
  - name: fct_transactions
    columns:
      - name: order_id
        tests: [not_null]
      - name: unit_price
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"
      - name: quantity
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

  - name: dim_products
    columns:
      - name: sku
        tests: [unique, not_null]
      - name: retail_price
        tests:
          - dbt_utils.expression_is_true:
              expression: ">= 0"
```

---

## 📝 README (excerpt)

- Edit `config/defaults.yaml` to align to brand-specific exports (Sephora/Zara/H&M).
- Add category mappings for bespoke values (e.g., new `payment_type`).
- The AuditReport JSON is agent-friendly: use `rule_violations`, `pandera_errors`, and `missing_required` to decide next actions.
- To enforce in-warehouse quality, adapt the dbt tests and run them nightly.

