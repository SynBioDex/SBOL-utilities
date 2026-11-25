"""The SBOL 2.3.0 data model, as a schema the validator reads.

Every SBOL 2, PROV-O, and OM class the specification adopts is listed with its parent classes and the properties it
declares directly. Each property carries the catalog rule governing it, its cardinality, the kind of value it holds,
and, for references, the class the referenced object must have and whether the reference names a child held in the
same document.
"""

from __future__ import annotations

from sbol_utilities.validation.schema import Cardinality, ClassSpec, PropertySpec, Reference, Schema, ValueKind
from sbol_utilities.vocab import (
    DCTERMS_DESCRIPTION,
    DCTERMS_TITLE,
    OM_NS,
    PROV_NS,
    RDF_TYPE,
    RDFS_COMMENT,
    RDFS_LABEL,
    SBOL2_NS,
)


def sbol_iri(local: str) -> str:
    """The IRI of a term in the SBOL 2 namespace."""
    return SBOL2_NS + local


def prov_iri(local: str) -> str:
    """The IRI of a term in the PROV namespace."""
    return PROV_NS + local


def om_iri(local: str) -> str:
    """The IRI of a term in the OM namespace."""
    return OM_NS + local


# --- classes -----------------------------------------------------------------------------------------------------

IDENTIFIED = sbol_iri("Identified")
TOP_LEVEL = sbol_iri("TopLevel")
MEASURED = sbol_iri("Measured")
COMPONENT_INSTANCE = sbol_iri("ComponentInstance")
LOCATION = sbol_iri("Location")
SEQUENCE = sbol_iri("Sequence")
COMPONENT_DEFINITION = sbol_iri("ComponentDefinition")
MODULE_DEFINITION = sbol_iri("ModuleDefinition")
MODEL = sbol_iri("Model")
COLLECTION = sbol_iri("Collection")
COMBINATORIAL_DERIVATION = sbol_iri("CombinatorialDerivation")
IMPLEMENTATION = sbol_iri("Implementation")
ATTACHMENT = sbol_iri("Attachment")
EXPERIMENTAL_DATA = sbol_iri("ExperimentalData")
EXPERIMENT = sbol_iri("Experiment")
GENERIC_TOP_LEVEL = sbol_iri("GenericTopLevel")
COMPONENT = sbol_iri("Component")
FUNCTIONAL_COMPONENT = sbol_iri("FunctionalComponent")
MODULE = sbol_iri("Module")
MAPS_TO = sbol_iri("MapsTo")
SEQUENCE_ANNOTATION = sbol_iri("SequenceAnnotation")
SEQUENCE_CONSTRAINT = sbol_iri("SequenceConstraint")
VARIABLE_COMPONENT = sbol_iri("VariableComponent")
INTERACTION = sbol_iri("Interaction")
PARTICIPATION = sbol_iri("Participation")
RANGE = sbol_iri("Range")
CUT = sbol_iri("Cut")
GENERIC_LOCATION = sbol_iri("GenericLocation")
ACTIVITY = prov_iri("Activity")
AGENT = prov_iri("Agent")
PLAN = prov_iri("Plan")
ASSOCIATION = prov_iri("Association")
USAGE = prov_iri("Usage")
OM_MEASURE = om_iri("Measure")
OM_UNIT = om_iri("Unit")
OM_SINGULAR_UNIT = om_iri("SingularUnit")
OM_COMPOUND_UNIT = om_iri("CompoundUnit")
OM_UNIT_MULTIPLICATION = om_iri("UnitMultiplication")
OM_UNIT_DIVISION = om_iri("UnitDivision")
OM_UNIT_EXPONENTIATION = om_iri("UnitExponentiation")
OM_PREFIXED_UNIT = om_iri("PrefixedUnit")
OM_PREFIX = om_iri("Prefix")
OM_SI_PREFIX = om_iri("SIPrefix")
OM_BINARY_PREFIX = om_iri("BinaryPrefix")

# --- predicates --------------------------------------------------------------------------------------------------

