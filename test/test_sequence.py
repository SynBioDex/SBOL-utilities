import unittest

import sbol3

from sbol_utilities.sequence import unambiguous_dna_sequence, unambiguous_rna_sequence, unambiguous_protein_sequence


class TestSequence(unittest.TestCase):

    def test_sequence_validators(self):
        assert unambiguous_dna_sequence('actGATCG')
        assert not unambiguous_dna_sequence('this is a non-DNA string')
        assert unambiguous_rna_sequence('acugaucg')
        assert not unambiguous_rna_sequence('actgatcg')
        assert unambiguous_protein_sequence('tklqpntvir')
        assert not unambiguous_protein_sequence('tklqxpntvir')

        s = sbol3.Sequence('http://test.org/seq', namespace='http://test.org/',
                           encoding=sbol3.IUPAC_DNA_ENCODING, elements='acgacg')
        assert unambiguous_dna_sequence(s)
        assert unambiguous_rna_sequence(s)  # Because DNA and RNA use the same EDAM identifier
        assert not unambiguous_protein_sequence(s)
        s.elements = 'tklqpntvir'
        assert not unambiguous_rna_sequence(s)
        assert not unambiguous_protein_sequence(s)
        s.encoding = sbol3.IUPAC_PROTEIN_ENCODING
        assert unambiguous_protein_sequence(s)


if __name__ == '__main__':
    unittest.main()
