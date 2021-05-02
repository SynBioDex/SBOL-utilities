import sbol_utilities.excel_to_sbol
import openpyxl
import tempfile
import sbol3
import filecmp
import os
import logging
import sys
from unittest.mock import patch


TESTFILE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_files',
    )

logging.getLogger().setLevel(level=logging.DEBUG)


def test_conversion():
    wb = openpyxl.load_workbook(TESTFILE_DIR + '/simple_library.xlsx', data_only=True)
    sbol3.set_namespace('http://sbolstandard.org/testfiles/')
    doc = sbol_utilities.excel_to_sbol.excel_to_sbol(wb)

    assert not doc.validate().errors and not doc.validate().warnings
    assert len(doc.find('BasicParts').members) == 25
    assert len(doc.find('CompositeParts').members) == 6
    assert len(doc.find('LinearDNAProducts').members) == 2
    assert len(doc.find('FinalProducts').members) == 2

    temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    doc.write(temp_name, sbol3.SORTED_NTRIPLES)
    assert filecmp.cmp(temp_name, TESTFILE_DIR + '/simple_library.nt',shallow=False)


def test_constraints():
    wb = openpyxl.load_workbook(TESTFILE_DIR + '/constraints_library.xlsx', data_only=True)
    sbol3.set_namespace('http://sbolstandard.org/testfiles/')
    doc = sbol_utilities.excel_to_sbol.excel_to_sbol(wb)

    assert not doc.validate().errors and not doc.validate().warnings
    assert len(doc.find('BasicParts').members) == 43
    assert len(doc.find('CompositeParts').members) == 8
    assert len(doc.find('LinearDNAProducts').members) == 2
    assert len(doc.find('FinalProducts').members) == 2

    temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    doc.write(temp_name, sbol3.SORTED_NTRIPLES)
    assert filecmp.cmp(temp_name, TESTFILE_DIR + '/constraints_library.nt',shallow=False)


def test_commandline():
    temp_name = tempfile.gettempdir() + '/' + next(tempfile._get_candidate_names())
    test_args = ['excel_file', '-vv', TESTFILE_DIR + '/simple_library.xlsx', '-o', temp_name, '-n', 'http://sbolstandard.org/testfiles/']
    with patch.object(sys, 'argv', test_args):
        sbol_utilities.excel_to_sbol.main()
    assert filecmp.cmp(temp_name+'.nt', TESTFILE_DIR + '/simple_library.nt',shallow=False)
