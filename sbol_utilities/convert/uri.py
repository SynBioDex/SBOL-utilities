"""SBOL 2 ⇄ SBOL 3 IRI algebra and ontology-term spelling.

SBOL 2 encodes an object's version as the last path segment (``<prefix>/<displayId>/<version>``); SBOL 3 places it
before the displayId (``<prefix>/<version>/<displayId>``). The conversion recomputes identities by decomposing an IRI
into namespace, version, and displayId and reassembling them for the target version, exactly as the
SynBioDex/SBOL-Converter reference (``createSBOL3Uri`` / ``createSBOL2Uri``) and sbol-rs do.

A segment counts as a version when it is empty or a leading ASCII digit followed by letters, digits, ``_``, ``.``,
or ``-``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from itertools import count
from typing import NamedTuple


def is_version_valid(segment: str) -> bool:
    """Whether ``segment`` is a valid SBOL version: empty, or a leading ASCII digit then word characters."""
    if not segment:
        return True
    if not ("0" <= segment[0] <= "9"):
        return False
    return all(c.isalnum() or c in "_.-" for c in segment)


# SBOL 3 IRI decomposition: <prefix>/<version>/<displayId>


def display_id_sbol3(uri: str) -> str:
    """The final path segment of an SBOL 3 IRI (``""`` when there is no ``/``)."""
    i = uri.rfind("/")
    return uri[i + 1 :] if i >= 0 else ""


def version_sbol3(uri: str) -> str:
    """The version segment immediately before the displayId, or ``""`` when absent or not version-shaped."""
    last = uri.rfind("/")
    if last < 0:
        return ""
    second_last = uri.rfind("/", 0, last)
    if second_last < 0:
        return ""
    version = uri[second_last + 1 : last]
    return version if is_version_valid(version) else ""


def namespace_sbol3(uri: str) -> str:
    """The IRI minus its displayId, and minus its version segment when one is present."""
    version = version_sbol3(uri)
    last = uri.rfind("/")
    if last < 0:
        return ""
    namespace = uri[:last]
    if not version:
        return namespace
    second_last = namespace.rfind("/")
    return namespace[:second_last] if second_last >= 0 else ""


# SBOL 2 IRI decomposition: <prefix>/<displayId>/<version>


class Sbol2Iri(NamedTuple):
    """The parts of an SBOL 2 identity."""

    #: the IRI minus its displayId and, when present, its version
    prefix: str
    display_id: str
    #: the last segment when it is version-shaped, otherwise ``""``
    version: str

    @classmethod
    def parse(cls, iri: str) -> Sbol2Iri | None:
        """Decompose an IRI, or None for one the reference treats as non-decomposable: empty, ending in ``/``, or
        without any ``/``.

        An IRI whose only segment after the first ``/`` is version-shaped keeps the whole IRI as both prefix and
        displayId, as the reference does.
        """
        last = iri.rfind("/")
        if not iri or iri.endswith("/") or last < 0:
            return None
        segment = iri[last + 1 :]
        if not is_version_valid(segment):
            return cls(iri[:last], segment, "")
        second_last = iri.rfind("/", 0, last)
        if second_last < 0:
            return cls(iri, iri, segment)
        return cls(iri[:second_last], iri[second_last + 1 : last], segment)


def version_sbol2(uri: str) -> str | None:
    """The version segment, ``""`` when the last segment is not version-shaped, None when not decomposable."""
    parts = Sbol2Iri.parse(uri)
    return None if parts is None else parts.version


def display_id_sbol2(uri: str) -> str | None:
    """The segment before the version when the IRI is versioned, otherwise the last segment."""
    parts = Sbol2Iri.parse(uri)
    return None if parts is None else parts.display_id


def uri_prefix_sbol2(uri: str) -> str | None:
    """The IRI minus its displayId (and version, when present)."""
    parts = Sbol2Iri.parse(uri)
    return None if parts is None else parts.prefix


def versioned(persistent_identity: str, version: str | None) -> str:
    """The SBOL 2 identity ``<persistentIdentity>/<version>``, or the persistentIdentity itself without a version."""
    return persistent_identity if version is None else f"{persistent_identity}/{version}"


def without_version(iri: str, version: str | None) -> str:
    """``iri`` minus a trailing ``/<version>``, when it has that version and ends with it."""
    return iri[: -len(version) - 1] if version and iri.endswith("/" + version) else iri


# Cross-version identity construction


def create_sbol2_uri(sbol3_uri: str) -> str:
    """The SBOL 2 IRI ``<namespace>/<displayId>[/<version>]`` for an SBOL 3 IRI; non-decomposable input is returned."""
    version = version_sbol3(sbol3_uri)
    sbol2 = f"{namespace_sbol3(sbol3_uri)}/{display_id_sbol3(sbol3_uri)}"
    if version:
        sbol2 += f"/{version}"
    return sbol3_uri if sbol2 == "/" else sbol2


def create_sbol3_uri(sbol2_uri: str) -> str:
    """The SBOL 3 IRI ``<prefix>[/<version>]/<displayId>`` for an SBOL 2 IRI; non-decomposable input is returned."""
    parts = Sbol2Iri.parse(sbol2_uri)
    if parts is None:
        return sbol2_uri
    sbol3 = parts.prefix
    if parts.version:
        sbol3 += f"/{parts.version}"
    if parts.display_id:
        sbol3 += f"/{parts.display_id}"
    return sbol3


# Ontology terms. SBOL 2 and SBOL 3 spell the same SO / SBO / EDAM terms differently; the field a term appears in
# selects the conversion, and each conversion also toggles the URI scheme (http <-> https) unconditionally, as the
# reference does. SBOL 3 spellings: https://identifiers.org/SO:<id>, .../SBO:<id>, .../edam:<id>. SBOL 2 spellings:
# http://identifiers.org/so/SO:<id>, .../biomodels.sbo/SBO:<id>, .../edam/<id>.


def _identifiers_org_path(uri: str) -> str | None:
    """Path of an identifiers.org IRI (either scheme), or None for any other IRI.

    Ontology-term spelling applies only to identifiers.org IRIs; every other IRI (a lab's own role or type
    vocabulary, for instance) is kept exactly as written.
    """
    for base in ("https://identifiers.org/", "http://identifiers.org/"):
        if uri.startswith(base):
            return uri[len(base) :]
    return None


def _respell(uri: str, old_prefix: str, new_prefix: str, scheme: str) -> str:
    """Rewrite an identifiers.org term: ``old_prefix`` (any case) becomes ``new_prefix``, with scheme ``scheme``."""
    path = _identifiers_org_path(uri)
    if path is None:
        return uri
    if path[: len(old_prefix)].lower() == old_prefix.lower():
        path = new_prefix + path[len(old_prefix) :]
    return f"{scheme}://identifiers.org/{path}"


def convert_so_2_to_3(uri: str) -> str:
    """Sequence Ontology term, SBOL 2 -> SBOL 3: drop the ``so/`` path segment."""
    return _respell(uri, "so/SO:", "SO:", "https")


def convert_so_3_to_2(uri: str) -> str:
    """Sequence Ontology term, SBOL 3 -> SBOL 2: reinstate the ``so/`` path segment."""
    return _respell(uri, "SO:", "so/SO:", "http")


def convert_sbo_2_to_3(uri: str) -> str:
    """Systems Biology Ontology term, SBOL 2 -> SBOL 3: drop ``biomodels.sbo/``."""
    return _respell(uri, "biomodels.sbo/SBO:", "SBO:", "https")


def convert_sbo_3_to_2(uri: str) -> str:
    """Systems Biology Ontology term, SBOL 3 -> SBOL 2: reinstate ``biomodels.sbo/``."""
    return _respell(uri, "SBO:", "biomodels.sbo/SBO:", "http")


def convert_edam_2_to_3(uri: str) -> str:
    """EDAM term, SBOL 2 -> SBOL 3: rewrite the ``edam/`` path segment to ``edam:``."""
    return _respell(uri, "edam/", "edam:", "https")


def convert_edam_3_to_2(uri: str) -> str:
    """EDAM term, SBOL 3 -> SBOL 2: rewrite ``edam:`` back to ``edam/``."""
    return _respell(uri, "edam:", "edam/", "http")


def component_type_2_to_3(uri: str) -> str:
    """A non-BioPAX Component type, SBOL 2 -> SBOL 3: SO terms are respelled, anything else passes through."""
    return convert_so_2_to_3(uri) if "so/so:" in uri.lower() else uri


def component_type_3_to_2(uri: str) -> str:
    """A non-BioPAX Component type, SBOL 3 -> SBOL 2: the mirror of :func:`component_type_2_to_3`."""
    return convert_so_3_to_2(uri) if "so:" in uri.lower() else uri


# Generic IRI helpers


def last_segment(iri: str) -> str:
    """The text after the last ``/``, ``#``, or ``:`` of an IRI, or the whole IRI when that would be empty."""
    split = max(iri.rfind("/"), iri.rfind("#"), iri.rfind(":"))
    return iri[split + 1 :] if 0 <= split < len(iri) - 1 else iri


