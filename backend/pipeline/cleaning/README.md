# Retail Cleaner Starter

This is a ready-to-run starter of the YAML-driven retail cleaner + Streamlit UI.

## Quick Start

1) Install Python 3.10+
2) In a terminal inside this folder:

```
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

3) Run the Streamlit UI:
```
streamlit run streamlit_app.py
```
Upload a CSV, pick the table type, and download the cleaned file.

4) Clean via CLI:
```
python retail_cleaner.py --input data/yourfile.csv --table transactions --output out/ --report out/
```

5) Config:
Edit `config/defaults.yaml` to change aliases, dtypes, rules.



Here’s a complete **README.md** you can drop into your project root (`retail-cleaner-starter/README.md`).
It explains every component, from setup to functionality — written in a professional tone suitable for GitHub or documentation hosting.

---

# 🧹 Retail Data Cleaning & Validation System

A modular, **YAML-driven data cleaning and validation framework** built for **retail and e-commerce analytics**.
It standardizes, cleans, and audits large datasets (sales, inventory, customers, pricing, logistics, etc.) — producing human-readable visual reports and machine-readable audit logs.

---

## 🚀 Features

### 1️⃣ **Automated Data Cleaning**

* Detects and cleans datasets across multiple retail domains:

  * Transactions / Sales
  * Inventory
  * Products / Catalog
  * Customers
  * Returns
  * Pricing / Promotions
  * Campaigns / Marketing
  * Purchase Orders
  * Shipments / Logistics
* Automatically infers table type using **column pattern detection** (`auto_detector.guess_table`)
* Cleans **CSV** and **Parquet** files — single or batch folders

---

### 2️⃣ **YAML-Driven Configuration**

* Centralized config in `config/defaults.yaml`
* Defines:

  * Expected columns & aliases
  * Dtypes (`string`, `float`, `Int64`, `boolean`, `datetime64[ns]`)
  * Required fields
  * Outlier handling (IQR or MAD)
  * Business rules
  * Category normalization maps

This makes the system **configurable without editing code**.

---

### 3️⃣ **Data Cleaning Pipeline**

Each dataset passes through a well-structured 9-stage cleaning pipeline (`retail_core.clean_table`):

| Stage | Operation                                   | Description                                                         |
| ----- | ------------------------------------------- | ------------------------------------------------------------------- |
| 1     | **Column normalization & alias resolution** | Matches varied column names using YAML aliases                      |
| 2     | **Date coercion**                           | Parses multiple date formats and drops invalid ones                 |
| 3     | **Type coercion**                           | Converts data types (numeric, boolean, string)                      |
| 4     | **Category standardization**                | Normalizes brand/channel/category values                            |
| 5     | **Missing value handling**                  | Drops incomplete required rows, imputes with median or defaults     |
| 6     | **Business rule enforcement**               | Applies constraints like `price ≥ 0`, `start ≤ end`, etc.           |
| 7     | **Duplicate removal**                       | Deduplicates rows by primary key                                    |
| 8     | **Outlier filtering**                       | Detects anomalies using IQR or MAD                                  |
| 9     | **Pandera schema validation**               | Validates final dataset schema with nullable and version-safe types |

---

### 4️⃣ **Audit & Reporting**

Every run generates a structured audit log (`AuditReport`) containing:

* Rows before/after cleaning
* Renamed columns
* Missing required columns
* Date coercion stats
* Type coercions and missing fills
* Outliers removed
* Rule violations and warnings
* Pandera validation summary

Saved automatically as JSON or displayed as an **interactive Streamlit report**.

---

### 5️⃣ **Streamlit Visual Dashboard**

Run the dashboard:

```bash
streamlit run streamlit_app.py
```

* Upload one or more CSV/Parquet files
* Automatic table inference and cleaning
* Visual audit summary with sections for:

  * Column mapping
  * Missing values filled
  * Outlier detection
  * Business rule violations
  * Pandera validation results
* Optional charts for:

  * Rule violation counts
  * Missing data distributions
  * Category normalization impact

---

### 6️⃣ **CLI Utility**

Run the CLI tool to clean files programmatically:

```bash
python retail_cleaner.py --input ./data/transactions.csv --output ./data/cleaned/ --report ./reports/
```

#### Options:

| Flag        | Description                                          |
| ----------- | ---------------------------------------------------- |
| `--input`   | Path to file or folder                               |
| `--table`   | Force table type (`transactions`, `inventory`, etc.) |
| `--config`  | YAML configuration file                              |
| `--outlier` | Override outlier method (`iqr` / `mad`)              |
| `--verbose` | (Optional) Print column-match scores                 |
| `--output`  | Output directory or file                             |
| `--report`  | JSON report path                                     |

---

### 7️⃣ **Data Quality Dashboard**

Optional add-on (`dq_dashboard.py`) creates an overview of multiple audit reports:

* Aggregates multiple run metrics
* Summarizes violations, missing counts, outliers
* Helps QA teams track cleaning quality over time

---

### 8️⃣ **Corrupted Dataset Testing**

A test suite of large CSVs (`retail_large_data` + `retail_large_data_corrupted`) is included:

* Clean datasets for benchmarking
* Corrupted datasets for validation stress testing:

  * Random missing values
  * Wrong data types
  * Invalid dates (`32/13/2024`)
  * Extreme outliers
  * Negative quantities and closing stock

Use these to verify each stage of your cleaning pipeline.

---

## 🧩 Folder Structure

```
retail-cleaner-starter/
│
├── retail_cleaner.py              # CLI entry point
├── retail_core.py                 # Main cleaning logic
├── auto_detector.py               # Table inference engine
├── streamlit_app.py               # Web dashboard
├── dq_dashboard.py                # Multi-report dashboard
│
├── config/
│   └── defaults.yaml              # YAML schema + cleaning rules
│
├── data/
│   ├── retail_large_data/         # Clean large test datasets
│   └── retail_large_data_corrupted/ # Corrupted stress-test datasets
│
├── reports/                       # Auto-saved audit reports (JSON)
└── README.md
```

---

## ⚙️ Setup

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

Dependencies include:

```
pandas
numpy
pyyaml
pandera
streamlit
matplotlib
```

---

## 📈 Example Usage

### CLI

```bash
python retail_cleaner.py --input data/transactions_large.csv --outlier iqr
```

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

Upload `transactions_large_corrupted.csv` and view:

* Rule Violations
* Outlier removal counts
* Filled missing values
* Pandera schema validation feedback

---

## 🧠 Tech Highlights

* **Schema enforcement:** via Pandera (with version-safe bool/boolen compatibility)
* **Dynamic YAML schema** loading for scalability
* **Streamlit dashboard** for analyst-friendly visualization
* **Modular architecture** (extend with new dataset types easily)
* **Audit transparency:** every operation is tracked and saved

---

## 🏁 Future Extensions

* AI-powered **data quality agent** using LLMs to explain violations
* Integration with **Airbyte or Great Expectations** for ETL pipelines
* Auto-schema generation from raw retail data
* Cloud deployment with AWS Lambda or Streamlit Cloud

---

Would you like me to create a **shorter README.md** (for GitHub display) or keep this full-length documentation format?

