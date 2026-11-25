"""The SBOL 3.1.0 data model (Table 23 and the adopted PROV-O and OM classes), as a schema the validator reads.

Each class lists its direct parents and the properties it declares, with cardinality, value kind, and, for
references, the target class and whether the target is a child held in the same document.
"""

from __future__ import annotations

from sbol_utilities.validation.schema import Cardinality, ClassSpec, PropertySpec, Reference, Schema, ValueKind
from sbol_utilities.vocab import OM_NS, PROV_NS, SBOL3_NS


def sbol_iri(local: str) -> str:
    """The IRI of a term in the SBOL 3 namespace."""
    return SBOL3_NS + local


def prov_iri(local: str) -> str:
    """The IRI of a term in the PROV namespace."""
    return PROV_NS + local


def om_iri(local: str) -> str:
    """The IRI of a term in the OM namespace."""
    return OM_NS + local


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


def value_property(predicate: str, cardinality: Cardinality, kind: ValueKind) -> PropertySpec:
    """A property holding literals or IRIs that are not references to objects of the model."""
    return PropertySpec(predicate, cardinality, kind)


def child_property(predicate: str, cardinality: Cardinality, target: str) -> PropertySpec:
    """A property referring to children held in the same document."""
    return PropertySpec(predicate, cardinality, URI, Reference(target, local=True))


def reference_property(predicate: str, cardinality: Cardinality, target: str) -> PropertySpec:
    """A property referring to objects that may live in another document."""
    return PropertySpec(predicate, cardinality, URI, Reference(target, local=False))


IDENTIFIED = sbol_iri("Identified")
TOP_LEVEL = sbol_iri("TopLevel")
ATTACHMENT = sbol_iri("Attachment")
COLLECTION = sbol_iri("Collection")
COMBINATORIAL_DERIVATION = sbol_iri("CombinatorialDerivation")
COMPONENT = sbol_iri("Component")
COMPONENT_REFERENCE = sbol_iri("ComponentReference")
CONSTRAINT = sbol_iri("Constraint")
CUT = sbol_iri("Cut")
ENTIRE_SEQUENCE = sbol_iri("EntireSequence")
EXPERIMENT = sbol_iri("Experiment")
EXPERIMENTAL_DATA = sbol_iri("ExperimentalData")
EXTERNALLY_DEFINED = sbol_iri("ExternallyDefined")
FEATURE = sbol_iri("Feature")
IMPLEMENTATION = sbol_iri("Implementation")
INTERACTION = sbol_iri("Interaction")
INTERFACE = sbol_iri("Interface")
LOCATION = sbol_iri("Location")
LOCAL_SUB_COMPONENT = sbol_iri("LocalSubComponent")
MODEL = sbol_iri("Model")
PARTICIPATION = sbol_iri("Participation")
RANGE = sbol_iri("Range")
SEQUENCE = sbol_iri("Sequence")
SEQUENCE_FEATURE = sbol_iri("SequenceFeature")
SUB_COMPONENT = sbol_iri("SubComponent")
VARIABLE_FEATURE = sbol_iri("VariableFeature")
PROV_ACTIVITY = prov_iri("Activity")
PROV_AGENT = prov_iri("Agent")
PROV_ASSOCIATION = prov_iri("Association")
PROV_PLAN = prov_iri("Plan")
PROV_USAGE = prov_iri("Usage")
OM_MEASURE = om_iri("Measure")
OM_UNIT = om_iri("Unit")
OM_SINGULAR_UNIT = om_iri("SingularUnit")
OM_COMPOUND_UNIT = om_iri("CompoundUnit")
OM_UNIT_DIVISION = om_iri("UnitDivision")
OM_UNIT_EXPONENTIATION = om_iri("UnitExponentiation")
OM_UNIT_MULTIPLICATION = om_iri("UnitMultiplication")
OM_PREFIXED_UNIT = om_iri("PrefixedUnit")
OM_PREFIX = om_iri("Prefix")
OM_SI_PREFIX = om_iri("SIPrefix")
OM_BINARY_PREFIX = om_iri("BinaryPrefix")

