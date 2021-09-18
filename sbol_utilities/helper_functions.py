import unicodedata
from typing import Iterable, Union, Optional

import sbol3
import tyto

#########################
# Collection of shared helper functions for utilities package


def flatten(collection: Iterable[list]) -> list:
    """Flatten list of lists into a single list

    :param collection: list of lists
    :return: flattened list
    """
    return [item for sublist in collection for item in sublist]


def toplevel_named(doc: sbol3.Document, name: str) -> Optional[sbol3.Identified]:
    """Find the unique TopLevel document object with the given name (rather than displayID or URI)

    :param doc: SBOL document to search
    :param name: name to look for
    :return: object, if found, or None if not
    :raises ValueError: if there are multiple objects with the given name
    """
    found = [o for o in doc.objects if o.name == name]
    if len(found) == 0:
        return None
    elif len(found) == 1:
        return found[0]
    else:
        raise ValueError(f'Name is not unique: {name}')


def unambiguous_dna_sequence(sequence: str) -> bool:
    """Check if a sequence consists only of unambiguous DNA characters

    :param sequence: string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    return sequence.lower().strip('acgt') == ''


def unambiguous_rna_sequence(sequence: str) -> bool:
    """Check if a sequence consists only of unambiguous RNA characters

    :param sequence: string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    return sequence.lower().strip('acgu') == ''


