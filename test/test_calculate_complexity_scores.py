import unittest
import sys
import tempfile
import os
import sbol3
from unittest.mock import patch
import sbol_utilities.calculate_complexity_scores
import sbol_utilities.sbol_diff


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
                             (str(s1) == replaced_subject and p1 == p2 and o1 == o2) or
                             (s1 == s2 and p1 == p2 and str(o1) == replaced_subject))
               for (s1, p1, o1), (s2, p2, o2) in zip(sorted(first_graph), sorted(second_graph)))


class TestIDTCalculateComplexityScore(unittest.TestCase):
    def test_IDT_calculate_complexity_score(self):
        """Test that a library-call invocation of complexity scoring works"""
        username = 'jfgm'
        password = 'CompuIDT1598@'
        ClientID = '1598'
        ClientSecret = 'babd134e-fc99-4a84-8e8c-719e9125d5d1'

        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc = sbol3.Document()
        doc.read(os.path.join(test_dir, 'test_files', 'BBa_J23101.nt'))

        results = sbol_utilities.calculate_complexity_scores.IDT_calculate_complexity_score(username, password, ClientID, ClientSecret, doc)
        assert len(results) == 1, f'Expected 1 sequence, but found {len(results)}'

    def test_commandline(self):
        """Test that a command-line invocation of complexity scoring works"""
        test_dir = os.path.dirname(os.path.realpath(__file__))
        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        test_args = ['calculate_complexity_scores.py','jfgm', 'CompuIDT1598@', '1598', 'babd134e-fc99-4a84-8e8c-719e9125d5d1',
                     os.path.join(test_dir, 'test_files', 'Test_file_Complexity_Scores.nt'), temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol_utilities.calculate_complexity_scores.main()

        comparison_file = os.path.join(test_dir, 'test_files', 'Comparison_file_Complexity_Scores.nt')

        doc1 = sbol3.Document()
        doc1.read(comparison_file)
        doc2 = sbol3.Document()
        doc2.read(temp_name)

        self.assertTrue(same_except_timestamps(doc1, doc2))


if __name__ == '__main__':
    unittest.main()
