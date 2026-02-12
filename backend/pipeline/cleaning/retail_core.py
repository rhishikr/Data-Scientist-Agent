from __future__ import annotations
import os, re, json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Iterable
import pandas as pd
import numpy as np
import yaml
from auto_detector import guess_table  # single import

# ---------------- Pandera (optional) ----------------
PANDERA_AVAILABLE = False
try:
    import pandera as pa
    PANDERA_AVAILABLE = True

    # Generic getter to stay compatible across Pandera versions
    def _pa_get(*names):
        for n in names:
            if hasattr(pa, n):
                return getattr(pa, n)
        return None

    # Version-agnostic type aliases
    PA_BOOL  = _pa_get("Bool", "Boolean")
    PA_FLOAT = _pa_get("Float", "Float6x4")
    PA_INT   = _pa_get("Int64", "Int")
    PA_STR   = _pa_get("String")
    PA_DT    = _pa_get("DateTime", "Datetime")

except Exception:
    pa = None
    PANDERA_AVAILABLE = False
    PA_BOOL = PA_FLOAT = PA_INT = PA_STR = PA_DT = None

__version__ = "rc-core-2025-12-10"

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

    def asdict(self):
        return asdict(self)

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

def _extract_numeric(val):
    """
    Try to pull a numeric value out of strings like '10', '10.5', '10 mins'.
    Returns a string numeric or NaN if nothing numeric is found.
    """
    if pd.isna(val):
        return np.nan
    s = str(val)
    m = re.search(r"-?\d+(\.\d+)?", s)
    if m:
        return m.group(0)
    return np.nan


# ---- Date parsing helpers ----

