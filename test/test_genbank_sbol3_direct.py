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

    def _test_genbank_to_sbol3(self, SAMPLE_SBOL3_FILE: Path, SAMPLE_GENBANK_FILE: Path):
        TEST_OUTPUT_SBOL3 = str(SAMPLE_SBOL3_FILE) + ".test"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(SAMPLE_GENBANK_FILE),
            TEST_OUTPUT_SBOL3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        sbol3_file_1 = sbol3.Document()
        sbol3_file_1.read(
            location=str(SAMPLE_SBOL3_FILE), file_format=sbol3.SORTED_NTRIPLES
        )
        assert not doc_diff(
            test_output_sbol3, sbol3_file_1
        ), f"Converted SBOL3 file: {TEST_OUTPUT_SBOL3} not identical to expected file: {SAMPLE_SBOL3_FILE}"
    
    def _test_sbol3_to_genbank(self, SAMPLE_SBOL3_FILE: str, SAMPLE_GENBANK_FILE: str):
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=[SAMPLE_SBOL3_FILE])
        doc3 = sbol3.Document()
        doc3.read(os.path.join(tmp_sub, SAMPLE_SBOL3_FILE))
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, SAMPLE_GENBANK_FILE + ".test")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=doc3, gb_file=outfile, write=True
        )
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(
            test_dir, "test_files", SAMPLE_GENBANK_FILE
        )
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {outfile} is not identical to expected file {comparison_file}"


    def test_gbtosbol3_1(self):
        """Test conversion of a simple genbank file with a single sequence"""
        GENBANK_FILE = Path(__file__).parent / "test_files" / "BBa_J23101.gb"
        SBOL3_FILE = (
            Path(__file__).parent
            / "test_files"
            / "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        self._test_genbank_to_sbol3(SAMPLE_SBOL3_FILE=SBOL3_FILE, SAMPLE_GENBANK_FILE=GENBANK_FILE)

    def test_gbtosbol3_2(self):
        """Test conversion of a simple genbank file with a multiple sequence with multiple features"""
        GENBANK_FILE = (
            Path(__file__).parent / "test_files" / "iGEM_SBOL2_imports.gb"
        )
        SBOL3_FILE = (
            Path(__file__).parent
            / "test_files"
            / "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        self._test_genbank_to_sbol3(SAMPLE_SBOL3_FILE=SBOL3_FILE, SAMPLE_GENBANK_FILE=GENBANK_FILE)

    def test_sbol3togb_1(self):
        """Test ability to convert from SBOL3 to GenBank using new converter"""
        SBOL3_FILE = "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        GENBANK_FILE = "BBa_J23101_from_sbol3_direct.gb"
        self._test_sbol3_to_genbank(SAMPLE_SBOL3_FILE=SBOL3_FILE, SAMPLE_GENBANK_FILE=GENBANK_FILE)

    def test_sbol3togb_2(self):
        """Test ability to convert from SBOL3 to GenBank with multiple records/features using new converter"""
        SBOL3_FILE = "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        GENBANK_FILE = "iGEM_SBOL2_imports_from_sbol3_direct.gb"
        self._test_sbol3_to_genbank(SAMPLE_SBOL3_FILE=SBOL3_FILE, SAMPLE_GENBANK_FILE=GENBANK_FILE)

    def test_round_trip_multiple_loc_feat(self):
        SAMPLE_GENBANK_FILE = "sequence2_modified.gb"
        sbol3.set_namespace(TEST_NAMESPACE)
        TEST_OUTPUT_SBOL3 = SAMPLE_GENBANK_FILE + ".nt"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(SAMPLE_GENBANK_FILE),
            TEST_OUTPUT_SBOL3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=[SAMPLE_GENBANK_FILE])
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, str(SAMPLE_GENBANK_FILE) + ".test")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=test_output_sbol3, gb_file=outfile, write=True
        )
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(
            test_dir, "test_files", SAMPLE_GENBANK_FILE
        )
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {outfile} is not identical to expected file {comparison_file}"
    
if __name__ == "__main__":
    unittest.main()
