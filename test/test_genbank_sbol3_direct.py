import unittest
import filecmp
import sbol3
import os
from pathlib import Path
from helpers import copy_to_tmp
from sbol_utilities.sbol_diff import doc_diff
from sbol_utilities.sbol3_genbank_conversion import (
    GenBank_SBOL3_Converter,
    TEST_NAMESPACE,
)


class TestGenBankSBOL3(unittest.TestCase):
    # Create converter instance
    converter = GenBank_SBOL3_Converter()

    def test_gbtosbol3_1(self):
        """Test conversion of a simple genbank file with a single sequence"""
        SAMPLE_GENBANK_FILE_1 = Path(__file__).parent / "test_files" / "BBa_J23101.gb"
        SAMPLE_SBOL3_FILE_1 = (
            Path(__file__).parent
            / "test_files"
            / "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        TEST_OUTPUT_SBOL3 = str(SAMPLE_SBOL3_FILE_1) + ".test"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(SAMPLE_GENBANK_FILE_1),
            TEST_OUTPUT_SBOL3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        sbol3_file_1 = sbol3.Document()
        sbol3_file_1.read(
            location=str(SAMPLE_SBOL3_FILE_1), file_format=sbol3.SORTED_NTRIPLES
        )
        assert not doc_diff(
            test_output_sbol3, sbol3_file_1
        ), f"Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SAMPLE_SBOL3_FILE_1}"

    def test_gbtosbol3_2(self):
        """Test conversion of a simple genbank file with a multiple sequence with multiple features"""
        SAMPLE_GENBANK_FILE_2 = (
            Path(__file__).parent / "test_files" / "iGEM_SBOL2_imports.gb"
        )
        SAMPLE_SBOL3_FILE_2 = (
            Path(__file__).parent
            / "test_files"
            / "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        TEST_OUTPUT_SBOL3 = str(SAMPLE_SBOL3_FILE_2) + ".test"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(SAMPLE_GENBANK_FILE_2),
            TEST_OUTPUT_SBOL3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        sbol3_file_2 = sbol3.Document()
        sbol3_file_2.read(
            location=str(SAMPLE_SBOL3_FILE_2), file_format=sbol3.SORTED_NTRIPLES
        )
        assert not doc_diff(
            test_output_sbol3, sbol3_file_2
        ), f"Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SAMPLE_SBOL3_FILE_2}"

    def test_sbol3togb_1(self):
        """Test ability to convert from SBOL3 to GenBank using new converter"""
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=["BBa_J23101_from_genbank_to_sbol3_direct.nt"])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, "BBa_J23101_from_genbank_to_sbol3_direct.nt"))
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, "BBa_J23101.gb")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=doc3, gb_file=outfile, write=True
        )
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(
            test_dir, "test_files", "BBa_J23101_from_sbol3_direct.gb"
        )
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {comparison_file} is not identical"

    def test_sbol3togb_2(self):
        """Test ability to convert from SBOL3 to GenBank with multiple records/features using new converter"""
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=["iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"))
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, "iGEM_SBOL2_imports.gb")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=doc3, gb_file=outfile, write=True
        )
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(
            test_dir, "test_files", "iGEM_SBOL2_imports_from_sbol3_direct.gb"
        )
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {comparison_file} is not identical"


if __name__ == "__main__":
    unittest.main()
