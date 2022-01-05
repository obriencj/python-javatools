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

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""


from os import walk
from os.path import getsize, isdir, isfile, islink, join, relpath
from six import BytesIO
from six.moves import zip_longest
from zipfile import is_zipfile, ZipFile, ZipInfo, _EndRecData
from zlib import crc32

from .dirutils import LEFT, RIGHT, DIFF, SAME, closing


__all__ = (
    "compare", "compare_zips",
    "open_zip", "open_zip_entry",
    "zip_file", "zip_entry_rollup",
    "LEFT", "RIGHT", "DIFF", "SAME", )


try:
    buffer
except NameError:
    buffer = memoryview


_CHUNKSIZE = 2 ** 14


def compare(left, right):
    """
    yields EVENT,ENTRY pairs describing the differences between left
    and right, which are filenames for a pair of zip files
    """

    with open_zip(left) as lz, open_zip(right) as rz:
        return compare_zips(lz, rz)


def compare_zips(left, right):
    """
    yields EVENT,ENTRY pairs describing the differences between left
    and right ZipFile instances
    """

    ll = set(left.namelist())
    rl = set(right.namelist())

    for f in ll:
        if f in rl:
            rl.remove(f)

            if f[-1] == '/':
                # it's a directory entry
                pass

            elif _different(left, right, f):
                yield DIFF, f

            else:
                yield SAME, f

        else:
            yield LEFT, f

    for f in rl:
        yield RIGHT, f


def _different(left, right, f):
    """
    true if entry f is different between left and right ZipFile
    instances
    """

    li = left.getinfo(f)
    ri = right.getinfo(f)

    if (li.file_size == ri.file_size) and (li.CRC == ri.CRC):
        # ok, they seem passibly similar, let's deep check them.
        return _deep_different(left, right, f)

    else:
        # yup, they're different
        return True


def _deep_different(left, right, entry):
    """
    checks that entry is identical between ZipFile instances left and
    right
    """

    left = chunk_zip_entry(left, entry)
    right = chunk_zip_entry(right, entry)

    for ldata, rdata in zip_longest(left, right):
        if ldata != rdata:
            return True
    return False


def collect_compare(left, right):
    """
    collects the differences between left and right, which are
    filenames for valid zip files, into a tuple of lists: added,
    removed, altered, same
    """

    return collect_compare_into(left, right, [], [], [], [])


def collect_compare_into(left, right, added, removed, altered, same):
    """
    collects the differences between left and right, which are
    filenames for valid zip files, into the lists added, removed,
    altered, and same.  Returns a tuple of added, removed, altered,
    same
    """

    with open_zip(left) as lz, open_zip(right) as rz:
        return collect_compare_zips_into(lz, rz,
                                         added, removed,
                                         altered, same)


def collect_compare_zips(left, right):
    """
    collects the differences between left and right ZipFile instances
    into a tuple of lists: added, removed, altered, same
    """

    return collect_compare_zips_into(left, right, [], [], [], [])


def collect_compare_zips_into(left, right, added, removed, altered, same):
    """
    collects the differences between left and right ZipFile instances
    into the lists added, removed, altered, and same.  Returns a tuple
    of added, removed, altered, same
    """

    for event, filename in compare_zips(left, right):
        if event == LEFT:
            group = removed
        elif event == RIGHT:
            group = added
        elif event == DIFF:
            group = altered
        elif event == SAME:
            group = same
        else:
            assert False

        if group is not None:
            group.append(filename)

    return added, removed, altered, same


def is_zipstream(data):
    """
    just like zipfile.is_zipfile, but works upon buffers and streams
    rather than filenames.

    If data supports the read method, it will be treated as a stream
    and read from to test whether it is a valid ZipFile.

    If data also supports the tell and seek methods, it will be
    rewound after being tested.
    """

    if isinstance(data, (str, buffer)):
        data = BytesIO(data)

    if hasattr(data, "read"):
        tell = 0
        if hasattr(data, "tell"):
            tell = data.tell()

        try:
            result = bool(_EndRecData(data))
        except IOError:
            result = False

        if hasattr(data, "seek"):
            data.seek(tell)

    else:
        raise TypeError("requies str, buffer, or stream-like object")

    return result


def file_crc32(filename, chunksize=_CHUNKSIZE):
    """
    calculate the CRC32 of the contents of filename
    """

    check = 0
    with open(filename, 'rb') as fd:
        for data in iter(lambda: fd.read(chunksize), b""):
            check = crc32(data, check)
    return check


def _collect_infos(dirname):

    """ Utility function used by ExplodedZipFile to generate ZipInfo
    entries for all of the files and directories under dirname """

    for r, _ds, fs in walk(dirname):
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
                i.CRC = file_crc32(df)
                yield i.filename, i

            else:
                # TODO: is there any more special treatment?
                pass


class ExplodedZipFile(object):
    """
    A directory wrapped up to look like a ZipFile. It only populates
    the filename, file_size, and CRC fields of the child ZipInfo
    members.
    """

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
        return open(join(self.fn, name), mode)


    def read(self, name):
        with self.open(name) as fd:
            return fd.read()


    def close(self):
        self.members = None


def zip_file(fn, mode="r"):
    """
    returns either a zipfile.ZipFile instance or an ExplodedZipFile
    instance, depending on whether fn is the name of a valid zip file,
    or a directory.
    """

    if isdir(fn):
        return ExplodedZipFile(fn)
    elif is_zipfile(fn):
        return ZipFile(fn, mode)
    else:
        raise Exception("cannot treat as an archive: %r" % fn)


def open_zip(filename, mode="r"):
    """
    opens a zip file archive at filename in the given mode and returns
    a context manager which will close the archive when the context
    exits. Use eg: with open_zip('my.zip') as z: ...

    In Python 2.6, this will be a ClosingContext instance. In 2.7
    onward, the zipfile.ZipFile class provides its own managed context
    and so the instance is returned unwrapped
    """

    return closing(zip_file(filename, mode))


def open_zip_entry(zipfile, name, mode='r'):
    """
    opens an entry from an opened zip file archive in the given mode
    and returns a context manager which will close the stream when the
    context exits. Use eg: with open_zip_entry(my_zip, 'MANIFEST.MF')
    as data: ...

    In Python 2.6, this will be a ClosingContext instance. In 2.7
    onward, the zipfile.ZipExtFile class provides its own managed
    context and so the instance is returned unwrapped
    """

    return closing(zipfile.open(name, mode))


def chunk_zip_entry(zipfile, name, chunksize=_CHUNKSIZE):
    """
    opens an entry from an openex zip file archive and yields
    sequential chunks of data from the resulting stream.
    """

    with open_zip_entry(zipfile, name, mode='r') as stream:
        data = stream.read(chunksize)
        while data:
            yield data
            data = stream.read(chunksize)


def zip_entry_rollup(zipfile):
    """
    returns a tuple of (files, dirs, size_uncompressed,
    size_compressed). files+dirs will equal len(zipfile.infolist)
    """

    files = dirs = 0
    total_c = total_u = 0

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
