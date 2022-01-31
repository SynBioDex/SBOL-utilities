import os
from pathlib import Path
import argparse
import logging

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

def define_package(*args: sbol3.Document):
    """Function to take one or more sbol documents, check if they are a package,
     and create a new sbol document with the package definition included

    Args:
        *args (sbol3.Document): The document(s) to be checked for a package

    Return
        doc (sbol3.Document): The document with the added package info
    """

    # Call check_namespace
    logging.info('Checking namespaces')
    is_package, package_namespace = check_namespaces(*args)
    logging.info(f'SBOL Document is a package: {is_package}')

    # If all namespaces are the same, add package and save as new file
    if is_package:

        # Get list of identities of all top level objects from all files
        all_identities = [o.identity for doc in args for o in doc.objects]

        # Define the package
        package = sep_054.Package(package_namespace + '/package')

        # All top level objects are members
        package.members = all_identities

        # Namespace must match the hasNamespace value for all of its members
        package.namespace = package_namespace

        # Combine all of the docs into one
        doc = args[0]
        for sbol_doc in args[1:]:
            doc_objects = [o for o in sbol_doc.objects]
            doc.add(doc_objects)
        
        # Add the package to the document
        doc.add(package)

        # Return the doc
        return(doc)
        

def check_namespaces(*args: sbol3.Document):
    """ Check if the namespaces of all top level objects in one or more files
    are the same

    Args:
        *args (sbol3.Document): Document(s) containing top level objects

    Returns:
        is_package (boolean): True if all namespaces are the same
        namespace (string): Namespace of the first object
    """

    # Get a list of all namespaces
    all_namespaces = [o.namespace for doc in args for o in doc.objects]

    # Check all namespaces are the same
    is_package = all(x == all_namespaces[0] for x in all_namespaces)

    # Get the first namespace to pass the string
    # Which position you pick won't matter if it is a package
    namespace = all_namespaces[0]

    return is_package, namespace

def main():
    """
    Main wrapper: read from input file, invoke check_namespace, then write to 
    output file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('sbol_file', help="SBOL file used as input")
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help="Name of SBOL file to be written")
    parser.add_argument('-t', '--file-type', dest='file_type',
                        default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', 
                        default=0,
                        help="Print running explanation of expansion process")
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    log_level = logging.WARN if verbosity == 0 \
        else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.getLogger().setLevel(level=log_level)
    output_file = args_dict['output_file']
    file_type = args_dict['file_type']
    sbol_file = args_dict['sbol_file']
    extension = type_to_standard_extension[file_type]
    outfile_name = output_file if output_file.endswith(extension) \
        else output_file+extension

    # Read file
    logging.info('Reading SBOL file '+sbol_file)
    doc = sbol3.Document()
    doc.read(sbol_file)

    # Call define_package
    new_doc = define_package(doc)

    # Write out the new file
    new_doc.write(outfile_name, file_type)
    logging.info('Package file written to '+ outfile_name)
    

if __name__ == '__main__':
    main()
