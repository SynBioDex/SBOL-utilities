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

A test marked ``@pytest.mark.corpus("<name>")`` runs once per item of that corpus (see :data:`CORPORA`), receiving the
item as its ``path`` argument (or the argument the marker names with ``argname=``).

Run ``python test/sboltestsuite.py`` to populate the cache ahead of time.
"""

from __future__ import annotations

import json
import os
import re
import sys
import warnings
from collections.abc import Callable
from functools import cache, partial
from pathlib import Path
from typing import Any

import pytest

from sbol_utilities.validation.runtime_data import SBOL_TEST_SUITE_COMMIT as COMMIT
from sbol_utilities.validation.runtime_data import DataUnavailable, checkout_revision, download

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "sboltestsuite" / COMMIT

#: Corpus directories used by the tests
SBOL2_CORPORA = ("SBOL2", "SBOL2_bp", "SBOL2_ic", "SBOL2_nc")
SBOL2_INVALID = "InvalidFiles"
SBOL3_CORPUS = "SBOL3"
SBOL3_INVALID = "SBOL3_InvalidFiles"
EXPECTED = "Expected"
DIRECTORIES = SBOL2_CORPORA + (SBOL2_INVALID, SBOL3_CORPUS, SBOL3_INVALID, EXPECTED, "Rules", "Ontology")


class SuiteUnavailable(RuntimeError):
    """The corpus is neither configured nor downloadable."""


def required() -> bool:
    """Whether a missing corpus should fail tests instead of skipping them."""
    return os.environ.get("SBOL_TEST_SUITE_REQUIRED", "").lower() not in ("", "0", "false", "no", "off")


@cache
def _located() -> Path | SuiteUnavailable:
    """The corpus directory, or why there is none; decided once per process."""
    configured = os.environ.get("SBOL_TEST_SUITE_DIR")
    if configured:
        path = Path(configured).expanduser()
        if not (path / SBOL3_INVALID).is_dir() or not (path / EXPECTED).is_dir():
            return SuiteUnavailable(f"SBOL_TEST_SUITE_DIR={configured} lacks {SBOL3_INVALID}/ or {EXPECTED}/")
        revision = checkout_revision(path)
        if revision and revision != COMMIT:
            warnings.warn(f"SBOL_TEST_SUITE_DIR is at {revision}; the tests are pinned to {COMMIT}")
        return path
    if not CACHE_DIR.is_dir():
        try:
            download(CACHE_DIR, DIRECTORIES)
        except DataUnavailable as error:
            return SuiteUnavailable(str(error))
    return CACHE_DIR


def suite_root() -> Path:
    """Directory holding the SBOLTestSuite corpus, downloading the pinned archive on first use.

    :raises SuiteUnavailable: when the corpus is neither configured nor downloadable
    """
    located = _located()
    if isinstance(located, SuiteUnavailable):
        raise located
    return located


@cache
def load_json(relative: str) -> Any:
    """The parsed content of a JSON file of the suite, by suite-relative path."""
    return json.loads((suite_root() / relative).read_text(encoding="utf-8"))


def relative_name(path: Path) -> str:
    """Suite-relative name of a fixture, the key used in Expected/ and in test ids."""
    return path.relative_to(suite_root()).as_posix()


def sbol2_files(corpus: str) -> list[Path]:
    """Sorted RDF/XML files of one SBOL 2 corpus directory."""
    return sorted((suite_root() / corpus).glob("*.xml"))


def sbol3_manifest() -> list[Path]:
    """Every valid SBOL 3 file: the Turtle serialization of each SBOL3 test case and validation example."""
    return sorted((suite_root() / SBOL3_CORPUS).rglob("*.ttl"))


def sbol3_invalid_files() -> list[Path]:
    """SBOL 3 files that each violate the rule they are named after."""
    return sorted((suite_root() / SBOL3_INVALID).glob("*.ttl"))


#: name used with ``@pytest.mark.corpus`` -> the files (or, for ``expected-issues``, the suite-relative names) a test
#: marked with it runs over
CORPORA: dict[str, Callable[[], list]] = {
    **{corpus: partial(sbol2_files, corpus) for corpus in SBOL2_CORPORA},
    "SBOL2-all": lambda: [path for corpus in SBOL2_CORPORA for path in sbol2_files(corpus)],
    SBOL2_INVALID: partial(sbol2_files, SBOL2_INVALID),
    SBOL3_CORPUS: sbol3_manifest,
    SBOL3_INVALID: sbol3_invalid_files,
    "SBOL3/validation_examples": lambda: sorted((suite_root() / SBOL3_CORPUS / "validation_examples").glob("*.ttl")),
    "expected-issues": lambda: sorted(load_json(f"{EXPECTED}/validation/issues.json")["files"]),
}


def corpus_params(name: str) -> list:
    """pytest parameters for the items of a corpus, safe to call at collection time.

    When the suite is unavailable this is a single placeholder, which the ``sbol_test_suite`` fixture skips or,
    under SBOL_TEST_SUITE_REQUIRED, fails.
    """
    try:
        items = CORPORA[name]()
    except SuiteUnavailable:
        return [pytest.param(None, id="sboltestsuite-unavailable")]
    return [pytest.param(item, id=relative_name(item) if isinstance(item, Path) else item) for item in items]


_RULE_FILE = re.compile(r"(sbol3?)-(\d{5})(?:_.*)?\.(?:xml|ttl)")


def rule_for(path: Path) -> str:
    """The rule an invalid file is named after: ``sbol-NNNNN[_case].xml`` violates ``sbol2-NNNNN`` and
    ``sbol3-NNNNN_case.ttl`` violates ``sbol3-NNNNN``.

    :raises ValueError: when the file is not named after a rule
    """
    match = _RULE_FILE.fullmatch(path.name)
    if match is None:
        raise ValueError(f"{path.name} is not named after a validation rule")
    return f"{'sbol2' if match.group(1) == 'sbol' else 'sbol3'}-{match.group(2)}"


def set_diff(expected: set, actual: set, limit: int = 40) -> str:
    """How two sets differ, as text listing up to ``limit`` items of each side ('' when they are equal)."""
    lines: list[str] = []
    for label, items in (("expected only", expected - actual), ("actual only", actual - expected)):
        if items:
            lines.append(f"{label} ({len(items)}):")
            lines.extend(f"  {item}" for item in sorted(map(str, items))[:limit])
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        print(suite_root())
    except SuiteUnavailable as error:
        print(error, file=sys.stderr)
        sys.exit(1)
