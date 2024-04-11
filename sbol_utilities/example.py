import sbol3
import sbol2
from sbol_utilities.conversion import convert2to3, convert3to2
import tyto
from sbol3_sbol2_conversion import SBOL2To3ConversionVisitor, SBOL3To2ConversionVisitor
from pprint import pprint

sbol3.set_namespace('http://examples.org')

dummy_doc2 = sbol2.Document()
dummy_doc3 = sbol3.Document()

component3 = sbol3.Component('component', sbol3.SBO_DNA)
subcomponent3 = sbol3.SubComponent(component3)
component3.features.append(subcomponent3)

component2 = sbol2.ComponentDefinition('component', sbol3.SBO_DNA)
subcomponent2 = sbol2.Component(definition=component2.identity)
component2.components.add(subcomponent2)

participation3 = sbol3.Participation(sbol3.SBO_REACTANT, subcomponent3)
participation2 = sbol2.Participation(participant=subcomponent2)
participation2.addRole(sbol2.SBO_REACTANT)

converter3to2 = SBOL3To2ConversionVisitor(dummy_doc3)
participation2_converted = converter3to2.visit_participation(participation3)
converter2to3 = SBOL2To3ConversionVisitor(dummy_doc2, None)
participation3_converted = converter2to3.visit_participation(participation2)

print(participation3.participant)
print(participation3_converted.participant)
print(getattr(participation3_converted, 'participant'))


def compare_participations(p1, p2):
    for k in vars(p1):
        if k in ['properties', '_properties']:
            continue
        if str(getattr(p1, k)) != str(getattr(p2, k)):
            print('prop:', k)
            print('original:', getattr(p1, k))
            print('converted:', getattr(p2, k))
            print()


print('## Participation 2')
compare_participations(participation2, participation2_converted)

print('## Participation 3')
compare_participations(participation3, participation3_converted)

