"""The SBOL 3.1.0 data model (Table 23 and the adopted PROV-O and OM classes), as a schema the validator reads.

Each class lists its direct parents and the properties it declares, with cardinality, value kind, and, for
references, the target class and whether the target is a child held in the same document.
"""

from __future__ import annotations

from sbol_utilities.validation.schema import Cardinality, ClassSpec, PropertySpec, Reference, Schema, ValueKind
from sbol_utilities.vocab import OM_NS, PROV_NS, SBOL3_NS


def _sbol(local: str) -> str:
    return SBOL3_NS + local


def _prov(local: str) -> str:
    return PROV_NS + local


def _om(local: str) -> str:
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


def _value(predicate: str, cardinality: Cardinality, kind: ValueKind) -> PropertySpec:
    """A property holding literals or IRIs that are not references to objects of the model."""
    return PropertySpec(predicate, cardinality, kind)


def _child(predicate: str, cardinality: Cardinality, target: str) -> PropertySpec:
    """A property referring to children held in the same document."""
    return PropertySpec(predicate, cardinality, URI, Reference(target, local=True))


def _reference(predicate: str, cardinality: Cardinality, target: str) -> PropertySpec:
    """A property referring to objects that may live in another document."""
    return PropertySpec(predicate, cardinality, URI, Reference(target, local=False))


IDENTIFIED = _sbol("Identified")
TOP_LEVEL = _sbol("TopLevel")
ATTACHMENT = _sbol("Attachment")
COLLECTION = _sbol("Collection")
COMBINATORIAL_DERIVATION = _sbol("CombinatorialDerivation")
COMPONENT = _sbol("Component")
COMPONENT_REFERENCE = _sbol("ComponentReference")
CONSTRAINT = _sbol("Constraint")
CUT = _sbol("Cut")
ENTIRE_SEQUENCE = _sbol("EntireSequence")
EXPERIMENT = _sbol("Experiment")
EXPERIMENTAL_DATA = _sbol("ExperimentalData")
EXTERNALLY_DEFINED = _sbol("ExternallyDefined")
FEATURE = _sbol("Feature")
IMPLEMENTATION = _sbol("Implementation")
INTERACTION = _sbol("Interaction")
INTERFACE = _sbol("Interface")
LOCATION = _sbol("Location")
LOCAL_SUB_COMPONENT = _sbol("LocalSubComponent")
MODEL = _sbol("Model")
PARTICIPATION = _sbol("Participation")
RANGE = _sbol("Range")
SEQUENCE = _sbol("Sequence")
SEQUENCE_FEATURE = _sbol("SequenceFeature")
SUB_COMPONENT = _sbol("SubComponent")
VARIABLE_FEATURE = _sbol("VariableFeature")
PROV_ACTIVITY = _prov("Activity")
PROV_AGENT = _prov("Agent")
PROV_ASSOCIATION = _prov("Association")
PROV_PLAN = _prov("Plan")
PROV_USAGE = _prov("Usage")
OM_MEASURE = _om("Measure")
OM_UNIT = _om("Unit")
OM_SINGULAR_UNIT = _om("SingularUnit")
OM_COMPOUND_UNIT = _om("CompoundUnit")
OM_UNIT_DIVISION = _om("UnitDivision")
OM_UNIT_EXPONENTIATION = _om("UnitExponentiation")
OM_UNIT_MULTIPLICATION = _om("UnitMultiplication")
OM_PREFIXED_UNIT = _om("PrefixedUnit")
OM_PREFIX = _om("Prefix")
OM_SI_PREFIX = _om("SIPrefix")
OM_BINARY_PREFIX = _om("BinaryPrefix")

