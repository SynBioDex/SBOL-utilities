import sbol2
import sbol3
import tyto
from sbol_utilities.conversion import convert2to3, convert3to2

sbol3.set_namespace('http://examples.org')

# sbol2.config.Config.setOption(sbol2.config.ConfigOptions.VALIDATE_ONLINE, False)
doc2 = sbol2.Document()

component2 = sbol2.ComponentDefinition('comp_def')

subcomponent2 = sbol2.FunctionalComponent('funct_comp', definition=component2.identity)

interaction2_component = sbol2.ModuleDefinition('mod_def')
interaction2_component.functionalComponents.add(subcomponent2)

doc2.add(interaction2_component)
doc2.add(component2)
doc2.write('doc2.xml')

doc3 = convert2to3(doc2,['http://examples.org'], use_native_converter=True)

doc3.write('doc3.xml')

doc2_roundtrip = convert3to2(doc3, use_native_converter=True)
doc2_roundtrip.write('doc2_roundrip.xml')

