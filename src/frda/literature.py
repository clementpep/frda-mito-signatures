"""Europe PMC client for the literature work (allowlisted source `europe-pmc`).

- `search`  reproducible query → search log (research/search-logs/) + candidate ids
- `add`     append papers to the corpus as `to_screen`, with metadata from Europe PMC
- `verify`  online audit used by the verifier: every paper exists with the recorded
            title, and every quote of a reading card appears verbatim in the paper
            (full text for open-access papers, abstract otherwise).

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
import re
import time
import unicodedata
import urllib.parse
import urllib.request
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
    raise RuntimeError(f"Europe PMC request failed: {url}: {last}")


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
    path = d / f"{log['date']}-{slug}.json"
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
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def full_text(pmcid: str) -> str:
    """Article body only: front matter and reference list would let a quote taken from a
    cited paper's title, or from another article's abstract, pass as this paper's text."""
    xml = _get(f"{BASE}/{pmcid}/fullTextXML", as_json=False)
    m = re.search(r"<body[ >].*?</body>", xml, flags=re.S)
    return m.group(0) if m else ""


MIN_QUOTE_CHARS = 20


def quote_is_substantive(quote: str) -> bool:
    return sum(ch.isalnum() for ch in normalise(quote)) >= MIN_QUOTE_CHARS


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
        rec = fetch_record(p.id)
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
            haystack = normalise(full_text(p.pmcid))
            if not haystack:
                problems.append(f"{path.name}: no article body in the full text of {p.pmcid}")
                continue
        else:
            haystack = normalise(rec.get("abstractText", "") + " " + rec.get("title", ""))
        for i, f in enumerate(card.findings, 1):
            needle = normalise(f.quote).strip(' ".')
            if not quote_is_substantive(needle):
                problems.append(f"{path.name}: finding {i} quote is not substantive text")
            elif needle not in haystack:
                problems.append(
                    f"{path.name}: finding {i} quote not found verbatim in the "
                    f"{card.source_text.replace('_', ' ')} ({f.location})"
                )
        time.sleep(0.2)
    return problems


def card_path(pid: str, root: Path | None = None) -> Path:
    return (root or paths.ROOT) / "research" / "cards" / card_filename(pid)
