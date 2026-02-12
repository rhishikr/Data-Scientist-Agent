from __future__ import annotations
import os, json, argparse
import pandas as pd
from retail_core import clean_table, infer_table_type, load_config

# (optional) only used for --verbose detection printouts
try:
    from auto_detector import guess_table
except Exception:
    guess_table = None

__version__ = "rc-yaml-2025-10-30"

def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    if path.lower().endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file: {path}")

def _write_any(df: pd.DataFrame, path: str):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    if path.endswith((".parquet", ".pq")):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)

def main():
    ap = argparse.ArgumentParser(description="Retail Cleaner (YAML-driven)")
    ap.add_argument("--input", required=True, help="File or folder (csv/parquet)")
    ap.add_argument("--table", help="transactions, inventory, products, returns, customers, web_analytics, campaigns, pricing, purchase_orders, shipments")
    ap.add_argument("--output", help="Output file or folder")
    ap.add_argument("--report", help="Report path (json). If folder input, per-file reports go into output folder")
    ap.add_argument("--config", default="config/defaults.yaml", help="YAML config path")
    ap.add_argument("--outlier", default=None, choices=["iqr","mad"], help="Override YAML outlier method")
    ap.add_argument("--verbose", action="store_true", help="Print table detection scores")  # ← NEW
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.outlier:
        cfg["outlier_method"] = args.outlier

    # Helper handles both new/old infer_table_type signatures
    def _infer(df: pd.DataFrame, filename: str | None):
        try:
            return infer_table_type(df, filename=filename, cfg=cfg)  # new signature
        except TypeError:
            return infer_table_type(df, filename=filename)  # fallback to old

    # -------- Folder mode --------
    if os.path.isdir(args.input):
        out_dir = args.output or os.path.join(args.input, "_cleaned")
        os.makedirs(out_dir, exist_ok=True)

        for fname in os.listdir(args.input):
            fp = os.path.join(args.input, fname)
            if not os.path.isfile(fp):
                continue
            try:
                df = _read_any(fp)
            except Exception:
                continue

            # Optional: show detection scores
            if args.verbose and guess_table is not None:
                try:
                    _, _, _, scores = guess_table(df, cfg, filename=fname)
                    best = max(scores, key=scores.get)
                    print(f"[detect] {fname} → best={best} ({scores[best]:.2f}) scores={scores}")
                except Exception as e:
                    print(f"[detect] {fname} → detection skipped ({e})")

            table = args.table or _infer(df, filename=fname) or "transactions"
            cleaned, rep = clean_table(df, table=table, cfg=cfg)

            stem, _ = os.path.splitext(fname)
            out_fp = os.path.join(out_dir, f"{stem}_{table}_clean.csv")
            rep_fp = os.path.join(out_dir, f"{stem}_{table}_report.json")
            _write_any(cleaned, out_fp)
            with open(rep_fp, "w") as f:
                json.dump(rep.asdict(), f, indent=2, default=str)
            print(f"[OK] {fname} -> {out_fp} ({table})")
        return

    # -------- Single file mode --------
    df = _read_any(args.input)

    if args.verbose and guess_table is not None:
        try:
            base = os.path.basename(args.input)
            _, _, _, scores = guess_table(df, cfg, filename=base)
            best = max(scores, key=scores.get)
            print(f"[detect] {base} → best={best} ({scores[best]:.2f}) scores={scores}")
        except Exception as e:
            print(f"[detect] {args.input} → detection skipped ({e})")

    table = args.table or _infer(df, filename=args.input) or "transactions"
    cleaned, rep = clean_table(df, table=table, cfg=cfg)

    stem, _ = os.path.splitext(args.input)
    out_fp = args.output or stem + f"_{table}_clean.csv"
    rep_fp = args.report or stem + f"_{table}_report.json"
    _write_any(cleaned, out_fp)
    with open(rep_fp, "w") as f:
        json.dump(rep.asdict(), f, indent=2, default=str)
    print(json.dumps(rep.asdict(), indent=2, default=str))

if __name__ == "__main__":
    main()
