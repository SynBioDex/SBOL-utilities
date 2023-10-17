import sbol3
import sbol2
from sbol2 import mapsto, model, sequenceconstraint

# Namespaces
from rdflib import URIRef

BACKPORT_NAMESPACE = 'http://sboltools.org/backport#'
BACKPORT2_VERSION = f'{BACKPORT_NAMESPACE}sbol2version'
BACKPORT3_NAMESPACE = f'{BACKPORT_NAMESPACE}sbol3namespace'

NON_EXTENSION_PROPERTY_PREFIXES = {sbol3.SBOL3_NS, sbol3.SBOL2_NS,  # SBOL 2 & 3 namespaces
                                   sbol3.RDF_NS, sbol3.PROV_NS, sbol3.OM_NS,  # Standard ontologies
                                   BACKPORT_NAMESPACE}  # Information added by this converter
SBOL2_NON_EXTENSION_PROPERTY_PREFIXES = NON_EXTENSION_PROPERTY_PREFIXES.union({
    'http://purl.org/dc/terms/description', 'http://purl.org/dc/terms/title'})


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
            # TODO: make sure that complex extension objects (e.g., from SBOLFactory) are properly converted
            # TODO: make sure that unhandled SBOL child objects / properties will throw errors
            # TODO: check if we need to add post-creation fix-up of links, to ensure they point to objects
        finally:
            sbol2.Config.setOption(sbol2.ConfigOptions.SBOL_COMPLIANT_URIS.value, saved_compliance)
            sbol2.setHomespace(saved_homespace)

    @staticmethod
    def _convert_extension_properties(obj3: sbol3.Identified, obj2: sbol2.Identified):
        """Copy over extension properties"""
        extension_properties = (p for p in obj3.properties
                                if not any(p.startswith(prefix) for prefix in NON_EXTENSION_PROPERTY_PREFIXES))
        for p in extension_properties:
            obj2.properties[p] = obj3._properties[p].copy()  # Can't use setPropertyValue because it may not be a string

    @staticmethod
    def _value_or_property(obj3: sbol3.Identified, value, prop: str):
        if prop in obj3._properties and len(obj3._properties[prop]) == 1:
            return value or obj3._properties[prop][0]
        return value

    def _convert_identified(self, obj3: sbol3.Identified, obj2: sbol2.Identified):
        """Map over the other properties of an identified object"""
        self._convert_extension_properties(obj3, obj2)
        # Map over equivalent properties
        obj2.displayId = obj3.display_id
        obj2.name = self._value_or_property(obj3, obj3.name, 'http://purl.org/dc/terms/title')
        obj2.description = self._value_or_property(obj3, obj3.description, 'http://purl.org/dc/terms/description')
        obj2.wasDerivedFrom = obj3.derived_from
        obj2.wasGeneratedBy = obj3.generated_by
        # Turn measures into extension properties
        if obj3.measures:
            raise NotImplementedError('Conversion of measures from SBOL3 to SBOL2 not yet implemented')

    def _convert_toplevel(self, obj3: sbol3.TopLevel, obj2: sbol2.TopLevel):
        """Map over the other properties of a TopLevel object"""
        self._convert_identified(obj3, obj2)
        obj2.attachments = [a.identity for a in obj3.attachments]
        obj2.properties[BACKPORT3_NAMESPACE] = [URIRef(obj3.namespace)]

    @staticmethod
    def _sbol2_version(obj: sbol3.Identified):
        if not hasattr(obj, 'sbol2_version'):
            obj.sbol2_version = sbol3.TextProperty(obj, BACKPORT2_VERSION, 0, 1)
        # TODO: since version is optional, if it's missing, should this be returning '1' or None?
        return obj.sbol2_version or '1'

    def visit_activity(self, act3: sbol3.Activity):
        # Make the Activity object and add it to the document
        act2 = sbol2.Activity(act3.identity, version=self._sbol2_version(act3))
        self.doc2.activities.add(act2)
        if act3.types:
            if len(act3.types) > 1:
                raise NotImplementedError('Conversion of multi-type Activities to SBOL2 not yet implemented:'
                                          'pySBOL2 currently supports a maximum of one type per activity'
                                          'Bug: https://github.com/SynBioDex/pySBOL2/issues/428')
            act2.types = act3.types[0]  # Take first type from list of length 1
        act2.startedAtTime = act3.start_time
        act2.endedAtTime = act3.end_time
        if act3.usage or act3.association:
            raise NotImplementedError('Conversion of Activity usage and association properties to SBOL2 '
                                      'not yet implemented, due to visitors failing to return values'
                                      'Bug: https://github.com/SynBioDex/pySBOL3/issues/437')
        act2.usages = [usage.accept(self) for usage in act3.usage]
        act2.associations = [assoc.accept(self) for assoc in act3.association]
        # TODO: pySBOL3 is currently missing wasInformedBy (https://github.com/SynBioDex/pySBOL3/issues/436
        # act2.wasInformedBy = act3.informed_by
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(act3, act2)

    def visit_agent(self, a: sbol3.Agent):
        # Priority: 3
        raise NotImplementedError('Conversion of Agent from SBOL3 to SBOL2 not yet implemented')

    def visit_association(self, a: sbol3.Association):
        # Priority: 3
        raise NotImplementedError('Conversion of Association from SBOL3 to SBOL2 not yet implemented')

    def visit_attachment(self, a: sbol3.Attachment):
        # Priority: 2
        raise NotImplementedError('Conversion of Attachment from SBOL3 to SBOL2 not yet implemented')

    def visit_binary_prefix(self, a: sbol3.BinaryPrefix):
        # Priority: 4
        raise NotImplementedError('Conversion of BinaryPrefix from SBOL3 to SBOL2 not yet implemented')

    def visit_collection(self, a: sbol3.Collection):
        # Priority: 1
        raise NotImplementedError('Conversion of Collection from SBOL3 to SBOL2 not yet implemented')

    def visit_combinatorial_derivation(self, a: sbol3.CombinatorialDerivation):
        # Priority: 2
        raise NotImplementedError('Conversion of CombinatorialDerivation from SBOL3 to SBOL2 not yet implemented')

    def visit_component(self, cp3: sbol3.Component):
        # Remap type if it's one of the ones that needs remapping; otherwise pass through unchanged
        type_map = {sbol3.SBO_DNA: sbol2.BIOPAX_DNA,  # TODO: distinguish BioPAX Dna from DnaRegion
                    sbol3.SBO_RNA: sbol2.BIOPAX_RNA,  # TODO: distinguish BioPAX Rna from RnaRegion
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
        # Priority: 3
        raise NotImplementedError('Conversion of ComponentReference from SBOL3 to SBOL2 not yet implemented')

    def visit_constraint(self, a: sbol3.Constraint):
        # Priority: 2
        raise NotImplementedError('Conversion of Constraint from SBOL3 to SBOL2 not yet implemented')

    def visit_cut(self, a: sbol3.Cut):
        # Priority: 2
        raise NotImplementedError('Conversion of Cut from SBOL3 to SBOL2 not yet implemented')

    def visit_document(self, doc3: sbol3.Document):
        for obj in doc3.objects:
            obj.accept(self)

    def visit_entire_sequence(self, a: sbol3.EntireSequence):
        # Priority: 3
        raise NotImplementedError('Conversion of EntireSequence from SBOL3 to SBOL2 not yet implemented')

    def visit_experiment(self, a: sbol3.Experiment):
        # Priority: 3
        raise NotImplementedError('Conversion of Experiment from SBOL3 to SBOL2 not yet implemented')

    def visit_experimental_data(self, a: sbol3.ExperimentalData):
        # Priority: 3
        raise NotImplementedError('Conversion of ExperimentalData from SBOL3 to SBOL2 not yet implemented')

    def visit_externally_defined(self, a: sbol3.ExternallyDefined):
        # Priority: 3
        raise NotImplementedError('Conversion of ExternallyDefined from SBOL3 to SBOL2 not yet implemented')

    def visit_implementation(self, implement3: sbol3.Implementation):
        # Priority: 1
        # Make the Implement object and add it to the document
        implement2 = sbol2.Implementation(implement3.identity, version=self._sbol2_version(implement3))
        self.doc2.addImplementation(implement2)
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(implement3, implement2)

    def visit_interaction(self, a: sbol3.Interaction):
        # Priority: 2
        raise NotImplementedError('Conversion of Interaction from SBOL3 to SBOL2 not yet implemented')

    def visit_interface(self, a: sbol3.Interface):
        # Priority: 3
        raise NotImplementedError('Conversion of Interface from SBOL3 to SBOL2 not yet implemented')

    def visit_local_sub_component(self, a: sbol3.LocalSubComponent):
        # Priority: 2
        raise NotImplementedError('Conversion of LocalSubComponent from SBOL3 to SBOL2 not yet implemented')

    def visit_measure(self, a: sbol3.Measure):
        # Priority: 3
        raise NotImplementedError('Conversion of Measure from SBOL3 to SBOL2 not yet implemented')

    def visit_model(self, a: sbol3.Model):
        # Priority: 3
        raise NotImplementedError('Conversion of Model from SBOL3 to SBOL2 not yet implemented')

    def visit_participation(self, a: sbol3.Participation):
        # Priority: 2
        raise NotImplementedError('Conversion of Participation from SBOL3 to SBOL2 not yet implemented')

    def visit_plan(self, a: sbol3.Plan):
        # Priority: 3
        raise NotImplementedError('Conversion of Plan from SBOL3 to SBOL2 not yet implemented')

    def visit_prefixed_unit(self, a: sbol3.PrefixedUnit):
        # Priority: 4
        raise NotImplementedError('Conversion of PrefixedUnit from SBOL3 to SBOL2 not yet implemented')

    def visit_range(self, a: sbol3.Range):
        # Priority: 2
        raise NotImplementedError('Conversion of Range from SBOL3 to SBOL2 not yet implemented')

    def visit_si_prefix(self, a: sbol3.SIPrefix):
        # Priority: 4
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
        # Priority: 1
        raise NotImplementedError('Conversion of SequenceFeature from SBOL3 to SBOL2 not yet implemented')

    def visit_singular_unit(self, a: sbol3.SingularUnit):
        # Priority: 4
        raise NotImplementedError('Conversion of SingularUnit from SBOL3 to SBOL2 not yet implemented')

    def visit_sub_component(self, a: sbol3.SubComponent):
        # Priority: 1
        raise NotImplementedError('Conversion of SubComponent from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_division(self, a: sbol3.UnitDivision):
        # Priority: 4
        raise NotImplementedError('Conversion of UnitDivision from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_exponentiation(self, a: sbol3.UnitExponentiation):
        # Priority: 4
        raise NotImplementedError('Conversion of UnitExponentiation from SBOL3 to SBOL2 not yet implemented')

    def visit_unit_multiplication(self, a: sbol3.UnitMultiplication):
        # Priority: 4
        raise NotImplementedError('Conversion of UnitMultiplication from SBOL3 to SBOL2 not yet implemented')

    def visit_usage(self, a: sbol3.Usage):
        # Priority: 3
        raise NotImplementedError('Conversion of Usage from SBOL3 to SBOL2 not yet implemented')

    def visit_variable_feature(self, a: sbol3.VariableFeature):
        # Priority: 2
        raise NotImplementedError('Conversion of VariableFeature from SBOL3 to SBOL2 not yet implemented')


class SBOL2To3ConversionVisitor:
    """This class is used to map every object in an SBOL3 document into an empty SBOL2 document"""

    doc3: sbol3.Document
    namespaces: list

    def __init__(self, doc2: sbol2.Document, namespaces: list):
        # Create the target document
        self.doc3 = sbol3.Document()
        self.namespaces = namespaces
        #   # Immediately run the conversion
        self._convert(doc2)

    def _convert(self, doc2: sbol2.Document):
        # Note: namespaces don't need to be bound for SBOL3 documents, which don't usually use XML
        # We can skip all the preliminaries and just go to conversion
        self.visit_document(doc2)
        # TODO: check if there is additional work needed for Annotation & GenericTopLevel conversion

    @staticmethod
    def _convert_extension_properties(obj2: sbol2.Identified, obj3: sbol3.Identified):
        """Copy over extension properties"""
        extension_properties = (p for p in obj2.properties
                                if not any(p.startswith(prefix) for prefix in SBOL2_NON_EXTENSION_PROPERTY_PREFIXES))
        for p in extension_properties:
            obj3._properties[p] = obj2.properties[p]

    def _convert_identified(self, obj2: sbol2.Identified, obj3: sbol3.Identified):
        """Map over the other properties of an Identified object"""
        self._convert_extension_properties(obj2, obj3)
        # Map over equivalent properties
        # display_id and namespace are handled during creation
        if obj2.version:  # Save version for unpacking later if needed
            obj3.sbol2_version = sbol3.TextProperty(obj3, BACKPORT2_VERSION, 0, 1)
            obj3.sbol2_version = obj2.version
        obj3.name = obj2.name
        obj3.description = obj2.description
        obj3.derived_from = obj2.wasDerivedFrom
        obj3.generated_by = obj2.wasGeneratedBy
        # TODO: unpack measures from extension properties

    def _convert_toplevel(self, obj2: sbol2.TopLevel, obj3: sbol3.TopLevel):
        """Map over the other properties of a TopLevel object"""
        self._convert_identified(obj2, obj3)
        obj3.attachments = [a.identity for a in obj2.attachments]

    def _sbol3_namespace(self, obj2: sbol2.TopLevel):
        # If a namespace is explicitly set, that takes priority
        if BACKPORT3_NAMESPACE in obj2.properties:
            namespaces = obj2.properties[BACKPORT3_NAMESPACE]
            if len(namespaces) != 1:
                raise ValueError(f'Object {obj2.identity} backport namespace property should have precisely one value, '
                                 f'but was {namespaces}')
            return namespaces[0]
        # Check if the object starts with any of the provided namespaces
        for namespace in self.namespaces:
            if obj2.identity.startswith(namespace):
                return namespace
        # Otherwise, use default behavior
        return None

    def visit_activity(self, act2: sbol2.Activity):
        # Make the Activity object and add it to the document
        act3 = sbol3.Activity(act2.identity, namespace=self._sbol3_namespace(act2),
                              start_time=act2.startedAtTime, end_time=act2.endedAtTime)
        self.doc3.add(act3)
        # Convert child objects after adding to document
        if act2.types:  # TODO: wrapping not needed after resolution of https://github.com/SynBioDex/pySBOL2/issues/428
            act3.types = [act2.types]
        act3.usage = [usage.visit_usage(self) for usage in act2.usages]
        act3.association = [assoc.visit_association(self) for assoc in act2.associations]
        # TODO: pySBOL3 is currently missing wasInformedBy (https://github.com/SynBioDex/pySBOL3/issues/436
        # act3.informed_by = act2.wasInformedBy
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(act2, act3)

    def visit_agent(self, a: sbol2.Agent):
        # Priority: 3
        raise NotImplementedError('Conversion of Agent from SBOL2 to SBOL3 not yet implemented')

    def visit_association(self, a: sbol2.Association):
        # Priority: 3
        raise NotImplementedError('Conversion of Association from SBOL2 to SBOL3 not yet implemented')

    def visit_attachment(self, a: sbol2.Attachment):
        # Priority: 2
        raise NotImplementedError('Conversion of Attachment from SBOL2 to SBOL3 not yet implemented')

    def visit_collection(self, a: sbol2.Collection):
        # Priority: 1
        raise NotImplementedError('Conversion of Collection from SBOL2 to SBOL3 not yet implemented')

    def visit_combinatorial_derivation(self, a: sbol2.CombinatorialDerivation):
        # Priority: 2
        raise NotImplementedError('Conversion of CombinatorialDerivation from SBOL2 to SBOL3 not yet implemented')

    def visit_component_definition(self, cd2: sbol2.ComponentDefinition):
        # Remap type if it's one of the ones that needs remapping; otherwise pass through unchanged
        type_map = {sbol2.BIOPAX_DNA: sbol3.SBO_DNA,
                    'http://www.biopax.org/release/biopax-level3.owl#Dna': sbol3.SBO_DNA,  # TODO: make reversible
                    sbol2.BIOPAX_RNA: sbol3.SBO_RNA,
                    'http://www.biopax.org/release/biopax-level3.owl#Rna': sbol3.SBO_RNA,  # TODO: make reversible
                    sbol2.BIOPAX_PROTEIN: sbol3.SBO_PROTEIN,
                    sbol2.BIOPAX_SMALL_MOLECULE: sbol3.SBO_SIMPLE_CHEMICAL,
                    sbol2.BIOPAX_COMPLEX: sbol3.SBO_NON_COVALENT_COMPLEX}
        types3 = [type_map.get(t, t) for t in cd2.types]
        # Make the Component object and add it to the document
        cp3 = sbol3.Component(cd2.identity, types3, namespace=self._sbol3_namespace(cd2),
                              roles=cd2.roles, sequences=cd2.sequences)
        self.doc3.add(cp3)
        # Convert the Component properties not covered by the constructor
        if cd2.components:
            raise NotImplementedError('Conversion of ComponentDefinition components '
                                      'from SBOL2 to SBOL3 not yet implemented')
        if cd2.sequenceAnnotations:
            raise NotImplementedError('Conversion of ComponentDefinition sequenceAnnotations '
                                      'from SBOL2 to SBOL3 not yet implemented')
        if cd2.sequenceConstraints:
            raise NotImplementedError('Conversion of ComponentDefinition sequenceConstraints '
                                      'from SBOL2 to SBOL3 not yet implemented')
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(cd2, cp3)

    def visit_component(self, a: sbol2.Component):
        # Priority: 2
        raise NotImplementedError('Conversion of Component from SBOL2 to SBOL3 not yet implemented')

    def visit_cut(self, a: sbol2.Cut):
        # Priority: 2
        raise NotImplementedError('Conversion of Cut from SBOL2 to SBOL3 not yet implemented')

    def visit_document(self, doc2: sbol2.Document):
        for obj in doc2.componentDefinitions:
            self.visit_component_definition(obj)
        for obj in doc2.moduleDefinitions:
            self.visit_module_definition(obj)
        for obj in doc2.models:
            self.visit_model(obj)
        for obj in doc2.sequences:
            self.visit_sequence(obj)
        for obj in doc2.collections:
            self.visit_collection(obj)
        for obj in doc2.activities:
            self.visit_activity(obj)
        for obj in doc2.plans:
            self.visit_plan(obj)
        for obj in doc2.agents:
            self.visit_agent(obj)
        for obj in doc2.attachments:
            self.visit_attachment(obj)
        for obj in doc2.combinatorialderivations:
            self.visit_combinatorial_derivation(obj)
        for obj in doc2.implementations:
            self.visit_implementation(obj)
        for obj in doc2.experiments:
            self.visit_experiment(obj)
        for obj in doc2.experimentalData:
            self.visit_experimental_data(obj)
        # TODO: handle "standard extensions" in pySBOL2:
        #   designs, builds, tests, analyses, sampleRosters, citations, keywords

    def visit_experiment(self, a: sbol2.Experiment):
        # Priority: 3
        raise NotImplementedError('Conversion of Experiment from SBOL2 to SBOL3 not yet implemented')

    def visit_experimental_data(self, a: sbol2.ExperimentalData):
        # Priority: 3
        raise NotImplementedError('Conversion of ExperimentalData from SBOL2 to SBOL3 not yet implemented')

    def visit_functional_component(self, a: sbol2.FunctionalComponent):
        # Priority: 3
        raise NotImplementedError('Conversion of FunctionalComponent from SBOL2 to SBOL3 not yet implemented')

    def visit_generic_location(self, a: sbol2.GenericLocation):
        # Priority: 3
        raise NotImplementedError('Conversion of GenericLocation from SBOL2 to SBOL3 not yet implemented')

    def visit_implementation(self, imp2: sbol2.Implementation):
        # Priority: 1
        # Make the Implementation object and add it to the document
        imp3 = sbol3.Implementation(imp2.identity, namespace=self._sbol3_namespace(imp2))
        self.doc3.add(imp3)
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(imp2, imp3)

        # raise NotImplementedError('Conversion of Implementation from SBOL2 to SBOL3 not yet implemented')

    def visit_interaction(self, a: sbol2.Interaction):
        # Priority: 2
        raise NotImplementedError('Conversion of Interaction from SBOL2 to SBOL3 not yet implemented')

    def visit_maps_to(self, a: sbol2.mapsto.MapsTo):
        # Priority: 3
        raise NotImplementedError('Conversion of MapsTo from SBOL2 to SBOL3 not yet implemented')

    def visit_measure(self, a: sbol2.measurement.Measurement):
        # Priority: 3
        raise NotImplementedError('Conversion of Measure from SBOL2 to SBOL3 not yet implemented')

    def visit_model(self, a: sbol2.model.Model):
        # Priority: 3
        raise NotImplementedError('Conversion of Model from SBOL2 to SBOL3 not yet implemented')

    def visit_module(self, a: sbol2.Module):
        # Priority: 3
        raise NotImplementedError('Conversion of Module from SBOL2 to SBOL3 not yet implemented')

    def visit_module_definition(self, a: sbol2.ModuleDefinition):
        # Priority: 3
        raise NotImplementedError('Conversion of ModuleDefinition from SBOL2 to SBOL3 not yet implemented')

    def visit_participation(self, a: sbol2.Participation):
        # Priority: 2
        raise NotImplementedError('Conversion of Participation from SBOL2 to SBOL3 not yet implemented')

    def visit_plan(self, a: sbol2.Plan):
        # Priority: 3
        raise NotImplementedError('Conversion of Plan from SBOL2 to SBOL3 not yet implemented')

    def visit_range(self, a: sbol2.Range):
        # Priority: 2
        raise NotImplementedError('Conversion of Range from SBOL2 to SBOL3 not yet implemented')

    def visit_sequence(self, seq2: sbol2.Sequence):
        # Remap encoding if it's one of the ones that needs remapping; otherwise pass through unchanged
        encoding_map = {sbol2.SBOL_ENCODING_IUPAC: sbol3.IUPAC_DNA_ENCODING,
                        sbol2.SBOL_ENCODING_IUPAC_PROTEIN: sbol3.IUPAC_PROTEIN_ENCODING,
                        sbol2.SBOL_ENCODING_SMILES: sbol3.SMILES_ENCODING}
        encoding3 = encoding_map.get(seq2.encoding, seq2.encoding)
        # Make the Sequence object and add it to the document
        seq3 = sbol3.Sequence(seq2.identity, namespace=self._sbol3_namespace(seq2),
                              elements=seq2.elements, encoding=encoding3)
        self.doc3.add(seq3)
        # Map over all other TopLevel properties and extensions not covered by the constructor
        self._convert_toplevel(seq2, seq3)

    def visit_sequence_annotation(self, seq2: sbol2.SequenceAnnotation):
        # Priority: 1
        raise NotImplementedError('Conversion of SequenceAnnotation from SBOL2 to SBOL3 not yet implemented')

    def visit_sequence_constraint(self, seq2: sbol2.sequenceconstraint.SequenceConstraint):
        # Priority: 2
        raise NotImplementedError('Conversion of SequenceConstraint from SBOL2 to SBOL3 not yet implemented')

    def visit_usage(self, a: sbol2.Usage):
        # Priority: 3
        raise NotImplementedError('Conversion of Usage from SBOL2 to SBOL3 not yet implemented')

    def visit_variable_component(self, a: sbol2.VariableComponent):
        # Priority: 2
        raise NotImplementedError('Conversion of VariableComponent from SBOL2 to SBOL3 not yet implemented')


def convert3to2(doc3: sbol3.Document) -> sbol2.Document:
    """Convert an SBOL3 document to an SBOL2 document

    :param doc3: SBOL3 document to convert
    :returns: SBOL2 document
    """
    converter = SBOL3To2ConversionVisitor(doc3)
    return converter.doc2


def convert2to3(doc2: sbol2.Document, namespaces=None) -> sbol3.Document:
    """Convert an SBOL2 document to an SBOL3 document

    :param doc2: SBOL2 document to convert
    :param namespaces: list of URI prefixes to treat as namespaces
    :returns: SBOL3 document
    """
    converter = SBOL2To3ConversionVisitor(doc2, namespaces)
    return converter.doc3
