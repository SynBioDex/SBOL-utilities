import unittest
import os
from pathlib import Path

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

    def test_build_reference_cache(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(test_dir, 'test_files', 'expanded_with_sequences.nt')
        doc = sbol3.Document()
        doc.read(test_file)
        cache = build_reference_cache(doc)
        # There are 529 occurrences of '22-rdf-syntax-ns#type' in expanded_with_sequences.nt,
        # which in this particular case means there are 529 separate sbol objects. That's not
        # always the case, but is the case here.
        self.assertEqual(529, len(cache))
        # plant a fake item in the cache and make sure the relevant functions
        # find it. This tests that they are actually using the cache.
        sbol3.set_namespace('https://github.com/synbiodex/sbol-utilities')
        sequence = sbol3.Sequence('seq1')
        c1 = sbol3.Component('c1', types=[sbol3.SBO_DNA], sequences=[sequence])
        doc.add(c1)
        cache[sequence.identity] = sequence
        # The sequence is not found without the cache because it is not in the document
        with self.assertRaises(ChildNotFound):
            found_object = find_child(c1.sequences[0])
        with self.assertRaises(TopLevelNotFound):
            found_object = find_top_level(c1.sequences[0])
        # Using the cache finds the sequence because we manually added
        # the sequence to the cache to test that the functions are
        # actually using the cache. This is not the expected usage
        # pattern, this is only for unit testing.
        found_object = find_child(c1.sequences[0], cache)
        self.assertEqual(sequence, found_object)
        found_object = find_top_level(c1.sequences[0], cache)
        self.assertEqual(sequence, found_object)

    def test_with_cached_references(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(test_dir, 'test_files', 'expanded_with_sequences.nt')
        doc = sbol3.Document()
        doc.read(test_file)
        target_uri = 'http://sbolstandard.org/testfiles/mmilCFP'
        # The document should not have the secret reference cache attribute
        self.assertFalse(hasattr(doc, '_sbol_utilities_reference_cache'))
        with cached_references(doc):
            # Now the document should have the secret reference cache attribute
            self.assertTrue(hasattr(doc, '_sbol_utilities_reference_cache'))
            # We know there are 529 objects in the document. Use that to verify the cache length.
            self.assertEqual(529, len(doc._sbol_utilities_reference_cache))
            # The target uri should be in the cache
            self.assertIn(target_uri, doc._sbol_utilities_reference_cache)
            obj = doc.find(target_uri)
            self.assertEqual(target_uri, obj.identity)
        # Make sure find_child and find_top_level are using the hidden cache
        with cached_references(doc) as reference_cache:
            # plant a fake item in the cache and make sure the relevant functions
            # find it. This tests that they are actually using the cache.
            sbol3.set_namespace('https://github.com/synbiodex/sbol-utilities')
            sequence = sbol3.Sequence('seq1')
            c1 = sbol3.Component('c1', types=[sbol3.SBO_DNA], sequences=[sequence])
            doc.add(c1)
            with self.assertRaises(ChildNotFound):
                find_child(c1.sequences[0])
            with self.assertRaises(TopLevelNotFound):
                find_top_level(c1.sequences[0])
            reference_cache[sequence.identity] = sequence
            # Pass the cache explicitly to find the objects
            found_object = find_child(c1.sequences[0], reference_cache)
            self.assertEqual(sequence, found_object)
            found_object = find_top_level(c1.sequences[0], reference_cache)
            self.assertEqual(sequence, found_object)
            # Use the implicit/hidden/secret cache to find objects
            found_object = find_child(c1.sequences[0])
            self.assertEqual(sequence, found_object)
            found_object = find_top_level(c1.sequences[0])
            self.assertEqual(sequence, found_object)

    def test_outgoing(self):
        """Test the outgoing_links function"""
        doc = sbol3.Document()
        test_dir = Path(__file__).parent
        doc.read(str(test_dir / 'test_files' / 'incomplete_constraints_library.nt'))

        expected = {'http://parts.igem.org/E0040',
                    'http://parts.igem.org/J23105_sequence',
                    'http://parts.igem.org/J23109',
                    'http://sbolstandard.org/testfiles/B0030_sequence',
                    'http://sbolstandard.org/testfiles/B0031',
                    'http://sbolstandard.org/testfiles/Multicolor_expression_template',
                    'http://sbolstandard.org/testfiles/Multicolor_expression_template/LocalSubComponent1',
                    'http://sbolstandard.org/testfiles/UNSX_UP',
                    'http://sbolstandard.org/testfiles/UNSX_sequence',
                    'http://sbolstandard.org/testfiles/_4_FPs'}
        self.assertEqual(outgoing_links(doc), expected)

    def test_find_feature(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(test_dir, 'test_files', 'BBa_J23101.nt')
        doc = sbol3.Document()
        doc.read(test_file)
        # create the main component which contain the features then add it to sbol3 Document
        i13504 = sbol3.Component('i13504', sbol3.SBO_DNA)
        i13504.name = 'iGEM 2016 interlab reporter'
        i13504.description = 'GFP expression cassette used for 2016 iGEM interlab study'
        i13504.roles.append(sbol3.SO_NS + '0000804')
        doc.add(i13504)
        # creating a feature and add it to the sbol3 Document
        b0034 = sbol3.Component('B0034', sbol3.SBO_DNA)
        b0034.name = 'RBS (Elowitz 1999)'
        b0034.roles = [sbol3.SO_NS + '0000139']
        doc.add(b0034)
        i13504.features.append(sbol3.SubComponent(b0034))
        # creating a feature without adding it to the sbol3 Document
        e0040 = sbol3.Component('E0040', sbol3.SBO_DNA)
        e0040.name = 'GFP'
        e0040.roles = [sbol3.SO_NS + '0000316']

        self.assertEqual(find_feature(i13504,b0034),f'Feature: {b0034} has a known identity')
        self.assertEqual(find_feature(i13504,e0040),None)




if __name__ == '__main__':
    unittest.main()