PERSISTENT_IDENTITY = sbol_iri("persistentIdentity")
DISPLAY_ID = sbol_iri("displayId")
VERSION = sbol_iri("version")
TITLE = DCTERMS_TITLE
DESCRIPTION = DCTERMS_DESCRIPTION
WAS_DERIVED_FROM = prov_iri("wasDerivedFrom")
WAS_GENERATED_BY = prov_iri("wasGeneratedBy")
ATTACHMENT_P = sbol_iri("attachment")
MEASURE = sbol_iri("measure")
DEFINITION = sbol_iri("definition")
ACCESS = sbol_iri("access")
MAPS_TO_P = sbol_iri("mapsTo")
ORIENTATION = sbol_iri("orientation")
SEQUENCE_P = sbol_iri("sequence")
ELEMENTS = sbol_iri("elements")
ENCODING = sbol_iri("encoding")
TYPE = sbol_iri("type")
ROLE = sbol_iri("role")
COMPONENT_P = sbol_iri("component")
SEQUENCE_ANNOTATION_P = sbol_iri("sequenceAnnotation")
SEQUENCE_CONSTRAINT_P = sbol_iri("sequenceConstraint")
MODULE_P = sbol_iri("module")
FUNCTIONAL_COMPONENT_P = sbol_iri("functionalComponent")
INTERACTION_P = sbol_iri("interaction")
MODEL_P = sbol_iri("model")
SOURCE = sbol_iri("source")
LANGUAGE = sbol_iri("language")
FRAMEWORK = sbol_iri("framework")
FORMAT = sbol_iri("format")
SIZE = sbol_iri("size")
HASH = sbol_iri("hash")
MEMBER = sbol_iri("member")
TEMPLATE = sbol_iri("template")
VARIABLE_COMPONENT_P = sbol_iri("variableComponent")
STRATEGY = sbol_iri("strategy")
BUILT = sbol_iri("built")
EXPERIMENTAL_DATA_P = sbol_iri("experimentalData")
RDF_TYPE_P = sbol_iri("rdfType")
ROLE_INTEGRATION = sbol_iri("roleIntegration")
SOURCE_LOCATION = sbol_iri("sourceLocation")
DIRECTION = sbol_iri("direction")
LOCAL = sbol_iri("local")
REMOTE = sbol_iri("remote")
REFINEMENT = sbol_iri("refinement")
LOCATION_P = sbol_iri("location")
SUBJECT = sbol_iri("subject")
OBJECT = sbol_iri("object")
RESTRICTION = sbol_iri("restriction")
START = sbol_iri("start")
END = sbol_iri("end")
AT = sbol_iri("at")
PARTICIPATION_P = sbol_iri("participation")
PARTICIPANT = sbol_iri("participant")
VARIABLE = sbol_iri("variable")
VARIANT = sbol_iri("variant")
VARIANT_COLLECTION = sbol_iri("variantCollection")
VARIANT_DERIVATION = sbol_iri("variantDerivation")
OPERATOR = sbol_iri("operator")
STARTED_AT_TIME = prov_iri("startedAtTime")
ENDED_AT_TIME = prov_iri("endedAtTime")
QUALIFIED_ASSOCIATION = prov_iri("qualifiedAssociation")
QUALIFIED_USAGE = prov_iri("qualifiedUsage")
WAS_INFORMED_BY = prov_iri("wasInformedBy")
AGENT_P = prov_iri("agent")
HAD_ROLE = prov_iri("hadRole")
HAD_PLAN = prov_iri("hadPlan")
ENTITY = prov_iri("entity")
OM_SYMBOL = om_iri("symbol")
OM_ALTERNATIVE_SYMBOL = om_iri("alternativeSymbol")
OM_ALTERNATIVE_LABEL = om_iri("alternativeLabel")
OM_LONG_COMMENT = om_iri("longcomment")
OM_HAS_NUMERICAL_VALUE = om_iri("hasNumericalValue")
OM_HAS_UNIT = om_iri("hasUnit")
OM_HAS_FACTOR = om_iri("hasFactor")
OM_HAS_TERM1 = om_iri("hasTerm1")
OM_HAS_TERM2 = om_iri("hasTerm2")
OM_HAS_NUMERATOR = om_iri("hasNumerator")
OM_HAS_DENOMINATOR = om_iri("hasDenominator")
OM_HAS_BASE = om_iri("hasBase")
OM_HAS_EXPONENT = om_iri("hasExponent")
OM_HAS_PREFIX = om_iri("hasPrefix")

# --- enumerated values -------------------------------------------------------------------------------------------

