"""Research memory and arbitration: the rules that make the bibliography and the
choice of leads auditable."""

import pytest
import yaml
from pydantic import ValidationError

from frda import literature, research
from frda.backlog import Backlog, pick_next

CARD = """---
paper: MED:111
read_date: 2026-10-20
read_by: L-004
source_text: abstract_only
question: q
model_system: fibroblasts
independent_units: 3 vs 3 donors
methods: RNA-seq
findings:
  - statement: FXN is lower.
    quote: "Frataxin transcript levels were markedly reduced in patient cells."
    location: Abstract
limitations: [small n]
---
notes
"""


def paper(pid="MED:111", **over):
    p = dict(
        id=pid,
        title="A paper",
        kind="primary",
        open_access=False,
        added="2026-10-20",
        added_by="L-002",
        status="to_screen",
    )
    p.update(over)
    return p


def write(root, corpus=None, ideas=None, cards=None, synth=None, decisions=None):
    r = root / "research"
    (r / "cards").mkdir(parents=True, exist_ok=True)
    (r / "synthesis").mkdir(exist_ok=True)
    (r / "decisions").mkdir(exist_ok=True)
    (r / "corpus.yaml").write_text(yaml.safe_dump({"papers": corpus or []}))
    (r / "ideas.yaml").write_text(yaml.safe_dump({"ideas": ideas or []}))
    for name, text in (cards or {}).items():
        (r / "cards" / name).write_text(text)
    if synth:
        (r / "synthesis" / "s.md").write_text(synth)
    for name, text in (decisions or {}).items():
        (r / "decisions" / name).write_text(text)


def test_read_paper_needs_card_and_screen_reason():
    with pytest.raises(ValidationError):
        research.Paper.model_validate(paper(status="read", screen_reason="core"))
    with pytest.raises(ValidationError):
        research.Paper.model_validate(paper(status="excluded"))


def test_cross_references(tmp_path):
    write(
        tmp_path,
        corpus=[paper(status="read", screen_reason="RQ1", card="research/cards/MED_111.md")],
        cards={"MED_111.md": CARD},
        synth="FXN is reduced [@MED:111]. Unknown claim [@MED:999].",
    )
    probs = research.problems(tmp_path)
    assert any("MED:999, not in corpus" in p for p in probs)
    assert not any("MED:111" in p for p in probs)


def test_citing_an_unread_paper_fails(tmp_path):
    write(tmp_path, corpus=[paper(status="to_read", screen_reason="RQ1")], synth="x [@MED:111].")
    assert any("has not been read" in p for p in research.problems(tmp_path))


def test_full_text_claim_on_closed_paper_fails(tmp_path):
    write(
        tmp_path,
        corpus=[paper(status="read", screen_reason="RQ1", card="research/cards/MED_111.md")],
        cards={"MED_111.md": CARD.replace("abstract_only", "full_text")},
    )
    assert any("non open-access" in p for p in research.problems(tmp_path))


def idea(**over):
    i = dict(
        id="I-001",
        title="t",
        question="q",
        rationale="r",
        status="seed",
        created="2026-10-20",
        updated="2026-10-20",
    )
    i.update(over)
    return i


SCORES = {
    "novelty": 4,
    "feasibility": 4,
    "value": 3,
    "cost": 3,
    "risk": 3,
    "rationale": "Grounded in MED:111 and GSE104288 availability.",
}


def test_idea_gates():
    research.Idea.model_validate(idea())
    with pytest.raises(ValidationError):  # candidate without scores / novelty / decision
        research.Idea.model_validate(idea(status="candidate"))
    ok = research.Idea.model_validate(
        idea(
            status="candidate",
            scores=SCORES,
            novelty_check="apparently_new",
            publishable_if="either way",
            decision="RD-002",
        )
    )
    assert ok.scores.priority == pytest.approx(0.3 * 4 + 0.25 * 4 + 0.25 * 3 + 0.1 * 3 + 0.1 * 3)


def test_idea_decision_and_sources_must_exist(tmp_path):
    write(tmp_path, ideas=[idea(status="parked", decision="RD-009", sources=["MED:404"])])
    probs = research.problems(tmp_path)
    assert any("RD-009 not found" in p for p in probs)
    assert any("MED:404 not in corpus" in p for p in probs)


def test_plan_budget_must_sum_to_one(tmp_path):
    write(tmp_path)
    (tmp_path / "research" / "plan.yaml").write_text(
        yaml.safe_dump(
            {
                "current_phase": "A",
                "phases": [{"id": "A"}],
                "budget_bounds": [0.0, 0.8],
                "track_budget": {"literature": 0.9, "main": 0.4},
            }
        )
    )
    probs = research.problems(tmp_path)
    assert any("sums to" in p for p in probs) and any("outside bounds" in p for p in probs)


