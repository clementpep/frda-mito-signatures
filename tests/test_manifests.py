import io

import pytest
from pydantic import ValidationError

from frda.manifest import Manifest, load_all, load_allowlist


def test_seed_manifests_valid_and_allowlisted():
    allow = load_allowlist()
    manifests = {m.id: m for m in load_all()}
    assert {"GSE104288", "GSE145115"} <= set(manifests)
    for m in manifests.values():
        for f in m.files:
            assert allow.source_for(f.url) is not None
            assert f.sha256 and len(f.sha256) == 64


def test_gse104288_design_matches_geo_overall_design():
    m = {m.id: m for m in load_all()}["GSE104288"]
    assert len(m.group("FRDA").samples) == 18
    assert len(m.group("control").samples) == 17
    assert m.group("FRDA").independent_units == 18


def test_gse145115_replicates_are_not_independent_units():
    m = {m.id: m for m in load_all()}["GSE145115"]
    assert all(g.independent_units == 1 for g in m.groups)
    assert sum(len(g.samples) for g in m.groups) == 24


def test_sample_in_two_groups_is_rejected():
    m = {m.id: m for m in load_all()}["GSE104288"].model_dump()
    m["groups"][1]["samples"].append(m["groups"][0]["samples"][0])
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_controlled_access_is_out_of_scope():
    m = {m.id: m for m in load_all()}["GSE104288"].model_dump()
    m["access"]["level"] = "controlled"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_http_urls_rejected():
    m = {m.id: m for m in load_all()}["GSE104288"].model_dump()
    m["files"][0]["url"] = m["files"][0]["url"].replace("https://", "http://")
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


class _Resp(io.BytesIO):
    def __init__(self, body: bytes, length: int):
        super().__init__(body)
        self.headers = {"Content-Length": str(length)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_short_transfer_is_retried_not_reported_as_drift(tmp_path, monkeypatch):
    # 2026-10-31: NCBI answered 200 with 0 of 3118820 bytes about one time in two; the short
    # body used to be hashed and reported as "upstream file changed".
    from frda import acquire

    body = b"x" * 100
    answers = [_Resp(b"", 100), _Resp(body[:40], 100), _Resp(body, 100)]
    monkeypatch.setattr(acquire.urllib.request, "urlopen", lambda req, timeout: answers.pop(0))
    monkeypatch.setattr(acquire.time, "sleep", lambda s: None)
    dest = tmp_path / "f.gz"
    acquire._download("https://example.org/f.gz", dest)
    assert dest.read_bytes() == body and answers == []

    monkeypatch.setattr(acquire.urllib.request, "urlopen", lambda req, timeout: _Resp(b"", 100))
    with pytest.raises(acquire.DownloadError, match="received 0 of 100 bytes"):
        acquire._download("https://example.org/f.gz", dest)
