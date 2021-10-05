import difflib
import filecmp
import unittest

from sbol_utilities.helper_functions import *


def assert_files_identical(file1: str, file2: str) -> None:
    """check if two files are identical; if not, report their diff

    :param file1: path of first file to compare
    :param file2: path of second file to compare
    :return: true if
    """
    if not filecmp.cmp(file1, file2, shallow=False):
        with open(file1, 'r') as f1:
            with open(file2, 'r') as f2:
                diff = difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file1, tofile=file2)
        raise AssertionError("File differs from expected value:\n"+''.join(diff))


class TestHelpers(unittest.TestCase):

    def test_url_sanitization(self):
        # SBOL2 version stripping:
        assert strip_sbol2_version('https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA/1') == \
               'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA'
        assert strip_sbol2_version('https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA') == \
               'https://synbiohub.programmingbiology.org/public/Eco1C1G1T1/LmrA'

        # displayId cleaning:
        assert url_to_identity('http://foo/bar/baz.qux') == 'http://foo/bar/baz_qux'

        # extension detection and stripping
        assert design_file_type('something.fasta') == 'FASTA'
        assert design_file_type('something.xlsx') == None
        assert design_file_type('something.xml') == 'SBOL2'
        assert design_file_type('something.nt') == 'SBOL3'
        assert strip_filetype_suffix('http://foo/bar/baz.gb') == 'http://foo/bar/baz'
        assert strip_filetype_suffix('http://foo/bar/baz.qux') == 'http://foo/bar/baz.qux'

if __name__ == '__main__':
    unittest.main()
