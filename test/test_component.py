import filecmp
import os
import tempfile
import unittest
from pathlib import Path

import sbol3
import tyto

from sbol_utilities.component import contained_components, contains, add_feature, add_interaction, \
    constitutive, ed_restriction_enzyme, \
    regulate, order, in_role, all_in_role, ensure_singleton_feature, is_dna_part
from sbol_utilities.component import dna_component_with_sequence, rna_component_with_sequence, \
    protein_component_with_sequence, media, functional_component, promoter, rbs, cds, terminator, \
    protein_stability_element, gene, operator, engineered_region, mrna, transcription_factor, \
    strain, ed_simple_chemical, ed_protein

from sbol_utilities.component import ed_restriction_enzyme, backbone, part_in_backbone,  part_in_backbone_from_sbol, \
    digestion, ligation, Assembly_plan_composite_in_backbone_single_enzyme
from sbol_utilities.helper_functions import find_top_level, toplevel_named, TopLevelNotFound, outgoing_links
from sbol_utilities.sbol_diff import doc_diff    
from sbol_utilities.conversion import convert_from_genbank


class TestComponent(unittest.TestCase):

    def test_dna_part(self):
        """Test the correctness of is_dna_part check"""
        # create a test dna component
        dna_identity = 'Test_dna_identity'
        dna_sequence = 'Test_dna_sequence'
        dna_description = 'Test_dna_description'
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        # we don't need dna_sequence object
        test_dna_component, _ = dna_component_with_sequence(dna_identity, dna_sequence, description=dna_description)
        # adding atleast 1 SO role
        test_dna_component.roles.append(sbol3.SO_GENE)
        assert is_dna_part(test_dna_component) 

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

        self.assertEqual(contained_components(system), {system, gfp_cds})
        self.assertEqual(outgoing_links(doc), set())
        self.assertEqual(in_role(prod, sbol3.SBO_PRODUCT), gfp)
        self.assertEqual(all_in_role(prod, sbol3.SBO_TEMPLATE),
                         [ensure_singleton_feature(system, gfp_cds)])

        # confirm that the system constructed is exactly as expected
        tmp_out = tempfile.mkstemp(suffix='.nt')[1]
        doc.write(tmp_out, sbol3.SORTED_NTRIPLES)
        test_dir = os.path.dirname(os.path.realpath(__file__))
        comparison_file = os.path.join(test_dir, 'test_files', 'component_construction.nt')
        assert filecmp.cmp(tmp_out, comparison_file), f'Converted file {tmp_out} is not identical'

    def test_containment(self):
        """Test the operation of the contained_components function"""
        doc = sbol3.Document()
        test_dir = Path(__file__).parent
        doc.read(str(test_dir / 'test_files' / 'constraints_library.nt'))

        # Total of 43 parts, 2 non-library composites, 6 templates, 2 inserts
        self.assertEqual(len(contained_components(doc.objects)), 53)
        self.assertEqual(len(contained_components(toplevel_named(doc, 'BB-B0032-BB'))), 4)
        self.assertEqual(len(contained_components(toplevel_named(doc, 'UNSX-UP'))), 3)
        # 1 template, 4 in first slot, 4+template in 2nd slot
        c = toplevel_named(doc, 'Multicolor expression')
        self.assertEqual(len(contained_components(c)), 10)
        # 1 template, 4 in first slot, 4+template in 2nd slot
        c = toplevel_named(doc, 'Multicolor regulatory')
        self.assertEqual(len(contained_components(c)), 10)
        # 1 template, 1 backbone, 1 insert, 10 in 1st slot, 4 in 2nd (-1 shared), 5 in 3rd, 2 others
        self.assertEqual(len(contained_components(toplevel_named(doc, 'Two color - operon'))), 23)

        # Test again with an incomplete file. Should fail when missing elements are requested, but not when untouched
        doc.read(str(test_dir / 'test_files' / 'incomplete_constraints_library.nt'))
        self.assertRaises(TopLevelNotFound, lambda: contained_components(doc.objects))
        self.assertEqual(len(contained_components(toplevel_named(doc, 'BB-B0032-BB'))), 4)
        self.assertRaises(TopLevelNotFound, lambda: contained_components(toplevel_named(doc, 'Multicolor expression')))

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

    def test_restriction_enzyme_bp011(self):
        """Test the restriction_enzyme function"""
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        restriction_enzyme_name = 'BsaI'
        restriction_enzyme_definition = 'http://rebase.neb.com/rebase/enz/BsaI.html' # TODO: replace with getting the URI from Enzyme when REBASE identifiers become available in biopython 1.80
        bsai = ed_restriction_enzyme(restriction_enzyme_name)
        assert bsai.definition == restriction_enzyme_definition, 'Constructor Error: ed_restriction_enzyme'
        
    def test_backbone_bp011(self):
        """Test the backbone function"""
        hlc_doc = sbol3.Document()
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        backbone_identity = 'backbone'
        backbone_sequence = 'aaGGGGttttCCCCaa'
        dropout_location = [3,15]
        fusion_site_length = 4
        test_description = 'test'

        hl_circular_backbone_component, hl_circular_backbone_seq = backbone(identity=backbone_identity, sequence=backbone_sequence, dropout_location=dropout_location, fusion_site_length=fusion_site_length, linear=False, description=test_description)
        hlc_doc.add([hl_circular_backbone_component, hl_circular_backbone_seq])

        circular_backbone_seq = sbol3.Sequence(f'{backbone_identity}_seq', elements=backbone_sequence, encoding=sbol3.IUPAC_DNA_ENCODING)
        circular_backbone_component =  sbol3.Component(backbone_identity, types=[sbol3.SBO_DNA, sbol3.SO_CIRCULAR], roles=[sbol3.SO_DOUBLE_STRANDED, tyto.SO.plasmid_vector], sequences=[circular_backbone_seq], description=test_description)

        dropout_location_comp = sbol3.Range(sequence=circular_backbone_seq, start=dropout_location[0], end=dropout_location[1])
        insertion_site_location1 = sbol3.Range(sequence=circular_backbone_seq, start=dropout_location[0], end=dropout_location[0]+fusion_site_length, order=1)
        insertion_site_location2 = sbol3.Range(sequence=circular_backbone_seq, start=dropout_location[1]-fusion_site_length, end=dropout_location[1], order=3)
        open_backbone_location1 = sbol3.Range(sequence=circular_backbone_seq, start=1, end=dropout_location[0]+fusion_site_length -1, order=2)
        open_backbone_location2 = sbol3.Range(sequence=circular_backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(backbone_sequence), order=1)
        dropout_sequence_feature = sbol3.SequenceFeature(locations=[dropout_location_comp], roles=[tyto.SO.deletion])
        insertion_sites_feature = sbol3.SequenceFeature(locations=[insertion_site_location1, insertion_site_location2], roles=[tyto.SO.insertion_site])
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])

        circular_backbone_component.features.append(dropout_sequence_feature)
        circular_backbone_component.features.append(insertion_sites_feature)
        circular_backbone_component.features.append(open_backbone_feature)
        backbone_dropout_meets = sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=dropout_sequence_feature, object=open_backbone_feature)
        circular_backbone_component.constraints.append(backbone_dropout_meets)
        doc.add([circular_backbone_component, circular_backbone_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: Circular {backbone_identity}'

        hlc_doc = sbol3.Document()
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        hl_linear_backbone_component, hl_linear_backbone_seq = backbone(identity=backbone_identity, sequence=backbone_sequence, dropout_location=dropout_location, fusion_site_length=fusion_site_length, linear=True, description=test_description)
        hlc_doc.add([hl_linear_backbone_component, hl_linear_backbone_seq])

        linear_backbone_seq = sbol3.Sequence(f'{backbone_identity}_seq', elements=backbone_sequence, encoding=sbol3.IUPAC_DNA_ENCODING)
        linear_backbone_component =  sbol3.Component(backbone_identity, types=[sbol3.SBO_DNA, sbol3.SO_LINEAR], roles=[sbol3.SO_DOUBLE_STRANDED, sbol3.SO_ENGINEERED_REGION], sequences=[linear_backbone_seq], description=test_description)

        dropout_location_comp = sbol3.Range(sequence=linear_backbone_seq, start=dropout_location[0], end=dropout_location[1]) 
        insertion_site_location1 = sbol3.Range(sequence=linear_backbone_seq, start=dropout_location[0], end=dropout_location[0]+fusion_site_length, order=1)
        insertion_site_location2 = sbol3.Range(sequence=linear_backbone_seq, start=dropout_location[1]-fusion_site_length, end=dropout_location[1], order=3)
        open_backbone_location1 = sbol3.Range(sequence=linear_backbone_seq, start=1, end=dropout_location[0]+fusion_site_length-1, order=1)
        open_backbone_location2 = sbol3.Range(sequence=linear_backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(backbone_sequence), order=3)
        dropout_sequence_feature = sbol3.SequenceFeature(locations=[dropout_location_comp], roles=[tyto.SO.deletion])
        insertion_sites_feature = sbol3.SequenceFeature(locations=[insertion_site_location1, insertion_site_location2], roles=[tyto.SO.insertion_site])
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])

        linear_backbone_component.features.append(dropout_sequence_feature)
        linear_backbone_component.features.append(insertion_sites_feature)
        linear_backbone_component.features.append(open_backbone_feature)
        backbone_dropout_meets = sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=dropout_sequence_feature, object=open_backbone_feature)
        linear_backbone_component.constraints.append(backbone_dropout_meets)
        doc.add([linear_backbone_component, linear_backbone_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: Linear {backbone_identity}'
        
    def test_part_in_backbone_bp011(self):
        """Test the part_in_backbone function"""
        hlc_doc = sbol3.Document()
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        test_promoter, test_promoter_seq = promoter('pTest', 'aaTTaa')
        dropout_location = [4,14]
        fusion_site_length = 4
        test_backbone, test_backbone_seq = backbone('test_bb','cccGGGGTTGGGGccc', dropout_location, fusion_site_length, linear=False)
        identity_pib = 'part_in_backbone'
        hlc_doc.add([test_promoter, test_promoter_seq, test_backbone, test_backbone_seq])
        doc.add([test_promoter, test_promoter_seq, test_backbone, test_backbone_seq])

        hl_part_in_backbone_circular, hl_part_in_backbone_circular_sequence = part_in_backbone(identity_pib, part=test_promoter, backbone=test_backbone)
        hlc_doc.add([hl_part_in_backbone_circular, hl_part_in_backbone_circular_sequence])

        backbone_sequence = test_backbone.sequences[0].lookup().elements
        open_backbone_sequence_from_location1=backbone_sequence[test_backbone.features[-1].locations[0].start -1 : test_backbone.features[-1].locations[0].end]
        open_backbone_sequence_from_location2=backbone_sequence[test_backbone.features[-1].locations[1].start -1 : test_backbone.features[-1].locations[1].end]
        
        part_sequence = test_promoter.sequences[0].lookup().elements
        part_in_backbone_seq_str = part_sequence + open_backbone_sequence_from_location2 + open_backbone_sequence_from_location1
        part_in_backbone_component, part_in_backbone_seq = dna_component_with_sequence(identity_pib, part_in_backbone_seq_str)
        part_in_backbone_component.roles.append(tyto.SO.plasmid_vector) #review
        part_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=1, end=len(part_sequence))
        backbone_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=len(part_sequence)+1, end=len(part_in_backbone_seq_str))
        source_location = sbol3.Range(sequence=backbone_sequence, start=test_backbone.features[-1].locations[0].start, end=test_backbone.features[-1].locations[0].end) # review
        part_subcomponent = sbol3.SubComponent(test_promoter, roles=[tyto.SO.engineered_insert], locations=[part_subcomponent_location], role_integration='http://sbols.org/v3#mergeRoles')
        backbone_subcomponent = sbol3.SubComponent(test_backbone, locations=[backbone_subcomponent_location], source_locations=[source_location])  #[backbone.features[2].locations[0]]) #generalize source location
        part_in_backbone_component.features.append(part_subcomponent)
        part_in_backbone_component.features.append(backbone_subcomponent)
        part_in_backbone_component_circular = part_in_backbone_component
        part_in_backbone_component_circular.types.append(sbol3.SO_CIRCULAR)
        doc.add([part_in_backbone_component_circular, part_in_backbone_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: Circular {identity_pib}'

        hlc_doc = sbol3.Document()
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')

        hlc_doc.add([test_promoter, test_promoter_seq, test_backbone, test_backbone_seq])
        doc.add([test_promoter, test_promoter_seq, test_backbone, test_backbone_seq])

        hl_part_in_backbone_linear, hl_part_in_backbone_linear_sequence = part_in_backbone(identity_pib, part=test_promoter, backbone=test_backbone, linear=True)
        hlc_doc.add([hl_part_in_backbone_linear, hl_part_in_backbone_linear_sequence])

        part_in_backbone_seq_str = open_backbone_sequence_from_location1 + part_sequence + open_backbone_sequence_from_location2
        part_in_backbone_component, part_in_backbone_seq = dna_component_with_sequence(identity_pib, part_in_backbone_seq_str)
        part_in_backbone_component.roles.append(tyto.SO.plasmid_vector) #review
        part_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=1, end=len(part_sequence))
        backbone_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=len(part_sequence)+1, end=len(part_in_backbone_seq_str))
        source_location = sbol3.Range(sequence=backbone_sequence, start=test_backbone.features[-1].locations[0].start, end=test_backbone.features[-1].locations[0].end) # review
        part_subcomponent = sbol3.SubComponent(test_promoter, roles=[tyto.SO.engineered_insert], locations=[part_subcomponent_location], role_integration='http://sbols.org/v3#mergeRoles')
        backbone_subcomponent = sbol3.SubComponent(test_backbone, locations=[backbone_subcomponent_location], source_locations=[source_location])  #[backbone.features[2].locations[0]]) #generalize source location
        part_in_backbone_component.features.append(part_subcomponent)
        part_in_backbone_component.features.append(backbone_subcomponent)
        part_in_backbone_component_linear = part_in_backbone_component
        part_in_backbone_component_linear.types.append(sbol3.SO_LINEAR)
        doc.add([part_in_backbone_component_linear, part_in_backbone_seq])
        assert doc_diff(doc, hlc_doc) == 0, f'Constructor Error: Linear {identity_pib}'
        
    def test_part_in_backbone_from_sbol_bp011(self):
        hlc_doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        test_dir = os.path.dirname(os.path.realpath(__file__))
        b0015_dir = os.path.join(test_dir, 'test_files', 'b0015.gb')
        # Part in backbone from SBOL
        target_b0015_unitary_part_sequence = 'ccaggcatcaaataaaacgaaaggctcagtcgaaagactgggcctttcgttttatctgttgtttgtcggtgaacgctctctactagagtcacactggctcaccttcgggtgggcctttctgcgtttata'
        b0015_doc = convert_from_genbank(b0015_dir, 'https://github.com/Gonza10V')
        b0015_ef = [top_level for top_level in b0015_doc if type(top_level)==sbol3.Component][0]
        hlc_b0015_ef_in_bb, hlc_b0015_ef_in_bb_seq = part_in_backbone_from_sbol('b0015_ef_in_bb', b0015_ef, [518,646], [sbol3.SO_TERMINATOR], 4, False, name='b0015_ef_in_bb')
        hlc_doc.add([hlc_b0015_ef_in_bb, hlc_b0015_ef_in_bb_seq])
        for feature in hlc_b0015_ef_in_bb.features:
            if feature.roles == [sbol3.SO_TERMINATOR, tyto.SO.engineered_insert]:
                b0015_unitary_part_sequence = feature.locations[0].sequence.lookup().elements[feature.locations[0].start-1:feature.locations[0].end]
        assert target_b0015_unitary_part_sequence == b0015_unitary_part_sequence , "Unitary part sequence does not match target sequence"
        assert len(hlc_b0015_ef_in_bb.features) == 3, f"Incorrect number of features, number of features expeted is 3, got {len(hlc_b0015_ef_in_bb.features)}"
        assert set(hlc_b0015_ef_in_bb.types) == set([sbol3.SBO_DNA, sbol3.SO_CIRCULAR]) , f"Incorrect types, types expected are [sbol3.SBO_DNA, sbol3.SO_CIRCULAR], got {hlc_b0015_ef_in_bb.types}"
        assert set(hlc_b0015_ef_in_bb.roles) == set([sbol3.SO_DOUBLE_STRANDED, sbol3.SO_TERMINATOR, tyto.SO.plasmid_vector]), f"Incorrect roles, roles expected are [sbol3.SO_DOUBLE_STRANDED, sbol3.SO_TERMINATOR, tyto.SO.plasmid_vector], got {hlc_b0015_ef_in_bb.roles}"
        features_roles = set()
        for ft in hlc_b0015_ef_in_bb.features:
            for role in ft.roles:
                features_roles.add(role)
        assert features_roles == set([tyto.SO.insertion_site, sbol3.SO_TERMINATOR, tyto.SO.engineered_insert]), f"Incorrect feature roles, roles expected are [tyto.SO.insertion_site, sbol3.SO_TERMINATOR, tyto.SO.engineered_insert], got {features_roles}"
        
    def test_assembly_plan_bp011(self):
        """Test assembly plan class"""
        doc = sbol3.Document()
        sbol3.set_namespace('http://sbolstandard.org/testfiles')
        test_dir = os.path.dirname(os.path.realpath(__file__))
        # Assembly plan setup
        bsai = ed_restriction_enzyme('BsaI')
        #lvl1 acceptor
        lvl1_pOdd_acceptor_seq = 'gctcgagtcccgtcaagtcagcgtaatgctctgccagtgttacaaccaattaaccaattctgattagaaaaactcatcgagcatcaaatgaaactgcaatttattcatatcaggattatcaataccatatttttgaaaaagccgtttctgtaatgaaggagaaaactcaccgaggcagttccataggatggcaagatcctggtatcggtctgcgattccgactcgtccaacatcaatacaacctattaatttcccctcgtcaaaaataaggttatcaagtgagaaatcaccatgagtgacgactgaatccggtgagaatggcaaaagcttatgcatttctttccagacttgttcaacaggccagccattacgctcgtcatcaaaatcactcgcatcaaccaaaccgttattcattcgtgattgcgcctgagcgagacgaaatacgcgatcgctgttaaaaggacaattacaaacaggaatcgaatgcaaccggcgcaggaacactgccagcgcatcaacaatattttcacctgaatcaggatattcttctaatacctggaatgctgttttcccggggatcgcagtggtgagtaaccatgcatcatcaggagtacggataaaatgcttgatggtcggaagaggcataaattccgtcagccagtttagtctgaccatctcatctgtaacatcattggcaacgctacctttgccatgtttcagaaacaactctggcgcatcgggcttcccatacaatcgatagattgtcgcacctgattgcccgacattatcgcgagcccatttatacccatataaatcagcatccatgttggaatttaatcgcggcctggagcaagacgtttcccgttgaatatggctcataacaccccttgtattactgtttatgtaagcagacagttttattgttcatgatgatatatttttatcttgtgcaatgtaacatcagagattttgagacacaacgtggctttgttgaataaatcgaacttttgctgagttgaaggatcagctcgagtgccacctgacgtctaagaaaccattattatcatgacattaacctataaaaataggcgtatcacgaggcagaatttcagataaaaaaaatccttagctttcgctaaggatgatttctggaattcgctcttcaatgggagtgagacccaatacgcaaaccgcctctccccgcgcgttggccgattcattaatgcagctggcacgacaggtttcccgactggaaagcgggcagtgagcgcaacgcaattaatgtgagttagctcactcattaggcaccccaggctttacactttatgcttccggctcgtatgttgtgtggaattgtgagcggataacaatttcacacatactagagaaagaggagaaatactagatggcttcctccgaagacgttatcaaagagttcatgcgtttcaaagttcgtatggaaggttccgttaacggtcacgagttcgaaatcgaaggtgaaggtgaaggtcgtccgtacgaaggtacccagaccgctaaactgaaagttaccaaaggtggtccgctgccgttcgcttgggacatcctgtccccgcagttccagtacggttccaaagcttacgttaaacacccggctgacatcccggactacctgaaactgtccttcccggaaggtttcaaatgggaacgtgttatgaacttcgaagacggtggtgttgttaccgttacccaggactcctccctgcaagacggtgagttcatctacaaagttaaactgcgtggtaccaacttcccgtccgacggtccggttatgcagaaaaaaaccatgggttgggaagcttccaccgaacgtatgtacccggaagacggtgctctgaaaggtgaaatcaaaatgcgtctgaaactgaaagacggtggtcactacgacgctgaagttaaaaccacctacatggctaaaaaaccggttcagctgccgggtgcttacaaaaccgacatcaaactggacatcacctcccacaacgaagactacaccatcgttgaacagtacgaacgtgctgaaggtcgtcactccaccggtgcttaataacgctgatagtgctagtgtagatcgctactagagccaggcatcaaataaaacgaaaggctcagtcgaaagactgggcctttcgttttatctgttgtttgtcggtgaacgctctctactagagtcacactggctcaccttcgggtgggcctttctgcgtttataggtctcaGCTTgcatgaagagcctgcagtccggcaaaaaagggcaaggtgtcaccaccctgccctttttctttaaaaccgaaaagattacttcgcgttatgcaggcttcctcgctcactgactcgctgcgctcggtcgttcggctgcggcgagcggtatcagctcactcaaaggcggtaatacggttatccacagaatcaggggataacgcaggaaagaacatgtgagcaaaaggccagcaaaaggccaggaaccgtaaaaaggccgcgttgctggcgtttttccacaggctccgcccccctgacgagcatcacaaaaatcgacgctcaagtcagaggtggcgaaacccgacaggactataaagataccaggcgtttccccctggaagctccctcgtgcgctctcctgttccgaccctgccgcttaccggatacctgtccgcctttctcccttcgggaagcgtggcgctttctcatagctcacgctgtaggtatctcagttcggtgtaggtcgttcgctccaagctgggctgtgtgcacgaaccccccgttcagcccgaccgctgcgccttatccggtaactatcgtcttgagtccaacccggtaagacacgacttatcgccactggcagcagccactggtaacaggattagcagagcgaggtatgtaggcggtgctacagagttcttgaagtggtggcctaactacggctacactagaagaacagtatttggtatctgcgctctgctgaagccagttaccttcggaaaaagagttggtagctcttgatccggcaaacaaaccaccgctggtagcggtggtttttttgtttgcaagcagcagattacgcgcagaaaaaaaggatctcaagaagatcctttgatcttttctacggggtctgacgctcagtggaacgaaaactcacgttaagggattttggtcatgagattatcaaaaaggatcttcacctagatccttttaaattaaaaatgaagttttaaatcaatctaaagtatatatgagtaaacttggtctgaca'
        podd_backbone, podd_backbone_seq = backbone('pOdd_bb', lvl1_pOdd_acceptor_seq, [1169,2259], 4, False, name='pOdd_bb')
        doc.add([podd_backbone,podd_backbone_seq])
        #parts in backbone
        j23100_b0034_dir = os.path.join(test_dir, 'test_files', 'j23100_b0034.gb')
        sfgfp_dir = os.path.join(test_dir, 'test_files', 'sfgfp.gb')
        b0015_dir = os.path.join(test_dir, 'test_files', 'b0015.gb')
        j23100_b0034_doc = convert_from_genbank(j23100_b0034_dir, 'https://github.com/Gonza10V')
        j23100_b0034_ac = [top_level for top_level in j23100_b0034_doc if type(top_level)==sbol3.Component][0]
        j23100_b0034_ac_seq_str = j23100_b0034_ac.sequences[0].lookup().elements
        sfgfp_doc = convert_from_genbank(sfgfp_dir, 'https://github.com/Gonza10V')
        sfgfp_ce = [top_level for top_level in sfgfp_doc if type(top_level)==sbol3.Component][0]
        sfgfp_ce_seq_str = sfgfp_ce.sequences[0].lookup().elements
        b0015_doc = convert_from_genbank(b0015_dir, 'https://github.com/Gonza10V')
        b0015_ef = [top_level for top_level in b0015_doc if type(top_level)==sbol3.Component][0]
        b0015_ef_seq_str = b0015_ef.sequences[0].lookup().elements
        j23100_b0034_ac_in_bb, j23100_b0034_ac_in_bb_seq = part_in_backbone_from_sbol('j23100_b0034_ac_in_bb', j23100_b0034_ac, [476,545], [sbol3.SO_PROMOTER, sbol3.SO_RBS], 4, False, name='j23100_b0034_ac_in_bb')
        doc.add([j23100_b0034_ac_in_bb, j23100_b0034_ac_in_bb_seq])
        sfgfp_ce_in_bb, sfgfp_ce_in_bb_seq = part_in_backbone_from_sbol('sfgfp_ce_in_bb', sfgfp_ce, [130,854], [sbol3.SO_CDS], 4, False, name='sfgfp_ce_in_bb')
        doc.add([sfgfp_ce_in_bb, sfgfp_ce_in_bb_seq])
        b0015_ef_in_bb, b0015_ef_in_bb_seq = part_in_backbone_from_sbol('b0015_ef_in_bb', b0015_ef, [518,646], [sbol3.SO_TERMINATOR], 4, False, name='b0015_ef_in_bb')
        doc.add([b0015_ef_in_bb, b0015_ef_in_bb_seq])
        #Assembly plan
        test_assembly_plan = Assembly_plan_composite_in_backbone_single_enzyme( 
                            name='constitutive_gfp_tu',
                            parts_in_backbone=[j23100_b0034_ac_in_bb, sfgfp_ce_in_bb, b0015_ef_in_bb], 
                            acceptor_backbone=podd_backbone,
                            restriction_enzyme=bsai,
                            document=doc)
        test_assembly_plan.run()
        #Check assembly plan
        expected_assembled_j23100_b0034_ac_seq_str = j23100_b0034_ac_seq_str[475:545]
        assembled_j23100_b0034_ac_seq_str = test_assembly_plan.extracted_parts[0].sequences[0].lookup().elements
        assert expected_assembled_j23100_b0034_ac_seq_str==assembled_j23100_b0034_ac_seq_str, 'Constructor Error: First extracted part sequence does not match expected sequence'

        expected_assembled_sfgfp_ce_seq_str = sfgfp_ce_seq_str[129:854]
        assembled_sfgfp_ce_seq_str = test_assembly_plan.extracted_parts[1].sequences[0].lookup().elements
        assert expected_assembled_sfgfp_ce_seq_str==assembled_sfgfp_ce_seq_str, 'Constructor Error: Second extracted part sequence does not match expected sequence'

        expected_assembled_b0015_ef_seq_str = b0015_ef_seq_str[513:650]
        assembled_b0015_ef_seq_str = test_assembly_plan.extracted_parts[2].sequences[0].lookup().elements
        assert expected_assembled_b0015_ef_seq_str==assembled_b0015_ef_seq_str, 'Constructor Error: Third extracted part sequence does not match expected sequence'

        expected_assembled_open_backbone_seq_str = lvl1_pOdd_acceptor_seq[2255:] + lvl1_pOdd_acceptor_seq[:1172]
        assembled_open_backbone_seq_str = test_assembly_plan.extracted_parts[-1].sequences[0].lookup().elements
        assert expected_assembled_open_backbone_seq_str==assembled_open_backbone_seq_str, 'Constructor Error: Last extracted part (open backbone) sequence does not match expected sequence'

        expected_composite_seq_str = expected_assembled_open_backbone_seq_str[:-4] + expected_assembled_j23100_b0034_ac_seq_str[:-4] + expected_assembled_sfgfp_ce_seq_str[:-4] + expected_assembled_b0015_ef_seq_str[:-4]
        assembled_composite_seq_str = test_assembly_plan.composites[0][0].sequences[0].lookup().elements
        assert expected_composite_seq_str==assembled_composite_seq_str, 'Constructor Error: Composite sequence does not match expected sequence'

if __name__ == '__main__':
    unittest.main()
