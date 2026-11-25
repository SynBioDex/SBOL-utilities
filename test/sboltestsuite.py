"""Locate (and if needed download) the SynBioDex/SBOLTestSuite conformance corpus.

SBOLTestSuite is the cross-implementation corpus published by the SBOL standards body: valid and invalid SBOL 2 and
SBOL 3 files, the validation issues and conversions each file is expected to produce (``Expected/``), and the rule
catalogs and ontology facts validators use. The tests use the commit sbol-utilities pins
(:data:`sbol_utilities.validation.runtime_data.SBOL_TEST_SUITE_COMMIT`) and never copy the corpus into this
repository: it is read from ``$SBOL_TEST_SUITE_DIR`` when that points at a checkout, otherwise fetched once from
GitHub into ``.cache/sboltestsuite/<commit>/`` at the repository root (gitignored).

Environment:

* ``SBOL_TEST_SUITE_DIR`` -- use this checkout instead of the cache. It should be at the pinned commit; a different
  revision is used as-is, with a warning.
* ``SBOL_TEST_SUITE_REQUIRED=1`` -- fail rather than skip when the corpus cannot be found or downloaded (set in CI).

Run ``python test/sboltestsuite.py`` to populate the cache ahead of time.
"""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import pytest

from sbol_utilities.validation.runtime_data import SBOL_TEST_SUITE_COMMIT as COMMIT
from sbol_utilities.validation.runtime_data import DataUnavailable, download

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "sboltestsuite" / COMMIT

#: Corpus directories used by the tests
SBOL2_CORPORA = ("SBOL2", "SBOL2_bp", "SBOL2_ic", "SBOL2_nc")
SBOL2_INVALID = "InvalidFiles"
SBOL3_CORPUS = "SBOL3"
SBOL3_INVALID = "SBOL3_InvalidFiles"
EXPECTED = "Expected"
DIRECTORIES = SBOL2_CORPORA + (SBOL2_INVALID, SBOL3_CORPUS, SBOL3_INVALID, EXPECTED, "Rules", "Ontology")


#: Placeholder parameter for a parametrized test whose corpus is unavailable; the ``sbol_test_suite`` fixture
#: decides whether that case skips or fails
UNAVAILABLE = pytest.param(None, id="sboltestsuite-unavailable")


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


@lru_cache(maxsize=None)
def suite_root() -> Path:
    """Directory holding the SBOLTestSuite corpus, downloading the pinned archive on first use."""
    configured = os.environ.get("SBOL_TEST_SUITE_DIR")
    if configured:
        path = Path(configured).expanduser()
        if not (path / SBOL3_INVALID).is_dir() or not (path / EXPECTED).is_dir():
            raise SuiteUnavailable(f"SBOL_TEST_SUITE_DIR={configured} lacks {SBOL3_INVALID}/ or {EXPECTED}/")
        revision = _checkout_revision(path)
        if revision and revision != COMMIT:
            warnings.warn(f"SBOL_TEST_SUITE_DIR is at {revision}; the tests are pinned to {COMMIT}")
        return path
    if not CACHE_DIR.is_dir():
        try:
            download(CACHE_DIR, DIRECTORIES)
        except DataUnavailable as error:
            raise SuiteUnavailable(str(error)) from error
    return CACHE_DIR


def sbol2_files(corpus: str) -> List[Path]:
    """Sorted RDF/XML files of one SBOL 2 corpus directory."""
    return sorted((suite_root() / corpus).glob("*.xml"))


def sbol3_manifest() -> List[Path]:
    """Every valid SBOL 3 file: the Turtle serialization of each SBOL3 test case and validation example."""
    return sorted((suite_root() / SBOL3_CORPUS).rglob("*.ttl"))


def sbol3_invalid_files() -> List[Path]:
    """SBOL 3 files that each violate the rule they are named after."""
    return sorted((suite_root() / SBOL3_INVALID).glob("*.ttl"))


def relative_name(path: Path) -> str:
    """Suite-relative name of a fixture, the key used in Expected/ and in test ids."""
    return path.relative_to(suite_root()).as_posix()


def corpus_params(files: Callable[[], Iterable[Path]]) -> list:
    """pytest parameters for corpus files, safe to call at collection time.

    When the corpus is unavailable this yields a single placeholder parameter instead of raising during collection;
    the ``sbol_test_suite`` fixture then skips that case or, under SBOL_TEST_SUITE_REQUIRED, fails it.
    """
    try:
        return [pytest.param(path, id=relative_name(path)) for path in files()]
    except SuiteUnavailable:
        return [UNAVAILABLE]


if __name__ == "__main__":
    try:
        print(suite_root())
    except SuiteUnavailable as error:
        print(error, file=sys.stderr)
        sys.exit(1)
