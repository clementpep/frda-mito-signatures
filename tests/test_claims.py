import json

import pytest
from pydantic import ValidationError

from frda.claims import Check, Claim, check_claim, evaluate_check, resolve_pointer


def make_claim(**over):
    base = dict(
        id="C-001",
        statement="FXN expression is lower in FRDA than in control fibroblasts.",
        status="reproduced",
        evidence_level="single_dataset",
        datasets=["GSE104288"],
        task="T-004",
        artifact="results/P-x/a.json",
        checks=[{"pointer": "/fxn/log2_fc", "op": "lt", "value": 0}],
        limitations=["normalised counts only"],
        source={"pmid": "1", "location": "Fig 1", "published_value": "x"},
    )
    base.update(over)
    return Claim.model_validate(base)


def write_artifact(root, payload):
    p = root / "results" / "P-x"
    p.mkdir(parents=True)
    (p / "a.json").write_text(json.dumps(payload))


def test_pointer_and_ops():
    doc = {"a": {"b": [1.0, 2.5]}}
    assert resolve_pointer(doc, "/a/b/1") == 2.5
    assert evaluate_check(0.5, Check(pointer="/", op="between", value=[0, 1]))
    assert evaluate_check(1.0000001, Check(pointer="/", op="approx", value=1, tolerance=1e-3))
    assert not evaluate_check(1.0, Check(pointer="/", op="lt", value=1))


def test_claim_passes_and_fails_on_artifact(tmp_path):
    write_artifact(tmp_path, {"fxn": {"log2_fc": -1.2}})
    assert check_claim(make_claim(), tmp_path) == []
    (tmp_path / "results/P-x/a.json").write_text(json.dumps({"fxn": {"log2_fc": 0.3}}))
    assert any("failed" in p for p in check_claim(make_claim(), tmp_path))


def test_missing_artifact_is_a_problem(tmp_path):
    assert check_claim(make_claim(), tmp_path)


@pytest.mark.parametrize(
    "word", ["cures", "proves", "causes", "drug candidate", "therapeutic benefit"]
)
def test_forbidden_wording(tmp_path, word):
    write_artifact(tmp_path, {"fxn": {"log2_fc": -1.2}})
    claim = make_claim(statement=f"This signature {word} FRDA.")
    assert any("forbidden wording" in p for p in check_claim(claim, tmp_path))


def test_reproduced_needs_source():
    with pytest.raises(ValidationError):
        make_claim(source=None)


def test_new_needs_novelty_check():
    with pytest.raises(ValidationError):
        make_claim(status="new", source=None)
