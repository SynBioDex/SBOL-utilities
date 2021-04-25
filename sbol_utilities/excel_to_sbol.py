import unicodedata

import sbol3
import openpyxl
import tyto
import warnings
import argparse
import logging
import re

###############################################################
# Utilities

type_to_standard_extension = { # pySBOL3/issues/244
    sbol3.SORTED_NTRIPLES: '.nt',
    sbol3.NTRIPLES: '.nt',
    sbol3.JSONLD: '.json',
    sbol3.RDF_XML: '.xml',
    sbol3.TURTLE: '.ttl'
}


def string_to_display_id(name):
    display_id = name.strip().replace(" ","_").replace("-","_") # display id is name processed to comply with rules
    if display_id[0].isdigit(): display_id = "_"+display_id
    return display_id


def basic_sheet(wb: openpyxl.Workbook):
    return wb['Basic Parts']


def composite_sheet(wb: openpyxl.Workbook):
    return wb['Basic Parts']

###############################################################
# Metadata extraction


def read_metadata(wb: openpyxl.Workbook, doc: sbol3.Document):
    # Read the metadata
    wsB = basic_sheet(wb)
    basic_parts_name = wsB['B1'].value
    basic_parts_description = wsB['A11'].value

    wsC = composite_sheet(wb)
    composite_parts_name = wsC['B1'].value
    composite_parts_description = wsC['A11'].value

    # Make the collections
    basic_parts = sbol3.Collection('BasicParts', name = basic_parts_name, description = basic_parts_description)
    doc.add(basic_parts)

    composite_parts = sbol3.Collection('CompositeParts', name = composite_parts_name, description = composite_parts_description)
    doc.add(composite_parts)

    linear_products = sbol3.Collection('LinearDNAProducts', name = 'Linear DNA Products', description = 'Linear DNA constructs to be fabricated')
    doc.add(linear_products)

    final_products = sbol3.Collection('FinalProducts', name = 'Final Products', description = 'Final products desired for actual fabrication')
    doc.add(final_products)

    # return the set of created collections
    return basic_parts, composite_parts, linear_products, final_products


###############################################################
# Read a row for a basic part and turn it into SBOL


def row_to_basic_part(row, basic_parts, linear_products, final_products):
    # Parse material from sheet row
    name = row[0].value
    if name is None:
        return  # skip lines without names
    display_id = string_to_display_id(name)
    try:
        raw_role = row[1].value  # try to look up with tyto; if fail, leave blank or add to description
        role = (tyto.SO.get_uri_by_term(raw_role) if raw_role else None)
    except LookupError:
        role = None
    design_notes = (row[2].value if row[2].value else "")
    description = (row[4].value if row[4].value else "")
    final_product = row[9].value # boolean
    circular = row[10].value # boolean
    length = row[11].value
    raw_sequence = row[12].value
    sequence = (None if raw_sequence is None else "".join(unicodedata.normalize("NFKD", raw_sequence).upper().split()))
    assert (sequence is None and length==0) or len(sequence)==length, \
        'Part "'+name+'" has a mismatched sequence length: check for bad characters and extra whitespace'

    # build a component from the material
    logging.debug('Creating basic part "'+name+'"')
    component = sbol3.Component(display_id, sbol3.SBO_DNA)
    doc.add(component)
    component.name = name
    component.description = (design_notes+"\n"+description).strip()
    if role: component.roles.append(role)
    if circular: component.types.append(sbol3.SO_CIRCULAR)
    if sequence:
        sbol_seq = sbol3.Sequence(display_id+"_sequence")
        sbol_seq.encoding = 'https://identifiers.org/edam:format_1207'  ### BUG: pySBOL #185
        sbol_seq.elements = sequence
        doc.add(sbol_seq)
        component.sequences.append(sbol_seq.identity)

    # add the component to the appropriate collections
    basic_parts.members.append(component.identity)
    if final_product:
        linear_products.members.append(component.identity)
        final_products.members.append(component.identity)


