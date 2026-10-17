"""Europe PMC client for the literature work (allowlisted source `europe-pmc`).

- `search`  reproducible query → search log (research/search-logs/) + candidate ids
- `add`     append papers to the corpus as `to_screen`, with metadata from Europe PMC
- `verify`  online audit used by the verifier: every paper exists with the recorded
            title, and every quote of a reading card appears in the paper as the same
            sequence of words and numbers within one block (full text for open-access papers,
            abstract otherwise). Best-effort by design: case, light punctuation and
            sub/superscript formatting are ignored, and only quotes and titles are checked
            (not the paraphrase, location or published values) — the verifier reads those.
- `citations` citation chasing via OpenAlex, resolved to Europe PMC ids.

An LLM can invent a plausible paper or a plausible quote; this module is how the
project catches it. Europe PMC is fetched here rather than through `frda.acquire`: these are
metadata and article texts checked against the corpus, not datasets with frozen checksums
(allowlist source `europe-pmc`).
"""

from __future__ import annotations

import datetime as dt
import difflib
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from frda import paths
from frda.research import Paper, card_filename, load_cards, load_corpus
from frda.yamlio import dump_yaml, load_yaml

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "frda-mito-signatures/0.1 (+https://github.com/clementpep/frda-mito-signatures)"


def _get(url: str, *, as_json: bool = True, retries: int = 3) -> Any:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if as_json else body
        except Exception as exc:  # network: retry, then surface the error
            last = exc
            time.sleep(1.5 * (attempt + 1))
    safe = re.sub(r"(api_key=)[^&]+", r"\1***", url)
    raise RuntimeError(f"request failed: {safe}: {last}")


def pid_of(rec: dict) -> str:
    return f"{rec['source']}:{rec['id']}"


def search(query: str, max_hits: int = 200) -> dict[str, Any]:
    """Run a query, return {query, date, hit_count, results:[{id,title,year,...}]}."""
    results: list[dict[str, Any]] = []
    cursor = "*"
    hit_count = 0
    while len(results) < max_hits:
        params = {
            "query": query,
            "format": "json",
            "resultType": "lite",
            "pageSize": str(min(100, max_hits - len(results))),
            "cursorMark": cursor,
        }
        data = _get(f"{BASE}/search?{urllib.parse.urlencode(params)}")
        hit_count = int(data.get("hitCount", 0))
        page = data.get("resultList", {}).get("result", [])
        for r in page:
            results.append(
                {
                    "id": pid_of(r),
                    "title": r.get("title", ""),
                    "year": int(r["pubYear"]) if r.get("pubYear", "").isdigit() else None,
                    "first_author": (r.get("authorString") or "").split(",")[0] or None,
                    "journal": r.get("journalTitle"),
                    "open_access": r.get("isOpenAccess") == "Y",
                }
            )
        nxt = data.get("nextCursorMark")
        if not page or not nxt or nxt == cursor:
            break
        cursor = nxt
    return {
        "query": query,
        "date": dt.date.today().isoformat(),
        "hit_count": hit_count,
        "retrieved": len(results),
        "results": results,
    }


def save_search_log(log: dict[str, Any], slug: str, task: str, root: Path | None = None) -> Path:
    d = (root or paths.ROOT) / "research" / "search-logs"
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-") or "search"
    path = d / f"{log['date']}-{slug}.json"
    n = 2
    while path.exists():  # a search log is evidence: never overwrite one
        path = d / f"{log['date']}-{slug}-{n}.json"
        n += 1
    path.write_text(json.dumps({**log, "task": task}, indent=2, ensure_ascii=False) + "\n")
    return path


def fetch_record(pid: str) -> dict[str, Any] | None:
    src, ext = pid.split(":", 1)
    q = urllib.parse.quote(f"EXT_ID:{ext} AND SRC:{src}")
    data = _get(f"{BASE}/search?query={q}&format=json&resultType=core")
    res = data.get("resultList", {}).get("result", [])
    for r in res:  # never trust the first hit blindly: source and id must match
        if r.get("source") == src and str(r.get("id")) == ext:
            return r
    return None


