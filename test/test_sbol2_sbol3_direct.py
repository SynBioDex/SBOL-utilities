import tempfile
from pathlib import Path

import unittest

import sbol2
import sbol3

from sbol_utilities.conversion import convert2to3, convert3to2
from sbol_utilities.sbol_diff import file_diff

TEST_FILES = Path(__file__).parent / 'test_files'


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
                #self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
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
                #self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
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
                #self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
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
                #self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
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
                #self.assertFalse(file_diff(str(tmp3), str(TEST_FILES / 'BBa_J23101_patched.nt')))
                doc2_loop = convert3to2(doc3, True)
                # report = doc2.validate()
                # self.assertEqual(len(report), 0, f'Validation failed: {report}')
                tmp2 = Path(tmpdir) / 'doc2_loop.xml'
                doc2_loop.write(tmp2)
                self.assertFalse(file_diff(str(tmp2), str(TEST_FILES / 'seq_componentDefinition.xml')))
                
if __name__ == '__main__':
    unittest.main()
