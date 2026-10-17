"""Loading matrices declared in manifests. Analyses go through these helpers so
that group membership always comes from the reviewed manifest, never from an
ad-hoc regex in a pipeline."""

from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd

from frda.acquire import raw_path
from frda.manifest import Manifest, ManifestFile, load_manifest


def _leading_comment_lines(path: Path, prefix: str | None) -> int:
    if not prefix:
        return 0
    opener = gzip.open if path.suffix == ".gz" else open
    n = 0
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith(prefix):
                break
            n += 1
    return n


def read_manifest_file(path: Path, f: ManifestFile, nrows: int | None = None) -> pd.DataFrame:
    """Read a declared matrix: skip metadata lines, index by gene id, rename columns to the
    manifest's sample names (column_map). Unmapped columns are kept as-is (and then reported
    by `check_columns`)."""
    df = pd.read_csv(
        path,
        sep="\t",
        index_col=f.gene_id_column,
        skiprows=_leading_comment_lines(path, f.comment_prefix),
        nrows=nrows,
    )
    df.index = df.index.astype(str)
    if f.column_map:
        df = df.rename(columns=f.column_map)
    return df


def load_matrix(dataset_id: str, file_name: str | None = None, raw_dir: Path | None = None):
    """Return (DataFrame genes x samples, Manifest). Index = gene ids."""
    m = load_manifest(dataset_id)
    f = m.files[0] if file_name is None else m.file(file_name)
    path = raw_path(m, f, raw_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run `make fetch` first")
    return read_manifest_file(path, f), m


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
