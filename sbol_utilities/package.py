from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from hashlib import sha256
from itertools import chain
from pathlib import Path
from typing import Union, Optional, Callable
from urllib.parse import urlparse, urljoin, unquote

import tyto
from sbol3.refobj_property import ReferencedURI
from sbol_factory import SBOLFactory
import sbol3

# Create SEP054 Python classes from definition file
from sbol_utilities.helper_functions import sbol3_namespace, same_namespace, id_sort

sep_054 = SBOLFactory('sep_054', Path(__file__).parent / 'sep_054_extension.ttl', 'http://sbols.org/SEP054#')

DEFAULT_CATALOG_NAMESPACE = "https://biopackages.org/"
"""Root namespace used for centralized package hosting"""
# TODO: in the future, may wish to consider options for multiple hosting locations

GENERATED_CONTENT_SUBDIRECTORY = '.sip'
"""Per SEP 054: When built with respect to a specific directory, generated content SHOULD be stored in a hidden 
subdirectory named .sip.

The `.sip` directory MUST contain nothing besides the `package.nt` and dissociated package files.
The directory MAY, of course, omit these files before they have been built.
The contents of each dissociated package files SHOULD contain precisely the set of dependencies indicated for that 
package in `package.nt`."""
PACKAGE_FILE_NAME = 'package.nt'
"""Per SEP_054: Each Package and its associated filed-derived sub-Package objects (but not sub-directory derived 
sub-packages), SHOULD be stored in sorted N-triples format in a file named .sip/package.nt."""
DISSOCIATED_IMPORT_TEMPLATE = '{}.nt'
"""Per SEP 054: Imports from a dissociated package X SHOULD be stored in sorted N-triples format in a file 
named .sip/X.nt"""
CONVERTED_MODULE_TEMPLATE = '{}.nt'
"""Per SEP 054: Imports from a dissociated package X SHOULD be stored in sorted N-triples format in a file 
named .sip/X.nt"""

BUILD_SUBDIRECTORY = '.build'
"""Per SEP 054: When built with respect to a specific directory, a build artifact SHOULD be stored in a hidden 
subdirectory named .build.

The `.build` directory MAY also be used to store other transient artifacts, such as intermediate outputs used in 
production of a package or cached files that are not yet converted to their final format.
"""
PACKAGE_DISTRIBUTION_TEMPLATE = '{}-distribution-package.{}'
"""Per SEP 054: For a package named X, the name of a build artifact for package distribution (i.e., without atomic 
package dependencies) SHOULD be X-distribution-package.[EXTENSION], where [EXTENSION] is an appropriate extension 
for its format."""
STANDALONE_DISTRIBUTION_TEMPLATE = '{}-standalone-package.{}'
"""Per SEP 054: For a package named X, the name of a build artifact for stand-alone distribution (i.e., with all 
dependencies included in the artifact) SHOULD be X-standalone-package.[EXTENSION], where [EXTENSION] is an 
appropriate extension for its format."""

DEFAULT_PACKAGE_CATALOG_DIRECTORY = Path.home() / GENERATED_CONTENT_SUBDIRECTORY
"""By default a package catalog will be stored in a generated subdirectory of the user's home directory."""

PACKAGE_CATALOG_NAME = 'package-catalog.nt'
"""Name of the file used to store a catalog of available packages"""

PACKAGE_HASH_NAME_LENGTH = 32
"""Length of names created from package URIs"""


class PackageError(Exception):
    """An error has occurred in the package system"""


def _embedded_packages(root: sep_054.Package, doc: sbol3.Document) -> list[sep_054.Package]:
    """Find a list of packages embedded in a possibly "fat" package document, ensuring all are referred to
    from the root (possibly recursively) as subpackages or dependencies, walking the tree in a predictable order

    :param root: Package for the document, which may refer to other packages embedded or elsewhere
    :param doc: Document to search
    :return: list of embedded Package objects, in traversal order
    :raises PackageError if there are packages not part of the expected tree
    """
    package_dict = {p.identity: p for p in doc.objects if isinstance(p, sep_054.Package)}
    try:
        pending_packages = [package_dict.pop(root.identity)]
    except KeyError:
        raise PackageError(f'Package document does not include expected root Package: {root.identity}')

    embedded_packages = list()
    while pending_packages:
        next_package = pending_packages.pop()
        embedded_packages.append(next_package)
        # Look for sub-packages and dependencies
        for p in list(id_sort(next_package.subpackages)) + id_sort(d.package for d in next_package.dependencies):
            if str(p) in package_dict:  # if it's in the IDs, then it's in the document and not yet checked
                pending_packages.append(package_dict.pop(str(p)))
    if package_dict:
        raise PackageError(f'Document embeds packages not referred to from root: {list(package_dict.keys())}')
    return embedded_packages