def _kind(rec: dict[str, Any]) -> str:
    if rec.get("source") == "PPR":
        return "preprint"
    types = " ".join((rec.get("pubTypeList") or {}).get("pubType", [])).lower()
    if "review" in types:
        return "review"
    return "primary"


def paper_from_record(rec: dict[str, Any], task: str, found_by: list[str]) -> Paper:
    return Paper(
        id=pid_of(rec),
        title=html.unescape(rec.get("title", "")).strip(),
        year=int(rec["pubYear"]) if str(rec.get("pubYear", "")).isdigit() else None,
        journal=((rec.get("journalInfo") or {}).get("journal") or {}).get("title"),
        first_author=(rec.get("authorString") or "").split(",")[0] or None,
        doi=rec.get("doi"),
        pmcid=rec.get("pmcid"),
        kind=_kind(rec),
        open_access=rec.get("isOpenAccess") == "Y",
        added=dt.date.today().isoformat(),
        added_by=task,
        found_by=found_by,
        status="to_screen",
    )


def add_papers(
    ids: list[str], task: str, found_by: list[str], root: Path | None = None
) -> list[str]:
    """Add ids not yet in the corpus; return the ids actually added."""
    root = root or paths.ROOT
    path = root / "research" / "corpus.yaml"
    raw = load_yaml(path) if path.exists() else None
    raw = raw or {"papers": []}
    corpus = load_corpus(root)
    known = {p.id for p in corpus.papers}
    known_doi = {p.doi.lower() for p in corpus.papers if p.doi}
    added: list[str] = []
    for pid in ids:
        if pid in known:
            continue
        rec = fetch_record(pid)
        if rec is None:
            raise RuntimeError(
                f"{pid}: not found in Europe PMC (refusing to add an unverifiable id)"
            )
        paper = paper_from_record(rec, task, found_by)
        if paper.doi and paper.doi.lower() in known_doi:
            continue  # same work under another source id (e.g. preprint + article)
        raw["papers"].append(paper.model_dump(exclude_none=True))
        known.add(paper.id)
        if paper.doi:
            known_doi.add(paper.doi.lower())
        added.append(paper.id)
        time.sleep(0.2)
    dump_yaml(raw, path)
    return added


# --------------------------------------------------------------------------- verification


