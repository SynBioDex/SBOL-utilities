import sys
import tempfile
import unittest
import os
import filecmp
import collections
from unittest.mock import patch

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2, convert_to_genbank, convert_to_fasta, \
    convert_from_fasta, convert_from_genbank, \
    main, sbol2fasta, sbol2genbank, sbol2to3, sbol3to2, fasta2sbol, genbank2sbol
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
        assert len(report) == 0, "\n".join(str(issue) for issue in report)
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
        assert len(report) == 0, "\n".join(str(issue) for issue in report)
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
        validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            self.assertEqual(doc2.validate(), 'Valid.')
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)
        assert len(doc2.componentDefinitions) == 1, f'Expected 1 CD, but found {len(doc2.componentDefinitions)}'
        # TODO: bring this back after resolution of https://github.com/sboltools/sbolgraph/issues/15
        #assert len(doc2.activities) == 1, f'Expected 1 Activity, but found {len(doc2.activities)}'
        assert len(doc2.sequences) == 1, f'Expected 1 Sequence, but found {len(doc2.sequences)}'
        assert doc2.componentDefinitions[0].identity == 'https://synbiohub.org/public/igem/BBa_J23101'
        assert doc2.componentDefinitions[0].sequences[0] == 'https://synbiohub.org/public/igem/BBa_J23101_sequence'
        assert doc2.sequences[0].encoding == 'http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html'
        assert doc2.sequences[0].elements == 'tttacagctagctcagtcctaggtattatgctagc'

    @unittest.expectedFailure
    def test_combinatorial_derivation_3_2_conversion(self):
        """Test ability to convert combinatorial derivations between SBOL3 and SBOL2"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['constraints_library.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'constraints_library.nt'))

        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3)
        validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            self.assertEqual(doc2.validate(), 'Valid.')
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)
        doc3 = convert2to3(doc2)
        report = doc3.validate()
        assert len(report) == 0, "\n".join(str(issue) for issue in report)
        outfile = os.path.join(tmp_sub, 'round_tripped.nt')
        doc3.write(outfile)

        # check round trip
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'constraints_library.nt')
        assert filecmp.cmp(outfile, comparison_file), f'Round-tripped file {outfile} is not identical'

    def test_3to2_orientation_conversion(self):
        """Test ability to convert orientation from SBOL3to SBOL2"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['iGEM_SBOL2_imports.nt', 'feature_orientation_conversion.nt'])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, 'iGEM_SBOL2_imports.nt'))

        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3)
        validate_online = sbol2.Config.getOption(sbol2.ConfigOptions.VALIDATE_ONLINE)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            self.assertEqual(doc2.validate(), 'Valid.')
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)
        # ids of location block containing orientation before conversion
        location_ids_sbol3 = []

        def append_location_id_with_orientation(o):
            if isinstance(o, sbol3.Location):
                if hasattr(o, 'orientation') and o.orientation:
                    location_ids_sbol3.append(o.identity)
        doc3.traverse(append_location_id_with_orientation)
        # ids of location block containing orientation after conversion
        location_ids_sbol2 = []
        for c in doc2.componentDefinitions:
            for sa in c.sequenceAnnotations:
                for loc in sa.locations:
                    if hasattr(loc, 'orientation') and loc.orientation:
                        location_ids_sbol2.append(loc.identity)
                        assert loc.orientation == 'http://sbols.org/v2#inline'
        assert len(location_ids_sbol2) == 12
        assert collections.Counter(location_ids_sbol2) == collections.Counter(location_ids_sbol3)

        # also check the feeature orientations are getting converted
        doc3 = sbol3.Document()
        doc3.read('test/test_files/feature_orientation_conversion.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3)
        try:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, False)
            self.assertEqual(doc2.validate(), 'Valid.')
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.VALIDATE_ONLINE, validate_online)

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

    def test_id_map_conversion_from_fasta(self):
        """Test ability to convert from SBOL3 to FASTA"""
        """Test ability to convert from GenBank to SBOL3"""
        # Get the SBOL3 test document
        tmp_sub = copy_to_tmp(package=['BBa_J23101.fasta'])
        doc3 = convert_from_fasta(os.path.join(tmp_sub, 'BBa_J23101.fasta'), 'https://synbiohub.org/public/igem',
                                  identity_map={'BBa_J23101': 'https://somewhere_else.org/public/igem/BBa_J23101'})

        # Note: cannot directly round-trip because converter is lossy
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'BBa_J23101_from_fasta_altname.nt')
        comparison_doc = sbol3.Document()
        comparison_doc.read(comparison_file)
        assert not doc_diff(doc3, comparison_doc), f'Converted FASTA file not identical to {comparison_file}'

    def test_commandline(self):
        test_files = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_files')
        temp_name = tempfile.mkstemp()[1]
        test_file = {
            'fasta': os.path.join(test_files, 'BBa_J23101.fasta'),
            'genbank': os.path.join(test_files, 'BBa_J23101.gb'),
            'from_fasta': os.path.join(test_files, 'BBa_J23101_from_fasta.nt'),
            'from_genbank': os.path.join(test_files, 'BBa_J23101_from_genbank.nt'),
            'sbol3': os.path.join(test_files, 'BBa_J23101.nt'),
            'sbol323': os.path.join(test_files, 'BBa_J23101_3to2to3.nt')
        }

        # Run the generic command-line converter with a couple of different configurations:
        test_args = ['sbol-converter', '-o', temp_name, '-n', 'https://synbiohub.org/public/igem', 'FASTA', 'SBOL3',
                     test_file['fasta']]
        with patch.object(sys, 'argv', test_args):
            main()
        assert filecmp.cmp(temp_name, test_file['from_fasta']), f'Converted file {temp_name} is not identical'

        test_args = ['sbol-converter', '-o', temp_name, 'SBOL3', 'SBOL3', test_file['sbol3']]
        with patch.object(sys, 'argv', test_args):
            main()
        assert filecmp.cmp(temp_name, test_file['sbol3']), f'Converted file {temp_name} is not identical'

        # Run the other six tests
        test_args = ['fasta2sbol', '-o', temp_name, '-n', 'https://synbiohub.org/public/igem', test_file['fasta']]
        with patch.object(sys, 'argv', test_args):
            fasta2sbol()
        assert filecmp.cmp(temp_name, test_file['from_fasta']), f'Converted file {temp_name} is not identical'

        # genbank conversion should succeed the same way when not online if not given an online argument
        test_args = ['genbank2sbol', '-o', temp_name, '-n', 'https://synbiohub.org/public/igem', test_file['genbank']]
        with patch.object(sys, 'argv', test_args):
            genbank2sbol()
        assert filecmp.cmp(temp_name, test_file['from_genbank']), f'Converted file {temp_name} is not identical'

        test_args = ['sbol2fasta', '-o', temp_name, test_file['sbol3']]
        with patch.object(sys, 'argv', test_args):
            sbol2fasta()
        assert filecmp.cmp(temp_name, test_file['fasta']), f'Converted file {temp_name} is not identical'

        test_args = ['sbol2genbank', '-o', temp_name, test_file['sbol3']]
        with patch.object(sys, 'argv', test_args):
            sbol2genbank()
        assert filecmp.cmp(temp_name, test_file['genbank']), f'Converted file {temp_name} is not identical'

        # SBOL2 serialization is not stable, so test via round-trip instead
        test_args = ['sbol3to2', '-o', temp_name, test_file['sbol3']]
        with patch.object(sys, 'argv', test_args):
            sbol3to2()
        temp_name_2 = tempfile.mkstemp()[1]
        test_args = ['sbol2to3', '-o', temp_name_2, temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol2to3()
        assert filecmp.cmp(temp_name_2, test_file['sbol323']), f'Converted file {temp_name} is not identical'

    def test_online_conversion(self):
        """Test whether we are able to use the online converter"""
        test_files = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_files')
        temp_name = tempfile.mkstemp()[1]
        test_file = {
            'genbank': os.path.join(test_files, 'BBa_J23101.gb'),
            'from_genbank': os.path.join(test_files, 'BBa_J23101_from_genbank.nt'),
        }

        test_args = ['genbank2sbol', '-o', temp_name, '-n', 'https://synbiohub.org/public/igem', test_file['genbank'],
                     '--allow-genbank-online']
        with patch.object(sys, 'argv', test_args):
            genbank2sbol()
        assert filecmp.cmp(temp_name, test_file['from_genbank']), f'Converted file {temp_name} is not identical'


if __name__ == '__main__':
    unittest.main()
