import argparse
import logging
import os
import sys
import time
from typing import Union, Tuple, Optional, Sequence

import rdflib.compare
import sbol3

BACKPORT_NAMESPACE = 'http://sboltools.org/backport#'


def _load_rdf(fpath: Union[str, bytes, os.PathLike]) -> rdflib.Graph:
    rdf_format = rdflib.util.guess_format(fpath)
    graph1 = rdflib.Graph()
    graph1.parse(fpath, format=rdf_format)
    return graph1


def _detect_sbol_version(graph: rdflib.Graph) -> Optional[str]:
    """
    Detect the SBOL version of a document from its RDF namespace declarations and URIs

    :param graph: the RDF graph to analyze
    :return: 'sbol2', 'sbol3', or None if version cannot be determined
    """
    sbol2_namespace = 'http://sbols.org/v2#'
    sbol3_namespace = 'http://sbols.org/v3#'

    namespaces = {str(ns) for _, ns in graph.namespaces()}

    if sbol2_namespace in namespaces:
        return 'sbol2'
    if sbol3_namespace in namespaces:
        return 'sbol3'

    if all(str(p).startswith(sbol2_namespace) for _, p, _ in graph):
        return 'sbol2'
    if all(str(p).startswith(sbol3_namespace) for _, p, _ in graph):
        return 'sbol3'

    return None


def _check_inappropriate_backport_properties(graph: rdflib.Graph, document_version) -> Tuple[bool, list]:
    """
    Check if a document contains inappropriate backport properties for its version

    :param graph: the RDF graph to check
    :param document_version: 'sbol2' or 'sbol3' indicating the document version
    :return: tuple of (has_inappropriate_properties, list_of_inappropriate_properties)
    """
    inappropriate_properties = []

    # Check for inappropriate backport properties
    for s, p, _ in graph:
        predicate_str = str(p)
        subject_str = str(s)
        if predicate_str == BACKPORT_NAMESPACE and document_version in subject_str:
            # SBOL2 document should not have sbol2version backport properties
            inappropriate_properties.append(predicate_str)

    return len(inappropriate_properties) > 0, inappropriate_properties


def validate_backport_properties(g: rdflib.Graph, document_version: str) -> bool:
    """
    Validate that a document does not contain inappropriate backport properties for its version.

    :param g: The RDF graph to validate.
    :param document_version: 'sbol2' or 'sbol3' indicating the document version.
    :return: True if validation passes (no inappropriate backport properties found).
    :raises ValueError: if inappropriate backport properties are found.
    """
    has_inappropriate, inappropriate_properties = _check_inappropriate_backport_properties(g, document_version)

    if has_inappropriate:
        version_display = document_version.upper()
        raise ValueError(
            f'Document validation failed: {version_display} document contains '
            f'inappropriate backport properties: {inappropriate_properties}. '
            f'These properties suggest the document was converted from a different SBOL version '
            f'but was not properly cleaned up after conversion.'
        )

    return True


def _remove_selective_backport_properties(graph: rdflib.Graph) -> rdflib.Graph:
    """
    Create a new graph with all backport properties from the original graph removed.

    :param graph: the RDF graph to clean
    :return: a new graph with backport properties removed
    """
    clean_graph = rdflib.Graph()
    for prefix, namespace in graph.namespaces():
        clean_graph.bind(prefix, namespace)

    for s, p, o in graph:
        predicate_str = str(p)
        if not predicate_str.startswith(BACKPORT_NAMESPACE):
            clean_graph.add((s, p, o))

    return clean_graph


