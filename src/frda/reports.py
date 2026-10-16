"""Verification reports written by the verifier routine
(autonomy/verifications/<task>-<sha7>.md, YAML front matter + body)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from frda import paths
from frda.yamlio import read_front_matter

Verdict = Literal["PASS", "CHANGES_REQUESTED", "NEEDS_HUMAN"]


class ReportMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    reviewed_sha: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    verdict: Verdict
    date: str

    @field_validator("date", mode="before")
    @classmethod
    def _date_to_str(cls, v: object) -> object:
        # YAML parses unquoted 2026-10-17 as a date; keep the ISO string.
        return v.isoformat() if isinstance(v, dt.date) else v

    attempt: int = Field(ge=1)
    summary: str
    gates: dict[str, Literal["PASS", "FAIL", "WARN", "SKIP"]]
    acceptance_met: str = Field(pattern=r"^\d+/\d+$")
    recomputed: list[str] = Field(
        default_factory=list, description="Numbers independently recomputed by the verifier."
    )
    blocking_findings: int = Field(ge=0)


def load_reports(directory: Path | None = None) -> list[tuple[Path, ReportMeta]]:
    directory = directory or paths.VERIFICATIONS
    out = []
    for p in sorted(directory.glob("*.md")):
        meta, _ = read_front_matter(p)
        out.append((p, ReportMeta.model_validate(meta)))
    return out
