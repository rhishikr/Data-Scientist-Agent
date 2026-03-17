# Data & Scripts

This document explains the synthetic data generation, shell scripts, data lifecycle, and pipeline processing modules.

## Synthetic Data

The project uses synthetic retail data for development and demonstration. The data generation script creates 12 CSV files representing a complete retail business dataset.

### Generated Tables

| File | Description | Key Columns |
|---|---|---|
| `customers.csv` | Customer demographics | customer_id, name, email, age, gender, location, signup_date |
| `products.csv` | Product catalog | product_id, name, category, brand, price, cost |
| `inventory.csv` | Stock levels | product_id, location, stock_quantity, reorder_point |
| `transactions.csv` | Order history | transaction_id, customer_id, product_id, quantity, total, date |
| `transactions_with_session.csv` | Session-linked orders | Same as transactions + session_id |
| `payments.csv` | Payment details | payment_id, transaction_id, method, status, amount |
| `marketing.csv` | Campaign metrics | campaign_id, channel, spend, impressions, clicks |
| `campaign_performance.csv` | Daily campaign data | campaign_id, date, spend, revenue, conversions |
| `sessions.csv` | User browsing sessions | session_id, customer_id, start_time, duration, pages_viewed |
| `events.csv` | Granular user events | event_id, session_id, event_type, timestamp |
| `web_analytics.csv` | Web behavior metrics | date, visitors, page_views, bounce_rate |
| `funnel_summary.csv` | Conversion funnel | stage, count, conversion_rate |

### Generation Script

**`backend/scripts/generate_synthetic_data.py`** (~46KB)

Generates a complete set of baseline data with realistic distributions:
- Customer demographics with geographic spread
- Product catalog across multiple categories and brands
- Transaction history with seasonal patterns
- Marketing campaigns across channels (email, social, search, etc.)
- Web analytics with session behavior

Output: CSV files in `backend/data/raw/`

### Update/Simulation Script

**`backend/scripts/simulate_update.py`** (~39KB)

Simulates incremental data changes with configurable business scenarios:

| Scenario | Effect |
|---|---|
| `organic-growth` | Steady natural growth (default) |
| `profit` | High conversions, low returns, strong margins |
| `loss` | Declining performance, low conversions, high returns |
| `seasonal-spike` | Temporary demand surge (holiday season) |
| `stockout-crisis` | Inventory shortages impacting sales |
| `marketing-blitz` | Heavy marketing spend driving traffic |
| `churn-wave` | Increased customer churn |
| `new-product-launch` | New product with early adoption patterns |

### Migration Script

**`backend/scripts/migrate_raw_to_supabase.py`**

Uploads generated CSV files from `backend/data/raw/` to Supabase raw tables. Run this after generating data.

## Shell Scripts

### `start.sh` — Start Both Servers

```bash
bash start.sh
```

1. Activates the Python virtual environment
2. Starts the backend (`python app.py`) on port 8000
3. Waits for the backend to be ready (polls `/docs` endpoint)
4. Starts the frontend (`npm run dev`) on port 5173
5. Ctrl+C stops both servers (cleanup via trap)

### `generate_data.sh` — Generate Fresh Data

```bash
bash generate_data.sh
```

Runs `backend/scripts/generate_synthetic_data.py` to create all 12 CSV files from scratch. Replaces any existing data in `backend/data/raw/`.

### `update_data.sh` — Simulate Data Updates

```bash
bash update_data.sh [--days N] [--scenario SCENARIO]
```

Examples:
```bash
bash update_data.sh                              # 7-day organic growth
bash update_data.sh --days 14 --scenario profit  # 14-day profit scenario
bash update_data.sh --scenario stockout-crisis   # 7-day stockout crisis
```

## Data Lifecycle

```
1. Generate data      →  bash generate_data.sh
                          (creates CSVs in backend/data/raw/)
       │
2. Upload to Supabase →  python scripts/migrate_raw_to_supabase.py
                          (populates raw_* tables)
       │
3. Pipeline triggered →  POST /api/pipeline/run (or via frontend)
       │
4. Download to temp   →  Orchestrator downloads from Supabase to temp dirs
       │
5. Process through    →  CleaningAgent → FeatureAgent → HypothesisAgent
   7 agents              → InsightsAgent → KPIAgent → ForecastAgent → ActionAgent
       │
6. Store results      →  Snapshots to Supabase tables
                          CSV artifacts to storage bucket
       │
7. Rebuild RAG index  →  Pipeline outputs ingested into pgvector
       │
8. Cleanup            →  Temp directories deleted
```

