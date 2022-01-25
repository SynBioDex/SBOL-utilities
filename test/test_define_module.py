import filecmp
import unittest
import os

import sbol3

# FIXME: Need help with relative importing
# I think it's supposed to be 
import sbol_utilities.define_module
# But this gives me an error, ModuleNotFoundError: No module named 'sbol_utilities.define_module'
# Also tried
# import define_module
# from sbol_utilities import define_module
# FIXME: How to get rid of adding to path
# import sys
# sys.path.append('/c/Users/hscott/Documents/SBOL/SBOL-utilities/')
# import sbol_utilities.define_module

class TestDefineModule(unittest.TestCase):
    def test_define_module(self):
        """Test defining a module from an SBOL document"""
        
        # Read in the test file
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc = sbol3.Document()
        doc.read(os.path.join(test_dir, 'test_files', 'module_in.nt'))

        # Run the function
        new_doc = sbol_utilities.define_module.define_module(doc)

        # Read in the new file
        new_doc = sbol3.Document()
        new_doc.read(os.path.join(test_dir, 'test_files', 'out.nt')) # FIXME: Where does my file go by default?

        # Compare it to the saved results file, make sure they are the same
        comparison_file = os.path.join(test_dir, 'test_files', 'module_out.nt')
        assert filecmp.cmp(new_doc, comparison_file), 'Files are not identical'

        # Delete the file
        if os.path.exists('out.nt'):
            os.remove('out.nt')

if __name__ == '__main__':
    unittest.main()
