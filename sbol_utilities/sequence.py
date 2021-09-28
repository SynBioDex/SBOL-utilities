from typing import Union

import sbol3

############################
# Utilities for working with SBOL Sequence objects


def unambiguous_dna_sequence(sequence: Union[str, sbol3.Sequence]) -> bool:
    """Check if a sequence consists only of unambiguous DNA characters

    :param sequence: SBOL Sequence or string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    if isinstance(sequence, sbol3.Sequence):
        if sequence.encoding != sbol3.IUPAC_DNA_ENCODING:
            return False
        sequence = sequence.elements
    return sequence.lower().strip('acgt') == ''


def unambiguous_rna_sequence(sequence: Union[str, sbol3.Sequence]) -> bool:
    """Check if a sequence consists only of unambiguous RNA characters

    :param sequence: SBOL Sequence or string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    if isinstance(sequence, sbol3.Sequence):
        if sequence.encoding != sbol3.IUPAC_RNA_ENCODING:
            return False
        sequence = sequence.elements
    return sequence.lower().strip('acgu') == ''


def unambiguous_protein_sequence(sequence: Union[str, sbol3.Sequence]) -> bool:
    """Check if a sequence consists only of unambiguous protein characters

    :param sequence: SBOL Sequence or string to be checked
    :return: True if unambiguous DNA, false otherwise
    """
    if isinstance(sequence, sbol3.Sequence):
        if sequence.encoding != sbol3.IUPAC_PROTEIN_ENCODING:
            return False
        sequence = sequence.elements
    return sequence.lower().strip('acdefghiklmnpqrstvwy') == ''