##########################################
# Functions for parsing sub-components
# form of a sub-component:
# X: identifies a component or set thereof
# RC(X): X is reversed
reverse_complement_pattern = re.compile('RC\(.+\)')
# Returns sanitized text without optional reverse complement marker
def strip_RC(name):
    sanitized = name.strip()
    match = reverse_complement_pattern.match(sanitized)
    return (sanitized[3:-1] if (match and len(match.group())==len(sanitized)) else sanitized)
# returns true if part is reverse complement
def is_RC(name):
    sanitized = name.strip()
    return len(strip_RC(sanitized))<len(sanitized)
# returns a list of part names
def part_names(specification):
    return strip_RC(specification).split(',')
# list all the parts in the row that aren't fully resolved
def unresolved_subparts(row):
    return [name for spec in part_specifications(row) for name in part_names(spec) if not doc.find(string_to_display_id(name))]
# get the part specifications until they stop
def part_specifications(row):
    return (cell.value for cell in row[7:] if cell.value)

###############################################################
# Functions for making composites, combinatorials, and libraries

def make_composite_component(display_id,part_lists,reverse_complements):
    # Make the composite as an engineered region
    composite_part = sbol3.Component(display_id, sbol3.SBO_DNA)
    composite_part.roles.append(sbol3.SO_ENGINEERED_REGION)
    # for each part, make a SubComponent and link them together in sequence
    last_sub = None
    for part_list,rc in zip(part_lists,reverse_complements):
        assert len(part_list)==1
        sub = sbol3.SubComponent(part_list[0])
        sub.orientation = (sbol3.SBOL_REVERSE_COMPLEMENT if rc else sbol3.SBOL_INLINE)
        composite_part.features.append(sub)
        if last_sub: composite_part.constraints.append(sbol3.Constraint(sbol3.SBOL_MEETS,last_sub,sub))
        last_sub = sub
    # return the completed part
    return composite_part

constraint_pattern = re.compile('Part (\d+) (.+) Part (\d+)')
constraint_dict = {'same as':sbol3.SBOL_VERIFY_IDENTICAL,
                   'different from':sbol3.SBOL_DIFFERENT_FROM,
                   'same orientation as':sbol3.SBOL_SAME_ORIENTATION_AS,
                   'different orientation from':sbol3.SBOL_SAME_ORIENTATION_AS}
def make_constraint(constraint, part_list):
    m = constraint_pattern.match(constraint)
    assert m, ValueError("Constraint '"+constraint+"' does not match pattern 'Part X relation Part Y'")
    try: restriction = constraint_dict[m.group(2)]
    except KeyError: raise ValueError("Do not recognize constraint relation '"+restriction+"'")
    x = int(m.group(1))
    y = int(m.group(3))
    assert x is not y, ValueError("A part cannot constrain itself: "+constraint)
    for n in [x,y]:
       assert n>0 and n<=len(part_list), ValueError("Part number "+str(n)+" is not between 1 and "+str(len(part_list)))
    return sbol3.Constraint(restriction, part_list[x-1], part_list[y-1])


