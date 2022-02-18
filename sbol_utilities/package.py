import os
from pathlib import Path
import argparse
import logging
from attr import define
from urllib.parse import urlparse

from sbol_factory import SBOLFactory
import sbol3

from sbol_utilities.workarounds import type_to_standard_extension

# this makes a sub-package that will be used until these migrate into the SBOL3 namespace
sep_054 = SBOLFactory('sep_054',
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sep_054_extension.ttl'),
            'http://sbols.org/SEP054#')

PACKAGE_DIRECTORY = '.sip'
"""Per SEP 054: When built with respect to a specific directory, generated content SHOULD be stored in a hidden 
subdirectory named .sip.

The `.sip` directory MUST contain nothing besides the `package.nt` and dissociated package files.
The directory MAY, of course, omit these files before they have been build.
The contents of each dissociated package files SHOULD contain precisely the set of dependencies indicated for that package in `package.nt`."""
PACKAGE_FILE_NAME = 'package.nt'
"""Per SEP_054: Each Package and its associated Module objects (but not sub-packages), SHOULD be stored in sorted 
N-triples format in a file named .sip/package.nt"""
DISSOCIATED_IMPORT_TEMPLATE = '{}.nt'
"""Per SEP 054: Imports from a dissociated package X SHOULD be stored in sorted N-triples format in a file 
named .sip/X.nt"""
CONVERTED_MODULE_TEMPLATE = '{}.nt'
"""Per SEP 054: Imports from a dissociated package X SHOULD be stored in sorted N-triples format in a file 
named .sip/X.nt"""

BUILD_DIRECTORY = '.build'
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


def is_package_directory(dir: str):
    """Check if a directory is a package directory, by checking if it contains any SBOL3 file in itself or a package
    file in its .sip subdirectory"""


def regularize_package_directory(dir: str):
    """Ensure directory has a package subdirectory, which has only the package and dissociated package dependencies"""
    # Ensure that package directory exists
    package_path = os.path.join(dir, PACKAGE_DIRECTORY)
    Path(package_path).mkdir(parents=True, exist_ok=True)

    # Ensure that the package directory has no subdirectories
    package_sub_dirs = [s for s in os.scandir(package_path) if s.is_dir()]
    if len(package_sub_dirs):
        raise ValueError(f'Package {dir}: {PACKAGE_DIRECTORY} subdirectory should not have any subdirectories of its '
                         f'own, but found {package_sub_dirs[0]}')

def directory_to_package(dir: str):
    pass

def docs_to_package(root_package_doc: sbol3.Document, *sub_package_docs: sbol3.Document):
    """ Take files for a root packages and 0 or more sub-packages. For each
    file, a package object will be generated, then the sub-packages will be
    added to the root package.

    Args:
        root_package_file: First document, for the package
        *sub_package_files: The document(s) for subpackages

    Return
        package: The root package with the added sub-packages
    """
    root_package = define_package(root_package_doc)
    sub_package_list = [define_package(sub_package) for sub_package in sub_package_docs]

    package = aggregate_subpackages(root_package, sub_package_list)

    return(package)


def aggregate_subpackages(root_package: sep_054.Package,
                         sub_package_list: list[sep_054.Package]):
    """ Take a package object representing a root package and one or more 
        additional sbol package objects for the subpackages. Add the subpackages
        to the package definition, if their name spaces indicate that they are
        a proper subpackage for the rootpackage. Return the package object with
        the added subpackage information.
    Args:
        root_package (sep_054.Package): First document, for the package
        *sub_packages (sep_054.Package): The document(s) for subpackages

    Return
        root_package: The root package with the added sub-packages
    """
    # The root package should have conversion=false and dissociated not set
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

    return root_package

def define_package(package_file: sbol3.Document):
    """Function to take one sbol document and define a package from it

    Args:
        package_file (sbol3.Document): SBOL document containing a package

    Return
        package: The package definition
    """
    # Check that all of the objects have the same namespace, if they do, save
    # that as the package namespace
    candidate_namespaces = set(o.namespace for o in package_file.objects)

    if len(candidate_namespaces) == 0:
        raise ValueError(f'Document {package_file} does not contain any top-'
                         f'level objects, and so does not represent a package.')
    elif len(candidate_namespaces) == 1:
        package_namespace = ''.join(candidate_namespaces)
    else:
        raise ValueError(f'Document {package_file} does not represent a well-'
                         f'defined package. Not all members in the file have '
                         f'the same namespace. The namespaces found are '
                         f'{candidate_namespaces}.')

    # Get list of all top level objects in the package
    all_identities = [o.identity for o in package_file.objects]

    # Define the package
    # It is suggested to name all packages '/package', but not required
    package = sep_054.Package(package_namespace + '/package')
    package.members = all_identities
    package.namespace = package_namespace
    # TODO: Call a separate function to get the dependencies

    return package


def check_prefix(root_package, sub_package):
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
    root_URI = urlparse(root_namespace)
    sub_URI = urlparse(sub_namespace)

    # Check scheme and netloc are the same
    schemes = set(url.scheme for url in [root_URI, sub_URI])
    netlocs = set(url.netloc for url in [root_URI, sub_URI])

    if len(schemes) == 1 & len(netlocs) == 1:
        pass
    else:
        raise ValueError(f'The packages {root_package} and {sub_package} '
                         f'namespace URIs do not share the same URL scheme '
                         f'specifier or network location, and so do not '
                         f'represent a root and sub package.')

    # Break the paths down into chunks separated by "/"
    root_URI_split = root_URI.path.split('/')
    sub_URI_split = sub_URI.path.split('/')

    # Get all of the paths into one list
    all = [root_URI_split, sub_URI_split]

    # Get common elements
    zipped = list(zip(*all))
    common_elements = [list(set(zipped[i]))[0] for i in range(len(zipped)) if len(set(zipped[i])) == 1]

    # Check that the common elements are the same as the entire root package
    if common_elements == root_URI_split:
        is_sub = True
    else:
        raise ValueError(f'The namespace of package object {sub_package} '
                         f'({sub_URI}) does not contain the namesace of the '
                         f'root package object {root_packag} ({root_URI}) as a '
                         f'prefix. So {sub_package} is not a valid sub-package '
                         f'of {root_package}')

    return(is_sub)



def get_package_obj(sub_package_list, URI):
    """ Find a package within a list with a given namespace

    Args:
        sub_package_list (list of sep054.Package): List of package objects to 
            search
        URI (string): URI of package object of interest

    Returns:
        package (sep054.Package): Package object with the correct namespace
    """
    all_namespaces = [package.namespace for package in sub_package_list]

    target_namespace = "/".join(URI.split('/')[0:-1])

    package_index = all_namespaces.index(target_namespace)

    package = sub_package_list[package_index]

    return package