def normalise(text: str) -> str:
    """Typographic normalisation (Unicode forms, dashes, quotes, whitespace, case)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2212", "-")  # minus sign
    text = text.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


# ----------------------------------------------------------------------------------------------
# Verbatim matching (redesigned after T-021 verification, attempts 1-4).
#
# A quote is accepted only if its sequence of word tokens appears contiguously inside ONE text
# block of the paper (a paragraph, a title, a table cell, the abstract, the title).
#   - Tokens are whole words or whole numbers ("1.5", "2:50,000"), so a quote cannot match half a
#     word ("rataxin" in "frataxin") or fuse two numbers ("5" + "0" -> "50").
#   - Block boundaries are structural (separate token lists), not characters: nothing a quote
#     contains can match or cross them.
#   - Light punctuation (, . ; : ( ) [ ] quotes ! ?) is ignored when comparing, so a faithful
#     quote that leaves out a citation marker still matches; signs and operators (- + < > = % ±)
#     are significant.
#   - One parser for everything (stdlib HTMLParser: tolerant, case-insensitive, namespace-blind),
#     so XML full texts and HTML-ish abstracts are read the same way.
#   - Numeric bibliography markers (<xref ref-type="bibr">1</xref>, "[2]", "3-5") are removed;
#     author-year citations and figure/table references are prose and kept. Footnotes and
#     formulas are removed AND end the block, so text around them cannot be joined.
# ----------------------------------------------------------------------------------------------

TAG = re.compile(r"</?([A-Za-z][\w:.-]*)(?:\s+[\w:.-]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'))?)*\s*/?>")
NUMERIC_MARKER = re.compile(r"[\[\(]?\s*\d+(?:\s*[-\u2013,]\s*\d+)*\s*[\]\)]?")
BLOCK_TAGS = {
    "p",
    "sec",
    "title",
    "label",
    "caption",
    "fig",
    "table-wrap",
    "table",
    "tr",
    "td",
    "th",
    "list",
    "list-item",
    "disp-quote",
    "abstract",
    "body",
    "def-item",
    "def",
    "term",
    "kwd",
    "boxed-text",
    "br",
    "break",
    "article-title",
    "ref",
    "ref-list",
    "fn-group",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ul",
    "ol",
    "div",
    "section",
    "blockquote",
}
CUT_TAGS = {
    "fn",
    "inline-formula",
    "disp-formula",
    "mml:math",
    "math",
    "tex-math",
    "alt-text",
    "long-desc",
    "x-script",
    "x-style",
    "x-textarea",
}
BLOCK_TAGS |= {"x-title", "graphic", "inline-graphic", "media", "table-wrap-foot"}
# HTMLParser reads <title>, <script>, <style>, <textarea> as raw text (inner tags become text);
# JATS uses <title> for every section heading, so these are renamed before parsing.
RAW_TEXT_TAGS = re.compile(r"<(/?)(title|script|style|textarea)\b", flags=re.I)
MARKER = "\ue000"  # placeholder for a dropped numeric citation marker (private-use character)
MARKER_RUN = re.compile(MARKER + r"(?:[\s,;\-\u2013\[\]()]*" + MARKER + r")*")
IGNORED_PUNCT = set(",.;:()[]{}\"'!?")
# Numbers are whole tokens and keep an attached sign or leading decimal point (".5" != "5",
# "-1.2" != "1.2"), but only when not glued to a preceding word or number ("1-2" stays 1, -, 2).
TOKEN = re.compile(r"(?<![\w.])[-+]?\.?\d+(?:[.,:/]\d+)*|\d+(?:[.,:/]\d+)*|\w+|[^\w\s]")


def _is_numeric_marker(text: str) -> bool:
    return bool(NUMERIC_MARKER.fullmatch(text.strip()))


class _Blocks(HTMLParser):
    """Collect text blocks from XML/HTML markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.current: list[str] = []
        self.cut_depth = 0
        self.xref: list[tuple[str | None, list[str]]] = []  # (ref-type, collected text)

    def _flush_xrefs(self) -> None:
        # An xref left open by malformed markup must not swallow the following blocks.
        while self.xref:
            _, parts = self.xref.pop()
            self._emit("".join(parts))

    def _end_block(self) -> None:
        self._flush_xrefs()
        text = MARKER_RUN.sub(" ", "".join(self.current)).strip()
        if text:
            self.blocks.append(text)
        self.current = []

    def _emit(self, data: str) -> None:
        if self.xref:
            self.xref[-1][1].append(data)
        else:
            self.current.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in CUT_TAGS:
            if self.cut_depth == 0:
                self._end_block()
            self.cut_depth += 1
        elif self.cut_depth:
            return
        elif tag in BLOCK_TAGS:
            self._end_block()
        elif tag == "xref":
            ref_type = dict(attrs).get("ref-type")
            self.xref.append((ref_type.lower() if ref_type else None, []))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.cut_depth:
            return
        if tag in BLOCK_TAGS or tag in CUT_TAGS:
            self._end_block()  # a self-closing formula or graphic still separates the text
        else:
            self._emit(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in CUT_TAGS and self.cut_depth:
            self.cut_depth -= 1
            return
        if self.cut_depth:
            return
        if tag == "xref" and self.xref:
            ref_type, parts = self.xref.pop()
            text = "".join(parts)
            # Only bibliography markers are dropped; untyped xrefs and figure/table references are
            # prose. A placeholder keeps neighbours apart; runs like "[1]-[3]" collapse to a space.
            self._emit(MARKER if ref_type == "bibr" and _is_numeric_marker(text) else text)
        elif tag in BLOCK_TAGS:
            self._end_block()

    def handle_data(self, data: str) -> None:
        if not self.cut_depth:
            self._emit(data)

    def close(self) -> None:
        super().close()
        self._end_block()


def significant_tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(normalise(text)) if t not in IGNORED_PUNCT]


def text_blocks(markup: str) -> list[list[str]]:
    """Markup -> list of blocks, each a list of significant tokens."""
    parser = _Blocks()
    markup = markup.replace(MARKER, " ")  # a literal U+E000 in the paper is not a citation marker
    parser.feed(RAW_TEXT_TAGS.sub(lambda m: f"<{m.group(1)}x-{m.group(2).lower()}", markup))
    parser.close()
    return [toks for b in parser.blocks if (toks := significant_tokens(b))]


