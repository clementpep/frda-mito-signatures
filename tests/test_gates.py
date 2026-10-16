"""The gates are the project's contract with itself: these tests pin their
behaviour so that weakening one shows up as a failing test in review."""

import json
from pathlib import Path

import yaml

from frda import gates, hub
from frda.gates import Context
from frda.hashing import sha256_file
from frda.provenance import write_json

from .conftest import git


def add_run(root: Path, name: str, units: dict, kind: str = "exploratory", prereg=None):
    d = root / "results" / name
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "a.json", {"x": {"v": -1.0}})
    run = {
        "pipeline": name,
        "task": "T-004",
        "code_sha": "abc",
        "inputs": [],
        "params": {},
        "environment": {},
        "independent_units": units,
        "analysis_kind": kind,
        "preregistration": prereg,
        "outputs": [{"path": "a.json", "sha256": sha256_file(d / "a.json")}],
    }
    (d / "run.json").write_text(json.dumps(run))
    return f"results/{name}/a.json"


def set_claims(root: Path, claims: list[dict]):
    (root / "evaluation" / "claims.yaml").write_text(yaml.safe_dump({"claims": claims}))


def claim(cid, artifact, **over):
    c = dict(
        id=cid,
        statement="FXN is lower in FRDA fibroblasts.",
        status="reproduced",
        evidence_level="single_dataset",
        datasets=["GSE104288"],
        task="T-004",
        artifact=artifact,
        checks=[{"pointer": "/x/v", "op": "lt", "value": 0}],
        limitations=["l"],
        source={"pmid": "1", "location": "Fig 1", "published_value": "v"},
    )
    c.update(over)
    return c


def test_seed_repository_passes_all_gates_without_data():
    results = gates.run_all(Path(__file__).resolve().parents[1])
    failed = {r.name: r.details for r in results if r.status == "FAIL"}
    assert failed == {}


def test_new_claim_before_reproduction_fails(sandbox):
    art = add_run(sandbox, "P-010", {"FRDA": 18, "control": 17})
    (sandbox / "docs").mkdir()
    (sandbox / "docs" / "nov.json").write_text("{}")
    set_claims(
        sandbox, [claim("C-001", art, status="new", source=None, novelty_check="docs/nov.json")]
    )
    r = gates.gate_claims(Context(sandbox))
    assert r.status == "FAIL" and any("before any verified reproduction" in d for d in r.details)


def test_low_independent_units_must_be_exploratory(sandbox):
    art = add_run(sandbox, "P-005", {"FRDA_DMSO": 1, "FRDA_A196_high": 1})
    set_claims(sandbox, [claim("C-002", art, evidence_level="single_dataset")])
    r = gates.gate_claims(Context(sandbox))
    assert r.status == "FAIL" and any("exploratory" in d for d in r.details)
    set_claims(sandbox, [claim("C-002", art, evidence_level="exploratory")])
    assert gates.gate_claims(Context(sandbox)).status == "PASS"


def test_edited_output_detected(sandbox):
    add_run(sandbox, "P-004", {"FRDA": 18, "control": 17})
    (sandbox / "results/P-004/a.json").write_text('{"x": {"v": -99}}')
    r = gates.gate_run_records(Context(sandbox))
    assert r.status == "FAIL" and "edited after the run" in r.details[0]


PREREG = """---
id: PR-001
task: T-011
title: t
hypotheses: [h]
primary_outcome: o
expected_direction: down
analysis_plan: p
decision_rule: r
created: 2026-10-20
---
body
"""


def test_preregistration_must_precede_confirmatory_results(sandbox):
    pr = sandbox / "preregistrations" / "PR-001-x.md"
    pr.parent.mkdir()
    pr.write_text(PREREG)
    add_run(
        sandbox,
        "P-012",
        {"a": 5, "b": 5},
        kind="confirmatory",
        prereg="preregistrations/PR-001-x.md",
    )
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "prereg and results together")
    r = gates.gate_preregistration(Context(sandbox))
    assert r.status == "FAIL"


def test_preregistration_ok_when_committed_first(sandbox):
    pr = sandbox / "preregistrations" / "PR-001-x.md"
    pr.parent.mkdir()
    pr.write_text(PREREG)
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "prereg")
    add_run(
        sandbox,
        "P-012",
        {"a": 5, "b": 5},
        kind="confirmatory",
        prereg="preregistrations/PR-001-x.md",
    )
    git(sandbox, "add", "-A")
    git(sandbox, "commit", "-q", "-m", "results")
    assert gates.gate_preregistration(Context(sandbox)).status == "PASS"
    pr.write_text(PREREG.replace("down", "up"))
    git(sandbox, "commit", "-q", "-am", "edit prereg after results")
    assert gates.gate_preregistration(Context(sandbox)).status == "FAIL"


def test_stale_hub_summary_detected(sandbox):
    assert gates.gate_hub_summary(Context(sandbox)).status == "PASS"
    bl = yaml.safe_load((sandbox / "autonomy/backlog.yaml").read_text())
    bl["tasks"][0]["status"] = "blocked"
    (sandbox / "autonomy/backlog.yaml").write_text(yaml.safe_dump(bl, sort_keys=False))
    assert gates.gate_hub_summary(Context(sandbox)).status == "FAIL"
    summary = hub.build_summary(sandbox)
    assert summary["progress"]["blocked"] == 1


def test_pass_report_with_blocking_findings_rejected(sandbox):
    d = sandbox / "autonomy" / "verifications"
    (d / "T-001-abcdef1.md").write_text(
        "---\ntask: T-001\nreviewed_sha: abcdef1\nverdict: PASS\ndate: '2026-10-17'\nattempt: 1\n"
        "summary: s\ngates: {lint: PASS, test: PASS, verify: PASS, reproduce: PASS}\n"
        "acceptance_met: 4/4\nblocking_findings: 2\n---\nbody\n"
    )
    assert gates.gate_verification_reports(Context(sandbox)).status == "FAIL"


def test_data_committed_is_rejected(sandbox):
    (sandbox / "data" / "raw").mkdir(parents=True)
    (sandbox / "data" / "raw" / "x.txt").write_text("x")
    git(sandbox, "add", "-f", "data/raw/x.txt")
    assert gates.gate_repo_hygiene(Context(sandbox)).status == "FAIL"
