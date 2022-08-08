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

    def _test_genbank_to_sbol3(self, sample_sbol3_file: Path, sample_genbank_file: Path):
        """Helper method to test conversion of a given GenBank file to SBOL3 using new converter.
        :param SAMPLE_SBOL3_FILE: Path of expected SBOL3 converted file
        :param SAMPLE_GENBANK_FILE: Path of given GenBank file to convert
        """
        test_output_sbol3 = str(sample_sbol3_file) + ".test"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(sample_genbank_file),
            test_output_sbol3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        sbol3_file_1 = sbol3.Document()
        sbol3_file_1.read(
            location=str(sample_sbol3_file), file_format=sbol3.SORTED_NTRIPLES
        )
        assert not doc_diff(
            test_output_sbol3, sbol3_file_1
        ), f"Converted SBOL3 file: {test_output_sbol3} not identical to expected file: {sample_sbol3_file}"
    
    def _test_sbol3_to_genbank(self, sample_sbol3_file: Path, sample_genbank_file: Path):
        """Helper method to test conversion of a given SBOL3 file to GenBank using new converter.
        :param SAMPLE_SBOL3_FILE: Path of given SBOL3 file to convert
        :param SAMPLE_GENBANK_FILE: Path of expected GenBank converted file 
        """
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=[str(sample_sbol3_file)])
        doc3 = sbol3.Document()
        doc3.read(str(sample_sbol3_file))
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, str(sample_genbank_file).split("/")[-1] + ".test")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=doc3, gb_file=outfile, write=True
        )
        comparison_file = str(sample_genbank_file)
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {outfile} is not identical to expected file {comparison_file}"

    def _test_round_trip_genbank(self, sample_genbank_file: Path):
        """Helper method to test conversion of a given GenBank file to SBOL3 and then back to GenBank 
        and confirm the final file is exactly the same as the initial provided file.
        :param SAMPLE_GENBANK_FILE: Path of given GenBank file to round trip test
        """
        sbol3.set_namespace(TEST_NAMESPACE)
        test_output_sbol3 = str(sample_genbank_file) + ".nt"
        # Don't write to file for testing, we directly compare sbol documents
        test_output_sbol3 = self.converter.convert_genbank_to_sbol3(
            str(sample_genbank_file),
            test_output_sbol3,
            namespace=TEST_NAMESPACE,
            write=False,
        )
        # create tmp directory to store generated genbank file in for comparison
        tmp_sub = copy_to_tmp(package=[str(sample_genbank_file)])
        # Convert to GenBank and check contents
        outfile = os.path.join(tmp_sub, str(sample_genbank_file).split("/")[-1] + ".test")
        self.converter.convert_sbol3_to_genbank(
            sbol3_file=None, doc=test_output_sbol3, gb_file=outfile, write=True
        )
        comparison_file = str(sample_genbank_file)
        assert filecmp.cmp(
            outfile, comparison_file
        ), f"Converted GenBank file {outfile} is not identical to expected file {comparison_file}"

    def test_gbtosbol3_1(self):
        """Test conversion of a simple genbank file with a single sequence"""
        genbank_file = Path(__file__).parent / "test_files" / "BBa_J23101.gb"
        sbol3_file = (
            Path(__file__).parent
            / "test_files"
            / "sbol3_genbank_conversion"
            / "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        self._test_genbank_to_sbol3(sample_sbol3_file=sbol3_file, sample_genbank_file=genbank_file)

    def test_gbtosbol3_2(self):
        """Test conversion of a simple genbank file with a multiple sequence with multiple features"""
        genbank_file = (
            Path(__file__).parent / "test_files" / "iGEM_SBOL2_imports.gb"
        )
        sbol3_file = (
            Path(__file__).parent
            / "test_files"
            / "sbol3_genbank_conversion"
            / "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        )
        sbol3.set_namespace(TEST_NAMESPACE)
        self._test_genbank_to_sbol3(sample_sbol3_file=sbol3_file, sample_genbank_file=genbank_file)

    def test_sbol3togb_1(self):
        """Test ability to convert from SBOL3 to GenBank using new converter"""
        genbank_file = (
            Path(__file__).parent / "test_files" / "sbol3_genbank_conversion" / "BBa_J23101_from_sbol3_direct.gb"
        )
        sbol3_file = (
            Path(__file__).parent
            / "test_files"
            / "sbol3_genbank_conversion"
            / "BBa_J23101_from_genbank_to_sbol3_direct.nt"
        )
        self._test_sbol3_to_genbank(sample_sbol3_file=sbol3_file, sample_genbank_file=genbank_file)

    def test_sbol3togb_2(self):
        """Test ability to convert from SBOL3 to GenBank with multiple records/features using new converter"""
        genbank_file = (
            Path(__file__).parent / "test_files" / "sbol3_genbank_conversion" / "iGEM_SBOL2_imports_from_sbol3_direct.gb"
        )
        sbol3_file = (
            Path(__file__).parent
            / "test_files"
            / "sbol3_genbank_conversion"
            / "iGEM_SBOL2_imports_from_genbank_to_sbol3_direct.nt"
        )
        self._test_sbol3_to_genbank(sample_sbol3_file=sbol3_file, sample_genbank_file=genbank_file)

    def test_round_trip_extra_properties(self):
        """Test ability to produce same genbank file on round trip when original genbank file has non standard
        values for extraneous properties
        """
        genbank_file = (
            Path(__file__).parent / "test_files" / "sbol3_genbank_conversion" / "test_extra_properties.gb"
        )
        self._test_round_trip_genbank(genbank_file)

    def test_round_trip_multiple_loc_feat(self):
        """Test ability to produce same genbank file on round trip when original genbank file has multiple 
        locations on a feature
        """
        genbank_file = (
            Path(__file__).parent / "test_files" / "sbol3_genbank_conversion" / "multiple_feature_locations.gb"
        )
        self._test_round_trip_genbank(genbank_file)
    

if __name__ == "__main__":
    unittest.main()