def validate_package_document(namespace: str, doc: sbol3.Document) -> sep_054.Package:
    """Check that an SBOL Document is a valid representation of the named package. Specifically:
    - The document must contain a Package object for the namespace
    - Every member of the Package must be in the Document
    - The Package objects for subpackages MAY be in the document; if they are, their members must be too.
    - The Package objects for dependencies MAY be in the document; if they are, their members must be too.
    - Every TopLevel object in the document MUST be part of this subpackage/dependency/member tree

    :param namespace: namespace for the package represented by the document
    :param doc: Document to be validated
    :returns: Package object for the namespace, as found in document
    :raises PackageError if validation fails
    """
    # TODO: allow raising of multiple exceptions, for better debugging
    # Make sure there is a copy of the package object in the package:
    package_object_uri = package_id(namespace)
    package = doc.find(package_object_uri)
    if not package:
        raise PackageError(f'Cannot find Package in SBOL document: {package_object_uri}')
    elif not isinstance(package, sep_054.Package):
        raise PackageError(f'Object should be a Package, but is not: {package}')
    elif not same_namespace(namespace, package.namespace):
        raise PackageError(f'Package {package.identity} should have namespace {namespace} but was {package.namespace}')

    # Make sure all package members and document contents are identical, following subpackage/dependency tree as needed
    object_ids = {o.identity: o for o in doc.objects}
    for check_package in _embedded_packages(package, doc):
        # check if any members are missing:
        missing_members = {str(m) for m in check_package.members} - object_ids.keys()
        if missing_members:
            raise PackageError(f'Package {check_package.namespace} missing listed members: {sorted(missing_members)}')
        # remove contents from less of objects to account for
        del object_ids[check_package.identity]
        for m in check_package.members:
            del object_ids[str(m)]

    # if anything was left after walking tree, it's an unexpected member error:
    if object_ids:
        raise PackageError(f'Package {namespace} contains unexpected TopLevel objects: {sorted(object_ids.keys())}')

    return package


def get_package_directory(directory: Union[Path, str]) -> Path:
    """Return path to package directory, after ensuring it exists and has no subdirectories of its own.

    :param directory: directory on which to ensure package subdirectory exists
    :returns: Path to package directory
    """
    return _ensure_leaf_subdirectory(directory, GENERATED_CONTENT_SUBDIRECTORY)


def get_build_directory(directory: Union[Path, str]) -> Path:
    """Return path to build directory, after ensuring it exists and has no subdirectories of its own.

    :param directory: directory on which to ensure build subdirectory exists
    :returns: Path to build directory
    """
    return _ensure_leaf_subdirectory(directory, BUILD_SUBDIRECTORY)


def _ensure_leaf_subdirectory(directory: Path, leaf_name: str) -> Path:
    """Ensure directory has a named subdirectory (e.g., for package or build), and has no subdirectories of its own

    :param directory: directory on which to ensure leaf subdirectory exists
    :param leaf_name: name for subdirectory
    :returns: Path to leaf directory
    """
    leaf_path = Path(directory) / leaf_name
    # Ensure that package directory exists
    leaf_path.mkdir(parents=True, exist_ok=True)
    # Ensure that the package directory has no subdirectories
    leaf_sub_dirs = [s for s in os.scandir(leaf_path) if s.is_dir()]
    if len(leaf_sub_dirs):
        raise PackageError(f'In package directory {directory}, subdirectory {leaf_name} should have no further '
                           f'subdirectories, but found {leaf_sub_dirs}')
    return leaf_path


