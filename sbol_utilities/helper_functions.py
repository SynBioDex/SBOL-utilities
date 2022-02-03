import logging
import itertools
from typing import Iterable, Union, Optional

import sbol3
import tyto

#########################
# Collection of miscellaneous helper functions for utilities package
# These should be considered experimental and may be removed at any time


def flatten(collection: Iterable[list]) -> list:
    """Deprecated: switch to using itertools.chain(*collection)"""
    logging.warning('Deprecated: switch to using itertools.chain(*collection)')
    return list(itertools.chain(*collection))


def id_sort(i: iter):
    """Sort a collection of SBOL objects and/or URIs by identity URI"""
    return sorted(i, key=lambda x: x.identity if isinstance(x, sbol3.Identified) else x)


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


def strip_sbol2_version(identity: str) -> str:
    """Ensure that an SBOL2 or SBOL3 URI is an SBOL3 URI by stripping any SBOL2 version identifier from the end

    :param identity: URI to be sanitized
    :return: URI without terminal version, if any
    """
    last_segment = identity.split('/')[-1]
    try:
        _ = int(last_segment)  # if last segment is a number...
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
    extensions = itertools.chain(*((itertools.chain(*v.values()) if isinstance(v, dict) else v)
                                   for v in GENETIC_DESIGN_FILE_TYPES.values()))
    for x in extensions:
        if identity.endswith(x):
            return identity[:-(len(x))]  # TODO: change to removesuffix when python 3.9 is the minimum version
    return identity


def url_to_identity(url: str) -> str:
    """Sanitize a URL string for use as an identity, turning everything after the last "/" to sanitize as a displayId

    :param url: URL to sanitize
    :return: equivalent identity
    """
    split = url.rsplit('/', maxsplit=1)
    return f'{split[0]}/{sbol3.string_to_display_id(split[1])}'


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
            isinstance(obj, sbol3.ExternallyDefined):  # if there's a type, check for circularity
        return sbol3.SO_CIRCULAR in obj.types
    elif isinstance(obj, sbol3.SubComponent):  # if it's a subcomponent, check its definition
        return is_plasmid(obj.instance_of.lookup())
    else:
        return False
