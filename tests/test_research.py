"""Research memory and arbitration: the rules that make the bibliography and the
choice of leads auditable."""

import json
import urllib.parse

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


def test_title_check_ignores_escaped_inline_markup(tmp_path, monkeypatch):
    # FIX-L002a: Europe PMC escapes inline tags (&lt;i&gt;), the corpus stores them unescaped once
    # (paper_from_record). Shapes of MED:40919203, MED:32249386 and MED:42383006.
    cases = [
        (
            "Characterization and immunoprotective efficacy of a fumarate reductase <i>frdA</i> "
            "mutant of <i>Salmonella enteritidis</i>.",
            "Characterization and immunoprotective efficacy of a fumarate reductase "
            "&lt;i&gt;frdA&lt;/i&gt; mutant of &lt;i&gt;Salmonella enteritidis&lt;/i&gt;.",
        ),
        (
            "Calpain-Inhibitors Protect Frataxin-Deficient Dorsal Root Ganglia Neurons from Loss "
            "of Mitochondrial Na<sup>+</sup>/Ca<sup>2+</sup> Exchanger, NCLX, and Apoptosis.",
            "Calpain-Inhibitors Protect Frataxin-Deficient Dorsal Root Ganglia Neurons from Loss "
            "of Mitochondrial Na&lt;sup&gt;+&lt;/sup&gt;/Ca&lt;sup&gt;2+&lt;/sup&gt; Exchanger, "
            "NCLX, and Apoptosis.",
        ),
        (
            "Dysregulation of sphingolipid-metabolizing enzymes in Friedreich's ataxia: "
            "<i>In vitro</i> and <i>in vivo</i> insights into therapeutic targeting.",
            "Dysregulation of sphingolipid-metabolizing enzymes in Friedreich's ataxia: "
            "&lt;i&gt;In vitro&lt;/i&gt; and &lt;i&gt;in vivo&lt;/i&gt; insights into "
            "therapeutic targeting.",
        ),
    ]
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    for recorded, epmc in cases:
        assert literature.title_text(recorded) == literature.title_text(epmc)
        write(tmp_path, corpus=[paper(title=recorded)])
        monkeypatch.setattr(literature, "fetch_record", lambda pid, t=epmc: {"title": t})
        assert literature.verify(root=tmp_path) == []
    # A genuinely different title still fails at the unchanged 0.9 threshold.
    write(tmp_path, corpus=[paper(title=cases[0][0])])
    monkeypatch.setattr(
        literature,
        "fetch_record",
        lambda pid: {"title": "Frataxin deficiency &lt;i&gt;in vivo&lt;/i&gt; alters iron uptake."},
    )
    assert any("recorded title differs" in p for p in literature.verify(root=tmp_path))


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
    blocks = literature.text_blocks(literature.full_text_markup("PMC1"))
    assert literature.quote_found("Nothing relevant here at all", blocks)
    assert not literature.quote_found("Frataxin transcript levels were markedly reduced", blocks)
    assert not literature.quote_found("Another quote from a cited paper", blocks)


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
    xml = (
        "<body><p>Expression differed (p &lt; 0.05 and q &gt; 0.1) in <italic>FXN</italic>."
        "</p></body>"
    )
    blocks = literature.text_blocks(xml)
    assert literature.quote_found("Expression differed (p < 0.05 and q > 0.1) in FXN.", blocks)
    assert not literature.quote_found("Expression differed (p > 0.05 and q > 0.1) in FXN.", blocks)


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


# --- attempt-3 findings: citation markers, path agreement, block boundaries -------------------

XREF_BODY = (
    "<body><sec><title>Results</title><p>Frataxin is reduced in fibroblast cells"
    '<xref ref-type="bibr" rid="b1">1</xref>. Next sentence here.</p>'
    "<p>Second paragraph starts with H<sub>2</sub>O<sub>2</sub> exposure.</p></sec></body>"
)
XLINK_BODY = XREF_BODY.replace('rid="b1"', 'rid="b1" xlink:href="#b1"')  # forces the fallback


