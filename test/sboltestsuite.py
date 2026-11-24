"""Locate (and if needed download) the SynBioDex/SBOLTestSuite conformance corpus.

SBOLTestSuite is the cross-implementation corpus published by the SBOL standards body. The tests pin one commit and
never redistribute the corpus: it is read from ``$SBOL_TEST_SUITE_DIR`` when that points at a checkout, otherwise
fetched once from GitHub into ``.cache/sboltestsuite/<commit>/`` at the repository root (gitignored).

Environment:

* ``SBOL_TEST_SUITE_DIR`` -- use this checkout instead of the cache. It should be at :data:`COMMIT`; a different
  revision is used as-is, with a warning.
* ``SBOL_TEST_SUITE_REQUIRED=1`` -- fail rather than skip when the corpus cannot be found or downloaded (set in CI).

Run ``python test/sboltestsuite.py`` to populate the cache ahead of time.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import urllib.request
import warnings
import zipfile
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import pytest

#: SBOLTestSuite commit the tests are pinned to (the same commit sbol-rs pins)
COMMIT = "0044284331b2f915a6e4b9d50e1cbf3ea2f62dcd"
ARCHIVE_URL = f"https://github.com/SynBioDex/SBOLTestSuite/archive/{COMMIT}.zip"

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "sboltestsuite" / COMMIT
LOCAL_SUPPLEMENT_DIR = Path(__file__).resolve().parent / "test_files" / "sboltestsuite_local"

#: Corpus directories used by the tests
SBOL2_CORPORA = ("SBOL2", "SBOL2_bp", "SBOL2_ic", "SBOL2_nc")
SBOL2_INVALID = "InvalidFiles"
SBOL3_CORPUS = "SBOL3"
DIRECTORIES = SBOL2_CORPORA + (SBOL2_INVALID, SBOL3_CORPUS)


class SuiteUnavailable(RuntimeError):
    """The corpus is neither configured nor downloadable."""


def required() -> bool:
    """Whether a missing corpus should fail tests instead of skipping them."""
    return os.environ.get("SBOL_TEST_SUITE_REQUIRED", "") not in ("", "0", "false")


def _checkout_revision(path: Path) -> Optional[str]:
    try:
        result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _download(destination: Path) -> None:
    with urllib.request.urlopen(ARCHIVE_URL, timeout=120) as response:  # noqa: S310 (fixed https URL)
        payload = response.read()
    staging = destination.with_name(destination.name + ".partial")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        prefix = f"SBOLTestSuite-{COMMIT}/"
        for member in archive.infolist():
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            relative = member.filename[len(prefix) :]
            if relative.split("/", 1)[0] not in DIRECTORIES:
                continue
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    staging.rename(destination)


def suite_root() -> Path:
    """Directory holding the SBOLTestSuite corpora, downloading the pinned archive on first use."""
    configured = os.environ.get("SBOL_TEST_SUITE_DIR")
    if configured:
        path = Path(configured).expanduser()
        if not (path / "SBOL2").is_dir():
            raise SuiteUnavailable(f"SBOL_TEST_SUITE_DIR={configured} does not contain an SBOL2 directory")
        revision = _checkout_revision(path)
        if revision and revision != COMMIT:
            warnings.warn(f"SBOL_TEST_SUITE_DIR is at {revision}; the tests are pinned to {COMMIT}")
        return path
    if not CACHE_DIR.is_dir():
        CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        try:
            _download(CACHE_DIR)
        except Exception as error:  # network failures, bad archives
            raise SuiteUnavailable(f"Could not download SBOLTestSuite from {ARCHIVE_URL}: {error}") from error
    return CACHE_DIR


def sbol2_files(corpus: str) -> List[Path]:
    """Sorted RDF/XML files of one SBOL 2 corpus directory."""
    return sorted((suite_root() / corpus).glob("*.xml"))


def sbol3_manifest() -> List[Path]:
    """Every valid SBOL 3 fixture: the Turtle file of each SBOLTestSuite SBOL3 test case plus the local supplements.

    The local supplements cover ExperimentalData and VariableFeature, which the upstream corpus does not exercise.
    """
    corpus = sorted((suite_root() / SBOL3_CORPUS).rglob("*.ttl"))
    return corpus + sorted(LOCAL_SUPPLEMENT_DIR.glob("*.ttl"))


def relative_name(path: Path) -> str:
    """Corpus-relative name of a fixture, used as a stable key in goldens and test ids."""
    if path.parent == LOCAL_SUPPLEMENT_DIR:
        return f"repo/{LOCAL_SUPPLEMENT_DIR.name}/{path.name}"
    return path.relative_to(suite_root()).as_posix()


def corpus_params(files: Callable[[], Iterable[Path]]) -> list:
    """pytest parameters for corpus files, safe to call at collection time.

    When the corpus is unavailable this yields a single parameter that skips (or, under SBOL_TEST_SUITE_REQUIRED,
    fails) instead of raising during collection.
    """
    try:
        return [pytest.param(path, id=relative_name(path)) for path in files()]
    except SuiteUnavailable as error:
        mark = pytest.mark.xfail(strict=True, reason=str(error)) if required() else pytest.mark.skip(reason=str(error))
        return [pytest.param(None, id="sboltestsuite-unavailable", marks=mark)]


if __name__ == "__main__":
    try:
        print(suite_root())
    except SuiteUnavailable as error:
        print(error, file=sys.stderr)
        sys.exit(1)