def quote_found(quote: str, blocks: list[list[str]]) -> bool:
    needle = significant_tokens(quote)
    if not needle:
        return False
    n = len(needle)
    first = needle[0]
    for toks in blocks:
        for i in range(len(toks) - n + 1):
            if toks[i] == first and toks[i : i + n] == needle:
                return True
    return False


def full_text_markup(pmcid: str) -> str:
    """The article body only: front matter and reference list would let a quote taken from a
    cited paper's title, or from another article's abstract, pass as this paper's text."""
    xml = _get(f"{BASE}/{pmcid}/fullTextXML", as_json=False)
    m = re.search(r"<body[ >].*?</body>", xml, flags=re.S)
    return m.group(0) if m else ""


MIN_QUOTE_CHARS = 20
MIN_QUOTE_WORDS = 4


def quote_is_substantive(quote: str) -> bool:
    words = [t for t in significant_tokens(quote) if any(ch.isalpha() for ch in t)]
    return sum(ch.isalnum() for ch in quote) >= MIN_QUOTE_CHARS and len(words) >= MIN_QUOTE_WORDS


def verify(paper_ids: list[str] | None = None, root: Path | None = None) -> list[str]:
    """Online audit. Returns problems (empty = all good).

    Explicit ids that are not in the corpus, or an empty target list, are problems: an audit
    that checks nothing must not report PASS.
    """
    root = root or paths.ROOT
    corpus = load_corpus(root)
    cards = load_cards(root)
    problems: list[str] = []
    if paper_ids is not None:
        known = {p.id for p in corpus.papers}
        problems += [
            f"{pid}: not in the corpus (nothing to verify)" for pid in paper_ids if pid not in known
        ]
    targets = [p for p in corpus.papers if paper_ids is None or p.id in paper_ids]
    if not targets:
        problems.append("no paper to verify")
        return problems
    for p in targets:
        try:
            rec = fetch_record(p.id)
        except RuntimeError as exc:
            problems.append(f"{p.id}: could not be checked ({exc}); re-run lit-verify")
            continue
        if rec is None:
            problems.append(f"{p.id}: does not exist in Europe PMC")
            continue
        ratio = difflib.SequenceMatcher(
            None, normalise(p.title), normalise(rec.get("title", ""))
        ).ratio()
        if ratio < 0.9:
            problems.append(f"{p.id}: recorded title differs from Europe PMC ({ratio:.2f})")
        if p.pmcid and rec.get("pmcid") and p.pmcid != rec.get("pmcid"):
            problems.append(f"{p.id}: recorded pmcid {p.pmcid} != Europe PMC {rec.get('pmcid')}")
        if p.id not in cards:
            continue
        path, card = cards[p.id]
        if card.source_text == "full_text":
            if not p.pmcid or p.pmcid != rec.get("pmcid"):
                problems.append(f"{path.name}: full_text card without the paper's own pmcid")
                continue
            try:
                blocks = text_blocks(full_text_markup(p.pmcid))
            except RuntimeError as exc:
                problems.append(f"{path.name}: full text unavailable ({exc}); re-run lit-verify")
                continue
            if not blocks:
                problems.append(f"{path.name}: no article body in the full text of {p.pmcid}")
                continue
        else:
            # Abstract and title are separate blocks: a quote cannot straddle them.
            blocks = text_blocks(rec.get("abstractText", "")) + text_blocks(rec.get("title", ""))
        for i, f in enumerate(card.findings, 1):
            if TAG.search(f.quote):
                problems.append(
                    f"{path.name}: finding {i} quote contains markup; copy the text only"
                )
            elif any(ord(ch) < 32 and ch not in "\t\n\r" for ch in f.quote):
                problems.append(f"{path.name}: finding {i} quote contains control characters")
            elif not quote_is_substantive(f.quote):
                problems.append(f"{path.name}: finding {i} quote is not substantive text")
            elif not quote_found(f.quote, blocks):
                problems.append(
                    f"{path.name}: finding {i} quote not found verbatim in the "
                    f"{card.source_text.replace('_', ' ')} ({f.location})"
                )
        time.sleep(0.2)
    return problems