# Predicates
DISPLAY_ID = sbol_iri("displayId")
NAME = sbol_iri("name")
DESCRIPTION = sbol_iri("description")
HAS_NAMESPACE = sbol_iri("hasNamespace")
HAS_ATTACHMENT = sbol_iri("hasAttachment")
HAS_MEASURE = sbol_iri("hasMeasure")
TYPE = sbol_iri("type")
ROLE = sbol_iri("role")
ELEMENTS = sbol_iri("elements")
ENCODING = sbol_iri("encoding")
SOURCE = sbol_iri("source")
FORMAT = sbol_iri("format")
SIZE = sbol_iri("size")
HASH = sbol_iri("hash")
HASH_ALGORITHM = sbol_iri("hashAlgorithm")
MEMBER = sbol_iri("member")
TEMPLATE = sbol_iri("template")
STRATEGY = sbol_iri("strategy")
HAS_VARIABLE_FEATURE = sbol_iri("hasVariableFeature")
IN_CHILD_OF = sbol_iri("inChildOf")
REFERS_TO = sbol_iri("refersTo")
HAS_SEQUENCE = sbol_iri("hasSequence")
HAS_FEATURE = sbol_iri("hasFeature")
HAS_CONSTRAINT = sbol_iri("hasConstraint")
HAS_INTERACTION = sbol_iri("hasInteraction")
HAS_INTERFACE = sbol_iri("hasInterface")
HAS_MODEL = sbol_iri("hasModel")
SUBJECT = sbol_iri("subject")
OBJECT = sbol_iri("object")
RESTRICTION = sbol_iri("restriction")
AT = sbol_iri("at")
DEFINITION = sbol_iri("definition")
ORIENTATION = sbol_iri("orientation")
ORDER = sbol_iri("order")
HAS_LOCATION = sbol_iri("hasLocation")
INSTANCE_OF = sbol_iri("instanceOf")
ROLE_INTEGRATION = sbol_iri("roleIntegration")
SOURCE_LOCATION = sbol_iri("sourceLocation")
LANGUAGE = sbol_iri("language")
FRAMEWORK = sbol_iri("framework")
HAS_PARTICIPATION = sbol_iri("hasParticipation")
PARTICIPANT = sbol_iri("participant")
HIGHER_ORDER_PARTICIPANT = sbol_iri("higherOrderParticipant")
INPUT = sbol_iri("input")
OUTPUT = sbol_iri("output")
NONDIRECTIONAL = sbol_iri("nondirectional")
START = sbol_iri("start")
END = sbol_iri("end")
BUILT = sbol_iri("built")
CARDINALITY = sbol_iri("cardinality")
VARIABLE = sbol_iri("variable")
VARIANT = sbol_iri("variant")
VARIANT_COLLECTION = sbol_iri("variantCollection")
VARIANT_DERIVATION = sbol_iri("variantDerivation")
VARIANT_MEASURE = sbol_iri("variantMeasure")
PROV_WAS_DERIVED_FROM = prov_iri("wasDerivedFrom")
PROV_WAS_GENERATED_BY = prov_iri("wasGeneratedBy")
PROV_ENDED_AT_TIME = prov_iri("endedAtTime")
PROV_STARTED_AT_TIME = prov_iri("startedAtTime")
PROV_ENTITY = prov_iri("entity")
PROV_HAD_PLAN = prov_iri("hadPlan")
PROV_HAD_ROLE = prov_iri("hadRole")
PROV_QUALIFIED_ASSOCIATION = prov_iri("qualifiedAssociation")
PROV_QUALIFIED_USAGE = prov_iri("qualifiedUsage")
PROV_WAS_INFORMED_BY = prov_iri("wasInformedBy")
PROV_AGENT_PREDICATE = prov_iri("agent")
OM_HAS_UNIT = om_iri("hasUnit")
OM_HAS_NUMERICAL_VALUE = om_iri("hasNumericalValue")
OM_HAS_PREFIX = om_iri("hasPrefix")
OM_ALTERNATIVE_LABEL = om_iri("alternativeLabel")
OM_ALTERNATIVE_SYMBOL = om_iri("alternativeSymbol")
OM_COMMENT = om_iri("comment")
OM_HAS_FACTOR = om_iri("hasFactor")
OM_LABEL = om_iri("label")
OM_LONG_COMMENT = om_iri("longcomment")
OM_SYMBOL = om_iri("symbol")
OM_HAS_DENOMINATOR = om_iri("hasDenominator")
OM_HAS_NUMERATOR = om_iri("hasNumerator")
OM_HAS_BASE = om_iri("hasBase")
OM_HAS_EXPONENT = om_iri("hasExponent")
OM_HAS_TERM1 = om_iri("hasTerm1")
OM_HAS_TERM2 = om_iri("hasTerm2")

