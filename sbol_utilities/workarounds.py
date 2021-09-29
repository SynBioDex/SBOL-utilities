import unicodedata
from typing import Iterable, Union, Optional

import sbol3
import tyto

#########################
# This file contains workarounds for known issues in pySBOL3
# They will be removed when pySBOL3 upgrades fix the issues

# TODO: remove after resolution of https://github.com/SynBioDex/pySBOL3/issues/191
def string_to_display_id(name: str) -> str:
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


# TODO: remove after resolution of https://github.com/SynBioDex/pySBOL3/issues/234
def get_parent(self: sbol3.Identified) -> Optional[sbol3.Identified]:
    """Find the parent of this child object

    :param self: Object to search from
    :return: parent or None if it cannot be found (e.g., this is a toplevel)
    """
    if self.identity:
        return self.document.find(self.identity.rsplit('/', 1)[0])
    else:
        return None
sbol3.Identified.get_parent = get_parent


# TODO: remove after resolution of https://github.com/SynBioDex/pySBOL3/issues/234
def get_toplevel(self: sbol3.Identified) -> Optional[sbol3.TopLevel]:
    """Find the SBOL3 TopLevel object containing this SBOL3 object

    :param self: Object to search from
    :return: Enclosing TopLevel (self if it is a TopLevel) or None if there is nothing enclosing
    """
    if isinstance(self, sbol3.TopLevel):
        return self
    else:
        parent = self.get_parent()
        if parent:
            return get_toplevel(parent)
        else:
            return None