def make_combinatorial_derivation(document, display_id,part_lists,reverse_complements,constraints):
    # Make the combinatorial derivation and its template
    template = sbol3.Component(display_id + "_template", sbol3.SBO_DNA)
    document.add(template)
    cd = sbol3.CombinatorialDerivation(display_id, template)
    cd.strategy = sbol3.SBOL_ENUMERATE
    # for each part, make a SubComponent or LocalSubComponent in the template and link them together in sequence
    template_part_list = []
    for part_list,rc in zip(part_lists,reverse_complements):
        # it's a variable if there are multiple values or if there's a single value that's a combinatorial derivation
        if len(part_list)>1 or not isinstance(part_list[0],sbol3.Component):
            sub = sbol3.LocalSubComponent({sbol3.SBO_DNA}) # make a template variable
            sub.name = "Part "+str(len(template_part_list)+1)
            template.features.append(sub)
            var = sbol3.VariableFeature(cardinality=sbol3.SBOL_ONE, variable=sub)
            cd.variable_features.append(var)
            # add all of the parts as variables
            for part in part_list:
                if isinstance(part,sbol3.Component): var.variants.append(part)
                elif isinstance(part,sbol3.CombinatorialDerivation): var.variant_derivations.append(part)
                else: raise ValueError("Don't know how to make library element for "+part.name+", a "+print(part))
        else: # otherwise it's a fixed element of the template
            sub = sbol3.SubComponent(part_list[0])
            template.features.append(sub)
        # in either case, orient and order the template elements
        sub.orientation = (sbol3.SBOL_REVERSE_COMPLEMENT if rc else sbol3.SBOL_INLINE)
        if template_part_list: template.constraints.append(sbol3.Constraint(sbol3.SBOL_MEETS,template_part_list[-1],sub))
        template_part_list.append(sub)
    # next, add all of the constraints to the template
    #template.constraints = (make_constraint(c.strip(),template_part_list) for c in (constraints.split(',') if constraints else [])) # impacted by pySBOL3 appending
    c_list = (make_constraint(c.strip(),template_part_list) for c in (constraints.split(',') if constraints else []))
    for c in c_list: template.constraints.append(c)
    # return the completed part
    return cd


def make_composite_part(document, row, composite_parts, linear_products, final_products):
    # Parse material from sheet row
    name = row[0].value
    display_id = string_to_display_id(name)
    design_notes = (row[1].value if row[1].value else "")
    description = (row[2].value if row[2].value else "")
    final_product = row[3].value # boolean
    transformed_strain = row[4].value
    backbone_or_locus = row[5].value
    constraints = row[6].value
    reverse_complements = [is_RC(spec) for spec in part_specifications(row)]
    part_lists = [[document.find(string_to_display_id(name)) for name in part_names(spec)] for spec in part_specifications(row)]
    combinatorial = any(x for x in part_lists if len(x)>1 or isinstance(x[0],sbol3.CombinatorialDerivation))
    # Build the composite
    logging.debug("Creating "+("library" if combinatorial else "composite part")+' "'+name+'"')
    linear_dna_display_id = (display_id + "_ins" if backbone_or_locus else display_id)
    if combinatorial:
        composite_part = make_combinatorial_derivation(document,linear_dna_display_id,part_lists,reverse_complements,constraints)
    else:
        composite_part = make_composite_component(linear_dna_display_id,part_lists,reverse_complements)
    composite_part.name = name
    composite_part.description = (design_notes+"\n"+description).strip()
    # add the component to the appropriate collections
    doc.add(composite_part)
    composite_parts.members.append(composite_part.identity)
    if final_product: linear_products.members.append(composite_part.identity)
    ###############
    # Consider strain and locus information
    if transformed_strain: warnings.warn("Not yet handling strain information: "+transformed_strain)
    if backbone_or_locus:
        #warnings.warn("Assuming plasmid backbone, not locus: "+backbone_or_locus)
        backbone = document.find(string_to_display_id(backbone_or_locus))
        assert backbone, ValueError("Couldn't find specified backbone '"+backbone_or_locus+"'")
        assert tyto.SO.get_uri_by_term('plasmid') in backbone.roles, ValueError("Specified backbone '"+backbone_or_locus+"' is not a plasmid")
        if combinatorial:
            logging.debug("Embedding library '" + composite_part.name + "' in plasmid backbone '" + backbone_or_locus + "'")
            plasmid = sbol3.Component(display_id + "_template", sbol3.SBO_DNA)
            document.add(plasmid)
            part_sub = sbol3.LocalSubComponent({sbol3.SBO_DNA})
            part_sub.name = "Inserted Construct"
            plasmid.features.append(part_sub)
            plasmid_cd = sbol3.CombinatorialDerivation(display_id, plasmid)
            document.add(plasmid_cd)
            part_var = sbol3.VariableFeature(cardinality=sbol3.SBOL_ONE, variable=part_sub)
            plasmid_cd.variable_features.append(part_var)
            part_var.variant_derivations.append(composite_part)
            if final_product: final_products.members.append(plasmid_cd)
        else:
            logging.debug("Embedding part '" + composite_part.name + "' in plasmid backbone '" + backbone_or_locus + "'")
            plasmid = sbol3.Component(display_id,sbol3.SBO_DNA)
            document.add(plasmid)
            part_sub = sbol3.SubComponent(composite_part)
            plasmid.features.append(part_sub)
            if final_product: final_products.members += {plasmid}
        backbone_sub = sbol3.SubComponent(backbone)
        plasmid.features.append(backbone_sub)
        plasmid.constraints.append(sbol3.Constraint(sbol3.SBOL_MEETS,part_sub,backbone_sub))
        plasmid.constraints.append(sbol3.Constraint(sbol3.SBOL_MEETS,backbone_sub,part_sub))



