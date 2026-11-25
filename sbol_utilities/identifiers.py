"""Lexical rules for SBOL identifiers, shared by sbol_utilities.convert and sbol_utilities.validation."""

from __future__ import annotations

import re

DISPLAY_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def is_valid_display_id(text: str) -> bool:
    """Whether ``text`` is a displayId: ASCII letters, digits, and underscores, not starting with a digit."""
    return DISPLAY_ID.fullmatch(text) is not None
