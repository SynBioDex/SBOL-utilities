import sbol2
import sbol3
import tyto
from sbol_utilities.conversion import convert2to3, convert3to2

sbol3.set_namespace('http://examples.org')

# sbol2.config.Config.setOption(sbol2.config.ConfigOptions.VALIDATE_ONLINE, False)
doc2 = sbol2.Document()

component2 = sbol2.ComponentDefinition('hello')

subcomponent2 = sbol2.FunctionalComponent('subcomp', definition=component2.identity)

interaction2_component = sbol2.ModuleDefinition('hello2')
interaction2_component.functionalComponents.add(subcomponent2)

participation2 = sbol2.Participation(uri='reactant1', participant=subcomponent2)
participation2.addRole(sbol2.SBO_REACTANT)

interaction2 = sbol2.Interaction(
    'reaction1',
    interaction_type=tyto.SBO.cleavage
)

interaction2.participations.add(participation2)

interaction2_component.interactions.add(interaction2)


doc2.add(interaction2_component)
doc2.add(component2)
doc2.write('doc2.ttl')

doc3 = convert2to3(doc2,['http://examples.org'], use_native_converter=True)

doc3.write('doc3.ttl')

doc2_roundtrip = convert3to2(doc3, use_native_converter=True)
doc2_roundtrip.write('doc2_roundrip.ttl')



# def compare_objects(p1, p2):
#     for k in vars(p1):
#         if k in ['properties', '_properties']:
#             continue
#         if str(getattr(p1, k)) != str(getattr(p2, k)):
#             print('prop:', k)
#             print('original:', getattr(p1, k))
#             print('converted:', getattr(p2, k))
#             print()