"""Claims ledger (evaluation/claims.yaml).

A claim is the only way a scientific statement enters this project: the
evidence dossier, the hub and the manuscript are all rendered from it. Each
claim points to a JSON artifact and carries machine-checkable assertions, so
the verification gates re-evaluate every claim on every run.

Status vocabulary — what an FRDA researcher needs to tell apart:
  reproduced        a published result we re-derived (source + location required)
  refuted           a published result we failed to re-derive (same)
  new               a result not found in the literature we checked
  not_demonstrated  something tested that did not hold, or remains untestable here
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from frda import paths
from frda.yamlio import load_yaml

Status = Literal["reproduced", "refuted", "new", "not_demonstrated"]
EvidenceLevel = Literal["exploratory", "single_dataset", "replicated", "preregistered_confirmed"]
Op = Literal["lt", "le", "gt", "ge", "eq", "approx", "between"]

# Wording that would turn an expression result into a clinical or causal claim.
FORBIDDEN_WORDING = [
    r"\bcures?\b",
    r"\bheals?\b",
    r"\btherapeutic (?:benefit|efficacy)\b",
    r"\bproves?\b",
    r"\bcauses?\b",
    r"\bcausal(?:ly)?\b",
    r"\btreatment for\b",
    r"\bclinically (?:effective|relevant)\b",
    r"\bdrug candidate\b",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Strict):
    pmid: str | None = None
    doi: str | None = None
    location: str = Field(description="Figure / table / page where the published value is.")
    published_value: str = Field(description="The value as published, verbatim.")


class Check(Strict):
    pointer: str = Field(description="JSON pointer into the artifact, e.g. /fxn/log2_fc")
    op: Op
    value: float | list[float]
    tolerance: float | None = None


class Claim(Strict):
    id: str = Field(pattern=r"^C-\d{3}$")
    statement: str
    status: Status
    evidence_level: EvidenceLevel
    datasets: list[str] = Field(min_length=1)
    task: str
    artifact: str
    checks: list[Check] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    source: Source | None = None
    novelty_check: str | None = Field(
        default=None, description="For status=new: path to the literature-search log."
    )
    verified_by: str | None = None

    @model_validator(mode="after")
    def status_requirements(self) -> Claim:
        if self.status in {"reproduced", "refuted"} and self.source is None:
            raise ValueError(f"{self.id}: {self.status} claims need a published source")
        if self.status == "new" and not self.novelty_check:
            raise ValueError(f"{self.id}: a 'new' claim needs a novelty_check log")
        return self


class Ledger(Strict):
    claims: list[Claim] = Field(default_factory=list)


def load_ledger(path: Path | None = None) -> Ledger:
    data = load_yaml(path or paths.CLAIMS) or {}
    return Ledger.model_validate(data)


def resolve_pointer(doc: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return doc
    cur = doc
    for raw in pointer.lstrip("/").split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def evaluate_check(actual: float, check: Check) -> bool:
    v = check.value
    if check.op == "between":
        if not isinstance(v, list) or len(v) != 2:
            raise ValueError("between needs [low, high]")
        return v[0] <= actual <= v[1]
    if isinstance(v, list):
        raise ValueError(f"op {check.op} needs a scalar value")
    if check.op == "approx":
        tol = check.tolerance if check.tolerance is not None else 1e-6
        return math.isclose(actual, v, rel_tol=tol, abs_tol=tol)
    return {
        "lt": actual < v,
        "le": actual <= v,
        "gt": actual > v,
        "ge": actual >= v,
        "eq": actual == v,
    }[check.op]


def check_claim(claim: Claim, root: Path | None = None) -> list[str]:
    """Problems with one claim (empty = OK)."""
    root = root or paths.ROOT
    problems: list[str] = []
    artifact = root / claim.artifact
    if not artifact.exists():
        return [f"{claim.id}: artifact {claim.artifact} missing"]
    try:
        doc = json.loads(artifact.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{claim.id}: artifact is not valid JSON ({exc})"]
    for chk in claim.checks:
        try:
            actual = resolve_pointer(doc, chk.pointer)
        except (KeyError, IndexError, ValueError):
            problems.append(f"{claim.id}: pointer {chk.pointer} not found in artifact")
            continue
        if not isinstance(actual, int | float) or isinstance(actual, bool):
            problems.append(f"{claim.id}: {chk.pointer} is not numeric ({actual!r})")
            continue
        if not evaluate_check(float(actual), chk):
            problems.append(
                f"{claim.id}: check {chk.pointer} {chk.op} {chk.value} failed ({actual})"
            )
    for pattern in FORBIDDEN_WORDING:
        if re.search(pattern, claim.statement, flags=re.IGNORECASE):
            problems.append(f"{claim.id}: statement uses forbidden wording /{pattern}/")
    if claim.novelty_check and not (root / claim.novelty_check).exists():
        problems.append(f"{claim.id}: novelty_check {claim.novelty_check} missing")
    if claim.verified_by and not (root / claim.verified_by).exists():
        problems.append(f"{claim.id}: verified_by {claim.verified_by} missing")
    return problems
