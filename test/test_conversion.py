import unittest
import os
import filecmp

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2, convert_to_genbank, convert_to_fasta, \
    convert_from_fasta, convert_from_genbank
from helpers import copy_to_tmp
from sbol_utilities.sbol_diff import doc_diff
# TODO: Add command-line utilities and test them too


class Test2To3Conversion(unittest.TestCase):
    def test_convert_identities(self):
        """Test conversion of a complex file"""
        test_dir = os.path.dirname(os.path.realpath(__file__))
        input_path = os.path.join(test_dir, 'test_files', 'sbol3-small-molecule.rdf')
        doc = convert2to3(input_path)
        # check for issues in converted document
        report = doc.validate()
        for issue in report:
            print(issue)
        assert len(report) == 0
        # Expecting 9 top level objects, 4 Components, 4 Sequences, and 1 prov:Activity
        self.assertEqual(9, len(doc.objects))

    def test_convert_object(self):
        """Test conversion of a loaded SBOL2 document"""
        test_dir = os.path.dirname(os.path.realpath(__file__))
        input_path = os.path.join(test_dir, 'test_files', 'sbol3-small-molecule.rdf')
        doc2 = sbol2.Document()
        doc2.read(input_path)
        doc = convert2to3(doc2)
        # check for issues in converted document
        report = doc.validate()
        for issue in report:
            print(issue)
        assert len(report) == 0
        # Expecting 9 top level objects, 4 Components, 4 Sequences, and 1 prov:Activity
        self.assertEqual(9, len(doc.objects))

    def test_3to2_conversion(self):
        """Test ability to convert from SBOL3 to SBOL2"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['BBa_J23101.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'BBa_J23101.nt'))

        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3)
        assert len(doc2.componentDefinitions) == 1, f'Expected 1 CD, but found {len(doc2.componentDefinitions)}'
        # TODO: bring this back after resolution of https://github.com/sboltools/sbolgraph/issues/15
        #assert len(doc2.activities) == 1, f'Expected 1 Activity, but found {len(doc2.activities)}'
        assert len(doc2.sequences) == 1, f'Expected 1 Sequence, but found {len(doc2.sequences)}'
        assert doc2.componentDefinitions[0].identity == 'https://synbiohub.org/public/igem/BBa_J23101'
        assert doc2.componentDefinitions[0].sequences[0] == 'https://synbiohub.org/public/igem/BBa_J23101_sequence'
        assert doc2.sequences[0].encoding == 'http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html'
        assert doc2.sequences[0].elements == 'tttacagctagctcagtcctaggtattatgctagc'

    def test_genbank_conversion(self):
        """Test ability to convert from SBOL3 to GenBank"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['BBa_J23101.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'BBa_J23101.nt'))

        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, 'BBa_J23101.gb')
        convert_to_genbank(doc3, outfile)

        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'BBa_J23101.gb')
        assert filecmp.cmp(outfile, comparison_file), f'Converted GenBank file {comparison_file} is not identical'

    def test_conversion_from_genbank(self):
        """Test ability to convert from GenBank to SBOL3"""
        # Get the GenBank test document and convert
        tmp_sub = copy_to_tmp(package=['BBa_J23101.gb'])
        doc3 = convert_from_genbank(os.path.join(tmp_sub, 'BBa_J23101.gb'), 'https://synbiohub.org/public/igem')

        # Note: cannot directly round-trip because converter is a) lossy, and b) inserts extra materials
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'BBa_J23101_from_genbank.nt')
        comparison_doc = sbol3.Document()
        comparison_doc.read(comparison_file)
        assert not doc_diff(doc3, comparison_doc), f'Converted GenBank file not identical to {comparison_file}'

    def test_genbank_multi_conversion(self):
        """Test ability to convert from SBOL3 to GenBank"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['iGEM_SBOL2_imports.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'iGEM_SBOL2_imports.nt'))

        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, 'iGEM_SBOL2_imports.gb')
        convert_to_genbank(doc3, outfile)

        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'iGEM_SBOL2_imports.gb')
        assert filecmp.cmp(outfile, comparison_file), f'Converted GenBank file {comparison_file} is not identical'

    def test_fasta_conversion(self):
        """Test ability to convert from SBOL3 to FASTA"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['BBa_J23101.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'BBa_J23101.nt'))

        # Convert to FASTA and check contents
        outfile = os.path.join(tmp_sub, 'BBa_J23101.fasta')
        convert_to_fasta(doc3, outfile)

        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'BBa_J23101.fasta')
        assert filecmp.cmp(outfile, comparison_file), f'Converted FASTA file {comparison_file} is not identical'

    def test_conversion_from_fasta(self):
        """Test ability to convert from SBOL3 to FASTA"""
        """Test ability to convert from GenBank to SBOL3"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['BBa_J23101.fasta'])
        doc3 = convert_from_fasta(os.path.join(tmp_sub, 'BBa_J23101.fasta'), 'https://synbiohub.org/public/igem')

        # Note: cannot directly round-trip because converter is lossy
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'BBa_J23101_from_fasta.nt')
        comparison_doc = sbol3.Document()
        comparison_doc.read(comparison_file)
        assert not doc_diff(doc3, comparison_doc), f'Converted FASTA file not identical to {comparison_file}'


if __name__ == '__main__':
    unittest.main()