###############################################################
# Entry-point method: given an openpyxl pointer to an Excel file, return an Excel doc file

def excel_to_sbol(excel_wb, output_file='out', file_type='sorted-nt'):
    doc = sbol3.Document()

    logging.info('Reading metadata for collections')
    basic_parts, composite_parts, linear_products, final_products = read_metadata(wb, doc)

    logging.info('Reading basic parts')
    for row in basic_sheet(wb).iter_rows(min_row=20):
        row_to_basic_part(row, basic_parts, linear_products, final_products)
    logging.info('Created ' + str(len(basic_parts.members)) + ' basic parts')

    logging.info('Reading composite parts and libraries')
    # first collect all rows with names
    pending_parts = {row for row in composite_sheet(wb).iter_rows(min_row=24) if row[0].value}
    while pending_parts:
        ready = {row for row in pending_parts if not unresolved_subparts(row)}
        if not ready: raise ValueError("Could not resolve subparts" + ''.join(
            ("\n in '" + row[0].value + "':" + ''.join(" '" + x + "'" for x in unresolved_subparts(row))) for row in
            pending_parts))
        for row in ready:
            make_composite_part(doc, row, composite_parts, linear_products, final_products)
        pending_parts -= ready
    logging.info('Created ' + str(len(composite_parts.members)) + ' composite parts or libraries')

    logging.info('Created SBOL document with '+str(len(basic_parts.members))+' basic parts and '+str(len(composite_parts.members))+' composite parts or libraries')
    report = doc.validate()
    logging.info('Validation of document found ' + str(len(report.errors)) + ' errors and ' + str(len(report.warnings)) + ' warnings')
    return doc


###############################################################
# Main wrapper: read from input file, invoke excel_to_sbol, then write to output file

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('excel_file',help="Excel file used as input")
    parser.add_argument('-n','--namespace',dest='namespace',
                        help="Namespace for Components in output file")
    parser.add_argument('-o','--output',dest='output_file', default='out',
                        help="Name of SBOL file to be written")
    parser.add_argument('-t','--file-type',dest='file_type', default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('-v','--verbose',dest='verbose',action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=(logging.WARN if verbosity==0 else logging.INFO if verbosity==1 else logging.DEBUG))
    output_file = args_dict['output_file']
    file_type = args_dict['file_type']
    excel_file = args_dict['excel_file']
    sbol3.set_namespace(args_dict['namespace'])

    # Read file, convert, and write resulting document
    logging.info('Accessing Excel file '+excel_file)
    wb = openpyxl.load_workbook(excel_file, data_only=True)
    doc = excel_to_sbol(wb)
    outfile_name = output_file+type_to_standard_extension[file_type]
    doc.write(outfile_name,file_type)
    logging.info('SBOL file written to '+outfile_name)
