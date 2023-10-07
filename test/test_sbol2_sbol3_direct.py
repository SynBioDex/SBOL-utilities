import tempfile
from pathlib import Path

import unittest

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2
from sbol_utilities.sbol_diff import file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


class TestDirectSBOL2SBOL3Conversion(unittest.TestCase):

    def test_3to2_conversion(self):
        """Test ability to convert a simple part from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / 'BBa_J23101.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        with tempfile.NamedTemporaryFile(suffix='.xml') as tmp:
            doc2.write(tmp.name)
            self.assertFalse(file_diff(tmp.name, str(TEST_FILES / 'BBa_J23101.xml')))


if __name__ == '__main__':
    unittest.main()
