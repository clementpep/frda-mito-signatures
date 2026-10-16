"""Research backlog (autonomy/backlog.yaml): the queue the worker routine
pulls from. Status transitions are made by routines on branches; `main` only
ever holds states that passed verification."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from frda import paths
from frda.yamlio import load_yaml

TaskStatus = Literal[
    "proposed",  # suggested by the watch routine, not yet accepted by the verifier
    "ready",
    "in_review",
    "changes_requested",
    "done",
    "blocked",
    "needs_human",
]
TaskKind = Literal[
    "data",
    "qc",
    "reproduction",
    "analysis",
    "evidence",
    "literature",
    "supervision",
    "paper",
    "infra",
    "human",
]
# Effort tracks arbitrated by research/plan.yaml (track_budget). A thesis is not one queue:
# reading, the main line of analysis, exploration of leads and writing compete for time.
Track = Literal["literature", "main", "exploration", "writing", "infra"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Milestone(Strict):
    id: str
    title: str
    goal: str
    exit_criteria: list[str] = Field(min_length=1)


class Task(Strict):
    id: str = Field(pattern=r"^(T|L|W|R|FIX)-[0-9A-Za-z-]+$")
    title: str
    milestone: str
    status: TaskStatus
    priority: int = Field(ge=1, le=9, description="1 = most urgent")
    kind: TaskKind
    track: Track = "main"
    idea: str | None = Field(default=None, description="I-xxx this task serves, if any")
    depends_on: list[str] = Field(default_factory=list)
    goal: str
    acceptance: list[str] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)
    attempts: int = 0
    verification: str | None = None


class Backlog(Strict):
    version: int
    milestones: list[Milestone]
    tasks: list[Task]

    def task(self, task_id: str) -> Task:
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(task_id)

    def next_ready(self, exclude: set[str] | None = None) -> Task | None:
        exclude = exclude or set()
        done = {t.id for t in self.tasks if t.status == "done"}
        candidates = [
            t
            for t in self.tasks
            if t.status == "ready" and t.id not in exclude and set(t.depends_on) <= done
        ]
        candidates.sort(key=lambda t: (t.priority, t.id))
        return candidates[0] if candidates else None


def pick_next(
    backlog: Backlog,
    *,
    exclude: set[str] | None = None,
    budget: dict[str, float] | None = None,
    recent_tracks: list[str] | None = None,
) -> tuple[Task | None, str]:
    """Choose the next task. Returns (task, reason).

    Among ready tasks whose dependencies are done, take the track furthest below
    its budget share over the recent window of finished tasks, then the most
    urgent task of that track. Tracks with nothing ready are skipped, so effort
    flows to what can actually be done. Without a budget: plain priority order.
    """
    exclude = exclude or set()
    done = {t.id for t in backlog.tasks if t.status == "done"}
    ready = [
        t
        for t in backlog.tasks
        if t.status == "ready" and t.id not in exclude and set(t.depends_on) <= done
    ]
    if not ready:
        return None, "no ready task with satisfied dependencies"
    ready.sort(key=lambda t: (t.priority, t.id))
    fixes = [t for t in ready if t.id.startswith("FIX-")]
    if fixes:
        return fixes[0], "FIX tasks (data drift, broken main) go before any budget"
    if not budget:
        return ready[0], "priority order (no track budget)"
    recent = recent_tracks or []
    n = len(recent)
    share = {tr: (recent.count(tr) / n if n else 0.0) for tr in budget}
    tracks = {t.track for t in ready}
    # Tracks absent from the budget still run (e.g. infra fixes) but only after budgeted ones.
    scored = sorted(
        tracks,
        key=lambda tr: (
            -(budget.get(tr, -1.0) - share.get(tr, 0.0)),
            min(t.priority for t in ready if t.track == tr),
        ),
    )
    chosen = scored[0]
    task = next(t for t in ready if t.track == chosen)
    deficits = ", ".join(
        f"{tr} {budget[tr]:.0%} target / {share[tr]:.0%} done" for tr in sorted(budget)
    )
    return task, f"track {chosen} most behind its budget over last {n} tasks ({deficits})"


def recent_tracks(backlog: Backlog, root: Path | None = None, window: int = 10) -> list[str]:
    """Tracks of the last `window` finished tasks, ordered by verification date."""
    from frda.reports import load_reports

    root = root or paths.ROOT
    dates = {
        m.task: m.date
        for _, m in load_reports(root / "autonomy" / "verifications")
        if m.verdict == "PASS"
    }
    done = [t for t in backlog.tasks if t.status == "done" and t.id in dates]
    done.sort(key=lambda t: (dates[t.id], t.id))
    return [t.track for t in done[-window:]]


def load_backlog(path: Path | None = None) -> Backlog:
    return Backlog.model_validate(load_yaml(path or paths.BACKLOG))


def problems(backlog: Backlog, root: Path | None = None) -> list[str]:
    root = root or paths.ROOT
    out: list[str] = []
    ids = [t.id for t in backlog.tasks]
    dupes = {i for i in ids if ids.count(i) > 1}
    out += [f"duplicate task id {d}" for d in sorted(dupes)]
    milestones = {m.id for m in backlog.milestones}
    known = set(ids)
    for t in backlog.tasks:
        if t.milestone not in milestones:
            out.append(f"{t.id}: unknown milestone {t.milestone}")
        for d in t.depends_on:
            if d not in known:
                out.append(f"{t.id}: depends on unknown task {d}")
        if t.status == "done":
            if not t.verification:
                out.append(f"{t.id}: done without a verification report")
            elif not (root / t.verification).exists():
                out.append(f"{t.id}: verification report {t.verification} missing")
    # cycle detection
    graph = {t.id: set(t.depends_on) for t in backlog.tasks}
    state: dict[str, int] = {}

    def visit(n: str, stack: list[str]) -> None:
        if state.get(n) == 1:
            out.append("dependency cycle: " + " -> ".join([*stack, n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in graph.get(n, ()):
            visit(m, [*stack, n])
        state[n] = 2

    for n in graph:
        visit(n, [])
    return out
