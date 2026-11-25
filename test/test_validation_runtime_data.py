"""Locating, downloading, and bundling the rule catalogs and ontology facts."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from sbol_utilities.validation import runtime_data

PREFIX = f"SBOLTestSuite-{runtime_data.SBOL_TEST_SUITE_COMMIT}/"


def archive(files: dict[str, str]) -> bytes:
    """A zip archive laid out like GitHub's archive of the pinned commit."""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zipped:
        for name, text in files.items():
            zipped.writestr(PREFIX + name, text)
    return payload.getvalue()


@pytest.fixture
def served(monkeypatch):
    """Serve the given bytes in place of the SBOLTestSuite archive."""

    def serve(payload: bytes) -> None:
        monkeypatch.setattr(runtime_data.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(payload))

    return serve


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A directory holding the runtime files, like an SBOLTestSuite checkout."""
    root = tmp_path / "checkout"
    for name in runtime_data.RUNTIME_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(f"checkout copy of {name}")
    return root


def test_download_extracts_requested_directories(tmp_path, served):
    served(archive({"Rules/a.json": "a", "Ontology/b.tsv": "b", "SBOL3/c.ttl": "c", "README.md": "readme"}))
    destination = tmp_path / "cache" / "suite"
    runtime_data.download(destination, ("Rules", "Ontology"))
    assert sorted(p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()) == [
        "Ontology/b.tsv",
        "Rules/a.json",
    ]
    assert [p.name for p in destination.parent.iterdir()] == ["suite"]


def test_download_ignores_paths_that_escape_the_destination(tmp_path, served):
    served(archive({"Rules/../../escaped.txt": "x", "Rules/kept.json": "kept"}))
    destination = tmp_path / "cache" / "suite"
    runtime_data.download(destination, ("Rules",))
    assert (destination / "Rules" / "kept.json").read_text() == "kept"
    assert not list(tmp_path.rglob("escaped.txt"))


def test_download_fills_an_existing_destination(tmp_path, served):
    destination = tmp_path / "suite"
    (destination / "Rules").mkdir(parents=True)
    (destination / "Rules" / "old.json").write_text("old")
    served(archive({"Rules/new.json": "new"}))
    runtime_data.download(destination, ("Rules",))
    assert (destination / "Rules" / "old.json").read_text() == "old"
    assert (destination / "Rules" / "new.json").read_text() == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["suite"]


def test_download_reports_a_malformed_archive(tmp_path, served):
    served(b"<html>rate limited</html>")
    with pytest.raises(runtime_data.DataUnavailable, match="zip archive"):
        runtime_data.download(tmp_path / "suite")
    assert not list(tmp_path.iterdir())


def test_download_reports_a_network_failure(tmp_path, monkeypatch):
    def unreachable(*args, **kwargs):
        raise OSError("network unreachable")

    monkeypatch.setattr(runtime_data.urllib.request, "urlopen", unreachable)
    with pytest.raises(runtime_data.DataUnavailable, match="network unreachable"):
        runtime_data.download(tmp_path / "suite")


def test_checkout_variable_takes_precedence(monkeypatch, checkout):
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(checkout))
    assert runtime_data.runtime_root() == checkout


def test_checkout_variable_must_name_a_checkout(monkeypatch, tmp_path):
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(tmp_path / "missing"))
    with pytest.raises(runtime_data.DataUnavailable, match=runtime_data.CHECKOUT_VARIABLE):
        runtime_data.runtime_root()


def test_bundle_records_the_pinned_commit(monkeypatch, checkout, tmp_path):
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(checkout))
    destination = tmp_path / "data"
    runtime_data.bundle(destination)
    assert (destination / runtime_data.STAMP).read_text().strip() == runtime_data.SBOL_TEST_SUITE_COMMIT
    for name in runtime_data.RUNTIME_FILES:
        assert (destination / name).read_text() == f"checkout copy of {name}"


def test_bundle_for_another_commit_is_not_used(monkeypatch, checkout, tmp_path):
    monkeypatch.delenv(runtime_data.CHECKOUT_VARIABLE, raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    stale = tmp_path / "data"
    monkeypatch.setattr(runtime_data, "PACKAGE_DATA_DIR", stale)
    for name in runtime_data.RUNTIME_FILES:
        (stale / name).parent.mkdir(parents=True, exist_ok=True)
        (stale / name).write_text("stale")
    (stale / runtime_data.STAMP).write_text("0" * 40)
    cache = runtime_data.user_cache_dir()
    for name in runtime_data.RUNTIME_FILES:
        (cache / name).parent.mkdir(parents=True, exist_ok=True)
        (cache / name).write_text("cached")
    assert runtime_data.runtime_root() == cache
    (stale / runtime_data.STAMP).write_text(runtime_data.SBOL_TEST_SUITE_COMMIT)
    assert runtime_data.runtime_root() == stale


def test_current_bundle_is_kept_without_a_checkout(monkeypatch, tmp_path):
    monkeypatch.delenv(runtime_data.CHECKOUT_VARIABLE, raising=False)
    destination = tmp_path / "data"
    for name in runtime_data.RUNTIME_FILES:
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        (destination / name).write_text("bundled")
    (destination / runtime_data.STAMP).write_text(runtime_data.SBOL_TEST_SUITE_COMMIT)

    def no_network(*args, **kwargs):
        raise AssertionError("bundling a current directory must not download")

    monkeypatch.setattr(runtime_data.urllib.request, "urlopen", no_network)
    runtime_data.bundle(destination)
    assert (destination / runtime_data.RUNTIME_FILES[0]).read_text() == "bundled"
