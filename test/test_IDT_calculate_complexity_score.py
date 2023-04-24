import unittest
import filecmp
import sys
import tempfile
import os
import datetime
import sbol3
from unittest.mock import patch
import sbol_utilities.IDT_calculate_complexity_score
import sbol_utilities.sbol_diff



class TestIDTCalculateComplexityScore(unittest.TestCase):
    def test_IDT_calculate_complexity_score(self):
        username = 'jfgm'
        password = 'CompuIDT1598@'
        ClientID = '1598'
        ClientSecret = 'babd134e-fc99-4a84-8e8c-719e9125d5d1'

        #sbol3.set_namespace('http://sbolstandard.org/testfiles')
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

        DateTime = datetime.datetime.utcnow()
        # Create an Activity object to store timestamp
        sequence_timestamp = sbol3.Activity('Timestamp', end_time=DateTime.isoformat(timespec='seconds') + 'Z')
        #http://sbolstandard.org/testfiles/Timestamp
        #Verify that sbol_diff is 0, meaning there is no difference between documents
        assert 1 - sbol_utilities.sbol_diff.is_same(doc1, doc2), f'Converted file {temp_name} is not identical'

if __name__ == '__main__':
    unittest.main()