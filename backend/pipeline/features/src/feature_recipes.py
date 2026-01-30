import math
import pandas as pd
from .feature_registry import recipe

# ------------------------
# Helpers
# ------------------------
def _sdiv(a, b):
    """Safe divide: returns 0 when denom is 0 or NaN."""
    return (a.astype(float)).where(b.astype(float).replace(0, pd.NA).notna(), 0) / b.replace(0, pd.NA)

def _month_to_num(series: pd.Series) -> pd.Series:
    """
    Convert month names/abbrevs (e.g., 'Feb') or numbers into 1..12.
    Unknowns -> NaN.
    """
    lookup = {
        'jan':1,'january':1,'01':1,'1':1,
        'feb':2,'february':2,'02':2,'2':2,
        'mar':3,'march':3,'03':3,'3':3,
        'apr':4,'april':4,'04':4,'4':4,
        'may':5,'05':5,'5':5,
        'jun':6,'june':6,'06':6,'6':6,
        'jul':7,'july':7,'07':7,'7':7,
        'aug':8,'august':8,'08':8,'8':8,
        'sep':9,'sept':9,'september':9,'09':9,'9':9,
        'oct':10,'october':10,'10':10,
        'nov':11,'november':11,'11':11,
        'dec':12,'december':12,'12':12
    }
    s = series.astype(str).str.strip().str.lower().map(lookup)
    return pd.to_numeric(s, errors="coerce")

def _one_hot_topN(df: pd.DataFrame, col: str, top_n: int = 10, prefix: str | None = None) -> pd.DataFrame:
    """One-hot encode top N frequent categories; all others collapsed to 'other'."""
    if col not in df.columns:
        return df
    prefix = prefix or col
    vc = df[col].astype(str).value_counts(dropna=False)
    keep = set(vc.head(top_n).index)
    tmp = df[col].astype(str).where(df[col].astype(str).isin(keep), 'other')
    dummies = pd.get_dummies(tmp, prefix=prefix, dtype=int)
    return pd.concat([df, dummies], axis=1)

# ------------------------
# ORDER-LEVEL  (kept minimal)
# ------------------------
@recipe("order_hour_of_day", requires=["order_datetime"], level="order",
        description="Hour of purchase; daypart effects.")
