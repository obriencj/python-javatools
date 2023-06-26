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
Utility module for discovering the differences between two directory
trees

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""


from filecmp import dircmp
from fnmatch import fnmatch
from os import makedirs, walk
from os.path import exists, isdir, join, relpath
from shutil import copy


LEFT = "left only"
RIGHT = "right only"
DIFF = "changed"
SAME = "same"
BOTH = SAME  # meh, synonyms


def fnmatches(entry, *pattern_list):
    """
    returns true if entry matches any of the glob patterns, false
    otherwise
    """

    for pattern in pattern_list:
        if pattern and fnmatch(entry, pattern):
            return True
    return False


def makedirsp(dirname):
    """
    create dirname if it doesn't exist
    """

    if dirname and not exists(dirname):
        makedirs(dirname)


def copydir(orig, dest):
    """
    copies directory orig to dest. Returns a list of tuples of
    relative filenames which were copied from orig to dest
    """

    copied = list()

    makedirsp(dest)

    for root, dirs, files in walk(orig):
        for d in dirs:
            # ensure directories exist
            makedirsp(join(dest, d))

        for f in files:
            root_f = join(root, f)
            dest_f = join(dest, relpath(root_f, orig))
            copy(root_f, dest_f)
            copied.append((root_f, dest_f))

    return copied


def compare(left, right):
    """
    generator emiting pairs indicating the contents of the left and
    right directories. The pairs are in the form of (difference,
    filename) where difference is one of the LEFT, RIGHT, DIFF, or
    BOTH constants. This generator recursively walks both trees.
    """

    dc = dircmp(left, right, ignore=[])
    return _gen_from_dircmp(dc, left, right)


def _gen_from_dircmp(dc, lpath, rpath):
    """
    do the work of comparing the dircmp
    """

    left_only = dc.left_only
    left_only.sort()

    for f in left_only:
        fp = join(dc.left, f)
        if isdir(fp):
            for r, _ds, fs in walk(fp):
                r = relpath(r, lpath)
                for f in fs:
                    yield (LEFT, join(r, f))
        else:
            yield (LEFT, relpath(fp, lpath))

    right_only = dc.right_only
    right_only.sort()

    for f in right_only:
        fp = join(dc.right, f)
        if isdir(fp):
            for r, _ds, fs in walk(fp):
                r = relpath(r, rpath)
                for f in fs:
                    yield (RIGHT, join(r, f))
        else:
            yield (RIGHT, relpath(fp, rpath))

    diff_files = dc.diff_files
    diff_files.sort()

    for f in diff_files:
        yield (DIFF, join(relpath(dc.right, rpath), f))

    same_files = dc.same_files
    same_files.sort()

    for f in same_files:
        yield (BOTH, join(relpath(dc.left, lpath), f))

    subdirs = dc.subdirs.values()
    subdirs = sorted(subdirs)
    for sub in subdirs:
        for event in _gen_from_dircmp(sub, lpath, rpath):
            yield event


def collect_compare(left, right):
    """
    returns a tuple of four lists describing the file paths that have
    been (in order) added, removed, altered, or left the same
    """

    return collect_compare_into(left, right, [], [], [], [])


def collect_compare_into(left, right, added, removed, altered, same):
    """
    collect the results of compare into the given lists (or None if
    you do not wish to collect results of that type. Returns a tuple
    of (added, removed, altered, same)
    """

    for event, filename in compare(left, right):
        if event == LEFT:
            group = removed

        elif event == RIGHT:
            group = added

        elif event == DIFF:
            group = altered

        elif event == BOTH:
            group = same

        else:
            assert False

        if group is not None:
            group.append(filename)

    return added, removed, altered, same


class ClosingContext(object):
    # pylint: disable=R0903
    # too few public methods (none)

    """
    A simple context manager which is created with an object instance,
    and will return that instance from __enter__ and call the close
    method on the instance in __exit__
    """


    def __init__(self, managed):
        self.managed = managed


    def __enter__(self):
        return self.managed


    def __exit__(self, exc_type, _exc_val, _exc_tb):
        managed = self.managed
        self.managed = None

        if managed is not None and hasattr(managed, "close"):
            managed.close()

        return exc_type is None


def closing(managed):
    """
    If the managed object already provides its own context management
    via the __enter__ and __exit__ methods, it is returned
    unchanged. However, if the instance does not, a ClosingContext
    will be created to wrap it. When the ClosingContext exits, it will
    call managed.close()
    """

    if managed is None or hasattr(managed, "__enter__"):
        return managed
    else:
        return ClosingContext(managed)


#
# The end.