def directory_to_package(directory: Union[Path, str]):
    # Check it is a package directory
    # Check that there is NOT a package directory
    # TODO: consider refactor based on how catalog work turns out

    # Walk the tree from the bottom up
    for root, dirs, files in os.walk(directory, topdown=False):
        # Read all SBOL files in as documents
        file_list = [f for f in files if f.endswith(".nt")]  # TODO: generalize to other formats
        path_list = [root + '/' + file for file in file_list]
        doc_list = []
        for file in path_list:
            doc = sbol3.Document()
            doc.read(file)
            doc_list.append(doc)

        # Make a list of the package objects for each of the subpackages
        # Define packages for the files saved in the directory
        sub_package_list = [doc_to_package(doc) for doc in doc_list]
        # Collect packages from subdirectories
        for sub_dir in dirs:
            path = os.path.join(root, sub_dir, GENERATED_CONTENT_SUBDIRECTORY, 'package.nt')
            doc = sbol3.Document()
            doc.read(path)
            # TODO: Check there is only one object- a package, if no throw an error
            package = doc.objects[0]
            sub_package_list.append(package)

        # Get the namespace (longest common path of all the namespaces)
        # FIXME: Does the package namespace HAVE to match the path in the dir, or is that nice but not required?
        # If there is just one sub package is the package namespace the same as the subpackage namespace?
        package_namespace = get_prefix(sub_package_list)

        # Define the package
        # It is suggested to name all packages '/package', but not required
        # The package will have no members, only subpackages
        package = sep_054.Package(package_namespace + '/package')
        package.namespace = package_namespace
        package.conversion = False
        package.subpackages = sub_package_list

        # Add the package to a document
        doc = sbol3.Document()
        doc.add(package)

        # Make the package directory
        get_package_directory(root)

        # Save the document to the package directory
        out_path = os.path.join(root, GENERATED_CONTENT_SUBDIRECTORY, 'package.nt')
        doc.write(out_path, sbol3.SORTED_NTRIPLES)


def docs_to_package(root_package_doc: sbol3.Document, sub_package_docs: list[sbol3.Document]) -> sep_054.Package:
    """ Take files for a root packages and 0 or more sub-packages. For each
    file, a package object will be generated, then the sub-packages will be
    added to the root package.

    Args:
        root_package_doc: First document, for the package
        sub_package_docs: The document(s) for subpackages

    Return
        package: The root package with the added sub-packages
    """
    root_package = doc_to_package(root_package_doc)
    sub_package_list = [doc_to_package(sub_package) for sub_package in sub_package_docs]
    aggregate_subpackages(root_package, sub_package_list)
    return root_package


def aggregate_subpackages(root_package: sep_054.Package, sub_package_list: list[sep_054.Package]):
    """ Modifies a root package by adding the sub-packages to its definition
    (after checking that their namespaces are compatible with being sub-packages of the root)
    Args:
        root_package: Package to add to
        sub_package_list: sub-packages to add to root
    """
    # The root package should have conversion=false and dissociated not set
    # TODO: check if this is true, rather than assuming it should be made true
    root_package.conversion = False

    # For each of the sub-packages, check if it's namespace contains the root
    # package namespace and add it to the root package
    for package in sub_package_list:
        if check_prefix(root_package, package):
            root_package.subpackages.append(package)
        else:
            raise ValueError(f'Package object {package} is not a well-defined '
                             f'subpackage of the root package {root_package}. The '
                             f'sub-package namespace is {package.namespace}, which '
                             f'does not share a prefix with the root package '
                             f'namespace {root_package.namespace}.')


def doc_to_package(doc: sbol3.Document, validate: bool = True) -> sep_054.Package:
    """Transform an SBOL document into a package with no subpackages, adding Package to document
    Requires that all TopLevel objects in the Document share the same namespace

    :param doc: SBOL document from which package should be generated
    :param validate: if true, validate the document
    :returns: Package object
    """
    # Collect TopLevel object namespaces: if all are the same, that is the package namespace
    candidate_namespaces = set(o.namespace for o in doc.objects)
    if len(candidate_namespaces) == 0:
        raise ValueError(f'Document {doc} must contain at least one SBOL TopLevel objects to be a package')
    elif len(candidate_namespaces) == 1:
        package_namespace = candidate_namespaces.pop()
    else:
        raise ValueError(f'Document {doc} does not form a well-defined package, as objects different namespaces.'
                         f'The namespaces found are {candidate_namespaces}.')

    # Create and return the Package object
    with sbol3_namespace(package_namespace):
        package = sep_054.Package('package', members=doc.objects, conversion=False)
        doc.add(package)
        if validate:
            validate_package_document(package_namespace, doc)
        return package


