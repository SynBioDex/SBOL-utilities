from sbol_utilities.helper_functions import *


def test_sequence_validators():
    assert unambiguous_dna_sequence('actGATCG')
    assert not unambiguous_dna_sequence('this is a non-DNA string')
    assert unambiguous_rna_sequence('acugaucg')
    assert not unambiguous_rna_sequence('actgatcg')
    assert unambiguous_protein_sequence('tklqpntvir')
    assert not unambiguous_protein_sequence('tklqxpntvir')