# Predicates
DISPLAY_ID = _sbol("displayId")
NAME = _sbol("name")
DESCRIPTION = _sbol("description")
HAS_NAMESPACE = _sbol("hasNamespace")
HAS_ATTACHMENT = _sbol("hasAttachment")
HAS_MEASURE = _sbol("hasMeasure")
TYPE = _sbol("type")
ROLE = _sbol("role")
ELEMENTS = _sbol("elements")
ENCODING = _sbol("encoding")
SOURCE = _sbol("source")
FORMAT = _sbol("format")
SIZE = _sbol("size")
HASH = _sbol("hash")
HASH_ALGORITHM = _sbol("hashAlgorithm")
MEMBER = _sbol("member")
TEMPLATE = _sbol("template")
STRATEGY = _sbol("strategy")
HAS_VARIABLE_FEATURE = _sbol("hasVariableFeature")
IN_CHILD_OF = _sbol("inChildOf")
REFERS_TO = _sbol("refersTo")
HAS_SEQUENCE = _sbol("hasSequence")
HAS_FEATURE = _sbol("hasFeature")
HAS_CONSTRAINT = _sbol("hasConstraint")
HAS_INTERACTION = _sbol("hasInteraction")
HAS_INTERFACE = _sbol("hasInterface")
HAS_MODEL = _sbol("hasModel")
SUBJECT = _sbol("subject")
OBJECT = _sbol("object")
RESTRICTION = _sbol("restriction")
AT = _sbol("at")
DEFINITION = _sbol("definition")
ORIENTATION = _sbol("orientation")
ORDER = _sbol("order")
HAS_LOCATION = _sbol("hasLocation")
INSTANCE_OF = _sbol("instanceOf")
ROLE_INTEGRATION = _sbol("roleIntegration")
SOURCE_LOCATION = _sbol("sourceLocation")
LANGUAGE = _sbol("language")
FRAMEWORK = _sbol("framework")
HAS_PARTICIPATION = _sbol("hasParticipation")
PARTICIPANT = _sbol("participant")
HIGHER_ORDER_PARTICIPANT = _sbol("higherOrderParticipant")
INPUT = _sbol("input")
OUTPUT = _sbol("output")
NONDIRECTIONAL = _sbol("nondirectional")
START = _sbol("start")
END = _sbol("end")
BUILT = _sbol("built")
CARDINALITY = _sbol("cardinality")
VARIABLE = _sbol("variable")
VARIANT = _sbol("variant")
VARIANT_COLLECTION = _sbol("variantCollection")
VARIANT_DERIVATION = _sbol("variantDerivation")
VARIANT_MEASURE = _sbol("variantMeasure")
PROV_WAS_DERIVED_FROM = _prov("wasDerivedFrom")
PROV_WAS_GENERATED_BY = _prov("wasGeneratedBy")
PROV_ENDED_AT_TIME = _prov("endedAtTime")
PROV_STARTED_AT_TIME = _prov("startedAtTime")
PROV_ENTITY = _prov("entity")
PROV_HAD_PLAN = _prov("hadPlan")
PROV_HAD_ROLE = _prov("hadRole")
PROV_QUALIFIED_ASSOCIATION = _prov("qualifiedAssociation")
PROV_QUALIFIED_USAGE = _prov("qualifiedUsage")
PROV_WAS_INFORMED_BY = _prov("wasInformedBy")
PROV_AGENT_PREDICATE = _prov("agent")
OM_HAS_UNIT = _om("hasUnit")
OM_HAS_NUMERICAL_VALUE = _om("hasNumericalValue")
OM_HAS_PREFIX = _om("hasPrefix")
OM_ALTERNATIVE_LABEL = _om("alternativeLabel")
OM_ALTERNATIVE_SYMBOL = _om("alternativeSymbol")
OM_COMMENT = _om("comment")
OM_HAS_FACTOR = _om("hasFactor")
OM_LABEL = _om("label")
OM_LONG_COMMENT = _om("longcomment")
OM_SYMBOL = _om("symbol")
OM_HAS_DENOMINATOR = _om("hasDenominator")
OM_HAS_NUMERATOR = _om("hasNumerator")
OM_HAS_BASE = _om("hasBase")
OM_HAS_EXPONENT = _om("hasExponent")
OM_HAS_TERM1 = _om("hasTerm1")
OM_HAS_TERM2 = _om("hasTerm2")

