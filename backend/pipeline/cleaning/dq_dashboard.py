
# dq_dashboard.py
import os, json, glob
from typing import Dict, Any, List
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Retail Data Quality Dashboard", layout="wide")

st.title("🧼 Retail Data Quality Dashboard")
st.caption("Point this at your reports folder (where *_report.json files are written).")

# ---- Sidebar: folder picker ----
reports_dir = st.text_input("Reports folder", value="out")
st.write("")

def load_reports(folder: str) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(os.path.join(folder, "*_report.json")))
    out = []
    for p in paths:
        try:
            with open(p, "r") as f:
                out.append(json.load(f))
        except Exception as e:
            st.warning(f"Could not read {p}: {e}")
    return out

reports = load_reports(reports_dir)

if not reports:
    st.info("No reports found yet. Run the cleaner first to generate *_report.json files, then refresh.")
    st.stop()

# Normalize to DataFrame for easy aggregation
df = pd.json_normalize(reports)

# ------- Overview cards -------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Files Processed", len(df))
col2.metric("Total Rows (Before)", int(df["rows_before"].sum()))
col3.metric("Total Rows (After)", int(df["rows_after"].sum()))
col4.metric("Rows Dropped", int((df["rows_before"] - df["rows_after"]).sum()))

st.divider()

# ------- By table summary -------
st.subheader("By Table Summary")
by_table = df.groupby("table").agg(
    files=("table", "count"),
    rows_before=("rows_before", "sum"),
    rows_after=("rows_after", "sum"),
    duplicates_removed=("duplicates_removed", "sum"),
).reset_index()
by_table["rows_dropped"] = by_table["rows_before"] - by_table["rows_after"]
st.dataframe(by_table)

# ------- Plot: Rows dropped per table (matplotlib) -------
fig1, ax1 = plt.subplots()
ax1.bar(by_table["table"], by_table["rows_dropped"])
ax1.set_title("Rows Dropped per Table")
ax1.set_xlabel("Table")
ax1.set_ylabel("Rows Dropped")
plt.xticks(rotation=30, ha="right")
st.pyplot(fig1)

# ------- Plot: Duplicates removed per table (matplotlib) -------
fig2, ax2 = plt.subplots()
ax2.bar(by_table["table"], by_table["duplicates_removed"])
ax2.set_title("Duplicates Removed per Table")
ax2.set_xlabel("Table")
ax2.set_ylabel("Duplicates Removed")
plt.xticks(rotation=30, ha="right")
st.pyplot(fig2)

st.divider()

# ------- Detailed view per file -------
st.subheader("Per-File Details")
st.caption("Pick a row index to inspect the full JSON and key metrics.")
st.dataframe(df[["table","rows_before","rows_after","duplicates_removed","outlier_method"]])

idx = st.number_input("View report index", min_value=0, max_value=len(df)-1, value=0, step=1)
selected = reports[int(idx)]

st.write("### Selected Report (Key Metrics)")
cols = st.columns(3)
cols[0].write(f"**Table:** {selected.get('table')}")
cols[0].write(f"**Version:** {selected.get('version')}")
cols[1].write(f"**Rows Before:** {selected.get('rows_before')}")
cols[1].write(f"**Rows After:** {selected.get('rows_after')}")
cols[2].write(f"**Duplicates Removed:** {selected.get('duplicates_removed')}")
cols[2].write(f"**Outlier Method:** {selected.get('outlier_method')}")

st.write("**Missing Required Columns:**", selected.get("missing_required", []))
st.write("**Rule Violations:**", selected.get("rule_violations", {}))
st.write("**Rule Warnings:**", selected.get("rule_warnings", {}))
st.write("**Pandera Errors:**", selected.get("pandera_errors", []))

with st.expander("Show Full JSON"):
    st.json(selected)
