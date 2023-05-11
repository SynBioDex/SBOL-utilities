import unittest
import sys
import tempfile
import os
import sbol3
from unittest.mock import patch
import sbol_utilities.IDT_calculate_complexity_score
import sbol_utilities.sbol_diff

def is_same(doc1: sbol3.Document, doc2: sbol3.Document) -> bool:

    _, first_graph, second_graph = sbol_utilities.sbol_diff._diff_graphs(doc1.graph(), doc2.graph())

    # Ensure that the only diff is the timestamp
    ret = True
    for _, predicate1, _ in first_graph:
        if predicate1 == "http://www.w3.org/ns/prov#endedAtTime":
            continue
        else:
            ret = False
    for _, predicate2, _ in second_graph:
        if predicate2 == "http://www.w3.org/ns/prov#endedAtTime":
            continue
        else:
            ret = False
    return ret

class TestIDTCalculateComplexityScore(unittest.TestCase):
    def test_IDT_calculate_complexity_score(self):
        username = 'jfgm'
        password = 'CompuIDT1598@'
        ClientID = '1598'
        ClientSecret = 'babd134e-fc99-4a84-8e8c-719e9125d5d1'

        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc = sbol3.Document()
        doc.read(os.path.join(test_dir, 'test_files', 'BBa_J23101.nt'))

        results = sbol_utilities.IDT_calculate_complexity_score.IDT_calculate_complexity_score(username, password, ClientID, ClientSecret, doc)
        assert len(results) == 1, f'Expected 1 sequence, but found {len(results)}'

    def test_commandline(self):

        test_dir = os.path.dirname(os.path.realpath(__file__))
        temp_name = tempfile.mkstemp(suffix='.nt')[1]
        test_args = ['IDT_calculate_complexity_score.py','jfgm', 'CompuIDT1598@', '1598', 'babd134e-fc99-4a84-8e8c-719e9125d5d1',
                     os.path.join(test_dir, 'test_files', 'Test_file_Complexity_Scores.nt'), temp_name]
        with patch.object(sys, 'argv', test_args):
            sbol_utilities.IDT_calculate_complexity_score.main()

        comparison_file = os.path.join(test_dir, 'test_files', 'Comparison_file_Complexity_Scores.nt')

        doc1 = sbol3.Document()
        doc1.read(comparison_file)
        doc2 = sbol3.Document()
        doc2.read(temp_name)

        assert 1 - is_same(doc1, doc2), f'Converted file {temp_name} is not identical'
if __name__ == '__main__':
    unittest.main()