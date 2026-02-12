from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .io import read_csv_folder
from .infer import infer_column_types, cap_categories
from .tests import pearson_spearman, cat_vs_num, cat_vs_cat, bh_fdr

# Project root: backend/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLEAN_DIR = os.path.join(ROOT, "data", "cleaned_data")
FEAT_DIR  = os.path.join(ROOT, "data", "featured_data")
OUT_DIR   = os.path.join(ROOT, "data", "hypothesis_outputs")

    # datasets: Dict[str, pd.DataFrame] = {}
    # datasets.update(cleaned)
    # datasets.update({f"{k}_features": v for k, v in featured.items()})
# Keep only these cleaned datasets
KEEP_CLEANED = {"inventory", "marketing", "payments", "web_analytics"}
# Keep only these featured datasets
KEEP_FEATURED = {"customers_features", "products_features", "transactions_features"}

# Effect-size thresholds (tune as you like)
MIN_R = 0.2          # Pearson/Spearman absolute correlation
MIN_CRAMERS_V = 0.1  # Chi-square (Cramer's V)
MIN_COHENS_D = 0.2   # 2-group numeric difference effect size
MIN_ETA2 = 0.01      # ANOVA eta-squared (small but non-trivial)

def _passes_effect_size(r: Dict[str, Any]) -> bool:
    """
    Only keep results that are both statistically significant (q <= alpha)
    and practically meaningful (effect size thresholds).
    """
    test = (r.get("test") or "").lower()
    es = r.get("effect_size")

    # If effect size missing, allow through (but ideally we compute it everywhere)
    if es is None:
        return True

    try:
        es_f = float(es)
    except Exception:
        return True

    if test in ("pearson", "spearman"):
        return abs(es_f) >= MIN_R

    if test == "chi-square":
        return es_f >= MIN_CRAMERS_V

    # 2-group
    if "t-test" in test:
        return abs(es_f) >= MIN_COHENS_D

    # 3+ groups
    if test == "anova":
        return es_f >= MIN_ETA2

    # fallback
    return True

def run_hypothesis_agent(alpha: float = 0.05) -> Dict[str, Any]:
    os.makedirs(OUT_DIR, exist_ok=True)

    cleaned = read_csv_folder(CLEAN_DIR)
    featured = read_csv_folder(FEAT_DIR)

    # Build the datasets dict based on your rule:
    datasets: Dict[str, pd.DataFrame] = {}

    # Keep only selected cleaned
    for k, v in cleaned.items():
        if k in KEEP_CLEANED:
            datasets[k] = v

    # Keep only selected featured (and DO NOT rename keys)
    for k, v in featured.items():
        if k in KEEP_FEATURED:
            datasets[k] = v

    results: List[Dict[str, Any]] = []

    # --- Run tests dataset-by-dataset ---
    for name, df in datasets.items():
        if df is None or df.empty or df.shape[1] < 2:
            continue

        df_work = df.copy()

        # Avoid huge O(n^2) blowups
        if len(df_work) > 20000:
            df_work = df_work.sample(20000, random_state=42)

        numeric_cols, cat_cols = infer_column_types(df_work)

        # Bucket high-cardinality categories
        for c in cat_cols:
            df_work[c] = cap_categories(df_work, c, max_levels=12)

        # numeric-numeric correlations
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                x, y = numeric_cols[i], numeric_cols[j]
                rows = pearson_spearman(df_work, x, y)
                if not rows:
                    continue
                n_pair = int(df_work[[x, y]].dropna().shape[0])
                for row in rows:
                    results.append({
                        "dataset": name,
                        "x": x,
                        "y": y,
                        "test": row["test"],
                        "stat": row["stat"],
                        "p_value": row["p_value"],
                        "n": n_pair,
                        "effect_size": row["stat"],  # r or rho
                        "notes": "numeric-numeric",
                    })

        # categorical-numeric
        for cat in cat_cols:
            for num in numeric_cols:
                row = cat_vs_num(df_work, cat, num)
                if not row:
                    continue

                results.append({
                    "dataset": name,
                    "x": cat,
                    "y": num,
                    "test": row["test"],
                    "stat": row.get("stat"),
                    "p_value": row.get("p_value"),
                    "alt_test": row.get("alt_test"),
                    "alt_p_value": row.get("alt_p_value"),
                    "n": row.get("n"),
                    "effect_size": row.get("effect_size"),  # NOW filled from tests.py
                    "notes": row.get("notes", ""),
                })

        # categorical-categorical
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
                    "effect_size": row.get("effect_size"),  # Cramer's V
                    "notes": "cat-cat",
                })

    # --- Multiple comparisons correction (BH FDR) ---
    pvals = [r.get("p_value") for r in results]
    p_adj = bh_fdr(pvals)

    for r, q in zip(results, p_adj):
        r["p_adj"] = q
        stat_sig = (q is not None and q <= alpha)
        r["significant"] = stat_sig and _passes_effect_size(r)

    sig = [r for r in results if r.get("significant")]

    # Sort significant by smallest adjusted p
    sig_sorted = sorted(sig, key=lambda rr: (rr.get("p_adj") is None, rr.get("p_adj", 1.0)))

    top_findings = []
    for r in sig_sorted[:25]:
        pa = r.get("p_adj")
        es = r.get("effect_size")
        top_findings.append(
            f"{r['dataset']}: {r['x']} vs {r['y']} ({r['test']}) "
            f"p_adj={pa:.4g} effect={es}"
        )

    payload = {
        "meta": {
            "alpha": alpha,
            "fdr_method": "bh",
            "datasets": list(datasets.keys()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "num_tests": len(results),
            "num_significant": len(sig),
            "effect_thresholds": {
                "min_abs_r": MIN_R,
                "min_cramers_v": MIN_CRAMERS_V,
                "min_abs_cohens_d": MIN_COHENS_D,
                "min_eta_squared": MIN_ETA2,
            },
        },
        "results": results,
        "top_findings": top_findings,
    }

    # Save JSON + CSV
    json_path = os.path.join(OUT_DIR, "hypothesis_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    csv_path = os.path.join(OUT_DIR, "hypothesis_results.csv")
    pd.DataFrame(results).to_csv(csv_path, index=False)

    return payload
    datasets: Dict[str, pd.DataFrame] = {}
    datasets.update(cleaned)
    datasets.update({f"{k}_features": v for k, v in featured.items()})