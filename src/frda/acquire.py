"""Download manifest files, verify SHA-256, append a provenance record.

A checksum mismatch is a hard failure: the file is not kept. Upstream drift
(GEO re-processing a supplementary file) must be noticed, not absorbed.
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from frda import paths
from frda.hashing import sha256_file
from frda.manifest import Manifest, ManifestFile, load_allowlist

USER_AGENT = "frda-mito-signatures/0.1 (+https://github.com/clementpep/frda-mito-signatures)"


class ChecksumMismatch(RuntimeError):
    pass


def raw_path(manifest: Manifest, f: ManifestFile, raw_dir: Path | None = None) -> Path:
    return (raw_dir or paths.RAW) / manifest.id / f.name


class DownloadError(RuntimeError):
    """The transfer itself failed (cut short, network). Not evidence of upstream drift."""


RETRY_DELAYS = (2, 4, 8, 16, 32, 64)  # NCBI drops come in bursts: ~2 min in all


def _download_once(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
        expected = resp.headers.get("Content-Length")
        try:
            shutil.copyfileobj(resp, out)
        except http.client.IncompleteRead as exc:
            raise DownloadError(f"{url}: transfer cut short ({exc})") from exc
    got = dest.stat().st_size
    # NCBI's HTTPS front end drops transfers at random (seen 2026-10-31: 0 of 3118820 bytes
    # with status 200). A short body must not reach the checksum and pass for upstream drift.
    if expected is not None and got != int(expected):
        raise DownloadError(f"{url}: received {got} of {expected} bytes")


def _download(url: str, dest: Path) -> None:
    """Download with retries on transfer failures only; the checksum is checked by the caller."""
    for attempt, delay in enumerate((0, *RETRY_DELAYS)):
        time.sleep(delay)
        try:
            _download_once(url, dest)
            return
        except (DownloadError, urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == len(RETRY_DELAYS):
                raise DownloadError(f"{exc} (after {attempt + 1} attempts)") from exc


def fetch_file(
    manifest: Manifest,
    f: ManifestFile,
    *,
    raw_dir: Path | None = None,
    record: bool = False,
    force: bool = False,
    log_path: Path | None = None,
) -> tuple[Path, str]:
    """Return (path, sha256). With `record=True` an unset checksum is accepted
    (bootstrap of a new manifest); a set checksum is always enforced."""
    allow = load_allowlist()
    if allow.source_for(f.url) is None:
        raise PermissionError(f"{f.url} is not covered by data-manifests/allowlist.yaml")

    dest = raw_path(manifest, f, raw_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force and f.sha256 and sha256_file(dest) == f.sha256:
        return dest, f.sha256

    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=".part-")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        _download(f.url, tmp)
        digest = sha256_file(tmp)
        if f.sha256 is None and not record:
            raise ChecksumMismatch(
                f"{manifest.id}/{f.name}: no sha256 in manifest (run with --record-checksums "
                "once, review the diff, commit)."
            )
        if f.sha256 is not None and digest != f.sha256:
            raise ChecksumMismatch(
                f"{manifest.id}/{f.name}: sha256 {digest} != manifest {f.sha256}. "
                "Upstream file changed: do NOT update the manifest silently, open a task."
            )
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)

    entry = {
        "dataset": manifest.id,
        "file": f.name,
        "url": f.url,
        "sha256": digest,
        "size_bytes": dest.stat().st_size,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    log = log_path or paths.PROVENANCE_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return dest, digest