PUBLIC = sbol_iri("public")
PRIVATE = sbol_iri("private")
INLINE = sbol_iri("inline")
MERGE_ROLES = sbol_iri("mergeRoles")
OVERRIDE_ROLES = sbol_iri("overrideRoles")
VERIFY_IDENTICAL = sbol_iri("verifyIdentical")
USE_LOCAL = sbol_iri("useLocal")
USE_REMOTE = sbol_iri("useRemote")
MERGE = sbol_iri("merge")
ENUMERATE = sbol_iri("enumerate")
SAMPLE = sbol_iri("sample")
OP_ZERO_OR_ONE = sbol_iri("zeroOrOne")
OP_ONE = sbol_iri("one")
OP_ZERO_OR_MORE = sbol_iri("zeroOrMore")
OP_ONE_OR_MORE = sbol_iri("oneOrMore")
PRECEDES = sbol_iri("precedes")
SAME_ORIENTATION_AS = sbol_iri("sameOrientationAs")
OPPOSITE_ORIENTATION_AS = sbol_iri("oppositeOrientationAs")
DIFFERENT_FROM = sbol_iri("differentFrom")
ROLE_DESIGN = sbol_iri("design")
ROLE_BUILD = sbol_iri("build")
ROLE_TEST = sbol_iri("test")
ROLE_LEARN = sbol_iri("learn")

IUPAC_NUCLEIC_ENCODING = "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html"
IUPAC_PROTEIN_ENCODING = "http://www.chem.qmul.ac.uk/iupac/AminoAcid/"
SMILES_ENCODING = "http://www.opensmiles.org/opensmiles.html"
IUPAC_NUCLEIC_ALPHABET = frozenset("ACGTURYSWKMBDHVN-.")

BIOPAX = "http://www.biopax.org/release/biopax-level3.owl#"
BIOPAX_DNA_REGION = BIOPAX + "DnaRegion"
BIOPAX_RNA_REGION = BIOPAX + "RnaRegion"
BIOPAX_DNA_MOLECULE = BIOPAX + "Dna"
BIOPAX_RNA_MOLECULE = BIOPAX + "Rna"
BIOPAX_PROTEIN = BIOPAX + "Protein"
BIOPAX_COMPLEX = BIOPAX + "Complex"
BIOPAX_SMALL_MOLECULE = BIOPAX + "SmallMolecule"
#: Table 2 ComponentDefinition types, matched by exact IRI
BIOPAX_TYPES = frozenset(
    [
        BIOPAX_DNA_REGION,
        BIOPAX_RNA_REGION,
        BIOPAX_DNA_MOLECULE,
        BIOPAX_RNA_MOLECULE,
        BIOPAX_PROTEIN,
        BIOPAX_COMPLEX,
        BIOPAX_SMALL_MOLECULE,
    ]
)
#: Table 1 sequence encodings (IUPAC DNA and RNA share one IRI)
TABLE_1_ENCODINGS = frozenset([IUPAC_NUCLEIC_ENCODING, IUPAC_PROTEIN_ENCODING, SMILES_ENCODING])
#: Table 7 SequenceConstraint restrictions
TABLE_7_RESTRICTIONS = frozenset([PRECEDES, SAME_ORIENTATION_AS, OPPOSITE_ORIENTATION_AS, DIFFERENT_FROM])

SO_SEQUENCE_FEATURE = "SO:0000110"
SO_TOPOLOGY_ATTRIBUTE = "SO:0000986"
SO_STRAND_ATTRIBUTE = "SO:0000983"
SBO_OCCURRING_ENTITY_REPRESENTATION = "SBO:0000231"
SBO_PARTICIPANT_ROLE = "SBO:0000003"
SBO_SYSTEMS_DESCRIPTION_PARAMETER = "SBO:0000545"
SBO_MODELING_FRAMEWORK = "SBO:0000004"

# --- schema ------------------------------------------------------------------------------------------------------

EXACTLY_ONE = Cardinality.EXACTLY_ONE
ZERO_OR_ONE = Cardinality.ZERO_OR_ONE
ONE_OR_MORE = Cardinality.ONE_OR_MORE
ZERO_OR_MORE = Cardinality.ZERO_OR_MORE

URI = ValueKind.URI
URL = ValueKind.URL
STRING = ValueKind.STRING
INTEGER = ValueKind.INTEGER
LONG = ValueKind.LONG
FLOAT = ValueKind.FLOAT
DATE_TIME = ValueKind.DATE_TIME


def property_spec(
    rule: str | None, predicate: str, cardinality: Cardinality, kind: ValueKind, reference: Reference | None = None
) -> PropertySpec:
    """A property row; ``rule`` is None for a property no catalog rule governs."""
    return PropertySpec(predicate, cardinality, kind, reference, rule)


def local_reference(target: str) -> Reference:
    """A reference to a child held in the same document."""
    return Reference(target, local=True)


