import tempfile
from pathlib import Path

import unittest

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2
from sbol_utilities.sbol_diff import file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


class TestDirectSBOL2SBOL3Conversion(unittest.TestCase):

    # TODO: turn on validation
    def test_3to2_conversion(self):
        """Test ability to convert a simple part from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / 'BBa_J23101.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        #self.assertEqual(len(doc2.validate()), 0)
        with tempfile.NamedTemporaryFile(suffix='.xml') as tmp2:
            doc2.write(tmp2.name)
            self.assertFalse(file_diff(tmp2.name, str(TEST_FILES / 'BBa_J23101.xml')))
            doc3_loop = convert2to3(doc2)
            #self.assertEqual(len(doc3_loop.validate()), 0)
            with tempfile.NamedTemporaryFile(suffix='.nt') as tmp3:
                doc3_loop.write(tmp3.name)
                self.assertFalse(file_diff(tmp3.name, str(TEST_FILES / 'BBa_J23101_patched.nt')))

    def test_2to3_conversion(self):
        """Test ability to convert a simple part from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / 'BBa_J23101.xml')
        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, True)
        #self.assertEqual(len(doc3.validate()), 0)
        with tempfile.NamedTemporaryFile(suffix='.nt') as tmp3:
            doc3.write(tmp3.name)
            self.assertFalse(file_diff(tmp3.name, str(TEST_FILES / 'BBa_J23101.nt')))
            doc2_loop = convert3to2(doc3)
            # self.assertEqual(len(doc2_loop.validate()), 0)
            with tempfile.NamedTemporaryFile(suffix='.xml') as tmp2:
                doc2_loop.write(tmp2.name)
                self.assertFalse(file_diff(tmp2.name, str(TEST_FILES / 'BBa_J23101.xml')))


if __name__ == '__main__':
    unittest.main()
