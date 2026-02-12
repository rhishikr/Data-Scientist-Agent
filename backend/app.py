import os
import sys
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ✅ ONLY import your hypothesis runner
from pipeline.hypothesis.runner import run_hypothesis_agent

app = FastAPI(title="Hypothesis Testing Backend Only")

# ✅ optional: keep CORS so you can call it from React later
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/hypothesis/run")
def run_hypothesis():
    """
    Run hypothesis tests using:
    - backend/data/cleaned_data/*.csv
    - backend/data/featured_data/*.csv

    Saves to:
    - backend/data/hypothesis_outputs/hypothesis_results.json
    - backend/data/hypothesis_outputs/hypothesis_results.csv
    """
    return run_hypothesis_agent(alpha=0.05)

BACKEND_ROOT = Path(__file__).resolve().parent  # backend/
DATA_DIR = BACKEND_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
FEATURED_DIR = DATA_DIR / "featured_data"
REPORTS_DIR = DATA_DIR / "reports"
HYP_DIR = DATA_DIR / "hypothesis_outputs"

CLEAN_SCRIPT = BACKEND_ROOT / "pipeline" / "cleaning" / "clean_folder.py"
FE_SCRIPT = BACKEND_ROOT / "pipeline" / "features" / "feature_folder.py"


def _reset_dir(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def _run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()
        raise RuntimeError(err)
    return (p.stdout or "").strip()


@app.get("/api/pipeline/run_all")
def run_all(reset: bool = True, alpha: float = 0.05):
    """
    Full scratch run:
    1) Cleaning  -> backend/data/cleaned
    2) Features  -> backend/data/featured_data
    3) Hypothesis -> backend/data/hypothesis_outputs (via run_hypothesis_agent)
    """
    try:
        # ---- sanity checks
        if not RAW_DIR.exists():
            raise RuntimeError(f"Missing raw folder: {RAW_DIR}")
        if not CLEAN_SCRIPT.exists():
            raise RuntimeError(f"Missing cleaning script: {CLEAN_SCRIPT}")
        if not FE_SCRIPT.exists():
            raise RuntimeError(f"Missing feature script: {FE_SCRIPT}")

        # ---- reset outputs (from scratch)
        if reset:
            _reset_dir(CLEANED_DIR)
            _reset_dir(FEATURED_DIR)
            _reset_dir(REPORTS_DIR)
            _reset_dir(HYP_DIR)
        else:
            CLEANED_DIR.mkdir(parents=True, exist_ok=True)
            FEATURED_DIR.mkdir(parents=True, exist_ok=True)
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            HYP_DIR.mkdir(parents=True, exist_ok=True)

        # ---- 1) CLEANING
        clean_log = _run_cmd(
            [
                sys.executable,
                str(CLEAN_SCRIPT),
                "--input_dir", str(RAW_DIR),
                "--output_dir", str(CLEANED_DIR),
                "--reports_dir", str(REPORTS_DIR),
            ],
            cwd=CLEAN_SCRIPT.parent,
        )

        # ---- 2) FEATURE ENGINEERING
        # Make pipeline/features/src importable if your feature code uses internal imports
        env = os.environ.copy()
        fe_src = (BACKEND_ROOT / "pipeline" / "features" / "src").resolve()
        env["PYTHONPATH"] = str(fe_src) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        fe_log = _run_cmd(
            [
                sys.executable,
                str(FE_SCRIPT),
                "--input_dir", str(CLEANED_DIR),
                "--output_dir", str(FEATURED_DIR),
                "--reports_dir", str(REPORTS_DIR),
            ],
            cwd=FE_SCRIPT.parent,
            env=env,
        )

        # ---- 3) HYPOTHESIS
        hypo = run_hypothesis_agent(alpha=alpha)

        return {
            "status": "success",
            "reset": reset,
            "paths": {
                "raw": str(RAW_DIR),
                "cleaned": str(CLEANED_DIR),
                "featured": str(FEATURED_DIR),
                "reports": str(REPORTS_DIR),
                "hypothesis_outputs": str(HYP_DIR),
            },
            "cleaning_log_tail": clean_log[-1200:],
            "feature_log_tail": fe_log[-1200:],
            "hypothesis": hypo,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Running full pipeline directly (no FastAPI)...")
    run_all(reset=True)
