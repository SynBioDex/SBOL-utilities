import argparse
import logging
import re
import sys
import tempfile
import warnings
from typing import Union, Dict, List, Any, Optional

import rdflib
import sbol2
import sbol3
from Bio import SeqIO, SeqRecord
from Bio.Seq import Seq

from sbol_utilities.convert import ConversionResult, DowngradeOptions, UpgradeOptions, downgrade, upgrade
from sbol_utilities.helper_functions import strip_sbol2_version, GENETIC_DESIGN_FILE_TYPES, \
    find_top_level
from sbol_utilities.rdf_io import detect_sbol_version, load_graph, to_sbol2_document, to_sbol3_document
from sbol_utilities.sbol3_genbank_conversion import GenBankSBOL3Converter
from sbol_utilities.validation import ValidationConfig, validate_sbol2, validate_sbol3
from sbol_utilities.vocab import LEGACY_BACKPORT, SBOL2
from sbol_utilities.workarounds import id_sort

#: Conversion output is checked against every rule except the completeness family, because converted designs
#: routinely reference parts held in other documents
CONVERSION_VALIDATION = ValidationConfig(complete=False, best_practice=False)

#: An xsd:dateTime lexical form with whole seconds: date and time, then an optional time zone
WHOLE_SECOND_DATETIME = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|[+-]\d{2}:\d{2})?$')

#: PROV Activity properties whose dateTime values libSBOLj parses
ACTIVITY_TIMES = (rdflib.URIRef(sbol3.PROV_NS + 'startedAtTime'), rdflib.URIRef(sbol3.PROV_NS + 'endedAtTime'))


def convert_identities2to3(sbol3_data: str) -> str:
    """Convert SBOL2 identities into SBOL3 identities.

    Takes RDF-XML data as a string, converts all SBOL2 identities into
    SBOL3 identities, and returns RDF-XML as a string.

    Deprecated: :func:`convert2to3` produces SBOL3 identities directly.
    """
    warnings.warn('convert_identities2to3 is deprecated and will be removed; convert2to3 produces SBOL3 identities '
                  'directly.', DeprecationWarning, stacklevel=2)
    # Convert the /[version] identities of SBOL2 into identities for SBOL3
    g = rdflib.Graph().parse(data=sbol3_data, format=sbol3.RDF_XML)

    # for all objects in the prov namespace, add an SBOL type
    for s, p, o in g.triples((None, rdflib.RDF.type, None)):
        if o.startswith(sbol3.PROV_NS):
            if str(o) in {sbol3.PROV_ASSOCIATION, sbol3.PROV_USAGE}:
                g.add((s, p, rdflib.URIRef(sbol3.SBOL_IDENTIFIED)))
            else:
                g.add((s, p, rdflib.URIRef(sbol3.SBOL_TOP_LEVEL)))

    subjects = sorted(list(set(g.subjects())))
    for old_identity in subjects:
        # Check if the identity needs to change:
        new_identity = rdflib.URIRef(strip_sbol2_version(old_identity))
        if new_identity == old_identity:
            continue

        # Verify that s has a rdflib.RDF.type in the sbol3 namespace
        sbol3_type_count = 0
        for o in g.objects(old_identity, rdflib.RDF.type):
            if o.startswith(sbol3.SBOL3_NS):
                sbol3_type_count += 1
        if sbol3_type_count < 1:
            # Not an SBOL object, so don't rename it
            continue

        # Update all triples where old_identity is the subject
        for s, p, o in g.triples((old_identity, None, None)):
            g.add((new_identity, p, o))
            g.remove((s, p, o))
        # Update all triples where old_identity is the object
        for s, p, o in g.triples((None, None, old_identity)):
            g.add((s, p, new_identity))
            g.remove((s, p, o))
    return g.serialize(format="xml")


def convert2to3(sbol2_doc: Union[str, sbol2.Document], namespaces=None) -> sbol3.Document:
    """Convert an SBOL2 document to an equivalent SBOL3 document

    The conversion runs in pure Python (:func:`sbol_utilities.convert.upgrade`) and its output is checked with
    :func:`sbol_utilities.validation.validate_sbol3`, excluding the completeness rules.

    :param sbol2_doc: Document to convert, or the path of an SBOL2 file
    :param namespaces: list of URI prefixes to treat as namespaces
    :return: equivalent SBOL3 document
    :raises ValueError: if the input is not SBOL2, or the converted document violates an SBOL3 validation rule
    """
    return _upgrade(sbol2_doc, namespaces, preserve_backport=True)


