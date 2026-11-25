"""Shared pytest configuration: SBOLTestSuite availability, markers, and corpus parametrization."""

from __future__ import annotations

import pytest

import sboltestsuite


def pytest_configure(config):
    """Register the markers used by the conformance suites."""
    config.addinivalue_line("markers", "sboltestsuite: test reads the SynBioDex/SBOLTestSuite corpus")
    config.addinivalue_line(
        "markers", "corpus(name, argname='path'): run the test once per item of an SBOLTestSuite corpus"
    )


def pytest_generate_tests(metafunc):
    """Parametrize a test marked ``corpus`` over the items of the corpus it names."""
    marker = metafunc.definition.get_closest_marker("corpus")
    if marker is not None:
        metafunc.parametrize(marker.kwargs.get("argname", "path"), sboltestsuite.corpus_params(marker.args[0]))


@pytest.fixture(scope="session")
def sbol_test_suite():
    """Root of the SBOLTestSuite corpus; skips (or fails, under SBOL_TEST_SUITE_REQUIRED) when unavailable."""
    try:
        return sboltestsuite.suite_root()
    except sboltestsuite.SuiteUnavailable as error:
        if sboltestsuite.required():
            pytest.fail(str(error))
        pytest.skip(str(error))


@pytest.fixture(autouse=True)
def _corpus_tests_need_the_suite(request):
    """Skip or fail a test marked ``corpus`` or ``sboltestsuite`` when the suite is unavailable."""
    if request.node.get_closest_marker("corpus") or request.node.get_closest_marker("sboltestsuite"):
        request.getfixturevalue("sbol_test_suite")