# Vocabulary values
INLINE = sbol_iri("inline")
REVERSE_COMPLEMENT = sbol_iri("reverseComplement")
SO_INLINE = "https://identifiers.org/SO:0001030"
SO_REVERSE_COMPLEMENT = "https://identifiers.org/SO:0001031"
MERGE_ROLES = sbol_iri("mergeRoles")
OVERRIDE_ROLES = sbol_iri("overrideRoles")
ENUMERATE = sbol_iri("enumerate")
SAMPLE = sbol_iri("sample")
ONE = sbol_iri("one")
ZERO_OR_ONE_VALUE = sbol_iri("zeroOrOne")
ONE_OR_MORE_VALUE = sbol_iri("oneOrMore")
ZERO_OR_MORE_VALUE = sbol_iri("zeroOrMore")
PRECEDES = sbol_iri("precedes")
STRICTLY_PRECEDES = sbol_iri("strictlyPrecedes")
MEETS = sbol_iri("meets")
IS_DISJOINT_FROM = sbol_iri("isDisjointFrom")
CONTAINS = sbol_iri("contains")
STRICTLY_CONTAINS = sbol_iri("strictlyContains")
EQUALS = sbol_iri("equals")
COVERS = sbol_iri("covers")
OVERLAPS = sbol_iri("overlaps")
FINISHES = sbol_iri("finishes")
STARTS = sbol_iri("starts")
SAME_ORIENTATION_AS = sbol_iri("sameOrientationAs")
OPPOSITE_ORIENTATION_AS = sbol_iri("oppositeOrientationAs")
DIFFERENT_FROM = sbol_iri("differentFrom")
VERIFY_IDENTICAL = sbol_iri("verifyIdentical")
REPLACES = sbol_iri("replaces")
DESIGN = sbol_iri("design")
BUILD = sbol_iri("build")
TEST = sbol_iri("test")
LEARN = sbol_iri("learn")

ORIENTATION_IRIS = frozenset({INLINE, REVERSE_COMPLEMENT, SO_INLINE, SO_REVERSE_COMPLEMENT})
ROLE_INTEGRATION_IRIS = frozenset({MERGE_ROLES, OVERRIDE_ROLES})
STRATEGY_IRIS = frozenset({ENUMERATE, SAMPLE})
CARDINALITY_IRIS = frozenset({ONE, ZERO_OR_ONE_VALUE, ONE_OR_MORE_VALUE, ZERO_OR_MORE_VALUE})
RESTRICTION_IRIS = frozenset(
    {
        VERIFY_IDENTICAL,
        DIFFERENT_FROM,
        REPLACES,
        SAME_ORIENTATION_AS,
        OPPOSITE_ORIENTATION_AS,
        IS_DISJOINT_FROM,
        STRICTLY_CONTAINS,
        CONTAINS,
        EQUALS,
        MEETS,
        COVERS,
        OVERLAPS,
        PRECEDES,
        STRICTLY_PRECEDES,
        FINISHES,
        STARTS,
    }
)
SEQUENTIAL_RESTRICTION_IRIS = frozenset(
    {PRECEDES, STRICTLY_PRECEDES, MEETS, OVERLAPS, CONTAINS, STRICTLY_CONTAINS, EQUALS, FINISHES, STARTS}
)
KNOWN_VALUE_IRIS = frozenset(
    ORIENTATION_IRIS - {SO_INLINE, SO_REVERSE_COMPLEMENT}
    | ROLE_INTEGRATION_IRIS
    | STRATEGY_IRIS
    | CARDINALITY_IRIS
    | RESTRICTION_IRIS
    | {DESIGN, BUILD, TEST, LEARN}
)

#: Predicates whose values are child objects owned by the subject
COMPOSITE_PREDICATES = (
    HAS_FEATURE,
    HAS_CONSTRAINT,
    HAS_INTERACTION,
    HAS_INTERFACE,
    HAS_LOCATION,
    SOURCE_LOCATION,
    HAS_PARTICIPATION,
    HAS_VARIABLE_FEATURE,
    PROV_QUALIFIED_USAGE,
    PROV_QUALIFIED_ASSOCIATION,
)

