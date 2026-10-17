from frda.backlog import Backlog, load_backlog, problems


def test_seed_backlog_valid():
    bl = load_backlog()
    assert problems(bl) == []
    done = {t.id for t in bl.tasks if t.status == "done"}
    eligible = [t for t in bl.tasks if t.status == "ready" and set(t.depends_on) <= done]
    first = bl.next_ready()
    assert first is not None
    assert first.id == min(eligible, key=lambda t: (t.priority, t.id)).id


def test_next_ready_respects_dependencies_and_exclusions():
    bl = load_backlog()
    done = {t.id for t in bl.tasks if t.status == "done"}
    first = bl.next_ready()
    assert first is not None
    nxt = bl.next_ready(exclude={first.id})
    assert nxt is not None
    assert nxt.id != first.id and nxt.status == "ready" and set(nxt.depends_on) <= done
    blocked = [t for t in bl.tasks if t.status == "ready" and not set(t.depends_on) <= done]
    assert blocked, "seed backlog should contain tasks waiting on dependencies"
    excluded_all = {t.id for t in bl.tasks if set(t.depends_on) <= done}
    assert bl.next_ready(exclude=excluded_all) is None  # never picks a task with open deps


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
