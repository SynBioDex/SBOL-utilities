"""Lexical forms of the literal values the SBOL data models use, shared by the SBOL 2 and SBOL 3 validators.

Integers are limited to the signed 64-bit range, the range the reference validators hold them in, so a literal
outside it is not a valid integer value.
"""

from __future__ import annotations

import re

from rdflib import Literal

from sbol_utilities.vocab import RDF_LANG_STRING, XSD_STRING

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1

_INTEGER = re.compile(r"[+-]?[0-9]+")
_FLOAT = re.compile(r"[+-]?(?:inf|infinity|nan|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:e[+-]?[0-9]+)?)", re.IGNORECASE)
_DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?"
)


def parse_i64(text: str | None) -> int | None:
    """The integer ``text`` spells in decimal with an optional sign, or None when it is absent, malformed, or outside
    the signed 64-bit range."""
    if text is None or _INTEGER.fullmatch(text) is None:
        return None
    number = int(text)
    return number if I64_MIN <= number <= I64_MAX else None


def is_float_lexical(text: str) -> bool:
    """Whether ``text`` spells a decimal or floating-point number, including the infinities and NaN."""
    return _FLOAT.fullmatch(text) is not None


def is_date_time_lexical(text: str) -> bool:
    """Whether ``text`` has the shape of an xsd:dateTime: date, ``T``, time, optional fraction and time zone."""
    return _DATE_TIME.fullmatch(text) is not None


def literal_datatype(literal: Literal) -> str:
    """The datatype IRI RDF 1.1 gives a literal: xsd:string for a plain one, rdf:langString for a tagged one."""
    if literal.datatype is not None:
        return str(literal.datatype)
    return RDF_LANG_STRING if literal.language else XSD_STRING
