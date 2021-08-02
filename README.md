# SBOL-utilities
SBOL-utilities is a collection of scripts and functions for manipulating SBOL 3 data that can be imported or run from the command line.

## Installation

```
pip3 install sbol-utilities
```

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

### Expand the combinatorial derivations in an SBOL file

The `sbol-expand-derivations` utility searches through an SBOL file for CombinatorialDerivation objects and expands them to create a library of all of the specific constructs.
