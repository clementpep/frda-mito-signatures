"""Export of results/hub/summary.json, read by poups-ai-hub (/research).
Contract: docs/HUB_CONTRACT.md. Bump SCHEMA_VERSION on any breaking change
and update the hub's zod schema in the same week."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from frda import paths
from frda.backlog import load_backlog
from frda.claims import load_ledger
from frda.gitutil import git
from frda.manifest import load_all
from frda.reports import load_reports
from frda.yamlio import load_yaml

SCHEMA_VERSION = 1
REPO_URL = "https://github.com/clementpep/frda-mito-signatures"
VOLATILE = ("generated_at", "commit")


def _project(root: Path) -> dict[str, Any]:
    meta = load_yaml(root / "autonomy" / "project.yaml")
    return {**meta, "repo_url": REPO_URL}


def build_summary(root: Path | None = None) -> dict[str, Any]:
    root = root or paths.ROOT
    backlog = load_backlog(root / "autonomy" / "backlog.yaml")
    ledger = load_ledger(root / "evaluation" / "claims.yaml")
    reports = load_reports(root / "autonomy" / "verifications")
    manifests = load_all(root / "data-manifests")

    counts: dict[str, int] = {}
    for t in backlog.tasks:
        counts[t.status] = counts.get(t.status, 0) + 1

    milestones = []
    for m in backlog.milestones:
        tasks = [t for t in backlog.tasks if t.milestone == m.id]
        done = sum(t.status == "done" for t in tasks)
        status = "done" if tasks and done == len(tasks) else ("in_progress" if done else "todo")
        milestones.append(
            {
                "id": m.id,
                "title": m.title,
                "goal": m.goal,
                "status": status,
                "tasks_done": done,
                "tasks_total": len(tasks),
            }
        )

    verifications = [
        {
            "task": meta.task,
            "date": meta.date,
            "verdict": meta.verdict,
            "summary": meta.summary,
            "attempt": meta.attempt,
            "acceptance_met": meta.acceptance_met,
            "report_url": f"{REPO_URL}/blob/main/{p.relative_to(root).as_posix()}",
        }
        for p, meta in reports
    ]
    verifications.sort(key=lambda v: (v["date"], v["task"]), reverse=True)

    try:
        commit = git("rev-parse", "HEAD", root=root)
    except RuntimeError:
        commit = "unknown"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit,
        "project": _project(root),
        "progress": {
            "total": len(backlog.tasks),
            **{
                s: counts.get(s, 0)
                for s in (
                    "done",
                    "in_review",
                    "ready",
                    "changes_requested",
                    "blocked",
                    "needs_human",
                    "proposed",
                )
            },
        },
        "milestones": milestones,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "milestone": t.milestone,
                "status": t.status,
                "kind": t.kind,
            }
            for t in backlog.tasks
        ],
        "claims": [
            {
                "id": c.id,
                "statement": c.statement,
                "status": c.status,
                "evidence_level": c.evidence_level,
                "datasets": c.datasets,
                "limitations": c.limitations,
                "verified": c.verified_by is not None,
                "source": (
                    {"pmid": c.source.pmid, "doi": c.source.doi, "location": c.source.location}
                    if c.source
                    else None
                ),
            }
            for c in ledger.claims
        ],
        "verifications": verifications[:20],
        "datasets": [
            {
                "id": m.id,
                "title": m.title,
                "tissue_or_model": m.tissue_or_model,
                "assay": m.assay,
                "url": m.landing_url,
                "groups": [
                    {
                        "name": g.name,
                        "independent_units": g.independent_units,
                        "unit": g.unit,
                        "samples": len(g.samples),
                    }
                    for g in m.groups
                ],
            }
            for m in manifests
        ],
    }


def stable(summary: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in summary.items() if k not in VOLATILE}


def write(path: Path | None = None) -> Path:
    path = path or paths.HUB_SUMMARY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_summary(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path