def unambiguous_protein_sequence(sequence: str) -> bool:
    """Check if a sequence consists only of unambiguous protein characters

    :param sequence: string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    return sequence.lower().strip('acdefghiklmnpqrstvwy') == ''


def strip_sbol2_version(identity: str) -> str:
    """Ensure that an SBOL2 or SBOL3 URI is an SBOL3 URI by stripping any SBOL2 version identifier from the end

    :param identity: URI to be sanitized
    :return: URI without terminal version, if any
    """
    last_segment = identity.split('/')[-1]
    try:
        sbol2_version = int(last_segment)  # if last segment is a number...
        return identity.rsplit('/', 1)[0]  # ... then return everything else
    except ValueError:  # if last segment was not a number, there is no version to strip
        return identity


# TODO: replace with EDAM format entries when SBOL2 and SBOL3 can be differentiated
GENETIC_DESIGN_FILE_TYPES = {
    'FASTA': {'.fasta', '.fa'},
    'GenBank': {'.genbank', '.gb'},
    'SBOL2': {'.xml'},
    'SBOL3': {sbol3.NTRIPLES: {'.nt'},
              sbol3.RDF_XML: {'.rdf'},
              sbol3.TURTLE: {'.ttl'},
              sbol3.JSONLD: {'.json', '.jsonld'}
              }
}


def design_file_type(name: str) -> Optional[str]:
    """Guess a genetic design file's type from its name

    :param name: file name (path allowed)
    :return: type name (from GENETIC_DESIGN_FILE_TYPES) if known, None if not
    """
    for t, v in GENETIC_DESIGN_FILE_TYPES.items():
        if isinstance(v, set):
            if any(x for x in v if name.endswith(x)):
                return t
        else:  # dictionary
            if any(sub for sub in v.values() if any(x for x in sub if name.endswith(x))):
                return t
    return None


def strip_filetype_suffix(identity: str) -> str:
    """Prettify a URL by stripping standard genetic design file type suffixes off of it

    :param identity: URL to sanitize
    :return: sanitized URL
    """
    extensions = flatten((flatten(v.values()) if isinstance(v, dict) else v) for v in GENETIC_DESIGN_FILE_TYPES.values())
    for x in extensions:
        if identity.endswith(x):
            return identity.removesuffix(x)
    return identity


# TODO: remove after resolution of https://github.com/SynBioDex/pySBOL3/issues/191
def string_to_display_id(name):
    def sanitize_character(c):
        replacements = {' ': '_', '-': '_', '.': '_'}
        c = replacements.get(c, c)  # first, see if there is a wired replacement
        if c.isalnum() or c == '_':  # keep allowed characters
            return c
        else:  # all others are changed into a reduced & compatible form of their unicode name
            return f'_{unicodedata.name(c).replace(" SIGN","").replace(" ","_")}'

    # make replacements in order to get a compliant displayID
    display_id = "".join([sanitize_character(c) for c in name.strip()])
    # prepend underscore if there is an initial digit
    if display_id[0].isdigit():
        display_id = "_"+display_id
    return display_id


def url_to_identity(url: str) -> str:
    """Sanitize a URL string for use as an identity, turning everything after the last "/" to sanitize as a displayId

    :param url: URL to sanitize
    :return: equivalent identity
    """
    split = url.rsplit('/',maxsplit=1)
    return f'{split[0]}/{string_to_display_id(split[1])}'


def is_plasmid(obj: Union[sbol3.Component, sbol3.Feature]) -> bool:
    """Check if an SBOL Component or Feature is a plasmid-like structure, i.e., either circular or having a plasmid role

    :param obj: design to be checked
    :return: true if plasmid
    """
    def has_plasmid_role(x):
        # TODO: replace speed-kludge with this proper query after resolution of https://github.com/SynBioDex/tyto/issues/32
        #return any(r for r in x.roles if tyto.SO.plasmid.is_ancestor_of(r) or tyto.SO.vector_replicon.is_ancestor_of(r))
        # speed-kludge alternative:
        plasmid_roles = {tyto.SO.plasmid, tyto.SO.vector_replicon, tyto.SO.plasmid_vector}
        for r in x.roles:
            try:
                regularized = tyto.SO.get_uri_by_term(tyto.SO.get_term_by_uri(r))
                if regularized in plasmid_roles:
                    return True
            except LookupError:
                pass
        return False

    if has_plasmid_role(obj):  # both components and features have roles that can indicate a plasmid type
        return True
    elif isinstance(obj, sbol3.Component) or isinstance(obj, sbol3.LocalSubComponent) or \
            isinstance(obj, sbol3.ExternallyDefined): # if there's a type, check for circularity
        return sbol3.SO_CIRCULAR in obj.types
    elif isinstance(obj, sbol3.SubComponent): # if it's a subcomponent, check its definition
        return is_plasmid(obj.instance_of.lookup())
    else:
        return False


#########################
# Kludge/workaround materials that should be removed after certain issues are resolved

type_to_standard_extension = {  # TODO: remove after resolution of pySBOL3/issues/244
    sbol3.SORTED_NTRIPLES: '.nt',
    sbol3.NTRIPLES: '.nt',
    sbol3.JSONLD: '.json',
    sbol3.RDF_XML: '.xml',
    sbol3.TURTLE: '.ttl'
}

# Workaround for pySBOL3 issue #231: should be applied to every iteration on a collection of SBOL objects
# TODO: delete after resolution of pySBOL3 issue #231
def id_sort(i: iter):
    sortable = list(i)
    sortable.sort(key=lambda x: x.identity if isinstance(x, sbol3.Identified) else x)
    return sortable

# Patch to stabilize order returned in cloning, part of the pySBOL3 issue #231 workaround
# TODO: delete after resolution of pySBOL3 issue #231
def sort_owned_objects(self):
    for k in self._owned_objects.keys():
        self._owned_objects[k] = id_sort(self._owned_objects[k])



# Kludges for copying certain types of TopLevel objects
# TODO: delete after resolution of pySBOL issue #235, along with following functions
def copy_toplevel_and_dependencies(target, t):
    if not target.find(t.identity):
        if isinstance(t, sbol3.Collection):
            copy_collection_and_dependencies(target, t)
        elif isinstance(t, sbol3.Component):
            copy_component_and_dependencies(target, t)
        elif isinstance(t, sbol3.Sequence):
            t.copy(target) # no dependencies for Sequence
        else:
            raise ValueError("Not set up to copy dependencies of "+str(t))

def copy_collection_and_dependencies(target, c):
    c.copy(target)
    for m in id_sort(c.members):
        copy_toplevel_and_dependencies(target, m.lookup())

def copy_component_and_dependencies(target, c):
    c.copy(target)
    for f in id_sort(c.features):
        if isinstance(f,sbol3.SubComponent):
            copy_toplevel_and_dependencies(target, f.instance_of.lookup())
    for s in id_sort(c.sequences):
        copy_toplevel_and_dependencies(target, s.lookup())



## Kludge for replacing a feature in a Component
# TODO: delete after resolution of pySBOL issue #207
def replace_feature(component, old, new):
    component.features.remove(old)
    component.features.append(new)
    # should be more thorough, but kludging to just look at constraints
    for ct in component.constraints:
        if ct.subject == old.identity: ct.subject = new.identity
        if ct.object == old.identity: ct.object = new.identity


# TODO: remove kludge after resolution of https://github.com/SynBioDex/tyto/issues/21
tyto_cache = {}
def tyto_lookup_with_caching(term: str) -> str:
    if term not in tyto_cache:
        try:
            tyto_cache[term] = tyto.SO.get_uri_by_term(term)
        except LookupError as e:
            tyto_cache[term] = e
    if isinstance(tyto_cache[term], LookupError):
        raise tyto_cache[term]
    else:
        return tyto_cache[term]