DATE_PATTERNS = [
    ("%Y-%m-%d", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("%Y-%m-%d %H:%M:%S", re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$")),
    ("%Y/%m/%d", re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")),
    ("%m/%d/%Y", re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")),
    ("%d-%m-%Y", re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")),
    ("%Y%m%d", re.compile(r"^\d{8}$")),
]

# -------------------------------------------------------------------
# Date parsing: simpler, more forgiving, better metrics
# -------------------------------------------------------------------
def _parse_dates(df: pd.DataFrame, cols: Iterable[str]) -> Tuple[pd.DataFrame, int, int]:
    """
    Parse any date-like columns using pandas' flexible parser.

    Returns:
        df, dates_fixed, dates_dropped

    - dates_fixed  = non-empty values that successfully parsed AND whose original
                     string was not already a plain 'YYYY-MM-DD' date.
                     (i.e., we actually "normalized" something: time part,
                     slashes, month names, etc.)
    - dates_dropped = non-empty values that ended up as NaT (truly invalid).

    NOTE: blank / NA inputs do NOT count as "fixed" or "dropped".
    """
    fixed_total = 0
    dropped_total = 0

    for col in cols:
        if col not in df.columns:
            continue

        # Work with string view for comparison + masks
        orig_str = df[col].astype("string")
        # non-empty means: not NaN and not just ""
        nonempty = orig_str.notna() & (orig_str.str.strip() != "")

        # Let pandas try its best on all formats (timestamps, month names, etc.)
        parsed = pd.to_datetime(
            orig_str,
            errors="coerce",              # invalid → NaT
            infer_datetime_format=True,   # speed + robustness
            utc=False
        )
        df[col] = parsed

        # 1) DATES DROPPED: non-empty originals that became NaT
        dropped = (nonempty & df[col].isna()).sum()
        dropped_total += int(dropped)

        # 2) DATES FIXED:
        #    non-empty + parsed OK + original was not already 'YYYY-MM-DD'
        iso_like = orig_str.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
        fixed = (nonempty & df[col].notna() & ~iso_like).sum()
        fixed_total += int(fixed)

    return df, fixed_total, dropped_total


# ---- dtype casting ----

def _to_bool(series: pd.Series) -> pd.Series:
    true_set = {"1", "true", "t", "yes", "y", "on"}
    false_set = {"0", "false", "f", "no", "n", "off"}

    def cast(v):
        if v is None or pd.isna(v):
            return pd.NA
        s = str(v).strip().lower()
        if s in true_set:
            return True
        if s in false_set:
            return False
        try:
            return bool(float(s))
        except Exception:
            return pd.NA

    return series.astype("string").map(cast).astype("boolean")

def _cast_dtypes(df: pd.DataFrame, table: str, cfg: dict):
    coerced = {}
    for col, dt in cfg["tables"][table].get("dtypes", {}).items():
        if col not in df.columns:
            continue
        s = df[col]
        before = s.isna().sum()
        if dt == "datetime64[ns]":
            df[col] = pd.to_datetime(s, errors="coerce")
        elif dt == "boolean":
            df[col] = _to_bool(s)
        elif dt == "Int64":
            df[col] = pd.to_numeric(s, errors="coerce").round().astype("Int64")
        elif dt == "float":
            df[col] = pd.to_numeric(s, errors="coerce").astype("float")
        elif dt == "string":
            df[col] = s.astype("string").str.strip()
        after = df[col].isna().sum()
        coerced[col] = int(max(0, after - before))
    return df, coerced

# ---- category normalization ----

def _standardize_categories(df: pd.DataFrame, table: str, cfg: dict):
    changes = {}
    maps = cfg.get("category_maps", {}).get(table, {})
    for col, mapping in maps.items():
        if col not in df.columns:
            continue
        before = df[col].astype("string")
        lower = before.str.strip().str.lower()
        mapped = lower.map(mapping).fillna(lower)
        df[col] = mapped
        chg = {}
        for a, b in zip(before.fillna(""), mapped.fillna("")):
            if a != b:
                chg[str(a)] = str(b)
        if chg:
            changes[col] = chg
    return df, changes

# ---- missing values ----

def _fill_missing(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    """
    1) Drop rows missing required keys.
    2) For numeric columns:
         - Pre-clean strings like '10 mins' → '10'
         - Convert to numeric
         - If we have at least 1 real numeric value, fill NaNs with median
         - If we have 0 real numerics, leave column as-is (don't force zeros)
    3) For booleans: fill NaN with False.
    """
    # --- 1. Drop rows missing required columns ---
    req = [c for c in cfg["tables"][table].get("required", []) if c in df.columns]
    before = len(df)
    if req:
        df = df.dropna(subset=req)
    rep.rows_dropped_for_required = before - len(df)

    # --- 2. Numeric fills (float + Int64) ---
    for col, dt in cfg["tables"][table].get("dtypes", {}).items():
        if col not in df.columns:
            continue

        if dt in ("float", "Int64"):
            # Start from the current column
            raw = df[col]

            # Step 2a: pre-clean units / text (e.g. '10 mins' → '10')
            cleaned = raw.map(_extract_numeric)

            # Step 2b: convert to numeric
            num = pd.to_numeric(cleaned, errors="coerce")

            # How many valid numeric values do we have?
            valid = num.notna().sum()

            if valid == 0:
                # All entries failed numeric parsing.
                # Do NOT overwrite the column with zeros. Keep original values.
                continue

            # We have some valid numerics → compute median on them only
            med = num[~num.isna()].median()

            # Use median for NaNs; if med is NaN for some reason, fall back to 0
            fill_value = 0 if pd.isna(med) else med
            na_before = raw.isna().sum()

            df[col] = num.fillna(fill_value)
            na_after = df[col].isna().sum()

            # how many NaNs we actually filled
            filled = max(0, na_before - na_after)
            if filled:
                rep.na_filled[col] = int(filled)

        elif dt == "boolean":
            na = df[col].isna().sum()
            if na:
                df[col] = df[col].fillna(False)
                rep.na_filled[col] = int(na)

    return df


# ---- duplicates ----

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

# ---- outliers ----

def _iqr_mask(s: pd.Series, k: float = 1.5):
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return pd.Series([True] * len(s), index=s.index)
    low, high = q1 - k * iqr, q3 + k * iqr
    return (s >= low) & (s <= high)

def _mad_mask(s: pd.Series, z: float = 5.0):
    med = s.median()
    mad = np.median(np.abs(s - med))
    if mad == 0 or pd.isna(mad):
        return pd.Series([True] * len(s), index=s.index)
    zscore = 0.6745 * (s - med) / mad
    return zscore.abs() <= z

def _remove_outliers(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    cols = cfg["tables"][table].get("outlier_cols", [])
    method = cfg.get("outlier_method", "iqr")
    rep.outlier_method = method
    for col in cols:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        mask = _iqr_mask(s) if method == "iqr" else _mad_mask(s)
        removed = int((~mask & s.notna()).sum())
        if removed:
            rep.outliers_removed[col] = removed
            df = df[mask | s.isna()]
    return df

# ---- business rules ----

def _apply_business_rules(df: pd.DataFrame, table: str, cfg: dict, rep: AuditReport):
    rules = cfg["tables"][table].get("business_rules", [])
    vios, warns = {}, {}

    def count(mask: pd.Series, key: str, warn: bool = False):
        # mask=True means rows that PASS the rule
        bad = (~mask) & mask.index.to_series().notna()
        n_bad = int(bad.sum())
        if n_bad > 0:
            (warns if warn else vios)[key] = n_bad

    def nonneg_col(col: str, rule_key: str | None = None):
        """Set negative values to 0, keep everything else unchanged."""
        if col not in df.columns:
            return
        s = pd.to_numeric(df[col], errors="coerce")
        ok = s.isna() | (s >= 0)
        # record violations
        count(ok, rule_key or f"{col}>=0")
        # only touch the truly bad ones
        bad_mask = ~ok & s.notna()
        if bad_mask.any():
            df.loc[bad_mask, col] = 0
    
    
    for r in rules:
        # Generic non-negative
        #if r.endswith(">=0"):
        #    col = r.split(">=")[0]
        #    nonneg(col)
        
        # --- generic "col>=0" rules, including avg_session_time_min>=0 ---
        if r.endswith(">=0") and "<=" not in r and "nonnegative" not in r:
            col_name = r.split(">=", 1)[0].strip()
            nonneg_col(col_name, rule_key=r)
            continue

        # existing specific rules below ...
        if r == "quantity>=0":
            nonneg_col("quantity", rule_key=r)
        if r == "unit_price>=0":
            nonneg_col("unit_price", rule_key=r)
        if r == "discount>=0":
            nonneg_col("discount", rule_key=r)

        if r == "nonnegative_all_numeric":
            for c in df.select_dtypes(include=["number"]).columns:
                nonneg_col(c, rule_key=f"{c}>=0")

        # rating bounds
        if r == "rating>=1" and "rating" in df.columns:
            m = df["rating"].isna() | (pd.to_numeric(df["rating"], errors="coerce") >= 1)
            count(m, "rating>=1")
            df.loc[~m, "rating"] = 1
        if r == "rating<=5" and "rating" in df.columns:
            m = df["rating"].isna() | (pd.to_numeric(df["rating"], errors="coerce") <= 5)
            count(m, "rating<=5")
            df.loc[~m, "rating"] = 5

        # marketing funnel
        if r == "conversions<=clicks" and {"conversions", "clicks"}.issubset(df.columns):
            m = (
                df["conversions"].isna()
                | df["clicks"].isna()
                | (pd.to_numeric(df["conversions"], errors="coerce")
                   <= pd.to_numeric(df["clicks"], errors="coerce"))
            )
            count(m, "conversions<=clicks")
        if r == "clicks<=impressions" and {"clicks", "impressions"}.issubset(df.columns):
            m = (
                df["clicks"].isna()
                | df["impressions"].isna()
                | (pd.to_numeric(df["clicks"], errors="coerce")
                   <= pd.to_numeric(df["impressions"], errors="coerce"))
            )
            count(m, "clicks<=impressions")

        # inventory: reorder <= quantity (warn)
        if r == "reorder_level<=quantity_available?warn" and {
            "reorder_level", "quantity_available"
        }.issubset(df.columns):
            rl = pd.to_numeric(df["reorder_level"], errors="coerce")
            qa = pd.to_numeric(df["quantity_available"], errors="coerce")
            m = rl.isna() | qa.isna() | (rl <= qa)
            count(m, "reorder<=qty", warn=True)

        # transactions: total ≈ qty * price (warn + fix total)
        if r == "total≈qty*price?warn" and {
            "quantity", "price_per_unit", "total_amount"
        }.issubset(df.columns):
            qty = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
            price = pd.to_numeric(df["price_per_unit"], errors="coerce").fillna(0)
            est = qty * price
            total = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
            diff = (total - est).abs()
            tol = 0.01  # 1 cent tolerance
            m = diff <= tol
            count(m, "total≈qty*price", warn=True)
            df.loc[~m, "total_amount"] = est[~m]

        # web analytics generic bounds already covered by >=0 rules

    rep.rule_violations, rep.rule_warnings = vios, warns
    return df

# ---- small pre-cleaners (currency + text) ----

_currency_re = re.compile(r"[^0-9.\-]")

def _strip_currency(series: pd.Series) -> pd.Series:
    """
    Remove currency symbols and non-numeric chars from amount/price/spend-like columns.
    """
    return (
        series.astype("string")
        .str.replace(_currency_re, "", regex=True)
        .replace("", np.nan)
    )

def _clean_feedback_text(series: pd.Series) -> pd.Series:
    """
    Light cleaning: strip HTML tags, normalize whitespace, keep emojis if present.
    """
    # remove simple HTML tags
    no_html = series.astype("string").str.replace(r"<[^>]+>", " ", regex=True)
    # collapse multiple spaces/newlines
    return no_html.str.replace(r"\s+", " ", regex=True).str.strip()

# ---------- Public API ----------

def clean_table(df: pd.DataFrame, table: str, cfg: dict):
    """
    Main orchestrator: alias resolution → currency/text pre-clean →
    dates → dtypes → categories → missing → rules → duplicates → outliers → schema validation.
    """
    global TABLES
    TABLES = cfg.get("tables", {})

    rep = AuditReport(table=table, rows_before=len(df))

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 1) rename by aliases & check required
    df, ren, missing = _resolve_columns(df, table, cfg)
    rep.columns_renamed, rep.missing_required = ren, missing

    # 2) table-specific pre-cleaners BEFORE casting
    if table == "products":
        if "price" in df.columns:
            df["price"] = _strip_currency(df["price"])
    if table == "marketing":
        if "spend" in df.columns:
            df["spend"] = _strip_currency(df["spend"])
    if table == "payments":
        if "amount" in df.columns:
            df["amount"] = _strip_currency(df["amount"])
    if table == "feedback":
        if "feedback_text" in df.columns:
            df["feedback_text"] = _clean_feedback_text(df["feedback_text"])

    # 3) dates / timestamps (looser detection: date, time, timestamp in col name)
    date_cols = [
        c
        for c in df.columns
        if any(k in c.lower() for k in ("date", "time", "timestamp"))
    ]
    if date_cols:
        df, fixed, dropped = _parse_dates(df, date_cols)
        rep.dates_fixed, rep.dates_dropped = fixed, dropped

    # 4) dtypes
    df, coerce = _cast_dtypes(df, table, cfg)
    rep.dtype_coercions = coerce

    # 5) categories
    df, chg = _standardize_categories(df, table, cfg)
    rep.category_changes = chg

    # 6) missing/impute
    df = _fill_missing(df, table, cfg, rep)

    # 7) business rules
    df = _apply_business_rules(df, table, cfg, rep)

    # 8) duplicates
    df = _remove_duplicates(df, table, cfg, rep)

    # 9) outliers
    df = _remove_outliers(df, table, cfg, rep)

    # 10) pandera validation (version-agnostic)
    if PANDERA_AVAILABLE and pa is not None:
        try:
            fields = {}
            boolean_cols_for_validation = []

            for col, dt in cfg["tables"][table].get("dtypes", {}).items():
                if col not in df.columns:
                    continue
                if dt == "string" and PA_STR:
                    fields[col] = pa.Column(PA_STR, nullable=True)
                elif dt == "float" and PA_FLOAT:
                    fields[col] = pa.Column(PA_FLOAT, nullable=True)
                elif dt == "Int64" and PA_INT:
                    fields[col] = pa.Column(PA_INT, nullable=True)
                elif dt == "boolean":
                    boolean_cols_for_validation.append(col)
                    if PA_BOOL:
                        fields[col] = pa.Column(PA_BOOL, nullable=True)
                    else:
                        fields[col] = pa.Column(nullable=True)
                elif dt == "datetime64[ns]" and PA_DT:
                    fields[col] = pa.Column(PA_DT, nullable=True)

            if fields:
                schema = pa.DataFrameSchema(fields, coerce=False)
                df_for_validate = df.copy()
                for col in boolean_cols_for_validation:
                    if col in df_for_validate.columns:
                        df_for_validate[col] = (
                            pd.Series(df_for_validate[col])
                            .fillna(False)
                            .astype(bool)
                        )
                schema.validate(df_for_validate, lazy=True)
        except Exception as e:
            rep.pandera_errors = [str(e)[:300]]

    rep.rows_after = len(df)
    return df, rep

# -------------- Table detection --------------

_HINTS = [
    ("transactions", ["transaction_id", "total_amount", "price_per_unit"]),
    ("inventory", ["quantity_available", "reorder_level", "warehouse_location"]),
    ("products", ["product_id", "name", "price"]),
    ("returns", ["return_id", "refund_amount"]),  # not used now, but kept
    ("customers", ["customer_id", "signup_date"]),
    ("web_analytics", ["session_id", "pageviews", "session_duration_sec"]),
    ("marketing", ["campaign_id", "impressions", "clicks"]),
    ("payments", ["payment_id", "amount", "method"]),
    ("feedback", ["feedback_id", "rating", "feedback_text"]),
]

def infer_table_type(df: pd.DataFrame, filename: str | None, cfg: dict) -> str | None:
    # 1) YAML-aware smart guess
    table, conf, mapping, scores = guess_table(
        df, cfg, filename=filename, min_confidence=0.45
    )
    if table:
        return table

    # 2) Fallback: filename hint
    if filename:
        name = os.path.basename(filename).lower()
        for t in cfg.get("tables", {}).keys():
            if t in name:
                return t

    # 3) Legacy column-based hints
    for t, cols in _HINTS:
        if all(c in df.columns for c in cols):
            return t
    return None