def _upgrade(sbol2_doc: Union[str, sbol2.Document], namespaces, preserve_backport: bool) -> sbol3.Document:
    """Convert SBOL2 to SBOL3, optionally without the https://sbols.org/backport/2_3# round-trip annotations"""
    source = _without_legacy_backport(sbol2_doc)
    if detect_sbol_version(source) == 3:
        raise ValueError('Cannot convert from SBOL2 to SBOL3: the input is already SBOL3')
    options = UpgradeOptions(namespaces=list(namespaces) if namespaces else None, preserve_backport=preserve_backport)
    graph = _checked(upgrade(source, options), 'SBOL2', 'SBOL3', validate_sbol3)
    return to_sbol3_document(graph)


def _checked(result: ConversionResult, source_version: str, target_version: str, validate) -> rdflib.Graph:
    """The converted graph, after logging the conversion's warnings and confirming the graph is valid

    :param result: outcome of an upgrade or downgrade
    :param source_version: name of the version converted from, for messages
    :param target_version: name of the version converted to, for messages
    :param validate: validator for the target version
    :raises ValueError: if the converted graph violates a validation rule of the target version
    """
    for warning in result.report.warnings:
        logging.warning('%s-to-%s conversion: %s', source_version, target_version, warning)
    errors = validate(result.graph, CONVERSION_VALIDATION).errors
    if errors:
        report_string = "\n".join(str(e) for e in errors)
        raise ValueError(f'Conversion from {source_version} to {target_version} produced an invalid document: '
                         f'{report_string}')
    return result.graph


def _without_legacy_backport(source: Union[str, sbol2.Document, sbol3.Document]) -> rdflib.Graph:
    """The source's triples minus annotations in the http://sboltools.org/backport# namespace.

    Those annotations are conversion metadata written by the sbolgraph converter; the converter records its own in
    https://sbols.org/backport/2_3#.
    """
    graph = rdflib.Graph()
    for triple in load_graph(source):
        if not str(triple[1]).startswith(str(LEGACY_BACKPORT)):
            graph.add(triple)
    return graph


def _without_sbol2_properties(graph: rdflib.Graph) -> rdflib.Graph:
    """The SBOL3 graph minus properties in the SBOL2 namespace.

    The sbolgraph converter leaves SBOL2 identity properties (such as persistentIdentity) in its SBOL3 output; the
    downgrade derives every SBOL2 identity property itself.
    """
    for triple in list(graph):
        if str(triple[1]).startswith(str(SBOL2)):
            graph.remove(triple)
    return graph


def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
    """Convert an SBOL3 document to an equivalent SBOL2 document

    The conversion runs in pure Python (:func:`sbol_utilities.convert.downgrade`) and its output is checked with
    :func:`sbol_utilities.validation.validate_sbol2`, excluding the completeness rules. The input document is not
    modified.

    :param doc3: Document to convert
    :return: equivalent SBOL2 document
    :raises ValueError: if the converted document violates an SBOL2 validation rule
    """
    return _downgrade(doc3, default_version=None)


def _downgrade(doc3: sbol3.Document, default_version: Optional[str]) -> sbol2.Document:
    """Convert SBOL3 to SBOL2, giving default_version to objects whose SBOL3 IRI carries no version"""
    source = _without_sbol2_properties(_without_legacy_backport(doc3))
    result = downgrade(source, DowngradeOptions(default_version=default_version))
    graph = _checked(result, 'SBOL3', 'SBOL2', validate_sbol2)
    _drop_location_sequences(graph)
    _add_activity_time_milliseconds(graph)
    return to_sbol2_document(graph)


def _add_activity_time_milliseconds(graph: rdflib.Graph) -> None:
    """Write Activity start and end times with milliseconds, which libSBOLj requires.

    libSBOLj, which pySBOL2 uses to validate and to export GenBank, rejects a valid xsd:dateTime without fractional
    seconds (sbol-12403). The rewritten value denotes the same instant.
    """
    for predicate in ACTIVITY_TIMES:
        for subject, value in list(graph.subject_objects(predicate)):
            match = WHOLE_SECOND_DATETIME.match(str(value)) if isinstance(value, rdflib.Literal) else None
            if match:
                graph.remove((subject, predicate, value))
                lexical = f'{match.group(1)}.000{match.group(2) or ""}'
                graph.add((subject, predicate, rdflib.Literal(lexical, datatype=value.datatype)))


