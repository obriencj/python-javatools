"""

author: Christopher O'Brien  <cobrien@redhat.com>

"""



from dirdelta import LEFT, RIGHT, DIFF, BOTH



def compare(left, right, lprefix=None, rprefix=None):
    from zipfile import ZipFile
    return compare_zips(ZipFile(left, 'r'), ZipFile(right, 'r'),
                        lprefix=lprefix, rprefix=rprefix)



def compare_zips(left, right, lprefix=None, rprefix=None):

    ll, rl = left.namelist(), right.namelist()

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
                yield BOTH, f

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



def _deep_different(left, right, f):

    # TODO: something like extract both, check byte-for-byte. If we're
    # here we know that they're the same length and have the same CRC
    # already, but we ought to be damn sure.

    # and this appears to be the only actual way to do this with the
    # zipfile ZipFile object API. wow.

    return left.read(f) != right.read(f)



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
        elif event == BOTH:
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

