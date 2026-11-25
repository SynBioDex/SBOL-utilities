"""Locate the validation-rule catalogs and ontology facts, which come from SynBioDex/SBOLTestSuite.

SBOLTestSuite publishes the SBOL 2.3.0 and SBOL 3.1.0 rule catalogs (``Rules/``) and the ontology facts snapshot
(``Ontology/``) alongside its test files. sbol-utilities pins one SBOLTestSuite commit, :data:`SBOL_TEST_SUITE_COMMIT`,
and looks for those files in order:

1. ``$SBOL_TEST_SUITE_DIR``, a checkout of SBOLTestSuite, when that variable is set;
2. the package's own ``data/`` directory, which ``setup.py`` fills when the package is built, when it was filled
   for the pinned commit;
3. a per-user cache, downloading those four files of the pinned commit, and checking their SHA-256, the first time
   they are needed.

This module uses only the standard library, so ``setup.py`` can load it before any dependency is installed.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import urllib.request
import warnings
import zipfile
from collections.abc import Collection
from pathlib import Path, PurePosixPath

#: SBOLTestSuite commit providing the rule catalogs, ontology facts, and (for the tests) the conformance corpus
SBOL_TEST_SUITE_COMMIT = "708911542acc1903e66a7d3bdd775e945597611b"
ARCHIVE_URL = f"https://github.com/SynBioDex/SBOLTestSuite/archive/{SBOL_TEST_SUITE_COMMIT}.zip"

PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
#: File in a bundled data directory naming the SBOLTestSuite commit the directory was filled for
STAMP = "COMMIT"
#: Environment variable naming an SBOLTestSuite checkout to read instead of the bundled or cached files
CHECKOUT_VARIABLE = "SBOL_TEST_SUITE_DIR"
#: Suite-relative path of each runtime data file -> the SHA-256 of its content at the pinned commit
RUNTIME_FILES = {
    "Rules/sbol2-rules.json": "9d82aa81453b6649b7fdea4c1e021f9917b8c9ee79288a5761161c06d9d069e1",
    "Rules/sbol3-rules.json": "e910dcb7e6ef8348f1cac9b5d4cb9d2397a8ac567f27a8cc72d2122f03ef190b",
    "Ontology/ontology_facts.tsv": "ce289073f2c37ed8cce7b639a4c88eb47bef3a1ac7cce4d72aaccc334812b6a9",
    "Ontology/ontology_sources.tsv": "5b113467da9f7ebac788d7504130ee4f649a67705223ef4a42a79643481db16f",
}
#: Where a single file of the pinned commit is served from
RAW_URL = f"https://raw.githubusercontent.com/SynBioDex/SBOLTestSuite/{SBOL_TEST_SUITE_COMMIT}/"


class DataUnavailable(RuntimeError):
    """The rule catalogs or ontology facts could not be found or downloaded."""


def user_cache_dir() -> Path:
    """Per-user cache directory for downloaded SBOLTestSuite files."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "sbol-utilities" / "sboltestsuite" / SBOL_TEST_SUITE_COMMIT


def checkout_revision(path: Path) -> str | None:
    """The commit a git checkout is at, or None when ``path`` is not a checkout or git is unavailable."""
    try:
        result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def download(destination: Path, directories: Collection[str] | None = None) -> None:
    """Extract the pinned SBOLTestSuite archive's top-level ``directories`` (all when None) into ``destination``.

    This fetches the whole repository archive; the tests use it for the conformance corpus.

    The files are staged beside ``destination`` and moved into place once all are written, so ``destination``
    appears complete or not at all. Files already in ``destination`` are replaced.
    """
    try:
        with urllib.request.urlopen(ARCHIVE_URL, timeout=300) as response:  # noqa: S310 (fixed https URL)
            payload = response.read()
    except OSError as error:
        raise DataUnavailable(f"Could not download SBOLTestSuite from {ARCHIVE_URL}: {error}") from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".", dir=destination.parent))
    try:
        try:
            _extract(payload, staging, directories)
        except zipfile.BadZipFile as error:
            raise DataUnavailable(f"{ARCHIVE_URL} did not return a zip archive: {error}") from error
        try:
            staging.rename(destination)
        except OSError:  # the destination already holds files
            for source in sorted(path for path in staging.rglob("*") if path.is_file()):
                target = destination / source.relative_to(staging)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _extract(payload: bytes, staging: Path, directories: Collection[str] | None) -> None:
    prefix = f"SBOLTestSuite-{SBOL_TEST_SUITE_COMMIT}/"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            relative = PurePosixPath(member.filename[len(prefix) :])
            if ".." in relative.parts or (directories is not None and relative.parts[0] not in directories):
                continue
            target = staging.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))


