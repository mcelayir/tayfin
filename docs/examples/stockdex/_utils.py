import json
from pathlib import Path
import pandas as pd
import datetime
import decimal
import numpy as np


def _sanitize_value(v):
    # Handle pandas/num types and convert to JSON-serializable primitives
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        try:
            return float(v)
        except Exception:
            return str(v)
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    return v


def write_schema_and_data(outdir: Path, name: str, df: pd.DataFrame, fmt: str):
    outdir.mkdir(parents=True, exist_ok=True)
    sample_rows = df.head(3).to_dict(orient="records")
    # sanitize sample rows
    sanitized = []
    for r in sample_rows:
        sr = {}
        for k, v in r.items():
            sr[k] = _sanitize_value(v)
        sanitized.append(sr)

    schema = {
        "name": name,
        "shape": df.shape,
        "columns": [c for c in df.columns],
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "sample": sanitized,
    }
    schema_path = outdir / f"schema_{name}.json"
    with schema_path.open("w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
    if fmt in ("csv", "both") and not df.empty:
        data_path = outdir / f"data_{name}.csv"
        df.to_csv(data_path, index=False)
