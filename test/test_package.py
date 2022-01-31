import filecmp
import unittest
import os
import tempfile

import sbol3

import sbol_utilities.package

class TestPackage(unittest.TestCase):
    def test_define_package(self):
        """Test defining a package from an SBOL document"""
        
        # Read in the test file
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc = sbol3.Document()
        doc.read(os.path.join(test_dir, 'test_files', 'package_in.nt'))

        # Run the function
        new_doc = sbol_utilities.package.define_package(doc)

        # Write a temporary file
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        new_doc.write(tmp_out, sbol3.SORTED_NTRIPLES)

        # Compare it to the saved results file, make sure they are the same
        comparison_file = os.path.join(test_dir, 'test_files', 'package_out.nt')
        assert filecmp.cmp(tmp_out, comparison_file), 'Files are not identical'

        # Delete the file
        if os.path.exists('out.nt'):
            os.remove('out.nt')

if __name__ == '__main__':
    unittest.main()
