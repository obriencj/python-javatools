# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see
# <http://www.gnu.org/licenses/>.



"""
Utilities for discovering entry deltas in a pair of zip files.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



from .dirutils import LEFT, RIGHT, DIFF, SAME



def compare(left, right):
    with open_zip(left) as l, open_zip(right) as r:
        return compare_zips(l, r)



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

    with left.open(f) as lfd, right.open(f) as rfd:
        for l,r in izip_longest(_chunk(lfd), _chunk(rfd)):
            if l != r:
                return True
        return False



def collect_compare(left, right):
    return collect_compare_into(left, right, [], [], [], [])



def collect_compare_into(left, right, added, removed, altered, same):
    with open_zip(left) as l, open_zip(right) as r:
        return collect_compare_zips_into(l, r, added, removed, altered, same)



def collect_compare_zips(left, right):
    return collect_compare_zips_into(left, right, [], [], [], [])



def collect_compare_zips_into(left, right, added, removed, altered, same):
        
    for event,filename in compare_zips(left, right):
        
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
            group.append(filename)

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
            #pylint: disable=W0212
            # unfortunately not otherwise available
            ret = bool(zipfile._EndRecData(f))
        except IOError:
            ret = False

        f.seek(t)

    else:
        raise TypeError("requies filename or stream-like object")

    return ret



def is_exploded(f):
    import os.path
    return os.path.isdir(f)



def _crc32(fname):
    import zlib

    with open(fname, 'rb') as fd:
        c = 0
        for chunk in _chunk(fd):
            c = zlib.crc32(chunk, c)
    return c



def _collect_infos(dirname):

    from zipfile import ZipInfo
    from os.path import relpath, join, getsize, islink, isfile
    from os import walk

    for r, _, fs in walk(dirname):
        if not islink(r) and r != dirname:
            i = ZipInfo()
            i.filename = join(relpath(r, dirname), "")
            i.file_size = 0
            i.compress_size = 0
            i.CRC = 0
            yield i.filename, i

        for f in fs:
            df = join(r, f)
            relfn = relpath(join(r, f), dirname)

            if islink(df):
                pass
                
            elif isfile(df):
                i = ZipInfo()
                i.filename = relfn
                i.file_size = getsize(df)
                i.compress_size = i.file_size
                i.CRC = _crc32(df)
                yield i.filename, i
            
            else:
                # TODO: is there any more special treatment?
                pass



class ExplodedZipFile(object):

    """ A directory wrapped up to look like a ZipFile. It only
    populates the filename, file_size, and CRC fields of the child
    ZipInfo members."""

    def __init__(self, pathname):
        self.fn = pathname
        self.filename = pathname
        self.members = None
        self.refresh()


    def refresh(self):
        self.members = dict(_collect_infos(self.fn))
        

    def getinfo(self, name):
        return self.members.get(name)


    def namelist(self):
        return sorted(self.members.keys())


    def infolist(self):
        return self.members.values()


    def open(self, name, mode='rb'):
        from os.path import join
        return open(join(self.fn, name), mode)


    def read(self, name):
        with self.open(name) as fd:
            return fd.read()


    def close(self):
        self.members = None



class ZipFileContext(object):

    """ A context manager for ZipFile instances. Creates an internal
    ZipFile, and closes it when the context exits. """

    def __init__(self, filename, mode="r"):
        self.fn = filename
        self.zf = None
        self.mode = mode

    def __enter__(self):
        self.zf = zip_file(self.fn, self.mode)
        return self.zf

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zf:
            self.zf.close()
            self.zf = None
        return (exc_type is None)



def zip_file(fn, mode="r"):

    """ returns either a zipfile.ZipFile instance, or an
    ExplodedZipFile instance, depending on whether fn is the name of a
    valid zip file, or a directory. """
    
    import zipfile
    
    if is_exploded(fn):
        return ExplodedZipFile(fn)
    elif is_zipfile(fn):
        return zipfile.ZipFile(fn, mode)
    else:
        raise Exception("cannot treat as an archive: %r" % fn)



def open_zip(filename, mode="r"):
    
    """ returns a ZipFileContext which will manage closing the zip for
    you. Use eg: with open_zip('my.zip') as z: ... """

    return ZipFileContext(filename, mode)



def zip_entry_rollup(zipfile):
    
    """ returns a tuple of (files, dirs, size_uncompressed,
    size_compressed). files+dirs will equal len(zipfile.infolist) """
    
    files, dirs = 0, 0
    total_c, total_u = 0, 0
    
    for i in zipfile.infolist():
        if i.filename[-1] == '/':
            # I wonder if there's a better detection method than this
            dirs += 1
        else:
            files += 1
            total_c += i.compress_size
            total_u += i.file_size
    
    return files, dirs, total_c, total_u
    


#
# The end.

