"""

author: Christopher O'Brien  <cobrien@redhat.com>

"""



from dirdelta import LEFT, RIGHT, DIFF, SAME



def compare(left, right, lprefix=None, rprefix=None):
    from zipfile import ZipFile
    return compare_zips(ZipFile(left, 'r'), ZipFile(right, 'r'),
                        lprefix=lprefix, rprefix=rprefix)



def compare_zips(left, right, lprefix=None, rprefix=None):

    ll, rl = set(left.namelist()), set(right.namelist())

    if lprefix or rprefix:
        # TODO: implement prefix skipping
        pass

    for f in ll:
        if f in rl:
            rl.remove(f)

            if _directory(left, right, f):
                pass

            elif _different(left, right, f):
                yield DIFF, f

            else:
                yield SAME, f

        else:
            yield LEFT, f

    for f in rl:
        yield RIGHT, f



def _directory(left, right, f):
    # the easy way out.
    return (f[-1] == '/')



def _different(left, right, f):
    l, r = left.getinfo(f), right.getinfo(f)

    if (l.file_size == r.file_size) and (l.CRC == r.CRC):
        # ok, they seem passibly similar, let's deep check them.
        return _deep_different(left, right, f)
        
    else:
        # yup, they're different
        return True



def _chunk(stream, size=10240):
    d = stream.read(size)
    while d:
        yield d
        d = stream.read(size)



def _deep_different(left, right, f):
    from itertools import izip_longest
    for l,r in izip_longest(_chunk(left), _chunk(right)):
        if l != r:
            return True
    return False



def collect_compare(left, right):
    return collect_compare_into(left, right, [], [], [], [])



def collect_compare_into(left, right, added, removed, altered, same):
    from zipfile import ZipFile
    lz, rz = ZipFile(left, "r"), ZipFile(right, "r")
    return collect_compare_zips_into(lz, rz, added, removed, altered, same)



def collect_compare_zips(left, right):
    return collect_compare_zips_into(left, right, [], [], [], [])



def collect_compare_zips_into(left, right, added, removed, altered, same):
        
    for event,file in compare_zips(left, right):
        
        if event == LEFT:
            group = removed
        elif event == RIGHT:
            group = added
        elif event == DIFF:
            group = altered
        elif event == SAME:
            group = same
        else:
            assert(False)

        if group is not None:
            group.append(file)

    return added,removed,altered,same



def is_zipfile(f):

    """ just like zipfile.is_zipfile, but also works upon file-like
    objects (and not just filenames) """

    import zipfile

    ret = False

    if isinstance(f, str):
        ret = zipfile.is_zipfile(f)

    elif hasattr(f, "read") and hasattr(f, "seek"):
        if hasattr(f, "tell"):
            t = f.tell()
        else:
            t = 0
        try:
            ret = bool(zipfile._EndRecData(f))
        except IOError:
            pass

        f.seek(t)

    else:
        raise TypeError("requies filename or stream-like object")

    return ret



#
# The end.

