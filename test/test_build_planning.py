import unittest

import sbol3
import tyto
from typing import Optional

from sbol_utilities.build_planning import validate_composite_part_assemblies, SBOL_ASSEMBLY_PLAN


class TestBuildPlanning(unittest.TestCase):

	def test_validate_composite_part_assemblies(self):
		test_doc = sbol3.Document()

		sbol3.set_namespace('http://testBuildPlanning.org')

		assert validate_composite_part_assemblies(assemble_BBa_K093005(test_doc))

		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'BBa_E1010_UNASSEMBLED'))
		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'BBa_K093005_UNASSEMBLED'))
		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'BBa_E1010_UNCONTAINED'))
		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'BBa_E1010_NOT_INSERT'))
		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'pSB1C3_NOT_BACKBONE'))
		assert not validate_composite_part_assemblies(assemble_BBa_K093005(test_doc, 'EXTRA_ASSEMBLY_COMPONENT'))

def assemble_BBa_K093005(doc: sbol3.Document, failure_mode: Optional[str] = ''):
	doc = sbol3.Document()

	sbol3.set_namespace('http://test_build_planning.org')

	# Create assembled parts BBa_B0034 and BBa_E1010

	assembled_rbs = sbol3.Component('BBa_B0034', sbol3.SBO_DNA, roles=[tyto.SO.ribosome_entry_site])
	assembled_cds = sbol3.Component('BBa_E1010', sbol3.SBO_DNA, roles=[tyto.SO.CDS])

	doc.add(assembled_rbs)
	doc.add(assembled_cds)

	# Create composite part BBa_K093005

	composite_part = sbol3.Component('BBa_K093005', sbol3.SBO_DNA, roles=[tyto.SO.engineered_region])

	composite_part_sc1 = sbol3.SubComponent(assembled_rbs)
	composite_part_sc2 = sbol3.SubComponent(assembled_cds)

	composite_part.features += [composite_part_sc1]
	composite_part.features += [composite_part_sc2]

	doc.add(composite_part)

	# Create backbone pSB1C3

	backbone = sbol3.Component('pSB1C3', [sbol3.SBO_DNA, tyto.SO.circular],
	                           roles=[tyto.SO.plasmid_vector])

	doc.add(backbone)

	# Create part in backbone for BBa_B0034 in pSB1C3

	rbs_in_backbone = sbol3.Component('BBa_B0034_in_pSB1C3', [sbol3.SBO_DNA, tyto.SO.circular],
	                                  roles=[tyto.SO.plasmid_vector])

	pib1_sc1 = sbol3.SubComponent(assembled_rbs, roles=[tyto.SO.engineered_insert])
	rbs_in_backbone.features += [pib1_sc1]
	pib1_sc2 = sbol3.SubComponent(backbone)
	rbs_in_backbone.features += [pib1_sc2]

	doc.add(rbs_in_backbone)

	# Create part in backbone for BBa_E1010 in pSB1C3

	cds_in_backbone = sbol3.Component('BBa_E1010_in_pSB1C3', [sbol3.SBO_DNA, tyto.SO.circular],
	                                  roles=[tyto.SO.plasmid_vector])

	if failure_mode != 'BBa_E1010_NOT_INSERT':
		pib2_sc1 = sbol3.SubComponent(assembled_cds, roles=[tyto.SO.engineered_insert])
		cds_in_backbone.features += [pib2_sc1]

	if failure_mode != 'pSB1C3_NOT_BACKBONE':
		pib2_sc2 = sbol3.SubComponent(backbone)
		cds_in_backbone.features += [pib2_sc2]

	doc.add(cds_in_backbone)

	# Create part in backbone for BBa_K093005 in pSB1C3

	gene_in_backbone = sbol3.Component('BBa_K093005_in_pSB1C3', [sbol3.SBO_DNA, tyto.SO.circular],
	                                      roles=[tyto.SO.plasmid_vector])

	pib3_sc1 = sbol3.SubComponent(composite_part, roles=[tyto.SO.engineered_insert])
	gene_in_backbone.features += [pib3_sc1]

	pib3_sc2 = sbol3.SubComponent(backbone)
	gene_in_backbone.features += [pib3_sc2]

	doc.add(gene_in_backbone)

	# Create component for assembly of BBa_K093005

	assembly_comp = sbol3.Component('BBa_K093005_assembly', tyto.SBO.functional_entity)

	assembly_comp_sc1 = sbol3.SubComponent(assembled_rbs)
	assembly_comp.features += [assembly_comp_sc1]
	if failure_mode != 'BBa_E1010_UNASSEMBLED':
		assembly_comp_sc2 = sbol3.SubComponent(assembled_cds)
		assembly_comp.features += [assembly_comp_sc2]
	if failure_mode != 'BBa_K093005_UNASSEMBLED':
		assembly_comp_sc3 = sbol3.SubComponent(composite_part)
		assembly_comp.features += [assembly_comp_sc3]
	assembly_comp_sc4 = sbol3.SubComponent(rbs_in_backbone)
	assembly_comp.features += [assembly_comp_sc4]
	assembly_comp_sc5 = sbol3.SubComponent(cds_in_backbone)
	assembly_comp.features += [assembly_comp_sc5]
	assembly_comp_sc6 = sbol3.SubComponent(gene_in_backbone)
	assembly_comp.features += [assembly_comp_sc6]

	pib_contains_rbs = sbol3.Constraint(sbol3.SBOL_CONTAINS, assembly_comp_sc4, assembly_comp_sc1)
	assembly_comp.constraints += [pib_contains_rbs]

	if failure_mode != 'BBa_E1010_UNCONTAINED' and failure_mode != 'BBa_E1010_UNASSEMBLED':
		pib_contains_cds = sbol3.Constraint(sbol3.SBOL_CONTAINS, assembly_comp_sc5, assembly_comp_sc2)
		assembly_comp.constraints += [pib_contains_cds]

	if failure_mode != 'BBa_K093005_UNASSEMBLED':
		pib_contains_gene = sbol3.Constraint(sbol3.SBOL_CONTAINS, assembly_comp_sc6, assembly_comp_sc3)
		assembly_comp.constraints += [pib_contains_gene]

	doc.add(assembly_comp)

	# Create activity for assembly of BBa_K093005

	assembly = sbol3.Activity('assemble_BBa_K093005', types=[sbol3.SBOL_DESIGN, SBOL_ASSEMBLY_PLAN])

	assembly_usage = sbol3.Usage(assembly_comp.identity, roles=[sbol3.SBOL_DESIGN])
	assembly.usage += [assembly_usage]

	if failure_mode == 'EXTRA_ASSEMBLY_COMPONENT':
		extra_assembly_comp = sbol3.Component('Extra_BBa_K093005_assembly', tyto.SBO.functional_entity)

		doc.add(extra_assembly_comp)

		extra_assembly_usage = sbol3.Usage(extra_assembly_comp.identity, roles=[sbol3.SBOL_DESIGN])
		assembly.usage += [extra_assembly_usage]

	doc.add(assembly)

	composite_part.generated_by += [assembly.identity]

	return composite_part

if __name__ == '__main__':
    unittest.main()