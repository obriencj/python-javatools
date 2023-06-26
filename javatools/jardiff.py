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
Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

:author: Christopher O'Brien  <obriencj@gmail.com>
:licence: LGPL
"""

import sys
from argparse import ArgumentParser
from os.path import isdir

from . import unpack_class
from .change import GenericChange, SuperChange, Addition, Removal
from .change import squash, yield_sorted_by_type
from .classdiff import JavaClassChange, JavaClassReport
from .dirutils import fnmatches
from .manifest import Manifest, ManifestChange
from .manifest import SignatureManifestChange, SignatureBlockFileChange
from .manifest import file_matches_sigfile, file_matches_sigblock
from .ziputils import compare_zips, open_zip, open_zip_entry
from .ziputils import LEFT, RIGHT, DIFF, SAME


__all__ = (
    "JarChange",
    "JarTypeChange", "JarContentsChange",
    "JarManifestChange",
    "JarContentChange", "JarContentAdded", "JarContentRemoved",
    "JarSignatureFileChange", "JarSignatureFileAdded",
    "JarSignatureFileRemoved",
    "JarSignatureBlockFileChange", "JarSignatureBlockFileAdded",
    "JarSignatureBlockFileRemoved",
    "JarClassChange", "JarClassAdded", "JarClassRemoved",
    "JarReport", "JarContentsReport", "JarClassReport",
    "cli", "main",
    "cli_jars_diff",
    "add_jardiff_optgroup", "default_jardiff_options", )


class JarTypeChange(GenericChange):
    """
    exploded vs. zipped and compression level
    """

    label = "Jar type"


    def fn_data(self, c):
        # TODO: create some kind of menial zipinfo output showing type
        # (exploded/zipped) and compression level

        return isdir(c)


    def fn_pretty(self, c):
        if isdir(c):
            return "exploded JAR"
        else:
            return "zipped JAR file"


class JarContentChange(SuperChange):
    """
    a file or directory changed between JARs
    """

    label = "Jar Content"


    def __init__(self, lzip, rzip, entry, is_change=True):
        super(JarContentChange, self).__init__(lzip, rzip)
        self.entry = entry
        self.changed = is_change


    def open_left(self):
        return open_zip_entry(self.ldata, self.entry)


    def open_right(self):
        return open_zip_entry(self.rdata, self.entry)


    def collect_impl(self):
        """
        Content changes refer to more concrete children, but by default
        are empty
        """

        return tuple()


    def get_description(self):
        c = "has changed" if self.is_change() else "is unchanged"
        return "%s %s: %s" % (self.label, c, self.entry)


    def is_ignored(self, options):
        return fnmatches(self.entry, *options.ignore_jar_entry) or \
            super(JarContentChange, self).is_ignored(options)


class JarContentAdded(JarContentChange, Addition):

    label = "Jar Content Added"


    def get_description(self):
        return "%s: %s" % (self.label, self.entry)


class JarContentRemoved(JarContentChange, Removal):

    label = "Jar Content Removed"


    def get_description(self):
        return "%s: %s" % (self.label, self.entry)


class JarClassAdded(JarContentAdded):

    label = "Java Class Added"


class JarClassRemoved(JarContentRemoved):

    label = "Java Class Removed"


class JarClassChange(JarContentChange):

    label = "Java Class"


    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd:
                linfo = unpack_class(lfd.read())

            with self.open_right() as rfd:
                rinfo = unpack_class(rfd.read())

            yield JavaClassChange(linfo, rinfo)


class JarClassReport(JarClassChange):

    report_name = "JavaClassReport"


    def __init__(self, l, r, entry, reporter):
        super(JarClassReport, self).__init__(l, r, entry)
        self.reporter = reporter


    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd:
                linfo = unpack_class(lfd.read())

            with self.open_right() as rfd:
                rinfo = unpack_class(rfd.read())

            yield JavaClassReport(linfo, rinfo, self.reporter)


class JarManifestChange(JarContentChange):

    label = "Jar Manifest"


    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd:
                lm = Manifest()
                lm.parse(lfd.read())

            with self.open_right() as rfd:
                rm = Manifest()
                rm.parse(rfd.read())

            yield ManifestChange(lm, rm)


class JarSignatureFileChange(JarContentChange):

    label = "Jar Signature File"

    def is_ignored(self, options):
        return options.ignore_jar_signature

    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd:
                lm = Manifest()
                lm.parse(lfd.read())

            with self.open_right() as rfd:
                rm = Manifest()
                rm.parse(rfd.read())

            yield SignatureManifestChange(lm, rm)


class JarSignatureFileAdded(JarContentAdded):

    label = "Jar Signature File Added"

    def is_ignored(self, options):
        return options.ignore_jar_signature


class JarSignatureFileRemoved(JarContentRemoved):

    label = "Jar Signature File Removed"

    def is_ignored(self, options):
        return options.ignore_jar_signature


class JarSignatureBlockFileChange(JarContentChange):

    label = "Jar Signature Block File"

    def is_ignored(self, options):
        return options.ignore_jar_signature

    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd, self.open_right() as rfd:
                lsig = lfd.read()
                rsig = rfd.read()
            yield SignatureBlockFileChange(lsig, rsig)


class JarSignatureBlockFileAdded(JarContentAdded):

    label = "Jar Signature Block File Added"


    def is_ignored(self, options):
        return options.ignore_jar_signature


class JarSignatureBlockFileRemoved(JarContentRemoved):

    label = "Jar Signature Block File Removed"


    def is_ignored(self, options):
        return options.ignore_jar_signature


class GenericFileChange(GenericChange):
    label = "Generic File"

    def get_description(self):
        return "[generic file change]"

    def fn_pretty(self, side_data):
        # We do not know how to represent it.
        # E.g. binary data can choke JSON encoder.
        return "[data]"


class JarGenericFileChange(JarContentChange):

    label = "Jar Generic File"

    def collect_impl(self):
        if self.is_change():
            with self.open_left() as lfd, self.open_right() as rfd:
                lsig = lfd.read()
                rsig = rfd.read()
            yield GenericFileChange(lsig, rsig)


class JarContentsChange(SuperChange):

    label = "JAR Contents"


    def __init__(self, left_fn, right_fn):
        super(JarContentsChange, self).__init__(left_fn, right_fn)
        self.lzip = None
        self.rzip = None


    @yield_sorted_by_type(JarManifestChange,
                          JarSignatureFileAdded,
                          JarSignatureFileRemoved,
                          JarSignatureFileChange,
                          JarSignatureBlockFileAdded,
                          JarSignatureBlockFileRemoved,
                          JarSignatureBlockFileChange,
                          JarGenericFileChange,
                          JarContentAdded,
                          JarContentRemoved,
                          JarContentChange,
                          JarClassAdded,
                          JarClassRemoved,
                          JarClassChange)
    def collect_impl(self):
        # these are opened for the duration of check_impl
        left = self.lzip
        right = self.rzip

        # this is our guarantee from invokation order
        assert left is not None
        assert right is not None

        for event, entry in compare_zips(left, right):
            if event == SAME:

                # TODO: should we split by file type to more specific
                # types of (un)changes? For now just emit a content
                # change with is_change set to False.

                if entry == "META-INF/MANIFEST.MF":
                    yield JarManifestChange(left, right, entry, False)

                elif file_matches_sigfile(entry):
                    yield JarSignatureFileChange(left, right, entry, False)

                elif file_matches_sigblock(entry):
                    yield JarSignatureBlockFileChange(left, right,
                                                      entry, False)

                elif fnmatches(entry, "*.class"):
                    yield JarClassChange(left, right, entry, False)

                else:
                    yield JarContentChange(left, right, entry, False)

            elif event == DIFF:
                if entry == "META-INF/MANIFEST.MF":
                    yield JarManifestChange(left, right, entry)

                elif file_matches_sigfile(entry):
                    yield JarSignatureFileChange(left, right, entry)

                elif file_matches_sigblock(entry):
                    yield JarSignatureBlockFileChange(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassChange(left, right, entry)

                else:
                    yield JarGenericFileChange(left, right, entry)

            elif event == LEFT:
                if file_matches_sigfile(entry):
                    yield JarSignatureFileRemoved(left, right, entry)

                elif file_matches_sigblock(entry):
                    yield JarSignatureBlockFileRemoved(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassRemoved(left, right, entry)

                else:
                    yield JarContentRemoved(left, right, entry)

            elif event == RIGHT:
                if file_matches_sigfile(entry):
                    yield JarSignatureFileAdded(left, right, entry)

                elif file_matches_sigblock(entry):
                    yield JarSignatureBlockFileAdded(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassAdded(left, right, entry)

                else:
                    yield JarContentAdded(left, right, entry)


    def check_impl(self):
        """
        Overridden to open the left and right zipfiles and to provide all
        subchecks with an open ZipFile instance rather than having
        them all open and close the ZipFile individually. For the
        duration of the check (which calls collect_impl), the
        attributes self.lzip and self.rzip will be available and used
        as the ldata and rdata of all subchecks.
        """

        with open_zip(self.ldata) as lzip:
            with open_zip(self.rdata) as rzip:
                self.lzip = lzip
                self.rzip = rzip
                ret = super(JarContentsChange, self).check_impl()

        self.lzip = None
        self.rzip = None

        return ret


class JarChange(SuperChange):

    label = "JAR"


    change_types = (JarTypeChange,
                    JarContentsChange)


class JarContentsReport(JarContentsChange):
    """
    overridden JarContentsChange which will swap out JarClassChange
    with JarClassReport instances. The check_impl method gains the
    side effect of causing all JarClassReports gathered to write
    reports of themselves to file.
    """


    def __init__(self, left_fn, right_fn, reporter):
        super(JarContentsReport, self).__init__(left_fn, right_fn)
        self.reporter = reporter


    def collect_impl(self):
        # a filter on the collect_impl of JarContentsChange which
        # replaces JarClassChange instances with a JarClassReport
        # instance instead.

        for change in JarContentsChange.collect_impl(self):
            if isinstance(change, JarClassChange) and change.is_change():
                name = JarClassReport.report_name
                sub_r = self.reporter.subreporter(change.entry, name)
                change = JarClassReport(change.ldata, change.rdata,
                                        change.entry, sub_r)
            yield change


    def check_impl(self):
        options = self.reporter.options
        changes = list()
        c = False

        with open_zip(self.ldata) as lzip:
            with open_zip(self.rdata) as rzip:

                self.lzip = lzip
                self.rzip = rzip

                for change in self.collect_impl():
                    change.check()
                    c = c or change.is_change()

                    if isinstance(change, JarClassReport):
                        changes.append(squash(change, options=options))
                        change.clear()
                    else:
                        changes.append(change)

        self.lzip = None
        self.rzip = None

        self.changes = changes
        return c, None


class JarReport(JarChange):
    """
    This class has side-effects. Running the check method with the
    reportdir options set to True will cause the deep checks to be
    written to file in that directory
    """

    report_name = "JarReport"


    def __init__(self, l, r, reporter):
        super(JarReport, self).__init__(l, r)
        self.reporter = reporter


    def collect_impl(self):
        for c in JarChange.collect_impl(self):
            if isinstance(c, JarContentsChange):
                c = JarContentsReport(c.ldata, c.rdata, self.reporter)
            yield c


    def check(self):
        # do the actual checking
        JarChange.check(self)

        # write to file
        self.reporter.run(self)


# ---- Begin jardiff CLI ----
#


def cli_jars_diff(options, left, right):
    from .report import quick_report, Reporter
    from .report import JSONReportFormat, TextReportFormat

    reports = getattr(options, "reports", tuple())
    if reports:
        rdir = options.report_dir or "./"

        rpt = Reporter(rdir, JarReport.report_name, options)
        rpt.add_formats_by_name(reports)

        delta = JarReport(left, right, rpt)

    else:
        delta = JarChange(left, right)

    delta.check()

    if not options.silent:
        if options.json:
            quick_report(JSONReportFormat, delta, options)
        else:
            quick_report(TextReportFormat, delta, options)

    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1


def cli(options):

    left, right = options.jar
    return cli_jars_diff(options, left, right)


def add_jardiff_optgroup(parser):
    """
    option group specific to the tests in jardiff
    """

    og = parser.add_argument_group("JAR Checking Options")

    og.add_argument("--ignore-jar-entry", action="append", default=[])

    og.add_argument("--ignore-jar-signature",
                    action="store_true", default=False,
                    help="Ignore JAR signing changes")

    og.add_argument("--ignore-manifest",
                    action="store_true", default=False,
                    help="Ignore changes to manifests")

    og.add_argument("--ignore-manifest-subsections",
                    action="store_true", default=False,
                    help="Ignore changes to manifest subsections")

    og.add_argument("--ignore-manifest-key",
                    action="append", default=[],
                    help="case-insensitive manifest keys to ignore")


def create_optparser(progname=None):
    """
    an OptionParser instance with the appropriate options and groups
    for the jardiff utility
    """

    from .classdiff import add_general_optgroup, add_classdiff_optgroup
    from javatools import report

    parser = ArgumentParser(prog=progname)
    parser.add_argument("jar", nargs=2,
                        help="JAR files to compare")

    add_general_optgroup(parser)
    add_jardiff_optgroup(parser)
    add_classdiff_optgroup(parser)

    report.add_general_report_optgroup(parser)
    report.add_json_report_optgroup(parser)
    report.add_html_report_optgroup(parser)

    return parser


def default_jardiff_options(updates=None):
    """
    generate an options object with the appropriate default values in
    place for API usage of jardiff features. overrides is an optional
    dictionary which will be used to update fields on the options
    object.
    """

    parser = create_optparser()
    options, _args = parser.parse_args(list())

    if updates:
        # pylint: disable=W0212
        options._update_careful(updates)

    return options


def main(args=sys.argv):
    """
    main entry point for the jardiff CLI
    """

    parser = create_optparser(args[0])
    return cli(parser.parse_args(args[1:]))


#
# The end.