def _drop_location_sequences(graph: rdflib.Graph) -> None:
    """Remove the optional sequence property from SBOL2 Locations.

    libSBOLj, which pySBOL2 uses to validate and to export GenBank, wrongly rejects valid Location sequence
    references (https://github.com/SynBioDex/libSBOLj/issues/621). The sequence a Location refers to remains
    available through its ComponentDefinition.
    """
    for location in set(graph.objects(None, SBOL2.location)):
        graph.remove((location, SBOL2.sequence, None))


def convert_to_fasta(doc3: sbol3.Document, path: str) -> None:
    """Convert an SBOL3 document to a FASTA file, which is written to disk
    Specifically, every Component with precisely one sequence of a nucleic acid type will result in a FASTA entry
    Components will no sequences will be silently omitted; those with multiple will result in a warning

    :param doc3: SBOL3 document to convert
    :param path: path to write FASTA file to
    """
    with open(path, 'w') as out:
        for c in id_sort([c for c in doc3.objects if isinstance(c, sbol3.Component)]):
            # Find all sequences of nucleic acid type
            na_seqs = [s for s in (find_top_level(s) for s in c.sequences)
                       if s.encoding == sbol3.IUPAC_DNA_ENCODING]
            if len(na_seqs) == 0:  # ignore components with no sequence to serialize
                continue
            elif len(na_seqs) == 1:  # if there is precisely one sequence, write it to the FASTA
                record = SeqIO.SeqRecord(Seq(na_seqs[0].elements), id=c.display_id, description=c.description or '')
                out.write(record.format('fasta'))
            else:  # warn about components with ambiguous sequences
                logging.warning(f'Ambiguous component ({len(na_seqs)} sequences) not converted to FASTA: {c.identity}')


def convert_from_fasta(path: str, namespace: str, identity_map: Dict[str, str] = None) -> sbol3.Document:
    """Convert a FASTA nucleotide document on disk into an SBOL3 document
    Specifically, every sequence in the FASTA will be converted into an SBOL Component and associated Sequence

    :param path: path to read FASTA file from
    :param namespace: URIs of Components will be set to {namespace}/{fasta_id}
    :param identity_map: dictionary mapping from displayId to identity, using for getting non-default namespaces
    :return: SBOL3 document containing converted materials
    """
    doc = sbol3.Document()
    with open(path, 'r') as f:
        for r in SeqIO.parse(f, 'fasta'):
            if identity_map and r.id in identity_map:
                identity = identity_map[r.id]
                # TODO: consider whether non-default remappings of namespaces will be useful
                namespace_to_use = None  # if we got an identity directly, let the namespace be inferred
            else:
                identity = f'{namespace}/{sbol3.string_to_display_id(r.id)}'
                namespace_to_use = namespace
            s = sbol3.Sequence(identity+'_sequence', name=r.name, description=r.description.strip(),
                               elements=str(r.seq), encoding=sbol3.IUPAC_DNA_ENCODING, namespace=namespace_to_use)
            doc.add(s)
            doc.add(sbol3.Component(identity, sbol3.SBO_DNA, name=r.name, description=r.description.strip(),
                                    sequences=[s.identity], namespace=namespace_to_use))
    return doc


# TODO: Figure out how to support multiple namespaces like we do for FASTA: currently, importing from multiple
#  namespaces will not work correctly
def convert_from_genbank(path: str, namespace: str, allow_genbank_online: bool = False, force_new_converter: bool = False) -> sbol3.Document:
    """Convert a GenBank document on disk into an SBOL3 document
    Specifically, the GenBank document is first imported to SBOL2, then converted from SBOL2 to SBOL3

    :param path: path to read GenBank file from
    :param namespace: URIs of Components will be set to {namespace}/{genbank_id}
    :param allow_genbank_online: Use the online converter, rather than the local converter
    :return: SBOL3 document containing converted materials
    """
    if force_new_converter:
        converter = GenBankSBOL3Converter()
        return converter.convert_genbank_to_sbol3(gb_file=path, namespace=namespace, write=False)
    doc2 = sbol2.Document()
    sbol2.setHomespace(namespace)
    # Convert document offline
    validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
    try:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, allow_genbank_online)
        doc2.importFromFormat(path)
    finally:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)

    # The GenBank importer gives every object version 1, which is not part of the design: drop it so the SBOL3
    # identities are {namespace}/{genbank_id}
    graph = load_graph(doc2)
    _drop_sbol2_versions(graph)
    doc = _upgrade(to_sbol2_document(graph), [namespace], preserve_backport=False)
    return doc


