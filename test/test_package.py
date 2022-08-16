import unittest
import os
from pathlib import Path
import tempfile
import shutil

import sbol3

from sbol_utilities import package
from sbol_utilities.helper_functions import sbol3_namespace
from sbol_utilities.package import PackageError
from sbol_utilities.sbol_diff import doc_diff, file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


class TestPackage(unittest.TestCase):
    def test_define_package_single_file(self):
        """Test defining a package from an SBOL document"""
        # Read in the test file
        doc_01 = sbol3.Document()
        doc_01.read(str(TEST_FILES / 'package_in_01.nt'))

        # Create the package and add it to a document
        out_doc = sbol3.Document()
        out_01 = package.doc_to_package(doc_01)
        out_doc.add(out_01)

        # Compare it to the saved results file, make sure they are the same
        expected = sbol3.Document()
        expected.read(str(TEST_FILES / 'package_out_01.nt'))
        self.assertFalse(doc_diff(out_doc, expected))

    def test_define_package_multi_file(self):
        """Test defining a package from multiple SBOL documents"""
        # Read in the test files
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc_01 = sbol3.Document()
        doc_01.read(os.path.join(test_dir, 'test_files', 'package_in_01.nt'))

        doc_02 = sbol3.Document()
        doc_02.read(os.path.join(test_dir, 'test_files', 'package_in_02.nt'))

        doc_03 = sbol3.Document()
        doc_03.read(os.path.join(test_dir, 'test_files', 'package_in_03.nt'))

        # Run the function
        # Here, I only want the package object, not any of the subpackages
        out_02 = package.docs_to_package(doc_01, [doc_02, doc_03])

        # Write a temporary file
        doc = sbol3.Document()
        doc.add(out_02)
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)

        # Compare it to the saved results file, make sure they are the same
        comparison_file = os.path.join(test_dir, 'test_files', 'package_out_02.nt')
        self.assertFalse(file_diff(tmp_out, comparison_file))

    def test_prefix_too_short(self):
        """ Test that having a sub-package with a different namespace than the 
        root package fails. All members of "package_in_01_error.nt" has the
        namespace "https://bad-example.org/MyPackage", whereas the subpackages
        are "https://example.org/MyPackage/promoters" and
        "https://example.org/MyPackage/repressors". Will raise a value error
        in check_prefix that "'The packages {root_package} and {sub_package}
        namespace URIs do not share the same URL scheme specifier or network
        location, and so do not represent a root and sub package.'
        """
        # Read in the test files
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc_01 = sbol3.Document()
        doc_01.read(os.path.join(test_dir, 'test_files', 'package_in_01_error.nt'))

        doc_02 = sbol3.Document()
        doc_02.read(os.path.join(test_dir, 'test_files', 'package_in_02.nt'))

        doc_03 = sbol3.Document()
        doc_03.read(os.path.join(test_dir, 'test_files', 'package_in_03.nt'))

        # Run the function
        with self.assertRaises(ValueError):
            package.docs_to_package(doc_01, [doc_02, doc_03])

    def test_subpackage_fails(self):
        """ Test that having one subpackage file with multiple namespaces fails.
        Raises value in define_package that not all members in the package have 
        the same namespace. "package_in_02_error.nt" has members with two 
        different namespaces, https://example.org/MyPackage/promoters and 
        https://example.org/MyPackage/inhibitors."""
        # Read in the test files
        test_dir = os.path.dirname(os.path.realpath(__file__))
        doc_01 = sbol3.Document()
        doc_01.read(os.path.join(test_dir, 'test_files', 'package_in_01.nt'))

        doc_02 = sbol3.Document()
        doc_02.read(os.path.join(test_dir, 'test_files', 'package_in_02_error.nt'))

        doc_03 = sbol3.Document()
        doc_03.read(os.path.join(test_dir, 'test_files', 'package_in_03.nt'))

        # Run the function
        with self.assertRaises(ValueError):
            package.docs_to_package(doc_01, [doc_02, doc_03])

    def test_make_package_from_MyPackage(self):
        """ Create a package based on the files in a directory (test/test_files/
        MyPackage). The function automatically saves the package files in the 
        .sip package directories of each subdirectory. """
        # Set the package directory
        test_dir = os.path.dirname(os.path.realpath(__file__))
        dir_name = os.path.join(test_dir, 'test_files', 'MyPackage')

        # Pass to the function
        package.directory_to_package(dir_name)

        # Compare all the package files to the saved results file, make sure
        # they are the same, then delete the package directory
        for root, _, _ in os.walk(dir_name):
            # Collect the output from the actual function
            # Want to get the path separate from the file for easy deleting
            out_path = os.path.join(root, '.sip')
            out_file = os.path.join(out_path, 'package.nt')

            # I have saved all the results to compare against in one
            # directory with the names corresponding to the subdirectory name
            # from the original directory
            file_name = root.split('/')[-1] + '.nt'
            comparison_file = os.path.join(test_dir,
                                           'test_files',
                                           'MyPackage-results',
                                           file_name)

            self.assertFalse(file_diff(out_file, comparison_file))

            # Delete the package directory
            # TODO: change to a temp directory so we don't have to do this
            shutil.rmtree(out_path, ignore_errors=True)

    def test_make_package_from_MyPackage_w_multiple_files(self):
        """ Create a package based on the files in a directory (test/test_files/
        MyPackage_w_multiple_files). The function automatically saves the 
        package file in the .sip package directories of each subdirectory. """
        # Set the package directory
        test_dir = os.path.dirname(os.path.realpath(__file__))
        dir_name = os.path.join(test_dir,
                                'test_files',
                                'MyPackage_w_multiple_files')

        # Pass to the function
        package.directory_to_package(dir_name)

        # Compare all the package files to the saved results file, make sure
        # they are the same, then delete the package directory
        for root, _, _ in os.walk(dir_name):
            # Collect the output from the actual function
            # Want to get the path separate from the file for easy deleting
            out_path = os.path.join(root, '.sip')
            out_file = os.path.join(out_path, 'package.nt')

            # I have saved all the results to compare against in one
            # directory with the names corresponding to the subdirectory name
            # from the original directory
            file_name = root.split('/')[-1] + '.nt'
            comparison_file = os.path.join(test_dir,
                                           'test_files',
                                           'MyPackage_w_multiple_files-results',
                                           file_name)

            self.assertFalse(file_diff(out_file, comparison_file))

            # Delete the package directory
            # TODO: change to a temp directory so we don't have to do this
            shutil.rmtree(out_path, ignore_errors=True)

    def test_make_package_from_MyPackage_w_sub_sub_packages(self):
        """ Create a package based on the files in a directory (test/test_files/
        MyPackage_w_sub_sub_packages). The function automatically saves the 
        package file in the .sip package directories of each subdirectory. """
        # Set the package directory
        test_dir = os.path.dirname(os.path.realpath(__file__))
        dir_name = os.path.join(test_dir,
                                'test_files',
                                'MyPackage_w_sub_sub_packages')

        # Pass to the function
        package.directory_to_package(dir_name)

        # Compare all the package files to the saved results file, make sure
        # they are the same, then delete the package directory
        for root, _, _ in os.walk(dir_name):
            # Collect the output from the actual function
            # Want to get the path separate from the file for easy deleting
            out_path = os.path.join(root, '.sip')
            out_file = os.path.join(out_path, 'package.nt')

            # I have saved all the results to compare against in one
            # directory with the names corresponding to the subdirectory name
            # from the original directory
            file_name = root.split('/')[-1] + '.nt'
            comparison_file = os.path.join(test_dir,
                                           'test_files',
                                           'MyPackage_w_sub_sub_packages-results',
                                           file_name)

            self.assertFalse(file_diff(out_file, comparison_file))

            # Delete the package directory
            # TODO: change to a temp directory so we don't have to do this
            shutil.rmtree(out_path, ignore_errors=True)

    def test_install_package(self):
        with tempfile.TemporaryDirectory() as temp_dir_name:
            tempdir = Path(temp_dir_name)
            # create a temporary package manager for testing
            package.ACTIVE_PACKAGE_MANAGER = package.PackageManager(tempdir)
            # make and install a miniature package
            doc = sbol3.Document()
            doc.read(str(TEST_FILES / 'BBa_J23101.nt'))
            p = package.doc_to_package(doc)
            package.install_package(p, doc)
            # check that the files that are created look like what is expected
            self.assertEqual(2, len(list(tempdir.iterdir())))
            self.assertFalse(file_diff(TEST_FILES / 'BBa_J23101.nt', tempdir / 'e9325cfb11264f3c300f592e33c97c04.nt'))
            catalog_doc = sbol3.Document()
            catalog_doc.read(str(tempdir / 'package-catalog.nt'))
            self.assertEqual(2, len(catalog_doc.objects))
            p = catalog_doc.find('https://synbiohub.org/package')
            self.assertEqual((tempdir / 'e9325cfb11264f3c300f592e33c97c04.nt').as_uri(),
                             p.attachments[0].lookup().source)

    def test_package_loader(self):
        """Test that package system can load packages and verify integrity of the load"""

        # Does not contain specified package
        with self.assertRaises(PackageError) as cm:
            package.load_package('https://synbiohub.org/public/', TEST_FILES / 'BBa_J23101_package.nt')
        self.assertTrue(str(cm.exception).startswith('Cannot find package https://synbiohub.org/public/package'))
        # object isn't a package
        with self.assertRaises(PackageError) as cm:
            package.load_package('https://synbiohub.org/public/BBa_J23101', TEST_FILES / 'BBa_J23101_bad_package.nt')
        msg = 'Object <Component https://synbiohub.org/public/BBa_J23101/package> is not a Package'
        self.assertTrue(str(cm.exception).startswith(msg))
        # Package has the wrong namespace
        with self.assertRaises(PackageError) as cm:
            package.load_package('https://synbiohub.org/public/igem', TEST_FILES / 'BBa_J23101_bad_package.nt')
        msg = 'Package https://synbiohub.org/public/igem/package should have namespace ' \
              'https://synbiohub.org/public/igem but found https://synbiohub.org'
        self.assertTrue(str(cm.exception).startswith(msg))
        # Package is missing members
        with self.assertRaises(PackageError) as cm:
            package.load_package('https://synbiohub.org/public/igem2', TEST_FILES / 'BBa_J23101_bad_package.nt')
        msg = 'Package https://synbiohub.org/public/igem2 was missing listed members: ' \
              '[\'https://synbiohub.org/public/igem/BBa_J23101_not_here\']'
        self.assertTrue(str(cm.exception).startswith(msg))
        # Package has unaccounted for objects
        with self.assertRaises(PackageError) as cm:
            package.load_package('https://synbiohub.org/public/igem3', TEST_FILES / 'BBa_J23101_bad_package.nt')
        msg = 'Package https://synbiohub.org/public/igem3 contains unexpected members: ' \
              '[\'https://synbiohub.org/public/BBa_J23101/package\', \'https://synbiohub.org/public/igem/package\', ' \
              '\'https://synbiohub.org/public/igem2/package\']'
        self.assertTrue(str(cm.exception).startswith(msg))

    def test_cross_document_lookup(self):
        """Test that package system correctly overrides the document lookup function to enable cross-package lookups"""
        # What I want for a load pattern:
        # sip install root-package-dir
        # Materials will be stored in Path.home() / ".sip"
        # A catalog is stored in Path.home() / ".sip" / "installed-packages.nt"
        # iGEM materials are stored in Path.home() / ".sip" / "igem"
        # sbol_utilities.package.load_package('igem')
        package.load_package('https://synbiohub.org/public/igem', TEST_FILES / 'BBa_J23101_package.nt')
        doc = sbol3.Document()
        with sbol3_namespace('http://foo.bar/baz'):
            doc.add(sbol3.Component('qux', sbol3.SBO_DNA,
                                    sequences=['https://synbiohub.org/public/igem/BBa_J23101_sequence']))

        c = doc.find('qux')
        self.assertEqual('https://synbiohub.org/public/igem/BBa_J23101_sequence', c.sequences[0].lookup().identity)


if __name__ == '__main__':
    unittest.main()
