"""

author: Christopher O'Brien  <obriencj@gmail.com>

"""



LEFT = "left only"
RIGHT = "right only"
DIFF = "changed"
SAME = "same"
BOTH = SAME # meh, synonyms




def fnmatches(entry, *pattern_list):
    from fnmatch import fnmatch
    for pattern in pattern_list:
        if pattern and fnmatch(entry, pattern):
            return True
    return False



def compare(left, right):

    """ generator emiting pairs indicating the contents of the left
    and right directories. The pairs are in the form of (difference,
    filename) where difference is one of the LEFT, RIGHT, DIFF, or
    BOTH constants. This generator recursively walks both trees."""

    from filecmp import dircmp
    
    dc = dircmp(left, right, ignore=[])
    return _gen_from_dircmp(dc, len(left), len(right))
    
    


def _gen_from_dircmp(dc, ltrim, rtrim):
    from os.path import isdir, join
    from os import walk
    
    for f in dc.left_only:
        fp = join(dc.left, f)
        if isdir(fp):
            for r,d,fs in walk(fp):
                r = r[ltrim:]
                for f in fs:
                    print r, f
                    yield(LEFT, join(r, f))
        else:
            yield (LEFT, fp[ltrim:]) #join(dc.left[ltrim:], f))
        
    for f in dc.right_only:
        fp = join(dc.right, f)
        if isdir(fp):
            for r,d,fs in walk(fp):
                r = r[rtrim:]
                for f in fs:
                    print r, f
                    yield(RIGHT, join(r, f))
        else:
            yield (RIGHT, fp[rtrim:]) #join(dc.right[rtrim:], f))

    for f in dc.diff_files:
        yield (DIFF, join(dc.right[rtrim:], f))

    for f in dc.same_files:
        yield (BOTH, join(dc.left[ltrim:], f))

    for sub in dc.subdirs.values():
        for event in _gen_from_dircmp(sub, ltrim, rtrim):
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