def _has_runtime_files(root: Path) -> bool:
    return all((root / name).is_file() for name in RUNTIME_FILES)


def _configured_checkout() -> Path | None:
    """The checkout ``$SBOL_TEST_SUITE_DIR`` names, or None when the variable is unset."""
    configured = os.environ.get(CHECKOUT_VARIABLE)
    if not configured:
        return None
    root = Path(configured).expanduser()
    if not _has_runtime_files(root):
        raise DataUnavailable(f"{CHECKOUT_VARIABLE}={configured} lacks one of {', '.join(RUNTIME_FILES)}")
    return root


def _is_current_bundle(root: Path) -> bool:
    """Whether ``root`` holds the runtime files as bundled for the pinned commit."""
    stamp = root / STAMP
    return _has_runtime_files(root) and stamp.is_file() and stamp.read_text().strip() == SBOL_TEST_SUITE_COMMIT


def fetch_runtime_files(destination: Path) -> None:
    """Download each runtime data file of the pinned commit into ``destination``, checking its SHA-256.

    A file is put in place only once its content is verified, so ``destination`` never holds unverified data.

    :raises DataUnavailable: when a file cannot be downloaded or does not have the expected content
    """
    for name, expected in RUNTIME_FILES.items():
        url = RAW_URL + name
        try:
            with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (fixed https URL)
                content = response.read()
        except OSError as error:
            raise DataUnavailable(f"Could not download {url}: {error}") from error
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise DataUnavailable(f"{url} has SHA-256 {actual}; expected {expected}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.{os.getpid()}.partial")
        partial.write_bytes(content)
        os.replace(partial, target)


def _cached_root() -> Path:
    cache = user_cache_dir()
    if not _has_runtime_files(cache):
        fetch_runtime_files(cache)
    return cache


def runtime_root() -> Path:
    """Directory holding ``Rules/`` and ``Ontology/``, downloading them when no other copy is available."""
    checkout = _configured_checkout()
    if checkout is not None:
        return checkout
    if _is_current_bundle(PACKAGE_DATA_DIR):
        return PACKAGE_DATA_DIR
    return _cached_root()


def runtime_file(name: str) -> Path:
    """Path of one runtime data file, e.g. ``Rules/sbol3-rules.json``."""
    return runtime_root() / name


def bundle(destination: Path = PACKAGE_DATA_DIR) -> None:
    """Fill ``destination`` (the package data directory, when building) with the runtime data files.

    The files come from ``$SBOL_TEST_SUITE_DIR`` when it is set and from the pinned commit otherwise. A destination
    already filled for the pinned commit is left as it is unless ``$SBOL_TEST_SUITE_DIR`` is set.
    """
    checkout = _configured_checkout()
    if checkout is None:
        if _is_current_bundle(destination):
            return
        source = _cached_root()
    else:
        source = checkout
        revision = checkout_revision(checkout)
        if revision and revision != SBOL_TEST_SUITE_COMMIT:
            warnings.warn(
                f"bundling validation data from {CHECKOUT_VARIABLE} at {revision}; the pinned commit is "
                f"{SBOL_TEST_SUITE_COMMIT}"
            )
    for name in RUNTIME_FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / name).read_bytes())
    (destination / STAMP).write_text(SBOL_TEST_SUITE_COMMIT + "\n")
