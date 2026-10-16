"""State of the autonomy loop, derived from git only.

Branch protocol (routines/procedures.md):
  auto/<TASK>      work in progress; head commit `work(<TASK>): ...` -> awaiting verification
                   head commit `verify(<TASK>): CHANGES_REQUESTED|NEEDS_HUMAN ...` -> back to worker / human
  verified/<TASK>  auto/<TASK> + one `verify(<TASK>): PASS` commit; landed on main by
                   .github/workflows/land-verified.yml, which deletes both branches.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from frda import paths
from frda.backlog import load_backlog, pick_next, recent_tracks
from frda.gitutil import git, is_ancestor
from frda.research import load_plan
from frda.yamlio import load_yaml

VERDICT_RE = re.compile(
    r"^verify\((?P<task>[^)]+)\): (?P<verdict>PASS|CHANGES_REQUESTED|NEEDS_HUMAN)"
)


@dataclass
class Branch:
    name: str
    task: str
    kind: str  # auto | verified
    head: str
    subject: str
    committed_at: str
    state: str  # needs_verification | changes_requested | needs_human | landing_pending | landed


def _remote_branches(prefix: str, root: Path) -> list[tuple[str, str, str, str]]:
    out = git(
        "for-each-ref",
        "--format=%(refname:strip=3)\t%(objectname)\t%(subject)\t%(committerdate:iso-strict)",
        f"refs/remotes/origin/{prefix}",
        root=root,
    )
    rows = []
    for line in out.splitlines():
        if line.strip():
            name, sha, subject, date = line.split("\t", 3)
            rows.append((name, sha, subject, date))
    return rows


def branches(root: Path | None = None) -> list[Branch]:
    root = root or paths.ROOT
    result: list[Branch] = []
    for kind in ("auto", "verified"):
        for name, sha, subject, date in _remote_branches(kind + "/", root):
            task = name.split("/", 1)[1]
            if is_ancestor(sha, "origin/main", root):
                state = "landed"
            elif kind == "verified":
                state = "landing_pending"
            else:
                m = VERDICT_RE.match(subject)
                if m and m.group("verdict") == "CHANGES_REQUESTED":
                    state = "changes_requested"
                elif m and m.group("verdict") == "NEEDS_HUMAN":
                    state = "needs_human"
                elif m and m.group("verdict") == "PASS":
                    state = "landing_pending"
                else:
                    state = "needs_verification"
            result.append(Branch(name, task, kind, sha, subject, date, state))
    result.sort(key=lambda b: b.committed_at)
    return result


def status(root: Path | None = None) -> dict[str, Any]:
    root = root or paths.ROOT
    cfg = load_yaml(root / "autonomy" / "config.yaml")
    bs = branches(root)
    verified_tasks = {b.task for b in bs if b.kind == "verified" and b.state != "landed"}
    open_auto = [b for b in bs if b.kind == "auto" and b.state != "landed"]
    # A task whose verified/ branch is waiting to land is no longer the worker's.
    active = [b for b in open_auto if b.task not in verified_tasks]
    wip = [
        b for b in active if b.task.startswith(("T-", "L-", "FIX-")) and b.state != "needs_human"
    ]

    next_worker: dict[str, Any] | None = None
    fix = next((b for b in active if b.state == "changes_requested"), None)
    if fix:
        next_worker = {"action": "address_changes", "task": fix.task, "branch": fix.name}
    elif len(wip) < cfg["wip_limit"]:
        bl = load_backlog(root / "autonomy" / "backlog.yaml")
        taken = {b.task for b in bs if b.state != "landed"}
        plan = load_plan(root)
        task, reason = pick_next(
            bl,
            exclude=taken,
            budget=plan.get("track_budget"),
            recent_tracks=recent_tracks(bl, root, plan.get("budget_window", 10)),
        )
        if task:
            next_worker = {
                "action": "start_task",
                "task": task.id,
                "track": task.track,
                "branch": f"auto/{task.id}",
                "why": reason,
            }

    pending = [b for b in active if b.state == "needs_verification"]
    next_verifier = (
        {
            "action": "verify",
            "task": pending[0].task,
            "branch": pending[0].name,
            "head": pending[0].head,
        }
        if pending
        else None
    )
    return {
        "config": cfg,
        "branches": [asdict(b) for b in bs],
        "wip": len(wip),
        "next_for_worker": next_worker,
        "next_for_verifier": next_verifier,
        "landing_pending": [b.name for b in bs if b.state == "landing_pending"],
        "needs_human": [b.name for b in bs if b.state == "needs_human"],
        "stale_landed": [b.name for b in bs if b.state == "landed"],
    }
