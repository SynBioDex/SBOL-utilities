"""Declarative SBOL 3.1.0 class and property tables (Table 23 and the adopted PROV-O / OM classes).

Mirrors sbol-rs ``crates/sbol3/src/validation/spec``: each class lists its direct parents and the properties declared
on it, with cardinality, lexical value kind, and, for reference properties, the target class and whether the target
must be a child held in the same document. The structural engine (:mod:`.structural`) and the class hierarchy used by
every rule read these tables.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

SBOL = "http://sbols.org/v3#"
PROV = "http://www.w3.org/ns/prov#"
OM = "http://www.ontology-of-units-of-measure.org/resource/om-2/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# Cardinalities
EXACTLY_ONE = "ExactlyOne"
ZERO_OR_ONE = "ZeroOrOne"
ONE_OR_MORE = "OneOrMore"
ZERO_OR_MORE = "ZeroOrMore"

# Value kinds
URI = "Uri"
URL = "Url"
STRING = "String"
INTEGER = "Integer"
LONG = "Long"
FLOAT = "Float"
DATE_TIME = "DateTime"

# Reference targets that are not SBOL classes (matched by exact rdf:type, or by OM class inheritance)
PROV_ACTIVITY_TARGET = "ProvActivity"
PROV_AGENT_TARGET = "ProvAgent"
PROV_ASSOCIATION_TARGET = "ProvAssociation"
PROV_PLAN_TARGET = "ProvPlan"
PROV_USAGE_TARGET = "ProvUsage"
OM_MEASURE_TARGET = "OmMeasure"
OM_UNIT_TARGET = "OmUnit"
OM_PREFIX_TARGET = "OmPrefix"


@dataclass(frozen=True)
class PropertySpec:
    """One property row: predicate, cardinality, value kind, and optional reference target."""

    predicate: str
    cardinality: str
    value_kind: str
    #: an SBOL class IRI or one of the ``*_TARGET`` tokens, for reference properties
    target: str | None = None
    #: the target must be present in the document (a contained child)
    require_local: bool = False
    #: rule policing this property's cardinality
    rule: str = "sbol3-10110"


@dataclass(frozen=True)
class ClassSpec:
    """One class: its direct parents and the properties it declares."""

    parents: tuple[str, ...]
    fields: tuple[PropertySpec, ...]


def _p(predicate: str, cardinality: str, kind: str) -> PropertySpec:
    return PropertySpec(predicate, cardinality, kind)


def _local(predicate: str, cardinality: str, target: str) -> PropertySpec:
    return PropertySpec(predicate, cardinality, URI, target, True)


def _external(predicate: str, cardinality: str, target: str) -> PropertySpec:
    return PropertySpec(predicate, cardinality, URI, target, False)


S = SBOL
IDENTIFIED = S + "Identified"
TOP_LEVEL = S + "TopLevel"
ATTACHMENT = S + "Attachment"
COLLECTION = S + "Collection"
COMBINATORIAL_DERIVATION = S + "CombinatorialDerivation"
COMPONENT = S + "Component"
COMPONENT_REFERENCE = S + "ComponentReference"
CONSTRAINT = S + "Constraint"
CUT = S + "Cut"
ENTIRE_SEQUENCE = S + "EntireSequence"
EXPERIMENT = S + "Experiment"
EXPERIMENTAL_DATA = S + "ExperimentalData"
EXTERNALLY_DEFINED = S + "ExternallyDefined"
FEATURE = S + "Feature"
IMPLEMENTATION = S + "Implementation"
INTERACTION = S + "Interaction"
INTERFACE = S + "Interface"
LOCATION = S + "Location"
LOCAL_SUB_COMPONENT = S + "LocalSubComponent"
MODEL = S + "Model"
PARTICIPATION = S + "Participation"
RANGE = S + "Range"
SEQUENCE = S + "Sequence"
SEQUENCE_FEATURE = S + "SequenceFeature"
SUB_COMPONENT = S + "SubComponent"
VARIABLE_FEATURE = S + "VariableFeature"
PROV_ACTIVITY = PROV + "Activity"
PROV_AGENT = PROV + "Agent"
PROV_ASSOCIATION = PROV + "Association"
PROV_PLAN = PROV + "Plan"
PROV_USAGE = PROV + "Usage"
OM_MEASURE = OM + "Measure"
OM_UNIT = OM + "Unit"
OM_SINGULAR_UNIT = OM + "SingularUnit"
OM_COMPOUND_UNIT = OM + "CompoundUnit"
OM_UNIT_DIVISION = OM + "UnitDivision"
OM_UNIT_EXPONENTIATION = OM + "UnitExponentiation"
OM_UNIT_MULTIPLICATION = OM + "UnitMultiplication"
OM_PREFIXED_UNIT = OM + "PrefixedUnit"
OM_PREFIX = OM + "Prefix"
OM_SI_PREFIX = OM + "SIPrefix"
OM_BINARY_PREFIX = OM + "BinaryPrefix"

# Predicates
DISPLAY_ID = S + "displayId"
NAME = S + "name"
DESCRIPTION = S + "description"
HAS_NAMESPACE = S + "hasNamespace"
HAS_ATTACHMENT = S + "hasAttachment"
HAS_MEASURE = S + "hasMeasure"
TYPE = S + "type"
ROLE = S + "role"
ELEMENTS = S + "elements"
ENCODING = S + "encoding"
SOURCE = S + "source"
FORMAT = S + "format"
SIZE = S + "size"
HASH = S + "hash"
HASH_ALGORITHM = S + "hashAlgorithm"
MEMBER = S + "member"
TEMPLATE = S + "template"
STRATEGY = S + "strategy"
HAS_VARIABLE_FEATURE = S + "hasVariableFeature"
IN_CHILD_OF = S + "inChildOf"
REFERS_TO = S + "refersTo"
HAS_SEQUENCE = S + "hasSequence"
HAS_FEATURE = S + "hasFeature"
HAS_CONSTRAINT = S + "hasConstraint"
HAS_INTERACTION = S + "hasInteraction"
HAS_INTERFACE = S + "hasInterface"
HAS_MODEL = S + "hasModel"
SUBJECT = S + "subject"
OBJECT = S + "object"
RESTRICTION = S + "restriction"
AT = S + "at"
DEFINITION = S + "definition"
ORIENTATION = S + "orientation"
ORDER = S + "order"
HAS_LOCATION = S + "hasLocation"
INSTANCE_OF = S + "instanceOf"
ROLE_INTEGRATION = S + "roleIntegration"
SOURCE_LOCATION = S + "sourceLocation"
LANGUAGE = S + "language"
FRAMEWORK = S + "framework"
HAS_PARTICIPATION = S + "hasParticipation"
PARTICIPANT = S + "participant"
HIGHER_ORDER_PARTICIPANT = S + "higherOrderParticipant"
INPUT = S + "input"
OUTPUT = S + "output"
NONDIRECTIONAL = S + "nondirectional"
START = S + "start"
END = S + "end"
BUILT = S + "built"
CARDINALITY = S + "cardinality"
VARIABLE = S + "variable"
VARIANT = S + "variant"
VARIANT_COLLECTION = S + "variantCollection"
VARIANT_DERIVATION = S + "variantDerivation"
VARIANT_MEASURE = S + "variantMeasure"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy"
PROV_ENDED_AT_TIME = PROV + "endedAtTime"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"
PROV_ENTITY = PROV + "entity"
PROV_HAD_PLAN = PROV + "hadPlan"
PROV_HAD_ROLE = PROV + "hadRole"
PROV_QUALIFIED_ASSOCIATION = PROV + "qualifiedAssociation"
PROV_QUALIFIED_USAGE = PROV + "qualifiedUsage"
PROV_WAS_INFORMED_BY = PROV + "wasInformedBy"
PROV_AGENT_PREDICATE = PROV + "agent"
OM_HAS_UNIT = OM + "hasUnit"
OM_HAS_NUMERICAL_VALUE = OM + "hasNumericalValue"
OM_HAS_PREFIX = OM + "hasPrefix"
OM_ALTERNATIVE_LABEL = OM + "alternativeLabel"
OM_ALTERNATIVE_SYMBOL = OM + "alternativeSymbol"
OM_COMMENT = OM + "comment"
OM_HAS_FACTOR = OM + "hasFactor"
OM_LABEL = OM + "label"
OM_LONG_COMMENT = OM + "longcomment"
OM_SYMBOL = OM + "symbol"
OM_HAS_DENOMINATOR = OM + "hasDenominator"
OM_HAS_NUMERATOR = OM + "hasNumerator"
OM_HAS_BASE = OM + "hasBase"
OM_HAS_EXPONENT = OM + "hasExponent"
OM_HAS_TERM1 = OM + "hasTerm1"
OM_HAS_TERM2 = OM + "hasTerm2"

# Vocabulary values
INLINE = S + "inline"
REVERSE_COMPLEMENT = S + "reverseComplement"
SO_INLINE = "https://identifiers.org/SO:0001030"
SO_REVERSE_COMPLEMENT = "https://identifiers.org/SO:0001031"
MERGE_ROLES = S + "mergeRoles"
OVERRIDE_ROLES = S + "overrideRoles"
ENUMERATE = S + "enumerate"
SAMPLE = S + "sample"
ONE = S + "one"
ZERO_OR_ONE_VALUE = S + "zeroOrOne"
ONE_OR_MORE_VALUE = S + "oneOrMore"
ZERO_OR_MORE_VALUE = S + "zeroOrMore"
PRECEDES = S + "precedes"
STRICTLY_PRECEDES = S + "strictlyPrecedes"
MEETS = S + "meets"
IS_DISJOINT_FROM = S + "isDisjointFrom"
CONTAINS = S + "contains"
STRICTLY_CONTAINS = S + "strictlyContains"
EQUALS = S + "equals"
COVERS = S + "covers"
OVERLAPS = S + "overlaps"
FINISHES = S + "finishes"
STARTS = S + "starts"
SAME_ORIENTATION_AS = S + "sameOrientationAs"
OPPOSITE_ORIENTATION_AS = S + "oppositeOrientationAs"
DIFFERENT_FROM = S + "differentFrom"
VERIFY_IDENTICAL = S + "verifyIdentical"
REPLACES = S + "replaces"
DESIGN = S + "design"
BUILD = S + "build"
TEST = S + "test"
LEARN = S + "learn"

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
            _p(DISPLAY_ID, ZERO_OR_ONE, STRING),
            _p(NAME, ZERO_OR_ONE, STRING),
            _p(DESCRIPTION, ZERO_OR_ONE, STRING),
            _local(HAS_MEASURE, ZERO_OR_MORE, OM_MEASURE_TARGET),
            _p(PROV_WAS_DERIVED_FROM, ZERO_OR_MORE, URI),
            _external(PROV_WAS_GENERATED_BY, ZERO_OR_MORE, PROV_ACTIVITY_TARGET),
        ),
    ),
    TOP_LEVEL: ClassSpec(
        (IDENTIFIED,),
        (
            _p(HAS_NAMESPACE, EXACTLY_ONE, URL),
            _external(HAS_ATTACHMENT, ZERO_OR_MORE, ATTACHMENT),
        ),
    ),
    ATTACHMENT: ClassSpec(
        (TOP_LEVEL,),
        (
            _p(SOURCE, EXACTLY_ONE, URI),
            _p(FORMAT, ZERO_OR_ONE, URI),
            _p(HASH_ALGORITHM, ZERO_OR_ONE, STRING),
            _p(HASH, ZERO_OR_ONE, STRING),
            _p(SIZE, ZERO_OR_ONE, LONG),
        ),
    ),
    COLLECTION: ClassSpec((TOP_LEVEL,), (_external(MEMBER, ZERO_OR_MORE, TOP_LEVEL),)),
    COMBINATORIAL_DERIVATION: ClassSpec(
        (TOP_LEVEL,),
        (
            _external(TEMPLATE, EXACTLY_ONE, COMPONENT),
            _p(STRATEGY, ZERO_OR_ONE, URI),
            _local(HAS_VARIABLE_FEATURE, ZERO_OR_MORE, VARIABLE_FEATURE),
        ),
    ),
    COMPONENT: ClassSpec(
        (TOP_LEVEL,),
        (
            _external(HAS_SEQUENCE, ZERO_OR_MORE, SEQUENCE),
            _p(ROLE, ZERO_OR_MORE, URI),
            _p(TYPE, ONE_OR_MORE, URI),
            _local(HAS_CONSTRAINT, ZERO_OR_MORE, CONSTRAINT),
            _local(HAS_FEATURE, ZERO_OR_MORE, FEATURE),
            _local(HAS_INTERACTION, ZERO_OR_MORE, INTERACTION),
            _local(HAS_INTERFACE, ZERO_OR_MORE, INTERFACE),
            _external(HAS_MODEL, ZERO_OR_MORE, MODEL),
        ),
    ),
    COMPONENT_REFERENCE: ClassSpec(
        (FEATURE,),
        (
            _external(REFERS_TO, EXACTLY_ONE, FEATURE),
            _external(IN_CHILD_OF, EXACTLY_ONE, SUB_COMPONENT),
        ),
    ),
    CONSTRAINT: ClassSpec(
        (IDENTIFIED,),
        (
            _external(OBJECT, EXACTLY_ONE, FEATURE),
            _p(RESTRICTION, EXACTLY_ONE, URI),
            _external(SUBJECT, EXACTLY_ONE, FEATURE),
        ),
    ),
    CUT: ClassSpec((LOCATION,), (_p(AT, EXACTLY_ONE, INTEGER),)),
    ENTIRE_SEQUENCE: ClassSpec((LOCATION,), ()),
    EXPERIMENT: ClassSpec((COLLECTION,), ()),
    EXPERIMENTAL_DATA: ClassSpec((TOP_LEVEL,), ()),
    EXTERNALLY_DEFINED: ClassSpec(
        (FEATURE,),
        (_p(DEFINITION, EXACTLY_ONE, URI), _p(TYPE, ONE_OR_MORE, URI)),
    ),
    FEATURE: ClassSpec((IDENTIFIED,), (_p(ROLE, ZERO_OR_MORE, URI), _p(ORIENTATION, ZERO_OR_ONE, URI))),
    IMPLEMENTATION: ClassSpec((TOP_LEVEL,), (_external(BUILT, ZERO_OR_ONE, COMPONENT),)),
    INTERACTION: ClassSpec(
        (IDENTIFIED,),
        (_p(TYPE, ONE_OR_MORE, URI), _local(HAS_PARTICIPATION, ZERO_OR_MORE, PARTICIPATION)),
    ),
    INTERFACE: ClassSpec(
        (IDENTIFIED,),
        (
            _external(INPUT, ZERO_OR_MORE, FEATURE),
            _external(OUTPUT, ZERO_OR_MORE, FEATURE),
            _external(NONDIRECTIONAL, ZERO_OR_MORE, FEATURE),
        ),
    ),
    LOCATION: ClassSpec(
        (IDENTIFIED,),
        (
            _p(ORIENTATION, ZERO_OR_ONE, URI),
            _p(ORDER, ZERO_OR_ONE, INTEGER),
            _external(HAS_SEQUENCE, EXACTLY_ONE, SEQUENCE),
        ),
    ),
    LOCAL_SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (_local(HAS_LOCATION, ZERO_OR_MORE, LOCATION), _p(TYPE, ONE_OR_MORE, URI)),
    ),
    MODEL: ClassSpec(
        (TOP_LEVEL,),
        (_p(SOURCE, EXACTLY_ONE, URI), _p(FRAMEWORK, EXACTLY_ONE, URI), _p(LANGUAGE, EXACTLY_ONE, URI)),
    ),
    PARTICIPATION: ClassSpec(
        (IDENTIFIED,),
        (
            _external(PARTICIPANT, ZERO_OR_ONE, FEATURE),
            _external(HIGHER_ORDER_PARTICIPANT, ZERO_OR_ONE, INTERACTION),
            _p(ROLE, ONE_OR_MORE, URI),
        ),
    ),
    RANGE: ClassSpec((LOCATION,), (_p(END, EXACTLY_ONE, INTEGER), _p(START, EXACTLY_ONE, INTEGER))),
    SEQUENCE: ClassSpec((TOP_LEVEL,), (_p(ELEMENTS, ZERO_OR_ONE, STRING), _p(ENCODING, ZERO_OR_ONE, URI))),
    SEQUENCE_FEATURE: ClassSpec((FEATURE,), (_local(HAS_LOCATION, ONE_OR_MORE, LOCATION),)),
    SUB_COMPONENT: ClassSpec(
        (FEATURE,),
        (
            _external(INSTANCE_OF, EXACTLY_ONE, COMPONENT),
            _p(ROLE_INTEGRATION, ZERO_OR_ONE, URI),
            _local(SOURCE_LOCATION, ZERO_OR_MORE, LOCATION),
            _local(HAS_LOCATION, ZERO_OR_MORE, LOCATION),
        ),
    ),
    VARIABLE_FEATURE: ClassSpec(
        (IDENTIFIED,),
        (
            _p(CARDINALITY, EXACTLY_ONE, URI),
            _external(VARIABLE, EXACTLY_ONE, FEATURE),
            _external(VARIANT_COLLECTION, ZERO_OR_MORE, COLLECTION),
            _external(VARIANT_DERIVATION, ZERO_OR_MORE, COMBINATORIAL_DERIVATION),
            _local(VARIANT_MEASURE, ZERO_OR_MORE, OM_MEASURE_TARGET),
            _external(VARIANT, ZERO_OR_MORE, COMPONENT),
        ),
    ),
    PROV_ACTIVITY: ClassSpec(
        (TOP_LEVEL,),
        (
            _p(PROV_ENDED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            _local(PROV_QUALIFIED_USAGE, ZERO_OR_MORE, PROV_USAGE_TARGET),
            _p(PROV_STARTED_AT_TIME, ZERO_OR_ONE, DATE_TIME),
            _external(PROV_WAS_INFORMED_BY, ZERO_OR_MORE, PROV_ACTIVITY_TARGET),
            _p(TYPE, ZERO_OR_MORE, URI),
            _local(PROV_QUALIFIED_ASSOCIATION, ZERO_OR_MORE, PROV_ASSOCIATION_TARGET),
        ),
    ),
    PROV_AGENT: ClassSpec((TOP_LEVEL,), ()),
    PROV_ASSOCIATION: ClassSpec(
        (IDENTIFIED,),
        (
            _external(PROV_AGENT_PREDICATE, EXACTLY_ONE, PROV_AGENT_TARGET),
            _p(PROV_HAD_ROLE, ZERO_OR_MORE, URI),
            _external(PROV_HAD_PLAN, ZERO_OR_ONE, PROV_PLAN_TARGET),
        ),
    ),
    PROV_PLAN: ClassSpec((TOP_LEVEL,), ()),
    PROV_USAGE: ClassSpec((IDENTIFIED,), (_p(PROV_ENTITY, EXACTLY_ONE, URI), _p(PROV_HAD_ROLE, ZERO_OR_MORE, URI))),
    OM_MEASURE: ClassSpec(
        (IDENTIFIED,),
        (
            _p(TYPE, ZERO_OR_MORE, URI),
            _external(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT_TARGET),
            _p(OM_HAS_NUMERICAL_VALUE, EXACTLY_ONE, FLOAT),
        ),
    ),
    OM_UNIT: ClassSpec(
        (TOP_LEVEL,),
        (
            _p(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            _p(OM_LABEL, EXACTLY_ONE, STRING),
            _p(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            _p(OM_SYMBOL, EXACTLY_ONE, STRING),
            _p(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            _p(OM_COMMENT, ZERO_OR_ONE, STRING),
        ),
    ),
    OM_SINGULAR_UNIT: ClassSpec(
        (OM_UNIT,),
        (_external(OM_HAS_UNIT, ZERO_OR_ONE, OM_UNIT_TARGET), _p(OM_HAS_FACTOR, ZERO_OR_ONE, FLOAT)),
    ),
    OM_COMPOUND_UNIT: ClassSpec((OM_UNIT,), ()),
    OM_UNIT_DIVISION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            _external(OM_HAS_DENOMINATOR, EXACTLY_ONE, OM_UNIT_TARGET),
            _external(OM_HAS_NUMERATOR, EXACTLY_ONE, OM_UNIT_TARGET),
        ),
    ),
    OM_UNIT_EXPONENTIATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (_external(OM_HAS_BASE, EXACTLY_ONE, OM_UNIT_TARGET), _p(OM_HAS_EXPONENT, EXACTLY_ONE, INTEGER)),
    ),
    OM_UNIT_MULTIPLICATION: ClassSpec(
        (OM_COMPOUND_UNIT,),
        (
            _external(OM_HAS_TERM1, EXACTLY_ONE, OM_UNIT_TARGET),
            _external(OM_HAS_TERM2, EXACTLY_ONE, OM_UNIT_TARGET),
        ),
    ),
    OM_PREFIXED_UNIT: ClassSpec(
        (OM_UNIT,),
        (
            _external(OM_HAS_UNIT, EXACTLY_ONE, OM_UNIT_TARGET),
            _external(OM_HAS_PREFIX, EXACTLY_ONE, OM_PREFIX_TARGET),
        ),
    ),
    OM_PREFIX: ClassSpec(
        (TOP_LEVEL,),
        (
            _p(OM_ALTERNATIVE_LABEL, ZERO_OR_MORE, STRING),
            _p(OM_COMMENT, ZERO_OR_ONE, STRING),
            _p(OM_HAS_FACTOR, EXACTLY_ONE, FLOAT),
            _p(OM_LABEL, EXACTLY_ONE, STRING),
            _p(OM_LONG_COMMENT, ZERO_OR_ONE, STRING),
            _p(OM_ALTERNATIVE_SYMBOL, ZERO_OR_MORE, STRING),
            _p(OM_SYMBOL, EXACTLY_ONE, STRING),
        ),
    ),
    OM_SI_PREFIX: ClassSpec((OM_PREFIX,), ()),
    OM_BINARY_PREFIX: ClassSpec((OM_PREFIX,), ()),
}

#: Classes that make an object a TopLevel
TOP_LEVEL_CLASSES: frozenset[str] = frozenset(
    {
        TOP_LEVEL,
        ATTACHMENT,
        COLLECTION,
        COMBINATORIAL_DERIVATION,
        COMPONENT,
        EXPERIMENT,
        EXPERIMENTAL_DATA,
        IMPLEMENTATION,
        MODEL,
        SEQUENCE,
        PROV_ACTIVITY,
        PROV_AGENT,
        PROV_PLAN,
        OM_UNIT,
        OM_SINGULAR_UNIT,
        OM_COMPOUND_UNIT,
        OM_UNIT_DIVISION,
        OM_UNIT_EXPONENTIATION,
        OM_UNIT_MULTIPLICATION,
        OM_PREFIXED_UNIT,
        OM_PREFIX,
        OM_SI_PREFIX,
        OM_BINARY_PREFIX,
    }
)

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

KNOWN_PROPERTIES: frozenset[str] = frozenset(f.predicate for c in CLASS_SPECS.values() for f in c.fields)


def _ancestors(class_iri: str) -> frozenset[str]:
    result = {class_iri}
    for parent in CLASS_SPECS[class_iri].parents:
        result |= _ancestors(parent)
    return frozenset(result)


#: class IRI -> the class and every ancestor
ANCESTORS: dict[str, frozenset[str]] = {iri: _ancestors(iri) for iri in CLASS_SPECS}


def is_a(class_iri: str, target: str) -> bool:
    """Whether a known class equals or inherits from ``target``."""
    ancestors = ANCESTORS.get(class_iri)
    return bool(ancestors and target in ancestors)


def is_known_sbol_iri(iri: str) -> bool:
    """Whether an IRI is a known class, property, or vocabulary value."""
    return iri in CLASS_SPECS or iri in KNOWN_PROPERTIES or iri in KNOWN_VALUE_IRIS


def property_specs_for(rdf_types: Iterable[str]) -> dict[str, PropertySpec]:
    """Allowed properties for an object with these rdf:types; subclass rows override inherited ones."""
    specs: dict[str, PropertySpec] = {}

    def collect(iri: str) -> None:
        spec = CLASS_SPECS.get(iri)
        if spec is None:
            return
        for parent in spec.parents:
            collect(parent)
        for field in spec.fields:
            specs[field.predicate] = field

    for rdf_type in sorted(rdf_types):
        collect(rdf_type)
    return specs


def local_name(class_iri: str) -> str:
    """Local name of a class IRI, after its namespace."""
    for namespace in (SBOL, PROV, OM):
        if class_iri.startswith(namespace):
            return class_iri[len(namespace) :]
    return class_iri