def test_citation_markers_are_dropped_and_namespaces_do_not_matter():
    for body in (XREF_BODY, XLINK_BODY, XREF_BODY.upper().replace("FRATAXIN", "Frataxin")):
        blocks = literature.text_blocks(body)
        assert literature.quote_found(
            "Frataxin is reduced in fibroblast cells. Next sentence here.", blocks
        )
        assert not literature.quote_found("Frataxin is reduced in fibroblast cells1. Next", blocks)


def test_quotes_cannot_straddle_blocks():
    blocks = literature.text_blocks(XREF_BODY)
    assert not literature.quote_found("Next sentence here. Second paragraph starts", blocks)
    assert not literature.quote_found("Results Frataxin is reduced in fibroblast", blocks)
    # the old separator character is just a character: it cannot help a quote cross a block
    assert not literature.quote_found("fibroblast cells. Next sentence here. \u00b6 Second", blocks)


def test_quote_with_citation_number_fails_and_natural_quote_passes(tmp_path, monkeypatch):
    def card(quote):
        return CARD.replace("abstract_only", "full_text").replace(
            "Frataxin transcript levels were markedly reduced in patient cells.", quote
        )

    monkeypatch.setattr(
        literature, "fetch_record", lambda pid: {"title": "A paper", "pmcid": "PMC111"}
    )
    monkeypatch.setattr(literature, "_get", lambda url, as_json=True: XREF_BODY)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    corpus = [
        paper(
            status="read",
            screen_reason="RQ1",
            card="research/cards/MED_111.md",
            open_access=True,
            pmcid="PMC111",
        )
    ]
    write(
        tmp_path,
        corpus=corpus,
        cards={"MED_111.md": card("Frataxin is reduced in fibroblast cells. Next sentence here.")},
    )
    assert literature.verify(root=tmp_path) == []
    write(
        tmp_path,
        corpus=corpus,
        cards={"MED_111.md": card("Frataxin is reduced in fibroblast cells1. Next sentence here.")},
    )
    assert any("not found verbatim" in p for p in literature.verify(root=tmp_path))


def test_prose_comparisons_in_quotes_are_not_markup():
    assert not literature.TAG.search("cd4<cd8 t cells were more frequent in patients")
    assert literature.TAG.search("frataxin <italic>fxn</italic> levels")


def test_abstract_and_title_are_separate_blocks(tmp_path, monkeypatch):
    straddling = CARD.replace(
        "Frataxin transcript levels were markedly reduced in patient cells.",
        "markedly reduced in patient cells. A paper about frataxin",
    )
    write(
        tmp_path,
        corpus=[paper(status="read", screen_reason="RQ1", card="research/cards/MED_111.md")],
        cards={"MED_111.md": straddling},
    )
    rec = {
        "title": "A paper about frataxin",
        "abstractText": "Levels were markedly reduced in patient cells.",
    }
    monkeypatch.setattr(literature, "fetch_record", lambda pid: rec)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    assert any("not found verbatim" in p for p in literature.verify(root=tmp_path))


def test_author_year_citations_are_kept_as_prose():
    body = (
        '<body><p>Population frequency of 1-2:50,000 (<xref rid="c6" ref-type="bibr">Campuzano '
        "et al., 1996</xref>), and caused by deficient frataxin.</p></body>"
    )
    for b in (body, body.replace('rid="c6"', 'rid="c6" xlink:href="#c6"')):
        blocks = literature.text_blocks(b)
        assert literature.quote_found(
            "frequency of 1-2:50,000 (Campuzano et al., 1996), and caused by deficient frataxin.",
            blocks,
        )
    for marker in ("1", "2,3", "4-6", "[7]", "(8\u201310)"):
        assert literature._is_numeric_marker(marker)
    assert not literature._is_numeric_marker("Campuzano et al., 1996")


# --- attempt-4 findings: token matching, cut boundaries, word boundaries -----------------------


def test_dropped_footnotes_and_formulas_cannot_fuse_text():
    blocks = literature.text_blocks(
        "<body><p>Levels were 5<fn><p>x</p></fn>0 percent higher in patient cells overall.</p>"
        "<p>Levels of <inline-formula>FXN</inline-formula> were low in all patient lines.</p></body>"
    )
    assert not literature.quote_found("Levels were 50 percent higher in patient cells", blocks)
    assert not literature.quote_found("Levels of were low in all patient lines", blocks)
    assert literature.quote_found("percent higher in patient cells overall", blocks)


