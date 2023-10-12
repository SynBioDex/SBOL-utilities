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
        doc3.read(TEST_FILES / 'BBa_J23101_patched.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        #report = doc2.validate()
        #self.assertEqual(len(report), 0, f'Validation failed: {report}')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'BBa_J23101.xml')))
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3_loop.validate()), 0)
            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))

    def test_2to3_conversion(self):
        """Test ability to convert a simple part from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / 'BBa_J23101.xml')
        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        self.assertEqual(len(doc3.validate()), 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
            doc2_loop = convert3to2(doc3, True)
            # report = doc2.validate()
            # self.assertEqual(len(report), 0, f'Validation failed: {report}')
            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'BBa_J23101.xml')))


if __name__ == '__main__':
    unittest.main()