def check_prefix(root_package: sep_054.Package, sub_package: sep_054.Package):
    """ Check that the namespace of the sub-package is a path extension of the
    namespace of the root package
    
    Args:
        root_package (sep_054:Package): Root package object
        sub_package (sep_054:Package) Package object of the sub-package to check
    
    Returns:
        is_sub (boolean): True if the namespace of the sub-package is a valid
            namespace extension of the root package
    """
    # Get the namespaces
    root_namespace = root_package.namespace
    sub_namespace = sub_package.namespace

    # Parse the namespaces as URIs
    root_uri = urlparse(root_namespace)
    sub_uri = urlparse(sub_namespace)

    # Check scheme and netloc are the same
    schemes = set(url.scheme for url in [root_uri, sub_uri])
    netlocs = set(url.netloc for url in [root_uri, sub_uri])

    if len(schemes) == 1 & len(netlocs) == 1:
        pass
    else:
        raise ValueError(f'The packages {root_package} and {sub_package} '
                         f'namespace URIs do not share the same URL scheme '
                         f'specifier or network location, and so do not '
                         f'represent a root and sub package.')

    # Break the paths down into chunks separated by "/"
    root_uri_split = root_uri.path.split('/')
    sub_uri_split = sub_uri.path.split('/')

    # Get all the paths into one list
    # Get common elements
    zipped = list(zip(*[root_uri_split, sub_uri_split]))
    common_elements = [list(set(zipped[i]))[0] for i in range(len(zipped)) if len(set(zipped[i])) == 1]

    # Check that the common elements are the same as the entire root package
    if common_elements == root_uri_split:
        is_sub = True
    else:
        raise ValueError(f'The namespace of package object {sub_package} '
                         f'({sub_uri}) does not contain the namespace of the '
                         f'root package object {root_package} ({root_uri}) as a '
                         f'prefix. So {sub_package} is not a valid sub-package '
                         f'of {root_package}')
    return is_sub


def get_prefix(package_list):
    """ Check that the namespace of the sub-package is a path extension of the
    namespace of the root package
    
    Args:
        package_list (list of sep_054.Package):
    
    Returns:
        prefix (string): 
    """
    # Get the namespaces
    namespace_list = [package.namespace for package in package_list]

    # Parse the namespaces as URIs
    uri_list = [urlparse(namespace) for namespace in namespace_list]

    # Check scheme and netloc are the same
    schemes = set(url.scheme for url in uri_list)
    netlocs = set(url.netloc for url in uri_list)

    if len(schemes) == 1 & len(netlocs) == 1:
        pass
    else:
        raise ValueError(f'The package namespace URIs {namespace_list}'
                         f'do not share the same URL scheme '
                         f'specifier or network location, and so do not '
                         f'represent a root and sub package.')

    # Break the paths down into chunks separated by "/"
    split_uris = [URI.path.split('/') for URI in uri_list]

    # Get common elements
    zipped = list(zip(*split_uris))
    common_elements = [list(set(zipped[i]))[0] for i in range(len(zipped)) if len(set(zipped[i])) == 1]

    # Rejoin the common elements to get the common path
    common_path = '/'.join(common_elements)
    prefix = schemes.pop() + '://' + netlocs.pop() + common_path
    return prefix


def ensure_package_namespace(identifier: str) -> str:
    """Takes a proposed identifier for a package and converts it to a canonical package URI
    To avoid potential confusion, package names must be lower-case with ASCII alphanumeric/dash path elements.

    :param identifier: String to be turned into a valid package identifier, if possible
    :return: valid package namespace
    :raises PackageError: if package_id cannot be turned into a valid package namespace
    """
    # make sure it's all ASCII
    if not identifier.isascii():
        raise PackageError(f'Package identifier {identifier} has characters that are not ASCII')
    # canonicalize to lower case
    if not identifier.islower():
        identifier = identifier.lower()

    parsed = urlparse(identifier)
    if parsed.params or parsed.query or parsed.fragment:
        raise PackageError(f'Package identifier {identifier} must not have URL params, query, or fragment')
    # Make sure path is only alphanumeric, dash, and slash
    if not parsed.path.replace('-', '').replace('/', '').isalnum():
        raise PackageError(f'Package path {parsed.path} has characters that are not alphanumeric or dash')
    # Make sure there isn't a trailing slash
    if parsed.path[-1] == '/':
        raise PackageError(f'Package identifier {identifier} must not end with a slash')
    # If URL scheme is missing, assume it is a path and attempt to prepend with the default catalog namespace
    if not parsed.scheme:
        identifier = urljoin(DEFAULT_CATALOG_NAMESPACE, identifier)

    # Return final validated canonical form
    return identifier