def _drop_sbol2_versions(graph: rdflib.Graph) -> None:
    """Make every versioned SBOL2 object unversioned, renaming {persistentIdentity}/{version} to its persistentIdentity.

    References to renamed objects are updated to match.
    """
    renames = {}
    for subject, version in graph.subject_objects(SBOL2.version):
        persistent_identity = graph.value(subject, SBOL2.persistentIdentity)
        if persistent_identity is not None and str(subject) == f'{persistent_identity}/{version}':
            renames[subject] = persistent_identity
    graph.remove((None, SBOL2.version, None))
    for old, new in renames.items():
        for p, o in list(graph.predicate_objects(old)):
            graph.remove((old, p, o))
            graph.add((new, p, o))
        for s, p in list(graph.subject_predicates(old)):
            graph.remove((s, p, old))
            graph.add((s, p, new))


def convert_to_genbank(doc3: sbol3.Document, path: str, allow_genbank_online: bool = False, force_new_converter: bool = False) \
        -> List[SeqRecord.SeqRecord]:
    """Convert an SBOL3 document to a GenBank file, which is written to disk
    Note that for compatibility with version control software, if no prov:modified term is available on each Component,
    then a fixed bogus datestamp of January 1, 2000 is given

    :param doc3: SBOL3 document to convert
    :param path: path to write GenBank file to
    :param allow_genbank_online: use the online converter rather than the local converter
    :return: BioPython SeqRecord of the GenBank that was written
    """
    if force_new_converter:
        converter = GenBankSBOL3Converter()
        result_dict = converter.convert_sbol3_to_genbank(sbol3_file=None, doc=doc3, gb_file=path, write=True)
        return result_dict["seqrecords"]
    # first convert to SBOL2, then export to a temp GenBank file
    # GenBank records carry a version (VERSION <accession>.<n>); unversioned designs are exported as version 1
    doc2 = _downgrade(doc3, default_version='1')

    # TODO: remove this kludge after resolution of https://github.com/SynBioDex/libSBOLj/issues/622
    keepers = {'http://sbols.org/v2', 'http://www.w3.org/ns/prov', 'http://purl.org/dc/terms/',
               'http://sboltools.org/backport'}
    for c in doc2.componentDefinitions:  # wipe out all annotation properties
        c.properties = {p: v for p, v in c.properties.items() if any(k for k in keepers if p.startswith(k))}

    gb_tmp = tempfile.mkstemp(suffix='.gb')[1]
    # Convert document offline
    validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
    try:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, allow_genbank_online)
        doc2.exportToFormat('GenBank', gb_tmp)
    finally:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)

    # Read and re-write in order to sort and to purge invalid date information and standardize GenBank formatting
    with open(gb_tmp, 'r') as tmp:
        records = {r.id: r for r in SeqIO.parse(tmp, 'gb')}
    sorted_records = [records[r_id] for r_id in sorted(records)]
    # also sort the order of the feature qualifiers to ensure they remain stable
    for r in sorted_records:
        for f in r.features:
            f.qualifiers = {k: f.qualifiers[k] for k in sorted(f.qualifiers)}

    # write the final file
    SeqIO.write(sorted_records, path, 'gb')
    return sorted_records


#####################################
# Entry points for command-line usage:


