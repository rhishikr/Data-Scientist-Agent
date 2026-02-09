from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Any


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # write empty CSV with no rows
        pd.DataFrame().to_csv(path, index=False)
        return
    pd.DataFrame(rows).to_csv(path, index=False)


def write_single_row_csv(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([data]).to_csv(path, index=False)
