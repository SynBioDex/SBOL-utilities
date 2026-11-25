"""Declarative SBOL 2.3.0 data-model schema used by the validator.

Every SBOL 2, PROV-O, and OM class the specification adopts is listed with its parent classes and the properties it
declares directly. Each property carries the catalog rule governing it, its cardinality, the kind of value it holds,
and, for references, the class the referenced object must have and whether the reference names a composite child
held in the same document. The table mirrors the sbol-rs SBOL 2 schema so both validators share one model.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

SBOL2_NS = "http://sbols.org/v2#"
PROV_NS = "http://www.w3.org/ns/prov#"
OM_NS = "http://www.ontology-of-units-of-measure.org/resource/om-2/"
DCTERMS_NS = "http://purl.org/dc/terms/"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"


def _sbol(local: str) -> str:
    return SBOL2_NS + local


def _prov(local: str) -> str:
    return PROV_NS + local


def _om(local: str) -> str:
    return OM_NS + local


# --- classes -----------------------------------------------------------------------------------------------------

IDENTIFIED = _sbol("Identified")
TOP_LEVEL = _sbol("TopLevel")
MEASURED = _sbol("Measured")
COMPONENT_INSTANCE = _sbol("ComponentInstance")
LOCATION = _sbol("Location")
SEQUENCE = _sbol("Sequence")
COMPONENT_DEFINITION = _sbol("ComponentDefinition")
MODULE_DEFINITION = _sbol("ModuleDefinition")
MODEL = _sbol("Model")
COLLECTION = _sbol("Collection")
COMBINATORIAL_DERIVATION = _sbol("CombinatorialDerivation")
IMPLEMENTATION = _sbol("Implementation")
ATTACHMENT = _sbol("Attachment")
EXPERIMENTAL_DATA = _sbol("ExperimentalData")
EXPERIMENT = _sbol("Experiment")
GENERIC_TOP_LEVEL = _sbol("GenericTopLevel")
COMPONENT = _sbol("Component")
FUNCTIONAL_COMPONENT = _sbol("FunctionalComponent")
MODULE = _sbol("Module")
MAPS_TO = _sbol("MapsTo")
SEQUENCE_ANNOTATION = _sbol("SequenceAnnotation")
SEQUENCE_CONSTRAINT = _sbol("SequenceConstraint")
VARIABLE_COMPONENT = _sbol("VariableComponent")
INTERACTION = _sbol("Interaction")
PARTICIPATION = _sbol("Participation")
RANGE = _sbol("Range")
CUT = _sbol("Cut")
GENERIC_LOCATION = _sbol("GenericLocation")
ACTIVITY = _prov("Activity")
AGENT = _prov("Agent")
PLAN = _prov("Plan")
ASSOCIATION = _prov("Association")
USAGE = _prov("Usage")
OM_MEASURE = _om("Measure")
OM_UNIT = _om("Unit")
OM_SINGULAR_UNIT = _om("SingularUnit")
OM_COMPOUND_UNIT = _om("CompoundUnit")
OM_UNIT_MULTIPLICATION = _om("UnitMultiplication")
OM_UNIT_DIVISION = _om("UnitDivision")
OM_UNIT_EXPONENTIATION = _om("UnitExponentiation")
OM_PREFIXED_UNIT = _om("PrefixedUnit")
OM_PREFIX = _om("Prefix")
OM_SI_PREFIX = _om("SIPrefix")
OM_BINARY_PREFIX = _om("BinaryPrefix")

# --- predicates --------------------------------------------------------------------------------------------------

PERSISTENT_IDENTITY = _sbol("persistentIdentity")
DISPLAY_ID = _sbol("displayId")
VERSION = _sbol("version")
TITLE = DCTERMS_NS + "title"
DESCRIPTION = DCTERMS_NS + "description"
WAS_DERIVED_FROM = _prov("wasDerivedFrom")
WAS_GENERATED_BY = _prov("wasGeneratedBy")
ATTACHMENT_P = _sbol("attachment")
MEASURE = _sbol("measure")
DEFINITION = _sbol("definition")
ACCESS = _sbol("access")
MAPS_TO_P = _sbol("mapsTo")
ORIENTATION = _sbol("orientation")
SEQUENCE_P = _sbol("sequence")
ELEMENTS = _sbol("elements")
ENCODING = _sbol("encoding")
TYPE = _sbol("type")
ROLE = _sbol("role")
COMPONENT_P = _sbol("component")
SEQUENCE_ANNOTATION_P = _sbol("sequenceAnnotation")
SEQUENCE_CONSTRAINT_P = _sbol("sequenceConstraint")
MODULE_P = _sbol("module")
FUNCTIONAL_COMPONENT_P = _sbol("functionalComponent")
INTERACTION_P = _sbol("interaction")
MODEL_P = _sbol("model")
SOURCE = _sbol("source")
LANGUAGE = _sbol("language")
FRAMEWORK = _sbol("framework")
FORMAT = _sbol("format")
SIZE = _sbol("size")
HASH = _sbol("hash")
MEMBER = _sbol("member")
TEMPLATE = _sbol("template")
VARIABLE_COMPONENT_P = _sbol("variableComponent")
STRATEGY = _sbol("strategy")
BUILT = _sbol("built")
EXPERIMENTAL_DATA_P = _sbol("experimentalData")
RDF_TYPE_P = _sbol("rdfType")
ROLE_INTEGRATION = _sbol("roleIntegration")
SOURCE_LOCATION = _sbol("sourceLocation")
DIRECTION = _sbol("direction")
LOCAL = _sbol("local")
REMOTE = _sbol("remote")
REFINEMENT = _sbol("refinement")
LOCATION_P = _sbol("location")
SUBJECT = _sbol("subject")
OBJECT = _sbol("object")
RESTRICTION = _sbol("restriction")
START = _sbol("start")
END = _sbol("end")
AT = _sbol("at")
PARTICIPATION_P = _sbol("participation")
PARTICIPANT = _sbol("participant")
VARIABLE = _sbol("variable")
VARIANT = _sbol("variant")
VARIANT_COLLECTION = _sbol("variantCollection")
VARIANT_DERIVATION = _sbol("variantDerivation")
OPERATOR = _sbol("operator")
STARTED_AT_TIME = _prov("startedAtTime")
ENDED_AT_TIME = _prov("endedAtTime")
QUALIFIED_ASSOCIATION = _prov("qualifiedAssociation")
QUALIFIED_USAGE = _prov("qualifiedUsage")
WAS_INFORMED_BY = _prov("wasInformedBy")
AGENT_P = _prov("agent")
HAD_ROLE = _prov("hadRole")
HAD_PLAN = _prov("hadPlan")
ENTITY = _prov("entity")
RDFS_LABEL = RDFS_NS + "label"
RDFS_COMMENT = RDFS_NS + "comment"
OM_SYMBOL = _om("symbol")
OM_ALTERNATIVE_SYMBOL = _om("alternativeSymbol")
OM_ALTERNATIVE_LABEL = _om("alternativeLabel")
OM_LONG_COMMENT = _om("longcomment")
OM_HAS_NUMERICAL_VALUE = _om("hasNumericalValue")
OM_HAS_UNIT = _om("hasUnit")
OM_HAS_FACTOR = _om("hasFactor")
OM_HAS_TERM1 = _om("hasTerm1")
OM_HAS_TERM2 = _om("hasTerm2")
OM_HAS_NUMERATOR = _om("hasNumerator")
OM_HAS_DENOMINATOR = _om("hasDenominator")
OM_HAS_BASE = _om("hasBase")
OM_HAS_EXPONENT = _om("hasExponent")
OM_HAS_PREFIX = _om("hasPrefix")

# --- enumerated values -------------------------------------------------------------------------------------------

PUBLIC = _sbol("public")
PRIVATE = _sbol("private")
INLINE = _sbol("inline")
MERGE_ROLES = _sbol("mergeRoles")
OVERRIDE_ROLES = _sbol("overrideRoles")
VERIFY_IDENTICAL = _sbol("verifyIdentical")
USE_LOCAL = _sbol("useLocal")
USE_REMOTE = _sbol("useRemote")
MERGE = _sbol("merge")
ENUMERATE = _sbol("enumerate")
SAMPLE = _sbol("sample")
OP_ZERO_OR_ONE = _sbol("zeroOrOne")
OP_ONE = _sbol("one")
OP_ZERO_OR_MORE = _sbol("zeroOrMore")
OP_ONE_OR_MORE = _sbol("oneOrMore")
PRECEDES = _sbol("precedes")
SAME_ORIENTATION_AS = _sbol("sameOrientationAs")
OPPOSITE_ORIENTATION_AS = _sbol("oppositeOrientationAs")
DIFFERENT_FROM = _sbol("differentFrom")
ROLE_DESIGN = _sbol("design")
ROLE_BUILD = _sbol("build")
ROLE_TEST = _sbol("test")
ROLE_LEARN = _sbol("learn")

IUPAC_NUCLEIC_ENCODING = "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html"
IUPAC_PROTEIN_ENCODING = "http://www.chem.qmul.ac.uk/iupac/AminoAcid/"
SMILES_ENCODING = "http://www.opensmiles.org/opensmiles.html"
IUPAC_NUCLEIC_ALPHABET = frozenset("ACGTURYSWKMBDHVN-.")

_BIOPAX = "http://www.biopax.org/release/biopax-level3.owl#"
BIOPAX_DNA_REGION = _BIOPAX + "DnaRegion"
BIOPAX_RNA_REGION = _BIOPAX + "RnaRegion"
BIOPAX_DNA_MOLECULE = _BIOPAX + "Dna"
BIOPAX_RNA_MOLECULE = _BIOPAX + "Rna"
BIOPAX_PROTEIN = _BIOPAX + "Protein"
BIOPAX_COMPLEX = _BIOPAX + "Complex"
BIOPAX_SMALL_MOLECULE = _BIOPAX + "SmallMolecule"
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

EXACTLY_ONE = "1"
ZERO_OR_ONE = "0..1"
ONE_OR_MORE = "1..*"
ZERO_OR_MORE = "0..*"

URI = "Uri"
URL = "Url"
STRING = "String"
INTEGER = "Integer"
LONG = "Long"
FLOAT = "Float"
DATE_TIME = "DateTime"

#: canonical XSD datatype of each literal-valued kind
KIND_DATATYPES = {
    STRING: XSD_NS + "string",
    INTEGER: XSD_NS + "integer",
    LONG: XSD_NS + "long",
    FLOAT: XSD_NS + "decimal",
    DATE_TIME: XSD_NS + "dateTime",
}

#: reference targets that are not SBOL classes: the object must carry this exact rdf:type
TARGET_EXACT_TYPE = "exact"
#: reference targets satisfied by the class or any subclass
TARGET_CLASS = "class"

#: rule id of descriptors that no catalog rule governs (OM unit/prefix vocabulary, the shared measures descriptor)
NO_RULE = "sbol2-00000"


@dataclass(frozen=True)
class Reference:
    """The class a reference property must point at, and whether it names a composite child in the document."""

    target: str
    local: bool
    match: str = TARGET_CLASS


@dataclass(frozen=True)
class Field:
    """One property declared on a class."""

    rule: str
    predicate: str
    cardinality: str
    kind: str
    reference: Optional[Reference] = None


def _local(target: str, match: str = TARGET_CLASS) -> Reference:
    return Reference(target, True, match)


def _external(target: str, match: str = TARGET_CLASS) -> Reference:
    return Reference(target, False, match)


@dataclass(frozen=True)
class ClassSpec:
    """A class's parents and the fields it declares directly."""

    parents: Tuple[str, ...]
    fields: Tuple[Field, ...]