CLASS_SPECS: dict[str, ClassSpec] = {
    IDENTIFIED: ClassSpec(
        (),
        (
            value_property(DISPLAY_ID, ZERO_OR_ONE, STRING),
            value_property(NAME, ZERO_OR_ONE, STRING),
            value_property(DESCRIPTION, ZERO_OR_ONE, STRING),
            child_property(HAS_MEASURE, ZERO_OR_MORE, OM_MEASURE),
            value_property(PROV_WAS_DERIVED_FROM, ZERO_OR_MORE, URI),
            reference_property(PROV_WAS_GENERATED_BY, ZERO_OR_MORE, PROV_ACTIVITY),
        ),
    ),
    TOP_LEVEL: ClassSpec(
        (IDENTIFIED,),
        (
            value_property(HAS_NAMESPACE, EXACTLY_ONE, URL),
            reference_property(HAS_ATTACHMENT, ZERO_OR_MORE, ATTACHMENT),
        ),
    ),
    ATTACHMENT: ClassSpec(
        (TOP_LEVEL,),
        (
            value_property(SOURCE, EXACTLY_ONE, URI),
            value_property(FORMAT, ZERO_OR_ONE, URI),
            value_property(HASH_ALGORITHM, ZERO_OR_ONE, STRING),
            value_property(HASH, ZERO_OR_ONE, STRING),
            value_property(SIZE, ZERO_OR_ONE, LONG),
        ),
    ),
    COLLECTION: ClassSpec((TOP_LEVEL,), (reference_property(MEMBER, ZERO_OR_MORE, TOP_LEVEL),)),
    COMBINATORIAL_DERIVATION: ClassSpec(
        (TOP_LEVEL,),
        (
            reference_property(TEMPLATE, EXACTLY_ONE, COMPONENT),
            value_property(STRATEGY, ZERO_OR_ONE, URI),
            child_property(HAS_VARIABLE_FEATURE, ZERO_OR_MORE, VARIABLE_FEATURE),
        ),
    ),
    COMPONENT: ClassSpec(
        (TOP_LEVEL,),
        (
            reference_property(HAS_SEQUENCE, ZERO_OR_MORE, SEQUENCE),
            value_property(ROLE, ZERO_OR_MORE, URI),
            value_property(TYPE, ONE_OR_MORE, URI),
            child_property(HAS_CONSTRAINT, ZERO_OR_MORE, CONSTRAINT),
            child_property(HAS_FEATURE, ZERO_OR_MORE, FEATURE),
            child_property(HAS_INTERACTION, ZERO_OR_MORE, INTERACTION),
            child_property(HAS_INTERFACE, ZERO_OR_MORE, INTERFACE),
            reference_property(HAS_MODEL, ZERO_OR_MORE, MODEL),
        ),
    ),
    COMPONENT_REFERENCE: ClassSpec(
        (FEATURE,),
        (
            reference_property(REFERS_TO, EXACTLY_ONE, FEATURE),
            reference_property(IN_CHILD_OF, EXACTLY_ONE, SUB_COMPONENT),
        ),
    ),
    CONSTRAINT: ClassSpec(
        (IDENTIFIED,),
        (
            reference_property(OBJECT, EXACTLY_ONE, FEATURE),
            value_property(RESTRICTION, EXACTLY_ONE, URI),
            reference_property(SUBJECT, EXACTLY_ONE, FEATURE),
        ),
    ),
    CUT: ClassSpec((LOCATION,), (value_property(AT, EXACTLY_ONE, INTEGER),)),
    ENTIRE_SEQUENCE: ClassSpec((LOCATION,), ()),
    EXPERIMENT: ClassSpec((COLLECTION,), ()),
    EXPERIMENTAL_DATA: ClassSpec((TOP_LEVEL,), ()),
    EXTERNALLY_DEFINED: ClassSpec(
        (FEATURE,),
        (value_property(DEFINITION, EXACTLY_ONE, URI), value_property(TYPE, ONE_OR_MORE, URI)),
    ),
    FEATURE: ClassSpec(
        (IDENTIFIED,), (value_property(ROLE, ZERO_OR_MORE, URI), value_property(ORIENTATION, ZERO_OR_ONE, URI))
    ),
    IMPLEMENTATION: ClassSpec((TOP_LEVEL,), (reference_property(BUILT, ZERO_OR_ONE, COMPONENT),)),
    INTERACTION: ClassSpec(
        (IDENTIFIED,),
        (value_property(TYPE, ONE_OR_MORE, URI), child_property(HAS_PARTICIPATION, ZERO_OR_MORE, PARTICIPATION)),
    ),
    INTERFACE: ClassSpec(
        (IDENTIFIED,),
        (
            reference_property(INPUT, ZERO_OR_MORE, FEATURE),
            reference_property(OUTPUT, ZERO_OR_MORE, FEATURE),
            reference_property(NONDIRECTIONAL, ZERO_OR_MORE, FEATURE),
        ),
    ),
    LOCATION: ClassSpec(
        (IDENTIFIED,),
        (
            value_property(ORIENTATION, ZERO_OR_ONE, URI),
            value_property(ORDER, ZERO_OR_ONE, INTEGER),
            reference_property(HAS_SEQUENCE, EXACTLY_ONE, SEQUENCE),
        ),
    ),
    LOCAL_SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (child_property(HAS_LOCATION, ZERO_OR_MORE, LOCATION), value_property(TYPE, ONE_OR_MORE, URI)),
    ),
    MODEL: ClassSpec(
        (TOP_LEVEL,),
        (
            value_property(SOURCE, EXACTLY_ONE, URI),
            value_property(FRAMEWORK, EXACTLY_ONE, URI),
            value_property(LANGUAGE, EXACTLY_ONE, URI),
        ),
    ),
    PARTICIPATION: ClassSpec(
        (IDENTIFIED,),
        (
            reference_property(PARTICIPANT, ZERO_OR_ONE, FEATURE),
            reference_property(HIGHER_ORDER_PARTICIPANT, ZERO_OR_ONE, INTERACTION),
            value_property(ROLE, ONE_OR_MORE, URI),
        ),
    ),
    RANGE: ClassSpec(
        (LOCATION,), (value_property(END, EXACTLY_ONE, INTEGER), value_property(START, EXACTLY_ONE, INTEGER))
    ),
    SEQUENCE: ClassSpec(
        (TOP_LEVEL,), (value_property(ELEMENTS, ZERO_OR_ONE, STRING), value_property(ENCODING, ZERO_OR_ONE, URI))
    ),
    SEQUENCE_FEATURE: ClassSpec((FEATURE,), (child_property(HAS_LOCATION, ONE_OR_MORE, LOCATION),)),
    SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (
            reference_property(INSTANCE_OF, EXACTLY_ONE, COMPONENT),
            value_property(ROLE_INTEGRATION, ZERO_OR_ONE, URI),
            child_property(SOURCE_LOCATION, ZERO_OR_MORE, LOCATION),
            child_property(HAS_LOCATION, ZERO_OR_MORE, LOCATION),
        ),
    ),
    VARIABLE_FEATURE: ClassSpec(
        (IDENTIFIED,),
        (
            value_property(CARDINALITY, EXACTLY_ONE, URI),
            reference_property(VARIABLE, EXACTLY_ONE, FEATURE),
            reference_property(VARIANT_COLLECTION, ZERO_OR_MORE, COLLECTION),
            reference_property(VARIANT_DERIVATION, ZERO_OR_MORE, COMBINATORIAL_DERIVATION),
            child_property(VARIANT_MEASURE, ZERO_OR_MORE, OM_MEASURE),
            reference_property(VARIANT, ZERO_OR_MORE, COMPONENT),
        ),
    ),
    PROV_ACTIVITY: ClassSpec(
        (TOP_LEVEL,),
        (
            value_property(PROV_ENDED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            child_property(PROV_QUALIFIED_USAGE, ZERO_OR_MORE, PROV_USAGE),
            value_property(PROV_STARTED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            reference_property(PROV_WAS_INFORMED_BY, ZERO_OR_MORE, PROV_ACTIVITY),
            value_property(TYPE, ZERO_OR_MORE, URI),
            child_property(PROV_QUALIFIED_ASSOCIATION, ZERO_OR_MORE, PROV_ASSOCIATION),
        ),
    ),
    PROV_AGENT: ClassSpec((TOP_LEVEL,), ()),
    PROV_ASSOCIATION: ClassSpec(
        (IDENTIFIED,),
        (
            reference_property(PROV_AGENT_PREDICATE, EXACTLY_ONE, PROV_AGENT),
            value_property(PROV_HAD_ROLE, ZERO_OR_MORE, URI),
            reference_property(PROV_HAD_PLAN, ZERO_OR_ONE, PROV_PLAN),
        ),
    ),
    PROV_PLAN: ClassSpec((TOP_LEVEL,), ()),
    PROV_USAGE: ClassSpec(
        (IDENTIFIED,), (value_property(PROV_ENTITY, EXACTLY_ONE, URI), value_property(PROV_HAD_ROLE, ZERO_OR_MORE, URI))
    ),
    OM_MEASURE: ClassSpec(
        (IDENTIFIED,),
        (
            value_property(TYPE, ZERO_OR_MORE, URI),
            reference_property(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT),
            value_property(OM_HAS_NUMERICAL_VALUE, EXACTLY_ONE, FLOAT),
        ),
    ),
    OM_UNIT: ClassSpec(
        (TOP_LEVEL,),
        (
            value_property(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            value_property(OM_LABEL, EXACTLY_ONE, STRING),
            value_property(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            value_property(OM_SYMBOL, EXACTLY_ONE, STRING),
            value_property(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            value_property(OM_COMMENT, ZERO_OR_ONE, STRING),
        ),
    ),
    OM_SINGULAR_UNIT: ClassSpec(
        (OM_UNIT,),
        (reference_property(OM_HAS_UNIT, ZERO_OR_ONE, OM_UNIT), value_property(OM_HAS_FACTOR, ZERO_OR_ONE, FLOAT)),
    ),
    OM_COMPOUND_UNIT: ClassSpec((OM_UNIT,), ()),
    OM_UNIT_DIVISION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            reference_property(OM_HAS_DENOMINATOR, EXACTLY_ONE, OM_UNIT),
            reference_property(OM_HAS_NUMERATOR, EXACTLY_ONE, OM_UNIT),
        ),
    ),
    OM_UNIT_EXPONENTIATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (reference_property(OM_HAS_BASE, EXACTLY_ONE, OM_UNIT), value_property(OM_HAS_EXPONENT, EXACTLY_ONE, INTEGER)),
    ),
    OM_UNIT_MULTIPLICATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            reference_property(OM_HAS_TERM1, EXACTLY_ONE, OM_UNIT),
            reference_property(OM_HAS_TERM2, EXACTLY_ONE, OM_UNIT),
        ),
    ),
    OM_PREFIXED_UNIT: ClassSpec(
        (OM_UNIT,),
        (
            reference_property(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT),
            reference_property(OM_HAS_PREFIX, EXACTLY_ONE, OM_PREFIX),
        ),
    ),
    OM_PREFIX: ClassSpec(
        (TOP_LEVEL,),
        (
            value_property(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            value_property(OM_COMMENT, ZERO_OR_ONE, STRING),
            value_property(OM_HAS_FACTOR, EXACTLY_ONE, FLOAT),
            value_property(OM_LABEL, EXACTLY_ONE, STRING),
            value_property(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            value_property(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            value_property(OM_SYMBOL, EXACTLY_ONE, STRING),
        ),
    ),
    OM_SI_PREFIX: ClassSpec((OM_PREFIX,), ()),
    OM_BINARY_PREFIX: ClassSpec((OM_PREFIX,), ()),
}

#: the SBOL 3 data model
SCHEMA = Schema(CLASS_SPECS, TOP_LEVEL)


def is_known_sbol_iri(iri: str) -> bool:
    """Whether an IRI is a known class, property, or vocabulary value."""
    return iri in SCHEMA or iri in SCHEMA.predicates or iri in KNOWN_VALUE_IRIS


def local_name(class_iri: str) -> str:
    """Local name of a class IRI, after its namespace."""
    for namespace in (SBOL3_NS, PROV_NS, OM_NS):
        if class_iri.startswith(namespace):
            return class_iri[len(namespace) :]
    return class_iri
