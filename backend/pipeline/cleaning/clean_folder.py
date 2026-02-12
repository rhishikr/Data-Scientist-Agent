from __future__ import annotations

import os
import argparse
import json
from pathlib import Path

import pandas as pd

from retail_core import load_config, clean_table, infer_table_type

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


print("RUNNING FILE:", os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(
        description="Clean all CSV files in a folder and write cleaned CSVs + report."
    )
    parser.add_argument("--input_dir", required=True, help="Folder containing raw CSV files")
    parser.add_argument("--output_dir", required=True, help="Folder to write cleaned CSV files")
    parser.add_argument("--reports_dir", required=True, help="Folder to write cleaning_report.json")
    parser.add_argument(
        "--config",
        default="config/defaults.yaml",
        help="Path to YAML config (relative to retail-cleaner-starter)",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()

    # If config is absolute, use it. Otherwise resolve relative to THIS repo folder.
    config_path = (
        Path(args.config).resolve()
        if Path(args.config).is_absolute()
        else (Path(__file__).parent / args.config).resolve()
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(str(config_path))

    report = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "config_path": str(config_path),
        "files": [],
        "errors": [],
    }

    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {input_dir}")

    for f in csv_files:
        try:
            df = pd.read_csv(f)

            # ✅ FIX 1: infer_table_type signature is (df, filename, cfg)
            table_type = infer_table_type(df, str(f), cfg)

            if not table_type:
                raise ValueError(f"Could not infer table type for file: {f.name}")

            # ✅ FIX 2: clean_table signature is (df, table, cfg)
            cleaned_df, clean_rep = clean_table(df, table_type, cfg)

            out_name = f"{f.stem}_cleaned.csv"
            out_path = output_dir / out_name
            cleaned_df.to_csv(out_path, index=False)

            # ✅ FIX 3: AuditReport is a dataclass → use asdict()
            rep_dict = clean_rep.asdict() if hasattr(clean_rep, "asdict") else dict(clean_rep)

            report["files"].append(
                {
                    "input_file": f.name,
                    "table_type": table_type,
                    "output_file": out_name,
                    "rows_before": int(rep_dict.get("rows_before", len(df))),
                    "rows_after": int(rep_dict.get("rows_after", len(cleaned_df))),
                    "duplicates_removed": int(rep_dict.get("duplicates_removed", 0)),
                    "dtype_coercions": rep_dict.get("dtype_coercions", {}),
                    "na_filled": rep_dict.get("na_filled", {}),
                    "dates_fixed": int(rep_dict.get("dates_fixed", 0)),
                    "dates_dropped": int(rep_dict.get("dates_dropped", 0)),
                    "rows_dropped_for_required": int(rep_dict.get("rows_dropped_for_required", 0)),
                    "outliers_removed": rep_dict.get("outliers_removed", {}),
                    "rule_violations": rep_dict.get("rule_violations", {}),
                    "rule_warnings": rep_dict.get("rule_warnings", {}),
                    "pandera_errors": rep_dict.get("pandera_errors", []),
                }
            )

        except Exception as e:
            report["errors"].append({"file": f.name, "error": str(e)})

    # Write one single report file
    report_path = reports_dir / "cleaning_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    print(f" Cleaning done. Report written to: {report_path}")
    print(f" Cleaned files written to: {output_dir}")


if __name__ == "__main__":
    main()
