"""Tests for calculating sequence synthesis complexity scores via the IDT interface

To run these tests, you will need IDT access credentials (see: https://www.idtdna.com/pages/tools/apidoc)
The values of the IDT access credentials should be stored in a file in the top level directory called
'test_secret_idt_credentials.json', with the contents of the form:
{ "username": "username", "password": "password", "ClientID": "####", "ClientSecret": "XXXXXXXXXXXXXXXXXXX" }
"""
from pathlib import Path

import json

import unittest
import sys
import tempfile
import sbol3
from unittest.mock import patch
from sbol_utilities.calculate_complexity_scores import IDTAccountAccessor, idt_calculate_complexity_scores, \
    idt_calculate_sequence_complexity_scores, get_complexity_scores
import sbol_utilities.sbol_diff

# TODO: add to readme

def same_except_timestamps(doc1: sbol3.Document, doc2: sbol3.Document) -> bool:
    """Check that the only triple-level difference between two SBOL documents is their time-stamps

    :param doc1: first document to compare
    :param doc2: second document to compare
    :returns: True if identical, false if not
    """
    _, first_graph, second_graph = sbol_utilities.sbol_diff._diff_graphs(doc1.graph(), doc2.graph())
    replaced_subject = 'http://igem.org/IDT_complexity_score/Complexity_Report_20230516T194547Z_a2efceb0'
    # Return true only if all differences are time-stamps or the activity name
    ignored_predicates = {sbol3.PROV_ENDED_AT_TIME, sbol3.SBOL_DISPLAY_ID}
    return all(p1 == p2 and (str(p1) in ignored_predicates or
                             (str(s1) == replaced_subject and o1 == o2) or
                             (s1 == s2 and str(o1) == replaced_subject))
               for (s1, p1, o1), (s2, p2, o2) in zip(sorted(first_graph), sorted(second_graph)))


class TestIDTCalculateComplexityScore(unittest.TestCase):

    @unittest.skipIf(sys.platform == 'win32', reason='Not working on Windows https://github.com/SynBioDex/SBOL-utilities/issues/221')
    def test_IDT_calculate_complexity_score(self):
        """Test that a library-call invocation of complexity scoring works"""
        test_dir = Path(__file__).parent
        with open(test_dir.parent / 'test_secret_idt_credentials.json') as test_credentials:
            idt_accessor = IDTAccountAccessor.from_json(json.load(test_credentials))

        doc = sbol3.Document()
        doc.read(test_dir / 'test_files' / 'BBa_J23101.nt')

        # Check the scores - they should initially be all missing
        sequences = [obj for obj in doc if isinstance(obj, sbol3.Sequence)]
        scores = get_complexity_scores(sequences)
        self.assertEqual(scores, dict())
        # Compute sequences for
        results = idt_calculate_sequence_complexity_scores(idt_accessor, sequences)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[sequences[0]], 0)  # score is zero because the sequence both short and easy
        scores = get_complexity_scores(sequences)
        self.assertEqual(scores, results)

        # Compute results again: results should be blank, because the calculation is already made
        results = idt_calculate_complexity_scores(idt_accessor, doc)
        self.assertEqual(len(results), 0)
        self.assertEqual(results, dict())
        scores = get_complexity_scores(sequences)
        self.assertEqual(scores, {sequences[0]: 0})

    @unittest.skipIf(sys.platform == 'win32', reason='Not working on Windows https://github.com/SynBioDex/SBOL-utilities/issues/221')
    def test_commandline(self):
        """Test that a command-line invocation of complexity scoring works"""
        test_dir = Path(__file__).parent
        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        test_args = ['calculate_complexity_scores.py',
                     '--credentials', str(test_dir.parent / 'test_secret_idt_credentials.json'),
                     str(test_dir / 'test_files' / 'Test_file_Complexity_Scores.nt'), temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol_utilities.calculate_complexity_scores.main()

        # Compare expected results to actual output file
        expected = sbol3.Document()
        expected.read(test_dir / 'test_files' / 'Comparison_file_Complexity_Scores.nt')
        generated = sbol3.Document()
        generated.read(temp_name)
        self.assertTrue(same_except_timestamps(expected, generated))


if __name__ == '__main__':
    unittest.main()
