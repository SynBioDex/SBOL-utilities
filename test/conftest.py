"""Shared pytest configuration: SBOLTestSuite availability and markers."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sboltestsuite  # noqa: E402


def pytest_configure(config):
    """Register the markers used by the conformance suites."""
    config.addinivalue_line("markers", "sboltestsuite: test reads the SynBioDex/SBOLTestSuite corpus")


@pytest.fixture(scope="session")
def sbol_test_suite():
    """Root of the SBOLTestSuite corpus; skips (or fails, under SBOL_TEST_SUITE_REQUIRED) when unavailable."""
    try:
        return sboltestsuite.suite_root()
    except sboltestsuite.SuiteUnavailable as error:
        if sboltestsuite.required():
            pytest.fail(str(error))
        pytest.skip(str(error))
