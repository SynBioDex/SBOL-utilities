import pytest
import unittest
import sbol_utilities
import openpyxl
import tempfile
import sbol3
import filecmp
import os
import logging

TESTFILE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_files',
    )

class TestExcelToSBOL(unittest.TestCase):
    def test_conversion(self):
        wb = openpyxl.load_workbook(TESTFILE_DIR+'/simple_library.xlsx', data_only=True)
        sbol3.set_namespace('http://sbolstandard.org/testfiles/')
        doc = sbol_utilities.excel_to_sbol(wb)

        assert not doc.validate().errors and not doc.validate().warnings
        assert len(doc.find('BasicParts').members) == 25
        assert len(doc.find('CompositeParts').members) == 6
        assert len(doc.find('LinearDNAProducts').members) == 2
        assert len(doc.find('FinalProducts').members) == 2

        temp_name = tempfile.gettempdir()+next(tempfile._get_candidate_names())
        doc.write(temp_name, sbol3.SORTED_NTRIPLES)
        assert filecmp.cmp(temp_name,TESTFILE_DIR+'/simple_library.nt')

    def test_constraints(self):
        wb = openpyxl.load_workbook(TESTFILE_DIR+'/constraints_library.xlsx', data_only=True)
        sbol3.set_namespace('http://sbolstandard.org/testfiles/')
        doc = sbol_utilities.excel_to_sbol(wb)

        assert not doc.validate().errors and not doc.validate().warnings
        assert len(doc.find('BasicParts').members) == 43
        assert len(doc.find('CompositeParts').members) == 8
        assert len(doc.find('LinearDNAProducts').members) == 2
        assert len(doc.find('FinalProducts').members) == 2

        temp_name = tempfile.gettempdir()+next(tempfile._get_candidate_names())
        doc.write(temp_name, sbol3.SORTED_NTRIPLES)
        assert filecmp.cmp(temp_name,TESTFILE_DIR+'/constraints_library.nt')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
