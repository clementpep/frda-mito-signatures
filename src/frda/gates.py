"""Deterministic verification gates (`frda verify`).

These are the checks no agent gets to argue with. The verifier routine and
the CI run them on every branch; the landing workflow refuses to merge into
`main` unless they all pass. Weakening a gate is itself a blocking finding
(see routines/verifier.md, "gate tampering").
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from frda import backlog as backlog_mod
from frda import hub, paper, prereg, research
from frda.claims import check_claim, load_ledger
from frda.gitutil import commits_touching, is_ancestor, tracked_files
from frda.hashing import sha256_file
from frda.manifest import load_all, load_allowlist
from frda.reports import load_reports

Status = Literal["PASS", "FAIL", "WARN", "SKIP"]
MAX_TRACKED_BYTES = 2 * 1024 * 1024
MIN_INDEPENDENT_UNITS = 3


@dataclass
class GateResult:
    name: str
    status: Status
    details: list[str] = field(default_factory=list)


@dataclass
class Context:
    root: Path
    require_data: bool = False


def _result(name: str, problems: list[str], warnings: list[str] | None = None) -> GateResult:
    if problems:
        return GateResult(name, "FAIL", problems)
    if warnings:
        return GateResult(name, "WARN", warnings)
    return GateResult(name, "PASS")


def gate_manifests(ctx: Context) -> GateResult:
    problems: list[str] = []
    try:
        allow = load_allowlist(ctx.root / "data-manifests")
        manifests = load_all(ctx.root / "data-manifests")
    except ValidationError as exc:
        return GateResult("manifests", "FAIL", [str(exc)])
    if not manifests:
        problems.append("no dataset manifest")
    for m in manifests:
        if not m.access.reusable_with_llm_assistant:
            problems.append(f"{m.id}: not reusable with an LLM assistant: cannot be processed here")
        for f in m.files:
            if allow.source_for(f.url) is None:
                problems.append(f"{m.id}/{f.name}: source not in allowlist ({f.url})")
            if not f.sha256:
                problems.append(f"{m.id}/{f.name}: sha256 not recorded")
    return _result("manifests", problems)


def gate_data_integrity(ctx: Context) -> GateResult:
    from frda.io import check_columns, read_manifest_file  # imports pandas lazily

    problems: list[str] = []
    missing: list[str] = []
    for m in load_all(ctx.root / "data-manifests"):
        for f in m.files:
            path = ctx.root / "data" / "raw" / m.id / f.name
            if not path.exists():
                missing.append(f"{m.id}/{f.name} not downloaded")
                continue
            if f.sha256 and sha256_file(path) != f.sha256:
                problems.append(f"{m.id}/{f.name}: sha256 mismatch with manifest")
                continue
            try:
                header = read_manifest_file(path, f, nrows=2)
            except ValueError as exc:
                problems.append(f"{m.id}/{exc}")
                continue
            problems += [f"{f.name}: {p}" for p in check_columns(header, m)]
    if missing and ctx.require_data:
        problems += missing
    if missing and not problems:
        return GateResult("data_integrity", "SKIP", missing)
    return _result("data_integrity", problems)


def gate_repo_hygiene(ctx: Context) -> GateResult:
    problems: list[str] = []
    for rel in tracked_files(ctx.root):
        if rel.startswith("data/") and rel != "data/README.md":
            problems.append(f"{rel}: data files must not be committed")
        p = ctx.root / rel
        if p.is_file() and p.stat().st_size > MAX_TRACKED_BYTES:
            problems.append(
                f"{rel}: {p.stat().st_size} bytes > {MAX_TRACKED_BYTES} (results too big?)"
            )
    return _result("repo_hygiene", problems)


def _run_record_for(ctx: Context, artifact: str) -> dict | None:
    run = (ctx.root / artifact).parent / "run.json"
    if not run.exists():
        return None
    return json.loads(run.read_text(encoding="utf-8"))


def gate_claims(ctx: Context) -> GateResult:
    try:
        ledger = load_ledger(ctx.root / "evaluation" / "claims.yaml")
    except ValidationError as exc:
        return GateResult("claims", "FAIL", [str(exc)])
    problems: list[str] = []
    ids = [c.id for c in ledger.claims]
    problems += [f"duplicate claim id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    for c in ledger.claims:
        problems += check_claim(c, ctx.root)
        run = _run_record_for(ctx, c.artifact)
        if run is None:
            problems.append(f"{c.id}: no run.json next to its artifact (untraceable)")
            continue
        units = run.get("independent_units") or {}
        if not units:
            problems.append(f"{c.id}: run.json declares no independent_units")
        elif min(units.values()) < MIN_INDEPENDENT_UNITS and c.evidence_level != "exploratory":
            problems.append(
                f"{c.id}: a group has {min(units.values())} independent unit(s) "
                f"(< {MIN_INDEPENDENT_UNITS}); evidence_level must be 'exploratory'"
            )
        if (
            c.evidence_level == "preregistered_confirmed"
            and run.get("analysis_kind") != "confirmatory"
        ):
            problems.append(f"{c.id}: preregistered_confirmed requires a confirmatory run")
    # Brief: no "new" analysis before a published result has been reproduced.
    has_reproduction = any(c.status == "reproduced" and c.verified_by for c in ledger.claims)
    for c in ledger.claims:
        if c.status == "new" and not has_reproduction:
            problems.append(f"{c.id}: 'new' claim before any verified reproduction (milestone M1)")
    return _result("claims", problems)


def gate_preregistration(ctx: Context) -> GateResult:
    problems: list[str] = []
    files = prereg.all_files(ctx.root / "preregistrations")
    by_rel = {}
    for f in files:
        rel = f.relative_to(ctx.root).as_posix()
        try:
            prereg.load(f)
        except ValidationError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        by_rel[rel] = f
        history = commits_touching(rel, ctx.root)
        if len(history) > 1:
            problems.append(f"{rel}: edited after being committed; amend with a new PR-xxx file")
    for run_path in sorted((ctx.root / "results").glob("*/run.json")):
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run.get("analysis_kind") != "confirmatory":
            continue
        rel_run = run_path.relative_to(ctx.root).as_posix()
        pr = run.get("preregistration")
        if not pr or pr not in by_rel:
            problems.append(f"{rel_run}: confirmatory run without a valid preregistration")
            continue
        pr_commits = commits_touching(pr, ctx.root)
        if not pr_commits:
            problems.append(f"{rel_run}: preregistration {pr} is not committed yet")
            continue
        run_commits = commits_touching(rel_run, ctx.root)
        if run_commits:
            first_run = run_commits[-1]
            if pr_commits[-1] == first_run or not is_ancestor(pr_commits[-1], first_run, ctx.root):
                problems.append(f"{rel_run}: results committed before/with their preregistration")
    return _result("preregistration", problems)


def gate_run_records(ctx: Context) -> GateResult:
    problems: list[str] = []
    for run_path in sorted((ctx.root / "results").glob("*/run.json")):
        rel = run_path.relative_to(ctx.root).as_posix()
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: invalid JSON ({exc})")
            continue
        for key in ("pipeline", "task", "code_sha", "inputs", "params", "outputs", "environment"):
            if key not in run:
                problems.append(f"{rel}: missing {key}")
        for out in run.get("outputs", []):
            p = run_path.parent / out["path"]
            if not p.exists():
                problems.append(f"{rel}: output {out['path']} missing")
            elif sha256_file(p) != out["sha256"]:
                problems.append(f"{rel}: output {out['path']} edited after the run (sha mismatch)")
    return _result("run_records", problems)


def gate_backlog(ctx: Context) -> GateResult:
    try:
        bl = backlog_mod.load_backlog(ctx.root / "autonomy" / "backlog.yaml")
    except ValidationError as exc:
        return GateResult("backlog", "FAIL", [str(exc)])
    return _result("backlog", backlog_mod.problems(bl, ctx.root))


def gate_verification_reports(ctx: Context) -> GateResult:
    try:
        reports = load_reports(ctx.root / "autonomy" / "verifications")
    except ValidationError as exc:
        return GateResult("verification_reports", "FAIL", [str(exc)])
    problems = []
    for p, meta in reports:
        if meta.verdict == "PASS" and meta.blocking_findings:
            problems.append(f"{p.name}: PASS with {meta.blocking_findings} blocking finding(s)")
        if meta.verdict == "PASS" and any(v == "FAIL" for v in meta.gates.values()):
            problems.append(f"{p.name}: PASS although a gate failed")
    return _result("verification_reports", problems)


def gate_hub_summary(ctx: Context) -> GateResult:
    path = ctx.root / "results" / "hub" / "summary.json"
    if not path.exists():
        return GateResult("hub_summary", "FAIL", ["results/hub/summary.json missing: make hub"])
    current = json.loads(path.read_text(encoding="utf-8"))
    expected = hub.build_summary(ctx.root)
    if hub.stable(current) != hub.stable(expected):
        return GateResult("hub_summary", "FAIL", ["summary.json is stale: run `make hub`"])
    return GateResult("hub_summary", "PASS")


def gate_paper(ctx: Context) -> GateResult:
    src = ctx.root / "paper" / "manuscript.md"
    if not src.exists():
        return GateResult("paper", "SKIP", ["no manuscript yet"])
    _, problems = paper.render(src, ctx.root)
    return _result("paper", problems)


def gate_research(ctx: Context) -> GateResult:
    try:
        return _result("research", research.problems(ctx.root))
    except ValidationError as exc:
        return GateResult("research", "FAIL", [str(exc)])


GATES: list[Callable[[Context], GateResult]] = [
    gate_manifests,
    gate_data_integrity,
    gate_repo_hygiene,
    gate_claims,
    gate_preregistration,
    gate_run_records,
    gate_backlog,
    gate_research,
    gate_verification_reports,
    gate_hub_summary,
    gate_paper,
]


def run_all(root: Path, require_data: bool = False) -> list[GateResult]:
    ctx = Context(root=root, require_data=require_data)
    results = []
    for gate in GATES:
        try:
            results.append(gate(ctx))
        except Exception as exc:  # a crashing gate is a failing gate, never a skipped one
            results.append(GateResult(gate.__name__.removeprefix("gate_"), "FAIL", [repr(exc)]))
    return results
