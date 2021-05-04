import sbol3
import filecmp
import difflib

#########################
# Collection of shared helper functions for utilities package


# Flatten list of lists into a single list
def flatten(collection):
    return [item for sublist in collection for item in sublist]


#########################
# Kludge materials that should be removed after certain issues are resolved


# Workaround for pySBOL3 issue #231: should be applied to every iteration on a collection of SBOL objects
def id_sort(i: iter):
    sortable = list(i)
    sortable.sort(key=lambda x: x.identity if isinstance(x, sbol3.Identified) else x.lookup().identity)
    return sortable

# Kludges for copying certain types of TopLevel objects
# TODO: delete after resolution of pySBOL issue #235
def copy_toplevel_and_dependencies(target, t):
    if not target.find(t.identity):
        if isinstance(t, sbol3.Collection):
            copy_collection_and_dependencies(target, t)
        elif isinstance(t, sbol3.Component):
            copy_component_and_dependencies(target, t)
        elif isinstance(t, sbol3.Sequence):
            t.copy(target) # no dependencies for Sequence
        else:
            raise ValueError("Not set up to copy dependencies of "+str(t))

def copy_collection_and_dependencies(target, c):
    c.copy(target)
    for m in id_sort(c.members):
        copy_toplevel_and_dependencies(target, m.lookup())

def copy_component_and_dependencies(target, c):
    c.copy(target)
    for f in id_sort(c.features):
        if isinstance(f,sbol3.SubComponent):
            copy_toplevel_and_dependencies(target, f.instance_of.lookup())
    for s in id_sort(c.sequences):
        copy_toplevel_and_dependencies(target, s.lookup())



## Kludge for replacing a feature in a Component
# TODO: delete after resolution of pySBOL issue #207
def replace_feature(component, old, new):
    component.features.remove(old)
    component.features.append(new)
    # should be more thorough, but kludging to just look at constraints
    for ct in id_sort(component.constraints):
        if ct.subject == old.identity: ct.subject = new.identity
        if ct.object == old.identity: ct.object = new.identity


########################
# Used in testing; TODO: figure out how to host it in a test helpers file rather than the package
# check if two files are identical; if not, report their diff
def assert_files_identical(file1, file2):
    if not filecmp.cmp(file1, file2, shallow=False):
        with open(file1, 'r') as f1:
            with open(file2, 'r') as f2:
                diff = difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file1, tofile=file2)
        raise AssertionError("File differs from expected value:\n"+''.join(diff))
