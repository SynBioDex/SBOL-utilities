import unittest
import sbol3
from sbol_utilities.sbol_diff import doc_diff
from sbol_utilities.sbol3_genbank_conversion import convert_genbank_to_sbol3, \
    GENBANK_FILE_1, SBOL3_FILE_1

class TestGenBank2SBOL3(unittest.TestCase):
    def test_simple_file_1(self):
        """Test conversion of a simple genbank file with a single sequence"""
        sbol3.set_namespace("https://testing.sbol3.genbank/")
        TEST_OUTPUT_SBOL3 = SBOL3_FILE_1 + ".test" 
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = convert_genbank_to_sbol3(GENBANK_FILE_1, TEST_OUTPUT_SBOL3, 
                            namespace="https://testing.sbol3.genbank/", write=False)
        sbol3_file_1 = sbol3.Document()
        sbol3_file_1.read(location=SBOL3_FILE_1, file_format=sbol3.SORTED_NTRIPLES)
        assert not doc_diff(test_output_sbol3, sbol3_file_1), \
            f'Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SBOL3_FILE_1}'

if __name__ == '__main__':
    unittest.main()
