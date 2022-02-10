import filecmp
import unittest
import os
import tempfile

import sbol3

import sbol_utilities.package

class TestPackage(unittest.TestCase):
    def test_define_package_single_file(self):
        """Test defining a package from an SBOL document"""
        # Read in the test file
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc_01 = sbol3.Document()
        doc_01.read(os.path.join(test_dir, 'test_files', 'package_in_01.nt'))

        # Run the function
        out_01 = sbol_utilities.package.define_package(doc_01)

        # Write a temporary file
        doc = sbol3.Document()
        doc.add(out_01)
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)

        # Compare it to the saved results file, make sure they are the same
        comparison_file = os.path.join(test_dir, 'test_files', 'package_out_01.nt')
        assert filecmp.cmp(tmp_out, comparison_file), 'Output from package creation function with one file is not as expected'

    def test_define_package_multi_file(self):
        """Test defining a package from multiple SBOL documents"""
        # Read in the test files
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc_01 = sbol3.Document()
        doc_01.read(os.path.join(test_dir, 'test_files', 'package_in_01.nt'))

        doc_02 = sbol3.Document()
        doc_02.read(os.path.join(test_dir, 'test_files', 'package_in_02.nt'))

        doc_03 = sbol3.Document()
        doc_03.read(os.path.join(test_dir, 'test_files', 'package_in_03.nt'))

        # Run the function
        out_02 = sbol_utilities.package.aggregate_subpackages(doc_01, doc_02, doc_03)

        # Write a temporary file
        doc = sbol3.Document()
        doc.add(out_02)
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)

        # Compare it to the saved results file, make sure they are the same
        comparison_file = os.path.join(test_dir, 'test_files', 'package_out_02.nt')
        assert filecmp.cmp(tmp_out, comparison_file), 'Output from package creation function with three files is not as expected'


if __name__ == '__main__':
    unittest.main()
