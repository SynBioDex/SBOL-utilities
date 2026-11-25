"""Locate the validation-rule catalogs and ontology facts, which come from SynBioDex/SBOLTestSuite.

SBOLTestSuite publishes the SBOL 2.3.0 and SBOL 3.1.0 rule catalogs (``Rules/``) and the ontology facts snapshot
(``Ontology/``) alongside its test files. sbol-utilities pins one SBOLTestSuite commit, :data:`SBOL_TEST_SUITE_COMMIT`,
and looks for those files in order:

1. the package's own ``data/`` directory, which ``setup.py`` fills when the package is built;
2. ``$SBOL_TEST_SUITE_DIR``, a checkout of SBOLTestSuite;
3. a per-user cache, downloading the pinned commit's ``Rules/`` and ``Ontology/`` the first time they are needed.

This module uses only the standard library, so ``setup.py`` can load it before any dependency is installed.
"""

from __future__ import annotations

import io
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

#: SBOLTestSuite commit providing the rule catalogs, ontology facts, and (for the tests) the conformance corpus
SBOL_TEST_SUITE_COMMIT = "0cc9183f0d856f0ef8bff8ae5992ffbab4fc8fa8"
ARCHIVE_URL = f"https://github.com/SynBioDex/SBOLTestSuite/archive/{SBOL_TEST_SUITE_COMMIT}.zip"

PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
#: Suite-relative paths of the runtime data files
RUNTIME_FILES = (
    "Rules/sbol2-rules.json",
    "Rules/sbol3-rules.json",
    "Ontology/ontology_facts.tsv",
    "Ontology/ontology_sources.tsv",
)


class DataUnavailable(RuntimeError):
    """The rule catalogs or ontology facts could not be found or downloaded."""


def user_cache_dir() -> Path:
    """Per-user cache directory for downloaded SBOLTestSuite files."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "sbol-utilities" / "sboltestsuite" / SBOL_TEST_SUITE_COMMIT


def download(destination: Path, directories: Optional[tuple] = None) -> None:
    """Extract the pinned SBOLTestSuite archive's top-level ``directories`` (all when None) into ``destination``."""
    try:
        with urllib.request.urlopen(ARCHIVE_URL, timeout=300) as response:  # noqa: S310 (fixed https URL)
            payload = response.read()
    except OSError as error:
        raise DataUnavailable(f"Could not download SBOLTestSuite from {ARCHIVE_URL}: {error}") from error
    staging = destination.with_name(destination.name + ".partial")
    prefix = f"SBOLTestSuite-{SBOL_TEST_SUITE_COMMIT}/"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            relative = member.filename[len(prefix) :]
            if directories is not None and relative.split("/", 1)[0] not in directories:
                continue
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(destination)


def runtime_root() -> Path:
    """Directory holding ``Rules/`` and ``Ontology/``, downloading them when no other copy is available."""
    if all((PACKAGE_DATA_DIR / name).is_file() for name in RUNTIME_FILES):
        return PACKAGE_DATA_DIR
    configured = os.environ.get("SBOL_TEST_SUITE_DIR")
    if configured and all((Path(configured).expanduser() / name).is_file() for name in RUNTIME_FILES):
        return Path(configured).expanduser()
    cache = user_cache_dir()
    if not all((cache / name).is_file() for name in RUNTIME_FILES):
        download(cache, ("Rules", "Ontology"))
    return cache


def runtime_file(name: str) -> Path:
    """Path of one runtime data file, e.g. ``Rules/sbol3-rules.json``."""
    return runtime_root() / name


def bundle(destination: Path = PACKAGE_DATA_DIR) -> None:
    """Copy the runtime data files into ``destination`` (the package data directory, when building)."""
    source = runtime_root()
    if source == destination:
        return
    for name in RUNTIME_FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / name).read_bytes())
