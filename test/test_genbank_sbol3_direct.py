import unittest
import sbol3
from pathlib import Path
from sbol_utilities.sbol_diff import doc_diff
from sbol_utilities.sbol3_genbank_conversion import GenBank_SBOL3_Converter, TEST_NAMESPACE

class TestGenBank2SBOL3(unittest.TestCase):
    # Create converter instance
    converter = GenBank_SBOL3_Converter()
    def test_simple_file_1(self):
        """Test conversion of a simple genbank file with a single sequence"""
        SAMPLE_GENBANK_FILE_1 = str(Path(__file__).parent) + "/test_files/" + "BBa_J23101.gb"
        SAMPLE_SBOL3_FILE_1 = str(Path(__file__).parent) + "/test_files/" + "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        sbol3.set_namespace(TEST_NAMESPACE)
        TEST_OUTPUT_SBOL3 = SAMPLE_SBOL3_FILE_1 + ".test" 
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(SAMPLE_GENBANK_FILE_1, TEST_OUTPUT_SBOL3, 
                            namespace=TEST_NAMESPACE, write=False)
        sbol3_file_1 = sbol3.Document()
        sbol3_file_1.read(location=SAMPLE_SBOL3_FILE_1, file_format=sbol3.SORTED_NTRIPLES)
        assert not doc_diff(test_output_sbol3, sbol3_file_1), \
            f'Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SAMPLE_SBOL3_FILE_1}'

    def test_simple_file_2(self):
        """Test conversion of a simple genbank file with a multiple sequence with multiple features"""
        SAMPLE_GENBANK_FILE_2 = str(Path(__file__).parent) + "/test_files/" + "iGEM_SBOL2_imports.gb"
        SAMPLE_SBOL3_FILE_2 = str(Path(__file__).parent) + "/test_files/" + "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        sbol3.set_namespace(TEST_NAMESPACE)
        TEST_OUTPUT_SBOL3 = SAMPLE_SBOL3_FILE_2 + ".test" 
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(SAMPLE_GENBANK_FILE_2, TEST_OUTPUT_SBOL3, 
                            namespace=TEST_NAMESPACE, write=False)
        sbol3_file_2 = sbol3.Document()
        sbol3_file_2.read(location=SAMPLE_SBOL3_FILE_2, file_format=sbol3.SORTED_NTRIPLES)
        assert not doc_diff(test_output_sbol3, sbol3_file_2), \
            f'Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SAMPLE_SBOL3_FILE_2}'

if __name__ == '__main__':
    unittest.main()
