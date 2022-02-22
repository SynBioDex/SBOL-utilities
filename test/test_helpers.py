import unittest
import os
from sbol_utilities import component

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

    def test_filtering_top_level_objects(self):
        """Check filtering Top Level Objects by a condition"""
        test_dir = os.path.dirname(os.path.realpath(__file__))
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        # we consider simple_library document for the test
        simple_library = os.path.join(test_dir, 'test_files', 'simple_library.nt')
        doc = sbol3.Document()
        doc.read(simple_library)

        # we check for the no of dna parts in doc
        self.assertEqual(len(doc.objects), 68, f'Expected 34 TopLevel Objects, found {len(doc.objects)}')
        itr = filter_top_level(doc, component.is_dna_part)
        total_filtered = sum(1 for _ in itr)
        self.assertEqual(total_filtered, 24, f'Expected 24 Objects to satisfy filter, found {total_filtered}')

if __name__ == '__main__':
    unittest.main()
