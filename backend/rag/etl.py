# backend/rag/etl.py
import glob
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


def build_documents_from_csv_dir(
    data_dir: Path,
    max_sample_rows: int = 100,     # keep small for POC speed
    max_cols_per_row: int = 20
) -> List[Dict[str, Any]]:
    """
    Convert CSV files into a small set of retrievable 'documents'.

    Returns a list of dicts:
      { "text": str, "metadata": dict }
    """
    docs: List[Dict[str, Any]] = []

    csv_paths = sorted(glob.glob(str(Path(data_dir) / "*.csv")))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    for p in csv_paths:
        fp = Path(p)
        table = fp.name
        df = pd.read_csv(fp)

        # 1) Profile doc (highest value for RAG)
        missing = df.isna().mean().sort_values(ascending=False).head(15)
        profile_lines = [
            f"TABLE: {table}",
            f"ROWS: {len(df)}",
            f"COLS: {df.shape[1]}",
            "",
            "COLUMNS (name : dtype):",
            *[f"- {c}: {df[c].dtype}" for c in df.columns],
            "",
            "TOP MISSINGNESS (fraction):",
            *[f"- {k}: {v:.3f}" for k, v in missing.items()],
            "",
            "HEAD (5 rows):",
            df.head(5).to_string(index=False),
        ]
        docs.append({
            "text": "\n".join(profile_lines),
            "metadata": {"source": table, "doc_type": "profile"},
        })

        # 2) Small sampled rows doc (optional grounding)
        if len(df) > 0 and max_sample_rows > 0:
            sample = df.sample(min(len(df), max_sample_rows), random_state=42)
            cols = list(df.columns)[:max_cols_per_row]

            rows_text = []
            for _, row in sample.iterrows():
                pairs = [f"{c}={row[c]}" for c in cols]
                rows_text.append(f"{table} | " + " | ".join(pairs))

            docs.append({
                "text": "\n".join(rows_text),
                "metadata": {"source": table, "doc_type": "rows_sample"},
            })

    return docs