def command_line_converter(args_dict: Dict[str, Any]):
    """Run conversions from the command line by first reading/converting input to SBOL3, then writing/converting output

    :param args_dict: Parsed command line arguments
    :return: None
    """
    # Extract arguments:
    verbosity = args_dict['verbose']
    log_level = logging.WARN if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.getLogger().setLevel(level=log_level)
    output_file = args_dict['output_file']
    input_file_type = args_dict['input_file_type']
    output_file_type = args_dict['output_file_type']
    input_file = args_dict['input_file']
    namespace = args_dict['namespace']

    # check for errors
    if input_file_type not in GENETIC_DESIGN_FILE_TYPES.keys():
        logging.error(f'Unrecognized input type {input_file_type}, must be one of {GENETIC_DESIGN_FILE_TYPES.keys()}')
        sys.exit(1)
    if output_file_type not in GENETIC_DESIGN_FILE_TYPES.keys():
        logging.error(f'Unrecognized output type {output_file_type}, must be one of {GENETIC_DESIGN_FILE_TYPES.keys()}')
        sys.exit(1)
    if input_file_type in {'FASTA', 'GenBank'} and not namespace:
        logging.error(f'Namespace is required for conversion from FASTA or GenBank')
        sys.exit(1)

    # Load input into SBOL3
    logging.info('Reading input file '+input_file)
    if input_file_type == 'FASTA':
        doc3 = convert_from_fasta(input_file, namespace)
    elif input_file_type == 'GenBank':
        doc3 = convert_from_genbank(input_file, namespace, args_dict['allow_genbank_online'], args_dict['force_new_converter'])
    elif input_file_type == 'SBOL2':
        doc2 = sbol2.Document()
        doc2.read(input_file)
        doc3 = convert2to3(doc2, [namespace] if namespace else [])
    elif input_file_type == 'SBOL3':
        doc3 = sbol3.Document()
        doc3.read(input_file)
    else:
        raise ValueError(f'Unknown file type {input_file_type}; should have been caught earlier')

    # Convert output from SBOL3
    logging.info('Writing output file '+output_file)
    if output_file_type == 'FASTA':
        convert_to_fasta(doc3, output_file)
    elif output_file_type == 'GenBank':
        convert_to_genbank(doc3, output_file, args_dict['allow_genbank_online'], args_dict['force_new_converter'])
    elif output_file_type == 'SBOL2':
        doc2 = convert3to2(doc3)
        validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            doc2.write(output_file)
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)
    elif output_file_type == 'SBOL3':
        doc3.write(output_file, sbol3.SORTED_NTRIPLES)
    else:
        raise ValueError(f'Unknown file type {output_file_type}; should have been caught earlier')


def main():
    """Main wrapper: read from input file, invoke conversion based on type, then write to output file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file_type', help='Input file type, options: FASTA, GenBank, SBOL2, SBOL3 (default)')
    parser.add_argument('output_file_type', help='Output file type, options: FASTA, GenBank, SBOL2, SBOL3 (default)')
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-n', '--namespace', dest='namespace', default=None,
                        help='Namespace URL, required for conversions from FASTA and GenBank')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    parser.add_argument('--allow-genbank-online', dest='allow_genbank_online', action='store_true', default=False,
                        help='Perform GenBank conversion using online converter')
    parser.add_argument('--force-new-converter', dest='force_new_converter', action='store_true', default=False,
                        help='Use the direct GenBank converter instead of the pySBOL2-based GenBank converter.')
    args_dict = vars(parser.parse_args())
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def fasta2sbol():
    """Convert a FASTA file to an SBOL3 file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-n', '--namespace', dest='namespace', default=None,
                        help='Namespace URL, required for conversions from FASTA')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'FASTA'
    args_dict['output_file_type'] = 'SBOL3'
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def genbank2sbol():
    """Convert a GenBank file to an SBOL3 file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-n', '--namespace', dest='namespace', default=None,
                        help='Namespace URL, required for conversions from GenBank')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help='Print running explanation of conversion process')
    parser.add_argument('--allow-genbank-online', dest='allow_genbank_online', action='store_true', default=False,
                        help='Perform GenBank conversion using online converter')
    parser.add_argument('--force-new-converter', dest='force_new_converter', action='store_true', default=False,
                        help='Force the usage of new (offline) converter instead of legacy (online) converter.')
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'GenBank'
    args_dict['output_file_type'] = 'SBOL3'
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def sbol2to3():
    """Convert an SBOL2 file to an SBOL3 file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-n', '--namespace', dest='namespace', default=None,
                        help='Namespace URL, optional for conversions from SBOL2')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'SBOL2'
    args_dict['output_file_type'] = 'SBOL3'
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def sbol2fasta():
    """Convert an SBOL3 file to a FASTA file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'SBOL3'
    args_dict['output_file_type'] = 'FASTA'
    args_dict['namespace'] = None
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def sbol2genbank():
    """Convert an SBOL3 file to a GenBank file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    parser.add_argument('--allow-genbank-online', dest='allow_genbank_online', action='store_true', default=False,
                        help='Perform GenBank conversion using online converter')
    parser.add_argument('--force-new-converter', dest='force_new_converter', action='store_true', default=False,
                        help='Force the usage of new (offline) converter instead of legacy (online) converter.')
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'SBOL3'
    args_dict['output_file_type'] = 'GenBank'
    args_dict['namespace'] = None
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)


def sbol3to2():
    """Convert an SBOL3 file to an SBOL2 file"""
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Genetic design file used as input')
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help='Name of output file to be written')
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())
    args_dict['input_file_type'] = 'SBOL3'
    args_dict['output_file_type'] = 'SBOL2'
    args_dict['namespace'] = None
    # Call the shared command-line conversion routine
    command_line_converter(args_dict)

if __name__ == '__main__':
    main()
