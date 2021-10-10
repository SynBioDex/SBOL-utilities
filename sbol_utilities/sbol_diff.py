import argparse
import logging
import os
import sys
import time
from typing import Union, Tuple, Optional, Sequence

import rdflib.compare
import sbol3


def _load_rdf(fpath: Union[str, bytes, os.PathLike]) -> rdflib.Graph:
    rdf_format = rdflib.util.guess_format(fpath)
    graph1 = rdflib.Graph()
    graph1.parse(fpath, format=rdf_format)
    return graph1


def _diff_graphs(g1: rdflib.Graph, g2: rdflib.Graph) -> Tuple[rdflib.Graph, rdflib.Graph, rdflib.Graph]:
    iso1 = rdflib.compare.to_isomorphic(g1)
    iso2 = rdflib.compare.to_isomorphic(g2)
    rdf_diff = rdflib.compare.graph_diff(iso1, iso2)
    return rdf_diff


def _report_triples(header: Optional[str], graph: rdflib.Graph) -> None:
    if header:
        print(header)
    for s, p, o in graph:
        print(f'\t{s}, {p}, {o}')
    return None


def _report_diffs(desc1: str, in1: rdflib.Graph,
                  desc2: str, in2: rdflib.Graph) -> None:
    if in1:
        header = f'Triples in {desc1}, not in {desc2}:'
        _report_triples(header, in1)
    if in2:
        header = f'Triples in {desc2}, not in {desc1}:'
        _report_triples(header, in2)


def _diff_rdf(desc1: str, g1: rdflib.Graph, desc2: str, g2: rdflib.Graph,
              silent: bool = False) -> int:
    _, in1, in2 = _diff_graphs(g1, g2)
    if not in1 and not in2:
        return 0
    else:
        if not silent:
            _report_diffs(desc1, in1, desc2, in2)
        return 1


def file_diff(fpath1: str, fpath2: str, silent: bool = False) -> int:
    """
    Compute and report the difference between two SBOL3 files

    :param fpath1: path to the first SBOL3 file
    :param fpath2: path to the second SBOL3 file
    :param silent: whether to report differences to stdout
    :return: 1 if there are differences, 0 if they are the same
    """
    return _diff_rdf(fpath1, _load_rdf(fpath1), fpath2, _load_rdf(fpath2),
                     silent=silent)


def doc_diff(doc1: sbol3.Document, doc2: sbol3.Document,
             silent: bool = False) -> int:
    """
    Compute and report the difference between two SBOL3 documents

    :param doc1: the first SBOL3 document
    :param doc2: the second SBOL3 document
    :param silent: whether to report differences to stdout
    :return: 1 if there are differences, 0 if they are the same
    """
    return _diff_rdf('Document 1', doc1.graph(), 'Document 2', doc2.graph(),
                     silent=silent)


def _init_logging(debug=False):
    msg_format = "%(asctime)s.%(msecs)03dZ:%(levelname)s:%(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format=msg_format, datefmt=date_format, level=level)
    logging.Formatter.converter = time.gmtime


def _parse_args(args: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument('file1', metavar='FILE1',
                        help='First Input File')
    parser.add_argument('file2', metavar='FILE2',
                        help='Second Input File')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='Generate no output, only status')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging (default: disabled)')
    args = parser.parse_args(args)
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Command line interface to sbol_diff

    @param argv: command line arguments
    @return: 1 if there are differences, 0 if they are the same
    """
    args = _parse_args(argv)
    _init_logging(args.debug)
    return file_diff(args.file1, args.file2, silent=args.silent)


if __name__ == '__main__':
    sys.exit(main())