def test_whole_words_and_whole_numbers_only():
    blocks = literature.text_blocks(
        "<p>Frataxin is reduced in fibroblast cells, but this was not "
        "significantly different at 1.5 fold in 12 donors.</p>"
    )
    assert not literature.quote_found("rataxin is reduced in fibroblast", blocks)
    assert not literature.quote_found("this was not significant", blocks)
    assert not literature.quote_found("different at 1 fold in 12 donors", blocks)
    assert not literature.quote_found("different at 1.5 fold in 2 donors", blocks)
    assert literature.quote_found("this was not significantly different at 1.5 fold", blocks)


def test_figure_references_are_prose_numeric_bib_markers_are_not():
    blocks = literature.text_blocks(
        '<p>As shown in Fig. <xref ref-type="fig" rid="f2">2</xref>, frataxin decreased '
        '<sup><xref ref-type="bibr" rid="b3">3</xref></sup> in all lines.</p>'
    )
    assert literature.quote_found("As shown in Fig. 2, frataxin decreased in all lines.", blocks)
    assert not literature.quote_found("frataxin decreased 3 in all lines", blocks)


def test_signs_are_significant_light_punctuation_is_not():
    blocks = literature.text_blocks("<p>The log2 fold change was -1.2 (95% CI -1.6 to -0.8).</p>")
    assert literature.quote_found("The log2 fold change was -1.2 (95% CI -1.6 to -0.8)", blocks)
    assert literature.quote_found("The log2 fold change was \u22121.2", blocks)  # minus sign
    assert not literature.quote_found("The log2 fold change was 1.2", blocks)


