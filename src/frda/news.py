"""News for non-specialists (research/news/*.md): what was found, in plain French.

A news item travels like any other work: written on a branch (by the worker when a task lands
claims or closes a milestone, by the weekly supervision for the weekly chronicle), checked by the
verifier, landed on main — and only then announced (Telegram from the landing workflow, the hub
from summary.json). Popularising must never upgrade a result: the `news` gate ties every finding
to its claims and to their weakest evidence level, requires a "what it does NOT mean" section,
and refuses clinical or causal wording in French and English.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from frda import paths
from frda.claims import FORBIDDEN_WORDING, load_ledger
from frda.research import DateStr
from frda.yamlio import read_front_matter

NEWS_DIR = "research/news"
SECTIONS = (
    "Ce qu'on a fait",
    "Ce que ça veut dire",
    "Ce que ça ne veut pas dire",
    "Et ensuite",
)
EVIDENCE_ORDER = ["exploratory", "single_dataset", "replicated", "preregistered_confirmed"]
EVIDENCE_PLAIN = {
    "exploratory": "piste exploratoire, à confirmer",
    "single_dataset": "observé dans un seul jeu de données",
    "replicated": "retrouvé dans des données indépendantes",
    "preregistered_confirmed": "confirmé par une analyse annoncée à l'avance",
}
# Stems with their inflections (guérira, prouvent, causé...), not single forms. They are refused
# everywhere, negated or not: "ne prouve pas" and "pas de doute, ça prouve" cannot be told apart
# reliably, so the limits section is written without them ("ce n'est pas une démonstration").
FORBIDDEN_FR = [
    r"\bgu[ée]ri\w*",  # guérir, guérira, guérissent, guérison
    r"\bsoign(?:er|e|es|ent|era|eront|erait|é|ée|és|ées)\b",
    r"\brem[èe]des?\b",
    r"\bmiracle\w*|\bmiracul\w*",
    r"\bth[ée]rap\w*",  # thérapie, thérapeutique
    r"\bm[ée]dicament\w*",
    r"\btraitements? (?:efficaces?|prometteurs?)\b",
    r"\bprouv\w*",  # prouve, prouvent, prouvera, prouvé (not "éprouvé", "approuvé")
    r"\bpreuves? (?:que|formelles?|définitives?)\b",
    r"\bd[ée]montr\w*",  # démontre, démontré (not "démonstration")
    r"\b[ée]tabli(?:t|ssent|ra|ront|e|es|s)?\b",
    r"\bvalidé(?:e|s|es)?\b",  # validé (not "valide", "validation")
    r"\br[ée]pliqué(?:e|s|es)?\b",
    r"\bcaus(?:e|es|ent|era|eront|erait|ait|aient|é|ée|és|ées|er|al|ale|aux|alité)\b",
    r"\bprovoqu\w*",
    r"\bentra[îi]n\w*",
    r"\b(?:est|sont|serait|seraient|soit|soient) responsables? (?:de|du|des|d')",  # not "le responsable du projet"
    r"\bperc[ée]es?\b",
    r"\br[ée]volution\w*",
    r"\bespoirs?\b",
    r"\bavanc[ée]es? (?:majeures?|décisives?|historiques?)\b",
    # English, beyond the claims list
    r"\btherap\w*",
    r"\bbreakthroughs?\b",
    r"\bdemonstrat(?:e|es|ed)\b",
]
MAX_BODY_CHARS = 1800
ID_RE = r"^N-\d{8}-[a-z0-9-]+$"


class NewsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_RE)
    date: DateStr
    kind: Literal["finding", "milestone", "weekly", "literature", "decision", "project"]
    title: str = Field(min_length=10, max_length=90)
    claims: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    evidence: (
        Literal["exploratory", "single_dataset", "replicated", "preregistered_confirmed"] | None
    ) = None


def news_files(root: Path | None = None) -> list[Path]:
    d = (root or paths.ROOT) / NEWS_DIR
    if not d.exists():
        return []
    return sorted(p for p in d.glob("N-*.md"))


def load(path: Path) -> tuple[NewsMeta, str]:
    meta, body = read_front_matter(path)
    return NewsMeta.model_validate(meta), body.strip()


def problems(root: Path | None = None) -> list[str]:
    root = root or paths.ROOT
    out: list[str] = []
    claims = {c.id: c for c in load_ledger(root / "evaluation" / "claims.yaml").claims}
    seen: dict[str, str] = {}
    for path in news_files(root):
        name = path.name
        try:
            meta, body = load(path)
        except Exception as exc:  # schema error is a gate failure, reported per file
            out.append(f"{name}: {exc}")
            continue
        if path.stem != meta.id:
            out.append(f"{name}: file name must be the news id ({meta.id}.md)")
        if meta.id in seen:
            out.append(f"{name}: duplicate id {meta.id} (also {seen[meta.id]})")
        seen[meta.id] = name
        for section in SECTIONS:
            if not re.search(rf"^\*\*{re.escape(section)}\*\*", body, flags=re.M):
                out.append(f"{name}: missing section **{section}**")
        if len(body) > MAX_BODY_CHARS:
            out.append(f"{name}: {len(body)} characters > {MAX_BODY_CHARS} (keep it short)")
        out += [f"{name}: {p}" for p in wording_problems(meta.title, body)]
        unknown = [c for c in meta.claims if c not in claims]
        out += [f"{name}: claim {c} not in the ledger" for c in unknown]
        if meta.kind == "finding":
            if not meta.claims:
                out.append(f"{name}: a finding must cite its claims")
            if meta.evidence is None:
                out.append(f"{name}: a finding must state its evidence level")
        if meta.evidence is not None:
            # Any kind that prints a level of evidence (Telegram, hub) must have claims behind it.
            if not meta.claims:
                out.append(f"{name}: evidence '{meta.evidence}' stated without any claim behind it")
            known = [claims[c] for c in meta.claims if c in claims]
            if known:
                weakest = min(known, key=lambda c: EVIDENCE_ORDER.index(c.evidence_level))
                if EVIDENCE_ORDER.index(meta.evidence) > EVIDENCE_ORDER.index(
                    weakest.evidence_level
                ):
                    out.append(
                        f"{name}: evidence '{meta.evidence}' is stronger than its weakest claim "
                        f"{weakest.id} ('{weakest.evidence_level}')"
                    )
    return out


def wording_problems(title: str, body: str) -> list[str]:
    """Overselling words, French and English, after Unicode NFC normalisation (a decomposed
    "gue\u0301rit" must not slip past the accented stems). One report per distinct word."""
    text = unicodedata.normalize("NFC", f"{title}\n{body}")
    found: dict[str, None] = {}
    for pattern in [*FORBIDDEN_WORDING, *FORBIDDEN_FR]:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.setdefault(m.group(0).lower(), None)
    return [f"forbidden wording {w!r} (overclaiming)" for w in found]


def plain(body: str) -> str:
    """Markdown-lite to plain text (Telegram is sent without parse mode)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", body)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text.strip()


DEFAULT_LINK = "https://github.com/clementpep/frda-mito-signatures/tree/main/research/news"


def render_telegram(meta: NewsMeta, body: str, link: str = DEFAULT_LINK) -> str:
    lines = [f"🧬 Recherche FRDA — {meta.title}", "", plain(body)]
    if meta.evidence:
        lines += ["", f"Niveau de preuve : {EVIDENCE_PLAIN[meta.evidence]}."]
    lines += ["", f"Détails : {link}"]
    return "\n".join(lines)[:4000]


def summary(root: Path | None = None, limit: int = 20) -> list[dict]:
    items = []
    for path in news_files(root):
        try:
            meta, body = load(path)
        except Exception:
            continue  # reported by the gate
        items.append(
            {
                "id": meta.id,
                "date": meta.date,
                "kind": meta.kind,
                "title": meta.title,
                "body": body,
                "evidence": meta.evidence,
                "evidence_plain": EVIDENCE_PLAIN.get(meta.evidence or ""),
                "claims": meta.claims,
            }
        )
    items.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return items[:limit]
