import filecmp
import sys
import tempfile
import unittest
import os
from unittest.mock import patch

import openpyxl
import sbol3

import sbol_utilities.calculate_sequences
from sbol_utilities.excel_to_sbol import excel_to_sbol
from sbol_utilities.expand_combinatorial_derivations import expand_derivations


class TestDefineModule(unittest.TestCase):
    def test_define_module(self):
        """Test defining a module from an SBOL document"""
        # sbol3.set_namespace('http://sbolstandard.org/testfiles') # Is this what I want?
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc = sbol3.Document()
        doc.read(os.path.join(test_dir, 'test_files', 'module.nt'))
        prior_sequence_count = len([o for o in doc.objects if isinstance(o, sbol3.Sequence)])
        new_seqs = sbol_utilities.calculate_sequences.calculate_sequences(doc)
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)

        # check to see if all of the expected sequences have been filled in as anticipated
        # total number of new sequences should be: 20
        #   2018 Interlab: none - missing vector, prior parts all pasted in for vector
        #   FPs small: none with missing vector, 2x9 = 18 for insert combinations
        #   Round 1 order, All FPs: none - libraries
        #   UNSX-UP, BB-B0032-BB: 1 each = 2
        assert len(new_seqs) == 20, f'Expected 20 new sequences, but found {len(new_seqs)}'
        sequence_count = len([o for o in doc.objects if isinstance(o, sbol3.Sequence)])
        assert sequence_count - prior_sequence_count == len(new_seqs)
        # spot-check a couple of sequence lengths

        # run it again: no additional sequences should get computed
        new_seqs = sbol_utilities.calculate_sequences.calculate_sequences(doc)
        second_sequence_count = len([o for o in doc.objects if isinstance(o, sbol3.Sequence)])
        assert not new_seqs and sequence_count == second_sequence_count, f'Unexpected new sequences {new_seqs}'

        # make sure that what came out is exactly what was expected
        comparison_file = os.path.join(test_dir, 'test_files', 'expanded_with_sequences.nt')
        assert filecmp.cmp(tmp_out, comparison_file), f'Converted file {tmp_out} is not identical'

    def test_commandline(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        test_args = ['sbol-calculate-sequences', '-vv',
                     os.path.join(test_dir, 'test_files', 'module.nt'), '-o', temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol_utilities.calculate_sequences.main()
        comparison_file = os.path.join(test_dir, 'test_files', 'expanded_with_sequences.nt')
        assert filecmp.cmp(temp_name, comparison_file), f'Converted file {temp_name} is not identical'

if __name__ == '__main__':
    unittest.main()
