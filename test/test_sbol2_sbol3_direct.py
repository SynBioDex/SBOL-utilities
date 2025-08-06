import tempfile
from pathlib import Path

import unittest

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2
from sbol_utilities.sbol3_sbol2_conversion import SBOL3To2ConversionVisitor, BACKPORT2_VERSION
from sbol_utilities.sbol_diff import file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


class SBOLValidationError(Exception):
    """This exception class is intended for use within the context of TestCases to raise failures due to invalid SBOL
    documents."""
    pass


class SBOL2to3ConversionError(Exception):
    """This exception class is intended for use within the context of TestCases to raise failures converting SBOL2
    documents to SBOL3."""
    pass

class SBOL3to2ConversionError(Exception):
    """This exception class is intended for use within the context of TestCases to raise failures converting SBOL3
    documents to SBOL2."""
    pass


class TestDirectSBOL2SBOL3Conversion(unittest.TestCase):

    # TODO: turn on validation

    # J23101.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    def test_3to2_conversion(self):
        """Test ability to convert a simple part from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / 'BBa_J23101_patched.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        #report = doc2.validate()
        #self.assertEqual(len(report), 0, f'Validation failed: {report}')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'BBa_J23101.xml')))
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3_loop.validate()), 0)
            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
    '''

    # J23101.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    def test_2to3_conversion(self):
        """Test ability to convert a simple part from SBOL2 to SBOL3"""
        # Load an SBOL2 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / 'BBa_J23101.xml')
        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        self.assertEqual(len(doc3.validate()), 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
            doc2_loop = convert3to2(doc3, True)
            # report = doc2.validate()
            # self.assertEqual(len(report), 0, f'Validation failed: {report}')
            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'BBa_J23101.xml')))
    '''

    # sbol_3to2_implementation.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    def test_3to2_implementation_conversion(self):
        """Test ability to convert an implementation from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / 'sbol3_implementation.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        #report = doc2.validate()
        #self.assertEqual(len(report), 0, f'Validation failed: {report}')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'sbol_3to2_implementation.xml')))
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3_loop.validate()), 0)
            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'sbol3_implementation.nt')))
    '''

    # sbol_3to2_implementation.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    def test_2to3_implementation_conversion(self):
        """Test ability to convert an implementation from SBOL2 to SBOL3"""
        # Load an SBOL2 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / 'sbol_3to2_implementation.xml')
        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        self.assertEqual(len(doc3.validate()), 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'sbol3_implementation.nt')))
            doc2_loop = convert3to2(doc3, True)
            # report = doc2.validate()
            # self.assertEqual(len(report), 0, f'Validation failed: {report}')
            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'sbol_3to2_implementation.xml')))
    '''

    # sbol_3to2_collection.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    # sbol_3to2_collection.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    def test_3to2_collection_conversion(self):
        """Test ability to convert a collection from SBOL3 to SBOL2"""
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / 'sbol3_collection.nt')
        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        #report = doc2.validate()
        #self.assertEqual(len(report), 0, f'Validation failed: {report}')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'sbol_3to2_collection.xml')))
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3_loop.validate()), 0)
            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'sbol3_collection.nt')))
    '''

    # sbol_3to2_collection.xml is not SBOL compliant. Leaving conversions involving it for after the compliant converter is done
    '''
    def test_2to3_collection_conversion(self):
        """Test ability to convert a collection from SBOL2 to SBOL3"""
        # Load an SBOL2 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / 'sbol_3to2_collection.xml')
        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        self.assertEqual(len(doc3.validate()), 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'sbol3_collection.nt')))
            doc2_loop = convert3to2(doc3, True)
            # report = doc2.validate()
            # self.assertEqual(len(report), 0, f'Validation failed: {report}')
            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'sbol_3to2_collection.xml')))
    '''

    def test_empty_componentDefinition(self):
            """Test ability to convert a simple part from SBOL2 to SBOL3"""
            # Load an SBOL2 document and check its contents
            doc2 = sbol2.Document()
            doc2.read(TEST_FILES / 'empty_componentDefinition.xml')
            # Convert to SBOL3 and check contents
            doc3 = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3.validate()), 0)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp3 = Path(tmpdir) / 'doc3.nt'
                doc3.write(tmp3)
                self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'empty_componentDefinition.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'empty_componentDefinition.xml')))

            # Do the same for a file without versioning    
            doc2 = sbol2.Document()
            doc2.read(TEST_FILES / 'empty_componentDefinition_nover.xml')
            # Convert to SBOL3 and check contents
            doc3 = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3.validate()), 0)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp3 = Path(tmpdir) / 'doc3.nt'
                doc3.write(tmp3)
                self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'empty_componentDefinition_nover.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'empty_componentDefinition_nover.xml')))
                
    def test_minimal_sbol2_collection(self):
            """Test ability to convert a collection of simple parts from SBOL2 to SBOL3"""
            # Depends on working Component Definition conversion
            # Load an SBOL2 document and check its contents
            doc2 = sbol2.Document()
            doc2.read(TEST_FILES / 'minimal_sbol2_collection.xml')
            # Convert to SBOL3 and check contents
            doc3 = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3.validate()), 0)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp3 = Path(tmpdir) / 'doc3.nt'
                doc3.write(tmp3)
                self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'minimal_sbol2_collection.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'minimal_sbol2_collection.xml')))

                
    def test_sbol2_implementation(self):
            """Test ability to convert an implementation from SBOL2 to SBOL3"""
            # Load an SBOL2 document and check its contents
            doc2 = sbol2.Document()
            doc2.read(TEST_FILES / 'sbol_3to2_implementation_compliant.xml')
            # Convert to SBOL3 and check contents
            doc3 = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3.validate()), 0)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp3 = Path(tmpdir) / 'doc3.nt'
                doc3.write(tmp3)
                self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'sbol_3to2_implementation_compliant.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'sbol_3to2_implementation_compliant.xml')))

    def test_seq_componentDefinition(self):
            """Test ability to convert a Component Definition with a Sequence from SBOL2 to SBOL3"""
            # Depends on working Component Definition conversion
            # Load an SBOL2 document and check its contents
            doc2 = sbol2.Document()
            doc2.read(TEST_FILES / 'seq_componentDefinition.xml')
            # Convert to SBOL3 and check contents
            doc3 = convert2to3(doc2, use_native_converter=True)
            self.assertEqual(len(doc3.validate()), 0)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp3 = Path(tmpdir) / 'doc3.nt'
                doc3.write(tmp3)
                self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'seq_componentDefinition.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'seq_componentDefinition.xml')))

    def handle_2to3_conversion(self, test_filename: str, comparison_filename: str):
        """Provides a re-usable test handler for converting SBOL2 to SBOL3 with different test files
        :param test_filename: Name of an SBOL2 test file
        :param comparison_filename: Name of an SBOL3 file with expected conversion
    """
        """Test ability to convert a simple part from SBOL2 to SBOL3"""

        # Load an SBOL2 document and check its contents
        doc2 = sbol2.Document()
        doc2.read(TEST_FILES / test_filename)

        # Convert to SBOL3 and check contents
        doc3 = convert2to3(doc2, use_native_converter=True)
        report = doc3.validate()
        if len(report):
            raise SBOLValidationError(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp3 = Path(tmpdir) / 'doc3.nt'
            doc3.write(tmp3)
            if file_diff(str(tmp3), str(TEST_FILES / comparison_filename)):
                raise SBOL2to3ConversionError()

            # Round-trip back to SBOL2 and check contents
            doc2_loop = convert3to2(doc3, True)
            report = doc2_loop.validate()
            if report != 'Valid.':
                raise SBOLValidationError(report)

            tmp2 = Path(tmpdir) / 'doc2_loop.xml'
            doc2_loop.write(tmp2)
            if file_diff(str(tmp2), str(TEST_FILES / test_filename)):
                raise SBOL3to2ConversionError()

    def test_implementation_conversion(self):
        self.handle_2to3_conversion('sbol_3to2_implementation_compliant.xml', 'sbol_3to2_implementation_compliant.nt')

    def test_moduledefinition_conversion(self):
        self.handle_2to3_conversion('sbol_3to2_moduledefinition.xml', 'sbol_3to2_moduledefinition.nt')

    def test_functionalcomponent_conversion(self):
        self.handle_2to3_conversion('sbol_3to2_functionalcomponent.xml', 'sbol_3to2_functionalcomponent.nt')


class TestDirectSBOL3SBOL2Conversion(unittest.TestCase):

    def handle_3to2_conversion(self, test_filename: str, comparison_filename: str):
        """Provides a re-usable test handler for converting SBOL3 to SBOL2 with different test files
        :param test_filename: Name of an SBOL3 test file
        :param comparison_filename: Name of an SBOL2 file with expected conversion
    """
        # Load an SBOL3 document and check its contents
        doc3 = sbol3.Document()
        doc3.read(TEST_FILES / test_filename)

        # Convert to SBOL2 and check contents
        doc2 = convert3to2(doc3, True)
        report = doc2.validate()
        if report != 'Valid.':
            raise SBOLValidationError(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp2 = Path(tmpdir) / 'doc2.xml'
            doc2.write(tmp2)
            if file_diff(str(tmp2), str(TEST_FILES / comparison_filename)):
                raise SBOL3to2ConversionError()
 
            # Round-trip back to SBOL3 and check contents
            doc3_loop = convert2to3(doc2, use_native_converter=True)
            report = doc3_loop.validate()
            if len(report):
                raise SBOLValidationError(report)

            tmp3 = Path(tmpdir) / 'doc3_loop.nt'
            doc3_loop.write(tmp3)
            if file_diff(str(tmp3), str(TEST_FILES / test_filename)):
                raise SBOL2to3ConversionError()

    def test_implementation_conversion(self):
        self.handle_3to2_conversion('sbol_3to2_implementation_compliant.nt', 'sbol_3to2_implementation_compliant.xml')

    def test_moduledefinition_conversion(self):
        self.handle_3to2_conversion('sbol_3to2_moduledefinition.nt', 'sbol_3to2_moduledefinition.xml')
    
    def test_functionalcomponent_conversion(self):
        self.handle_3to2_conversion('sbol_3to2_functionalcomponent.nt', 'sbol_3to2_functionalcomponent.xml')

    def test_identity_conversion(self):
        """Test that 3->2 conversion of identity URIs conforms to SBOL-compliant URI structure."""
        visitor = SBOL3To2ConversionVisitor(sbol3.Document())
        c = sbol3.Component('http://example.com/foo', sbol3.SBO_DNA)
        self.assertEqual(visitor._sbol2_identity(c), 'http://example.com/foo')
        c.sbol2_version = '1'
        self.assertEqual(visitor._sbol2_identity(c), 'http://example.com/foo/1')

        # Test a non-TopLevel object
        sc = sbol3.SubComponent(c.identity)
        # URI is not initialized
        with self.assertRaises(ValueError):
            visitor._sbol2_identity(sc)
        # URI is initialized upon addition to parent
        c.features.append(sc)
        self.assertEqual(visitor._sbol2_identity(sc), 'http://example.com/foo/SubComponent1')

 
if __name__ == '__main__':
    unittest.main()
