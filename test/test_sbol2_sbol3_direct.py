import tempfile
from pathlib import Path

import unittest

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2
from sbol_utilities.sbol_diff import file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


class TestDirectSBOL2SBOL3Conversion(unittest.TestCase):

    def handle_2to3_conversion(self, test_filename, rubric_filename):
        """Provides a re-usable test handler for converting SBOL3 to SBOL2 with different test files
        test_filename: Name of an SBOL2 test file
        rubric_filename: Name of an SBOL3 file with expected conversion
    """
        """Test ability to convert a simple part from SBOL2 to SBOL3"""

        # Load an SBOL2 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / test_filename)

        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        self.assertEqual(len(doc3.validate()), 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / rubric_filename)))
            doc2_loop = convert3to2(doc3, True)
            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / test_filename)))
            report = doc3.validate()
            self.assertEqual(len(report), 0, f'Validation failed: {report}')

    def test_2to3_J23101_conversion(self):
        self.handle_2to3_conversion('BBa_J23101.xml', 'BBa_J23101_patched.nt')

    def test_2to3_implementation_conversion(self):
        self.handle_2to3_conversion('sbol_3to2_implementation.xml', 'sbol3_implementation.nt')

    def test_2to3_collection_conversion(self):
        self.handle_2to3_conversion('sbol_3to2_collection.xml', 'sbol3_collection.nt')


class TestDirectSBOL3SBOL2Conversion(unittest.TestCase):

    def handle_3to2_conversion(self, test_filename, rubric_filename):
        """Provides a re-usable test handler for converting SBOL3 to SBOL2 with different test files
        test_filename: Name of an SBOL3 test file
        rubric_filename: Name of an SBOL2 file with expected conversion
    """
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / test_filename)
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / rubric_filename)))
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3_loop.validate()), 0)
            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / test_filename)))
            report = doc2.validate()
            self.assertEqual(report, 'Valid.', f'Validation failed: {report}')

    # Currently fails with the following validation error:
    # sbol-12403: Strong Validation Error: The endedAtTime property of an Activity object is OPTIONAL and MAY contain
    # a DateTime. Reference: SBOL Version 2.3.0 Section 12.8.1 on page 73 : https://synbiohub.org/public/igem/igem2sbol
    @unittest.expectedFailure
    def test_3to2_J23101_conversion(self):
        self.handle_3to2_conversion('BBa_J23101_patched.nt', 'BBa_J23101.xml')

    def test_3to2_implementation_conversion(self):
        self.handle_3to2_conversion('sbol3_implementation.nt', 'sbol_3to2_implementation.xml')

    def test_3to2_collection_conversion(self):
        self.handle_3to2_conversion('sbol3_collection.nt', 'sbol_3to2_collection.xml')


if __name__ == '__main__':
    unittest.main()