def package_id(namespace: str) -> str:
    """Get the standard identity for a Package object from the package's namespace

    :param namespace: URI for the namespace
    :return: URI for the package object
    """
    return urljoin(f'{namespace}/', 'package')


# TODO: consider moving this to an SEP 054 class
@dataclass
class LoadedPackage:
    package: sep_054.Package
    document: sbol3.Document
    source_file: Path = None
    """File the package was loaded from, if any"""


class PackageManager:

    def __init__(self, catalog_directory: Path = DEFAULT_PACKAGE_CATALOG_DIRECTORY):
        self._catalog_directory = catalog_directory
        # ensure catalog directory exists
        self._catalog_directory.mkdir(parents=True, exist_ok=True)
        # Track set of loaded packages
        self.loaded_packages: dict[str, Union[LoadedPackage, list[LoadedPackage]]] = dict()
        """Tracks the set of currently loaded packages (initially empty). It is a dictionary mapping
         from namespace to the collection of loaded information"""
        self._catalog_file = self._catalog_directory / PACKAGE_CATALOG_NAME
        # Catalog of available packages, and document it was drawn from
        package_catalog, self._package_catalog_doc = PackageManager._load_package_catalog(self._catalog_file)
        # TODO: consider how to handle existence of multiple versions of packages. Likely just 1 in catalog, but caches?
        self.package_catalog = package_catalog
        """Dictionary mapping namespace strings to Package objects, each with its file as an Attachment"""

    @staticmethod
    def _load_package_catalog(catalog_file: Path) -> tuple[dict[str, sep_054.Package], sbol3.Document]:
        doc = sbol3.Document()
        # TODO: unwrap Path->str after https://github.com/SynBioDex/pySBOL3/issues/407 published in pySBOL3 1.0.2
        try:
            doc.read(str(catalog_file))
        except FileNotFoundError:
            logging.warning('Unable to find package catalog file %s; using empty catalog', catalog_file)
        return {p.namespace: p for p in doc.objects if isinstance(p, sep_054.Package)}, doc

    def _save_package_catalog(self, catalog_file: Path = None):
        # TODO: unwrap Path->str after https://github.com/SynBioDex/pySBOL3/issues/407 published in pySBOL3 1.0.2
        self._package_catalog_doc.write(str(catalog_file or self._catalog_file), sbol3.SORTED_NTRIPLES)

    @staticmethod
    def _identity_to_filename(identity: str) -> str:
        hash_name = sha256(identity.encode()).hexdigest()[:PACKAGE_HASH_NAME_LENGTH]
        return f'{hash_name}.nt'

    def install_package(self, namespace: str, doc: sbol3.Document) -> sep_054.Package:
        """Install a package into the package catalog, either from a local document or by downloading
        from the source given in the remote catalog
        TODO: create remote catalog

        :param namespace: namespace of the package being installed
        :param doc: Document containing the package and any bundled subpackages and dependencies
        :return: Package object for package that was just installed
        :raises PackageError: if the package does not validate or a file error occurs
        """
        logging.info('Installing package %s', namespace)
        # First validate package document, making sure it will be OK for loading
        try:
            package = validate_package_document(namespace, doc)
        except PackageError as e:
            raise PackageError(f'Validation error while attempting to install package {namespace}') from e

        # Write package document to catalog directory
        file_path = self._catalog_directory / PackageManager._identity_to_filename(package.identity)
        try:
            doc.write(str(file_path), sbol3.SORTED_NTRIPLES)
        except OSError as e:
            raise PackageError(f'Could not write package {namespace} to {str(file_path)}') from e

        # Create an attachment for the newly written file
        attachment = sbol3.Attachment(f'{package.identity}_file', source=file_path.as_uri(), format=tyto.EDAM.n_triples)
        package.attachments.append(attachment)
        # Add the package and save the catalog
        self._package_catalog_doc.add([package, attachment])
        self._save_package_catalog()
        self.package_catalog[package.namespace] = package
        logging.info('Successfully installed package %s', package.identity)

    def load_package(self, namespace: str, from_path: Optional[Union[Path, str]] = None,
                     doc: Optional[sbol3.Document] = None) -> sep_054.Package:
        """Ensure that the package with the designated URI is loaded.
        By default, attempts to load from the package catalog, overridden if from_path or doc is provided.
        If the package is already loaded, it will not be reloaded.
        Note that this will also load implicitly load any embedded sub-packages and dependencies

        :param namespace: namespace for package
        :param from_path: if set and package is not loaded, load from the provided path. doc must be None.
        :param doc: if set, use doc as a source for a not-loaded package
        :return: Package object that satisfies the load request
        :raises PackageError: if the package cannot be loaded or does not validate
        """
        # If already loaded and not dissociated, return package - dissociated requires more information
        if namespace in self.loaded_packages and not isinstance(self.loaded_packages[namespace], list):
            return self.loaded_packages[namespace].package

        if from_path and doc:
            raise PackageError('load_package must not be given both a path and a Document')
        elif from_path:  # convert str to Path if needed
            from_path = Path(from_path)
        elif not doc:  # get Path from catalog
            try:
                package = self.package_catalog[namespace]
                if len(package.attachments) != 1:
                    raise PackageError(f'Catalog links package {namespace} to {len(package.attachments)} files, not 1')
                file_uri = package.attachments[0].lookup().source
                from_path = Path(unquote(urlparse(file_uri).path))
            except KeyError:
                raise PackageError(f'Cannot find package {namespace} in catalog')

        # Now check if already loaded and dissociated:
        if namespace in self.loaded_packages and isinstance(self.loaded_packages[namespace], list):
            loaded = self.loaded_packages[namespace]
            matches = [lp for lp in loaded
                       if (from_path and from_path == lp.source_file) or (doc and doc == lp.document)]
            if len(matches):
                if len(matches) > 1:  # should never happen, since it should be prevented by other checks
                    raise PackageError('Internal error: multiple matching dissociated packages for {namespace}')
                else:
                    return matches[0].package
                # otherwise, this is a new fragment of a dissociated package, and can be returned independently

        # If being obtained from a path, load document:
        if from_path:
            try:
                doc = sbol3.Document()
                doc.read(str(from_path))
            except OSError as e:
                raise PackageError(f'Could not read package {namespace} from {str(from_path)}') from e

        # Validate package and collect its root Package object
        try:
            package = validate_package_document(namespace, doc)
        except PackageError as e:
            raise PackageError(f'Validation error while loading package {namespace} from file {from_path}') from e

        # add all embedded packages (including the root package) to the loaded package collect:
        for p in _embedded_packages(package, doc):
            if p.dissociated:  # dissociated packages can have multiple fragments loaded, track as a list
                if p.namespace not in self.loaded_packages:
                    self.loaded_packages[p.namespace] = list()
                elif not isinstance(self.loaded_packages[p.namespace], list):
                    raise PackageError(f'Cannot combine dissociated and non-dissociated packages for {p.namespace}')
                # TODO: check for conflicts between loaded fragments
                # add to the list of dissociated package fragments
                self.loaded_packages[p.namespace].append(LoadedPackage(p, doc, Path(from_path)))
            else:  # non-dissociated packages can only be loaded once
                if p.namespace in self.loaded_packages:
                    raise PackageError(f'Embedded package would override already-loaded package: {p.namespace} with '
                                       f'root {namespace} from {from_path}')
                self.loaded_packages[p.namespace] = LoadedPackage(p, doc, Path(from_path))
        # return the root package:
        return package

    def find_package_docs(self, uri: Union[ReferencedURI, str]) -> Optional[list[sbol3.Document]]:
        """Find which documents to check for a given URI by searching the loaded packages for a matching prefix
        If multiple prefixes match, use the longest one

        :param uri: URI to be searched for
        :returns list of Document objects to search
        """
        last_uri = None
        uri = str(uri)
        while uri and uri != last_uri:
            if uri in self.loaded_packages:
                loaded = self.loaded_packages[uri]
                if isinstance(loaded, LoadedPackage):
                    return [loaded.document]  # wrap non-dissociated into a list
                else:
                    return [lp.document for lp in loaded]  # for dissociated, map documents from list
            last_uri = uri
            uri = uri.rsplit('/', maxsplit=1)[0]
        return None

    def lookup(self, uri: Union[ReferencedURI, str]) -> Optional[sbol3.Identified]:
        """Look up an SBOL object by querying the loaded package with the matching prefix

        :param uri: identity to look up
        :return: SBOL object, if found
        """
        # TODO: figure out how lookup will work for embedded dependencies (including dissociated packages)
        package_docs = self.find_package_docs(uri)
        if package_docs:
            for doc in package_docs:
                found = doc.find(str(uri))
                if found:
                    return found
            return None
        else:
            raise PackageError(f'No loaded package has a namespace that contains {uri}')

    def traverse_dependencies(self, package: sep_054.Package, func: Callable[[sbol3.Identified], None]):
        """Executes traverse on all the documents associated with the dependencies of a package, in order of listing

        :param package: Package whose dependencies will be traversed
        :param func: Function to be called in traverse on each document
        """
        chained = list(chain(*(self.find_package_docs(dependency.package) for dependency in package.dependencies)))
        docs = filter(None, chained)
        for doc in docs:
            doc.traverse(func)

    def find_all_in_dependencies(self, package: sep_054.Package, predicate: Callable[[sbol3.Identified], bool]) -> \
            list[sbol3.Identified]:
        """Executes "find_all" on all the documents associated with the dependencies of a package.

        :param package: Package whose dependencies will be traversed
        :param predicate: Predicate to apply to dependencies
        :return: list of objects identified by find_all
        """
        result: list[sbol3.Identified] = []

        def wrapped_filter(visited: sbol3.Identified):
            if predicate(visited):
                result.append(visited)

        self.traverse_dependencies(package, wrapped_filter)
        return result