def order_hour_of_day(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.copy()
    out["order_hour_of_day"] = out["order_datetime"].dt.hour
    return out

@recipe("is_weekend_order", requires=["order_datetime"], level="order",
        description="Weekend purchase flag.")
def is_weekend_order(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.copy()
    out["is_weekend_order"] = out["order_datetime"].dt.dayofweek.isin([5,6]).astype(int)
    return out

# ------------------------
# ORDER-LINE  (kept minimal)
# ------------------------
@recipe("line_net_unit_price", requires=["net_line_amount","quantity"], level="order_lines",
        description="Net per-unit price after discounts.")
def line_net_unit_price(lines: pd.DataFrame) -> pd.DataFrame:
    out = lines.copy()
    q = out["quantity"].replace(0, pd.NA)
    out["line_net_unit_price"] = (out["net_line_amount"] / q).fillna(0.0)
    return out

@recipe("line_discount_pct", requires=["unit_price","net_line_amount","quantity"], level="order_lines",
        description="Discount percent per line item.")
def line_discount_pct(lines: pd.DataFrame) -> pd.DataFrame:
    out = lines.copy()
    denom = (out["unit_price"] * out["quantity"]).replace(0, pd.NA)
    out["line_discount_pct"] = (1.0 - (out["net_line_amount"] / denom)).clip(0,1).fillna(0.0)
    return out

# ------------------------
# CUSTOMER-LEVEL (kept minimal RFM-like)
# ------------------------
@recipe("customer_recency_days", requires=["order_datetime","customer_id"], level="order",
        description="Days since last order at record time.")
def customer_recency_days(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.sort_values(["customer_id","order_datetime"]).copy()
    out["prev_order_dt"] = out.groupby("customer_id")["order_datetime"].shift(1)
    out["customer_recency_days"] = (out["order_datetime"] - out["prev_order_dt"]).dt.days.fillna(9999)
    out.drop(columns=["prev_order_dt"], inplace=True)
    return out

@recipe("customer_frequency_30d", requires=["order_datetime","customer_id"], level="order",
        description="Rolling 30-day orders per customer.")
def customer_frequency_30d(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.sort_values(["customer_id","order_datetime"]).copy()
    out["one"] = 1
    out["customer_frequency_30d"] = (
        out.set_index("order_datetime").groupby("customer_id")["one"].rolling("30D").sum()
          .reset_index(level=0, drop=True).fillna(0).astype(int)
    )
    out.drop(columns=["one"], inplace=True)
    return out

# ------------------------
# SESSION-LEVEL (INDUSTRY PACK)
# ------------------------

# 1) Core engagement totals
@recipe("session_totals", requires=[], level="session",
        description="Total pages & duration using any available columns.")
def session_totals(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    # pages: prefer session_pages; else sum of component pages
    pages_cols = [c for c in ["session_pages","admin_pages","info_pages"] if c in out.columns]
    if "session_pages" in out.columns:
        out["total_pages"] = out["session_pages"].astype(float)
    elif pages_cols:
        out["total_pages"] = out[pages_cols].astype(float).sum(axis=1)
    else:
        out["total_pages"] = 0.0

    # duration: prefer session_duration; else sum of components
    dur_cols = [c for c in ["session_duration","admin_duration","info_duration"] if c in out.columns]
    if "session_duration" in out.columns:
        out["total_duration"] = out["session_duration"].astype(float)
    elif dur_cols:
        out["total_duration"] = out[dur_cols].astype(float).sum(axis=1)
    else:
        out["total_duration"] = 0.0
    return out

# 2) Per-page & ratio features (zero-safe)
@recipe("session_ratios", requires=["total_pages","total_duration"], level="session",
        description="Avg time per page + component ratios when present.")
def session_ratios(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    # basic
    out["avg_time_per_page"] = _sdiv(out["total_duration"], out["total_pages"]).fillna(0.0)

    # component ratios when present
    if "admin_pages" in out.columns:
        out["admin_page_ratio"] = _sdiv(out["admin_pages"], out["total_pages"]).fillna(0.0)
    if "info_pages" in out.columns:
        out["info_page_ratio"]  = _sdiv(out["info_pages"],  out["total_pages"]).fillna(0.0)
    if "session_pages" in out.columns:
        # Online Shoppers: session_pages came from ProductRelated = product-focused pages
        out["product_page_ratio"] = _sdiv(out["session_pages"], out["total_pages"]).fillna(0.0)

    if "admin_duration" in out.columns:
        out["admin_time_ratio"] = _sdiv(out["admin_duration"], out["total_duration"]).fillna(0.0)
    if "info_duration" in out.columns:
        out["info_time_ratio"]  = _sdiv(out["info_duration"],  out["total_duration"]).fillna(0.0)
    if "session_duration" in out.columns:
        out["product_time_ratio"] = _sdiv(out["session_duration"], out["total_duration"]).fillna(0.0)
    return out

# 3) Funnel quality / efficiency
@recipe("session_efficiency", requires=[], level="session",
        description="Value per page, value per second, exit/bounce metrics.")
def session_efficiency(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    if "page_value" in out.columns:
        if "total_pages" in out.columns:
            out["value_per_page"] = _sdiv(out["page_value"], out["total_pages"]).fillna(0.0)
        if "total_duration" in out.columns:
            out["value_per_second"] = _sdiv(out["page_value"], out["total_duration"]).fillna(0.0)
    if "bounce_rate" in out.columns:
        out["stickiness"] = (1.0 / out["bounce_rate"].replace(0, pd.NA)).fillna(0.0).clip(0, 1000)
    if "exit_rate" in out.columns and "bounce_rate" in out.columns:
        out["exit_to_bounce"] = _sdiv(out["exit_rate"], out["bounce_rate"]).fillna(0.0).clip(0, 1000)
    return out

# 4) Occasion & time encodings
@recipe("session_time_features", requires=[], level="session",
        description="Weekend flag passthrough + month cyclical sin/cos.")
def session_time_features(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    # passthrough weekend if present (normalize to 0/1)
    if "weekend" in out.columns:
        out["weekend_flag"] = pd.to_numeric(out["weekend"], errors="coerce").fillna(0).clip(0,1).astype(int)

    # Month cyclical from month_name
    if "month_name" in out.columns:
        m = _month_to_num(out["month_name"])
        out["month_num"] = m
        # sin/cos encoding
        with pd.option_context('mode.use_inf_as_na', True):
            out["month_sin"] = (2 * math.pi * m / 12.0).apply(math.sin)
            out["month_cos"] = (2 * math.pi * m / 12.0).apply(math.cos)
    return out

# 5) Promo & interaction effects
@recipe("session_interactions", requires=[], level="session",
        description="Interactions: (special_day x value), (weekend x value).")
def session_interactions(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    if "page_value" in out.columns and "special_day" in out.columns:
        out["specialday_value"] = out["page_value"] * out["special_day"]
    if "page_value" in out.columns and ("weekend_flag" in out.columns or "weekend" in out.columns):
        wf = out["weekend_flag"] if "weekend_flag" in out.columns else pd.to_numeric(out["weekend"], errors="coerce").fillna(0)
        out["weekend_value"] = out["page_value"] * wf
    return out

# 6) Categorical encodings (top-N one-hots)
@recipe("session_onehots", requires=[], level="session",
        description="One-hot for browser, OS, traffic, visitor_type, region (top 10 each).")
def session_onehots(s: pd.DataFrame) -> pd.DataFrame:
    out = s.copy()
    for col, prefix in [
        ("browser", "br"),
        ("operating_system", "os"),
        ("traffic_source", "src"),
        ("visitor_type", "vis"),
        ("region", "reg"),
    ]:
        out = _one_hot_topN(out, col, top_n=10, prefix=prefix)
    return out
