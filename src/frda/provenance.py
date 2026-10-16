"""Run records. Every pipeline writes `<out>/run.json` through `write_run`, so
any number in the repo can be traced to: code commit, input checksums,
parameters, package versions and output checksums."""

from __future__ import annotations

import contextlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from frda import paths
from frda.hashing import sha256_file

TRACKED_PACKAGES = ("numpy", "pandas", "scipy", "statsmodels", "matplotlib", "frda")


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=paths.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def package_versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for name in TRACKED_PACKAGES:
        with contextlib.suppress(metadata.PackageNotFoundError):
            out[name] = metadata.version(name)
    return out


def write_run(
    out_dir: Path,
    *,
    pipeline: str,
    task: str,
    inputs: list[dict[str, str]],
    params: dict[str, Any],
    independent_units: dict[str, int],
    outputs: list[str],
    analysis_kind: str = "exploratory",
    preregistration: str | None = None,
) -> Path:
    """`analysis_kind` is "exploratory" or "confirmatory"; a confirmatory run
    must cite the preregistration file it executes (checked by the gates)."""
    if analysis_kind not in {"exploratory", "confirmatory", "reproduction", "qc"}:
        raise ValueError(f"unknown analysis_kind {analysis_kind}")
    if analysis_kind == "confirmatory" and not preregistration:
        raise ValueError("a confirmatory run must reference its preregistration file")
    record = {
        "pipeline": pipeline,
        "task": task,
        "analysis_kind": analysis_kind,
        "preregistration": preregistration,
        "code_sha": _git_sha(),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "inputs": inputs,
        "params": params,
        "independent_units": independent_units,
        "environment": package_versions(),
        "outputs": [{"path": o, "sha256": sha256_file(out_dir / o)} for o in sorted(outputs)],
    }
    path = out_dir / "run.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def write_json(path: Path, data: Any) -> None:
    """Deterministic JSON (sorted keys, rounded floats) so reruns hash equal."""

    def _round(x: Any) -> Any:
        if isinstance(x, float):
            return float(f"{x:.6g}")
        if isinstance(x, dict):
            return {k: _round(v) for k, v in x.items()}
        if isinstance(x, list | tuple):
            return [_round(v) for v in x]
        return x

    path.write_text(json.dumps(_round(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
