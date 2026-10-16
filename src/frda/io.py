"""Loading matrices declared in manifests. Analyses go through these helpers so
that group membership always comes from the reviewed manifest, never from an
ad-hoc regex in a pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from frda.acquire import raw_path
from frda.manifest import Manifest, load_manifest


def load_matrix(dataset_id: str, file_name: str | None = None, raw_dir: Path | None = None):
    """Return (DataFrame genes x samples, Manifest). Index = gene ids."""
    m = load_manifest(dataset_id)
    f = m.files[0] if file_name is None else m.file(file_name)
    path = raw_path(m, f, raw_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run `make fetch` first")
    df = pd.read_csv(path, sep="\t", index_col=f.gene_id_column)
    df.index = df.index.astype(str)
    return df, m


def group_columns(manifest: Manifest, group: str) -> list[str]:
    return list(manifest.group(group).samples)


def check_columns(df: pd.DataFrame, manifest: Manifest) -> list[str]:
    """Problems between the matrix header and the manifest groups (empty = OK)."""
    problems: list[str] = []
    declared = {s for g in manifest.groups for s in g.samples}
    cols = set(map(str, df.columns))
    for s in sorted(declared - cols):
        problems.append(f"{manifest.id}: sample {s} declared in manifest but absent from matrix")
    for s in sorted(cols - declared):
        problems.append(f"{manifest.id}: column {s} in matrix but not assigned to any group")
    return problems
