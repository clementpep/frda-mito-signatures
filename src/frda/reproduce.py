"""Re-execute every registered pipeline from raw data into a scratch directory
and compare output checksums with the committed run records. A pipeline whose
outputs cannot be regenerated bit-for-bit (after the 6-significant-digit
rounding of `provenance.write_json`) is not reproducible, and fails."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frda import paths
from frda.hashing import sha256_file
from frda.yamlio import load_yaml


class Pipeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task: str
    command: str  # must contain {out}
    results_dir: str
    description: str


def load_registry(root: Path | None = None) -> list[Pipeline]:
    root = root or paths.ROOT
    data = load_yaml(root / "pipelines" / "registry.yaml") or {}
    return [Pipeline.model_validate(p) for p in data.get("pipelines") or []]


def reproduce_one(p: Pipeline, root: Path | None = None) -> list[str]:
    root = root or paths.ROOT
    committed = root / p.results_dir / "run.json"
    if not committed.exists():
        return [f"{p.id}: {p.results_dir}/run.json not committed"]
    expected = {o["path"]: o["sha256"] for o in json.loads(committed.read_text())["outputs"]}
    with tempfile.TemporaryDirectory(prefix=f"repro-{p.id}-") as tmp:
        cmd = [part.replace("{out}", tmp) for part in shlex.split(p.command)]
        if cmd and cmd[0] == "python":
            cmd[0] = sys.executable
        res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            return [f"{p.id}: pipeline failed ({res.returncode}): {res.stderr[-2000:]}"]
        problems = []
        for rel, sha in expected.items():
            out = Path(tmp) / rel
            if not out.exists():
                problems.append(f"{p.id}: rerun did not produce {rel}")
            elif sha256_file(out) != sha:
                problems.append(f"{p.id}: {rel} differs on rerun (non-deterministic or stale)")
        return problems
