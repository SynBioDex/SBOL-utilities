import filecmp
import os
import tempfile
import unittest

import sbol3
import tyto

from sbol_utilities.component import contained_components, contains, add_feature, add_interaction, constitutive, \
    regulate, order, in_role, all_in_role, ensure_singleton_feature

from sbol3 import component


class TestComponent(unittest.TestCase):

    def test_system_building(self):
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        system = sbol3.Component('system', sbol3.SBO_FUNCTIONAL_ENTITY)
        doc.add(system)
        # make a couple of stand-alone components
        gfp_cds = sbol3.Component('gfp_cds', sbol3.SBO_DNA, roles=[tyto.SO.CDS])
        doc.add(gfp_cds)

        # make a functional unit
        expression = add_feature(system, sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.engineered_region]))
        contains(expression, gfp_cds)
        rbs = contains(expression, sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.ribosome_entry_site]))
        regulate(rbs, gfp_cds)
        terminator = contains(expression, sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.terminator]))
        order(gfp_cds, terminator)
        constitutive(expression)
        # link it to a product
        gfp_mut3_ncbi = 'https://www.ncbi.nlm.nih.gov/protein/AAB18957.1'
        gfp = add_feature(system, sbol3.ExternallyDefined([sbol3.SBO_PROTEIN], gfp_mut3_ncbi))
        prod = add_interaction(sbol3.SBO_GENETIC_PRODUCTION,
                               participants={gfp: sbol3.SBO_PRODUCT, gfp_cds: sbol3.SBO_TEMPLATE})

        assert contained_components(system) == {system, gfp_cds}
        assert in_role(prod, sbol3.SBO_PRODUCT) == gfp
        assert all_in_role(prod, sbol3.SBO_TEMPLATE) == [ensure_singleton_feature(system, gfp_cds)]

        # confirm that the system constructed is exactly as expected
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'component_construction.nt')
        assert filecmp.cmp(tmp_out, comparison_file), f'Converted file {tmp_out} is not identical'

        hlc_doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        dna_comp, dna_seq = component.dna_component_with_sequence('J23101dna','tttacagctagctcagtcctaggtattatgctagc ', description='https://synbiohub.org/public/igem/BBa_J23101/1')
        rna_comp, rna_seq = component.rna_component_with_sequence('J23101rna','uuuacagcuagcucaguccuagguauuaugcuagc ', description='https://synbiohub.org/public/igem/BBa_J23101/1')
        pro_comp, pro_seq = component.protein_component_with_sequence('J23101pro','FTASSVLGIML', description='https://synbiohub.org/public/igem/BBa_J23101/1')
        media = component.media('LB')
        hlc_doc.add([dna_comp, dna_seq, rna_comp, rna_seq, pro_comp, pro_seq, media])
        report_sbol3 = hlc_doc.validate()
        assert len(report_sbol3) == 0

if __name__ == '__main__':
    unittest.main()
