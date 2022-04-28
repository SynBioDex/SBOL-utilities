import sbol2
import re

def objectType(class_obj):
        # used to decide the object type in the converter function
        pass

def displayId(class_obj):
    # used to set the object display id in converter function
    pass

def types(class_obj):
    # overwrites standard #DnaRegion biopax where another type is given
    if class_obj.cell_val not in class_obj.obj.types[0] and len(class_obj.obj.types) == 1:
        class_obj.obj.types = class_obj.cell_val

def moduleModuleDefiniton(class_obj):
    module_name_pref = class_obj.obj_uri.split("/")[-1]
    module_name_suf = class_obj.cell_val.split("/")[-1]
    mod1 = sbol2.Module(f"{module_name_pref}_{module_name_suf}")
    mod1.definition = class_obj.cell_val

    class_obj.obj.modules.add(mod1)

def additionalFuncComponent(class_obj):
    fc_name_pref = class_obj.obj_uri.split("/")[-1]
    fc_name_suf = class_obj.cell_val.split("/")[-1]

    fc1 = sbol2.FunctionalComponent(f"{fc_name_pref}_{fc_name_suf}")
    fc1.definition = class_obj.cell_val
    class_obj.obj.functionalComponents.add(fc1)

def definedFunComponent(class_obj):
    if isinstance(class_obj.cell_val, list):
        # pulling the functional component object
        # by the name (hence the split) from the obj_cit
        fcobj = class_obj.obj_dict[class_obj.cell_val[0].split("/")[-1]]['object']
    else:
        # pulling the functional component object
        # by the name (hence the split) from the obj_cit
        fcobj = class_obj.obj_dict[class_obj.cell_val.split("/")[-1]]['object']

    # print(class_obj.obj, fcobj)
    class_obj.obj.functionalComponents.add(fcobj.copy())

def subcomponents(class_obj):
    # if type is compdef do one thing, if combdev do another, else error
    if isinstance(class_obj.obj, sbol2.componentdefinition.ComponentDefinition):
        class_obj.obj.assemblePrimaryStructure(class_obj.cell_val)
        class_obj.obj.compile(assembly_method=None)

    elif isinstance(class_obj.obj, sbol2.combinatorialderivation.CombinatorialDerivation):
        comp_list = class_obj.cell_val
        comp_ind = 0
        variant_comps = {}
        for ind, comp in enumerate(comp_list):
            if "," in comp:
                comp_list[ind] = f'{class_obj.obj.displayId}_subcomponent_{comp_ind}'
                uri = f'{class_obj.obj.displayId}_subcomponent_{comp_ind}'
                sub_comp = sbol2.ComponentDefinition(uri)
                sub_comp.displayId = f'{class_obj.obj.displayId}_subcomponent_{comp_ind}'
                class_obj.doc.add(sub_comp)
                variant_comps[f'subcomponent_{comp_ind}'] = {'object': sub_comp, 'variant_list': comp}
                comp_ind += 1

        template = sbol2.ComponentDefinition(f'{class_obj.obj.displayId}_template')
        template.displayId = f'{class_obj.obj.displayId}_template'
        class_obj.doc.add(template)

        template.assemblePrimaryStructure(comp_list)
        template.compile(assembly_method=None)

        class_obj.obj.masterTemplate = template
        for var in variant_comps:
            var_comp = sbol2.VariableComponent(f'var_{var}')
            var_comp.displayId = f'var_{var}'
            var_comp.variable = variant_comps[var]['object']

            var_list = re.split(",", variant_comps[var]['variant_list'])
            var_list = [f'{sbol2.getHomespace()}{x.strip()}' for x in var_list]
            var_comp.variants = var_list
            class_obj.obj.variableComponents.add(var_comp)

    else:
        raise KeyError(f'The object type "{type(class_obj.obj)}" does not allow subcomponents. (sheet:{class_obj.sheet}, row:{class_obj.sht_row}, col:{class_obj.sht_col})')

def dataSource(class_obj):
    class_obj.obj.wasDerivedFrom = class_obj.cell_val
    if "pubmed.ncbi.nlm.nih.gov/" in class_obj.cell_val:
        if 'obo' not in class_obj.doc_pref_terms:
            class_obj.doc.addNamespace('http://purl.obolibrary.org/obo/', 'obo')
            class_obj.doc_pref_terms.append('obo')

        class_obj.obj.OBI_0001617 = sbol2.TextProperty(class_obj.obj,
                                                        'http://purl.obolibrary.org/obo/OBI_0001617',
                                                        0, 1, [])
        class_obj.obj.OBI_0001617 = class_obj.cell_val.split(".gov/")[1].replace("/", "")

def sequence(class_obj):
    # might need to be careful if the object type is sequence!
    if re.fullmatch(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', class_obj.cell_val):
        # if a url
        class_obj.obj.sequences = class_obj.cell_val

    elif re.match(r'^[a-zA-Z \s*]+$', class_obj.cell_val):
        # if a sequence string

        # removes spaces, enters, and makes all lower case
        class_obj.cell_val = "".join(class_obj.cell_val.split())
        class_obj.cell_val = class_obj.cell_val.replace(u"\ufeff", "").lower()

        # create sequence object
        sequence = sbol2.Sequence(f"{class_obj.obj.displayId}_sequence",
                                    class_obj.cell_val, sbol2.SBOL_ENCODING_IUPAC)
        if class_obj.obj.name is not None:
            sequence.name = f"{class_obj.obj.name} Sequence"

        class_obj.doc.addSequence(sequence)

        # link sequence object to component definition
        class_obj.obj.sequences = sequence

    else:
        raise ValueError(f'The cell value for {class_obj.obj.identity} is not an accepted sequence type, please use a sequence string or uri instead. Sequence value provided: {class_obj.cell_val} (sheet:{class_obj.sheet}, row:{class_obj.sht_row}, col:{class_obj.sht_col})')
