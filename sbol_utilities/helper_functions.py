    from __future__ import annotations
    import logging
    import itertools
    from collections.abc import Generator
    from contextlib import contextmanager
    from typing import Iterable, Union, Optional, Callable

    import sbol3
    from rdflib import URIRef
    from sbol3.refobj_property import ReferencedURI, ReferencedObjectList, ReferencedObjectSingleton
    import tyto

    #########################
    # Collection of miscellaneous helper functions for utilities package
    # These should be considered experimental and may be removed at any time


    class SBOLObjectNotFound(Exception):
        """Base Exception to be raised when an SBOL object lookup fails"""
        pass


    class TopLevelNotFound(SBOLObjectNotFound):
        """A missing TopLevel object may be resolved be retrieving the object"""
        pass


    class ChildNotFound(SBOLObjectNotFound):
        """A child object should always be in the document, so if it is missing that is an error"""
        pass


    def flatten(collection: Iterable[list]) -> list:
        """Deprecated: switch to using itertools.chain(*collection)"""
        logging.warning('Deprecated: switch to using itertools.chain(*collection)')
        return list(itertools.chain(*collection))


    def id_sort(i: iter):
        """Sort a collection of SBOL objects and/or URIs by identity URI"""
        return sorted(i, key=lambda x: x.identity if isinstance(x, sbol3.Identified) else x)


    def build_reference_cache(doc: sbol3.Document) -> dict[str, sbol3.Identified]:
        """Build a cache of identities from the given document to support
        faster lookups of referenced objects.

        :param doc: an sbol3 Document
        :returns: a cache of identities
        """
        cache = {}

        def cache_identity(obj: sbol3.Identified):
            cache[obj.identity] = obj
        doc.traverse(cache_identity)
        return cache


    @contextmanager
    def cached_references(doc: sbol3.Document) -> Generator[dict[str, sbol3.Identified]]:
        """Context manager for a document reference cache for use with
        find_child and find_top_level.

        ```python
        with cached_references(doc) as cache:
            find_top_level(component1.sequences[0], cache)
        ```

        Can also be used implicitly, without passing the cache as an argument:
        ```python
        with cached_references(doc):
            find_top_level(component1.sequences[0])
        ```

        :param doc: an sbol3 Document
        :returns: a generator of a reference cache
        """
        # An existing cache is tucked away so that it can be restored when
        # this context is exited.
        try:
            old_cache = doc._sbol_utilities_reference_cache
        except AttributeError:
            # AttributeError means the document does not already have a
            # reference cache. Tuck away None as the preceding cache.
            old_cache = None
        doc._sbol_utilities_reference_cache = build_reference_cache(doc)
        yield doc._sbol_utilities_reference_cache
        # Restore the cache to what it was before
        doc._sbol_utilities_reference_cache = old_cache


    def find_child(ref: ReferencedURI, cache: Optional[dict[str, sbol3.Identified]] = None):
        """Look up a child object; if it is not found, raise an exception

        :param ref: reference to look up
        :param cache: optional cache of identities to speed lookup
        :returns: object pointed to by reference
        :raises ChildNotFound: if object cannot be retrieved
        """
        if cache is None:
            try:
                doc = ref.parent.document
                cache = doc._sbol_utilities_reference_cache
            except AttributeError:
                # AttributeError means that either the `ref` does not have
                # a parent or the document does not have the cache
                # attribute. In either case, proceed without a cache
                pass
        try:
            return cache[str(ref)]
        except KeyError:
            # KeyError means the item was not found in the cache. Ignore
            # the error and fall through to a lookup below.
            pass
        except TypeError:
            # TypeError probably means the cache object is not subscriptable.
            # Ignore the error and fall through to a lookup below.
            pass
        child = ref.lookup()
        if not child:
            raise ChildNotFound(f'Could not find child object in document: {ref}')
        elif isinstance(child, sbol3.TopLevel):
            raise ValueError(f'Referenced object is not a child object: {ref}')
        return child


    def find_top_level(ref: ReferencedURI, cache: Optional[dict[str, sbol3.Identified]] = None):
        """Look up a top-level object; if it is not found, raise an exception

        :param ref: reference to look up
        :param cache: optional cache of identities to speed lookup
        :returns: object pointed to by reference
        :raises TopLevelNotFound: if object cannot be retrieved
        """
        if cache is None:
            try:
                doc = ref.parent.document
                cache = doc._sbol_utilities_reference_cache
            except AttributeError:
                # AttributeError means that either the `ref` does not have
                # a parent or the document does not have the cache
                # attribute. In either case, proceed without a cache
                pass
        try:
            return cache[str(ref)]
        except KeyError:
            # KeyError means the item was not found in the cache. Ignore
            # the error and fall through to a lookup below.
            pass
        except TypeError:
            # TypeError probably means the cache object is not subscriptable.
            # Ignore the error and fall through to a lookup below.
            pass
        top_level = ref.lookup()
        if not top_level:
            raise TopLevelNotFound(f'Could not find top-level object in document: {ref}')
        elif not isinstance(top_level, sbol3.TopLevel):
            raise ValueError(f'Referenced object is not a TopLevel: {ref}')
        return top_level


    def toplevel_named(doc: sbol3.Document, name: str) -> Optional[sbol3.TopLevel]:
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


    def filter_top_level(doc: sbol3.Document, filter: Callable[[sbol3.TopLevel], bool]) -> Iterable[sbol3.TopLevel]:
        """Filters and returns iterable of TopLevel Objects in a document,
        which match a criteria set by a callable argument.

        :param doc: SBOL Document to search
        :param filter: Callable acting as filter on List of TopLevel objects
        :return: TopLevel iterator satisfying given filter
        """
        return (obj for obj in doc.objects if filter(obj))


    def strip_sbol2_version(identity: str) -> str:
        """Ensure that an SBOL2 or SBOL3 URI is an SBOL3 URI by stripping any SBOL2 version identifier
        from the end to the URI

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


    def is_backbone(obj: Union[sbol3.Component, sbol3.Feature]) -> bool:
        """
        Check if an SBOL Component or Feature represents a backbone structure.
        This function determines if an object is considered a backbone based on
        specific criteria, such as roles or types that are indicative of backbone components.

        :param obj: The SBOL Component or Feature to be checked.
        :return: True if the object is identified as a backbone, False otherwise.
        """
        # Define criteria for identifying a backbone.
        backbone_roles = {tyto.SO.vector_replicon, tyto.SO.engineered_region}
        backbone_types = {sbol3.SO_CIRCULAR} 

        # Check if the object has any of the roles associated with backbones
        if any(role in obj.roles for role in backbone_roles):
            return True

        # Check if the object has any of the types associated with backbones
        if isinstance(obj, (sbol3.Component, sbol3.LocalSubComponent, sbol3.ExternallyDefined)):
            if any(ty in obj.types for ty in backbone_types):
                return True

        return False

    def is_plasmid(obj: Union[sbol3.Component, sbol3.Feature]) -> bool:
        """
        Check if an SBOL Component or Feature is a plasmid-like structure.
        This function determines if an object is considered a plasmid based on
        specific criteria, such as roles or types that are indicative of plasmid components.

        :param obj: The SBOL Component or Feature to be checked.
        :return: True if the object is identified as a plasmid, False otherwise.
        """
        # Define criteria for identifying a plasmid. This might include specific roles or types.
        plasmid_roles = {tyto.SO.plasmid, tyto.SO.circDNA}  # Example roles, adjust as necessary based on SEP 055
        plasmid_types = {sbol3.SO_CIRCULAR}  # Example type, can be adjusted

        # Check if the object has any of the roles associated with plasmids
        if any(role in obj.roles for role in plasmid_roles):
            return True

        # Check if the object has any of the types associated with plasmids
        if isinstance(obj, (sbol3.Component, sbol3.LocalSubComponent, sbol3.ExternallyDefined)):
            if any(ty in obj.types for ty in plasmid_types):
                return True

        # Additional logic could be implemented here based on further criteria from SEP 055

        return False

    class SBOL3PassiveVisitor:
        """This base class provides a do-nothing method for every SBOL3 visit type.
        This allows subclasses to override for only the parts they want to act on"""

        def visit_activity(self, _): pass
        def visit_agent(self, _): pass
        def visit_association(self, _): pass
        def visit_attachment(self, _): pass
        def visit_binary_prefix(self, _): pass
        def visit_collection(self, _): pass
        def visit_combinatorial_derivation(self, _): pass
        def visit_component(self, _): pass
        def visit_component_reference(self, _): pass
        def visit_constraint(self, _): pass
        def visit_cut(self, _): pass
        def visit_document(self): pass
        def visit_entire_sequence(self, _): pass
        def visit_experiment(self, _): pass
        def visit_experimental_data(self, _): pass
        def visit_externally_defined(self, _): pass
        def visit_implementation(self, _): pass
        def visit_interaction(self, _): pass
        def visit_interface(self, _): pass
        def visit_local_sub_component(self, _): pass
        def visit_measure(self, _): pass
        def visit_model(self, _): pass
        def visit_participation(self, _): pass
        def visit_plan(self, _): pass
        def visit_prefixed_unit(self, _): pass
        def visit_range(self, _): pass
        def visit_si_prefix(self, _): pass
        def visit_sequence(self, _): pass
        def visit_sequence_feature(self, _): pass
        def visit_singular_unit(self, _): pass
        def visit_sub_component(self, _): pass
        def visit_unit_division(self, _): pass
        def visit_unit_exponentiation(self, _): pass
        def visit_unit_multiplication(self, _): pass
        def visit_usage(self, _): pass
        def visit_variable_feature(self, _): pass


    def outgoing_links(doc: sbol3.Document) -> set[URIRef]:
        """Given a document, determine the set of links to objects not in the document

        :param doc: an SBOL document
        :return: set of URIs for objects not contained in the document
        """
        # build a cache and look for all references that cannot be resolved
        def collector(obj: sbol3.Identified):
            # Collect all ReferencedURI values in properties:
            references = []
            for pv in obj.__dict__.values():
                if isinstance(pv, ReferencedObjectList):
                    references.extend([v for v in pv if isinstance(v, ReferencedURI)])
                elif isinstance(pv, ReferencedObjectSingleton):
                    references.append(pv.get())

            # Check whether or not the references resolve
            for r in references:
                try:
                    _ = find_top_level(r)
                except TopLevelNotFound:
                    outgoing.add(str(r))
                except ValueError:
                    pass  # ignore references to child objects

        outgoing = set()
        with cached_references(doc):
            doc.traverse(collector)
        return outgoing

    def is_circular(obj: Union[sbol3.Component, sbol3.LocalSubComponent, sbol3.ExternallyDefined]) -> bool:
        """Check if an SBOL Component or Feature is circular.
        :param obj: design to be checked
        :return: true if circular
        """    
        return any(n==sbol3.SO_CIRCULAR for n in obj.types)
