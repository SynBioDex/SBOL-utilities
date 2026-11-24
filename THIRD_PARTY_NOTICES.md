# Third-party notices

## sbol-rs

`sbol_utilities/convert/` and `sbol_utilities/validation/` implement algorithms from
[sbol-rs](https://github.com/SynBioDex/sbol-rs). `sbol_utilities/validation/data/sbol2_rules.json`,
`sbol3_rules.json`, `ontology_facts.tsv`, and `ontology_sources.tsv` are derived from sbol-rs data files, and
`test/test_files/sboltestsuite_local/` and `test/test_files/sbolconverter_reference/` are copied from its test
fixtures.

```
sbol-rs
Copyright 2026 Mike Arpaia

Licensed under the MIT License or the Apache License, Version 2.0, at your option.
```

The MIT License text:

```
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## SynBioDex/SBOL-Converter

`test/test_files/sbolconverter_reference/` holds output of the
[SBOL-Converter](https://github.com/SynBioDex/SBOL-Converter), licensed under the Apache License, Version 2.0.

## Ontology data

`sbol_utilities/validation/data/ontology_facts.tsv` records term identifiers, hierarchy, and SBOL-specific
classification drawn from the following ontologies. Term labels are omitted. Source versions and checksums are in
`ontology_sources.tsv`.

| Ontology | License |
|---|---|
| EDAM | CC BY-SA 4.0 |
| Systems Biology Ontology (SBO) | Artistic License 2.0 |
| Sequence Ontology (SO) | CC BY 4.0 |
| Gene Ontology (GO) | CC BY 4.0 |
| ChEBI | CC BY 4.0 |
| Cell Ontology (CL) | CC BY 4.0 |
