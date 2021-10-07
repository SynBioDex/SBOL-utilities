import argparse
import logging
import os
import sys
import time
from typing import Union, Tuple, Optional, Sequence

import rdflib.compare


def load_rdf(fpath: Union[str, bytes, os.PathLike]) -> rdflib.Graph:
    rdf_format = rdflib.util.guess_format(fpath)
    graph1 = rdflib.Graph()
    graph1.parse(fpath, format=rdf_format)
    return graph1


def diff_rdf(g1: rdflib.Graph, g2: rdflib.Graph) -> Tuple[rdflib.Graph, rdflib.Graph, rdflib.Graph]:
    iso1 = rdflib.compare.to_isomorphic(g1)
    iso2 = rdflib.compare.to_isomorphic(g2)
    rdf_diff = rdflib.compare.graph_diff(iso1, iso2)
    return rdf_diff


def report_triples(header: Optional[str], graph: rdflib.Graph) -> None:
    if header:
        print(header)
    for s, p, o in graph:
        print(f'\t{s}, {p}, {o}')
    return None


def report_diffs(fpath1: str, in1: rdflib.Graph,
                 fpath2: str, in2: rdflib.Graph) -> None:
    if in1:
        header = f'Triples in {fpath1}, not in {fpath2}:'
        report_triples(header, in1)
    if in2:
        header = f'Triples in {fpath2}, not in {fpath1}:'
        report_triples(header, in2)


def sbol_diff(fpath1: str, fpath2: str, silent: bool = False) -> int:
    sbol1 = load_rdf(fpath1)
    sbol2 = load_rdf(fpath2)
    _, in1, in2 = diff_rdf(sbol1, sbol2)
    if not in1 and not in2:
        return 0
    else:
        if not silent:
            report_diffs(fpath1, in1, fpath2, in2)
        return 1


def init_logging(debug=False):
    msg_format = "%(asctime)s.%(msecs)03dZ:%(levelname)s:%(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format=msg_format, datefmt=date_format, level=level)
    logging.Formatter.converter = time.gmtime


def parse_args(args: Optional[Sequence[str]] = None):
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
    args = parse_args(argv)
    init_logging(args.debug)
    return sbol_diff(args.file1, args.file2, silent=args.silent)


if __name__ == '__main__':
    sys.exit(main())