# ---------------------------------------------------------------------------------------------
# Citation chasing (OpenAlex, CC0). A thesis bibliography is built backwards (what a core paper
# cites) and forwards (who cites it, e.g. who re-used GSE104288). OpenAlex works are resolved
# to Europe PMC ids so they enter the corpus through `add_papers` like any other hit.
# ---------------------------------------------------------------------------------------------

OPENALEX = "https://api.openalex.org"
MAILTO = "frda-mito-signatures@users.noreply.github.com"


def _openalex(path: str, params: dict[str, str]) -> Any:
    params = {**params, "mailto": MAILTO}
    key = os.environ.get("OPENALEX_API_KEY")  # environment secret; never logged or committed
    if key:
        params["api_key"] = key
    return _get(f"{OPENALEX}/{path}?{urllib.parse.urlencode(params)}")


def _openalex_work_id(paper: Paper) -> str:
    src, ext = paper.id.split(":", 1)
    if src == "MED":
        ref = f"pmid:{ext}"
    elif paper.doi:
        ref = f"doi:{paper.doi}"
    else:
        raise RuntimeError(f"{paper.id}: no PMID or DOI to find it in OpenAlex")
    work = _openalex(f"works/{ref}", {"select": "id"})
    return str(work["id"]).rsplit("/", 1)[-1]


def _epmc_id(work: dict[str, Any]) -> str | None:
    ids = work.get("ids") or {}
    if ids.get("pmid"):
        return "MED:" + str(ids["pmid"]).rstrip("/").rsplit("/", 1)[-1]
    doi = (ids.get("doi") or "").replace("https://doi.org/", "")
    if doi:
        q = urllib.parse.quote(f'DOI:"{doi}"')
        res = _get(f"{BASE}/search?query={q}&format=json&resultType=lite")
        hits = res.get("resultList", {}).get("result", [])
        if hits:
            return pid_of(hits[0])
    return None


def citations(pid: str, direction: str, max_hits: int = 500, root: Path | None = None) -> dict:
    """Works citing (`cited-by`) or cited by (`references`) a corpus paper, resolved to Europe
    PMC ids. Returns a log dict like `search` (kind "citations"); unresolved works are listed,
    never guessed."""
    if direction not in {"cited-by", "references"}:
        raise ValueError("direction must be cited-by or references")
    paper = load_corpus(root).get(pid)
    if paper is None:
        raise RuntimeError(f"{pid}: add it to the corpus first (frda lit-add)")
    wid = _openalex_work_id(paper)
    select = "id,ids,display_name,publication_year"
    works: list[dict[str, Any]] = []
    if direction == "cited-by":
        cursor = "*"
        while cursor and len(works) < max_hits:
            page = _openalex(
                "works",
                {"filter": f"cites:{wid}", "per-page": "200", "cursor": cursor, "select": select},
            )
            works += page.get("results", [])
            cursor = (page.get("meta") or {}).get("next_cursor")
            if not page.get("results"):
                break
    else:
        refs = _openalex(f"works/{wid}", {"select": "referenced_works"}).get("referenced_works", [])
        refs = [r.rsplit("/", 1)[-1] for r in refs][:max_hits]
        for i in range(0, len(refs), 50):
            page = _openalex(
                "works",
                {
                    "filter": "openalex_id:" + "|".join(refs[i : i + 50]),
                    "per-page": "50",
                    "select": select,
                },
            )
            works += page.get("results", [])
    results, unresolved = [], []
    for w in works:
        epmc = _epmc_id(w)
        entry = {
            "openalex": str(w.get("id", "")).rsplit("/", 1)[-1],
            "title": w.get("display_name") or "",
            "year": w.get("publication_year"),
        }
        (results if epmc else unresolved).append({**entry, "id": epmc} if epmc else entry)
        time.sleep(0.1)
    return {
        "kind": "citations",
        "source": "openalex",
        "query": f"{direction} {pid} (OpenAlex {wid})",
        "date": dt.date.today().isoformat(),
        "hit_count": len(works),
        "retrieved": len(results),
        "results": results,
        "unresolved": unresolved,
    }


def card_path(pid: str, root: Path | None = None) -> Path:
    return (root or paths.ROOT) / "research" / "cards" / card_filename(pid)
