"""Manuscript rendering. The manuscript source (paper/manuscript.md) never
contains a hand-typed result: numbers come from claim artifacts through
tokens, and every result sentence cites the claim it rests on.

  {{C-003:/signature/log2_fc:.2f}}   value at a JSON pointer of claim C-003's artifact
  [C-003]                            citation of a claim (must exist and be verified)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from frda import paths
from frda.claims import load_ledger, resolve_pointer

TOKEN = re.compile(r"\{\{(C-\d{3}):([^:}]+)(?::([^}]+))?\}\}")
CITE = re.compile(r"\[(C-\d{3})\]")
# Statistics typed by hand instead of through a token.
HAND_TYPED = re.compile(r"(?<![{\w/])(?:p|padj|FDR|q)\s*[<=>≤]\s*\d*\.\d+", re.IGNORECASE)

SOURCE = paths.ROOT / "paper" / "manuscript.md"
BUILD = paths.ROOT / "paper" / "build" / "manuscript.md"


def render(source: Path | None = None, root: Path | None = None) -> tuple[str, list[str]]:
    root = root or paths.ROOT
    source = source or SOURCE
    text = source.read_text(encoding="utf-8")
    claims = {c.id: c for c in load_ledger(root / "evaluation" / "claims.yaml").claims}
    problems: list[str] = []
    cache: dict[str, object] = {}

    def artifact(cid: str):
        if cid not in cache:
            cache[cid] = json.loads((root / claims[cid].artifact).read_text(encoding="utf-8"))
        return cache[cid]

    def sub(m: re.Match[str]) -> str:
        cid, pointer, fmt = m.group(1), m.group(2), m.group(3) or ".3g"
        if cid not in claims:
            problems.append(f"token references unknown claim {cid}")
            return m.group(0)
        try:
            value = resolve_pointer(artifact(cid), pointer)
            return format(value, fmt)
        except (KeyError, IndexError, ValueError, TypeError, FileNotFoundError) as exc:
            problems.append(f"token {m.group(0)} unresolved ({exc})")
            return m.group(0)

    rendered = TOKEN.sub(sub, text)
    for cid in sorted(set(CITE.findall(text))):
        if cid not in claims:
            problems.append(f"citation of unknown claim {cid}")
        elif not claims[cid].verified_by:
            problems.append(f"cites {cid}, which has not passed verification")
    stripped = TOKEN.sub("", text)
    for m in HAND_TYPED.finditer(stripped):
        problems.append(f"hand-typed statistic {m.group(0)!r}: use a claim token")
    return rendered, problems


def build(root: Path | None = None) -> list[str]:
    rendered, problems = render(root=root)
    BUILD.parent.mkdir(parents=True, exist_ok=True)
    BUILD.write_text(rendered, encoding="utf-8")
    return problems
