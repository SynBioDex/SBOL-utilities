import sbol_utilities.expand_combinatorial_derivations
import sbol_utilities.helper_functions
import tempfile
import sbol3
from sbol_utilities.helper_functions import assert_files_identical
import os
import logging
import sys
from unittest.mock import patch


TESTFILE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_files',
    )

logging.getLogger().setLevel(level=logging.DEBUG)


def test_expansion():
    doc = sbol3.Document()
    doc.read(TESTFILE_DIR + '/simple_library.nt')
    sbol3.set_namespace('http://sbolstandard.org/testfiles/')
    roots = list(sbol_utilities.expand_combinatorial_derivations.root_combinatorial_derivations(doc))
    assert len(roots) == 1, f'Unexpected roots: {[r.identity for r in roots]}'
    derivative_collections = sbol_utilities.expand_combinatorial_derivations.expand_derivations(roots)
    assert not doc.validate().errors and not doc.validate().warnings
    assert len(doc.find('Round_1_order_collection').members) == 24

    output_doc = sbol3.Document()
    for c in derivative_collections:
        sbol_utilities.helper_functions.copy_toplevel_and_dependencies(output_doc, c)
    report = output_doc.validate()
    assert not output_doc.validate().errors and not output_doc.validate().warnings

    temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    output_doc.write(temp_name, sbol3.SORTED_NTRIPLES)
    assert_files_identical(temp_name, TESTFILE_DIR + '/expanded_simple_library.nt') # TODO: work around pySBOL3 issue #231

def test_multibackbone():
    doc = sbol3.Document()
    doc.read(TESTFILE_DIR + '/two_backbones.nt')
    sbol3.set_namespace('http://sbolstandard.org/testfiles/')
    roots = list(sbol_utilities.expand_combinatorial_derivations.root_combinatorial_derivations(doc))
    assert len(roots) == 2
    derivative_collections = sbol_utilities.expand_combinatorial_derivations.expand_derivations(roots)
    assert not doc.validate().errors and not doc.validate().warnings
    assert len(doc.find('Two_by_six_ins_collection').members) == 6
    assert len(doc.find('Two_by_six_derivatives').members) == 12
    assert len(doc.find('Backbone_variants_derivatives').members) == 2


#def test_constraints():  # TODO: to be added when constraint-handling is incorporated.
    # wb = openpyxl.load_workbook(TESTFILE_DIR + '/constraints_library.nt', data_only=True)
    # sbol3.set_namespace('http://sbolstandard.org/testfiles/')
    # doc = sbol_utilities.excel_to_sbol.excel_to_sbol(wb)
    #
    # assert not doc.validate().errors and not doc.validate().warnings
    # assert len(doc.find('BasicParts').members) == 43
    # assert len(doc.find('CompositeParts').members) == 8
    # assert len(doc.find('LinearDNAProducts').members) == 2
    # assert len(doc.find('FinalProducts').members) == 2
    #
    # temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    # doc.write(temp_name, sbol3.SORTED_NTRIPLES)
    # assert filecmp.cmp(temp_name, TESTFILE_DIR + '/constraints_library.nt')


def test_commandline():
    temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    test_args = ['excel_file', '-vv', TESTFILE_DIR + '/simple_library.nt', '-o', temp_name]
    with patch.object(sys, 'argv', test_args):
        sbol_utilities.expand_combinatorial_derivations.main()
    assert_files_identical(temp_name+'.nt', TESTFILE_DIR + '/expanded_simple_library.nt') # TODO: work around pySBOL3 issue #231
