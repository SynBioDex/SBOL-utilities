# Contributing to the SBOL 2 ⇄ SBOL 3 converter and the SBOL validators

sbol-utilities converts between SBOL 2 and SBOL 3, and validates both versions, in pure Python on
[rdflib](https://rdflib.readthedocs.io/) graphs. No Node.js, Java, or network service is involved.

- [Code location](#code-location)
- [Behavioural reference](#behavioural-reference)
- [Local installation](#local-installation)
- [Tests and the SBOLTestSuite harness](#tests-and-the-sboltestsuite-harness)
- [Reference data](#reference-data)
- [Finding issues](#finding-issues)

## Code location

| Path | Contents |
|---|---|
| `sbol_utilities/convert/` | `upgrade()` (SBOL 2 → 3) and `downgrade()` (SBOL 3 → 2), their options, and the conversion report |
| `sbol_utilities/validation/` | `validate()`, `validate_sbol2()`, `validate_sbol3()`, configuration, reports, the rule registry, and the ontology snapshot |
| `sbol_utilities/validation/sbol2/`, `sbol_utilities/validation/sbol3/` | The rule implementations for each specification version |
| `sbol_utilities/validation/runtime_data.py` | The pinned SBOLTestSuite commit, and where the rule catalogs and ontology facts are read from |
| `sbol_utilities/rdf_io.py`, `sbol_utilities/vocab.py` | RDF loading/serialization, SBOL version detection, shared namespaces |
| `sbol_utilities/conversion.py` | The command-line converters and `convert2to3()` / `convert3to2()`, which return pySBOL documents |

`sbol_utilities/sbol3_sbol2_conversion.py` (the pySBOL-based visitor) and the `sbolgraph` JavaScript converter
are deprecated. They stay reachable through `convert2to3(..., converter='legacy_native' | 'sbolgraph')` until they
are removed.

```python
from sbol_utilities.convert import upgrade, downgrade
from sbol_utilities.validation import validate

sbol3_graph, report = upgrade("design_sbol2.xml")
print(validate(sbol3_graph))
sbol2_graph, report = downgrade(sbol3_graph)
```

## Behavioural reference

The converter makes the same decisions as the [SynBioDex/SBOL-Converter](https://github.com/SynBioDex/SBOL-Converter)
Java reference:

- the same IRIs: SBOL 2 `…/displayId/version` ⇄ SBOL 3 `…/version/displayId`
- the same class choices: a Component becomes a ModuleDefinition when it has interactions, the functional-entity
  type, or a sub-component instantiating a ModuleDefinition
- the same vocabulary rewrites, except that only identifiers.org ontology terms are respelled; other role and type
  IRIs are kept exactly as written (the reference changes their scheme and does not change it back)
- the same `https://sbols.org/backport/2_3#` round-trip annotations

The validators implement every machine-checkable rule of the SBOL 3.1.0 and SBOL 2.3.0 validation-rule catalogs. Rules that need other documents or the web run their local subset; the
report's `coverage` lists them as partially applied.

## Local installation

```bash
git clone https://github.com/SynBioDex/SBOL-utilities.git
cd SBOL-utilities
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]' pre-commit
pre-commit install
```

The pre-commit hooks (isort, black, flake8, mypy) cover the conversion and validation packages, their tests, and
`tools/`.

## Tests and the SBOLTestSuite harness

The conformance tests run against [SynBioDex/SBOLTestSuite](https://github.com/SynBioDex/SBOLTestSuite), pinned to
`SBOL_TEST_SUITE_COMMIT` in `sbol_utilities/validation/runtime_data.py`. SBOLTestSuite holds the valid and invalid
SBOL 2 and SBOL 3 files, the issues and conversions each file is expected to produce (`Expected/`), and the rule
catalogs and ontology facts (`Rules/`, `Ontology/`). None of it is stored in this repository:

- with `SBOL_TEST_SUITE_DIR=/path/to/SBOLTestSuite`, the tests use that checkout;
- otherwise the first run downloads the pinned archive into `.cache/sboltestsuite/` (gitignored);
- without network access the corpus tests skip, unless `SBOL_TEST_SUITE_REQUIRED=1` is set (as in CI).

| Test | Checks |
|---|---|
| `test/test_validation_differential.py` | Every SBOLTestSuite file produces exactly its expected issues, under each configuration |
| `test/test_validation_corpus.py` | Each SBOL 2 corpus isolates its configuration axis; every invalid file fires its rule; the SBOL 3 corpus is valid |
| `test/test_validation_catalog.py` | Every machine-checkable rule is implemented and has an SBOLTestSuite invalid file that fires it |
| `test/test_convert_corpus.py` | Upgrades, downgrades, and round trips over the corpus produce the expected graphs |
| `test/test_convert_reference.py` | Conversions agree with the Java SBOL-Converter's outputs |
| `test/test_convert_units.py` | IRI handling and vocabulary mappings |

```bash
SBOL_TEST_SUITE_DIR=~/git/SBOLTestSuite pytest test/test_validation_*.py test/test_convert_*.py
```

A failing conversion test prints the triples that differ from the expected graph.

## Reference data

New test documents and expected outputs belong in SBOLTestSuite: invalid SBOL 3 documents in `SBOL3_InvalidFiles/`
(named `sbol3-NNNNN_<case>.ttl` after the rule they violate), invalid SBOL 2 documents in `InvalidFiles/`, valid
documents in the SBOL 2 / SBOL 3 directories. SBOLTestSuite's `scripts/generate_expected.py` regenerates
`Expected/`, `Rules/`, and `Ontology/`. Then move `SBOL_TEST_SUITE_COMMIT` here to the new SBOLTestSuite commit.

Building the package (`pip install .`, `python -m build`) copies `Rules/` and `Ontology/` from the pinned commit into
`sbol_utilities/validation/data/`, so installed packages validate offline. A source checkout without that copy reads
them from `$SBOL_TEST_SUITE_DIR`, or downloads them once into the user cache.

## Finding issues

Converter and validator issues are labelled
[`sbol-converter`](https://github.com/SynBioDex/SBOL-utilities/issues?q=is%3Aissue%20state%3Aopen%20label%3Asbol-converter)
on GitHub.
