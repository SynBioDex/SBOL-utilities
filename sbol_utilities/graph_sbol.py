import sbol3
import graphviz
import rdflib
import argparse


def graph_sbol(doc: sbol3.Document, file_format: str = "pdf", view_now: bool = False, outfile:str = "out",
               write_source: bool = False):
    g = doc.graph()
    dot_master = graphviz.Digraph()

    dot = graphviz.Digraph(name='cluster_toplevels')
    for obj in doc.objects:
        dot.graph_attr['style'] = 'invis'

        # Graph TopLevel
        obj_label = _get_node_label(g, obj.identity)
        dot.node('Document')
        dot.node(_strip_scheme(obj.identity))
        dot.edge('Document', _strip_scheme(obj.identity))
    dot_master.subgraph(dot)

    for obj in doc.objects:
        dot = graphviz.Digraph(name='cluster_%s' %_strip_scheme(obj.identity))
        dot.graph_attr['style'] = 'invis'

        # Graph owned objects
        t = _visit_children(obj, [])
        for start_node, edge, end_node in t:
            start_label = _get_node_label(g, start_node)
            end_label = _get_node_label(g, end_node)
            dot.node(_strip_scheme(start_node), label=start_label)
            dot.node(_strip_scheme(end_node), label=end_label)
            dot.edge(_strip_scheme(start_node), _strip_scheme(end_node), label=edge, **composition_relationship)
        dot_master.subgraph(dot)

    for obj in doc.objects:
        # Graph associations
        t = _visit_associations(obj, [])
        for triple in t:
            start_node, edge, end_node = triple
            start_label = _get_node_label(g, start_node)
            end_label = _get_node_label(g, end_node)
            dot_master.node(_strip_scheme(start_node), label=start_label)
            dot_master.node(_strip_scheme(end_node), label=end_label)
            # See https://stackoverflow.com/questions/2499032/subgraph-cluster-ranking-in-dot
            # constraint=false commonly gives unnecessarily convoluted edges.
            # It seems that weight=0 gives better results:
            dot_master.edge(_strip_scheme(start_node), _strip_scheme(end_node), label=edge, weight='0', **association_relationship)
        
    # write the source file, if requested
    if write_source:
        with open(f'{outfile}.dot', 'w') as source_out:
            source_out.write(dot_master.source)
    # finally, lay out and save in the intended format
    dot_master.render(outfile, view=view_now, format=file_format)
 

def _get_node_label(graph, uri):
    label = None
    for name in graph.objects(rdflib.URIRef(uri), rdflib.URIRef('http://sbols.org/v3#name')):
        return name
    for display_id in graph.objects(rdflib.URIRef(uri), rdflib.URIRef('http://sbols.org/v3#displayId')):
        return display_id
    return uri.split('//')[-1]


def _strip_scheme(uri):
    return uri.split('//')[-1]


def _visit_children(obj, triples=[]):
    for property_name, sbol_property in obj.__dict__.items():
        if isinstance(sbol_property, sbol3.ownedobject.OwnedObjectSingletonProperty):
            child = sbol_property.get()
            if child is not None:
                _visit_children(child, triples)
                triples.append((obj.identity, 
                                property_name,
                                child.identity))
        elif isinstance(sbol_property, sbol3.ownedobject.OwnedObjectListProperty):
            for child in sbol_property:
                _visit_children(child, triples)
                triples.append((obj.identity, 
                                property_name, 
                                child.identity))
    return triples


def _visit_associations(obj, triples=[]):
    for property_name, sbol_property in obj.__dict__.items():
        if isinstance(sbol_property, sbol3.refobj_property.ReferencedObjectSingleton):
            referenced_object = sbol_property.get()
            if referenced_object is not None:
                triples.append((obj.identity, 
                                property_name, 
                                referenced_object))
        elif isinstance(sbol_property, sbol3.refobj_property.ReferencedObjectList):
            for referenced_object in sbol_property:
                triples.append((obj.identity, 
                                property_name, 
                                referenced_object))
        elif isinstance(sbol_property, sbol3.ownedobject.OwnedObjectSingletonProperty):
            child = sbol_property.get()
            if child is not None:
                _visit_associations(child, triples)
        elif isinstance(sbol_property, sbol3.ownedobject.OwnedObjectListProperty):
            for child in sbol_property:
                _visit_associations(child, triples)
    return triples


association_relationship = {
        'arrowtail' : 'odiamond',
        'arrowhead' : 'vee',
        'fontname' : 'Bitstream Vera Sans',
        'fontsize' : '8',
        'dir' : 'both'
    } 

composition_relationship = {
        'arrowtail' : 'diamond',
        'arrowhead' : 'vee',
        'fontname' : 'Bitstream Vera Sans',
        'fontsize' : '8',
        'dir' : 'both'
    } 


def main():
    """Read input file into SBOL3 document, then invoke graph_sbol"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        dest="in_file",
        help="Input PAML file",
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="file_format",
        default="pdf",
        help="Final file format to produce graph in",
    )
    parser.add_argument(
        "-v",
        "--view",
        dest="view_now",
        action="store_true",
        help="Open generated file automatically",
    )
    parser.add_argument(
        "-s",
        "--write-source",
        dest="write_source",
        action="store_true",
        help="Write the source .dot file as well as the rendered output",
    )

    # Parse cli args
    args_dict = vars(parser.parse_args())
    doc = sbol3.Document()
    doc.read(args_dict['in_file'])
    outfile: str = args_dict['in_file'].split('.')[0]
    graph_sbol(doc, args_dict['file_format'], view_now=args_dict['view_now'], outfile=outfile,
               write_source=args_dict['write_source'])


if __name__ == "__main__":
    main()