def _diff_graphs(g1: rdflib.Graph, g2: rdflib.Graph,
                 strip_backport_properties: bool = False) -> Tuple[rdflib.Graph, rdflib.Graph, rdflib.Graph]:
    """
    Compare two RDF graphs and identify their differences, with special handling for SBOL documents.

    It can optionally strip away backport properties before comparison to ignore certain
    version-specific details. The comparison is based on isomorphism, meaning the graph
    structure is considered, not just the raw RDF statements.

    :param g1: The first RDF graph to compare.
    :param g2: The second RDF graph to compare.
    :param strip_backport_properties: If True, remove backport properties before comparison.
                                      Defaults to False.
    :return: A tuple of three graphs: (both, in_g1, in_g2).
             - both: Statements that are common to both graphs.
             - in_g1: Statements that are only in the first graph.
             - in_g2: Statements that are only in the second graph.
    """
    g1_sbol_version = _detect_sbol_version(g1)
    g2_sbol_version = _detect_sbol_version(g2)

    g1_to_compare = g1
    g2_to_compare = g2
    if strip_backport_properties:
        g1_to_compare = _remove_selective_backport_properties(g1)
        g2_to_compare = _remove_selective_backport_properties(g2)

    iso1 = rdflib.compare.to_isomorphic(g1_to_compare)
    iso2 = rdflib.compare.to_isomorphic(g2_to_compare)
    rdf_diff = rdflib.compare.graph_diff(iso1, iso2)
    return rdf_diff


def _report_triples(header: Optional[str], graph: rdflib.Graph) -> None:
    if header:
        print(header)
    for s, p, o in graph:
        print(f'\t{s}, {p}, {o}')
    return None


def _report_diffs(desc1: str, in1: rdflib.Graph, desc2: str, in2: rdflib.Graph) -> None:
    if in1:
        header = f'Triples in {desc1}, not in {desc2}:'
        _report_triples(header, in1)
    if in2:
        header = f'Triples in {desc2}, not in {desc1}:'
        _report_triples(header, in2)


def _diff_rdf(desc1: str, g1: rdflib.Graph, desc2: str, g2: rdflib.Graph, silent: bool = False,
              strip_backport_properties: bool = False) -> int:
    _, in1, in2 = _diff_graphs(g1, g2, strip_backport_properties=strip_backport_properties)
    if not in1 and not in2:
        return 0
    else:
        if not silent:
            _report_diffs(desc1, in1, desc2, in2)
        return 1


def file_diff(fpath1: str, fpath2: str, silent: bool = False,
              strip_backport_properties: bool = False) -> int:
    """
    Compute and report the difference between two SBOL files.

    :param fpath1: path to the first SBOL file.
    :param fpath2: path to the second SBOL file.
    :param silent: whether to report differences to stdout.
    :param strip_backport_properties: whether to strip backport properties before comparing.
    :return: 1 if there are differences, 0 if they are the same.
    """
    return _diff_rdf(fpath1, _load_rdf(fpath1), fpath2, _load_rdf(fpath2), silent=silent,
                     strip_backport_properties=strip_backport_properties)


def doc_diff(doc1: sbol3.Document, doc2: sbol3.Document, silent: bool = False,
             strip_backport_properties: bool = False) -> int:
    """
    Compute and report the difference between two SBOL3 documents

    :param doc1: the first SBOL3 document
    :param doc2: the second SBOL3 document
    :param silent: whether to report differences to stdout
    :param strip_backport_properties: whether to strip backport properties before comparing
    :return: 1 if there are differences, 0 if they are the same
    """
    return _diff_rdf('Document 1', doc1.graph(), 'Document 2', doc2.graph(), silent=silent,
                     strip_backport_properties=strip_backport_properties)


def _init_logging(debug=False):
    msg_format = '%(asctime)s.%(msecs)03dZ:%(levelname)s:%(message)s'
    date_format = '%Y-%m-%dT%H:%M:%S'
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format=msg_format, datefmt=date_format, level=level)
    logging.Formatter.converter = time.gmtime


def _parse_args(args: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument('file1', metavar='FILE1', help='First Input File')
    parser.add_argument('file2', metavar='FILE2', help='Second Input File')
    parser.add_argument('-s', '--silent', action='store_true', help='Generate no output, only status')
    parser.add_argument('--strip-backport-properties', action='store_true',
                        help='Strip backport properties before comparing')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging (default: disabled)')
    args = parser.parse_args(args)
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Command line interface to sbol_diff.

    :param argv: command line arguments.
    :return: 1 if there are differences, 0 if they are the same.
    """
    args = _parse_args(argv)
    _init_logging(args.debug)
    return file_diff(args.file1, args.file2, silent=args.silent,
                     strip_backport_properties=args.strip_backport_properties)


if __name__ == '__main__':
    sys.exit(main())
