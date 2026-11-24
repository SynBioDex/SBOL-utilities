# Contributing to the SBOL 2 ⇄ SBOL 3 converter and the SBOL validators

sbol-utilities converts between SBOL 2 and SBOL 3, and validates both versions, in pure Python on
[rdflib](https://rdflib.readthedocs.io/) graphs. No Node.js, Java, or network service is involved.

- [Code location](#code-location)
- [Behavioural reference](#behavioural-reference)
- [Local installation](#local-installation)
- [Tests and the SBOLTestSuite harness](#tests-and-the-sboltestsuite-harness)
- [Regenerating goldens and vendored data](#regenerating-goldens-and-vendored-data)
- [Finding issues](#finding-issues)

## Code location

| Path | Contents |
|---|---|
| `sbol_utilities/convert/` | `upgrade()` (SBOL 2 → 3) and `downgrade()` (SBOL 3 → 2), their options, and the conversion report |
| `sbol_utilities/validation/` | `validate()`, `validate_sbol2()`, `validate_sbol3()`, configuration, reports, the rule registry, and the ontology snapshot |
| `sbol_utilities/validation/sbol2/`, `sbol_utilities/validation/sbol3/` | The rule implementations for each specification version |
| `sbol_utilities/validation/data/` | Rule catalogs and ontology facts vendored from sbol-rs |
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
Java reference and [sbol-rs](https://github.com/SynBioDex/sbol-rs):

- the same IRIs: SBOL 2 `…/displayId/version` ⇄ SBOL 3 `…/version/displayId`
- the same class choices: a Component becomes a ModuleDefinition when it has interactions, the functional-entity
  type, or a sub-component instantiating a ModuleDefinition
- the same vocabulary rewrites
- the same `https://sbols.org/backport/2_3#` round-trip annotations

The validators implement every machine-checkable rule of the SBOL 3.1.0 and SBOL 2.3.0 validation-rule catalogs
and report the same issues sbol-rs does. Rules that need other documents or the web run their local subset; the
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
the commit in `test/sboltestsuite.py`. The corpus is not stored in this repository:

- with `SBOL_TEST_SUITE_DIR=/path/to/SBOLTestSuite`, the tests use that checkout;
- otherwise the first run downloads the pinned archive into `.cache/sboltestsuite/` (gitignored);
- without network access the corpus tests skip, unless `SBOL_TEST_SUITE_REQUIRED=1` is set (as in CI).

| Test | Checks |
|---|---|
| `test/test_validation_differential.py` | Every corpus file and per-rule case reports exactly the issues sbol-rs reports, under each configuration |
| `test/test_validation_corpus.py` | Each SBOL 2 corpus isolates its configuration axis; InvalidFiles fire their rules; the SBOL 3 corpus is valid |
| `test/test_validation_catalog.py` | Every machine-checkable rule is implemented and has a firing case under `test/validation_cases/` |
| `test/test_convert_corpus.py` | Upgrades, downgrades, and round trips over the corpus match sbol-rs's output graphs |
| `test/test_convert_reference.py` | Conversions agree with the Java SBOL-Converter's outputs |
| `test/test_convert_units.py` | IRI handling and vocabulary mappings |

```bash
SBOL_TEST_SUITE_DIR=~/git/SBOLTestSuite pytest test/test_validation_*.py test/test_convert_*.py
```

To add a validation rule case, write a minimal document under `test/validation_cases/sbol2/` or `sbol3/`, named
`<rule-id>[_<description>].ttl` (for example `sbol3-10104_child_url.ttl`). It must fire that rule. Documents that
must be clean go in the `valid/` subdirectory. Then regenerate the goldens so the case is also checked against
sbol-rs.

When a conversion fingerprint mismatches, set `SBOL_RS_CLI` to an sbol-rs `sbol` binary
(`cargo build --release -p sbol-cli` in sbol-rs). The failure message then shows a triple-level diff.

## Regenerating goldens and vendored data

```bash
# sbol-rs verdicts and conversion fingerprints over the corpus and the rule cases
python tools/generate_sbol_rs_goldens.py /path/to/sbol-rs/target/release/sbol
# rule catalogs and ontology facts (Python 3.11+)
python tools/sync_sbol_rs_data.py /path/to/sbol-rs
```

Goldens hold only file names, rule ids, severities, subject IRIs, and graph fingerprints. No corpus content is
copied.

## Finding issues

Converter and validator issues are labelled
[`sbol-converter`](https://github.com/SynBioDex/SBOL-utilities/issues?q=is%3Aissue%20state%3Aopen%20label%3Asbol-converter)
on GitHub.
