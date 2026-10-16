"""Preregistrations (preregistrations/PR-xxx-*.md).

A confirmatory analysis states its hypothesis, primary outcome, expected
direction and decision rule in a file committed BEFORE the analysis runs.
Git history is the timestamp: the gates check that the preregistration's
commit is an ancestor of the commit that introduced the results, and that the
file was never edited afterwards (amendments go in a new file)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from frda import paths
from frda.yamlio import read_front_matter

PREREG_DIR = paths.ROOT / "preregistrations"


class Prereg(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^PR-\d{3}$")
    task: str
    title: str
    hypotheses: list[str] = Field(min_length=1)
    primary_outcome: str
    expected_direction: str
    analysis_plan: str
    decision_rule: str
    created: str

    @field_validator("created", mode="before")
    @classmethod
    def _date_to_str(cls, v: object) -> object:
        # YAML parses unquoted 2026-10-17 as a date; keep the ISO string.
        return v.isoformat() if isinstance(v, dt.date) else v

    amends: str | None = None


def load(path: Path) -> Prereg:
    meta, _ = read_front_matter(path)
    return Prereg.model_validate(meta)


def all_files(directory: Path | None = None) -> list[Path]:
    directory = directory or PREREG_DIR
    return sorted(directory.glob("PR-*.md")) if directory.exists() else []
