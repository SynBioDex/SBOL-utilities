import sbol3
import sbol2
from sbol_utilities.conversion import convert2to3, convert3to2
from sbol3_sbol2_conversion import SBOL2To3ConversionVisitor, SBOL3To2ConversionVisitor
import tyto

sbol3.set_namespace('http://examples.org')

doc3 = sbol3.Document()

component3 = sbol3.Component('component')
subcomponent3 = sbol3.SubComponent(component3)
component3.features.append(subcomponent3)


participation3 = sbol3.Participation(sbol3.SBO_REACTANT, subcomponent3)

interaction3 = sbol3.Interaction(
    tyto.SBO.cleavage,
    participations=[participation3]
)

interaction3_component = sbol3.Component('interaction_component', interactions=[interaction3], types=[tyto.SBO.cleavage])

doc3.add(component3)
doc3.add(interaction3_component)




