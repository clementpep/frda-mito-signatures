from __future__ import annotations

import subprocess
from pathlib import Path

from frda import paths


def git(*args: str, root: Path | None = None, check: bool = True) -> str:
    res = subprocess.run(
        ["git", *args], cwd=root or paths.ROOT, capture_output=True, text=True, check=False
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout.strip()


def commits_touching(path: str, root: Path | None = None) -> list[str]:
    """Commits that touched `path`, newest first (empty if untracked/no git)."""
    try:
        out = git("log", "--format=%H", "--", path, root=root)
    except RuntimeError:
        return []
    return [line for line in out.splitlines() if line]


def is_ancestor(a: str, b: str, root: Path | None = None) -> bool:
    res = subprocess.run(
        ["git", "merge-base", "--is-ancestor", a, b], cwd=root or paths.ROOT, capture_output=True
    )
    return res.returncode == 0


def tracked_files(root: Path | None = None) -> list[str]:
    try:
        return git("ls-files", root=root).splitlines()
    except RuntimeError:
        return []
