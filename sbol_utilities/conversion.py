import argparse
import logging
import subprocess
import os
import sys
import tempfile
import urllib
from typing import Union, Dict, List, Any

import rdflib
import sbol2
import sbol3
from Bio import SeqIO, SeqRecord
from Bio.Seq import Seq

from sbol_utilities.helper_functions import strip_sbol2_version, GENETIC_DESIGN_FILE_TYPES
from sbol_utilities.workarounds import id_sort

# sbol javascript executable based on https://github.com/sboltools/sbolgraph
# Used for conversion between SBOL2 and SBOL3
SBOLGRAPH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sbolgraph-standalone.js')


def convert_identities2to3(sbol3_data: str) -> str:
    """Convert SBOL2 identities into SBOL3 identities.

    Takes RDF-XML data as a string, converts all SBOL2 identities into
    SBOL3 identities, and returns RDF-XML as a string.
    """
    # Convert the /[version] identities of SBOL2 into identities for SBOL3
    g = rdflib.Graph().parse(data=sbol3_data, format=sbol3.RDF_XML)

    # TODO: remove workaround after conversion errors fixed in https://github.com/sboltools/sbolgraph/issues/14
    # for all objects in the prov namespace, add an SBOL type
    # TODO: likely need to do this for OM namespace too
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

    :param sbol2_doc: Document to convert
    :param namespaces: list of URI prefixes to treat as namespaces
    :return: equivalent SBOL3 document
    """
    # if we've started with a Document in memory, write it to a temp file
    if namespaces is None:
        namespaces = []
    if isinstance(sbol2_doc, sbol2.Document):
        sbol2_path = tempfile.mkstemp(suffix='.xml')[1]
        validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            sbol2_doc.write(sbol2_path)
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)
    else:
        sbol2_path = sbol2_doc

    cmd = [SBOLGRAPH, '-output', 'sbol3',
           'import', sbol2_path,
           'convert', '--target-sbol-version', '3']
    # This will raise an exception if the command fails
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
        # Extract the rdf_xml output from the sbol converter
        rdf_xml = proc.stdout.decode('utf-8')
    except subprocess.CalledProcessError:
        raise ValueError('Embedded SBOL 2-to-3 converter failed opaquely, indicating a likely invalid SBOL file.')
    # Post-process the conversion by updating object identities
    rdf_xml = convert_identities2to3(rdf_xml)
    doc = sbol3.Document()
    doc.read_string(rdf_xml, sbol3.RDF_XML)

    # TODO: remove workaround after conversion errors fixed in https://github.com/sboltools/sbolgraph/issues/14
    # add in the missing namespace fields where possible, defaulting otherwise
    # TODO: add check for non-TopLevel? See https://github.com/SynBioDex/pySBOL3/issues/295
    needs_namespace = {o for o in doc.objects if o.namespace is None}
    for n in namespaces:
        assignable = {o for o in needs_namespace if o.identity.startswith(n)}
        for a in assignable:
            a.namespace = n
        needs_namespace = needs_namespace - assignable
    for o in needs_namespace:  # if no supplied namespace matches, default to scheme//netloc
        # figure out the server to access from the URL
        p = urllib.parse.urlparse(o.identity)
        server = urllib.parse.urlunparse([p.scheme, p.netloc, '', '', '', ''])
        o.namespace = server
    # infer sequences for locations:
    for s in (o for o in doc.objects if isinstance(o, sbol3.Component)):
        if len(s.sequences) != 1:  # can only infer sequences if there is precisely one
            continue
        for f in (f for f in s.features if isinstance(f, sbol3.SequenceFeature) or isinstance(f, sbol3.SubComponent)):
            for loc in f.locations:
                loc.sequence = s.sequences[0]
    # TODO: remove remap workarounds after conversions error fixed in https://github.com/sboltools/sbolgraph/issues/17
    # remap sequence encodings:
    encoding_remapping = {
        sbol2.SBOL_ENCODING_IUPAC: sbol3.IUPAC_DNA_ENCODING,
        sbol2.SBOL_ENCODING_IUPAC_PROTEIN: sbol3.IUPAC_PROTEIN_ENCODING,
        sbol2.SBOL_ENCODING_SMILES: sbol3.SMILES_ENCODING
    }
    for s in (o for o in doc.objects if isinstance(o, sbol3.Sequence)):
        if s.encoding in encoding_remapping:
            s.encoding = encoding_remapping[s.encoding]
    # remap component types:
    type_remapping = {
        sbol2.BIOPAX_DNA: sbol3.SBO_DNA,
        sbol2.BIOPAX_RNA: sbol3.SBO_RNA,
        sbol2.BIOPAX_PROTEIN: sbol3.SBO_PROTEIN,
        sbol2.BIOPAX_SMALL_MOLECULE: sbol3.SBO_SIMPLE_CHEMICAL,
        sbol2.BIOPAX_COMPLEX: sbol3.SBO_NON_COVALENT_COMPLEX
    }
    for c in (o for o in doc.objects if isinstance(o, sbol3.Component)):
        c.types = [(type_remapping[t] if t in type_remapping else t) for t in c.types]

    # remap orientation types
    orientation_remapping = {
        sbol2.SBOL_ORIENTATION_INLINE: sbol3.SBOL_INLINE,
        sbol2.SBOL_ORIENTATION_REVERSE_COMPLEMENT: sbol3.SBOL_REVERSE_COMPLEMENT
    }

    def change_orientation(o):
        if isinstance(o, sbol3.Location):
            if hasattr(o, 'orientation') and o.orientation in orientation_remapping:
                o.orientation = orientation_remapping[o.orientation]
    doc.traverse(change_orientation)

    report = doc.validate()
    if len(report):
        report_string = "\n".join(str(e) for e in doc.validate())
        raise ValueError(f'Conversion from SBOL2 to SBOL3 produced an invalid document: {report_string}')

    return doc


def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
    """Convert an SBOL3 document to an equivalent SBOL2 document

    :param doc3: Document to convert
    :return: equivalent SBOL2 document
    """
    # TODO: remove workarounds after conversion errors fixed in https://github.com/sboltools/sbolgraph/issues/16
    # remap sequence encodings:
    encoding_remapping = {
        sbol3.IUPAC_DNA_ENCODING: sbol2.SBOL_ENCODING_IUPAC,
        sbol3.IUPAC_PROTEIN_ENCODING: sbol2.SBOL_ENCODING_IUPAC_PROTEIN,
        sbol3.SMILES_ENCODING: sbol2.SBOL_ENCODING_SMILES
    }
    for s in (o for o in doc3.objects if isinstance(o, sbol3.Sequence)):
        if s.encoding in encoding_remapping:
            s.encoding = encoding_remapping[s.encoding]
    # remap component types:
    type_remapping = {
        sbol3.SBO_DNA: sbol2.BIOPAX_DNA,
        sbol3.SBO_RNA: sbol2.BIOPAX_RNA,
        sbol3.SBO_PROTEIN: sbol2.BIOPAX_PROTEIN,
        sbol3.SBO_SIMPLE_CHEMICAL: sbol2.BIOPAX_SMALL_MOLECULE,
        sbol3.SBO_NON_COVALENT_COMPLEX: sbol2.BIOPAX_COMPLEX
    }
    for c in (o for o in doc3.objects if isinstance(o, sbol3.Component)):
        c.types = [(type_remapping[t] if t in type_remapping else t) for t in c.types]

    # remap orientation types
    orientation_remapping = {
        sbol3.SBOL_INLINE: sbol2.SBOL_ORIENTATION_INLINE,
        sbol3.SBOL_REVERSE_COMPLEMENT: sbol2.SBOL_ORIENTATION_REVERSE_COMPLEMENT
    }

    def change_orientation(o):
        if isinstance(o, sbol3.Location) or isinstance(o, sbol3.Feature):
            if o.orientation in orientation_remapping:
                o.orientation = orientation_remapping[o.orientation]
    doc3.traverse(change_orientation)

    # Write to an RDF-XML temp file to run through the converter:
    sbol3_path = tempfile.mkstemp(suffix='.xml')[1]
    doc3.write(sbol3_path, sbol3.RDF_XML)

    # Run the actual conversion and return the resulting document
    cmd = [SBOLGRAPH, '-output', 'sbol2',
           'import', sbol3_path,
           'convert', '--target-sbol-version', '2']
    # This will raise an exception if the command fails
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
        # Extract the rdf_xml output from the sbol converter
        rdf_xml = proc.stdout.decode('utf-8')
    except subprocess.CalledProcessError:
        raise ValueError('Embedded SBOL 3-to-2 converter failed opaquely, possibly indicating an invalid SBOL file.')

    doc2 = sbol2.Document()
    doc2.readString(rdf_xml)
    # TODO: remove workaround after resolution of https://github.com/SynBioDex/libSBOLj/issues/621
    for c in doc2.componentDefinitions:
        for sa in c.sequenceAnnotations:
            for loc in sa.locations:
                loc.sequence = None  # remove optional sequences, per https://github.com/SynBioDex/libSBOLj/issues/621

    # Validate document offline
    validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
    try:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
        result = doc2.validate()
        if not result == "Valid.":
            raise ValueError(f'Conversion from SBOL3 to SBOL2 produced an invalid document: {result}')
    finally:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)

    return doc2


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
            na_seqs = [s.lookup() for s in c.sequences if s.lookup().encoding == sbol3.IUPAC_DNA_ENCODING]
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
def convert_from_genbank(path: str, namespace: str, allow_genbank_online: bool = False) -> sbol3.Document:
    """Convert a GenBank document on disk into an SBOL3 document
    Specifically, the GenBank document is first imported to SBOL2, then converted from SBOL2 to SBOL3

    :param path: path to read GenBank file from
    :param namespace: URIs of Components will be set to {namespace}/{genbank_id}
    :param allow_genbank_online: Use the online converter, rather than the local converter
    :return: SBOL3 document containing converted materials
    """
    doc2 = sbol2.Document()
    sbol2.setHomespace(namespace)
    # Convert document offline
    validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
    try:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, allow_genbank_online)
        doc2.importFromFormat(path)
    finally:
        sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)

    doc = convert2to3(doc2, [namespace])
    return doc


def convert_to_genbank(doc3: sbol3.Document, path: str, allow_genbank_online: bool = False) \
        -> List[SeqRecord.SeqRecord]:
    """Convert an SBOL3 document to a GenBank file, which is written to disk
    Note that for compatibility with version control software, if no prov:modified term is available on each Component,
    then a fixed bogus datestamp of January 1, 2000 is given

    :param doc3: SBOL3 document to convert
    :param path: path to write GenBank file to
    :param allow_genbank_online: use the online converter rather than the local converter
    :return: BioPython SeqRecord of the GenBank that was written
    """
    # first convert to SBOL2, then export to a temp GenBank file
    doc2 = convert3to2(doc3)

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
        doc3 = convert_from_genbank(input_file, namespace, args_dict['allow_genbank_online'])
    elif input_file_type == 'SBOL2':
        doc2 = sbol2.Document()
        doc2.read(input_file)
        doc3 = convert2to3(doc2, [namespace] if namespace else None)
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
        convert_to_genbank(doc3, output_file, args_dict['allow_genbank_online'])
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
