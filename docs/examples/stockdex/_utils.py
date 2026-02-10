import json
from pathlib import Path
import pandas as pd


def write_schema_and_data(outdir: Path, name: str, df: pd.DataFrame, fmt: str):
    outdir.mkdir(parents=True, exist_ok=True)
    schema = {
        "name": name,
        "shape": df.shape,
        "columns": [c for c in df.columns],
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "sample": df.head(3).to_dict(orient="records"),
    }
    schema_path = outdir / f"schema_{name}.json"
    with schema_path.open("w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
    if fmt in ("csv", "both") and not df.empty:
        data_path = outdir / f"data_{name}.csv"
        df.to_csv(data_path, index=False)
