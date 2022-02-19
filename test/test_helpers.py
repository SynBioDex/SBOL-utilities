import unittest

from sbol_utilities.helper_functions import *


class TestHelpers(unittest.TestCase):

    def test_url_sanitization(self):
        # SBOL2 version stripping:
        uri = 'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA/1'
        expected = 'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA'
        self.assertEqual(strip_sbol2_version(uri), expected)

        uri = 'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA'
        expected = 'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA'
        self.assertEqual(strip_sbol2_version(uri), expected)

        # displayId cleaning:
        self.assertEqual(url_to_identity('http://foo/bar/baz.qux'), 'http://foo/bar/baz_qux')

        # extension detection and stripping
        self.assertEqual(design_file_type('something.fasta'), 'FASTA')
        self.assertEqual(design_file_type('something.xlsx'), None)
        self.assertEqual(design_file_type('something.xml'), 'SBOL2')
        self.assertEqual(design_file_type('something.nt'), 'SBOL3')
        self.assertEqual(design_file_type('full path/full/path/something.genbank'), 'GenBank')
        self.assertEqual(strip_filetype_suffix('http://foo/bar/baz.gb'), 'http://foo/bar/baz')
        self.assertEqual(strip_filetype_suffix('http://foo/bar/baz.qux'), 'http://foo/bar/baz.qux')

if __name__ == '__main__':
    unittest.main()
