import json

import yaml

from frda import paper
from frda.hashing import sha256_file
from frda.provenance import write_json


def setup_claim(root, verified=True):
    (root / "results/P-4").mkdir(parents=True)
    write_json(root / "results/P-4/a.json", {"fxn": {"log2_fc": -1.23456}})
    (root / "evaluation").mkdir(exist_ok=True)
    c = dict(
        id="C-004",
        statement="s",
        status="reproduced",
        evidence_level="single_dataset",
        datasets=["GSE104288"],
        task="T-004",
        artifact="results/P-4/a.json",
        checks=[{"pointer": "/fxn/log2_fc", "op": "lt", "value": 0}],
        limitations=["l"],
        source={"pmid": "1", "location": "F1", "published_value": "v"},
        verified_by="autonomy/verifications/T-004-abc.md" if verified else None,
    )
    (root / "evaluation/claims.yaml").write_text(yaml.safe_dump({"claims": [c]}))


def test_render_tokens_and_citations(tmp_path):
    setup_claim(tmp_path)
    src = tmp_path / "m.md"
    src.write_text("FXN log2FC was {{C-004:/fxn/log2_fc:.2f}} [C-004].")
    text, problems = paper.render(src, tmp_path)
    assert text == "FXN log2FC was -1.23 [C-004]."
    assert problems == []


def test_render_flags_unverified_and_hand_typed(tmp_path):
    setup_claim(tmp_path, verified=False)
    src = tmp_path / "m.md"
    src.write_text("Strong effect (p < 0.001) [C-004] and {{C-999:/x}}.")
    _, problems = paper.render(src, tmp_path)
    joined = " | ".join(problems)
    assert "not passed verification" in joined
    assert "hand-typed" in joined
    assert "unknown claim C-999" in joined


def test_write_json_is_deterministic(tmp_path):
    write_json(tmp_path / "a.json", {"b": 1.0 / 3, "a": [2.0 / 3]})
    first = sha256_file(tmp_path / "a.json")
    write_json(tmp_path / "a.json", {"a": [0.6666666666666667], "b": 0.3333333333333333})
    assert sha256_file(tmp_path / "a.json") == first
    assert json.loads((tmp_path / "a.json").read_text())["b"] == 0.333333