ACTIVE_PACKAGE_MANAGER = PackageManager()
"""Package manager in use, initialized with default settings"""


def load_package(namespace: str, from_path: Optional[Union[Path, str]] = None, doc: Optional[sbol3.Document] = None) \
        -> sep_054.Package:
    """Ensure that the package with the designated URI is loaded.
    By default, attempts to load from the package catalog, overridden if from_path or doc is provided.
    If the package is already loaded, it will not be reloaded.
    Note that this will also load implicitly load any sub-packages that are embedded with the package
    TODO: load dependencies from package

    :param namespace: namespace for package
    :param from_path: if set and package is not loaded, load from the provided path. doc must be None.
    :param doc: if set, use doc as a source for a not-loaded package
    :return: Package object that satisfies the load request
    :raises PackageError: if the package cannot be loaded or does not validate
    """
    return ACTIVE_PACKAGE_MANAGER.load_package(namespace, from_path, doc)


def install_package(package: sep_054.Package, doc: sbol3.Document):
    ACTIVE_PACKAGE_MANAGER.install_package(package, doc)


def lookup(uri: Union[ReferencedURI, str]):
    return ACTIVE_PACKAGE_MANAGER.lookup(uri)


#################
# Replace ReferencedURI lookup function and Document find functions with package-aware lookup:
original_referenced_uri_lookup = sbol3.refobj_property.ReferencedURI.lookup


