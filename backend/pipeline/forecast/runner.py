from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from joblib import load

from .io import ForecastPaths, read_datasets, read_json, write_csv, write_json
from .schemas import ModelCard, ForecastSnapshot
from .features import infer_as_of, build_daily_revenue, ChurnConfig, map_with_default
from .train_revenue import train_revenue_model
from .train_demand import train_demand_model, build_daily_sku_demand
from .train_churn import train_churn_model
from .train_cashflow import train_cashflow_model
from .predict import forecast_next_days_recursive, predict_demand_sku


def _iso(x: Any) -> str:
    try:
        return pd.Timestamp(x).isoformat()
    except Exception:
        return str(x)


def run_forecasting(paths: ForecastPaths | None = None) -> Dict[str, Any]:
    paths = paths or ForecastPaths.default()
    os.makedirs(paths.out_dir, exist_ok=True)
    os.makedirs(paths.models_dir, exist_ok=True)

    data = read_datasets(paths)

    transactions = data.get("transactions", pd.DataFrame())
    transactions_features = data.get("transactions_features", pd.DataFrame())
    customers_features = data.get("customers_features", pd.DataFrame())
    payments = data.get("payments", pd.DataFrame())
    inventory = data.get("inventory", pd.DataFrame())

    as_of = infer_as_of(transactions, transactions_features)

    forecasts: Dict[str, Any] = {}
    model_cards: List[Dict[str, Any]] = []

    # -------------------------
    # 1) Revenue Forecast (ML)
    # -------------------------
    rev_model, rev_metrics, rev_feats, _rev_df = train_revenue_model(
        transactions=transactions,
        models_dir=paths.models_dir,
        model_id="revenue_hgbr_v1",
    )

    daily_rev = build_daily_revenue(transactions)
    rev_fc = forecast_next_days_recursive(
        model=rev_model,
        history=daily_rev.rename(columns={"revenue": "revenue"}),
        date_col="date",
        y_col="revenue",
        feature_cols=rev_feats,
        horizon_days=90,
    ).rename(columns={"yhat": "revenue_forecast"})

    write_csv(os.path.join(paths.out_dir, "revenue_forecast_daily.csv"), rev_fc)

    next_7 = float(rev_fc.head(7)["revenue_forecast"].sum())
    next_30 = float(rev_fc.head(30)["revenue_forecast"].sum())
    next_90 = float(rev_fc.head(90)["revenue_forecast"].sum())

    forecasts["forecasted_revenue"] = {
        "as_of": _iso(as_of),
        "next_7d": next_7,
        "next_30d": next_30,
        "next_90d": next_90,
        "series_daily_path": "revenue_forecast_daily.csv",
        "metrics": rev_metrics,
    }

    model_cards.append(ModelCard(
        model_id="revenue_hgbr_v1",
        task="forecasting",
        target="daily_revenue",
        training_window={"end": _iso(as_of), "notes": "daily revenue from transactions"},
        features_used=rev_feats,
        metrics=rev_metrics,
        caveats=[
            "Does not incorporate future promo calendar unless you add it as exogenous features.",
            "Recursive forecasting can drift on longer horizons; monitor weekly.",
        ],
    ).model_dump())

    # -------------------------
    # 2) Demand per SKU (ML) + corrected per-SKU predict
    # -------------------------
    demand_ok = True
    try:
        dem_model, dem_metrics, dem_feats, dem_train_df, cat_maps = train_demand_model(
            transactions_features=transactions_features,
            models_dir=paths.models_dir,
            top_n_skus=75,
            model_id="demand_hgbr_v1",
        )

        # Load the saved bundle so predict uses the same feature_cols + maps
        bundle = load(os.path.join(paths.models_dir, "demand_hgbr_v1.joblib"))

        # Build daily sku demand again (same logic) for history
        daily_sku = build_daily_sku_demand(transactions_features)
        if daily_sku.empty:
            raise ValueError("daily_sku_demand is empty; cannot forecast SKU demand.")

        # Choose SKUs to forecast (top by historical qty)
        sku_totals = daily_sku.groupby("sku")["qty"].sum().sort_values(ascending=False)
        top_skus = sku_totals.head(50).index.astype(str).tolist()

        # Prepare static features per SKU
        # Use last known attributes from daily_sku (already merged during build_daily_sku_demand)
        static_cols = []
        for c in ["category", "brand", "discount_percent", "average_rating", "stock", "cost_price", "retail_price"]:
            if c in daily_sku.columns:
                static_cols.append(c)

        last_attrs = (
            daily_sku.sort_values("date")
            .groupby("sku", as_index=False)[static_cols].last()
            if static_cols else pd.DataFrame({"sku": top_skus})
        )
        last_attrs["sku"] = last_attrs["sku"].astype(str)

        sku_forecast_rows = []
        sku_daily_series_rows = []

        for sku in top_skus:
            g = daily_sku[daily_sku["sku"].astype(str) == str(sku)].copy().sort_values("date")
            if len(g) < 45:
                continue

            # Ensure daily continuity for this SKU (missing days => 0)
            full = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
            g = g.set_index("date").reindex(full).fillna({"qty": 0.0}).rename_axis("date").reset_index()
            g["sku"] = str(sku)

            # static values
            row_attr = last_attrs[last_attrs["sku"] == str(sku)].head(1)
            cat = str(row_attr["category"].iloc[0]) if ("category" in row_attr.columns and not row_attr.empty) else ""
            brand = str(row_attr["brand"].iloc[0]) if ("brand" in row_attr.columns and not row_attr.empty) else ""

            sku_code = cat_maps["sku"].get(str(sku), -1)
            category_code = cat_maps.get("category", {}).get(cat, -1)
            brand_code = cat_maps.get("brand", {}).get(brand, -1)

            sku_static = {
                "sku_code": int(sku_code),
                "category_code": int(category_code),
                "brand_code": int(brand_code),
            }

            # numeric attrs (carry forward)
            for c in ["discount_percent", "average_rating", "stock", "cost_price", "retail_price"]:
                if c in row_attr.columns and not row_attr.empty:
                    sku_static[c] = float(pd.to_numeric(row_attr[c].iloc[0], errors="coerce") or 0.0)
                else:
                    sku_static[c] = 0.0

            sku_hist = g[["date", "qty"]].copy()
            fc_daily = predict_demand_sku(bundle=bundle, sku_history=sku_hist, sku_static=sku_static, horizon_days=30)
            fc_daily["sku"] = str(sku)

            # store daily series (optional for charts)
            sku_daily_series_rows.append(fc_daily)

            tot_30 = float(fc_daily["qty_forecast"].sum())
            sku_forecast_rows.append({"sku": str(sku), "forecast_qty_30d": tot_30, "avg_daily_forecast": tot_30 / 30.0})

        if sku_forecast_rows:
            sku_table = pd.DataFrame(sku_forecast_rows).sort_values("forecast_qty_30d", ascending=False)
            write_csv(os.path.join(paths.out_dir, "demand_forecast_sku.csv"), sku_table.head(200))

            # optional: daily series file for charts
            sku_daily = pd.concat(sku_daily_series_rows, ignore_index=True) if sku_daily_series_rows else pd.DataFrame()
            if not sku_daily.empty:
                write_csv(os.path.join(paths.out_dir, "demand_forecast_sku_daily.csv"), sku_daily)

            forecasts["forecasted_demand_per_sku"] = {
                "as_of": _iso(as_of),
                "horizon_days": 30,
                "table_path": "demand_forecast_sku.csv",
                "daily_series_path": "demand_forecast_sku_daily.csv" if (sku_daily_series_rows and not sku_daily.empty) else None,
                "metrics": dem_metrics,
                "note": "Forecasts top SKUs; long-tail SKUs can use intermittent-demand methods later.",
            }

            model_cards.append(ModelCard(
                model_id="demand_hgbr_v1",
                task="forecasting",
                target="daily_sku_quantity",
                training_window={"end": _iso(as_of), "notes": "trained on transactions_features daily SKU demand"},
                features_used=bundle["feature_cols"],
                metrics=dem_metrics,
                caveats=[
                    "Carries forward last-known SKU attributes (discount/rating/stock) into future days.",
                    "Top-SKU focus for stability; add intermittent-demand baselines for long tail.",
                ],
            ).model_dump())
        else:
            forecasts["forecasted_demand_per_sku"] = {"error": "No SKUs met minimum history requirements."}

    except Exception as e:
        demand_ok = False
        forecasts["forecasted_demand_per_sku"] = {"error": str(e)}

    # -------------------------
    # 3) Churn next month (ML)
    # -------------------------
    churn_bundle, churn_metrics, churn_feats, churn_ds = train_churn_model(
        transactions=transactions,
        customers_features=customers_features,
        models_dir=paths.models_dir,
        cfg=ChurnConfig(snapshot_every_days=7, churn_horizon_days=30, lookback_days=180),
        model_id="churn_logreg_cal_v1",
    )

    # load saved (ensures stable feature_cols)
    churn_saved = load(os.path.join(paths.models_dir, "churn_logreg_cal_v1.joblib"))
    churn_model = churn_saved["model"]
    churn_feature_cols = churn_saved["feature_cols"]

    churn_ds["snapshot_date"] = pd.to_datetime(churn_ds["snapshot_date"])
    latest_snap = churn_ds["snapshot_date"].max()
    latest = churn_ds[churn_ds["snapshot_date"] == latest_snap].copy()

    X = latest[churn_feature_cols].fillna(0.0)
    latest["churn_prob_30d"] = churn_model.predict_proba(X)[:, 1]

    churn_top = latest[["customer_id", "snapshot_date", "churn_prob_30d"]].sort_values("churn_prob_30d", ascending=False).head(500)
    write_csv(os.path.join(paths.out_dir, "churn_predictions.csv"), churn_top)

    expected_churn_rate = float(latest["churn_prob_30d"].mean())
    forecasts["expected_churn_next_month"] = {
        "as_of": _iso(as_of),
        "snapshot_date": _iso(latest_snap),
        "expected_churn_rate_next_30d": expected_churn_rate,
        "top_customers_path": "churn_predictions.csv",
        "definition": "churn_30d = no purchase in next 30 days after snapshot date",
        "metrics": churn_metrics,
    }

    model_cards.append(ModelCard(
        model_id="churn_logreg_cal_v1",
        task="classification",
        target="churn_30d",
        training_window={"end": _iso(as_of), "notes": "rolling weekly snapshots from transactions"},
        features_used=churn_feature_cols,
        metrics=churn_metrics,
        caveats=[
            "Churn is a proxy label based on inactivity window; tune horizon based on business cycle.",
            "Monitor calibration drift monthly.",
        ],
    ).model_dump())

    # -------------------------
    # 4) Cashflow proxy (ML)
    # -------------------------
    try:
        cash_bundle, cash_metrics, cash_feats, cash_df = train_cashflow_model(
            transactions=transactions,
            payments=payments,
            models_dir=paths.models_dir,
            model_id="cashflow_proxy_hgbr_v1",
        )
        cash_saved = load(os.path.join(paths.models_dir, "cashflow_proxy_hgbr_v1.joblib"))
        cash_model = cash_saved["model"]
        cash_feature_cols = cash_saved["feature_cols"]

        hist = cash_df[["date", "cash_proxy"]].copy()
        cash_fc = forecast_next_days_recursive(
            model=cash_model,
            history=hist.rename(columns={"cash_proxy": "cash_proxy"}),
            date_col="date",
            y_col="cash_proxy",
            feature_cols=cash_feature_cols,
            horizon_days=90,
        ).rename(columns={"yhat": "cashflow_proxy_forecast"})

        write_csv(os.path.join(paths.out_dir, "cashflow_forecast_daily.csv"), cash_fc)

        forecasts["projected_cashflow"] = {
            "as_of": _iso(as_of),
            "next_30d_cash_proxy": float(cash_fc.head(30)["cashflow_proxy_forecast"].sum()),
            "series_daily_path": "cashflow_forecast_daily.csv",
            "metrics": cash_metrics,
            "note": "Proxy cashflow = revenue - refunds aligned to order_date; add payment_date for true timing.",
        }

        model_cards.append(ModelCard(
            model_id="cashflow_proxy_hgbr_v1",
            task="forecasting",
            target="daily_cash_proxy",
            training_window={"end": _iso(as_of), "notes": "cashflow proxy from transactions/payments"},
            features_used=cash_feature_cols,
            metrics=cash_metrics,
            caveats=[
                "This is NOT settlement-timing cashflow (missing payment_date).",
                "Add payment_date/payment_amount for real cash timing forecasts.",
            ],
        ).model_dump())
    except Exception as e:
        forecasts["projected_cashflow"] = {"error": str(e)}

    # -------------------------
    # 5) Executive Insights (grounded) + LLM handoff for actions
    # -------------------------
    hyp = read_json(paths.hypothesis_json_path) or {}
    top_findings = hyp.get("top_findings", []) if isinstance(hyp.get("top_findings"), list) else []

    exec_summary = []
    exec_summary.append(f"If current patterns continue, forecasted revenue is ~{next_30:,.0f} in the next 30 days.")
    exec_summary.append(f"Expected churn over the next month is ~{expected_churn_rate*100:.1f}% (30-day inactivity proxy).")

    # Drivers / Risks / Opps (structured, deterministic)
    key_drivers = top_findings[:5]

    top_risks = [
        {
            "title": "Rising churn risk",
            "evidence": {
                "expected_churn_rate_next_30d": expected_churn_rate,
                "top_at_risk_customers_path": "churn_predictions.csv",
            },
        }
    ]
    if demand_ok:
        top_risks.append(
            {"title": "Demand concentration (top SKUs)", "evidence": {"demand_table": "demand_forecast_sku.csv"}}
        )

    top_opportunities = [
        {
            "title": "Retention targeting",
            "evidence": {"suggestion": "Use churn_predictions.csv to target high-risk customers first."},
        }
    ]

    # LLM handoff: we give it grounded context and let it rewrite recommended actions
    llm_actions_context = {
        "what_to_do": "Write 3 recommended actions in business language. Keep them feasible and tie each to evidence.",
        "constraints": [
            "Do NOT invent numbers; only use provided metrics.",
            "Prefer retention offers over site-wide discounts when churn risk is high.",
            "Mention any hypothesis-supported drivers if relevant.",
        ],
        "evidence": {
            "forecasted_revenue_next_30d": next_30,
            "expected_churn_rate_next_30d": expected_churn_rate,
            "top_hypothesis_findings": key_drivers,
            "files": {
                "revenue_forecast_daily": "revenue_forecast_daily.csv",
                "churn_predictions": "churn_predictions.csv",
                "demand_forecast_sku": "demand_forecast_sku.csv" if demand_ok else None,
            },
        },
        "example_style": "Concise, exec-friendly, action-oriented bullets.",
    }

    executive_insights = {
        "key_drivers_of_growth_decline": key_drivers,
        "top_3_risks": top_risks[:3],
        "top_3_opportunities": top_opportunities[:3],
        "recommended_actions_rule_based": [
            "Review churn_predictions.csv and prioritize outreach for the highest-risk customers.",
            "Track forecast vs actual weekly; retrain monthly or when drift is observed.",
        ],
        "recommended_actions_llm_context": llm_actions_context,
        "summary": exec_summary,
    }

    snapshot = ForecastSnapshot(
        meta={
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "as_of": _iso(as_of),
            "datasets_used": [k for k, v in data.items() if isinstance(v, pd.DataFrame) and not v.empty],
        },
        forecasts=forecasts,
        executive_insights=executive_insights,
    ).model_dump()

    write_json(os.path.join(paths.out_dir, "forecast_snapshot.json"), snapshot)
    write_json(os.path.join(paths.out_dir, "model_cards.json"), {"model_cards": model_cards})

    return snapshot


if __name__ == "__main__":
    run_forecasting()