def test_short_or_control_quotes_rejected(tmp_path, monkeypatch):
    assert not literature.quote_is_substantive("FXN 1.5 2.0 3.0 4.0 5.0 6.0 7.0")
    card = CARD.replace(
        "Frataxin transcript levels were markedly reduced in patient cells.",
        "Frataxin transcript levels were \\0 markedly reduced in patient cells.",
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
    assert any("control characters" in p for p in literature.verify(root=tmp_path))


# --- attempt-5 findings: decimal points, xref typing, and mutation-killing tests ---------------


def _found(markup, quote):
    return literature.quote_found(quote, literature.text_blocks(markup))


def test_leading_decimal_point_and_sign_are_part_of_the_number():
    assert not _found(
        "<p>levels went up 5 fold in cells here</p>", "levels went up .5 fold in cells"
    )
    assert not _found(
        "<p>levels went up .5 fold in cells here</p>", "levels went up 5 fold in cells"
    )
    assert _found("<p>levels went up .5 fold in cells here</p>", "levels went up .5 fold in cells")
    assert not _found("<p>a change of -1.2 in all donors</p>", "a change of 1.2 in all donors")
    # ranges and ratios are not mistaken for signed numbers
    assert _found(
        "<p>frequency of 1-2:50,000 in the population</p>", "frequency of 1-2:50,000 in the"
    )


def test_numbers_are_not_split_or_joined():
    src = "<p>expression rose 1.5 fold in treated patient cells</p>"
    assert _found(src, "expression rose 1.5 fold in treated")
    assert not _found(src, "expression rose 1 5 fold in treated")
    assert not _found(src, "expression rose 15 fold in treated")


def test_only_bibliography_xrefs_are_dropped():
    assert not _found(
        "<p>values of 5<xref>0</xref> were seen in cells</p>", "values of 5 were seen in cells"
    )
    assert _found(
        "<p>values of 5<xref>0</xref> were seen in cells</p>", "values of 50 were seen in cells"
    )
    # a dropped bibliography marker keeps its neighbours apart (no "cellshere")
    src = '<p>in cells<xref ref-type="bibr" rid="b1">1</xref>here today and now</p>'
    assert _found(src, "in cells here today and now")
    # a range split across markers leaves nothing behind
    src = (
        '<p>was reported before [<xref ref-type="bibr">1</xref>-<xref ref-type="bibr">3</xref>] '
        "in several cohorts</p>"
    )
    assert _found(src, "was reported before in several cohorts")


def test_block_end_events_split_text():
    src = "<sec><p>alpha beta gamma delta</p>tail words here now</sec>"
    assert not _found(src, "gamma delta tail words")
    assert _found(src, "tail words here now")


def test_operators_are_significant():
    src = "<p>levels were 20% higher (p = 0.01) with 3 ± 1 copies</p>"
    assert _found(src, "levels were 20% higher (p = 0.01) with 3 ± 1 copies")
    for altered in ("levels were 20 higher", "higher (p 0.01) with", "with 3 1 copies"):
        assert not _found(src, altered)


def test_cut_content_is_not_text():
    src = "<p>Levels of <inline-formula>FXN</inline-formula> were low in all patient lines.</p>"
    assert not _found(src, "FXN were low in all patient lines")
    assert not _found(
        "<p>A figure <alt-text>secret words in the alt text</alt-text> here.</p>",
        "secret words in the alt text",
    )
    # a self-closing cut tag still separates the text around it
    assert not _found("<p>alpha beta<disp-formula/>gamma delta</p>", "alpha beta gamma delta")


def test_quote_needs_four_words():
    assert not literature.quote_is_substantive("Mitochondrial dysfunction everywhere")
    assert literature.quote_is_substantive("Mitochondrial dysfunction was everywhere observed")


def test_section_titles_with_markup_are_text_and_unclosed_xref_does_not_swallow():
    src = "<sec><title>Effects of <italic>FXN</italic> silencing</title><p>body text one two</p></sec>"
    assert _found(src, "Effects of FXN silencing")
    assert not _found(src, "silencing body text one")
    src = '<p>first block with <xref ref-type="bibr">open marker never closed</p><p>second block words</p>'
    assert not _found(src, "never closed second block words")
    assert _found(src, "second block words")


# --- T-022: citation chasing, secrets, manifest column maps -----------------------------------


def test_citations_resolve_to_europe_pmc_and_never_guess(tmp_path, monkeypatch):
    write(tmp_path, corpus=[paper(pid="MED:111")])
    calls = []

    def fake_get(url, as_json=True, retries=3):
        calls.append(url)
        if "/works/pmid:111" in url:
            return {"id": "https://openalex.org/W1"}
        if "filter=cites" in url:
            return {
                "meta": {"next_cursor": None},
                "results": [
                    {
                        "id": "https://openalex.org/W2",
                        "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/222"},
                        "display_name": "Citing with PMID",
                        "publication_year": 2020,
                    },
                    {
                        "id": "https://openalex.org/W3",
                        "ids": {"doi": "https://doi.org/10.1/x"},
                        "display_name": "Citing with DOI",
                        "publication_year": 2021,
                    },
                    {
                        "id": "https://openalex.org/W4",
                        "ids": {},
                        "display_name": "No identifiers",
                        "publication_year": 2022,
                    },
                ],
            }
        if "europepmc" in url and "DOI" in urllib.parse.unquote(url):
            return {
                "resultList": {
                    "result": [
                        {
                            "source": "MED",
                            "id": "999",
                            "doi": "10.9/other",
                        },  # wrong DOI: never taken
                        {"source": "PPR", "id": "PPR9", "doi": "10.1/X"},
                    ]
                }
            }
        raise AssertionError(url)

    monkeypatch.setattr(literature, "_get", fake_get)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key-123")
    log = literature.citations("MED:111", "cited-by", root=tmp_path)
    assert [r["id"] for r in log["results"]] == ["MED:222", "PPR:PPR9"]
    assert [u["openalex"] for u in log["unresolved"]] == ["W4"]
    assert "secret-key-123" not in json.dumps(log)
    assert all("mailto=" in c for c in calls if "openalex" in c)


def test_request_errors_redact_the_api_key(monkeypatch):
    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(literature.urllib.request, "urlopen", boom)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError) as exc:
        literature._get("https://api.openalex.org/works?filter=x&api_key=supersecret&mailto=m")
    assert "supersecret" not in str(exc.value) and "api_key=***" in str(exc.value)


def test_literal_marker_character_in_source_is_not_a_citation():
    src = "<p>values of 5 were seen in cells today</p>"
    assert not literature.quote_found(
        "values of 5 were seen in cells",
        literature.text_blocks("<p>values of 50 were seen in cells today</p>"),
    )
    assert literature.quote_found("were seen in cells today", literature.text_blocks(src))