def external_reference(target: str) -> Reference:
    """A reference to an object that may live in another document."""
    return Reference(target, local=False)


IDENTIFIED_FIELDS = (
    property_spec("sbol2-10203", PERSISTENT_IDENTITY, ZERO_OR_ONE, URI),
    property_spec("sbol2-10204", DISPLAY_ID, ZERO_OR_ONE, STRING),
    property_spec("sbol2-10206", VERSION, ZERO_OR_ONE, STRING),
    property_spec("sbol2-10212", TITLE, ZERO_OR_ONE, STRING),
    property_spec("sbol2-10213", DESCRIPTION, ZERO_OR_ONE, STRING),
    property_spec("sbol2-10208", WAS_DERIVED_FROM, ZERO_OR_MORE, URI),
    property_spec("sbol2-10221", WAS_GENERATED_BY, ZERO_OR_MORE, URI, external_reference(ACTIVITY)),
)
TOP_LEVEL_FIELDS = (property_spec("sbol2-10306", ATTACHMENT_P, ZERO_OR_MORE, URI, external_reference(ATTACHMENT)),)
MEASURED_FIELDS = (property_spec(None, MEASURE, ZERO_OR_MORE, URI, local_reference(OM_MEASURE)),)
COMPONENT_INSTANCE_FIELDS = (
    property_spec("sbol2-10602", DEFINITION, EXACTLY_ONE, URI, external_reference(COMPONENT_DEFINITION)),
    property_spec("sbol2-10607", ACCESS, EXACTLY_ONE, URI),
    property_spec("sbol2-10606", MAPS_TO_P, ZERO_OR_MORE, URI, local_reference(MAPS_TO)),
)
LOCATION_FIELDS = (
    property_spec("sbol2-11002", ORIENTATION, ZERO_OR_ONE, URI),
    property_spec("sbol2-11003", SEQUENCE_P, ZERO_OR_ONE, URI, external_reference(SEQUENCE)),
)
SEQUENCE_FIELDS = (
    property_spec("sbol2-10402", ELEMENTS, EXACTLY_ONE, STRING),
    property_spec("sbol2-10403", ENCODING, EXACTLY_ONE, URI),
)
COMPONENT_DEFINITION_FIELDS = (
    property_spec("sbol2-10502", TYPE, ONE_OR_MORE, URI),
    property_spec("sbol2-10507", ROLE, ZERO_OR_MORE, URI),
    property_spec("sbol2-10512", SEQUENCE_P, ZERO_OR_MORE, URI, external_reference(SEQUENCE)),
    property_spec("sbol2-10519", COMPONENT_P, ZERO_OR_MORE, URI, local_reference(COMPONENT)),
    property_spec("sbol2-10521", SEQUENCE_ANNOTATION_P, ZERO_OR_MORE, URI, local_reference(SEQUENCE_ANNOTATION)),
    property_spec("sbol2-10524", SEQUENCE_CONSTRAINT_P, ZERO_OR_MORE, URI, local_reference(SEQUENCE_CONSTRAINT)),
)
MODULE_DEFINITION_FIELDS = (
    property_spec("sbol2-11602", ROLE, ZERO_OR_MORE, URI),
    property_spec("sbol2-11604", MODULE_P, ZERO_OR_MORE, URI, local_reference(MODULE)),
    property_spec("sbol2-11606", FUNCTIONAL_COMPONENT_P, ZERO_OR_MORE, URI, local_reference(FUNCTIONAL_COMPONENT)),
    property_spec("sbol2-11605", INTERACTION_P, ZERO_OR_MORE, URI, local_reference(INTERACTION)),
    property_spec("sbol2-11607", MODEL_P, ZERO_OR_MORE, URI, external_reference(MODEL)),
)
MODEL_FIELDS = (
    property_spec("sbol2-11502", SOURCE, EXACTLY_ONE, URL),
    property_spec("sbol2-11504", LANGUAGE, EXACTLY_ONE, URI),
    property_spec("sbol2-11508", FRAMEWORK, EXACTLY_ONE, URI),
)
COLLECTION_FIELDS = (property_spec("sbol2-12102", MEMBER, ZERO_OR_MORE, URI, external_reference(TOP_LEVEL)),)
COMBINATORIAL_DERIVATION_FIELDS = (
    property_spec("sbol2-12904", TEMPLATE, EXACTLY_ONE, URI, external_reference(COMPONENT_DEFINITION)),
    property_spec("sbol2-12906", VARIABLE_COMPONENT_P, ZERO_OR_MORE, URI, local_reference(VARIABLE_COMPONENT)),
    property_spec("sbol2-12914", STRATEGY, ZERO_OR_ONE, URI),
)
IMPLEMENTATION_FIELDS = (property_spec("sbol2-13102", BUILT, ZERO_OR_ONE, URI),)
ATTACHMENT_FIELDS = (
    property_spec("sbol2-13202", SOURCE, EXACTLY_ONE, URL),
    property_spec("sbol2-13204", FORMAT, ZERO_OR_ONE, URI),
    property_spec("sbol2-13207", SIZE, ZERO_OR_ONE, LONG),
    property_spec("sbol2-13208", HASH, ZERO_OR_ONE, STRING),
)
EXPERIMENT_FIELDS = (
    property_spec("sbol2-13402", EXPERIMENTAL_DATA_P, ZERO_OR_MORE, URI, external_reference(EXPERIMENTAL_DATA)),
)
GENERIC_TOP_LEVEL_FIELDS = (property_spec("sbol2-12302", RDF_TYPE_P, EXACTLY_ONE, URI),)
COMPONENT_FIELDS = (
    property_spec("sbol2-10702", ROLE, ZERO_OR_MORE, URI),
    property_spec("sbol2-10708", ROLE_INTEGRATION, ZERO_OR_ONE, URI),
    property_spec("sbol2-10710", SOURCE_LOCATION, ZERO_OR_MORE, URI, local_reference(LOCATION)),
)
FUNCTIONAL_COMPONENT_FIELDS = (property_spec("sbol2-11802", DIRECTION, EXACTLY_ONE, URI),)
MODULE_FIELDS = (
    property_spec("sbol2-11702", DEFINITION, EXACTLY_ONE, URI, external_reference(MODULE_DEFINITION)),
    property_spec("sbol2-11706", MAPS_TO_P, ZERO_OR_MORE, URI, local_reference(MAPS_TO)),
)
MAPS_TO_FIELDS = (
    property_spec("sbol2-10802", LOCAL, EXACTLY_ONE, URI, external_reference(COMPONENT_INSTANCE)),
    property_spec("sbol2-10805", REMOTE, EXACTLY_ONE, URI, external_reference(COMPONENT_INSTANCE)),
    property_spec("sbol2-10810", REFINEMENT, EXACTLY_ONE, URI),
)
SEQUENCE_ANNOTATION_FIELDS = (
    property_spec("sbol2-10902", LOCATION_P, ONE_OR_MORE, URI, local_reference(LOCATION)),
    property_spec("sbol2-10904", COMPONENT_P, ZERO_OR_ONE, URI, external_reference(COMPONENT)),
    property_spec("sbol2-10906", ROLE, ZERO_OR_MORE, URI),
)
SEQUENCE_CONSTRAINT_FIELDS = (
    property_spec("sbol2-11402", SUBJECT, EXACTLY_ONE, URI, external_reference(COMPONENT)),
    property_spec("sbol2-11404", OBJECT, EXACTLY_ONE, URI, external_reference(COMPONENT)),
    property_spec("sbol2-11407", RESTRICTION, EXACTLY_ONE, URI),
)
RANGE_FIELDS = (
    property_spec("sbol2-11102", START, EXACTLY_ONE, INTEGER),
    property_spec("sbol2-11103", END, EXACTLY_ONE, INTEGER),
)
CUT_FIELDS = (property_spec("sbol2-11202", AT, EXACTLY_ONE, INTEGER),)
INTERACTION_FIELDS = (
    property_spec("sbol2-11902", TYPE, ONE_OR_MORE, URI),
    property_spec("sbol2-11906", PARTICIPATION_P, ZERO_OR_MORE, URI, local_reference(PARTICIPATION)),
)
PARTICIPATION_FIELDS = (
    property_spec("sbol2-12004", ROLE, ONE_OR_MORE, URI),
    property_spec("sbol2-12002", PARTICIPANT, EXACTLY_ONE, URI, external_reference(FUNCTIONAL_COMPONENT)),
)
VARIABLE_COMPONENT_FIELDS = (
    property_spec("sbol2-13004", VARIABLE, EXACTLY_ONE, URI, external_reference(COMPONENT)),
    property_spec("sbol2-13007", VARIANT, ZERO_OR_MORE, URI, external_reference(COMPONENT_DEFINITION)),
    property_spec("sbol2-13009", VARIANT_COLLECTION, ZERO_OR_MORE, URI, external_reference(COLLECTION)),
    property_spec("sbol2-13013", VARIANT_DERIVATION, ZERO_OR_MORE, URI, external_reference(COMBINATORIAL_DERIVATION)),
    property_spec("sbol2-13002", OPERATOR, EXACTLY_ONE, URI),
)
ACTIVITY_FIELDS = (
    property_spec("sbol2-12412", TYPE, ZERO_OR_MORE, URI),
    property_spec("sbol2-12402", STARTED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
    property_spec("sbol2-12403", ENDED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
    property_spec("sbol2-12404", QUALIFIED_ASSOCIATION, ZERO_OR_MORE, URI, local_reference(ASSOCIATION)),
    property_spec("sbol2-12405", QUALIFIED_USAGE, ZERO_OR_MORE, URI, local_reference(USAGE)),
    property_spec("sbol2-12406", WAS_INFORMED_BY, ZERO_OR_MORE, URI, external_reference(ACTIVITY)),
)
ASSOCIATION_FIELDS = (
    property_spec("sbol2-12605", AGENT_P, EXACTLY_ONE, URI, external_reference(AGENT)),
    property_spec("sbol2-12602", HAD_ROLE, ZERO_OR_MORE, URI),
    property_spec("sbol2-12603", HAD_PLAN, ZERO_OR_ONE, URI, external_reference(PLAN)),
)
USAGE_FIELDS = (
    property_spec("sbol2-12502", ENTITY, EXACTLY_ONE, URI),
    property_spec("sbol2-12503", HAD_ROLE, ZERO_OR_MORE, URI),
)
OM_MEASURE_FIELDS = (
    property_spec("sbol2-13502", OM_HAS_NUMERICAL_VALUE, EXACTLY_ONE, FLOAT),
    property_spec("sbol2-13503", OM_HAS_UNIT, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
    property_spec("sbol2-13504", TYPE, ZERO_OR_MORE, URI),
)
OM_LABELS = (
    property_spec(None, OM_SYMBOL, EXACTLY_ONE, STRING),
    property_spec(None, OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
    property_spec(None, RDFS_LABEL, EXACTLY_ONE, STRING),
    property_spec(None, OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
    property_spec(None, RDFS_COMMENT, ZERO_OR_ONE, STRING),
    property_spec(None, OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
)
OM_UNIT_FIELDS = OM_LABELS
OM_SINGULAR_UNIT_FIELDS = (
    property_spec(None, OM_HAS_UNIT, ZERO_OR_ONE, URI, external_reference(OM_UNIT)),
    property_spec(None, OM_HAS_FACTOR, ZERO_OR_ONE, FLOAT),
)
OM_UNIT_MULTIPLICATION_FIELDS = (
    property_spec(None, OM_HAS_TERM1, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
    property_spec(None, OM_HAS_TERM2, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
)
OM_UNIT_DIVISION_FIELDS = (
    property_spec(None, OM_HAS_NUMERATOR, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
    property_spec(None, OM_HAS_DENOMINATOR, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
)
OM_UNIT_EXPONENTIATION_FIELDS = (
    property_spec(None, OM_HAS_BASE, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
    property_spec(None, OM_HAS_EXPONENT, EXACTLY_ONE, INTEGER),
)
OM_PREFIXED_UNIT_FIELDS = (
    property_spec(None, OM_HAS_UNIT, EXACTLY_ONE, URI, external_reference(OM_UNIT)),
    property_spec(None, OM_HAS_PREFIX, EXACTLY_ONE, URI, external_reference(OM_PREFIX)),
)
OM_PREFIX_FIELDS = OM_LABELS + (property_spec(None, OM_HAS_FACTOR, EXACTLY_ONE, FLOAT),)

#: class IRI -> (parents, directly declared fields), in the order the schema lists them
CLASSES: dict[str, ClassSpec] = {
    IDENTIFIED: ClassSpec((), IDENTIFIED_FIELDS),
    TOP_LEVEL: ClassSpec((IDENTIFIED,), TOP_LEVEL_FIELDS),
    MEASURED: ClassSpec((IDENTIFIED,), MEASURED_FIELDS),
    COMPONENT_INSTANCE: ClassSpec((MEASURED,), COMPONENT_INSTANCE_FIELDS),
    LOCATION: ClassSpec((IDENTIFIED,), LOCATION_FIELDS),
    SEQUENCE: ClassSpec((TOP_LEVEL,), SEQUENCE_FIELDS),
    COMPONENT_DEFINITION: ClassSpec((TOP_LEVEL,), COMPONENT_DEFINITION_FIELDS),
    MODULE_DEFINITION: ClassSpec((TOP_LEVEL,), MODULE_DEFINITION_FIELDS),
    MODEL: ClassSpec((TOP_LEVEL,), MODEL_FIELDS),
    COLLECTION: ClassSpec((TOP_LEVEL,), COLLECTION_FIELDS),
    COMBINATORIAL_DERIVATION: ClassSpec((TOP_LEVEL,), COMBINATORIAL_DERIVATION_FIELDS),
    IMPLEMENTATION: ClassSpec((TOP_LEVEL,), IMPLEMENTATION_FIELDS),
    ATTACHMENT: ClassSpec((TOP_LEVEL,), ATTACHMENT_FIELDS),
    EXPERIMENTAL_DATA: ClassSpec((TOP_LEVEL,), ()),
    EXPERIMENT: ClassSpec((TOP_LEVEL,), EXPERIMENT_FIELDS),
    GENERIC_TOP_LEVEL: ClassSpec((TOP_LEVEL,), GENERIC_TOP_LEVEL_FIELDS),
    COMPONENT: ClassSpec((COMPONENT_INSTANCE,), COMPONENT_FIELDS),
    FUNCTIONAL_COMPONENT: ClassSpec((COMPONENT_INSTANCE,), FUNCTIONAL_COMPONENT_FIELDS),
    MODULE: ClassSpec((MEASURED,), MODULE_FIELDS),
    MAPS_TO: ClassSpec((IDENTIFIED,), MAPS_TO_FIELDS),
    SEQUENCE_ANNOTATION: ClassSpec((IDENTIFIED,), SEQUENCE_ANNOTATION_FIELDS),
    SEQUENCE_CONSTRAINT: ClassSpec((IDENTIFIED,), SEQUENCE_CONSTRAINT_FIELDS),
    VARIABLE_COMPONENT: ClassSpec((IDENTIFIED,), VARIABLE_COMPONENT_FIELDS),
    INTERACTION: ClassSpec((MEASURED,), INTERACTION_FIELDS),
    PARTICIPATION: ClassSpec((MEASURED,), PARTICIPATION_FIELDS),
    RANGE: ClassSpec((LOCATION,), RANGE_FIELDS),
    CUT: ClassSpec((LOCATION,), CUT_FIELDS),
    GENERIC_LOCATION: ClassSpec((LOCATION,), ()),
    ACTIVITY: ClassSpec((TOP_LEVEL,), ACTIVITY_FIELDS),
    AGENT: ClassSpec((TOP_LEVEL,), ()),
    PLAN: ClassSpec((TOP_LEVEL,), ()),
    ASSOCIATION: ClassSpec((IDENTIFIED,), ASSOCIATION_FIELDS),
    USAGE: ClassSpec((IDENTIFIED,), USAGE_FIELDS),
    OM_MEASURE: ClassSpec((IDENTIFIED,), OM_MEASURE_FIELDS),
    OM_UNIT: ClassSpec((TOP_LEVEL,), OM_UNIT_FIELDS),
    OM_SINGULAR_UNIT: ClassSpec((OM_UNIT,), OM_SINGULAR_UNIT_FIELDS),
    OM_COMPOUND_UNIT: ClassSpec((OM_UNIT,), ()),
    OM_UNIT_MULTIPLICATION: ClassSpec((OM_COMPOUND_UNIT,), OM_UNIT_MULTIPLICATION_FIELDS),
    OM_UNIT_DIVISION: ClassSpec((OM_COMPOUND_UNIT,), OM_UNIT_DIVISION_FIELDS),
    OM_UNIT_EXPONENTIATION: ClassSpec((OM_COMPOUND_UNIT,), OM_UNIT_EXPONENTIATION_FIELDS),
    OM_PREFIXED_UNIT: ClassSpec((OM_UNIT,), OM_PREFIXED_UNIT_FIELDS),
    OM_PREFIX: ClassSpec((TOP_LEVEL,), OM_PREFIX_FIELDS),
    OM_SI_PREFIX: ClassSpec((OM_PREFIX,), ()),
    OM_BINARY_PREFIX: ClassSpec((OM_PREFIX,), ()),
}

#: the SBOL 2 data model
SCHEMA = Schema(CLASSES, TOP_LEVEL)

#: concrete class -> its "MUST NOT have properties other than ..." rule; the first class an object has wins
CLOSED_PROPERTY_RULES: tuple[tuple[str, str], ...] = (
    (SEQUENCE, "sbol2-10401"),
    (COMPONENT_DEFINITION, "sbol2-10501"),
    (COMPONENT, "sbol2-10701"),
    (MAPS_TO, "sbol2-10801"),
    (SEQUENCE_ANNOTATION, "sbol2-10901"),
    (RANGE, "sbol2-11101"),
    (CUT, "sbol2-11201"),
    (GENERIC_LOCATION, "sbol2-11301"),
    (SEQUENCE_CONSTRAINT, "sbol2-11401"),
    (MODEL, "sbol2-11501"),
    (MODULE_DEFINITION, "sbol2-11601"),
    (MODULE, "sbol2-11701"),
    (FUNCTIONAL_COMPONENT, "sbol2-11801"),
    (INTERACTION, "sbol2-11901"),
    (PARTICIPATION, "sbol2-12001"),
    (COLLECTION, "sbol2-12101"),
    (GENERIC_TOP_LEVEL, "sbol2-12301"),
    (ACTIVITY, "sbol2-12401"),
    (USAGE, "sbol2-12501"),
    (ASSOCIATION, "sbol2-12601"),
    (PLAN, "sbol2-12701"),
    (AGENT, "sbol2-12801"),
    (COMBINATORIAL_DERIVATION, "sbol2-12901"),
    (VARIABLE_COMPONENT, "sbol2-13001"),
    (IMPLEMENTATION, "sbol2-13101"),
    (ATTACHMENT, "sbol2-13201"),
    (EXPERIMENTAL_DATA, "sbol2-13301"),
    (EXPERIMENT, "sbol2-13401"),
    (OM_MEASURE, "sbol2-13501"),
)

#: predicate -> the XSD datatype the data model assigns its literals
LITERAL_DATATYPES: dict[str, str] = SCHEMA.literal_datatypes()

#: predicates whose triples are interpreted by the data model (all others are extension annotations)
MODEL_PREDICATES = frozenset([RDF_TYPE, TITLE, DESCRIPTION, RDFS_LABEL, RDFS_COMMENT])


def is_extension_predicate(predicate: str) -> bool:
    """Whether a predicate lies outside the SBOL 2, PROV, OM, and mapped Dublin Core / RDFS vocabulary."""
    return predicate not in MODEL_PREDICATES and not predicate.startswith((SBOL2_NS, PROV_NS, OM_NS))


#: reference predicate -> the rule requiring the referenced object to be in the document
COMPLETENESS_RULES = {
    SEQUENCE_P: "sbol2-10513",
    MODEL_P: "sbol2-11608",
    MEMBER: "sbol2-12103",
    TEMPLATE: "sbol2-12905",
    ATTACHMENT_P: "sbol2-10307",
    VARIANT: "sbol2-13008",
    VARIANT_COLLECTION: "sbol2-13010",
    VARIANT_DERIVATION: "sbol2-13012",
    WAS_GENERATED_BY: "sbol2-10222",
    WAS_INFORMED_BY: "sbol2-12407",
    AGENT_P: "sbol2-12606",
    HAD_PLAN: "sbol2-12604",
}

#: class a ``definition`` refers to -> the rule requiring that object to be in the document
DEFINITION_COMPLETENESS_RULES = {COMPONENT_DEFINITION: "sbol2-10604", MODULE_DEFINITION: "sbol2-11703"}


def completeness_rule(predicate: str, target: str) -> str | None:
    """The rule requiring an object referenced through ``predicate``, of class ``target``, to be in the document."""
    if predicate == DEFINITION:
        return DEFINITION_COMPLETENESS_RULES.get(target)
    return COMPLETENESS_RULES.get(predicate)


#: permitted participant-role SBO terms for each interaction-type SBO term (Table 11)
PARTICIPANT_ROLES_FOR_INTERACTION: dict[str, tuple[str, ...]] = {
    "SBO:0000169": ("SBO:0000020", "SBO:0000642", "SBO:0000598"),
    "SBO:0000170": ("SBO:0000459", "SBO:0000643", "SBO:0000598"),
    "SBO:0000177": ("SBO:0000010", "SBO:0000011"),
    "SBO:0000179": ("SBO:0000010",),
    "SBO:0000176": ("SBO:0000010", "SBO:0000011", "SBO:0000019"),
    "SBO:0000589": ("SBO:0000598", "SBO:0000645", "SBO:0000011"),
    "SBO:0000168": ("SBO:0000019", "SBO:0000644"),
}
