# Contributing to the SBOL 2 ⇄ SBOL 3 converter and the SBOL validators

sbol-utilities converts between SBOL 2 and SBOL 3, and validates both versions, in pure Python on
[rdflib](https://rdflib.readthedocs.io/) graphs.

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
| `sbol_utilities/convert/values.py`, `uri.py`, `identity.py` | The class, predicate, and value tables for both directions; IRI decomposition; SBOL 2 → 3 identities |
| `sbol_utilities/validation/` | `validate()`, `validate_sbol2()`, `validate_sbol3()`, configuration, reports, the rule registry, and the ontology snapshot |
| `sbol_utilities/validation/schema.py` | The types both data models are described with: classes, properties, cardinalities, value kinds |
| `sbol_utilities/validation/sbol2/`, `sbol_utilities/validation/sbol3/` | For each specification version: the data model (`spec.py`), the object model and lookups (`context.py`), shared queries, and the rule implementations (`rules/`) |
| `sbol_utilities/validation/graphs.py`, `datatypes.py` | Reference-cycle queries and literal lexical forms shared by both validators |
| `sbol_utilities/validation/runtime_data.py` | The pinned SBOLTestSuite commit, and where the rule catalogs and ontology facts are read from |
| `sbol_utilities/rdf_io.py`, `vocab.py`, `identifiers.py` | RDF loading/serialization, SBOL version detection, shared namespaces, displayId syntax |
| `sbol_utilities/conversion.py` | The command-line converters and `convert2to3()` / `convert3to2()`, which return pySBOL documents |

```python
from sbol_utilities.convert import upgrade, downgrade
from sbol_utilities.validation import validate

sbol3_graph, report = upgrade("design_sbol2.xml")
print(validate(sbol3_graph))
sbol2_graph, report = downgrade(sbol3_graph)
```

`upgrade()` and `downgrade()` return a `ConversionResult`, which unpacks as above and also offers `.graph` and
`.report`. `validate()` detects the SBOL version unless given `version=2` or `version=3`.

### Adding or changing a validation rule

A rule implementation is a function registered for the rule ids it checks:

```python
@REGISTRY.rule("sbol3-11501")
def cuts(ctx: Sbol3Context) -> None:
    """Cut positions are nonnegative and within the Sequence the Cut refers to."""
    for obj in ctx.instances(spec.CUT):
        ...
        ctx.report("sbol3-11501", obj, "Cut at must be greater than or equal to zero", property=spec.AT)
```

`ctx.instances(...)` yields the objects of a class, and `ctx.report(...)` records a violation at the severity the
rule catalog gives the rule, provided the rule's gate is on. A function may report only the rules it registered for.

## Behavioural reference

The converter makes the same decisions as the [SynBioDex/SBOL-Converter](https://github.com/SynBioDex/SBOL-Converter)
Java reference:

- the same IRIs: SBOL 2 `…/displayId/version` ⇄ SBOL 3 `…/version/displayId`
- the same class choices: a Component becomes a ModuleDefinition when it has interactions, the functional-entity
  type, or a sub-component instantiating a ModuleDefinition
- the same vocabulary rewrites, except that only identifiers.org ontology terms are respelled; other role and type
  IRIs are kept exactly as written (the reference changes their scheme and does not change it back)
- the same `https://sbols.org/backport/2_3#` round-trip annotations

The validators implement every machine-checkable rule of the SBOL 3.1.0 and SBOL 2.3.0 validation-rule catalogs
that can be decided from one document. Rules that need other documents or the web run their local subset; the
report's `coverage` lists them as partially applied. The rule catalog decides each rule's gate and severity.

## Local installation

```bash
git clone https://github.com/SynBioDex/SBOL-utilities.git
cd SBOL-utilities
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]' pre-commit
pre-commit install
```

The pre-commit hooks (isort, black, flake8, mypy) check every Python file except those listed under `exclude` in
`.pre-commit-config.yaml`. Their settings are in `pyproject.toml` and `setup.cfg`.

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
| `test/test_validation_corpus.py` | Each valid SBOL 2 corpus is error-free under its configuration; every invalid SBOL 3 file fires its rule; the SBOL 3 corpus is valid |
| `test/test_validation_catalog.py` | Every machine-checkable rule is implemented and has an SBOLTestSuite invalid file that fires it |
| `test/test_convert_corpus.py` | Upgrades, downgrades, and round trips over the corpus produce the expected graphs |
| `test/test_convert_reference.py` | Conversions agree with the Java SBOL-Converter's outputs |
| `test/test_convert_units.py` | IRI handling and vocabulary mappings |
| `test/test_convert_engine.py` | Upgrade and downgrade behaviour and options on small documents |
| `test/test_validation_units.py` | Cycle queries, the schema types, and lexical forms |
| `test/test_validation_runtime_data.py` | Locating, downloading, verifying, and bundling the rule catalogs and ontology facts |

A test marked `@pytest.mark.corpus("<name>")` runs once per file of that SBOLTestSuite corpus; the names are the keys
of `CORPORA` in `test/sboltestsuite.py`.

```bash
SBOL_TEST_SUITE_DIR=~/git/SBOLTestSuite pytest test/test_validation_*.py test/test_convert_*.py
```

A failing conversion test prints the triples that differ from the expected graph.

## Reference data

New test documents and expected outputs belong in SBOLTestSuite: invalid SBOL 3 documents in `SBOL3_InvalidFiles/`
(named `sbol3-NNNNN_<case>.ttl` after the rule they violate), invalid SBOL 2 documents in `SBOL2_InvalidFiles/`
(named `sbol2-NNNNN_<case>.xml`; `InvalidFiles/` holds only files libSBOLj rejects with the rule in their name),
valid documents in the SBOL 2 / SBOL 3 directories. SBOLTestSuite's `scripts/generate_expected.py` regenerates
`Expected/`, `Rules/`, and `Ontology/`. Then move `SBOL_TEST_SUITE_COMMIT` here to the new SBOLTestSuite commit and
set the checksums in `RUNTIME_FILES` beside it to those of the four runtime files at that commit
(`test/test_validation_runtime_data.py` compares them with a checkout at the pinned commit).

Building the package (`pip install .`, `python -m build`) copies `Rules/` and `Ontology/` into
`sbol_utilities/validation/data/` and records the pinned commit there, so installed packages validate offline. The
build takes the files from `$SBOL_TEST_SUITE_DIR` when it is set (warning if that checkout is not at the pinned
commit) and from the pinned commit otherwise.

At run time the validators read `$SBOL_TEST_SUITE_DIR` when it is set, otherwise the copy in
`sbol_utilities/validation/data/` when it was made for the pinned commit, otherwise they download the pinned commit's
four runtime files once into the user cache, accepting each only when its SHA-256 matches `RUNTIME_FILES`.

## Finding issues

Converter and validator issues are labelled
[`sbol-converter`](https://github.com/SynBioDex/SBOL-utilities/issues?q=is%3Aissue%20state%3Aopen%20label%3Asbol-converter)
on GitHub.