def _bl(tasks):
    base = dict(
        title="t",
        milestone="M",
        status="ready",
        priority=1,
        kind="data",
        goal="g",
        acceptance=["a"],
    )
    return Backlog.model_validate(
        {
            "version": 1,
            "milestones": [{"id": "M", "title": "m", "goal": "g", "exit_criteria": ["x"]}],
            "tasks": [{**base, **t} for t in tasks],
        }
    )


def test_pick_next_follows_the_track_most_behind_budget():
    bl = _bl(
        [{"id": "T-010", "track": "main"}, {"id": "L-001", "track": "literature", "priority": 5}]
    )
    budget = {"literature": 0.6, "main": 0.4}
    task, why = pick_next(bl, budget=budget, recent_tracks=["main", "main", "literature"])
    assert task.id == "L-001" and "literature" in why
    task, _ = pick_next(bl, budget=budget, recent_tracks=["literature"] * 4)
    assert task.id == "T-010"


def test_pick_next_skips_tracks_with_nothing_ready_and_fix_goes_first():
    bl = _bl([{"id": "T-010", "track": "main"}])
    task, _ = pick_next(bl, budget={"literature": 0.9, "main": 0.1}, recent_tracks=[])
    assert task.id == "T-010"
    bl = _bl(
        [
            {"id": "L-001", "track": "literature"},
            {"id": "FIX-2026-drift", "track": "infra", "priority": 9},
        ]
    )
    assert pick_next(bl, budget={"literature": 1.0}, recent_tracks=[])[0].id == "FIX-2026-drift"


def test_quote_verification_catches_invented_quotes(tmp_path, monkeypatch):
    write(
        tmp_path,
        corpus=[paper(status="read", screen_reason="RQ1", card="research/cards/MED_111.md")],
        cards={"MED_111.md": CARD},
    )
    rec = {
        "title": "A paper",
        "abstractText": "Background. Frataxin transcript levels were markedly   reduced in patient cells.",
    }
    monkeypatch.setattr(literature, "fetch_record", lambda pid: rec)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    assert literature.verify(root=tmp_path) == []
    rec["abstractText"] = "Frataxin levels were unchanged."
    assert any("not found verbatim" in p for p in literature.verify(root=tmp_path))
    monkeypatch.setattr(literature, "fetch_record", lambda pid: None)
    assert any("does not exist" in p for p in literature.verify(root=tmp_path))


def test_seed_research_memory_is_valid():
    assert research.problems() == []


# --- regression tests for the T-021 verification findings -------------------------------


def test_verify_fails_on_unknown_ids_and_empty_target(tmp_path, monkeypatch):
    write(tmp_path)
    monkeypatch.setattr(literature, "fetch_record", lambda pid: {"title": "x"})
    assert any("not in the corpus" in p for p in literature.verify(["MED:99999999"], root=tmp_path))
    assert any("no paper to verify" in p for p in literature.verify(root=tmp_path))


def test_degenerate_quotes_are_rejected():
    with pytest.raises(ValidationError):
        research.Finding(statement="s", quote='"......................."', location="Abstract")
    assert not literature.quote_is_substantive(". . . . . . . . . . . . . . .")


def test_full_text_card_requires_the_papers_own_pmcid(tmp_path, monkeypatch):
    write(
        tmp_path,
        corpus=[
            paper(
                status="read",
                screen_reason="RQ1",
                card="research/cards/MED_111.md",
                open_access=True,
                pmcid="PMC999",
            )
        ],
        cards={"MED_111.md": CARD.replace("abstract_only", "full_text")},
    )
    monkeypatch.setattr(
        literature, "fetch_record", lambda pid: {"title": "A paper", "pmcid": "PMC111"}
    )
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    probs = literature.verify(root=tmp_path)
    assert any("pmcid" in p for p in probs)


def test_full_text_search_is_limited_to_the_article_body(monkeypatch):
    xml = (
        "<article><front>Frataxin transcript levels were markedly reduced in patient cells."
        "</front><body><p>Nothing relevant here at all.</p></body>"
        "<back><ref>Another quote from a cited paper title in references.</ref></back></article>"
    )
    monkeypatch.setattr(literature, "_get", lambda url, as_json=True: xml)
    body = literature.full_text("PMC1")
    assert "Nothing relevant" in body and "Frataxin" not in body and "cited paper" not in body


def test_zero_budget_track_never_beats_a_funded_one():
    bl = _bl(
        [
            {"id": "T-010", "track": "main", "priority": 5},
            {"id": "T-099", "track": "exploration", "priority": 1},
        ]
    )
    budget = {"literature": 0.6, "main": 0.4, "exploration": 0.0}
    for recent in ([], ["main"] * 10, ["main", "literature"]):
        assert pick_next(bl, budget=budget, recent_tracks=recent)[0].id == "T-010"
    only_unfunded = _bl([{"id": "T-099", "track": "exploration"}])
    task, why = pick_next(only_unfunded, budget=budget, recent_tracks=[])
    assert task.id == "T-099" and "no budgeted track" in why