def package_aware_lookup(self: ReferencedURI) -> Optional[sbol3.Identified]:
    """Package-aware lookup works by first trying lookup in the local sbol3.Document, then checking if the references
    lead elsewhere."""
    # TODO: consider the handling of materials in the current document that should be in a different package
    return original_referenced_uri_lookup(self) or \
        ACTIVE_PACKAGE_MANAGER.lookup(self)


# Monkey-patch package-aware lookup function over base lookup function
sbol3.refobj_property.ReferencedURI.lookup = package_aware_lookup


def traverse_dependencies(package: sep_054.Package, func: Callable[[sbol3.Identified], None]):
    """Executes traverse on all the documents associated with the dependencies of a package, in order of listing

    :param package: Package whose dependencies will be traversed
    :param func: Function to be called in traverse on each document
    """
    return ACTIVE_PACKAGE_MANAGER.traverse_dependencies(package, func)


def find_all_in_dependencies(package: sep_054.Package, predicate: Callable[[sbol3.Identified], bool]) \
        -> list[sbol3.Identified]:
    """Executes "find_all" on all the documents associated with the dependencies of a package.

    :param package: Package whose dependencies will be traversed
    :param predicate: Predicate to apply to dependencies
    :return: list of objects identified by find_all
    """
    return ACTIVE_PACKAGE_MANAGER.find_all_in_dependencies(package, predicate)
