from frda.backlog import Backlog, load_backlog, problems


def test_seed_backlog_valid():
    bl = load_backlog()
    assert problems(bl) == []
    first = bl.next_ready()
    assert first is not None and first.id in {"T-001", "T-003", "T-006"}


def test_next_ready_respects_dependencies_and_exclusions():
    bl = load_backlog()
    ids_ready_now = {t.id for t in bl.tasks if t.status == "ready" and not t.depends_on}
    nxt = bl.next_ready(exclude={"T-001"})
    assert nxt is not None and nxt.id in ids_ready_now and nxt.id != "T-001"


def _mini(tasks):
    return Backlog.model_validate(
        {
            "version": 1,
            "milestones": [{"id": "M1", "title": "m", "goal": "g", "exit_criteria": ["x"]}],
            "tasks": tasks,
        }
    )


def _task(tid, **over):
    t = dict(
        id=tid,
        title="t",
        milestone="M1",
        status="ready",
        priority=1,
        kind="data",
        goal="g",
        acceptance=["a"],
    )
    t.update(over)
    return t


def test_cycle_detected(tmp_path):
    bl = _mini([_task("T-001", depends_on=["T-002"]), _task("T-002", depends_on=["T-001"])])
    assert any("cycle" in p for p in problems(bl, tmp_path))


def test_done_requires_existing_verification(tmp_path):
    bl = _mini([_task("T-001", status="done", verification="autonomy/verifications/x.md")])
    assert any("missing" in p for p in problems(bl, tmp_path))
