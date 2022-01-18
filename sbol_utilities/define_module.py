import argparse
import logging

import sbol3
import package # TODO: Suppress the output list

# TODO: Generalize importing to work in the intended use, right now this works 
# for calling command line functions from within the directory
from workarounds import type_to_standard_extension
# This is the exact same as in the other functions, should work for the actual
# version
# from sbol_utilities.workarounds import type_to_standard_extension

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
                        help="Name of SBOL file to output to (excluding type)") # TODO: Ask about this definition
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

    # Call check_namespace
    logging.info('Checking namespaces')
    is_module, module_namespace = check_namespaces(doc)
    logging.info(f'SBOL Document is a Module: {is_module}')

    ## For debugging ##
    print(f'SBOL Document is a Module: {is_module}')

    # If all namespaces are the same, add module and save as new file
    if is_module:
        # TODO: Check if the file already has a module defined, if so, abort

        # Get list of all members % TODO: Check I want the names and not somthing else
        all_names = [o.name for o in doc.objects]

        # Define the module
        module = package.sep_054.Module('Module', all_names) # TODO: Check what is an identity string, can I just call it 'module'? Do we want it to be user defined?

        # The displayId should be module, unless it is also a package # TODO: Check if it is also a package
        module.displayId('module')
        # Namespace must match the hasNamespace value for all of its members
        module.hasNamespace(module_namespace)

        # Add the module to the document
        doc.add(module)

        # TODO: Add the hasModule object too?

        # Write out the file
        doc.write(outfile_name, file_type)
        logging.info('Module file written to '+outfile_name)

def check_namespaces(doc: sbol3.Document):
    """ Check if the namespaces of all top level objects are the same

    :param doc: Document containing top level objects
    :return: boolean, true is all namespaces are the same
    """

    # Make a placeholder for the namespace
    namespace_holder = None

    # Loop through all TopLevel objects
    for o in doc.objects:

        # Save the first namespace
        if namespace_holder is None:
            namespace_holder = o.namespace

        # Compare every other namespace to the first
        if o.namespace == namespace_holder:
            continue
        else:
            return False

    # If all namespaces are the same, return true
    return True, namespace_holder

if __name__ == '__main__':
    main()