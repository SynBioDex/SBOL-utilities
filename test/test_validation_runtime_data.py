"""Locating, downloading, and bundling the rule catalogs and ontology facts."""

from __future__ import annotations

import hashlib
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
        """Make every download return ``payload``."""
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
    """Only the requested directories are extracted, and nothing else is left behind."""
    served(archive({"Rules/a.json": "a", "Ontology/b.tsv": "b", "SBOL3/c.ttl": "c", "README.md": "readme"}))
    destination = tmp_path / "cache" / "suite"
    runtime_data.download(destination, ("Rules", "Ontology"))
    assert sorted(p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()) == [
        "Ontology/b.tsv",
        "Rules/a.json",
    ]
    assert [p.name for p in destination.parent.iterdir()] == ["suite"]


def test_download_ignores_paths_that_escape_the_destination(tmp_path, served):
    """An archive member with ``..`` in its path is not written."""
    served(archive({"Rules/../../escaped.txt": "x", "Rules/kept.json": "kept"}))
    destination = tmp_path / "cache" / "suite"
    runtime_data.download(destination, ("Rules",))
    assert (destination / "Rules" / "kept.json").read_text() == "kept"
    assert not list(tmp_path.rglob("escaped.txt"))


def test_download_fills_an_existing_destination(tmp_path, served):
    """A download adds to a destination that already exists."""
    destination = tmp_path / "suite"
    (destination / "Rules").mkdir(parents=True)
    (destination / "Rules" / "old.json").write_text("old")
    served(archive({"Rules/new.json": "new"}))
    runtime_data.download(destination, ("Rules",))
    assert (destination / "Rules" / "old.json").read_text() == "old"
    assert (destination / "Rules" / "new.json").read_text() == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["suite"]


def test_download_reports_a_malformed_archive(tmp_path, served):
    """A payload that is not a zip archive raises DataUnavailable and leaves nothing behind."""
    served(b"<html>rate limited</html>")
    with pytest.raises(runtime_data.DataUnavailable, match="zip archive"):
        runtime_data.download(tmp_path / "suite")
    assert not list(tmp_path.iterdir())


def test_download_reports_a_network_failure(tmp_path, monkeypatch):
    """A network failure raises DataUnavailable."""

    def unreachable(*args, **kwargs):
        """Stand in for ``urlopen`` on a machine with no network."""
        raise OSError("network unreachable")

    monkeypatch.setattr(runtime_data.urllib.request, "urlopen", unreachable)
    with pytest.raises(runtime_data.DataUnavailable, match="network unreachable"):
        runtime_data.download(tmp_path / "suite")


def test_checkout_variable_takes_precedence(monkeypatch, checkout):
    """A configured checkout is used before bundled or cached data."""
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(checkout))
    assert runtime_data.runtime_root() == checkout


def test_checkout_variable_must_name_a_checkout(monkeypatch, tmp_path):
    """A configured checkout that does not exist is an error."""
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(tmp_path / "missing"))
    with pytest.raises(runtime_data.DataUnavailable, match=runtime_data.CHECKOUT_VARIABLE):
        runtime_data.runtime_root()


def test_bundle_records_the_pinned_commit(monkeypatch, checkout, tmp_path):
    """Bundling copies the data files and stamps them with the pinned commit."""
    monkeypatch.setenv(runtime_data.CHECKOUT_VARIABLE, str(checkout))
    destination = tmp_path / "data"
    runtime_data.bundle(destination)
    assert (destination / runtime_data.STAMP).read_text().strip() == runtime_data.SBOL_TEST_SUITE_COMMIT
    for name in runtime_data.RUNTIME_FILES:
        assert (destination / name).read_text() == f"checkout copy of {name}"


def test_bundle_for_another_commit_is_not_used(monkeypatch, checkout, tmp_path):
    """Bundled data stamped with another commit is passed over for the cache."""
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
    """Bundling over data already at the pinned commit downloads nothing."""
    monkeypatch.delenv(runtime_data.CHECKOUT_VARIABLE, raising=False)
    destination = tmp_path / "data"
    for name in runtime_data.RUNTIME_FILES:
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        (destination / name).write_text("bundled")
    (destination / runtime_data.STAMP).write_text(runtime_data.SBOL_TEST_SUITE_COMMIT)

    def no_network(*args, **kwargs):
        """Fail the test if anything is downloaded."""
        raise AssertionError("bundling a current directory must not download")

    monkeypatch.setattr(runtime_data.urllib.request, "urlopen", no_network)
    runtime_data.bundle(destination)
    assert (destination / next(iter(runtime_data.RUNTIME_FILES))).read_text() == "bundled"


@pytest.fixture
def raw_files(monkeypatch):
    """Serve the given content for every runtime file URL, recording the URLs requested."""
    requested: list[str] = []

    def serve(content: dict[str, bytes]) -> list[str]:
        """Serve each data file's content by URL, returning the list that records requested URLs."""

        def urlopen(url, **kwargs):
            """Record the URL and return the content of the file it names."""
            requested.append(url)
            return io.BytesIO(content[url[len(runtime_data.RAW_URL) :]])

        monkeypatch.setattr(runtime_data.urllib.request, "urlopen", urlopen)
        return requested

    return serve


def test_fetch_runtime_files_verifies_checksums(monkeypatch, tmp_path, raw_files):
    """Each data file is requested by name and stored when its checksum matches."""
    content = {name: f"content of {name}".encode() for name in runtime_data.RUNTIME_FILES}
    checksums = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
    monkeypatch.setattr(runtime_data, "RUNTIME_FILES", checksums)
    requested = raw_files(content)
    runtime_data.fetch_runtime_files(tmp_path / "cache")
    assert requested == [runtime_data.RAW_URL + name for name in checksums]
    assert all((tmp_path / "cache" / name).read_bytes() == data for name, data in content.items())


def test_fetch_runtime_files_rejects_unexpected_content(tmp_path, raw_files):
    """Content with the wrong checksum raises DataUnavailable and stores nothing."""
    raw_files({name: b"tampered" for name in runtime_data.RUNTIME_FILES})
    with pytest.raises(runtime_data.DataUnavailable, match="SHA-256"):
        runtime_data.fetch_runtime_files(tmp_path / "cache")
    assert not [path for path in (tmp_path / "cache").rglob("*") if path.is_file()]


def test_checksums_describe_the_pinned_commit():
    """The recorded checksums are those of the runtime files at the pinned commit, when a checkout at it is at hand."""
    configured = runtime_data.os.environ.get(runtime_data.CHECKOUT_VARIABLE)
    checkout = Path(configured).expanduser() if configured else None
    if checkout is None or runtime_data.checkout_revision(checkout) != runtime_data.SBOL_TEST_SUITE_COMMIT:
        pytest.skip("no SBOLTestSuite checkout at the pinned commit")
    for name, expected in runtime_data.RUNTIME_FILES.items():
        content = (checkout / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == expected, name
