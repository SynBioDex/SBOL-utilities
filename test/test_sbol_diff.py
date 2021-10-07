import os
import sys
import unittest
from unittest.mock import patch

import sbol_utilities.sbol_diff

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_FILES_DIR = os.path.join(TEST_DIR, 'test_files')
SL_SBOL_PATH = os.path.join(TEST_FILES_DIR, 'simple_library.nt')
ESL_SBOL_PATH = os.path.join(TEST_FILES_DIR, 'expanded_simple_library.nt')


class TestSbolDiff(unittest.TestCase):

    def test_command_line(self):
        test_args = ['sbol_diff', ESL_SBOL_PATH, ESL_SBOL_PATH]
        # Diff the same file, expecting no differences
        with patch.object(sys, 'argv', test_args):
            status = sbol_utilities.sbol_diff.main()
        self.assertEqual(0, status)
        # Diff two different files, use -s silent mode to prevent
        # unsightly output to terminal
        test_args = ['sbol_diff', '-s', ESL_SBOL_PATH, SL_SBOL_PATH]
        with patch.object(sys, 'argv', test_args):
            status = sbol_utilities.sbol_diff.main()
        self.assertEqual(1, status)

    def test_sbol_diff(self):
        # Invoke sbol_utilities.sbol_diff.sbol_diff directly
        actual = sbol_utilities.sbol_diff.file_diff(ESL_SBOL_PATH,
                                                    ESL_SBOL_PATH,
                                                    silent=True)
        expected = 0
        self.assertEqual(expected, actual)
        actual = sbol_utilities.sbol_diff.file_diff(ESL_SBOL_PATH,
                                                    SL_SBOL_PATH,
                                                    silent=True)
        expected = 1
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