# Vocabulary values
INLINE = _sbol("inline")
REVERSE_COMPLEMENT = _sbol("reverseComplement")
SO_INLINE = "https://identifiers.org/SO:0001030"
SO_REVERSE_COMPLEMENT = "https://identifiers.org/SO:0001031"
MERGE_ROLES = _sbol("mergeRoles")
OVERRIDE_ROLES = _sbol("overrideRoles")
ENUMERATE = _sbol("enumerate")
SAMPLE = _sbol("sample")
ONE = _sbol("one")
ZERO_OR_ONE_VALUE = _sbol("zeroOrOne")
ONE_OR_MORE_VALUE = _sbol("oneOrMore")
ZERO_OR_MORE_VALUE = _sbol("zeroOrMore")
PRECEDES = _sbol("precedes")
STRICTLY_PRECEDES = _sbol("strictlyPrecedes")
MEETS = _sbol("meets")
IS_DISJOINT_FROM = _sbol("isDisjointFrom")
CONTAINS = _sbol("contains")
STRICTLY_CONTAINS = _sbol("strictlyContains")
EQUALS = _sbol("equals")
COVERS = _sbol("covers")
OVERLAPS = _sbol("overlaps")
FINISHES = _sbol("finishes")
STARTS = _sbol("starts")
SAME_ORIENTATION_AS = _sbol("sameOrientationAs")
OPPOSITE_ORIENTATION_AS = _sbol("oppositeOrientationAs")
DIFFERENT_FROM = _sbol("differentFrom")
VERIFY_IDENTICAL = _sbol("verifyIdentical")
REPLACES = _sbol("replaces")
DESIGN = _sbol("design")
BUILD = _sbol("build")
TEST = _sbol("test")
LEARN = _sbol("learn")

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
            _value(DISPLAY_ID, ZERO_OR_ONE, STRING),
            _value(NAME, ZERO_OR_ONE, STRING),
            _value(DESCRIPTION, ZERO_OR_ONE, STRING),
            _child(HAS_MEASURE, ZERO_OR_MORE, OM_MEASURE),
            _value(PROV_WAS_DERIVED_FROM, ZERO_OR_MORE, URI),
            _reference(PROV_WAS_GENERATED_BY, ZERO_OR_MORE, PROV_ACTIVITY),
        ),
    ),
    TOP_LEVEL: ClassSpec(
        (IDENTIFIED,),
        (
            _value(HAS_NAMESPACE, EXACTLY_ONE, URL),
            _reference(HAS_ATTACHMENT, ZERO_OR_MORE, ATTACHMENT),
        ),
    ),
    ATTACHMENT: ClassSpec(
        (TOP_LEVEL,),
        (
            _value(SOURCE, EXACTLY_ONE, URI),
            _value(FORMAT, ZERO_OR_ONE, URI),
            _value(HASH_ALGORITHM, ZERO_OR_ONE, STRING),
            _value(HASH, ZERO_OR_ONE, STRING),
            _value(SIZE, ZERO_OR_ONE, LONG),
        ),
    ),
    COLLECTION: ClassSpec((TOP_LEVEL,), (_reference(MEMBER, ZERO_OR_MORE, TOP_LEVEL),)),
    COMBINATORIAL_DERIVATION: ClassSpec(
        (TOP_LEVEL,),
        (
            _reference(TEMPLATE, EXACTLY_ONE, COMPONENT),
            _value(STRATEGY, ZERO_OR_ONE, URI),
            _child(HAS_VARIABLE_FEATURE, ZERO_OR_MORE, VARIABLE_FEATURE),
        ),
    ),
    COMPONENT: ClassSpec(
        (TOP_LEVEL,),
        (
            _reference(HAS_SEQUENCE, ZERO_OR_MORE, SEQUENCE),
            _value(ROLE, ZERO_OR_MORE, URI),
            _value(TYPE, ONE_OR_MORE, URI),
            _child(HAS_CONSTRAINT, ZERO_OR_MORE, CONSTRAINT),
            _child(HAS_FEATURE, ZERO_OR_MORE, FEATURE),
            _child(HAS_INTERACTION, ZERO_OR_MORE, INTERACTION),
            _child(HAS_INTERFACE, ZERO_OR_MORE, INTERFACE),
            _reference(HAS_MODEL, ZERO_OR_MORE, MODEL),
        ),
    ),
    COMPONENT_REFERENCE: ClassSpec(
        (FEATURE,),
        (
            _reference(REFERS_TO, EXACTLY_ONE, FEATURE),
            _reference(IN_CHILD_OF, EXACTLY_ONE, SUB_COMPONENT),
        ),
    ),
    CONSTRAINT: ClassSpec(
        (IDENTIFIED,),
        (
            _reference(OBJECT, EXACTLY_ONE, FEATURE),
            _value(RESTRICTION, EXACTLY_ONE, URI),
            _reference(SUBJECT, EXACTLY_ONE, FEATURE),
        ),
    ),
    CUT: ClassSpec((LOCATION,), (_value(AT, EXACTLY_ONE, INTEGER),)),
    ENTIRE_SEQUENCE: ClassSpec((LOCATION,), ()),
    EXPERIMENT: ClassSpec((COLLECTION,), ()),
    EXPERIMENTAL_DATA: ClassSpec((TOP_LEVEL,), ()),
    EXTERNALLY_DEFINED: ClassSpec(
        (FEATURE,),
        (_value(DEFINITION, EXACTLY_ONE, URI), _value(TYPE, ONE_OR_MORE, URI)),
    ),
    FEATURE: ClassSpec((IDENTIFIED,), (_value(ROLE, ZERO_OR_MORE, URI), _value(ORIENTATION, ZERO_OR_ONE, URI))),
    IMPLEMENTATION: ClassSpec((TOP_LEVEL,), (_reference(BUILT, ZERO_OR_ONE, COMPONENT),)),
    INTERACTION: ClassSpec(
        (IDENTIFIED,),
        (_value(TYPE, ONE_OR_MORE, URI), _child(HAS_PARTICIPATION, ZERO_OR_MORE, PARTICIPATION)),
    ),
    INTERFACE: ClassSpec(
        (IDENTIFIED,),
        (
            _reference(INPUT, ZERO_OR_MORE, FEATURE),
            _reference(OUTPUT, ZERO_OR_MORE, FEATURE),
            _reference(NONDIRECTIONAL, ZERO_OR_MORE, FEATURE),
        ),
    ),
    LOCATION: ClassSpec(
        (IDENTIFIED,),
        (
            _value(ORIENTATION, ZERO_OR_ONE, URI),
            _value(ORDER, ZERO_OR_ONE, INTEGER),
            _reference(HAS_SEQUENCE, EXACTLY_ONE, SEQUENCE),
        ),
    ),
    LOCAL_SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (_child(HAS_LOCATION, ZERO_OR_MORE, LOCATION), _value(TYPE, ONE_OR_MORE, URI)),
    ),
    MODEL: ClassSpec(
        (TOP_LEVEL,),
        (_value(SOURCE, EXACTLY_ONE, URI), _value(FRAMEWORK, EXACTLY_ONE, URI), _value(LANGUAGE, EXACTLY_ONE, URI)),
    ),
    PARTICIPATION: ClassSpec(
        (IDENTIFIED,),
        (
            _reference(PARTICIPANT, ZERO_OR_ONE, FEATURE),
            _reference(HIGHER_ORDER_PARTICIPANT, ZERO_OR_ONE, INTERACTION),
            _value(ROLE, ONE_OR_MORE, URI),
        ),
    ),
    RANGE: ClassSpec((LOCATION,), (_value(END, EXACTLY_ONE, INTEGER), _value(START, EXACTLY_ONE, INTEGER))),
    SEQUENCE: ClassSpec((TOP_LEVEL,), (_value(ELEMENTS, ZERO_OR_ONE, STRING), _value(ENCODING, ZERO_OR_ONE, URI))),
    SEQUENCE_FEATURE: ClassSpec((FEATURE,), (_child(HAS_LOCATION, ONE_OR_MORE, LOCATION),)),
    SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (
            _reference(INSTANCE_OF, EXACTLY_ONE, COMPONENT),
            _value(ROLE_INTEGRATION, ZERO_OR_ONE, URI),
            _child(SOURCE_LOCATION, ZERO_OR_MORE, LOCATION),
            _child(HAS_LOCATION, ZERO_OR_MORE, LOCATION),
        ),
    ),
    VARIABLE_FEATURE: ClassSpec(
        (IDENTIFIED,),
        (
            _value(CARDINALITY, EXACTLY_ONE, URI),
            _reference(VARIABLE, EXACTLY_ONE, FEATURE),
            _reference(VARIANT_COLLECTION, ZERO_OR_MORE, COLLECTION),
            _reference(VARIANT_DERIVATION, ZERO_OR_MORE, COMBINATORIAL_DERIVATION),
            _child(VARIANT_MEASURE, ZERO_OR_MORE, OM_MEASURE),
            _reference(VARIANT, ZERO_OR_MORE, COMPONENT),
        ),
    ),
    PROV_ACTIVITY: ClassSpec(
        (TOP_LEVEL,),
        (
            _value(PROV_ENDED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            _child(PROV_QUALIFIED_USAGE, ZERO_OR_MORE, PROV_USAGE),
            _value(PROV_STARTED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            _reference(PROV_WAS_INFORMED_BY, ZERO_OR_MORE, PROV_ACTIVITY),
            _value(TYPE, ZERO_OR_MORE, URI),
            _child(PROV_QUALIFIED_ASSOCIATION, ZERO_OR_MORE, PROV_ASSOCIATION),
        ),
    ),
    PROV_AGENT: ClassSpec((TOP_LEVEL,), ()),
    PROV_ASSOCIATION: ClassSpec(
        (IDENTIFIED,),
        (
            _reference(PROV_AGENT_PREDICATE, EXACTLY_ONE, PROV_AGENT),
            _value(PROV_HAD_ROLE, ZERO_OR_MORE, URI),
            _reference(PROV_HAD_PLAN, ZERO_OR_ONE, PROV_PLAN),
        ),
    ),
    PROV_PLAN: ClassSpec((TOP_LEVEL,), ()),
    PROV_USAGE: ClassSpec(
        (IDENTIFIED,), (_value(PROV_ENTITY, EXACTLY_ONE, URI), _value(PROV_HAD_ROLE, ZERO_OR_MORE, URI))
    ),
    OM_MEASURE: ClassSpec(
        (IDENTIFIED,),
        (
            _value(TYPE, ZERO_OR_MORE, URI),
            _reference(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT),
            _value(OM_HAS_NUMERICAL_VALUE, EXACTLY_ONE, FLOAT),
        ),
    ),
    OM_UNIT: ClassSpec(
        (TOP_LEVEL,),
        (
            _value(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            _value(OM_LABEL, EXACTLY_ONE, STRING),
            _value(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            _value(OM_SYMBOL, EXACTLY_ONE, STRING),
            _value(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            _value(OM_COMMENT, ZERO_OR_ONE, STRING),
        ),
    ),
    OM_SINGULAR_UNIT: ClassSpec(
        (OM_UNIT,),
        (_reference(OM_HAS_UNIT, ZERO_OR_ONE, OM_UNIT), _value(OM_HAS_FACTOR, ZERO_OR_ONE, FLOAT)),
    ),
    OM_COMPOUND_UNIT: ClassSpec((OM_UNIT,), ()),
    OM_UNIT_DIVISION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            _reference(OM_HAS_DENOMINATOR, EXACTLY_ONE, OM_UNIT),
            _reference(OM_HAS_NUMERATOR, EXACTLY_ONE, OM_UNIT),
        ),
    ),
    OM_UNIT_EXPONENTIATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (_reference(OM_HAS_BASE, EXACTLY_ONE, OM_UNIT), _value(OM_HAS_EXPONENT, EXACTLY_ONE, INTEGER)),
    ),
    OM_UNIT_MULTIPLICATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            _reference(OM_HAS_TERM1, EXACTLY_ONE, OM_UNIT),
            _reference(OM_HAS_TERM2, EXACTLY_ONE, OM_UNIT),
        ),
    ),
    OM_PREFIXED_UNIT: ClassSpec(
        (OM_UNIT,),
        (
            _reference(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT),
            _reference(OM_HAS_PREFIX, EXACTLY_ONE, OM_PREFIX),
        ),
    ),
    OM_PREFIX: ClassSpec(
        (TOP_LEVEL,),
        (
            _value(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            _value(OM_COMMENT, ZERO_OR_ONE, STRING),
            _value(OM_HAS_FACTOR, EXACTLY_ONE, FLOAT),
            _value(OM_LABEL, EXACTLY_ONE, STRING),
            _value(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            _value(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            _value(OM_SYMBOL, EXACTLY_ONE, STRING),
        ),
    ),
    OM_SI_PREFIX: ClassSpec((OM_PREFIX,), ()),
    OM_BINARY_PREFIX: ClassSpec((OM_PREFIX,), ()),
}

#: the SBOL 3 data model
SCHEMA = Schema(CLASS_SPECS, TOP_LEVEL)

#: Order in which a multiply-typed object is assigned its primary typed kind (sbol-rs ``SbolObject`` dispatch)
TYPED_DISPATCH_ORDER: tuple[str, ...] = (
    ATTACHMENT,
    EXPERIMENT,
    COLLECTION,
    COMBINATORIAL_DERIVATION,
    COMPONENT,
    COMPONENT_REFERENCE,
    CONSTRAINT,
    CUT,
    ENTIRE_SEQUENCE,
    EXPERIMENTAL_DATA,
    EXTERNALLY_DEFINED,
    IMPLEMENTATION,
    INTERACTION,
    INTERFACE,
    LOCAL_SUB_COMPONENT,
    MODEL,
    PARTICIPATION,
    RANGE,
    SEQUENCE,
    SEQUENCE_FEATURE,
    SUB_COMPONENT,
    VARIABLE_FEATURE,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ASSOCIATION,
    PROV_PLAN,
    PROV_USAGE,
    OM_UNIT_DIVISION,
    OM_UNIT_EXPONENTIATION,
    OM_UNIT_MULTIPLICATION,
    OM_SINGULAR_UNIT,
    OM_COMPOUND_UNIT,
    OM_PREFIXED_UNIT,
    OM_UNIT,
    OM_SI_PREFIX,
    OM_BINARY_PREFIX,
    OM_PREFIX,
    OM_MEASURE,
)


def is_known_sbol_iri(iri: str) -> bool:
    """Whether an IRI is a known class, property, or vocabulary value."""
    return iri in SCHEMA or iri in SCHEMA.predicates or iri in KNOWN_VALUE_IRIS


def local_name(class_iri: str) -> str:
    """Local name of a class IRI, after its namespace."""
    for namespace in (SBOL3_NS, PROV_NS, OM_NS):
        if class_iri.startswith(namespace):
            return class_iri[len(namespace) :]
    return class_iri
