"""News for non-specialists: the gate must stop overselling before anything is announced."""

import subprocess
import sys
from pathlib import Path

import yaml

from frda import news

from .conftest import git

REPO = Path(__file__).resolve().parents[1]

BODY = """**Ce qu'on a fait**
On a comparé l'activité des gènes chez 18 personnes malades et 17 non malades.

**Ce que ça veut dire**
Le gène FXN est moins actif chez les personnes malades, comme publié en 2017.

**Ce que ça ne veut pas dire**
Ce n'est pas un traitement et cela ne montre pas de mécanisme.

**Et ensuite**
Vérifier dans d'autres données.
"""


def item(root, name="N-20261020-fxn", body=BODY, **meta):
    m = dict(
        id=name,
        date="2026-10-20",
        kind="finding",
        title="FXN moins actif chez les malades",
        claims=["C-001"],
        tasks=["T-004"],
        evidence="single_dataset",
    )
    m.update(meta)
    d = root / "research" / "news"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text("---\n" + yaml.safe_dump(m, allow_unicode=True) + "---\n" + body)


def ledger(root, level="single_dataset"):
    c = dict(
        id="C-001",
        statement="FXN is lower in FRDA fibroblasts.",
        status="reproduced",
        evidence_level=level,
        datasets=["GSE104288"],
        task="T-004",
        artifact="results/x.json",
        checks=[{"pointer": "/x", "op": "lt", "value": 0}],
        limitations=["l"],
        source={"pmid": "1", "location": "F1", "published_value": "v"},
    )
    (root / "evaluation").mkdir(exist_ok=True)
    (root / "evaluation" / "claims.yaml").write_text(yaml.safe_dump({"claims": [c]}))


def test_seed_news_valid():
    assert news.problems() == []


def test_valid_finding_passes(tmp_path):
    ledger(tmp_path)
    item(tmp_path)
    assert news.problems(tmp_path) == []


def test_evidence_cannot_exceed_the_weakest_claim(tmp_path):
    ledger(tmp_path, level="exploratory")
    item(tmp_path, evidence="replicated")
    assert any("stronger than its weakest claim" in p for p in news.problems(tmp_path))


def test_finding_needs_claims_and_sections(tmp_path):
    ledger(tmp_path)
    item(tmp_path, claims=[], body=BODY.replace("**Ce que ça ne veut pas dire**", "**Limites**"))
    probs = " | ".join(news.problems(tmp_path))
    assert "must cite its claims" in probs and "Ce que ça ne veut pas dire" in probs


def test_overselling_words_are_refused_in_french_and_english(tmp_path):
    ledger(tmp_path)
    for i, phrase in enumerate(
        [
            "Une percée qui pourrait guérir",
            "Cela prouve le mécanisme",
            "un espoir pour les patients",
            "this proves it",
        ]
    ):
        item(
            tmp_path,
            name=f"N-20261020-x{i}",
            body=BODY.replace("Vérifier dans", phrase + ". Vérifier dans"),
        )
    assert sum("forbidden wording" in p for p in news.problems(tmp_path)) >= 4


def test_unknown_claim_and_bad_filename(tmp_path):
    ledger(tmp_path)
    item(tmp_path, claims=["C-999"])
    (tmp_path / "research/news/N-20261020-fxn.md").rename(
        tmp_path / "research/news/N-20261020-other.md"
    )
    probs = " | ".join(news.problems(tmp_path))
    assert "C-999 not in the ledger" in probs and "file name must be the news id" in probs


def test_telegram_rendering_is_plain_and_states_evidence(tmp_path):
    ledger(tmp_path)
    item(tmp_path)
    meta, body = news.load(tmp_path / "research/news/N-20261020-fxn.md")
    text = news.render_telegram(meta, body, link="https://example.org")
    assert "**" not in text and "Niveau de preuve : observé dans un seul jeu de données." in text
    assert text.startswith("🧬 Recherche FRDA — FXN moins actif")


def test_announce_only_items_added_by_the_landing(tmp_path, monkeypatch):
    ledger(tmp_path)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@e.com")
    git(tmp_path, "config", "user.name", "t")
    item(tmp_path, name="N-20261019-old")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "old")
    before = git(tmp_path, "rev-parse", "HEAD")
    item(tmp_path, name="N-20261020-new")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "new")
    after = git(tmp_path, "rev-parse", "HEAD")
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts/announce_news.py"), before, after],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO / "src")},
    )
    assert out.returncode == 0
    assert "N-20261020-new" in out.stdout and "N-20261019-old" not in out.stdout
    assert "secrets not set" in out.stdout  # no credentials in tests: nothing is sent
