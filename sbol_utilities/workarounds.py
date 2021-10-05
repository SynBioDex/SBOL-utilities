import logging
from typing import Optional

import sbol3
import tyto

#############
# Deprecated functions
from sbol_utilities.helper_functions import id_sort


def string_to_display_id(name: str) -> str:
    # TODO: remove after a couple of releases
    logging.warning('sbol_utilities.workarounds.string_to_display_id is deprecated: use sbol3.string_to_display_id')
    return sbol3.string_to_display_id(name)


# TODO: remove kludge after resolution of https://github.com/SynBioDex/tyto/issues/21
def tyto_lookup_with_caching(term: str) -> str:
    logging.warning('sbol_utilities.workarounds.tyto_lookup_with_caching is deprecated; tyto now caches')
    return tyto.SO.get_uri_by_term(term)


#########################
# This file contains workarounds for known issues in pySBOL3
# They will be removed when pySBOL3 upgrades fix the associated issues

type_to_standard_extension = {  # TODO: remove after resolution of https://github.com/SynBioDex/pySBOL3/issues/244
    sbol3.SORTED_NTRIPLES: '.nt',
    sbol3.NTRIPLES: '.nt',
    sbol3.JSONLD: '.json',
    sbol3.RDF_XML: '.xml',
    sbol3.TURTLE: '.ttl'
}


# TODO: delete after resolution of https://github.com/SynBioDex/pySBOL3/issues/231
def sort_owned_objects(self):
    """Patch to stabilize order returned in cloning, part of the pySBOL3 issue #231 workaround"""
    for k in self._owned_objects.keys():
        self._owned_objects[k] = id_sort(self._owned_objects[k])



# Kludges for copying certain types of TopLevel objects
# TODO: delete after resolution of https://github.com/SynBioDex/pySBOL3/issues/235, along with following functions
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
# TODO: delete after resolution of https://github.com/SynBioDex/pySBOL3/issues/207
def replace_feature(component, old, new):
    component.features.remove(old)
    component.features.append(new)
    # should be more thorough, but kludging to just look at constraints
    for ct in component.constraints:
        if ct.subject == old.identity: ct.subject = new.identity
        if ct.object == old.identity: ct.object = new.identity


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