## Pipeline Modules

Each agent wraps a pipeline module in `backend/pipeline/`. These modules contain the actual data processing logic.

### `pipeline/cleaning/`

Data cleaning and validation.

| File | Purpose |
|---|---|
| `clean_folder.py` | CLI entry point — processes all CSVs in a directory |
| `retail_cleaner.py` | Retail-specific cleaning logic |
| `retail_core.py` | Core cleaning functions (31KB) — outlier detection, type coercion, null handling |
| `auto_detector.py` | Automatic data type and issue detection |
| `ge_validate.py` | Great Expectations validation rules |
| `dq_dashboard.py` | Data quality dashboard generation |
| `config/` | Cleaning configuration files (YAML) |
| `dbt/` | dbt models for data transformation |

### `pipeline/features/`

Feature engineering using Featuretools.

| File | Purpose |
|---|---|
| `feature_folder.py` | CLI entry point — processes cleaned data |
| `src/feature_engineer.py` | Core feature engineering logic |
| `src/business_feature_engineer.py` | Business domain-specific features |
| `src/entity_detector.py` | Detects entities and relationships between tables |
| `src/feature_recipes.py` | Pre-built feature templates |
| `src/feature_registry.py` | Feature catalog/registry |
| `src/ft_engineer.py` | Featuretools integration |
| `src/schema_mapper.py` | Schema mapping utilities |
| `src/ontology/` | Feature ontology definitions |

### `pipeline/hypothesis/`

Statistical hypothesis testing.

| File | Purpose |
|---|---|
| `runner.py` | Orchestration — runs all tests, applies FDR correction |
| `tests.py` | Statistical test implementations (t-test, chi-squared, correlation) |
| `infer.py` | Inference logic |
| `io.py` | File I/O utilities |

### `pipeline/insights/`

Business insight generation.

| File | Purpose |
|---|---|
| `runner.py` | Orchestration — generates all insight types |
| `customer.py` | Customer insights (churn risk, segmentation, CLV) |
| `product.py` | Product insights (performance, cross-sell opportunities) |
| `prescriptions.py` | Actionable prescriptions with priority/urgency |
| `hypothesis_support.py` | Statistical evidence for insights |
| `scoring.py` | Insight scoring and ranking |
| `thresholds.py` | Threshold definitions for alerts |
| `schemas.py` | Data schemas for insight objects |

### `pipeline/kpi/`

Key Performance Indicator computation.

| File | Purpose |
|---|---|
| `runner.py` | Orchestration — computes all KPIs (21KB) |
| `metrics.py` | KPI metric definitions (37KB) — revenue, AOV, churn, conversion, inventory, marketing |
| `io.py` | Data loading utilities |

### `pipeline/forecast/`

Machine learning forecasting.

| File | Purpose |
|---|---|
| `runner.py` | Orchestration — runs all forecast models (16KB) |
| `predict.py` | General prediction logic |
| `predict_demand.py` | Demand forecasting |
| `train_cashflow.py` | Cashflow model training |
| `train_demand.py` | Demand model training |
| `train_revenue.py` | Revenue model training |
| `train_churn.py` | Churn model training |
| `features.py` | Time-series feature engineering |
| `schemas.py` | Data schemas |
| `io.py` | File I/O and path management |

## Pre-trained ML Models

Located in `backend/models/`:

| Model File | Algorithm | Purpose |
|---|---|---|
| `revenue_hgbr_v1.joblib` (535KB) | HistGradientBoosting Regressor | Revenue forecasting |
| `demand_hgbr_v1.joblib` (218KB) | HistGradientBoosting Regressor | Demand forecasting |
| `cashflow_hgbr_v1.joblib` (637KB) | HistGradientBoosting Regressor | Cashflow forecasting |
| `cashflow_proxy_hgbr_v1.joblib` (557KB) | HistGradientBoosting Regressor | Cashflow proxy model |
| `churn_logreg_cal_v1.joblib` (9KB) | Calibrated Logistic Regression | Churn prediction |

These models are loaded by the forecast pipeline during the ForecastAgent's `act()` phase. They can be retrained by running the corresponding `train_*.py` scripts.