F = Field

IDENTIFIED_FIELDS = (
    F("sbol2-10203", PERSISTENT_IDENTITY, ZERO_OR_ONE, URI),
    F("sbol2-10204", DISPLAY_ID, ZERO_OR_ONE, STRING),
    F("sbol2-10206", VERSION, ZERO_OR_ONE, STRING),
    F("sbol2-10212", TITLE, ZERO_OR_ONE, STRING),
    F("sbol2-10213", DESCRIPTION, ZERO_OR_ONE, STRING),
    F("sbol2-10208", WAS_DERIVED_FROM, ZERO_OR_MORE, URI),
    F("sbol2-10221", WAS_GENERATED_BY, ZERO_OR_MORE, URI, _external(ACTIVITY, TARGET_EXACT_TYPE)),
)
TOP_LEVEL_FIELDS = (F("sbol2-10306", ATTACHMENT_P, ZERO_OR_MORE, URI, _external(ATTACHMENT)),)
MEASURED_FIELDS = (F(NO_RULE, MEASURE, ZERO_OR_MORE, URI, _local(OM_MEASURE, TARGET_EXACT_TYPE)),)
COMPONENT_INSTANCE_FIELDS = (
    F("sbol2-10602", DEFINITION, EXACTLY_ONE, URI, _external(COMPONENT_DEFINITION)),
    F("sbol2-10607", ACCESS, EXACTLY_ONE, URI),
    F("sbol2-10606", MAPS_TO_P, ZERO_OR_MORE, URI, _local(MAPS_TO)),
)
LOCATION_FIELDS = (
    F("sbol2-11002", ORIENTATION, ZERO_OR_ONE, URI),
    F("sbol2-11003", SEQUENCE_P, ZERO_OR_ONE, URI, _external(SEQUENCE)),
)
SEQUENCE_FIELDS = (
    F("sbol2-10402", ELEMENTS, EXACTLY_ONE, STRING),
    F("sbol2-10403", ENCODING, EXACTLY_ONE, URI),
)
COMPONENT_DEFINITION_FIELDS = (
    F("sbol2-10502", TYPE, ONE_OR_MORE, URI),
    F("sbol2-10507", ROLE, ZERO_OR_MORE, URI),
    F("sbol2-10512", SEQUENCE_P, ZERO_OR_MORE, URI, _external(SEQUENCE)),
    F("sbol2-10519", COMPONENT_P, ZERO_OR_MORE, URI, _local(COMPONENT)),
    F("sbol2-10521", SEQUENCE_ANNOTATION_P, ZERO_OR_MORE, URI, _local(SEQUENCE_ANNOTATION)),
    F("sbol2-10524", SEQUENCE_CONSTRAINT_P, ZERO_OR_MORE, URI, _local(SEQUENCE_CONSTRAINT)),
)
MODULE_DEFINITION_FIELDS = (
    F("sbol2-11602", ROLE, ZERO_OR_MORE, URI),
    F("sbol2-11604", MODULE_P, ZERO_OR_MORE, URI, _local(MODULE)),
    F("sbol2-11606", FUNCTIONAL_COMPONENT_P, ZERO_OR_MORE, URI, _local(FUNCTIONAL_COMPONENT)),
    F("sbol2-11605", INTERACTION_P, ZERO_OR_MORE, URI, _local(INTERACTION)),
    F("sbol2-11607", MODEL_P, ZERO_OR_MORE, URI, _external(MODEL)),
)
MODEL_FIELDS = (
    F("sbol2-11502", SOURCE, EXACTLY_ONE, URL),
    F("sbol2-11504", LANGUAGE, EXACTLY_ONE, URI),
    F("sbol2-11508", FRAMEWORK, EXACTLY_ONE, URI),
)
COLLECTION_FIELDS = (F("sbol2-12102", MEMBER, ZERO_OR_MORE, URI, _external(TOP_LEVEL)),)
COMBINATORIAL_DERIVATION_FIELDS = (
    F("sbol2-12904", TEMPLATE, EXACTLY_ONE, URI, _external(COMPONENT_DEFINITION)),
    F("sbol2-12906", VARIABLE_COMPONENT_P, ZERO_OR_MORE, URI, _local(VARIABLE_COMPONENT)),
    F("sbol2-12914", STRATEGY, ZERO_OR_ONE, URI),
)
IMPLEMENTATION_FIELDS = (F("sbol2-13102", BUILT, ZERO_OR_ONE, URI),)
ATTACHMENT_FIELDS = (
    F("sbol2-13202", SOURCE, EXACTLY_ONE, URL),
    F("sbol2-13204", FORMAT, ZERO_OR_ONE, URI),
    F("sbol2-13207", SIZE, ZERO_OR_ONE, LONG),
    F("sbol2-13208", HASH, ZERO_OR_ONE, STRING),
)
EXPERIMENT_FIELDS = (F("sbol2-13402", EXPERIMENTAL_DATA_P, ZERO_OR_MORE, URI, _external(EXPERIMENTAL_DATA)),)
GENERIC_TOP_LEVEL_FIELDS = (F("sbol2-12302", RDF_TYPE_P, EXACTLY_ONE, URI),)
COMPONENT_FIELDS = (
    F("sbol2-10702", ROLE, ZERO_OR_MORE, URI),
    F("sbol2-10708", ROLE_INTEGRATION, ZERO_OR_ONE, URI),
    F("sbol2-10710", SOURCE_LOCATION, ZERO_OR_MORE, URI, _local(LOCATION)),
)
FUNCTIONAL_COMPONENT_FIELDS = (F("sbol2-11802", DIRECTION, EXACTLY_ONE, URI),)
MODULE_FIELDS = (
    F("sbol2-11702", DEFINITION, EXACTLY_ONE, URI, _external(MODULE_DEFINITION)),
    F("sbol2-11706", MAPS_TO_P, ZERO_OR_MORE, URI, _local(MAPS_TO)),
)
MAPS_TO_FIELDS = (
    F("sbol2-10802", LOCAL, EXACTLY_ONE, URI, _external(COMPONENT_INSTANCE)),
    F("sbol2-10805", REMOTE, EXACTLY_ONE, URI, _external(COMPONENT_INSTANCE)),
    F("sbol2-10810", REFINEMENT, EXACTLY_ONE, URI),
)
SEQUENCE_ANNOTATION_FIELDS = (
    F("sbol2-10902", LOCATION_P, ONE_OR_MORE, URI, _local(LOCATION)),
    F("sbol2-10904", COMPONENT_P, ZERO_OR_ONE, URI, _external(COMPONENT)),
    F("sbol2-10906", ROLE, ZERO_OR_MORE, URI),
)
SEQUENCE_CONSTRAINT_FIELDS = (
    F("sbol2-11402", SUBJECT, EXACTLY_ONE, URI, _external(COMPONENT)),
    F("sbol2-11404", OBJECT, EXACTLY_ONE, URI, _external(COMPONENT)),
    F("sbol2-11407", RESTRICTION, EXACTLY_ONE, URI),
)
RANGE_FIELDS = (
    F("sbol2-11102", START, EXACTLY_ONE, INTEGER),
    F("sbol2-11103", END, EXACTLY_ONE, INTEGER),
)
CUT_FIELDS = (F("sbol2-11202", AT, EXACTLY_ONE, INTEGER),)
INTERACTION_FIELDS = (
    F("sbol2-11902", TYPE, ONE_OR_MORE, URI),
    F("sbol2-11906", PARTICIPATION_P, ZERO_OR_MORE, URI, _local(PARTICIPATION)),
)
PARTICIPATION_FIELDS = (
    F("sbol2-12004", ROLE, ONE_OR_MORE, URI),
    F("sbol2-12002", PARTICIPANT, EXACTLY_ONE, URI, _external(FUNCTIONAL_COMPONENT)),
)
VARIABLE_COMPONENT_FIELDS = (
    F("sbol2-13004", VARIABLE, EXACTLY_ONE, URI, _external(COMPONENT)),
    F("sbol2-13007", VARIANT, ZERO_OR_MORE, URI, _external(COMPONENT_DEFINITION)),
    F("sbol2-13009", VARIANT_COLLECTION, ZERO_OR_MORE, URI, _external(COLLECTION)),
    F("sbol2-13013", VARIANT_DERIVATION, ZERO_OR_MORE, URI, _external(COMBINATORIAL_DERIVATION)),
    F("sbol2-13002", OPERATOR, EXACTLY_ONE, URI),
)
ACTIVITY_FIELDS = (
    F("sbol2-12412", TYPE, ZERO_OR_MORE, URI),
    F("sbol2-12402", STARTED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
    F("sbol2-12403", ENDED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
    F("sbol2-12404", QUALIFIED_ASSOCIATION, ZERO_OR_MORE, URI, _local(ASSOCIATION, TARGET_EXACT_TYPE)),
    F("sbol2-12405", QUALIFIED_USAGE, ZERO_OR_MORE, URI, _local(USAGE, TARGET_EXACT_TYPE)),
    F("sbol2-12406", WAS_INFORMED_BY, ZERO_OR_MORE, URI, _external(ACTIVITY, TARGET_EXACT_TYPE)),
)
ASSOCIATION_FIELDS = (
    F("sbol2-12605", AGENT_P, EXACTLY_ONE, URI, _external(AGENT, TARGET_EXACT_TYPE)),
    F("sbol2-12602", HAD_ROLE, ZERO_OR_MORE, URI),
    F("sbol2-12603", HAD_PLAN, ZERO_OR_ONE, URI, _external(PLAN, TARGET_EXACT_TYPE)),
)
USAGE_FIELDS = (
    F("sbol2-12502", ENTITY, EXACTLY_ONE, URI),
    F("sbol2-12503", HAD_ROLE, ZERO_OR_MORE, URI),
)
OM_MEASURE_FIELDS = (
    F("sbol2-13502", OM_HAS_NUMERICAL_VALUE, EXACTLY_ONE, FLOAT),
    F("sbol2-13503", OM_HAS_UNIT, EXACTLY_ONE, URI, _external(OM_UNIT)),
    F("sbol2-13504", TYPE, ZERO_OR_MORE, URI),
)
_OM_LABELS = (
    F(NO_RULE, OM_SYMBOL, EXACTLY_ONE, STRING),
    F(NO_RULE, OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
    F(NO_RULE, RDFS_LABEL, EXACTLY_ONE, STRING),
    F(NO_RULE, OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
    F(NO_RULE, RDFS_COMMENT, ZERO_OR_ONE, STRING),
    F(NO_RULE, OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
)
OM_UNIT_FIELDS = _OM_LABELS
OM_SINGULAR_UNIT_FIELDS = (
    F(NO_RULE, OM_HAS_UNIT, ZERO_OR_ONE, URI, _external(OM_UNIT)),
    F(NO_RULE, OM_HAS_FACTOR, ZERO_OR_ONE, FLOAT),
)
OM_UNIT_MULTIPLICATION_FIELDS = (
    F(NO_RULE, OM_HAS_TERM1, EXACTLY_ONE, URI, _external(OM_UNIT)),
    F(NO_RULE, OM_HAS_TERM2, EXACTLY_ONE, URI, _external(OM_UNIT)),
)
OM_UNIT_DIVISION_FIELDS = (
    F(NO_RULE, OM_HAS_NUMERATOR, EXACTLY_ONE, URI, _external(OM_UNIT)),
    F(NO_RULE, OM_HAS_DENOMINATOR, EXACTLY_ONE, URI, _external(OM_UNIT)),
)
OM_UNIT_EXPONENTIATION_FIELDS = (
    F(NO_RULE, OM_HAS_BASE, EXACTLY_ONE, URI, _external(OM_UNIT)),
    F(NO_RULE, OM_HAS_EXPONENT, EXACTLY_ONE, INTEGER),
)
OM_PREFIXED_UNIT_FIELDS = (
    F(NO_RULE, OM_HAS_UNIT, EXACTLY_ONE, URI, _external(OM_UNIT)),
    F(NO_RULE, OM_HAS_PREFIX, EXACTLY_ONE, URI, _external(OM_PREFIX)),
)
OM_PREFIX_FIELDS = _OM_LABELS + (F(NO_RULE, OM_HAS_FACTOR, EXACTLY_ONE, FLOAT),)

#: class IRI -> (parents, directly declared fields), in the order the schema lists them
CLASSES: Dict[str, ClassSpec] = {
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

#: classes whose instances are TopLevel objects
TOP_LEVEL_CLASSES = frozenset(
    [
        TOP_LEVEL,
        SEQUENCE,
        COMPONENT_DEFINITION,
        MODULE_DEFINITION,
        MODEL,
        COLLECTION,
        COMBINATORIAL_DERIVATION,
        IMPLEMENTATION,
        ATTACHMENT,
        EXPERIMENTAL_DATA,
        EXPERIMENT,
        GENERIC_TOP_LEVEL,
        ACTIVITY,
        AGENT,
        PLAN,
        OM_UNIT,
        OM_SINGULAR_UNIT,
        OM_COMPOUND_UNIT,
        OM_UNIT_MULTIPLICATION,
        OM_UNIT_DIVISION,
        OM_UNIT_EXPONENTIATION,
        OM_PREFIXED_UNIT,
        OM_PREFIX,
        OM_SI_PREFIX,
        OM_BINARY_PREFIX,
    ]
)

#: concrete class -> its "MUST NOT have properties other than ..." rule; the first class an object has wins
CLOSED_PROPERTY_RULES: Tuple[Tuple[str, str], ...] = (
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

#: om:Unit and its subclasses
UNIT_CLASSES = (
    OM_UNIT,
    OM_SINGULAR_UNIT,
    OM_COMPOUND_UNIT,
    OM_UNIT_MULTIPLICATION,
    OM_UNIT_DIVISION,
    OM_UNIT_EXPONENTIATION,
    OM_PREFIXED_UNIT,
)


def is_a(class_iri: str, target: str) -> bool:
    """Whether ``class_iri`` is ``target`` or one of its subclasses."""
    return target in ancestors(class_iri)


@lru_cache(maxsize=None)
def ancestors(class_iri: str) -> frozenset:
    """``class_iri`` and every class it inherits from; empty for IRIs that are not schema classes."""
    spec = CLASSES.get(class_iri)
    if spec is None:
        return frozenset()
    result = {class_iri}
    for parent in spec.parents:
        result |= ancestors(parent)
    return frozenset(result)


def _collect(class_iri: str, into: Dict[str, Field]) -> None:
    spec = CLASSES.get(class_iri)
    if spec is None:
        return
    for parent in spec.parents:
        _collect(parent, into)
    for f in spec.fields:
        into[f.predicate] = f


@lru_cache(maxsize=None)
def fields_for_types(rdf_types: Tuple[str, ...]) -> Dict[str, Field]:
    """Every field (inherited and own) the sorted rdf:types resolve to, keyed by predicate; later types win."""
    result: Dict[str, Field] = {}
    for rdf_type in rdf_types:
        _collect(rdf_type, result)
    return dict(sorted(result.items()))


def _literal_datatypes(classes: Iterable[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for class_iri in classes:
        for f in CLASSES[class_iri].fields:
            datatype = KIND_DATATYPES.get(f.kind)
            if datatype:
                result[f.predicate] = datatype
    return result


#: predicate -> the XSD datatype the data model assigns its literals
LITERAL_DATATYPES: Dict[str, str] = _literal_datatypes(CLASSES)

#: predicates whose triples are interpreted by the data model (all others are extension annotations)
MODEL_PREDICATES = frozenset([RDF_TYPE, TITLE, DESCRIPTION, RDFS_LABEL, RDFS_COMMENT])


def is_extension_predicate(predicate: str) -> bool:
    """Whether a predicate lies outside the SBOL 2, PROV, OM, and mapped Dublin Core / RDFS vocabulary."""
    return predicate not in MODEL_PREDICATES and not predicate.startswith((SBOL2_NS, PROV_NS, OM_NS))


#: (predicate, reference target) -> the completeness rule requiring the referenced object in the document
def completeness_rule(predicate: str, target: str) -> Optional[str]:
    """The Complete-gated rule governing presence of an object referenced through ``predicate``."""
    if predicate == DEFINITION:
        return {COMPONENT_DEFINITION: "sbol2-10604", MODULE_DEFINITION: "sbol2-11703"}.get(target)
    return _COMPLETENESS_RULES.get(predicate)


_COMPLETENESS_RULES = {
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

#: permitted participant-role SBO terms for each interaction-type SBO term (Table 11)
PARTICIPANT_ROLES_FOR_INTERACTION: Dict[str, Tuple[str, ...]] = {
    "SBO:0000169": ("SBO:0000020", "SBO:0000642", "SBO:0000598"),
    "SBO:0000170": ("SBO:0000459", "SBO:0000643", "SBO:0000598"),
    "SBO:0000177": ("SBO:0000010", "SBO:0000011"),
    "SBO:0000179": ("SBO:0000010",),
    "SBO:0000176": ("SBO:0000010", "SBO:0000011", "SBO:0000019"),
    "SBO:0000589": ("SBO:0000598", "SBO:0000645", "SBO:0000011"),
    "SBO:0000168": ("SBO:0000019", "SBO:0000644"),
}


def field_rules() -> List[str]:
    """Every catalog rule a property descriptor carries."""
    return sorted({f.rule for spec in CLASSES.values() for f in spec.fields if f.rule != NO_RULE})
