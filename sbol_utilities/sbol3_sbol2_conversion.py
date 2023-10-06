import sbol3
import sbol2

SBOL2_VERSION_PREDICATE = 'http://sboltools.org/backport#sbol2version'


class SBOL3ConverterVisitor:

    doc2: sbol2.Document

    def __init__(self, doc2: sbol2.Document):
        self.doc2 = doc2

    def _convert_extension_properties(self, obj: sbol2.Identified):
        """Map over the other properties of an extension materials"""
        pass

    def _convert_identified(self, obj: sbol2.Identified):
        """Map over the other properties of an identified object"""
        pass

    def _convert_toplevel(self, obj: sbol2.TopLevel):
        """Map over the other properties of a toplevel object"""
        self._convert_identified(obj)
        pass

    @staticmethod
    def _sbol2_version(obj: sbol3.Identified):
        obj.sbol2_version = sbol3.TextProperty(obj, SBOL2_VERSION_PREDICATE, 0, 1)
        return obj.sbol2_version or '1'

    def visit_activity(self, a: sbol3.Activity):
        raise NotImplementedError('Conversion of Activity from SBOL3 to SBOL2 not yet implemented')

    def visit_agent(self, a: sbol3.Agent):
        raise NotImplementedError('Conversion of Agent from SBOL3 to SBOL2 not yet implemented')

    def visit_association(self, a: sbol3.Association):
        raise NotImplementedError('Conversion of Association from SBOL3 to SBOL2 not yet implemented')

    def visit_attachment(self, a: sbol3.Attachment):
        raise NotImplementedError('Conversion of Attachment from SBOL3 to SBOL2 not yet implemented')

    def visit_binary_prefix(self, a: sbol3.BinaryPrefix):
        raise NotImplementedError('Conversion of BinaryPrefix from SBOL3 to SBOL2 not yet implemented')

    def visit_collection(self, a: sbol3.Collection):
        raise NotImplementedError('Conversion of Collection from SBOL3 to SBOL2 not yet implemented')

    def visit_combinatorial_derivation(self, a: sbol3.CombinatorialDerivation):
        raise NotImplementedError('Conversion of CombinatorialDerivation from SBOL3 to SBOL2 not yet implemented')

    def visit_component(self, a: sbol3.Component):
        raise NotImplementedError('Conversion of Component from SBOL3 to SBOL2 not yet implemented')

    def visit_component_reference(self, a: sbol3.ComponentReference):
        raise NotImplementedError('Conversion of ComponentReference from SBOL3 to SBOL2 not yet implemented')

    def visit_constraint(self, a: sbol3.Constraint):
        raise NotImplementedError('Conversion of Constraint from SBOL3 to SBOL2 not yet implemented')

    def visit_cut(self, a: sbol3.Cut):
        raise NotImplementedError('Conversion of Cut from SBOL3 to SBOL2 not yet implemented')

    def visit_document(self, a: sbol3.Document):
        raise NotImplementedError('Conversion of Document from SBOL3 to SBOL2 not yet implemented')

    def visit_entire_sequence(self, a: sbol3.EntireSequence):
        raise NotImplementedError('Conversion of EntireSequence from SBOL3 to SBOL2 not yet implemented')

    def visit_experiment(self, a: sbol3.Experiment):
        raise NotImplementedError('Conversion of Experiment from SBOL3 to SBOL2 not yet implemented')

    def visit_experimental_data(self, a: sbol3.ExperimentalData):
        raise NotImplementedError('Conversion of ExperimentalData from SBOL3 to SBOL2 not yet implemented')

    def visit_externally_defined(self, a: sbol3.ExternallyDefined):
        raise NotImplementedError('Conversion of ExternallyDefined from SBOL3 to SBOL2 not yet implemented')

    def visit_implementation(self, a: sbol3.Implementation):
        raise NotImplementedError('Conversion of Implementation from SBOL3 to SBOL2 not yet implemented')

    def visit_interaction(self, a: sbol3.Interaction):
        raise NotImplementedError('Conversion of Interaction from SBOL3 to SBOL2 not yet implemented')

    def visit_interface(self, a: sbol3.Interface):
        raise NotImplementedError('Conversion of Interface from SBOL3 to SBOL2 not yet implemented')

    def visit_local_sub_component(self, a: sbol3.LocalSubComponent):
        raise NotImplementedError('Conversion of LocalSubComponent from SBOL3 to SBOL2 not yet implemented')

    def visit_measure(self, a: sbol3.Measure):
        raise NotImplementedError('Conversion of Measure from SBOL3 to SBOL2 not yet implemented')

    def visit_model(self, a: sbol3.Model):
        raise NotImplementedError('Conversion of Model from SBOL3 to SBOL2 not yet implemented')

    def visit_participation(self, a: sbol3.Participation):
        raise NotImplementedError('Conversion of Participation from SBOL3 to SBOL2 not yet implemented')

    def visit_plan(self, a: sbol3.Plan):
        raise NotImplementedError('Conversion of Plan from SBOL3 to SBOL2 not yet implemented')

    def visit_prefixed_unit(self, a: sbol3.PrefixedUnit):
        raise NotImplementedError('Conversion of PrefixedUnit from SBOL3 to SBOL2 not yet implemented')

    def visit_range(self, a: sbol3.Range):
        raise NotImplementedError('Conversion of Range from SBOL3 to SBOL2 not yet implemented')

    def visit_si_prefix(self, a: sbol3.SIPrefix):
        raise NotImplementedError('Conversion of SIPrefix from SBOL3 to SBOL2 not yet implemented')

    def visit_sequence(self, seq: sbol3.Sequence):
        # Make the Sequence object and add it to the document
        seq = sbol2.Sequence(seq.identity, seq.elements, encoding=seq.encoding, version=self._sbol2_version(seq))
        self.doc2.addSequence(seq)
        # Add all of the other TopLevel properties and extensions not already covered
        self._convert_toplevel(seq)

    def visit_sequence_feature(self, a: sbol3.SequenceFeature):
        raise NotImplementedError('Conversion of SequenceFeature from SBOL3 to SBOL2 not yet implemented')

    def visit_singular_unit(self, a: sbol3.SingularUnit):
        raise NotImplementedError('Conversion of SingularUnit from SBOL3 to SBOL2 not yet implemented')

    def visit_sub_component(self, a: sbol3.SubComponent):
        raise NotImplementedError('Conversion of SubComponent from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_division(self, a: sbol3.UnitDivision):
        raise NotImplementedError('Conversion of UnitDivision from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_exponentiation(self, a: sbol3.UnitExponentiation):
        raise NotImplementedError('Conversion of UnitExponentiation from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_multiplication(self, a: sbol3.UnitMultiplication):
        raise NotImplementedError('Conversion of UnitMultiplication from SBOL3 to SBOL2 not yet implemented')

    def visit_usage(self, a: sbol3.Usage):
        raise NotImplementedError('Conversion of Usage from SBOL3 to SBOL2 not yet implemented')

    def visit_variable_feature(self, a: sbol3.VariableFeature):
        raise NotImplementedError('Conversion of VariableFeature from SBOL3 to SBOL2 not yet implemented')


class SBOL2SBOL3Converter:
    @staticmethod
    def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
        """Convert an SBOL3 document to an SBOL2 document

        :param doc3: SBOL3 document to convert
        :returns: SBOL2 document
        """
        doc2 = sbol2.Document()
        doc3.accept(SBOL3ConverterVisitor(doc2))
        return doc2

    @staticmethod
    def convert2to3(doc2: sbol2.Document) -> sbol3.Document:
        """Convert an SBOL2 document to an SBOL3 document

        :param doc2: SBOL2 document to convert
        :returns: SBOL3 document
        """
        doc3 = sbol3.Document()
        # TODO: build converter here
        return doc3
