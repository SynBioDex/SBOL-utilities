import os
from pathlib import Path
import argparse
import logging
from attr import define

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

def aggregate_subpackages(root_package_file: sbol3.Document,
                         *sub_package_files: sbol3.Document):
    """Function to take one or more sbol documents, check if they are a package,
     and create a new sbol document with the package definition included

    Args:
        root_package_file (sbol3.Document): First document, for the package
        *subpackage_files (sbol3.Document): The document(s) for subpackages

    Return
        package: The package definition
    """
    # Define  the root package
    # It should have conversion=false and dissociated not set
    package = define_package(root_package_file)
    package.conversion = False

    # Make lists to hold package objects and dependencies for each subpackage
    sub_package_list = []
    sub_package_dependencies = []

    # Convert each sub-package file into a Package object and add it to the list
    for doc in sub_package_files:
        sub_package_list.append(define_package(doc))
        # TODO: Get the dependencies for each subpackage

    # Add the sub-package information to the package defintion
    package.subpackages = sub_package_list
    package.dependencies = sub_package_dependencies

    # Check that all the packages are valid
    check_namespaces(package, sub_package_list)

    # If the package is valid, return it
    return package, sub_package_list

def define_package(package_file: sbol3.Document):
    """Function to take one sbol document and define a package from it

    Args:
        package_file (sbol3.Document): SBOL document containing a package

    Return
        package: The package definition
    """
    # Get the namespace for the first object, if the file is a package, all 
    # namespaces should be the same, so which one you pick does not matter
    package_namespace = package_file.objects[0].namespace

    # Get list of all top level objects in the package
    all_identities = [o.identity for o in package_file.objects]

    # Define the package
    # It is suggested to name all packages '/package', but not required
    package = sep_054.Package(package_namespace + '/package')
    package.members = all_identities
    package.namespace = package_namespace
    # TODO: Call a separate function to get the dependencies

    return package

def get_prefix(subpackage_list):
    """ Find the shared prefix in the namespaces of a list of Package objects

    Args:
        subpackage_list (list of sep_054.Package objects): List of all the 
            sub-package package object

    Return
        prefix: The part of the namespace that all sub-packages have in common,
            will become the namespace of the package object. Example:
            sub-packages with namespaces 
            "https://example.org/MyPackage/promoters" and 
            "https://example.org/MyPackage/regulatory/repressors" would return 
            a prefix "https://example.org/MyPackage/"
    """
    # Get a list of all of the namespaces
    all_namespaces = [package.namespace for package in subpackage_list]

    # Take first word from array as reference
    ref_string = all_namespaces[0]
    ref_string_length = len(ref_string)

    # Make a holder for the prefix
    prefix = ""

    # Start with the first letter of the reference sub-string and add one letter
    # each loop
    for i in range(1, ref_string_length+1):
        # Generating the substring
        stem = ref_string[0:i]

        # Check all the namespaces have the substring
        is_present = all(stem in namespace for namespace in all_namespaces)
        
        if not is_present:
            break

        # If current substring is present in all strings and its length is 
        # greater than current result, save it as the stem
        if (is_present and len(prefix) < len(stem)):
            prefix = stem

    # Check if the namespace contains a .com or .org
    if any(s in prefix for s in ('.com', '.org', '.edu')):
        return(prefix)
    else:
        raise ValueError(f'The longest prefix found was {prefix}, which does '
                         f'include a .com. .org, or .edu')

def check_namespaces(package, sub_package_list=None):
    """ Check if the namespaces of all top level objects in a defined package
    are the same, and if all of its subpackages have the package namespace as a
    stem and are valid packages on their own

    Args:
        package (sep054.Package): Package to check
        sub_package_list (list of sep054.Package): The list of package objects 
            correlating to the URIs listed in package.subpackages

    Returns:
        is_package (boolean): True if all namespaces are the same
    """
    # Add the package to a document
    # CHECK: Do I have to do this? When I don't lookup doesn't work (no document object)
    # FIXME: Doesn't actually work- is always getting the namespace of the package
    # temp_doc = sbol3.Document()
    # temp_doc.add(package)

    # Check all members of the root package have the same namespace
    # Get a list of all namespaces
    # To get a namespace, remove the object name from the URI for each member
    # all_namespaces = set(o.namespace for member in package.members for o in member.parent.document.objects)
    all_namespaces = set("/".join(URI.split('/')[0:-1]) for URI in package.members)

    # Check all namespaces are the same
    if len(all_namespaces) == 1:
        pass
    else:
        raise ValueError(f'Not all members in package {package} have the same '
                         f'namespaces. The namespaces found are '
                         f'{all_namespaces}.')

    # Check all sub-packages have the same stem as the root package
    namespace_stem = package.namespace

    for sub_package_uri in package.subpackages:
        if namespace_stem in sub_package_uri:
            pass
        else:
            raise ValueError(f'Not all subpackages in package {package} share '
                             f'a common stem. {sub_package_uri} does not '
                             f'contain {namespace_stem}.')

        # Check each subpackage is a good package in of itself
        # Get the actual subpackage object
        sub_package_obj = get_package_obj(sub_package_list, sub_package_uri)
        # Check it
        check_namespaces(sub_package_obj)

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

