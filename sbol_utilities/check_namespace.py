import sbol3

import argparse
import logging

def main(doc: sbol3.Document):
    """
    Main wrapper: read from input file, invoke calculate_sequences, then write to output file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('sbol_file', help="SBOL file used as input")
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help="Name of SBOL file to be written")
    parser.add_argument('-t', '--file-type', dest='file_type', default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of expansion process")
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    log_level = logging.WARN if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.getLogger().setLevel(level=log_level)
    output_file = args_dict['output_file']
    file_type = args_dict['file_type']
    sbol_file = args_dict['sbol_file']
    extension = type_to_standard_extension[file_type]
    outfile_name = output_file if output_file.endswith(extension) else output_file+extension

    # Read file, convert, and write resulting document
    logging.info('Reading SBOL file '+sbol_file)
    doc = sbol3.Document()
    doc.read(sbol_file)
    logging.info('Calculating sequences')
    new_seqs = calculate_sequences(doc)
    logging.info(f'Calculated {len(new_seqs)} new sequences')
    doc.write(outfile_name, file_type)
    logging.info('SBOL file written to '+outfile_name)

def helper_function(doc: sbol3.Document):
    """ Check if the namespaces of all top level objects are the same

    :param doc: Document containing top level objects
    :return: boolean, true is all namespaces are the same
    """

    # Loop through the top level objects
        # Look at the name space
        # Save the first name space
        # Compare everyother name space to the first
            # If it matches, continue,
            # If t doesn't, quit

    print(filename)

if __name__ == '__main__':
    main()