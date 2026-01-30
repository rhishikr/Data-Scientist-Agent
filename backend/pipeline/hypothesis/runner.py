from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .io import read_csv_folder
from .infer import infer_column_types, cap_categories
from .tests import pearson_spearman, cat_vs_num, cat_vs_cat, bh_fdr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLEAN_DIR = os.path.join(ROOT, "data", "cleaned_data")
FEAT_DIR  = os.path.join(ROOT, "data", "featured_data")
OUT_DIR   = os.path.join(ROOT, "data", "hypothesis_outputs")

def run_hypothesis_agent(alpha: float = 0.05) -> Dict[str, Any]:
    os.makedirs(OUT_DIR, exist_ok=True)

    cleaned = read_csv_folder(CLEAN_DIR)
    featured = read_csv_folder(FEAT_DIR)

    datasets: Dict[str, pd.DataFrame] = {}
    datasets.update(cleaned)
    datasets.update({f"{k}_features": v for k, v in featured.items()})

    results: List[Dict[str, Any]] = []

    # --- Run tests dataset-by-dataset ---
    for name, df in datasets.items():
        if df is None or df.empty or df.shape[1] < 2:
            continue

        # cap huge datasets if needed (avoid O(n^2) explosion)
        # NOTE: remove or increase if you want everything
        df_work = df.copy()
        if len(df_work) > 20000:
            df_work = df_work.sample(20000, random_state=42)

        numeric_cols, cat_cols = infer_column_types(df_work)

        # cap categories (avoid 100s of levels)
        for c in cat_cols:
            df_work[c] = cap_categories(df_work, c, max_levels=12)

        # numeric-numeric correlations (pairwise)
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                x, y = numeric_cols[i], numeric_cols[j]
                for row in pearson_spearman(df_work, x, y):
                    results.append({
                        "dataset": name,
                        "x": x,
                        "y": y,
                        "test": row["test"],
                        "stat": row["stat"],
                        "p_value": row["p_value"],
                        "n": int(df_work[[x, y]].dropna().shape[0]),
                        "effect_size": row["stat"],  # correlation coefficient
                        "notes": "numeric-numeric",
                    })

        # cat-numeric
        for cat in cat_cols:
            for num in numeric_cols:
                row = cat_vs_num(df_work, cat, num)
                if not row:
                    continue
                # choose primary p (parametric) + store alt too
                results.append({
                    "dataset": name,
                    "x": cat,
                    "y": num,
                    "test": row["test"],
                    "stat": row["stat"],
                    "p_value": row["p_value"],
                    "alt_test": row.get("alt_test"),
                    "alt_p_value": row.get("alt_p_value"),
                    "n": row.get("n"),
                    "effect_size": None,
                    "notes": f"{len(row.get('groups', []))} groups",
                })

        # cat-cat
        for i in range(len(cat_cols)):
            for j in range(i + 1, len(cat_cols)):
                a, b = cat_cols[i], cat_cols[j]
                row = cat_vs_cat(df_work, a, b)
                if not row:
                    continue
                results.append({
                    "dataset": name,
                    "x": a,
                    "y": b,
                    "test": row["test"],
                    "stat": row["stat"],
                    "p_value": row["p_value"],
                    "n": row.get("n"),
                    "effect_size": row.get("effect_size"),
                    "notes": "cat-cat",
                })

    # --- Multiple comparisons correction ---
    pvals = [r.get("p_value") for r in results]
    p_adj = bh_fdr(pvals)
    for r, q in zip(results, p_adj):
        r["p_adj"] = q
        r["significant"] = (q is not None and q < alpha)

    # --- Top findings summary ---
    sig = [r for r in results if r.get("significant")]
    sig_sorted = sorted(sig, key=lambda r: (r.get("p_adj") is None, r.get("p_adj", 1.0)))

    top_findings = []
    for r in sig_sorted[:25]:
        top_findings.append(
            f"{r['dataset']}: {r['x']} vs {r['y']} ({r['test']}) p_adj={r['p_adj']:.4g}"
        )

    payload = {
        "meta": {
            "alpha": alpha,
            "fdr_method": "bh",
            "datasets": list(datasets.keys()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "num_tests": len(results),
            "num_significant": len(sig),
        },
        "results": results,
        "top_findings": top_findings,
    }

    # write JSON + CSV
    json_path = os.path.join(OUT_DIR, "hypothesis_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    csv_path = os.path.join(OUT_DIR, "hypothesis_results.csv")
    pd.DataFrame(results).to_csv(csv_path, index=False)

    return payload
