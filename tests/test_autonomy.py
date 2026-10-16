"""The branch protocol, exercised against a real bare remote."""

import subprocess
import sys
from pathlib import Path

from frda.autonomy import status

from .conftest import git

REPO = Path(__file__).resolve().parents[1]


def clone_with_remote(sandbox: Path, tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(sandbox, "remote", "add", "origin", str(remote))
    git(sandbox, "push", "-q", "origin", "main")
    git(sandbox, "fetch", "-q", "origin")
    return remote


def commit(root: Path, msg: str, name: str = "f.txt"):
    (root / name).write_text(msg)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg)


def test_protocol_states(sandbox, tmp_path):
    clone_with_remote(sandbox, tmp_path)
    st = status(sandbox)
    assert st["next_for_worker"]["action"] == "start_task"
    assert st["next_for_verifier"] is None

    git(sandbox, "checkout", "-q", "-b", "auto/T-001")
    commit(sandbox, "work(T-001): done")
    git(sandbox, "push", "-q", "origin", "auto/T-001")
    git(sandbox, "fetch", "-q", "origin")
    st = status(sandbox)
    assert st["next_for_verifier"]["task"] == "T-001"
    assert st["next_for_worker"] is None  # WIP limit 1 reached

    commit(sandbox, "verify(T-001): CHANGES_REQUESTED — 2 blocking", "g.txt")
    git(sandbox, "push", "-q", "origin", "auto/T-001")
    git(sandbox, "fetch", "-q", "origin")
    st = status(sandbox)
    assert st["next_for_worker"] == {
        "action": "address_changes",
        "task": "T-001",
        "branch": "auto/T-001",
    }
    assert st["next_for_verifier"] is None

    commit(sandbox, "work(T-001): fixed", "h.txt")
    commit(sandbox, "verify(T-001): PASS — ok", "i.txt")
    git(sandbox, "push", "-q", "origin", "HEAD:refs/heads/verified/T-001")
    git(sandbox, "fetch", "-q", "origin")
    st = status(sandbox)
    assert "verified/T-001" in st["landing_pending"]
    assert st["next_for_verifier"] is None


def test_landing_guard_accepts_only_bookkeeping(sandbox, tmp_path):
    git(sandbox, "checkout", "-q", "-b", "work")
    commit(sandbox, "work(T-001): handover")
    reviewed = git(sandbox, "rev-parse", "HEAD")
    rep = sandbox / "autonomy/verifications" / f"T-001-{reviewed[:7]}.md"
    rep.write_text(
        f"---\ntask: T-001\nreviewed_sha: {reviewed}\nverdict: PASS\ndate: '2026-10-17'\n"
        "attempt: 1\nsummary: ok\ngates: {lint: PASS, test: PASS, verify: PASS, reproduce: PASS}\n"
        "acceptance_met: 4/4\nblocking_findings: 0\n---\nbody\n"
    )
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "verify(T-001): PASS — ok")
    guard = [sys.executable, str(REPO / "scripts/check_verified_branch.py"), "verified/T-001"]
    assert subprocess.run(guard, cwd=sandbox).returncode == 0

    # Same, but the verify commit also sneaks a code change in: refused.
    git(sandbox, "reset", "-q", "--soft", "HEAD~1")
    (sandbox / "pipelines" / "evil.py").write_text("x = 1\n")
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "verify(T-001): PASS — ok")
    assert subprocess.run(guard, cwd=sandbox, capture_output=True).returncode == 1
