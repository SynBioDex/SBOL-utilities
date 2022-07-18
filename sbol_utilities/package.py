from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse

from sbol3.refobj_property import ReferencedURI
from sbol_factory import SBOLFactory
import sbol3

# Create SEP054 Python classes from definition file
from sbol_utilities.helper_functions import sbol3_namespace

sep_054 = SBOLFactory('sep_054', Path(__file__).parent / 'sep_054_extension.ttl', 'http://sbols.org/SEP054#')

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
        raise ValueError(f'Package {directory}: {leaf_name} subdirectory should have no subdirectories, but found '
                         f'{leaf_sub_dirs}')
    return leaf_path


def directory_to_package(directory: Union[Path, str]):
    # Check it is a package directory
    # Check that there is NOT a package directory
    # TODO:

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


def doc_to_package(doc: sbol3.Document) -> sep_054.Package:
    """Generate a package from the contents of a single SBOL document (ignoring  subpackages)

    :param doc: SBOL document from which package should be generated
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
        return sep_054.Package('package', members=doc.objects)


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
        self.loaded_packages: dict[str, LoadedPackage] = dict()
        """Tracks the set of currently loaded packages (initially empty). It is a dictionary mapping
         from namespace to the collection of loaded information"""
        self._catalog_file = self._catalog_directory / PACKAGE_CATALOG_NAME
        # Catalog of available packages, and document it was drawn from
        self.package_catalog, self._package_catalog_doc = PackageManager._load_package_catalog(self._catalog_file)

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

    def install_package(self, package: sep_054.Package, doc: sbol3.Document):
        # TODO: validate package against document before installation
        logging.info('Installing package %s', package.identity)
        # Write package document to collection
        file_path = self._catalog_directory / PackageManager._identity_to_filename(package.identity)
        doc.write(str(file_path), sbol3.SORTED_NTRIPLES)
        # Create an attachment for the newly written file
        # TODO: fill out the rest of the attachment fields correctly
        attachment = sbol3.Attachment(f'{package.identity}_file', source=file_path.as_uri())
        package.attachments.append(attachment)
        # Add the package and save the catalog
        self._package_catalog_doc.add([package, attachment])
        self._save_package_catalog()
        logging.info('Successfully installed package %s', package.identity)

    def load_package(self, uri, from_path):
        doc = sbol3.Document()
        # TODO: switch to trying to get the path from the catalog, converting file URI to path per the following:
        # from urllib.parse import unquote, urlparse
        # from_path = unquote(urlparse(uri).path)
        doc.read(str(from_path))
        # TODO: get the package too
        self.loaded_packages[uri] = LoadedPackage(None, doc)

    def find_package_doc(self, uri: ReferencedURI) -> Optional[sbol3.Document]:
        last_uri = None
        uri = str(uri)
        while uri and uri != last_uri:
            if uri in self.loaded_packages:
                return self.loaded_packages[uri].document
            last_uri = uri
            uri = uri.rsplit('/', maxsplit=1)[0]
        return None

    def lookup(self, uri: ReferencedURI):
        # TODO: figure out how lookup will work for dissociated packages
        package_doc = self.find_package_doc(uri)
        if package_doc:
            return package_doc.find(str(uri))
        else:
            return None


ACTIVE_PACKAGE_MANAGER = PackageManager()
"""Package manager in use, initialized with default settings"""


def load_package(uri, from_path):
    ACTIVE_PACKAGE_MANAGER.load_package(uri, from_path)


def install_package(package: sep_054.Package, doc: sbol3.Document):
    ACTIVE_PACKAGE_MANAGER.install_package(package, doc)


#################
# Replace ReferencedURI lookup function with package-aware lookup:
original_referenced_uri_lookup = sbol3.refobj_property.ReferencedURI.lookup


def package_aware_lookup(self: ReferencedURI) -> Optional[sbol3.Identified]:
    """Package-aware lookup works by first trying lookup in the local sbol3.Document, then checking if the references
    lead elsewhere."""
    # TODO: consider the handling of materials in the current document that should be in a different package
    return original_referenced_uri_lookup(self) or \
        ACTIVE_PACKAGE_MANAGER.lookup(self)


# Monkey-patch package-aware lookup function over base lookup function
sbol3.refobj_property.ReferencedURI.lookup = package_aware_lookup
