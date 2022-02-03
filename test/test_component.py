import filecmp
import os
import tempfile
import unittest

import sbol3
import tyto

from sbol_utilities.component import contained_components, contains, add_feature, add_interaction, constitutive, \
    regulate, order, in_role, all_in_role, ensure_singleton_feature
from sbol_utilities.component import dna_component_with_sequence, rna_component_with_sequence, \
    protein_component_with_sequence, media, functional_component, promoter, rbs, cds, terminator, \
    protein_stability_element, gene, operator, engineered_region, mrna, transcription_factor, \
    strain, ed_simple_chemical, ed_protein
from sbol_utilities.sbol_diff import doc_diff    


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
        rbs_comp = contains(expression, sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.ribosome_entry_site]))
        regulate(rbs_comp, gfp_cds)
        term_comp = contains(expression, sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.terminator]))
        order(gfp_cds, term_comp)
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

    def test_high_level_constructors(self):
        """Test construction of components and features using helper functions: for each, build manually and compare."""
        hlc_doc = sbol3.Document()
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        dna_identity = 'dna_component_with_sequence'
        dna_sequence = 'ttt'
        test_description = 'test'
        hl_dna_comp, hl_dna_seq = dna_component_with_sequence(dna_identity, dna_sequence, description=test_description)
        dna_seq = sbol3.Sequence(f'{dna_identity}_seq', elements=dna_sequence, encoding=sbol3.IUPAC_DNA_ENCODING)
        dna_comp = sbol3.Component(dna_identity, sbol3.SBO_DNA, sequences=[dna_seq], description=test_description)
        hlc_doc.add([hl_dna_comp, hl_dna_seq])
        doc.add([dna_comp, dna_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {dna_identity}'

        rna_identity = 'rna_component_with_sequence'
        rna_sequence = 'uuu'
        hl_rna_comp, hl_rna_seq = rna_component_with_sequence(rna_identity, rna_sequence, description=test_description)
        rna_seq = sbol3.Sequence(f'{rna_identity}_seq', elements=rna_sequence, encoding=sbol3.IUPAC_RNA_ENCODING)
        rna_comp = sbol3.Component(rna_identity, sbol3.SBO_RNA, sequences=[rna_seq], description=test_description)
        hlc_doc.add([hl_rna_comp, hl_rna_seq])
        doc.add([rna_comp, rna_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {rna_identity}'

        pro_identity = 'pro_component_with_sequence'
        pro_sequence = 'F'
        hl_pro_comp, hl_pro_seq = \
            protein_component_with_sequence(pro_identity, pro_sequence, description=test_description)
        pro_seq = sbol3.Sequence(f'{pro_identity}_seq', elements=pro_sequence, encoding=sbol3.IUPAC_PROTEIN_ENCODING)
        pro_comp = sbol3.Component(pro_identity, sbol3.SBO_PROTEIN, sequences=[pro_seq], description=test_description)
        hlc_doc.add([hl_pro_comp, hl_pro_seq])
        doc.add([pro_comp, pro_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {pro_identity}'

        fun_identity = 'fun_component_with_sequence'
        hlc_fun_comp = functional_component(fun_identity, description=test_description)
        fun_comp = sbol3.Component(fun_identity, sbol3.SBO_FUNCTIONAL_ENTITY, description=test_description)
        hlc_doc.add(hlc_fun_comp)
        doc.add(fun_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {fun_identity}'

        pro_identity = 'promoter'
        hlc_pro_comp, hlc_pro_seq = promoter(pro_identity, dna_sequence, description=test_description)
        p_comp, p_seq = dna_component_with_sequence(pro_identity, dna_sequence, description=test_description)
        p_comp.roles.append(sbol3.SO_PROMOTER)
        hlc_doc.add([hlc_pro_comp, hlc_pro_seq])
        doc.add([p_comp, p_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {pro_identity}'

        rbs_identity = 'rbs'
        hlc_rbs_comp, hlc_rbs_seq = rbs(rbs_identity, dna_sequence, description=test_description)
        rbs_comp, rbs_seq = dna_component_with_sequence(rbs_identity, dna_sequence, description=test_description)
        rbs_comp.roles. append(sbol3.SO_RBS)
        hlc_doc.add([hlc_rbs_comp, hlc_rbs_seq])
        doc.add([rbs_comp, rbs_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {rbs_identity}'

        cds_identity = 'cds'
        hlc_cds_comp, hlc_cds_seq = cds(cds_identity, dna_sequence, description=test_description)
        cds_comp, cds_seq = dna_component_with_sequence(cds_identity, dna_sequence, description=test_description)
        cds_comp.roles. append(sbol3.SO_CDS)
        hlc_doc.add([hlc_cds_comp, hlc_cds_seq])
        doc.add([cds_comp, cds_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {cds_identity}'

        ter_identity = 'terminator'
        hlc_ter_comp, hlc_ter_seq = terminator(ter_identity, dna_sequence, description=test_description)
        ter_comp, ter_seq = dna_component_with_sequence(ter_identity, dna_sequence, description=test_description)
        ter_comp.roles. append(sbol3.SO_TERMINATOR)
        hlc_doc.add([hlc_ter_comp, hlc_ter_seq])
        doc.add([ter_comp, ter_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {ter_identity}'

        pse_identity = 'protein_stability_element'
        hlc_pse_comp, hlc_pse_seq = protein_stability_element(pse_identity, dna_sequence, description=test_description)
        pse_comp, pse_seq = dna_component_with_sequence(pse_identity, dna_sequence, description=test_description)
        pse_comp.roles. append(tyto.SO.protein_stability_element)
        hlc_doc.add([hlc_pse_comp, hlc_pse_seq])
        doc.add([pse_comp, pse_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {pse_identity}'

        gene_identity = 'gene'
        hlc_gene_comp, hlc_gene_seq = gene(gene_identity, dna_sequence, description=test_description)
        gene_comp, gene_seq = dna_component_with_sequence(gene_identity, dna_sequence, description=test_description)
        gene_comp.roles. append(sbol3.SO_GENE)
        hlc_doc.add([hlc_gene_comp, hlc_gene_seq])
        doc.add([gene_comp, gene_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {gene_identity}'

        operator_identity = 'operator'
        hlc_ope_comp, hlc_ope_seq = operator(operator_identity, dna_sequence, description=test_description)
        ope_comp, ope_seq = dna_component_with_sequence(operator_identity, dna_sequence, description=test_description)
        ope_comp.roles. append(sbol3.SO_OPERATOR)
        hlc_doc.add([hlc_ope_comp, hlc_ope_seq])
        doc.add([ope_comp, ope_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {operator_identity}'

        enr_identity = 'engineered_region'
        enr_features = [pro_comp, rbs_comp, cds_comp, ter_comp]
        hlc_enr_comp = engineered_region(enr_identity, enr_features, description=test_description)
        enr_comp = sbol3.Component(enr_identity, sbol3.SBO_DNA, description=test_description)
        enr_comp.roles.append(sbol3.SO_ENGINEERED_REGION)
        for to_add in enr_features:
            if isinstance(to_add, sbol3.Component):
                to_add = sbol3.SubComponent(to_add)
            enr_comp.features.append(to_add)
        if len(enr_comp.features) > 1:
            for i in range(len(enr_comp.features)-1):
                constraint = sbol3.Constraint(sbol3.SBOL_PRECEDES, enr_comp.features[i], enr_comp.features[i+1])
                enr_comp.constraints = [constraint]
        else:
            pass
        hlc_doc.add(hlc_enr_comp)
        doc.add(enr_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {enr_identity}'

        mrna_identity = 'mrna'
        hlc_mrna_comp, hlc_mrna_seq = mrna(mrna_identity, rna_sequence, description=test_description)
        mrna_comp, mrna_seq = rna_component_with_sequence(mrna_identity, rna_sequence, description=test_description)
        mrna_comp.roles. append(sbol3.SO_MRNA)
        hlc_doc.add([hlc_mrna_comp, hlc_mrna_seq])
        doc.add([mrna_comp, mrna_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {mrna_identity}'

        tf_identity = 'transcription_factor'
        hlc_tf_comp, hlc_tf_seq = transcription_factor(tf_identity, rna_sequence, description=test_description)
        tf_comp, tf_seq = protein_component_with_sequence(tf_identity, rna_sequence, description=test_description)
        tf_comp.roles. append(sbol3.SO_TRANSCRIPTION_FACTOR)
        hlc_doc.add([hlc_tf_comp, hlc_tf_seq])
        doc.add([tf_comp, tf_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {tf_identity}'

        strain_identity = 'strain'
        hlc_strain_comp = strain(strain_identity, description=test_description)
        strain_comp = functional_component(strain_identity, description=test_description)
        strain_comp.roles.append(tyto.NCIT.Strain)
        hlc_doc.add(hlc_strain_comp)
        doc.add(strain_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {strain_identity}'

        cds_ed_sch_identity = 'cds_ed_sch_identity'
        hlc_cds_ed_sch_comp, _ = cds(cds_ed_sch_identity, dna_sequence, description=test_description)
        cds_comp, _ = dna_component_with_sequence(cds_ed_sch_identity, dna_sequence, description=test_description)
        cds_comp.roles. append(sbol3.SO_CDS)
        ed_sch_definition = 'http://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:177976'
        hlc_ed_sch = ed_simple_chemical(ed_sch_definition, description=test_description)
        ed_sch = sbol3.ExternallyDefined([sbol3.SBO_SIMPLE_CHEMICAL], ed_sch_definition, description=test_description)
        hlc_cds_ed_sch_comp.features.append(hlc_ed_sch)
        cds_comp.features.append(ed_sch)
        hlc_doc.add(hlc_cds_ed_sch_comp)
        doc.add(cds_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {ed_sch_definition}'

        cds_ed_pro_identity = 'cds_ed_pro_identity'
        hlc_cds_ed_pro_comp, _ = cds(cds_ed_pro_identity, dna_sequence, description=test_description)
        cds_comp, _ = dna_component_with_sequence(cds_ed_pro_identity, dna_sequence, description=test_description)
        cds_comp.roles. append(sbol3.SO_CDS)
        ed_pro_definition = 'https://www.uniprot.org/uniprot/P12747'
        hlc_ed_pro = ed_protein(ed_pro_definition, description=test_description)
        ed_pro = sbol3.ExternallyDefined([sbol3.SBO_PROTEIN], ed_pro_definition, description=test_description)
        hlc_cds_ed_pro_comp.features.append(hlc_ed_pro)
        cds_comp.features.append(ed_pro)
        hlc_doc.add(hlc_cds_ed_pro_comp)
        doc.add(cds_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {ed_pro_definition}'

        peptone = sbol3.Component('Bacto_Peptone', tyto.SBO.functional_entity, name='Bacto_Peptone',
                                  derived_from=['https://www.thermofisher.com/order/catalog/product/211820'])
        nacl = sbol3.Component('NaCl', tyto.SBO.functional_entity, name='NaCl',
                               derived_from=['https://www.sigmaaldrich.com/AU/en/product/sigald/s9888'])
        yeast_extract = sbol3.Component('Yeast_Extract', tyto.SBO.functional_entity, name='Yeast_Extract',
                                        derived_from=['https://www.thermofisher.com/order/catalog/product/212720'])

        recipe = {
            peptone: [10, tyto.OM.gram],
            nacl: [5, tyto.OM.gram],
            yeast_extract: [5, tyto.OM.gram]
        }

        media_identity = 'media'
        hlc_media_comp = media(media_identity, recipe, description=test_description)
        media_comp = functional_component(media_identity, description=test_description)
        media_comp.roles.append(tyto.NCIT.Media)
        if recipe:
            for key, value in recipe.items():
                if isinstance(key, sbol3.Component):
                    key = sbol3.SubComponent(key)
                key.measures.append(sbol3.Measure(value[0], value[1]))
                media_comp.features.append(key)
        hlc_doc.add(hlc_media_comp)
        doc.add(media_comp)
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: {media_identity}'

if __name__ == '__main__':
    unittest.main()