def test_manifest_column_map_and_comment_lines(tmp_path):
    from frda.io import check_columns, read_manifest_file
    from frda.manifest import Manifest, load_all

    m = {x.id: x for x in load_all()}["GSE104288"].model_dump()
    samples = [s for g in m["groups"] for s in g["samples"]]
    runs = {f"SRR{i:03d}": s for i, s in enumerate(samples)}
    body = "##annotation=G026\n##date=2021\ngene_id\t" + "\t".join(runs) + "\n"
    body += "ENSG1\t" + "\t".join("7" for _ in runs) + "\n"
    f = tmp_path / "counts.tsv"
    f.write_text(body)
    m["files"].append(
        {
            **m["files"][0],
            "name": "counts.tsv",
            "gene_id_column": "gene_id",
            "gene_id_type": "ensembl_gene_id",
            "column_map": runs,
            "comment_prefix": "##",
        }
    )
    manifest = Manifest.model_validate(m)
    df = read_manifest_file(f, manifest.file("counts.tsv"))
    assert list(df.index) == ["ENSG1"] and check_columns(df, manifest) == []
    # stricter since the T-022 verification: an incomplete map is an error, not a warning
    broken = dict(list(runs.items())[1:])  # one run left unmapped
    manifest.file("counts.tsv").column_map = broken
    with pytest.raises(ValueError, match="not covered by column_map"):
        read_manifest_file(f, manifest.file("counts.tsv"))


def test_column_map_is_validated(tmp_path):
    from frda.io import read_manifest_file
    from frda.manifest import ManifestFile

    base = dict(
        name="c.tsv",
        url="https://ftp.ncbi.nlm.nih.gov/geo/x",
        content="c",
        gene_id_column="gene_id",
        gene_id_type="ensembl_gene_id",
        values="v",
    )
    with pytest.raises(ValidationError, match="same sample"):
        ManifestFile.model_validate({**base, "column_map": {"SRR1": "F130", "SRR2": "F130"}})
    with pytest.raises(ValidationError, match="at least 2"):
        ManifestFile.model_validate({**base, "comment_prefix": "#"})
    f = tmp_path / "c.tsv"
    f.write_text("gene_id\tSRR1\tSRR2\nENSG1\t1\t2\n")
    with pytest.raises(ValueError, match="absent from the file header"):
        read_manifest_file(
            f,
            ManifestFile.model_validate(
                {**base, "column_map": {"SRR1": "F130", "SRR2": "F156", "SRR9": "F188"}}
            ),
        )
    f.write_text("gene_id\tF130\tF130\nENSG1\t1\t2\n")  # duplicated header without a map
    with pytest.raises(ValueError, match="duplicated sample columns"):
        read_manifest_file(f, ManifestFile.model_validate(base))


def test_check_columns_reports_duplicates():
    import pandas as pd

    from frda.io import check_columns
    from frda.manifest import load_all

    m = {x.id: x for x in load_all()}["GSE104288"]
    samples = [s for g in m.groups for s in g.samples]
    df = pd.DataFrame([[1] * (len(samples) + 1)], columns=[*samples, samples[0]])
    assert any("appears 2 times" in p for p in check_columns(df, m))


def test_citation_log_flags_truncation(tmp_path, monkeypatch):
    write(tmp_path, corpus=[paper(pid="MED:111")])

    def fake_get(url, as_json=True, retries=3):
        if "/works/pmid:111" in url:
            return {"id": "https://openalex.org/W1"}
        return {
            "meta": {"count": 300, "next_cursor": "abc"},
            "results": [
                {
                    "id": f"https://openalex.org/W{i}",
                    "ids": {"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{i}"},
                    "display_name": f"w{i}",
                    "publication_year": 2020,
                }
                for i in range(200)
            ],
        }

    monkeypatch.setattr(literature, "_get", fake_get)
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    log = literature.citations("MED:111", "cited-by", max_hits=150, root=tmp_path)
    assert log["hit_count"] == 300 and log["examined"] == 150 and log["truncated"] is True
    assert len(log["results"]) == 150
