import os
import streamlit as st
import pandas as pd
from io import BytesIO

from retail_core import load_config, clean_table, infer_table_type

st.set_page_config(page_title="Retail Cleaner (YAML-driven)", layout="wide")

st.title("Cleaning Agent")

# ------------------------------------------------------------------
# Config load
# ------------------------------------------------------------------
cfg_path = st.text_input("Config path", value="config/defaults.yaml")
cfg = load_config(cfg_path)


def render_visual_report(rep: dict):
    rows_before = int(rep.get("rows_before", 0))
    rows_after = int(rep.get("rows_after", 0))
    rows_dropped = rows_before - rows_after
    duplicates_removed = int(rep.get("duplicates_removed", 0))

    st.subheader("Data Quality Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows Before", rows_before)
    c2.metric("Rows After", rows_after)
    c3.metric("Rows Dropped", rows_dropped)
    c4.metric("Duplicates Removed", duplicates_removed)

    dtype_coercions = rep.get("dtype_coercions", {}) or {}
    if dtype_coercions:
        st.markdown("**Type Coercions (cells newly NA after cast)**")
        df_dc = pd.DataFrame(
            [{"column": k, "coercions": int(v)} for k, v in dtype_coercions.items()]
        ).sort_values("coercions", ascending=False)
        st.dataframe(df_dc, width="stretch")

    na_filled = rep.get("na_filled", {}) or {}
    if na_filled:
        st.markdown("**Missing Values Filled**")
        df_na = pd.DataFrame(
            [{"column": k, "filled": int(v)} for k, v in na_filled.items()]
        ).sort_values("filled", ascending=False)
        st.dataframe(df_na, width="stretch")

    outliers = rep.get("outliers_removed", {}) or {}
    if outliers:
        st.markdown(f"**Outliers Removed** (method: `{rep.get('outlier_method','')}`)")
        df_out = pd.DataFrame(
            [{"column": k, "removed": int(v)} for k, v in outliers.items()]
        ).sort_values("removed", ascending=False)
        st.dataframe(df_out, width="stretch")

    rules_bad = rep.get("rule_violations", {}) or {}
    rules_warn = rep.get("rule_warnings", {}) or {}

    if rules_bad:
        st.markdown("**Rule Violations**")
        df_rb = pd.DataFrame(
            [{"rule": k, "violations": int(v)} for k, v in rules_bad.items()]
        ).sort_values("violations", ascending=False)
        st.dataframe(df_rb, width="stretch")

    if rules_warn:
        st.markdown("**Rule Warnings**")
        df_rw = pd.DataFrame(
            [{"rule": k, "warnings": int(v)} for k, v in rules_warn.items()]
        ).sort_values("warnings", ascending=False)
        st.dataframe(df_rw, width="stretch")

    cat_changes = rep.get("category_changes", {}) or {}
    rows = []
    for col, mapping in cat_changes.items():
        rows.append({"column": col, "unique_changes": len(mapping)})
    if rows:
        st.markdown("**Category Normalizations**")
        st.dataframe(
            pd.DataFrame(rows).sort_values("unique_changes", ascending=False),
            width="stretch",
        )

    pandera_errs = rep.get("pandera_errors", []) or []
    if pandera_errs:
        st.markdown("**Schema Validation Errors (Pandera)**")
        for e in pandera_errs:
            st.code(str(e))

    with st.expander("Show raw JSON report"):
        st.json(rep)


# ------------------------------------------------------------------
# Batch: clean all CSVs in datasets/E-Commerce
# ------------------------------------------------------------------
st.subheader("📂 Processing all datasets")

DATA_DIR = "datasets/ecommerce2"

file_map = {
    "customers.csv": "customers",
    "feedback.csv": "feedback",
    "inventory.csv": "inventory",
    "marketing.csv": "marketing",
    "payments.csv": "payments",
    "products.csv": "products",
    "transactions.csv": "transactions",
    "web_analytics.csv": "web_analytics",
}

for fname, table_hint in file_map.items():
    full_path = os.path.join(DATA_DIR, fname)
    with st.expander(f"{fname} → table hint: `{table_hint}`", expanded=(fname == "transactions.csv")):
        if not os.path.exists(full_path):
            st.warning(f"File not found: `{full_path}` — skipping.")
            continue

        df_raw = pd.read_csv(full_path)

        st.markdown("**Raw preview (first 100 rows)**")
        st.dataframe(df_raw.head(100), width="stretch")

        # infer table type using YAML + hints
        inferred = infer_table_type(df_raw, filename=fname, cfg=cfg) or table_hint
        st.caption(f"Detected table type: `{inferred}` (hint was `{table_hint}`)")

        try:
            cleaned_df, report = clean_table(df_raw, table=inferred, cfg=cfg)
        except Exception as e:
            st.error(f"Error while cleaning `{fname}`: {e}")
            continue

        st.markdown("---")
        st.markdown("**Cleaned preview (first 100 rows)**")
        st.dataframe(cleaned_df.head(100), width="stretch")

        render_visual_report(report.asdict())

        # Download button
        csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇️ Download cleaned {fname}",
            data=csv_bytes,
            file_name=f"cleaned_{fname}",
            mime="text/csv",
            key=f"download_{fname}",
        )

# ------------------------------------------------------------------
# Optional: upload & clean a single file
# ------------------------------------------------------------------
st.subheader("✏️ Upload a single file (optional)")

uploaded = st.file_uploader("Upload CSV or Parquet", type=["csv", "parquet", "pq"])
if uploaded:
    if uploaded.name.endswith(".csv"):
        df_u = pd.read_csv(uploaded)
    else:
        df_u = pd.read_parquet(uploaded)

    fname = uploaded.name
    inferred = infer_table_type(df_u, filename=fname, cfg=cfg) or list(cfg["tables"].keys())[0]
    table = st.selectbox(
        "Select table type for this file",
        list(cfg["tables"].keys()),
        index=list(cfg["tables"].keys()).index(inferred),
    )

    cleaned_u, rep_u = clean_table(df_u, table=table, cfg=cfg)

    st.markdown("**Cleaned preview (first 100 rows)**")
    st.dataframe(cleaned_u.head(100), width="stretch")

    render_visual_report(rep_u.asdict())

    csv_u = cleaned_u.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download cleaned upload",
        data=csv_u,
        file_name=f"cleaned_{fname}",
        mime="text/csv",
    )
