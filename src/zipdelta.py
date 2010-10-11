"""

author: Christopher O'Brien  <cobrien@redhat.com>

"""



from dirdelta import LEFT, RIGHT, DIFF, SAME



def compare(left, right):

    return compare_zips(ZipFile(left), ZipFile(right))



def compare_zips(left, right):

    ll, rl = set(left.namelist()), set(right.namelist())

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
    lfd = left.open(f)
    rfd = right.open(f)

    for l,r in izip_longest(_chunk(lfd), _chunk(rfd)):
        if l != r:
            return True
    return False



def collect_compare(left, right):
    return collect_compare_into(left, right, [], [], [], [])



def collect_compare_into(left, right, added, removed, altered, same):
    lz, rz = ZipFile(left), ZipFile(right)
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



def is_exploded(f):
    import os.path
    return os.path.isdir(f)



def _crc32(fname):
    import zlib

    fd = open(fname, 'rb')
    c = 0
    for chunk in _chunk(fd):
        c = zlib.crc32(chunk, c)
    fd.close()

    return c



def _walk_populate(data, dirname, fnames):

    from zipfile import ZipInfo
    import os.path

    members, skip = data

    # we need to chop off the original dirname, which will be the
    # relative path to the directory of the exploded jar file.
    if not skip:
        skip = len(dirname)
        data[1] = skip
    nicedir = dirname[skip:]
    
    for f in fnames:
        df = os.path.join(dirname, f)

        if os.path.islink(df):
            pass
        
        elif os.path.isdir(df):
            i = ZipInfo()
            i.filename = os.path.join(nicedir, f, "")
            i.file_size = 0
            i.compress_size = 0
            i.CRC = 0
            members[i.filename] = i
                
        elif os.path.isfile(df):
            i = ZipInfo()
            i.filename = os.path.join(nicedir, f)
            i.file_size = os.path.getsize(df)
            i.compress_size = i.file_size
            i.CRC = _crc32(df)
            members[i.filename] = i
            
        else:
            pass



class ExplodedZipFile(object):

    """ A directory wrapped up to look like a ZipFile. It only
    populates the filename, file_size, and CRC fields of the child
    ZipInfo members."""

    def __init__(self, pathname):
        self.fn = pathname
        self.members = None
        self.refresh()


    def refresh(self):
        from os.path import walk
        
        members = {}
        walk(self.fn, _walk_populate, [members, 0])
        self.members = members
        

    def getinfo(self, name):
        return self.members.get(name)


    def namelist(self):
        return sorted(self.members.keys())


    def open(self, name, mode='rb'):
        from os.path import join
        return open(join(self.fn, name), mode)


    def read(self, name):
        fd = self.open(name)
        data = fd.read()
        fd.close()
        return data



def ZipFile(fn):

    """ returns either a zipfile.ZipFile instance, or an
    ExplodedZipFile instance, depending on whether fn is the name of a
    valid zip file, or a directory. """
    
    import zipfile
    
    if is_exploded(fn):
        return ExplodedZipFile(fn)
    elif is_zipfile(fn):
        return zipfile.ZipFile(fn, "r")
    else:
        raise Exception("cannot treat as an archive: %r" % fn)
    


#
# The end.

