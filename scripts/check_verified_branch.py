"""Guard for land-verified.yml: a `verified/<TASK>` branch may land only if its
last commit is the verifier's PASS commit, sitting directly on the worker's
handover commit it reviewed, and touching only verification bookkeeping.

Usage: python scripts/check_verified_branch.py verified/T-001
"""

from __future__ import annotations

import re
import subprocess
import sys

ALLOWED = ("autonomy/", "evaluation/claims.yaml", "results/hub/summary.json")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main(branch: str) -> int:
    from pathlib import Path

    from frda.reports import ReportMeta
    from frda.yamlio import read_front_matter

    task = branch.removeprefix("verified/")
    errors: list[str] = []
    subject = git("log", "-1", "--format=%s", "HEAD")
    if not re.match(rf"^verify\({re.escape(task)}\): PASS\b", subject):
        errors.append(f"HEAD subject is not 'verify({task}): PASS ...': {subject!r}")
    parent = git("rev-parse", "HEAD~1")
    parent_subject = git("log", "-1", "--format=%s", "HEAD~1")
    if not parent_subject.startswith(f"work({task})"):
        errors.append(
            f"reviewed commit is not the worker handover work({task}): {parent_subject!r}"
        )
    changed = [p for p in git("diff", "--name-only", "HEAD~1", "HEAD").splitlines() if p]
    for p in changed:
        if not p.startswith(ALLOWED):
            errors.append(f"verify commit touches {p} (only {ALLOWED} allowed)")
    reports = [
        p
        for p in changed
        if re.match(rf"^autonomy/verifications/{re.escape(task)}-[0-9a-f]+\.md$", p)
    ]
    if len(reports) != 1:
        errors.append(f"expected exactly one new report for {task}, found {reports}")
    else:
        meta, _ = read_front_matter(Path(reports[0]))
        rm = ReportMeta.model_validate(meta)
        if rm.verdict != "PASS":
            errors.append(f"report verdict is {rm.verdict}")
        if not parent.startswith(rm.reviewed_sha):
            errors.append(f"report reviewed {rm.reviewed_sha}, but the branch parent is {parent}")
        if rm.blocking_findings:
            errors.append(f"report lists {rm.blocking_findings} blocking finding(s)")
    for e in errors:
        print(f"::error::{e}")
    if errors:
        return 1
    print(f"verified branch OK: {task} reviewed at {parent[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