def url_origin(iri: str) -> str | None:
    """``scheme://host`` of a URL, or ``urn:<nid>`` of a URN; None for anything else."""
    scheme, sep, rest = iri.partition("://")
    if sep:
        slash = rest.find("/")
        host = rest if slash < 0 else rest[:slash]
        if scheme and host:
            return f"{scheme}://{host}"
    if iri.startswith("urn:") and len(iri) > 4:
        after = iri[4:]
        ends = [i for i in (after.find(":"), after.find("/")) if i >= 0]
        nid = after[: min(ends)] if ends else after
        if nid:
            return f"urn:{nid}"
    return None


def append_segment(iri: str, segment: str) -> str:
    """``iri/segment``, without doubling a trailing ``/``."""
    return f"{iri}{segment}" if iri.endswith("/") else f"{iri}/{segment}"


def slash_join(iri: str, segment: str) -> str:
    """``iri/segment``, even when ``iri`` already ends with ``/``."""
    return f"{iri}/{segment}"


def numbered(base: str) -> Iterator[str]:
    """``base``, ``base_2``, ``base_3``, …"""
    yield base
    for n in count(2):
        yield f"{base}_{n}"


def claim_child(
    parent: str, display_ids: Iterable[str], used: set[str], join: Callable[[str, str], str] = append_segment
) -> tuple[str, str]:
    """A ``(displayId, iri)`` child of ``parent`` whose IRI is not in ``used``, adding that IRI to ``used``.

    The first of ``display_ids`` giving a free IRI is taken, so the displayId always matches the IRI's last segment.
    """
    for display_id in display_ids:
        iri = join(parent, display_id)
        if iri not in used:
            used.add(iri)
            return display_id, iri
    raise ValueError(f"no free child IRI under {parent}")
