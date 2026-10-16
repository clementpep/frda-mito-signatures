"""Skeleton for a pipeline. Copy to pNNN_<slug>.py; not registered (example only).

uv run python pipelines/p000_example.py --out /tmp/p000
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from frda.io import group_columns, load_matrix
from frda.provenance import write_json, write_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    df, manifest = load_matrix("GSE104288")
    frda_cols = group_columns(manifest, "FRDA")
    ctrl_cols = group_columns(manifest, "control")
    log = np.log2(df + 1)
    summary = {
        "n_genes": int(df.shape[0]),
        "mean_log2_FRDA": float(log[frda_cols].to_numpy().mean()),
        "mean_log2_control": float(log[ctrl_cols].to_numpy().mean()),
    }
    write_json(args.out / "summary.json", summary)
    f = manifest.files[0]
    write_run(
        args.out,
        pipeline="P-000",
        task="T-000",
        inputs=[{"dataset": manifest.id, "file": f.name, "sha256": f.sha256 or ""}],
        params={"transform": "log2(x+1)"},
        independent_units={g.name: g.independent_units for g in manifest.groups},
        outputs=["summary.json"],
        analysis_kind="exploratory",
    )


if __name__ == "__main__":
    main()
