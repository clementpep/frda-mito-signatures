"""News for non-specialists: the gate must stop overselling before anything is announced."""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
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


def ledger(root, level="single_dataset", extra=()):
    """C-001 at `level`, plus (id, level) pairs in `extra`."""
    cs = [_claim("C-001", level)] + [_claim(i, lv) for i, lv in extra]
    (root / "evaluation").mkdir(exist_ok=True)
    (root / "evaluation" / "claims.yaml").write_text(yaml.safe_dump({"claims": cs}))


def _claim(cid, level):
    return dict(
        id=cid,
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


def test_evidence_ceiling_uses_the_weakest_of_several_claims(tmp_path):
    ledger(tmp_path, level="replicated", extra=[("C-002", "exploratory")])
    item(tmp_path, claims=["C-001", "C-002"], evidence="single_dataset")
    probs = news.problems(tmp_path)
    assert len(probs) == 1 and "weakest claim C-002 ('exploratory')" in probs[0]
    item(tmp_path, claims=["C-001", "C-002"], evidence="exploratory")
    assert news.problems(tmp_path) == []


@pytest.mark.parametrize("kind", ["milestone", "weekly", "project", "literature", "decision"])
def test_any_kind_stating_evidence_is_held_to_its_claims(tmp_path, kind):
    ledger(tmp_path, level="exploratory")
    item(tmp_path, kind=kind, claims=[], evidence="preregistered_confirmed")
    assert any("without any claim behind it" in p for p in news.problems(tmp_path))
    item(tmp_path, kind=kind, claims=["C-001"], evidence="preregistered_confirmed")
    assert any("stronger than its weakest claim" in p for p in news.problems(tmp_path))
    item(tmp_path, kind=kind, claims=[], evidence=None)
    assert news.problems(tmp_path) == []


OVERSELLING = [
    "Une percée",
    "des percées",
    "Cela pourrait guérir",
    "on guérira",
    "les cellules guérissent",
    "une guérison",
    "de nouveaux remèdes",
    "un remède",
    "un traitement miracle",
    "un traitement efficace",
    "Cela prouve le mécanisme",
    "Ces données prouvent",
    "la suite le prouvera",
    "c'est prouvé",
    "la preuve que",
    "la mutation cause la baisse",
    "les gènes causent",
    "un effet causé par",
    "un lien causal",
    "à cause de la mutation",
    "cela provoque",
    "une révolution",
    "ce travail révolutionne",
    "un espoir pour les personnes malades",
    "un espoir",
    "une avancée majeure",
    "soigner la maladie",
    "une thérapie",
    "un effet thérapeutique",
    "un nouveau médicament",
    "cela démontre",
    "c'est démontré",
    "l'étude établit",
    "un résultat validé",
    "un résultat répliqué",
    "le gène est responsable de la baisse",
    "cela entraîne une baisse",
    "this proves it",
    "a cure",
    "it causes",
    "a new therapy",
    "a breakthrough",
    "this demonstrates",
]


@pytest.mark.parametrize("phrase", OVERSELLING)
def test_each_overselling_form_is_refused(tmp_path, phrase):
    ledger(tmp_path)
    item(tmp_path, body=BODY.replace("Vérifier dans", phrase + ". Vérifier dans"))
    assert any("forbidden wording" in p for p in news.problems(tmp_path)), phrase


@pytest.mark.parametrize(
    "phrase",
    [
        "une approche éprouvée",
        "approuvé",
        "soigneusement",
        "une démonstration à venir",
        "le responsable du projet valide la publication",
        "une validation à venir",
    ],
)
def test_innocent_words_pass(tmp_path, phrase):
    ledger(tmp_path)
    item(tmp_path, body=BODY.replace("Vérifier dans", phrase + ". Vérifier dans"))
    assert news.problems(tmp_path) == [], phrase


LIMITS = "**Ce que ça ne veut pas dire**\n"


@pytest.mark.parametrize(
    "phrase",
    [
        # Affirmed despite a nearby negation: must never pass.
        "Pas de preuve mais cela prouve le mécanisme",
        "Il n'y a pas de doute que ça guérit",
        "Ce n'est pas tout : cela prouve le mécanisme",
        "Pas de doute, une percée",
        "Sans hésiter, un remède",
        "No doubt this is a cure",
        # Negated: refused too (no exception, the limits are written without banned words).
        "Cela ne prouve pas de mécanisme",
        "Ce n’est pas un remède",
        "Il n'y a aucune guérison",
        "This is not a cure",
    ],
)
def test_banned_words_are_refused_even_near_a_negation(tmp_path, phrase):
    ledger(tmp_path)
    item(tmp_path, body=BODY.replace(LIMITS, LIMITS + phrase + ". "))
    assert any("forbidden wording" in p for p in news.problems(tmp_path)), phrase


def test_decomposed_accents_do_not_bypass_the_stems(tmp_path):
    ledger(tmp_path)
    decomposed = "cela gue\u0301rit et c'est de\u0301montre\u0301"
    item(tmp_path, body=BODY.replace("Vérifier dans", decomposed + ". Vérifier dans"))
    probs = " | ".join(news.problems(tmp_path))
    assert "'guérit'" in probs and "'démontré'" in probs


def test_each_banned_word_is_reported_once(tmp_path):
    ledger(tmp_path)
    item(tmp_path, body=BODY.replace("Vérifier dans", "Le gène cause la baisse. Vérifier dans"))
    assert sum("'cause'" in p for p in news.problems(tmp_path)) == 1


def test_overselling_in_the_title_is_refused(tmp_path):
    ledger(tmp_path)
    item(tmp_path, title="Une percée sur l'ataxie de Friedreich")
    assert any("percée" in p for p in news.problems(tmp_path))


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


def test_announce_sends_and_never_prints_the_token(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(REPO / "scripts"))
    import announce_news

    ledger(tmp_path)
    item(tmp_path)
    path = tmp_path / "research/news/N-20261020-fxn.md"
    monkeypatch.setattr(announce_news, "added_news", lambda before, after: [path])
    monkeypatch.setenv("FRDA_TELEGRAM_BOT_TOKEN", "123:SECRET-TOKEN")
    monkeypatch.setenv("FRDA_TELEGRAM_CHAT_ID", "42")
    sent = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        sent.append((req.full_url, json.loads(req.data)))
        return Resp(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(announce_news.urllib.request, "urlopen", fake_urlopen)
    assert announce_news.main("a", "b") == 0
    ((url, payload),) = sent
    assert url.endswith("/bot123:SECRET-TOKEN/sendMessage") and payload["chat_id"] == "42"
    assert payload["text"].startswith("🧬 Recherche FRDA — FXN moins actif")
    out = capsys.readouterr().out
    assert "N-20261020-fxn -> sent" in out and "SECRET" not in out

    def failing(req, timeout):
        raise OSError("network down for https://api.telegram.org/bot123:SECRET-TOKEN/x")

    monkeypatch.setattr(announce_news.urllib.request, "urlopen", failing)
    assert announce_news.main("a", "b") == 0
    out = capsys.readouterr().out
    assert "::warning::" in out and "not announced" in out and "SECRET" not in out


def test_announce_survives_an_unreadable_item(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(REPO / "scripts"))
    import announce_news

    bad = tmp_path / "N-20261020-bad.md"
    bad.write_text("---\nid: nope\n---\nbody")
    monkeypatch.setattr(announce_news, "added_news", lambda before, after: [bad])
    assert announce_news.main("a", "b") == 0
    assert "::warning::" in capsys.readouterr().out
