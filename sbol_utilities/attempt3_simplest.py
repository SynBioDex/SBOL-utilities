import sbol3
import sbol2
from sbol_utilities.conversion import convert2to3, convert3to2
from sbol3_sbol2_conversion import SBOL2To3ConversionVisitor, SBOL3To2ConversionVisitor
import tyto

sbol3.set_namespace('http://examples.org')

doc3 = sbol3.Document()

component3 = sbol3.Component('comp_def', types=[sbol3.SBO_DNA])
subcomponent3 = sbol3.SubComponent(component3)

interaction3_component = sbol3.Component('mod_def', types=[sbol3.SBO_BIOCHEMICAL_REACTION])
interaction3_component.features.append(subcomponent3)

doc3.add(component3)
doc3.add(interaction3_component)
doc3.write('doc3_simplest.xml')





