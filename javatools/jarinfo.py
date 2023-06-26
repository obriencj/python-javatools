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
Module and utility for fetching information out of a JAR file, and
printing it out.

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""


from __future__ import print_function


import sys

from argparse import ArgumentParser
from json import dump

from . import unpack_class
from .classinfo import cli_print_classinfo, add_classinfo_optgroup
from .dirutils import fnmatches
from .ziputils import open_zip_entry, zip_file, zip_entry_rollup
from .manifest import Manifest


__all__ = (
    "JAR_PATTERNS", "JarInfo",
    "main", "cli", "add_jarinfo_optgroup",
    "cli_jar_classes", "cli_jar_manifest_info",
    "cli_jar_provides", "cli_jar_requires",
    "cli_jar_zip_info", "cli_jarinfo",
    "cli_jarinfo_json",
)


# for reference by other modules
JAR_PATTERNS = (
    "*.ear",
    "*.jar",
    "*.rar",
    "*.sar",
    "*.war",
)


REQ_BY_CLASS = "class.requires"
PROV_BY_CLASS = "class.provides"


class JarInfo(object):

    def __init__(self, filename=None, zipfile=None):
        if not (filename or zipfile):
            raise TypeError("one of pathname or zipinfo must be specified")

        self.filename = filename
        self.zipfile = zipfile

        self._requires = None
        self._provides = None


    def __del__(self):
        self.close()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return exc_type is None


    def open(self, entry, mode='r'):
        return open_zip_entry(self.get_zipfile(), entry, mode)


    def _collect_requires_provides(self):
        req = {}
        prov = {}

        # we need to collect private provides in order to satisfy deps
        # for things like anonymous inner classes, which have access
        # to private members of their parents. This is only used to
        # filter out false-positive requirements.
        p = set()

        for entry in self.get_classes():
            ci = self.get_classinfo(entry)
            for sym in ci.get_requires():
                req.setdefault(sym, list()).append((REQ_BY_CLASS, entry))
            for sym in ci.get_provides(private=False):
                prov.setdefault(sym, list()).append((PROV_BY_CLASS, entry))
            for sym in ci.get_provides(private=True):
                p.add(sym)

        req = dict((k, v) for k, v in req.items() if k not in p)

        self._requires = req
        self._provides = prov


    def get_requires(self, ignored=tuple()):
        if self._requires is None:
            self._collect_requires_provides()

        d = self._requires
        if ignored:
            d = dict((k, v) for k, v in d.items()
                     if not fnmatches(k, *ignored))
        return d


    def get_provides(self, ignored=tuple()):
        if self._provides is None:
            self._collect_requires_provides()

        d = self._provides
        if ignored:
            d = dict((k, v) for k, v in d.items()
                     if not fnmatches(k, *ignored))
        return d


    def get_classes(self):
        """
        sequence of .class files in the underlying zip
        """

        for n in self.get_zipfile().namelist():
            if fnmatches(n, "*.class"):
                yield n


    def get_classinfo(self, entry):
        """
        fetch a class entry as a JavaClassInfo instance
        """

        with self.open(entry) as cfd:
            return unpack_class(cfd)


    def get_zipfile(self):
        if self.zipfile is None:
            self.zipfile = zip_file(self.filename)
        return self.zipfile


    def get_manifest(self):
        mf = Manifest()
        mf.load_from_jar(self.filename)
        return mf


    def close(self):
        if self.zipfile:
            self.zipfile.close()
            self.zipfile = None


def cli_jar_manifest_info(jarinfo):
    mf = jarinfo.get_manifest()

    if not mf:
        print("Manifest not present.")
        print()
        return

    print("Manifest main section:")
    for k, v in sorted(mf.items()):
        print("  %s: %s" % (k, v))

    for _name, sect in sorted(mf.sub_sections.items()):
        print()
        print("Manifest sub-section:")
        for k, v in sorted(sect.items()):
            print("  %s: %s" % (k, v))

    print()


