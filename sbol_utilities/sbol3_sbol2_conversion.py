import sbol3
import sbol2

# Namespaces
from rdflib import URIRef

BACKPORT_NAMESPACE = 'http://sboltools.org/backport#'
BACKPORT2_VERSION = f'{BACKPORT_NAMESPACE}sbol2version'
BACKPORT3_NAMESPACE = f'{BACKPORT_NAMESPACE}sbol3namespace'

NON_EXTENSION_PROPERTY_PREFIXES = {sbol3.SBOL3_NS, sbol3.SBOL2_NS,  # SBOL 2 & 3 namespaces
                                   sbol3.RDF_NS, sbol3.PROV_NS, sbol3.OM_NS,  # Standard ontologies
                                   BACKPORT_NAMESPACE}  # Information added by this converter


class SBOL3To2ConversionVisitor:
    """This class is used to map every object in an SBOL3 document into an empty SBOL2 document"""

    doc2: sbol2.Document

    def __init__(self, doc3: sbol3.Document):
        # Create the target document
        self.doc2 = sbol2.Document()
        #   # Immediately run the conversion
        self._convert(doc3)

    def _convert(self, doc3: sbol3.Document):
        # Bind standard namespaces that aren't bound by default in pySBOL2
        self.doc2.addNamespace(BACKPORT_NAMESPACE, 'backport')
        self.doc2.addNamespace(sbol3.PROV_NS, 'prov')
        self.doc2.addNamespace(sbol3.OM_NS, 'om')
        self.doc2.addNamespace('http://purl.org/dc/terms/', 'dcterms')

        # Override parameters that will otherwise interfere in conversion, saving old values
        saved_compliance = sbol2.Config.getOption(sbol2.ConfigOptions.SBOL_COMPLIANT_URIS.value)
        sbol2.Config.setOption(sbol2.ConfigOptions.SBOL_COMPLIANT_URIS.value, False)
        saved_homespace = sbol2.getHomespace()
        sbol2.setHomespace('')

        # Try conversion, resetting saved parameter values afterward
        try:
            doc3.accept(self)
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.SBOL_COMPLIANT_URIS.value, saved_compliance)
            sbol2.setHomespace(saved_homespace)

    @staticmethod
    def _convert_extension_properties(obj3: sbol3.Identified, obj2: sbol2.Identified):
        """Copy over extension properties"""
        extension_properties = (p for p in obj3.properties
                                if not any(p.startswith(prefix) for prefix in NON_EXTENSION_PROPERTY_PREFIXES))
        for p in extension_properties:
            obj2.properties[p] = obj3._properties[p]  # Can't use setPropertyValue because it may not be a string

    def _convert_identified(self, obj3: sbol3.Identified, obj2: sbol2.Identified):
        """Map over the other properties of an identified object"""
        self._convert_extension_properties(obj3, obj2)
        # Map over equivalent properties
        obj2.displayId = obj3.display_id
        obj2.name = obj3.name
        obj2.description = obj3.description
        obj2.wasDerivedFrom = obj3.derived_from
        obj2.wasGeneratedBy = obj3.generated_by
        # Turn measures into extension properties
        if obj3.measures:
            raise NotImplementedError('Conversion of measures from SBOL3 to SBOL2 not yet implemented')
        pass

    def _convert_toplevel(self, obj3: sbol3.TopLevel, obj2: sbol2.TopLevel):
        """Map over the other properties of a TopLevel object"""
        self._convert_identified(obj3, obj2)
        obj2.attachments = [a.identity for a in obj3.attachments]
        obj2.properties[BACKPORT3_NAMESPACE] = [URIRef(obj3.namespace)]

    @staticmethod
    def _sbol2_version(obj: sbol3.Identified):
        obj.sbol2_version = sbol3.TextProperty(obj, BACKPORT2_VERSION, 0, 1)
        return obj.sbol2_version or '1'

    def visit_activity(self, act3: sbol3.Activity):
        # Make the Activity object and add it to the document
        act2 = sbol2.Activity(act3.identity, version=self._sbol2_version(act3))
        if act3.types:
            if len(act3.types) > 1:
                raise NotImplementedError('Conversion of multi-type activities to SBOL2 not yet implemented:'
                                          'pySBOL2 currently supports a maximum of one type per activity'
                                          'Bug: https://github.com/SynBioDex/pySBOL2/issues/428')
            act2.types = act3.types[0]  # Take first type from list of length 1
        act2.startedAtTime = act3.start_time
        act2.endedAtTime = act3.end_time
        act2.usages = act3.usage
        act2.associations = act3.association
        # TODO: pySBOL3 is currently missing wasInformedBy (https://github.com/SynBioDex/pySBOL3/issues/436
        # act2.wasInformedBy = act3.informed_by
        self.doc2.activities.add(act2)
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(act3, act2)

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

    def visit_component(self, cp3: sbol3.Component):
        # Remap type if it's one of the ones that needs remapping; otherwise pass through unchanged
        type_map = {sbol3.SBO_DNA: sbol2.BIOPAX_DNA,  # TODO: distinguish biopax Dna from DnaRegion
                    sbol3.SBO_RNA: sbol2.BIOPAX_RNA,  # TODO: distinguish biopax Rna from RnaRegion
                    sbol3.SBO_PROTEIN: sbol2.BIOPAX_PROTEIN,
                    sbol3.SBO_SIMPLE_CHEMICAL: sbol2.BIOPAX_SMALL_MOLECULE,
                    sbol3.SBO_NON_COVALENT_COMPLEX: sbol2.BIOPAX_COMPLEX}
        types2 = [type_map.get(t, t) for t in cp3.types]
        # Make the Component object and add it to the document
        cp2 = sbol2.ComponentDefinition(cp3.identity, types2, version=self._sbol2_version(cp3))
        self.doc2.addComponentDefinition(cp2)
        # Convert the Component properties not covered by the constructor
        cp2.roles = cp3.roles
        cp2.sequences = cp3.sequences
        if cp3.features:
            raise NotImplementedError('Conversion of Component features from SBOL3 to SBOL2 not yet implemented')
        if cp3.interactions:
            raise NotImplementedError('Conversion of Component interactions from SBOL3 to SBOL2 not yet implemented')
        if cp3.constraints:
            raise NotImplementedError('Conversion of Component constraints from SBOL3 to SBOL2 not yet implemented')
        if cp3.interface:
            raise NotImplementedError('Conversion of Component interface from SBOL3 to SBOL2 not yet implemented')
        if cp3.models:
            raise NotImplementedError('Conversion of Component models from SBOL3 to SBOL2 not yet implemented')
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(cp3, cp2)

    def visit_component_reference(self, a: sbol3.ComponentReference):
        raise NotImplementedError('Conversion of ComponentReference from SBOL3 to SBOL2 not yet implemented')

    def visit_constraint(self, a: sbol3.Constraint):
        raise NotImplementedError('Conversion of Constraint from SBOL3 to SBOL2 not yet implemented')

    def visit_cut(self, a: sbol3.Cut):
        raise NotImplementedError('Conversion of Cut from SBOL3 to SBOL2 not yet implemented')

    def visit_document(self, doc3: sbol3.Document):
        for obj in doc3.objects:
            obj.accept(self)

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

    def visit_sequence(self, seq3: sbol3.Sequence):
        # Remap encoding if it's one of the ones that needs remapping; otherwise pass through unchanged
        encoding_map = {sbol3.IUPAC_DNA_ENCODING: sbol2.SBOL_ENCODING_IUPAC,
                        sbol3.IUPAC_PROTEIN_ENCODING: sbol2.SBOL_ENCODING_IUPAC_PROTEIN,
                        sbol3.SMILES_ENCODING: sbol2.SBOL_ENCODING_SMILES}
        encoding2 = encoding_map.get(seq3.encoding, seq3.encoding)
        # Make the Sequence object and add it to the document
        seq2 = sbol2.Sequence(seq3.identity, seq3.elements, encoding=encoding2, version=self._sbol2_version(seq3))
        self.doc2.addSequence(seq2)
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(seq3, seq2)

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


def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
    """Convert an SBOL3 document to an SBOL2 document

    :param doc3: SBOL3 document to convert
    :returns: SBOL2 document
    """
    converter = SBOL3To2ConversionVisitor(doc3)
    return converter.doc2


def convert2to3(doc2: sbol2.Document) -> sbol3.Document:
    """Convert an SBOL2 document to an SBOL3 document

    :param doc2: SBOL2 document to convert
    :returns: SBOL3 document
    """
    doc3 = sbol3.Document()
    raise NotImplementedError('Conversion from SBOL2 to SBOL3 not yet implemented')
    return doc3
