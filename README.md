# SBOL-utilities
SBOL-utilities is a collection of scripts and functions for manipulating SBOL data that can be imported or run from the commandline.

## Installation

```
pip3 install sbol-utilities
```

## Graph SBOL Documents

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

