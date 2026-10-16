"""Repository paths. Everything is resolved from the repo root so the CLI works
from any working directory (routines, CI, notebooks)."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("FRDA_ROOT")
    if env:
        return Path(env).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "data-manifests").is_dir():
            return candidate
    # Fallback: the installed package lives in <root>/src/frda.
    return Path(__file__).resolve().parents[2]


ROOT = repo_root()
MANIFESTS = ROOT / "data-manifests"
DATA = ROOT / "data"
RAW = DATA / "raw"
PROVENANCE_LOG = DATA / "provenance.jsonl"
RESULTS = ROOT / "results"
HUB_SUMMARY = RESULTS / "hub" / "summary.json"
EVALUATION = ROOT / "evaluation"
CLAIMS = EVALUATION / "claims.yaml"
REPRO_TARGETS = EVALUATION / "reproduction-targets.yaml"
AUTONOMY = ROOT / "autonomy"
BACKLOG = AUTONOMY / "backlog.yaml"
VERIFICATIONS = AUTONOMY / "verifications"
PIPELINES_REGISTRY = ROOT / "pipelines" / "registry.yaml"
