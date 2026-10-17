"""Dataset manifests: the single source of truth for what we download, from
where, under which conditions, and what counts as an independent unit.

A manifest is reviewed like code. Nothing is downloaded that is not declared
here, and nothing is declared here whose source is not in `allowlist.yaml`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from frda import paths
from frda.yamlio import load_yaml

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Publication(Strict):
    pmid: str | None = None
    doi: str | None = None
    citation: str


class ManifestFile(Strict):
    name: str
    url: str
    sha256: str | None = Field(
        default=None, description="Filled by `frda fetch --record-checksums`, then frozen."
    )
    size_bytes: int | None = None
    content: str = Field(description="What the file contains, in plain words.")
    orientation: Literal["genes_x_samples"] = "genes_x_samples"
    gene_id_column: str
    gene_id_type: Literal["symbol", "ensembl_gene_id"]
    values: str = Field(description="Exact nature of the values (raw counts, normalised...).")
    column_map: dict[str, str] = Field(
        default_factory=dict,
        description="File column -> manifest sample name, when the file uses other ids "
        "(e.g. SRA run accessions). Must cover every sample column of the file.",
    )
    comment_prefix: str | None = Field(
        default=None, description="Leading metadata lines starting with this prefix are skipped."
    )

    @field_validator("url")
    @classmethod
    def https_only(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("file URLs must be https://")
        return v

    @field_validator("sha256")
    @classmethod
    def sha_format(cls, v: str | None) -> str | None:
        if v is not None and not SHA256_RE.match(v):
            raise ValueError("sha256 must be 64 lowercase hex chars")
        return v


class Group(Strict):
    name: str
    description: str
    samples: list[str] = Field(min_length=1, description="Exact column names in the matrix.")
    independent_units: int = Field(
        ge=1, description="Number of biologically independent units in this group."
    )
    unit: Literal["donor", "cell_line", "culture_replicate", "animal"]


class Access(Strict):
    level: Literal["public"]  # DUA / controlled access is out of scope by design.
    terms: str
    reusable_with_llm_assistant: bool
    rationale: str


class Manifest(Strict):
    id: str
    title: str
    source: str
    accession: str
    landing_url: str
    organism: str
    tissue_or_model: str
    assay: str
    platform: str | None = None
    publications: list[Publication] = Field(min_length=1)
    access: Access
    unit_of_observation: str
    independence_note: str
    known_confounders: list[str] = Field(default_factory=list)
    groups: list[Group] = Field(min_length=1)
    files: list[ManifestFile] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def groups_disjoint(self) -> Manifest:
        seen: dict[str, str] = {}
        for g in self.groups:
            for s in g.samples:
                if s in seen:
                    raise ValueError(f"sample {s} in both {seen[s]} and {g.name}")
                seen[s] = g.name
        return self

    def group(self, name: str) -> Group:
        for g in self.groups:
            if g.name == name:
                return g
        raise KeyError(f"{self.id}: no group {name!r}")

    def file(self, name: str) -> ManifestFile:
        for f in self.files:
            if f.name == name:
                return f
        raise KeyError(f"{self.id}: no file {name!r}")


class AllowedSource(Strict):
    id: str
    name: str
    url_prefixes: list[str]
    terms_url: str
    allowed_use: str


class Allowlist(Strict):
    sources: list[AllowedSource]

    def source_for(self, url: str) -> AllowedSource | None:
        for s in self.sources:
            if any(url.startswith(p) for p in s.url_prefixes):
                return s
        return None


def manifest_paths(directory: Path | None = None) -> list[Path]:
    directory = directory or paths.MANIFESTS
    return sorted(p for p in directory.glob("*.yaml") if p.stem.upper().startswith("GSE"))


def load_manifest(dataset_id: str, directory: Path | None = None) -> Manifest:
    directory = directory or paths.MANIFESTS
    return Manifest.model_validate(load_yaml(directory / f"{dataset_id}.yaml"))


def load_all(directory: Path | None = None) -> list[Manifest]:
    return [Manifest.model_validate(load_yaml(p)) for p in manifest_paths(directory)]


def load_allowlist(directory: Path | None = None) -> Allowlist:
    directory = directory or paths.MANIFESTS
    return Allowlist.model_validate(load_yaml(directory / "allowlist.yaml"))
