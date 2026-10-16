"""Research memory: the literature corpus, reading cards, the state-of-the-art
synthesis, the registry of research leads (ideas) and the supervisor's
research decisions. This is what a PhD student keeps in their head and
notebooks; here it is versioned, cross-referenced and checked.

  research/corpus.yaml          every paper ever considered (screened or read)
  research/cards/<id>.md        one reading card per read paper (verbatim quotes + location)
  research/synthesis/*.md       state of the art; every statement cites [@SRC:ID]
  research/ideas.yaml           research leads with a scored rubric and a status
  research/decisions/RD-*.md    arbitration decisions of the weekly supervision
  research/search-logs/*.json   reproducible literature searches (query, date, hits)

Paper ids are Europe PMC "source:id" pairs: MED:29125828 (PubMed), PPR:PPR1219382
(preprint), PMC:PMC5719256 (PMC-only). Everything here is offline-checkable;
online checks (do the papers exist, are the quotes in them) live in
`frda.literature` and are run by the verifier.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from frda import paths
from frda.yamlio import load_yaml, read_front_matter

RESEARCH = paths.ROOT / "research"
PAPER_ID = r"^(MED|PPR|PMC|AGR|CBA|ETH|HIR|PAT|CTX):[A-Za-z0-9._-]+$"
CITATION = re.compile(r"\[@((?:MED|PPR|PMC|AGR|CBA|ETH|HIR|PAT|CTX):[A-Za-z0-9._-]+)\]")


def _iso(v: object) -> object:
    return v.isoformat() if isinstance(v, dt.date) else v


# YAML parses unquoted 2026-10-17 as a date; keep ISO strings everywhere.
DateStr = Annotated[str, BeforeValidator(_iso)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- corpus


class Paper(Strict):
    id: str = Field(pattern=PAPER_ID)
    title: str
    year: int | None = None
    journal: str | None = None
    first_author: str | None = None
    doi: str | None = None
    pmcid: str | None = None
    kind: Literal["primary", "review", "preprint", "dataset", "methods", "other"]
    open_access: bool
    added: DateStr
    added_by: str = Field(description="Task or routine that added it (T-xxx, L-xxx, W-...).")
    found_by: list[str] = Field(default_factory=list, description="search-log ids that hit it")
    status: Literal["to_screen", "excluded", "to_read", "read"]
    screen_reason: str | None = Field(
        default=None, description="Why excluded / why kept, against the review protocol criteria."
    )
    relevance: int | None = Field(default=None, ge=0, le=3, description="0 none … 3 central")
    topics: list[str] = Field(default_factory=list)
    card: str | None = None

    @model_validator(mode="after")
    def consistency(self) -> Paper:
        if self.status == "read" and not self.card:
            raise ValueError(f"{self.id}: status read requires a card")
        if self.status in {"excluded", "to_read", "read"} and not self.screen_reason:
            raise ValueError(f"{self.id}: screened papers need a screen_reason")
        return self


class Corpus(Strict):
    papers: list[Paper] = Field(default_factory=list)

    def get(self, pid: str) -> Paper | None:
        return next((p for p in self.papers if p.id == pid), None)


# --------------------------------------------------------------------------- cards


class Finding(Strict):
    statement: str = Field(description="Our paraphrase, one sentence.")
    quote: str = Field(min_length=20, description="Verbatim sentence(s) from the paper.")
    location: str = Field(description="Section / figure / table / abstract.")

    @model_validator(mode="after")
    def substantive(self) -> Finding:
        if sum(ch.isalnum() for ch in self.quote) < 20:
            raise ValueError("quote must contain at least 20 letters or digits")
        return self


class CardMeta(Strict):
    paper: str = Field(pattern=PAPER_ID)
    read_date: DateStr
    read_by: str
    source_text: Literal["full_text", "abstract_only"]
    question: str
    model_system: str
    independent_units: str = Field(description="n per group, in independent units, as reported.")
    methods: str
    findings: list[Finding] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    datasets: list[str] = Field(default_factory=list, description="GEO / other accessions used")
    relevance_to: list[str] = Field(default_factory=list, description="Q1, Q2, ideas, tasks")
    leads: list[str] = Field(default_factory=list, description="Idea ids this paper inspired")


# --------------------------------------------------------------------------- ideas

IdeaStatus = Literal["seed", "scoping", "candidate", "active", "parked", "rejected", "done"]
RUBRIC = ("novelty", "feasibility", "value", "cost", "risk")
# Weights of the priority score. cost and risk count against (5 = cheap / safe is scored 5 by
# convention: "cost: 5" means LOW cost). Documented in research/PLAN.md.
WEIGHTS = {"novelty": 0.30, "feasibility": 0.25, "value": 0.25, "cost": 0.10, "risk": 0.10}


class Scores(Strict):
    novelty: int = Field(ge=1, le=5)
    feasibility: int = Field(ge=1, le=5)
    value: int = Field(ge=1, le=5)
    cost: int = Field(ge=1, le=5, description="5 = cheap")
    risk: int = Field(ge=1, le=5, description="5 = low risk")
    rationale: str = Field(min_length=20)

    @property
    def priority(self) -> float:
        return round(sum(getattr(self, k) * w for k, w in WEIGHTS.items()), 2)


class Idea(Strict):
    id: str = Field(pattern=r"^I-\d{3}$")
    title: str
    question: str
    rationale: str
    sources: list[str] = Field(default_factory=list, description="Paper ids in the corpus")
    data: list[str] = Field(
        default_factory=list, description="Public accessions that could test it"
    )
    status: IdeaStatus
    novelty_check: Literal["not_done", "known", "partially_known", "apparently_new"] = "not_done"
    scores: Scores | None = None
    publishable_if: str | None = Field(
        default=None, description="Why the result would be worth reporting, positive or negative."
    )
    decision: str | None = Field(default=None, description="RD-xxx that set the current status")
    tasks: list[str] = Field(default_factory=list)
    created: DateStr
    updated: DateStr
    history: list[str] = Field(default_factory=list, description="'YYYY-MM-DD status: reason'")

    @model_validator(mode="after")
    def gates(self) -> Idea:
        if self.status in {"candidate", "active", "done"}:
            if self.scores is None:
                raise ValueError(f"{self.id}: {self.status} ideas need scores")
            if self.novelty_check == "not_done":
                raise ValueError(f"{self.id}: {self.status} ideas need a novelty check")
            if not self.publishable_if:
                raise ValueError(f"{self.id}: {self.status} ideas need publishable_if")
        if (
            self.status in {"active", "parked", "rejected", "done", "candidate"}
            and not self.decision
        ):
            raise ValueError(f"{self.id}: status {self.status} must reference a decision (RD-xxx)")
        return self


class IdeaRegistry(Strict):
    ideas: list[Idea] = Field(default_factory=list)


# --------------------------------------------------------------------------- decisions


class DecisionMeta(Strict):
    id: str = Field(pattern=r"^RD-\d{3}$")
    date: DateStr
    kind: Literal["arbitration", "pivot", "budget", "phase"]
    summary: str
    ideas: list[str] = Field(default_factory=list)
    budget: dict[str, float] | None = None
    needs_human: bool = False


# --------------------------------------------------------------------------- loading


def load_corpus(root: Path | None = None) -> Corpus:
    p = (root or paths.ROOT) / "research" / "corpus.yaml"
    return Corpus.model_validate(load_yaml(p) or {}) if p.exists() else Corpus()


def load_ideas(root: Path | None = None) -> IdeaRegistry:
    p = (root or paths.ROOT) / "research" / "ideas.yaml"
    return IdeaRegistry.model_validate(load_yaml(p) or {}) if p.exists() else IdeaRegistry()


def load_cards(root: Path | None = None) -> dict[str, tuple[Path, CardMeta]]:
    d = (root or paths.ROOT) / "research" / "cards"
    out: dict[str, tuple[Path, CardMeta]] = {}
    for p in sorted(d.glob("*.md")) if d.exists() else []:
        if p.name.startswith("_"):  # _TEMPLATE.md
            continue
        meta, _ = read_front_matter(p)
        card = CardMeta.model_validate(meta)
        if card.paper in out:
            raise ValueError(f"two cards for {card.paper}: {out[card.paper][0].name}, {p.name}")
        out[card.paper] = (p, card)
    return out


def load_decisions(root: Path | None = None) -> dict[str, tuple[Path, DecisionMeta]]:
    d = (root or paths.ROOT) / "research" / "decisions"
    out: dict[str, tuple[Path, DecisionMeta]] = {}
    for p in sorted(d.glob("RD-*.md")) if d.exists() else []:
        meta, _ = read_front_matter(p)
        dm = DecisionMeta.model_validate(meta)
        if dm.id in out:
            raise ValueError(f"two decision files with id {dm.id}")
        out[dm.id] = (p, dm)
    return out


def card_filename(pid: str) -> str:
    return pid.replace(":", "_") + ".md"


# --------------------------------------------------------------------------- checks


def problems(root: Path | None = None) -> list[str]:
    """Offline cross-reference checks (used by the `research` gate)."""
    root = root or paths.ROOT
    out: list[str] = []
    corpus = load_corpus(root)
    ids = [p.id for p in corpus.papers]
    out += [f"corpus: duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    dois = [p.doi.lower() for p in corpus.papers if p.doi]
    out += [f"corpus: duplicate doi {d}" for d in sorted({d for d in dois if dois.count(d) > 1})]

    cards = load_cards(root)
    for p in corpus.papers:
        if p.card:
            if not (root / p.card).exists():
                out.append(f"{p.id}: card {p.card} missing")
            elif p.id not in cards:
                out.append(f"{p.id}: card {p.card} is about another paper")
    for pid, (path, card) in cards.items():
        paper = corpus.get(pid)
        rel = path.relative_to(root).as_posix()
        if paper is None:
            out.append(f"{rel}: paper {pid} not in corpus")
            continue
        if paper.status != "read":
            out.append(f"{rel}: corpus status of {pid} is {paper.status}, expected read")
        if card.source_text == "full_text" and not paper.open_access:
            out.append(f"{rel}: full_text reading claimed for a non open-access paper")

    synth = root / "research" / "synthesis"
    for md in sorted(synth.glob("*.md")) if synth.exists() else []:
        text = md.read_text(encoding="utf-8")
        for pid in sorted(set(CITATION.findall(text))):
            paper = corpus.get(pid)
            if paper is None:
                out.append(f"{md.name}: cites {pid}, not in corpus")
            elif paper.status != "read":
                out.append(
                    f"{md.name}: cites {pid}, which has not been read (status {paper.status})"
                )

    plan = load_plan(root)
    budget = plan.get("track_budget") or {}
    if plan:
        if abs(sum(budget.values()) - 1.0) > 0.01:
            out.append(f"plan: track_budget sums to {sum(budget.values()):.2f}, expected 1.00")
        lo, hi = plan.get("budget_bounds", [0.0, 1.0])
        for tr, v in budget.items():
            if not lo <= v <= hi:
                out.append(f"plan: budget {tr}={v} outside bounds [{lo}, {hi}]")
        window = plan.get("budget_window", 10)
        if not isinstance(window, int) or window < 1:
            out.append(f"plan: budget_window must be an integer >= 1, got {window!r}")
        for tr, floor in (plan.get("track_floor") or {}).items():
            if budget.get(tr, 0.0) < floor:
                out.append(f"plan: budget {tr}={budget.get(tr, 0.0)} below its floor {floor}")
        phases = {ph["id"] for ph in plan.get("phases", [])}
        if plan.get("current_phase") not in phases:
            out.append(f"plan: current_phase {plan.get('current_phase')} not in phases")

    decisions = load_decisions(root)
    registry = load_ideas(root)
    iids = [i.id for i in registry.ideas]
    out += [f"ideas: duplicate id {i}" for i in sorted({i for i in iids if iids.count(i) > 1})]
    for idea in registry.ideas:
        for s in idea.sources:
            if corpus.get(s) is None:
                out.append(f"{idea.id}: source {s} not in corpus")
        if idea.decision and idea.decision not in decisions:
            out.append(f"{idea.id}: decision {idea.decision} not found in research/decisions/")
    active = [i.id for i in registry.ideas if i.status == "active"]
    if plan and len(active) > plan.get("max_active_ideas", 1):
        out.append(f"ideas: {len(active)} active ideas {active} > max_active_ideas")
    for did, (_, dm) in decisions.items():
        if dm.kind == "pivot" and not dm.needs_human:
            out.append(f"{did}: a pivot decision must set needs_human: true (owner's call)")
        for iid in dm.ideas:
            if iid not in iids:
                out.append(f"{did}: references unknown idea {iid}")
    return out


def load_plan(root: Path | None = None) -> dict:
    p = (root or paths.ROOT) / "research" / "plan.yaml"
    return load_yaml(p) or {} if p.exists() else {}


def summary(root: Path | None = None) -> dict:
    """Compact view for the hub and the supervisor."""
    root = root or paths.ROOT
    corpus = load_corpus(root)
    counts: dict[str, int] = {}
    for p in corpus.papers:
        counts[p.status] = counts.get(p.status, 0) + 1
    registry = load_ideas(root)
    decisions = load_decisions(root)
    last = max(decisions.values(), key=lambda x: (x[1].date, x[1].id), default=None)
    plan = load_plan(root)
    return {
        "phase": plan.get("current_phase"),
        "track_budget": plan.get("track_budget", {}),
        "corpus": {
            "total": len(corpus.papers),
            **{s: counts.get(s, 0) for s in ("to_screen", "excluded", "to_read", "read")},
        },
        "ideas": [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "novelty_check": i.novelty_check,
                "priority": i.scores.priority if i.scores else None,
            }
            for i in registry.ideas
        ],
        "last_decision": (
            {"id": last[1].id, "date": last[1].date, "summary": last[1].summary} if last else None
        ),
    }
