import unittest

import sbol_utilities.expand_combinatorial_derivations
import sbol_utilities.helper_functions
import tempfile
import sbol3
import os
import logging
import sys
from unittest.mock import patch

from sbol_utilities.workarounds import copy_toplevel_and_dependencies
from test_helpers import assert_files_identical

TESTFILE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_files')

logging.getLogger().setLevel(level=logging.DEBUG)


class TestCDExpansion(unittest.TestCase):

    def test_expansion(self):
        """Test basic expansion of combinatorial derivations"""
        doc = sbol3.Document()
        doc.read(os.path.join(TESTFILE_DIR, 'simple_library.nt'))
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        roots = list(sbol_utilities.expand_combinatorial_derivations.root_combinatorial_derivations(doc))
        assert len(roots) == 1, f'Unexpected roots: {[r.identity for r in roots]}'
        derivative_collections = sbol_utilities.expand_combinatorial_derivations.expand_derivations(roots)
        assert not len(doc.validate())
        assert len(doc.find('Round_1_order_collection').members) == 24

        output_doc = sbol3.Document()
        for c in derivative_collections:
            copy_toplevel_and_dependencies(output_doc, c)
        assert not len(output_doc.validate())

        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        output_doc.write(temp_name, sbol3.SORTED_NTRIPLES)
        assert_files_identical(temp_name, os.path.join(TESTFILE_DIR, 'expanded_simple_library.nt'))

    def test_multi_backbone(self):
        """Test expansion of a specification with multiple backbones"""
        doc = sbol3.Document()
        doc.read(os.path.join(TESTFILE_DIR, 'two_backbones.nt'))
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        roots = list(sbol_utilities.expand_combinatorial_derivations.root_combinatorial_derivations(doc))
        assert len(roots) == 2
        derivative_collections = sbol_utilities.expand_combinatorial_derivations.expand_derivations(roots)
        assert not doc.validate().errors and not doc.validate().warnings
        assert len(doc.find('Two_by_six_ins_collection').members) == 6
        assert len(doc.find('Two_by_six_derivatives').members) == 12
        assert len(doc.find('Backbone_variants_derivatives').members) == 2

    #def test_constraints():  # TODO: to be added when constraint-handling is incorporated.
        # wb = openpyxl.load_workbook(TESTFILE_DIR + '/constraints_library.nt', data_only=True)
        # sbol3.set_namespace('http://sbolstandard.org/testfiles')
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

    def test_commandline(self):
        """Test expansion of combinatorial derivations from command line"""
        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        test_args = ['sbol-expand-derivations', '-vv', os.path.join(TESTFILE_DIR, 'simple_library.nt'), '-o', temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol_utilities.expand_combinatorial_derivations.main()
        assert_files_identical(temp_name, os.path.join(TESTFILE_DIR, 'expanded_simple_library.nt'))

if __name__ == '__main__':
    unittest.main()