def test_pick_next_is_deterministic_on_ties():
    bl = _bl([{"id": "T-010", "track": "main"}, {"id": "L-001", "track": "literature"}])
    budget = {"literature": 0.5, "main": 0.5}
    picks = {pick_next(bl, budget=budget, recent_tracks=[])[0].id for _ in range(20)}
    assert picks == {"L-001"}  # tie on deficit and priority -> track name order


def _pass_report(root, task, date):
    d = root / "autonomy" / "verifications"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{task}-abcdef1.md").write_text(
        f"---\ntask: {task}\nreviewed_sha: abcdef1\nverdict: PASS\ndate: '{date}'\nattempt: 1\n"
        "summary: s\ngates: {lint: PASS, test: PASS, verify: PASS, reproduce: PASS}\n"
        "acceptance_met: 1/1\nblocking_findings: 0\n---\n"
    )


def test_recent_tracks_window(tmp_path):
    from frda.backlog import recent_tracks

    bl = _bl(
        [
            {"id": "T-001", "track": "main", "status": "done"},
            {"id": "L-001", "track": "literature", "status": "done"},
        ]
    )
    _pass_report(tmp_path, "T-001", "2026-10-16")
    _pass_report(tmp_path, "L-001", "2026-10-17")
    assert recent_tracks(bl, tmp_path, window=10) == ["main", "literature"]
    assert recent_tracks(bl, tmp_path, window=1) == ["literature"]
    assert recent_tracks(bl, tmp_path, window=0) == []  # fails if the guard is removed
    assert recent_tracks(bl, tmp_path, window=True) == []


def test_unbudgeted_tracks_do_not_dilute_shares():
    bl = _bl([{"id": "T-010", "track": "main"}, {"id": "L-002", "track": "literature"}])
    budget = {"literature": 0.5, "main": 0.5}
    # 1 main + many infra: among budgeted work, main is 100 % and literature 0 % -> literature.
    task, _ = pick_next(bl, budget=budget, recent_tracks=["main"] + ["infra"] * 9)
    assert task.id == "L-002"


def test_bracketed_invented_span_fails(tmp_path, monkeypatch):
    card = CARD.replace(
        "Frataxin transcript levels were markedly reduced in patient cells.",
        "Frataxin transcript levels <we proved causation in all patients> were markedly reduced "
        "in patient cells.",
    )
    write(
        tmp_path,
        corpus=[paper(status="read", screen_reason="RQ1", card="research/cards/MED_111.md")],
        cards={"MED_111.md": card},
    )
    rec = {
        "title": "A paper",
        "abstractText": "Frataxin transcript levels were markedly reduced in patient cells.",
    }
    monkeypatch.setattr(literature, "fetch_record", lambda pid: rec)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    probs = literature.verify(root=tmp_path)
    assert probs and all("MED_111" in p for p in probs)


def test_literal_angle_brackets_in_source_are_kept():
    xml = "<body><p>Expression differed (p &lt; 0.05 and q &gt; 0.1) in <italic>FXN</italic>.</p></body>"
    text = literature.normalise(literature.markup_to_text(xml))
    assert "(p < 0.05 and q > 0.1) in fxn." in text
    # malformed XML fallback still keeps prose comparisons
    assert "p < 0.05 and q > 0.1" in literature.markup_to_text("<p>p < 0.05 and q > 0.1</p><br>")


def test_search_logs_are_never_overwritten(tmp_path):
    log = {"date": "2026-10-20", "query": "q", "hit_count": 0, "retrieved": 0, "results": []}
    a = literature.save_search_log(log, "RQ1 / test", "L-002", root=tmp_path)
    b = literature.save_search_log(log, "RQ1 / test", "L-002", root=tmp_path)
    assert a != b and a.name == "2026-10-20-rq1-test.json" and b.exists()


def test_plan_window_floor_and_pivot_checks(tmp_path):
    write(
        tmp_path,
        decisions={
            "RD-002.md": "---\nid: RD-002\ndate: 2026-10-20\nkind: pivot\n"
            "summary: switch to Parkinson\nneeds_human: false\n---\n"
        },
    )
    (tmp_path / "research" / "plan.yaml").write_text(
        yaml.safe_dump(
            {
                "current_phase": "A",
                "phases": [{"id": "A"}],
                "budget_window": 0,
                "track_floor": {"main": 0.2},
                "track_budget": {"literature": 0.9, "main": 0.1},
            }
        )
    )
    probs = " | ".join(research.problems(tmp_path))
    assert "budget_window" in probs and "below its floor" in probs and "pivot" in probs
