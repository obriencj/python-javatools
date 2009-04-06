"""

author: Christopher O'Brien  <siege@preoccupied.net>

"""



LEFT = "left only"
RIGHT = "right only"
DIFF = "changed"
BOTH = "same"



def compare(left, right):

    """ generator emiting pairs indicating the contents of the left
    and right directories. The pairs are in the form of (difference,
    filename) where difference is one of the LEFT, RIGHT, DIFF, or
    BOTH constants. This generator recursively walks both trees."""

    from filecmp import dircmp
    
    dc = dircmp(left, right, ignore=[])
    return _gen_from_dircmp(dc)
    


def _gen_from_dircmp(dc):
    from os.path import join 

    for f in dc.left_only:
        yield (LEFT, join(dc.left, f))
        
    for f in dc.right_only:
        yield (RIGHT, join(dc.right, f))

    for f in dc.diff_files:
        yield (DIFF, join(dc.right, f))

    for f in dc.same_files:
        yield (BOTH, join(dc.left, f))

    for sub in dc.subdirs.values():
        for event in _gen_from_dircmp(sub):
            yield event



def collect_compare(left, right):
    return collect_compare_into(left, right, [], [], [], [])



def collect_compare_into(left, right, added, removed, altered, same):

    for event,file in compare(left, right):
        
        if event == LEFT:
            group = removed
        elif event == RIGHT:
            group = added
        elif event == DIFF:
            group = altered
        elif event == BOTH:
            group = same
        else:
            assert(False)

        if group is not None:
            group.append(file)

    return added,removed,altered,same



#
# The end.
