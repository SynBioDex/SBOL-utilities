# SBOL-utilities

SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that can be run from the command line or as functions in Python.
[Additional documentation is online at readthedocs.io](https://sbol-utilities.readthedocs.io/en/latest/).

[![Documentation Status](https://readthedocs.org/projects/sbol-utilities/badge/?version=latest)](http://sbol-utilities.readthedocs.io/)
[![Docstrings Coverage](https://github.com/SynBioDex/SBOL-utilities/actions/workflows/docstr-coverage.yml/badge.svg)](https://github.com/SynBioDex/SBOL-utilities/actions/workflows/docstr-coverage.yml)
[![PyPI version fury.io](https://badge.fury.io/py/sbol-utilities.svg)](https://pypi.python.org/pypi/sbol-utilities/)
[![PyPI license](https://img.shields.io/pypi/l/sbol-utilities.svg)](https://pypi.python.org/pypi/sbol-utilities/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/sbol-utilities.svg)](https://pypi.python.org/pypi/sbol-utilities/)
[![gh-action badge](https://github.com/SynBioDex/SBOL-utilities/actions/workflows/python-app.yml/badge.svg)](https://github.com/SynBioDex/SBOL-utilities/actions)


## Installation

SBOL utilities requires Python 3.7+. 

To install the package and all dependences, run:
```
pip3 install sbol-utilities
```

Certain utilities also have non-Python dependencies, which must be installed separately:
- `graph-sbol` requires [Graphviz](https://graphviz.org/) to be able to render diagrams.
- `sbol-converter` requires [node.js](https://nodejs.org/en/) to be able to locally run Javascript.


## Utilities

### Graph SBOL Documents

The `graph_sbol` utility uses graphviz to render the object tree in an sbol Document. In addition it will write PDF and Graphviz source files.

To use in context of an application:

```
import sbol3
from sbol_utilities.graph_sbol import graph_sbol

doc = sbol3.Document()
doc.read('my_file.ttl')
graph_sbol(doc)
```

To run as a commandline executable:

```
graph-sbol -i my_file.ttl
```

### Convert an Excel template file to SBOL

The `excel-to-sbol` utility reads an Excel file specifying a library of basic and composite parts, formatted following `sbol_library_template.xlsx`.

### Convert beween SBOL3 and other genetic design formats

The `sbol-converter` utility converts between any of the SBOL3, SBOL2, GenBank, and FASTA formats.

Additional "macro" utilities convert specifically between SBOL3 and one of the other formats: 
- `sbol-to-fasta` and `fasta-to-sbol` convert from SBOL3 to FASTA and vice versa
- `sbol-to-genbank` and `genbank-to-sbol` convert from SBOL3 to GenBank and vice versa
- `sbol3-to-sbol2` and `sbol2-to-sbol3` convert to and from SBOL2

### Expand the combinatorial derivations in an SBOL file

The `sbol-expand-derivations` utility searches through an SBOL file for CombinatorialDerivation objects and expands them to create a library of all of the specific constructs.

### Calculate sequences of DNA components in an SBOL file

The `sbol-calculate-sequences` utility attempts to calculate the sequence of any DNA Component that can be fully specified from the sequences of its sub-components.

### Compute the difference between two SBOL3 documents
The `sbol-diff` utility computes the difference between two SBOL3 documents
and reports the differences.


## Contributing

We welcome contributions that patch bugs, improve existing utilities or documentation, or add new utilities!
For guidance on how to contribute effectively to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).