def cli_jar_zip_info(jarinfo):
    zipfile = jarinfo.get_zipfile()

    files, dirs, comp, uncomp = zip_entry_rollup(zipfile)
    prcnt = (float(comp) / float(uncomp)) * 100

    print("Contains %i files, %i directories" % (files, dirs))
    print("Uncompressed size is %i" % uncomp)
    print("Compressed size is %i (%0.1f%%)" % (comp, prcnt))
    print()


def cli_jar_classes(options, jarinfo):
    for entry in jarinfo.get_classes():
        ci = jarinfo.get_classinfo(entry)
        print("Entry: ", entry)
        cli_print_classinfo(options, ci)
        print()


def cli_jar_provides(options, jarinfo):
    print("jar provides:")

    for provided in sorted(jarinfo.get_provides().keys()):
        if not fnmatches(provided, *options.api_ignore):
            print(" ", provided)
    print()


def cli_jar_requires(options, jarinfo):
    print("jar requires:")

    for required in sorted(jarinfo.get_requires().keys()):
        if not fnmatches(required, *options.api_ignore):
            print(" ", required)
    print()


def cli_jarinfo(options, info):
    if options.zip:
        cli_jar_zip_info(info)

    if options.manifest:
        cli_jar_manifest_info(info)

    if options.jar_provides:
        cli_jar_provides(options, info)

    if options.jar_requires:
        cli_jar_requires(options, info)

    if options.jar_classes:
        cli_jar_classes(options, info)


def cli_jarinfo_json(options, info):
    data = {}

    if options.jar_provides:
        data["jar.provides"] = info.get_provides(options.api_ignore)

    if options.jar_requires:
        data["jar.requires"] = info.get_requires(options.api_ignore)

    if options.zip:
        zipfile = info.get_zipfile()
        filec, dirc, totalc, totalu = zip_entry_rollup(zipfile)
        prcnt = (float(totalc) / float(totalu)) * 100

        data["zip.type"] = zipfile.__class__.__name__
        data["zip.file_count"] = filec
        data["zip.dir_count"] = dirc
        data["zip.uncompressed_size"] = totalu
        data["zip.compressed_size"] = totalc
        data["zip.compress_percent"] = prcnt

    dump(data, sys.stdout, sort_keys=True, indent=2)


def cli(options):
    if options.verbose:
        options.zip = True
        options.lines = True
        options.locals = True
        options.disassemble = True
        options.sigs = True
        options.constpool = True

    options.indent = not (options.lines or
                          options.disassemble or
                          options.sigs)

    for fn in options.jarfiles:
        with JarInfo(filename=fn) as ji:
            if options.json:
                cli_jarinfo_json(options, ji)
            else:
                cli_jarinfo(options, ji)

    return 0


def add_jarinfo_optgroup(parser):
    g = parser.add_argument_group("JAR Info Options")

    g.add_argument("--zip", action="store_true", default=False,
                   help="print zip information")

    g.add_argument("--manifest", action="store_true", default=False,
                   help="print manifest information")

    g.add_argument("--jar-classes", action="store_true", default=False,
                   help="print information about contained classes")

    g.add_argument("--jar-provides", dest="jar_provides",
                   action="store_true", default=False,
                   help="API provides information at the JAR level")

    g.add_argument("--jar-requires", dest="jar_requires",
                   action="store_true", default=False,
                   help="API requires information at the JAR level")


def create_optparser(progname):
    parser = ArgumentParser(progname)

    parser.add_argument("jarfiles", nargs="+",
                        help="JAR files to inspect")
    parser.add_argument("--json", dest="json", action="store_true",
                        help="output in JSON mode")
    add_jarinfo_optgroup(parser)
    add_classinfo_optgroup(parser)

    return parser


def main(args=sys.argv):
    parser = create_optparser(args[0])
    return cli(parser.parse_args(args[1:]))


#
# The end.
