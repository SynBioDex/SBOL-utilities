import argparse
import logging

import sbol3
# FIXME: Make sure relative importing works with the intended  use case
# These ones SHOULD work
import sbol_utilities.package # TODO: Suppress the output list
from sbol_utilities.workarounds import type_to_standard_extension
# These ones SHOULDN'T WORK
# import package # TODO: Suppress the output list
# from workarounds import type_to_standard_extension

def define_module(doc: sbol3.Document):
    # Call check_namespace
    logging.info('Checking namespaces')
    is_module, module_namespace = check_namespaces(doc)
    logging.info(f'SBOL Document is a Module: {is_module}')

    # If all namespaces are the same, add module and save as new file
    if is_module:
        # TODO: Check if the file already has a module defined, if so, abort

        # Get list of all members 
        # TODO: Check I want the names and not somthing else, sequences have no names, will modules have no sequences
        all_names = [o.name for o in doc.objects]

        # Define the module
        # Module is expecting only one positional argument, 'identity'
        # TODO: Check what is an identity string, can I just call it 'module'? Do we want it to be user defined? # FIXME: Use full url not the display id, or set namespaces
        module = sbol_utilities.package.sep_054.Module('module') # Identity becomes "'http://sbols.org/unspecified_namespace/Module'", do I need to set a namespace, the namespace of the Module?
        # All top level objects are members
        module.members = all_names
        # The displayId should be module, unless it is also a package # TODO: Check if it is also a package
        # module.display_id = 'module' # Seems to be set automatically
        # Namespace must match the hasNamespace value for all of its members
        module.namespace = module_namespace

        # Add the module to the document
        doc.add(module)

        # Return the doc
        return(doc)
        

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

    # Call define_module
    new_doc = define_module(doc)

    # Write out the new file
    new_doc.write(outfile_name, file_type)
    logging.info('Module file written to '+ outfile_name)
    

if __name__ == '__main__':
    main()