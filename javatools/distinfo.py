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
Utility script and module for discovering information about a
distribution of mixed class files and JARs.

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""


from __future__ import print_function


import sys

from json import dump
from argparse import ArgumentParser
from os.path import isdir, join
from shutil import rmtree
from tempfile import mkdtemp

from . import unpack_classfile
from .jarinfo import JarInfo, JAR_PATTERNS, REQ_BY_CLASS, PROV_BY_CLASS
from .dirutils import fnmatches
from .ziputils import open_zip


DIST_JAR = "jar"
DIST_CLASS = "class"

REQ_BY_JAR = "jar.requires"
PROV_BY_JAR = "jar.provides"


class DistInfo(object):


    def __init__(self, base_path):
        self.base_path = base_path

        # a pair of strings useful for later reporting. Non-mandatory
        self.product = None
        self.version = None

        # if the dist is a zip, we'll explode it into tmpdir
        self.tmpdir = None

        self._contents = None
        self._requires = None
        self._provides = None


    def __del__(self):
        self.close()


    def _working_path(self):
        if self.tmpdir:
            return self.tmpdir

        elif isdir(self.base_path):
            return self.base_path

        else:
            self.tmpdir = mkdtemp()
            with open_zip(self.base_path, "r") as zf:
                zf.extractall(path=self.tmpdir)
            return self.tmpdir


    def _collect_requires_provides(self):
        req = {}
        prov = {}

        p = set()

        for entry in self.get_jars():
            ji = self.get_jarinfo(entry)
            for sym, data in ji.get_requires().items():
                req.setdefault(sym, []).append((REQ_BY_JAR, entry, data))
            for sym, data in ji.get_provides().items():
                prov.setdefault(sym, []).append((PROV_BY_JAR, entry, data))
                p.add(sym)
            ji.close()

        for entry in self.get_classes():
            ci = self.get_classinfo(entry)
            for sym in ci.get_requires():
                req.setdefault(sym, []).append((REQ_BY_CLASS, entry))
            for sym in ci.get_provides(private=False):
                prov.setdefault(sym, []).append((PROV_BY_CLASS, entry))
            for sym in ci.get_provides(private=True):
                p.add(sym)

        req = dict((k, v) for k, v in req.items() if k not in p)

        self._requires = req
        self._provides = prov


    def get_requires(self, ignored=tuple()):
        """ a map of requirements to what requires it. ignored is an
        optional list of globbed patterns indicating packages,
        classes, etc that shouldn't be included in the provides map"""

        if self._requires is None:
            self._collect_requires_provides()

        d = self._requires
        if ignored:
            d = dict((k, v) for k, v in d.items()
                     if not fnmatches(k, *ignored))
        return d


    def get_provides(self, ignored=tuple()):
        """ a map of provided classes and class members, and what
        provides them. ignored is an optional list of globbed patterns
        indicating packages, classes, etc that shouldn't be included
        in the provides map"""

        if self._provides is None:
            self._collect_requires_provides()

        d = self._provides
        if ignored:
            d = dict((k, v) for k, v in d.items()
                     if not fnmatches(k, *ignored))
        return d


    def get_jars(self):
        """ sequence of entry names found in this distribution """

        for entry in self.get_contents():
            if fnmatches(entry, *JAR_PATTERNS):
                yield entry


    def get_jarinfo(self, entry):
        return JarInfo(join(self.base_path, entry))


    def get_classes(self):
        """ sequence of entry names found in the distribution.  This
        is only the collection of class files directly in the dist, it
        does not include classes within JARs that are inthe dist."""

        for entry in self.get_contents():
            if fnmatches(entry, "*.class"):
                yield entry


    def get_classinfo(self, entry):
        return unpack_classfile(join(self.base_path, entry))


    def get_contents(self):
        if self._contents is None:
            self._contents = tuple(_collect_dist(self._working_path()))
        return self._contents


    def close(self):
        """ if this was a zip'd distribution, any introspection
        may have resulted in opening or creating temporary files.
        Call close in order to clean up. """

        if self.tmpdir:
            rmtree(self.tmpdir)
            self.tmpdir = None

        self._contents = None


def _collect_dist(pathn):
    from os.path import join, relpath
    from os import walk
    for r, _ds, fs in walk(pathn):
        for f in fs:
            yield relpath(join(r, f), pathn)


# --- CLI ---
#


def cli_dist_provides(options, info):
    print("distribution provides:")

    for provided in sorted(info.get_provides(options.api_ignore)):
        print(" ", provided)
    print()


def cli_dist_requires(options, info):
    print("distribution requires:")

    for required in sorted(info.get_requires(options.api_ignore)):
        print(" ", required)
    print()


def cli_distinfo(options, info):

    if options.dist_provides:
        cli_dist_provides(options, info)

    if options.dist_requires:
        cli_dist_requires(options, info)

    # TODO: simple things like listing JARs and non-JAR files


def cli_distinfo_json(options, info):
    data = {}

    if options.dist_provides:
        data["dist.provides"] = info.get_provides(options.api_ignore)

    if options.dist_requires:
        data["dist.requires"] = info.get_requires(options.api_ignore)

    dump(data, sys.stdout, sort_keys=True, indent=2)


def cli(options):
    # pylint: disable=W0613
    # parser unused

    pathn = options.dist
    info = DistInfo(pathn)

    if options.json:
        cli_distinfo_json(options, info)
    else:
        cli_distinfo(options, info)

    info.close()
    return 0


def add_distinfo_optgroup(parser):
    g = parser.add_argument_group("Distribution Info Options")

    g.add_argument("--dist-provides", dest="dist_provides",
                   action="store_true", default=False,
                   help="API provides information at the distribution level")

    g.add_argument("--dist-requires", dest="dist_requires",
                   action="store_true", default=False,
                   help="API requires information at the distribution level")


def create_optparser(progname):
    from .jarinfo import add_jarinfo_optgroup
    from .classinfo import add_classinfo_optgroup

    parser = ArgumentParser(prog=progname)
    parser.add_argument("dist", help="distribution to inspect")
    parser.add_argument("--json", dest="json", action="store_true",
                        help="output in JSON mode")

    add_distinfo_optgroup(parser)
    add_jarinfo_optgroup(parser)
    add_classinfo_optgroup(parser)

    return parser


def main(args=sys.argv):
    parser = create_optparser(args[0])
    return cli(parser.parse_args(args[1:]))


#
# The end.
