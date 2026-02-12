from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .customer import (
    derive_customer_thresholds,
    detect_at_risk_and_churn,
    detect_engaged_no_purchase,
    detect_revenue_concentration,
)
from .hypothesis_support import build_hypothesis_index, HypothesisIndex
from .io import DataPaths, load_featured, load_hypothesis_results
from .product import (
    derive_product_thresholds,
    detect_high_demand_low_stock,
    detect_high_discount_underperformance,
    detect_low_rating_risk,
)
from .schemas import InsightBundle, InsightRunMeta, utc_now_iso
from .validate import validate_all


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)

    # Store complex fields as JSON strings for CSV portability
    if "evidence" in df.columns:
        df["evidence"] = df["evidence"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    if "hypothesis_support" in df.columns:
        df["hypothesis_support"] = df["hypothesis_support"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    if "datasets_used" in df.columns:
        df["datasets_used"] = df["datasets_used"].apply(lambda x: ",".join(x) if isinstance(x, list) else str(x))
    if "tags" in df.columns:
        df["tags"] = df["tags"].apply(lambda x: ",".join(x) if isinstance(x, list) else str(x))

    df.to_csv(path, index=False)


def run_insights(project_root: str | Path) -> InsightBundle:
    root = Path(project_root)
    paths = DataPaths(base_dir=root)

    featured = load_featured(paths)

    # Hypotheses
    hyp_rows = load_hypothesis_results(paths)
    hyp_idx: HypothesisIndex = build_hypothesis_index(hyp_rows)

    # Universe counts (per dataset) for confidence scaling
    sig_by_ds = {}
    for r in hyp_rows:
        ds = str(r.get("dataset", "")).strip()
        if not ds:
            continue
        if bool(r.get("significant", False)):
            sig_by_ds[ds] = sig_by_ds.get(ds, 0) + 1

    insights = []

    # -------- Customers --------
    customers = featured.get("customers_features")
    if customers is not None and not customers.empty:
        c_thr = derive_customer_thresholds(customers)
        cust_sig_universe = sig_by_ds.get("customers_features", 0)

        insights += detect_engaged_no_purchase(customers, hyp_idx, cust_sig_universe, c_thr)
        insights += detect_at_risk_and_churn(customers, hyp_idx, cust_sig_universe, c_thr)
        insights += detect_revenue_concentration(customers, hyp_idx, cust_sig_universe, c_thr)

    # -------- Products --------
    products = featured.get("products_features")
    if products is not None and not products.empty:
        p_thr = derive_product_thresholds(products)
        prod_sig_universe = sig_by_ds.get("products_features", 0)

        insights += detect_low_rating_risk(products, hyp_idx, prod_sig_universe, p_thr)
        insights += detect_high_discount_underperformance(products, hyp_idx, prod_sig_universe, p_thr)
        insights += detect_high_demand_low_stock(products, hyp_idx, prod_sig_universe, p_thr)

    validation = validate_all(insights)

    meta = InsightRunMeta(
        generated_at=utc_now_iso(),
        datasets_used=sorted(list(featured.keys())),
        num_insights=len(insights),
    )

    bundle = InsightBundle(meta=meta, insights=insights, validation=validation)

    out_dir = paths.insights_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(out_dir / "insights.json", bundle.to_dict())
    _write_csv(out_dir / "insights.csv", [i.to_dict() for i in insights])

    return bundle
